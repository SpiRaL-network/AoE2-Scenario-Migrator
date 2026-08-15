from __future__ import annotations

import hashlib
import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import (
    Finding,
    LegacyCondition,
    LegacyEffect,
    LegacyPlayer,
    LegacyScenario,
    LegacyTrigger,
    LegacyUnit,
    ScenarioFormatError,
    Severity,
)

SECTION_MARKER = -99
PLAYER_SLOTS = 16
PLAYABLE_PLAYERS = 8
MAX_REASONABLE_COUNT = 1_000_000


@dataclass(frozen=True, slots=True)
class VersionProfile:
    code: int
    name: str
    messages: int
    max_disabled_techs_units: int
    max_disabled_buildings: int
    has_map_ai_type: bool
    has_hd_teams: bool
    has_player_numbers: bool
    has_map_unknowns: bool
    has_population: bool


PROFILES: dict[int, VersionProfile] = {
    code: VersionProfile(code, "Age of Kings", 5, 30, 20, False, False, False, False, False)
    for code in (118, 119, 120, 121)
}
PROFILES.update(
    {
        122: VersionProfile(122, "The Conquerors", 6, 30, 20, True, False, False, False, True),
        123: VersionProfile(123, "AoE2 HD", 6, 30, 20, True, True, False, False, True),
        124: VersionProfile(124, "AoE2 HD Patch 4", 6, 30, 20, True, True, True, True, True),
        126: VersionProfile(126, "AoE2 HD Patch 6", 6, 30, 30, True, True, True, True, True),
    }
)


@dataclass(slots=True)
class Reader:
    data: bytes
    pos: int = 0

    def take(self, size: int, label: str) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise ScenarioFormatError(
                f"{label}: needs {size} bytes at 0x{self.pos:X}; "
                f"only {len(self.data) - self.pos} remain"
            )
        start = self.pos
        self.pos += size
        return self.data[start : self.pos]

    def unpack(self, fmt: str, label: str) -> Any:
        raw = self.take(struct.calcsize("<" + fmt), label)
        values = struct.unpack("<" + fmt, raw)
        return values[0] if len(values) == 1 else values

    def many(self, fmt: str, label: str) -> tuple[Any, ...]:
        raw = self.take(struct.calcsize("<" + fmt), label)
        return struct.unpack("<" + fmt, raw)

    def i8(self, label: str) -> int:
        return self.unpack("b", label)

    def u8(self, label: str) -> int:
        return self.unpack("B", label)

    def i16(self, label: str) -> int:
        return self.unpack("h", label)

    def u16(self, label: str) -> int:
        return self.unpack("H", label)

    def i32(self, label: str) -> int:
        return self.unpack("i", label)

    def u32(self, label: str) -> int:
        return self.unpack("I", label)

    def f32(self, label: str) -> float:
        return self.unpack("f", label)

    def f64(self, label: str) -> float:
        return self.unpack("d", label)

    def sized(self, length_size: int, label: str) -> bytes:
        size = self.u16(label + ".length") if length_size == 2 else self.u32(label + ".length")
        if size > len(self.data) - self.pos:
            raise ScenarioFormatError(f"{label}: impossible length {size} at 0x{self.pos:X}")
        return self.take(size, label)


def _text(raw: bytes) -> str:
    return raw.rstrip(b"\0").decode("cp1252", errors="replace")


def _count(value: int, label: str, remaining: int, item_size: int = 1) -> None:
    if value < 0 or value > MAX_REASONABLE_COUNT or value * item_size > remaining:
        raise ScenarioFormatError(f"{label}: unsafe count {value} at remaining size {remaining}")


