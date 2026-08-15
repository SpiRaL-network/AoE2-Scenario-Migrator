from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    location: str = ""
    original: Any = None
    repaired: Any = None
    applied: bool = False


@dataclass(slots=True)
class LegacyEffect:
    effect_type: int
    fields: list[int]
    message: str = ""
    sound_name: str = ""
    selected_object_ids: list[int] = field(default_factory=list)
    offset: int = 0


@dataclass(slots=True)
class LegacyCondition:
    condition_type: int
    fields: list[int]
    offset: int = 0


@dataclass(slots=True)
class LegacyTrigger:
    name: str
    description: str
    enabled: int
    looping: int
    objective: int
    objective_order: int
    objective_string_id: int
    effects: list[LegacyEffect]
    effect_order: list[int]
    conditions: list[LegacyCondition]
    condition_order: list[int]
    offset: int = 0


@dataclass(slots=True)
class LegacyUnit:
    owner_block: int
    x: float
    y: float
    z: float
    reference_id: int
    unit_const: int
    status: int
    rotation: float
    animation_frame: int
    garrisoned_in_id: int
    offset: int = 0


@dataclass(slots=True)
class LegacyPlayer:
    legacy_index: int
    name: str = ""
    string_table_name_id: int = -1
    enabled: int = 0
    human: int = 0
    civilization: int = 0
    resources: list[int] = field(default_factory=lambda: [0] * 6)
    player_number: int = 0
    diplomacy: list[int] = field(default_factory=lambda: [3] * 16)
    disabled_techs: list[int] = field(default_factory=list)
    disabled_units: list[int] = field(default_factory=list)
    disabled_buildings: list[int] = field(default_factory=list)
    starting_age: int = 0
    population_limit: int = 200
    camera_x: float = 0
    camera_y: float = 0
    allied_victory: int = 0
    color: int = 0
    ai_mode: int = 0
    ai_names: dict[str, str] = field(default_factory=dict)
    embedded_ai: dict[str, bytes] = field(default_factory=dict)


@dataclass(slots=True)
class LegacyScenario:
    source: Path
    source_sha256: str
    outer_version: str
    inner_version: str
    format_name: str
    compressed_offset: int
    next_uid: int
    original_filename: str
    message_string_ids: list[int]
    messages: list[str]
    cinematics: list[str]
    players: list[LegacyPlayer]
    lock_teams: int
    allow_players_choose_teams: int
    random_start_points: int
    max_teams: int
    all_techs: int
    victory: list[int]
    map_ai_type: int
    map_width: int
    map_height: int
    terrain: list[tuple[int, int]]
    units: list[LegacyUnit]
    triggers: list[LegacyTrigger]
    trigger_order: list[int]
    included_files: list[tuple[str, bytes]]
    findings: list[Finding] = field(default_factory=list)
    trailing_bytes: int = 0

    @property
    def unit_count(self) -> int:
        return len(self.units)

    @property
    def effect_count(self) -> int:
        return sum(len(trigger.effects) for trigger in self.triggers)

    @property
    def condition_count(self) -> int:
        return sum(len(trigger.conditions) for trigger in self.triggers)

    def summary(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "source_sha256": self.source_sha256,
            "format": self.format_name,
            "outer_version": self.outer_version,
            "inner_version": self.inner_version,
            "original_filename": self.original_filename,
            "map": {"width": self.map_width, "height": self.map_height},
            "players_enabled": sum(bool(player.enabled) for player in self.players[:8]),
            "units": self.unit_count,
            "triggers": len(self.triggers),
            "effects": self.effect_count,
            "conditions": self.condition_count,
            "included_files": [name for name, _ in self.included_files],
            "findings": [asdict(item) for item in self.findings],
            "trailing_bytes": self.trailing_bytes,
        }


class ScenarioFormatError(RuntimeError):
    """Raised when an input is unsupported, truncated, or structurally unsafe."""
