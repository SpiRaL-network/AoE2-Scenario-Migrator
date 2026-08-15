from __future__ import annotations

import contextlib
import hashlib
import io
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

from .converter import build_de_scenario, latest_target_version, write_de_scenario
from .legacy import read_legacy_scenario
from .models import LegacyScenario, ScenarioFormatError
from .repairs import apply_safe_repairs
from .report import write_html_report, write_json_report

APP_VERSION = "0.1.0"
Progress = Callable[[str], None]


@dataclass(slots=True)
class ConversionOptions:
    output_dir: Path | None = None
    overwrite: bool = False
    aggressive_repair: bool = False
    json_report: bool = True
    html_report: bool = True


def _notify(callback: Progress | None, message: str) -> None:
    if callback:
        callback(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _output_path(source: Path, options: ConversionOptions) -> Path:
    directory = (options.output_dir or source.parent).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{source.stem}_DE_LATEST.aoe2scenario"
    if options.overwrite or not candidate.exists():
        return candidate
    number = 2
    while True:
        alternate = directory / f"{source.stem}_DE_LATEST_{number}.aoe2scenario"
        if not alternate.exists():
            return alternate
        number += 1


def inspect_file(path: str | Path, *, aggressive_repair: bool = False) -> LegacyScenario:
    scenario = read_legacy_scenario(path)
    apply_safe_repairs(scenario, aggressive=aggressive_repair)
    return scenario


def _validate_output(path: Path, source: LegacyScenario) -> dict[str, Any]:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        parsed = AoE2DEScenario.from_file(str(path))
    unit_count = len(parsed.unit_manager.get_all_units())
    trigger_count = len(parsed.trigger_manager.triggers)
    effect_count = sum(len(trigger.effects) for trigger in parsed.trigger_manager.triggers)
    condition_count = sum(len(trigger.conditions) for trigger in parsed.trigger_manager.triggers)
    terrain_matches = True
    for x in range(source.map_width):
        for y in range(source.map_height):
            expected_id, expected_elevation = source.terrain[x * source.map_height + y]
            if source.inner_version in {"1.18", "1.19", "1.20", "1.21", "1.22"} and expected_id == 41:
                expected_id = 47
            tile = parsed.map_manager.get_tile(x, y)
            if int(tile.terrain_id) != expected_id or tile.elevation != max(0, min(8, expected_elevation)):
                terrain_matches = False
                break
        if not terrain_matches:
            break

    expected_units = {
        unit.reference_id: (
            0 if unit.owner_block == 8 else unit.owner_block + 1,
            unit.unit_const,
            round(unit.x, 5),
            round(unit.y, 5),
            round(unit.z, 5),
            unit.status,
            unit.animation_frame,
            -1 if source.format_name == "Age of Kings" and unit.garrisoned_in_id == 0 else unit.garrisoned_in_id,
        )
        for unit in source.units
    }
    actual_units = {
        unit.reference_id: (
            int(unit._player),
            int(unit.unit_const),
            round(unit.x, 5),
            round(unit.y, 5),
            round(unit.z, 5),
            unit.status,
            unit.initial_animation_frame,
            unit.garrisoned_in_id,
        )
        for unit in parsed.unit_manager.get_all_units()
    }

    trigger_semantics = True
    if trigger_count == len(source.triggers):
        for old, new in zip(source.triggers, parsed.trigger_manager.triggers):
            if (
                old.name != new.name
                or old.description != new.description
                or old.enabled != new.enabled
                or old.looping != new.looping
                or old.effect_order != list(new.effect_order)
                or old.condition_order != list(new.condition_order)
                or [item.effect_type for item in old.effects] != [item.effect_type for item in new.effects]
                or [item.condition_type for item in old.conditions]
                != [item.condition_type for item in new.conditions]
            ):
                trigger_semantics = False
                break
    else:
        trigger_semantics = False

    message_matches = all(
        getattr(parsed.message_manager, field) == source.messages[index]
        for index, field in enumerate(("instructions", "hints", "victory", "loss", "history", "scouts"))
        if index < len(source.messages)
    )
    checks = {
        "map_size": parsed.map_manager.map_size == source.map_width,
        "terrain": terrain_matches,
        "units": unit_count == source.unit_count,
        "unit_semantics": expected_units == actual_units,
        "triggers": trigger_count == len(source.triggers),
        "effects": effect_count == source.effect_count,
        "conditions": condition_count == source.condition_count,
        "trigger_semantics": trigger_semantics,
        "messages": message_matches,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "actual": {
            "map_size": parsed.map_manager.map_size,
            "units": unit_count,
            "triggers": trigger_count,
            "effects": effect_count,
            "conditions": condition_count,
            "scenario_version": ".".join(str(v) for v in parsed.scenario_version_tuple),
        },
    }


def convert_file(
    path: str | Path,
    options: ConversionOptions | None = None,
    *,
    progress: Progress | None = None,
) -> dict[str, Any]:
    options = options or ConversionOptions()
    source_path = Path(path).expanduser().resolve()
    _notify(progress, f"Reading {source_path.name}")
    source = inspect_file(source_path, aggressive_repair=options.aggressive_repair)
    _notify(progress, f"Building AoE2 DE {latest_target_version()} scenario")
    target = build_de_scenario(source)
    destination = _output_path(source_path, options)
    if destination.exists() and options.overwrite:
        backup = destination.with_suffix(destination.suffix + ".bak")
        if backup.exists():
            backup.unlink()
        destination.replace(backup)
    else:
        backup = None

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=destination.stem + ".",
            suffix=".tmp.aoe2scenario",
            dir=destination.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
        _notify(progress, "Writing temporary output")
        write_de_scenario(target, temporary_path)
        _notify(progress, "Reopening and validating output")
        validation = _validate_output(temporary_path, source)
        if not validation["ok"]:
            raise ScenarioFormatError(f"Post-write validation failed: {validation['checks']}")
        os.replace(temporary_path, destination)
        temporary_path = None
    except Exception:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        if backup and backup.exists() and not destination.exists():
            backup.replace(destination)
        raise

    report: dict[str, Any] = {
        "application": "AoE2 Scenario Migrator",
        "application_version": APP_VERSION,
        "input": str(source_path),
        "output": str(destination),
        "output_sha256": _sha256(destination),
        "backup": str(backup) if backup else None,
        "target_version": latest_target_version(),
        "source": source.summary(),
        "validation": validation,
    }
    if options.json_report:
        json_path = destination.parent / f"{destination.stem}.conversion.json"
        write_json_report(json_path, report)
        report["json_report"] = str(json_path)
    if options.html_report:
        html_path = destination.parent / f"{destination.stem}.conversion.html"
        write_html_report(html_path, report)
        report["html_report"] = str(html_path)
    _notify(progress, f"Done: {destination.name}")
    return report