def _inflate(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) < 32:
        raise ScenarioFormatError("The file is too short to be an AoE2 legacy scenario")
    outer_version = raw[:4].decode("ascii", errors="replace")
    header_length, check, timestamp, instructions_length = struct.unpack_from("<IIII", raw, 4)
    expected = 20 + instructions_length + 8
    candidates: list[tuple[int, bytes, int]] = []
    for extra in range(65):
        start = expected + extra
        if start >= len(raw):
            break
        try:
            inflater = zlib.decompressobj(-15)
            data = inflater.decompress(raw[start:]) + inflater.flush()
        except zlib.error:
            continue
        if not inflater.eof or len(data) < 8:
            continue
        inner = struct.unpack_from("<f", data, 4)[0]
        if math.isfinite(inner) and round(inner * 100) in PROFILES:
            candidates.append((start, data, len(inflater.unused_data)))
    if not candidates:
        raise ScenarioFormatError(
            "No supported AoK/AoC/HD raw-deflate stream was found in the scenario"
        )
    start, data, trailing = min(candidates, key=lambda item: item[0])
    return data, {
        "outer_version": outer_version,
        "header_length": header_length,
        "check": check,
        "timestamp": timestamp,
        "instructions_length": instructions_length,
        "compressed_offset": start,
        "outer_trailing_bytes": trailing,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _read_effect(r: Reader, trigger_index: int, effect_index: int) -> LegacyEffect:
    start = r.pos
    effect_type = r.i32(f"trigger[{trigger_index}].effect[{effect_index}].type")
    field_count = r.i32(f"trigger[{trigger_index}].effect[{effect_index}].field_count")
    if not 0 <= field_count <= 64:
        raise ScenarioFormatError(
            f"trigger {trigger_index} effect {effect_index}: invalid field count {field_count}"
        )
    fields = list(r.many(f"{field_count}i", "effect.fields")) if field_count else []
    message = _text(r.sized(4, "effect.message"))
    sound_name = _text(r.sized(4, "effect.sound"))
    selected_count = fields[4] if len(fields) > 4 else 0
    if selected_count > 0:
        _count(selected_count, "selected object count", len(r.data) - r.pos, 4)
        selected = list(r.many(f"{selected_count}i", "effect.selected_objects"))
    else:
        selected = []
    return LegacyEffect(effect_type, fields, message, sound_name, selected, start)


def _read_condition(r: Reader, trigger_index: int, condition_index: int) -> LegacyCondition:
    start = r.pos
    condition_type = r.i32(f"trigger[{trigger_index}].condition[{condition_index}].type")
    field_count = r.i32(f"trigger[{trigger_index}].condition[{condition_index}].field_count")
    if not 0 <= field_count <= 64:
        raise ScenarioFormatError(
            f"trigger {trigger_index} condition {condition_index}: invalid field count {field_count}"
        )
    fields = list(r.many(f"{field_count}i", "condition.fields")) if field_count else []
    return LegacyCondition(condition_type, fields, start)


def _read_trigger(r: Reader, index: int) -> LegacyTrigger:
    start = r.pos
    enabled = r.i32("trigger.enabled")
    looping = r.u8("trigger.looping")
    r.i32("trigger.unknown")
    objective = r.u8("trigger.objective")
    objective_order = r.i32("trigger.objective_order")
    objective_string_id = r.i32("trigger.objective_string_id")
    description = _text(r.sized(4, "trigger.description"))
    name = _text(r.sized(4, "trigger.name"))
    effect_count = r.i32("trigger.effect_count")
    _count(effect_count, "trigger effect count", len(r.data) - r.pos, 8)
    effects = [_read_effect(r, index, i) for i in range(effect_count)]
    effect_order = [r.i32("trigger.effect_order") for _ in range(effect_count)]
    condition_count = r.i32("trigger.condition_count")
    _count(condition_count, "trigger condition count", len(r.data) - r.pos, 8)
    conditions = [_read_condition(r, index, i) for i in range(condition_count)]
    condition_order = [r.i32("trigger.condition_order") for _ in range(condition_count)]
    return LegacyTrigger(
        name,
        description,
        enabled,
        looping,
        objective,
        objective_order,
        objective_string_id,
        effects,
        effect_order,
        conditions,
        condition_order,
        start,
    )


def _read_bitmap(r: Reader, has_bitmap: int) -> None:
    r.take(8, "bitmap duplicate dimensions")
    r.i16("bitmap marker")
    if not has_bitmap:
        return
    info = r.take(40, "bitmap info header")
    image_size = struct.unpack_from("<I", info, 20)[0]
    colors_used = struct.unpack_from("<I", info, 32)[0] or 256
    r.take(colors_used * 4, "bitmap palette")
    r.take(image_size, "bitmap pixels")


def read_legacy_scenario(path: str | Path) -> LegacyScenario:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ScenarioFormatError(f"Input file not found: {source}")
    data, outer = _inflate(source)
    r = Reader(data)
    findings: list[Finding] = []
    next_uid = r.u32("next_uid")
    inner_float = r.f32("inner_version")
    profile = PROFILES.get(round(inner_float * 100))
    if profile is None:
        raise ScenarioFormatError(f"Unsupported inner scenario version {inner_float:.3f}")

    players = [LegacyPlayer(i, player_number=i, color=i) for i in range(PLAYER_SLOTS)]
    for player in players:
        player.name = _text(r.take(256, f"player[{player.legacy_index}].name"))
    for player in players:
        player.string_table_name_id = r.i32(f"player[{player.legacy_index}].name_stid")
    for player in players:
        player.enabled, player.human, player.civilization, unknown = r.unpack(
            "4i", f"player[{player.legacy_index}].metadata"
        )
        if unknown != 4:
            findings.append(
                Finding(
                    "LEGACY.PLAYER_METADATA_CONSTANT",
                    Severity.WARNING,
                    f"Player slot {player.legacy_index} metadata constant is {unknown}, expected 4",
                )
            )
    r.i32("post_player_unknown")
    r.i8("post_player_byte")
    r.f32("post_player_float")
    original_filename = _text(r.sized(2, "original_filename"))

    message_stids = [r.i32("message_string_id") for _ in range(profile.messages)]
    messages = [_text(r.sized(2, f"message[{i}]")) for i in range(profile.messages)]
    cinematics = [_text(r.sized(2, f"cinematic[{i}]")) for i in range(4)]
    _read_bitmap(r, r.i32("has_bitmap"))

    for kind in ("vc", "cty", "ai"):
        for player in players:
            player.ai_names[kind] = _text(r.sized(2, f"player[{player.legacy_index}].{kind}"))
    for player in players:
        sizes = [r.u32(f"player[{player.legacy_index}].embedded_ai_size") for _ in range(3)]
        for kind, size in zip(("vc", "cty", "ai"), sizes):
            if size:
                player.embedded_ai[kind] = r.take(size, f"player[{player.legacy_index}].{kind}_data")
    for player in players:
        player.ai_mode = r.u8(f"player[{player.legacy_index}].ai_mode")

    if r.i32("resources_section") != SECTION_MARKER:
        findings.append(Finding("LEGACY.SECTION_MARKER", Severity.WARNING, "Resources marker differs from -99"))
    for player in players:
        player.resources = list(r.unpack("6I", f"player[{player.legacy_index}].resources"))
        if profile.has_player_numbers:
            player.player_number = r.i32(f"player[{player.legacy_index}].player_number")
    if r.i32("victory_section") != SECTION_MARKER:
        findings.append(Finding("LEGACY.SECTION_MARKER", Severity.WARNING, "Victory marker differs from -99"))
    victory = list(r.unpack("10i", "global_victory"))
    for player in players:
        player.diplomacy = list(r.unpack("16i", f"player[{player.legacy_index}].diplomacy"))
    r.take(0x2D00, "diplomacy padding")
    r.i32("diplomacy middle marker")
    r.take(PLAYER_SLOTS * 4, "allied victory duplicate")
    lock_teams = allow_teams = random_starts = 0
    max_teams = 4
    if profile.has_hd_teams:
        lock_teams, allow_teams, random_starts, max_teams = r.unpack("4B", "HD team settings")

    for kind, attr, maximum in (
        ("technology", "disabled_techs", profile.max_disabled_techs_units),
        ("unit", "disabled_units", profile.max_disabled_techs_units),
        ("building", "disabled_buildings", profile.max_disabled_buildings),
    ):
        count_offsets: list[int] = []
        counts: list[int] = []
        for player in players:
            count_offsets.append(r.pos)
            counts.append(r.i32(f"player[{player.legacy_index}].disabled_{kind}_count"))
        all_values = [
            list(r.unpack(f"{maximum}i", f"player[{player.legacy_index}].disabled_{kind}"))
            for player in players
        ]
        for player, count, values, offset in zip(players, counts, all_values, count_offsets):
            safe_count = min(max(count, 0), maximum)
            if count != safe_count:
                findings.append(
                    Finding(
                        "REPAIR.DISABLED_COUNT_RANGE",
                        Severity.ERROR,
                        f"Invalid disabled-{kind} count for legacy player slot {player.legacy_index}",
                        f"decompressed:0x{offset:X}",
                        count,
                        safe_count,
                        True,
                    )
                )
            setattr(player, attr, [value for value in values[:safe_count] if value >= 0])
    r.take(8, "disabled unused")
    all_techs = r.i32("all_techs")
    for player in players:
        player.starting_age = r.i32(f"player[{player.legacy_index}].starting_age")

    if r.i32("map_section") != SECTION_MARKER:
        findings.append(Finding("LEGACY.SECTION_MARKER", Severity.WARNING, "Map marker differs from -99"))
    camera_y, camera_x = r.unpack("2i", "legacy camera")
    players[0].camera_x, players[0].camera_y = camera_x, camera_y
    map_ai_type = r.i32("map_ai_type") if profile.has_map_ai_type else 0
    if profile.has_map_unknowns:
        r.take(16, "HD map unknowns")
    width, height = r.unpack("2I", "map dimensions")
    if not (1 <= width <= 480 and 1 <= height <= 480):
        raise ScenarioFormatError(f"Unsafe map dimensions {width}x{height}")
    terrain = []
    for x in range(width):
        for y in range(height):
            terrain_id, elevation, zero = r.unpack("3B", f"terrain[{x},{y}]")
            if zero:
                findings.append(
                    Finding(
                        "LEGACY.TERRAIN_PADDING",
                        Severity.WARNING,
                        f"Terrain tile {x},{y} has non-zero padding {zero}",
                    )
                )
            terrain.append((terrain_id, elevation))

    if r.i32("player_count_before_units") != 9:
        findings.append(Finding("LEGACY.PLAYER_COUNT", Severity.WARNING, "Unit section player count differs from 9"))
    for player in players[:PLAYABLE_PLAYERS]:
        duplicates = list(r.unpack("6f", f"player[{player.legacy_index}].resource_duplicates"))
        if profile.has_population:
            player.population_limit = max(0, round(r.f32(f"player[{player.legacy_index}].population")))
        if not all(math.isfinite(value) for value in duplicates):
            findings.append(Finding("LEGACY.RESOURCE_FLOAT", Severity.WARNING, "Non-finite duplicate resource value"))

    units: list[LegacyUnit] = []
    unit_owner_blocks = [8, *range(8)]
    seen_ids: set[int] = set()
    duplicate_ids: list[int] = []
    for owner in unit_owner_blocks:
        unit_count = r.u32(f"player[{owner}].unit_count")
        _count(unit_count, f"player {owner} unit count", len(data) - r.pos, 29)
        for index in range(unit_count):
            start = r.pos
            y, x, z, reference_id, unit_const, status, rotation, frame, garrison = r.unpack(
                "3fIhbfhI", f"player[{owner}].unit[{index}]"
            )
            if reference_id in seen_ids:
                duplicate_ids.append(reference_id)
            seen_ids.add(reference_id)
            units.append(
                LegacyUnit(owner, x, y, z, reference_id, unit_const, status, rotation, frame, garrison, start)
            )
    for duplicate in sorted(set(duplicate_ids)):
        findings.append(
            Finding(
                "REPAIR.DUPLICATE_UNIT_REFERENCE",
                Severity.ERROR,
                f"Duplicate unit reference ID {duplicate}; conversion requires deterministic remapping",
                original=duplicate,
            )
        )

    if r.i32("player_count_before_player_data_3") != 9:
        findings.append(Finding("LEGACY.PLAYER_COUNT", Severity.WARNING, "Player-data-3 count differs from 9"))
    for player in players[:PLAYABLE_PLAYERS]:
        name_length = r.i16(f"player[{player.legacy_index}].pd3_name_length")
        if name_length < 0:
            raise ScenarioFormatError(f"Negative player-data-3 name length for player {player.legacy_index}")
        r.take(name_length, "player-data-3 constant name")
        player.camera_x, player.camera_y = r.unpack("2f", "player-data-3 camera")
        r.take(4, "player-data-3 shorts")
        player.allied_victory = r.u8("player-data-3 allied victory")
        diplomacy_count = r.i16("player-data-3 diplomacy count")
        if not 0 <= diplomacy_count <= 16:
            raise ScenarioFormatError(f"Unsafe player-data-3 diplomacy count {diplomacy_count}")
        r.take(diplomacy_count * 5, "player-data-3 diplomacy arrays")
        player.color = r.i32("player-data-3 color")
        version = r.f32("player-data-3 version")
        extra_count = r.i16("player-data-3 extra count")
        if version == 2.0:
            r.take(8, "player-data-3 version-2 bytes")
        if extra_count < 0:
            raise ScenarioFormatError(f"Unsafe player-data-3 extra record count {extra_count}")
        r.take(extra_count * 44, "player-data-3 extra records")
        r.take(7, "player-data-3 tail")
        r.i32("player-data-3 end")

    r.f64("trigger_system_version")
    r.u8("objective_state")
    trigger_count = r.u32("trigger_count")
    _count(trigger_count, "trigger count", len(data) - r.pos, 30)
    triggers = [_read_trigger(r, index) for index in range(trigger_count)]
    trigger_order = [r.u32("trigger_order") for _ in range(trigger_count)]

    included_unknown_1, included_unknown_2 = r.unpack("2i", "included file flags")
    if included_unknown_2 == 1:
        r.take(396, "included file compatibility header")
    included_files: list[tuple[str, bytes]] = []
    if included_unknown_1 == 1:
        included_count = r.i32("included_file_count")
        _count(included_count, "included file count", len(data) - r.pos, 8)
        for index in range(included_count):
            name = _text(r.sized(4, f"included_file[{index}].name"))
            payload = r.sized(4, f"included_file[{index}].payload")
            included_files.append((name, payload))

    trailing_bytes = len(data) - r.pos
    if trailing_bytes:
        findings.append(
            Finding(
                "LEGACY.TRAILING_BYTES",
                Severity.WARNING,
                f"{trailing_bytes} unparsed bytes remain at the end of the decompressed scenario",
            )
        )
    return LegacyScenario(
        source=source,
        source_sha256=outer["sha256"],
        outer_version=outer["outer_version"],
        inner_version=f"{inner_float:.2f}",
        format_name=profile.name,
        compressed_offset=outer["compressed_offset"],
        next_uid=next_uid,
        original_filename=original_filename,
        message_string_ids=message_stids,
        messages=messages,
        cinematics=cinematics,
        players=players,
        lock_teams=lock_teams,
        allow_players_choose_teams=allow_teams,
        random_start_points=random_starts,
        max_teams=max_teams,
        all_techs=all_techs,
        victory=victory,
        map_ai_type=map_ai_type,
        map_width=width,
        map_height=height,
        terrain=terrain,
        units=units,
        triggers=triggers,
        trigger_order=trigger_order,
        included_files=included_files,
        findings=findings,
        trailing_bytes=trailing_bytes,
    )
