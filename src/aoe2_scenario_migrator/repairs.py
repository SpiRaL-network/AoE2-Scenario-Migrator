from __future__ import annotations

from .models import Finding, LegacyScenario, ScenarioFormatError, Severity


def _valid_order(order: list[int], count: int) -> bool:
    return len(order) == count and sorted(order) == list(range(count))


def apply_safe_repairs(scenario: LegacyScenario, *, aggressive: bool = False) -> None:
    """Apply deterministic repairs and reject unsafe ambiguity.

    The legacy reader already normalizes fixed-array counts while retaining a finding.
    This pass repairs relationship-level problems after every structure is available.
    """
    if float(scenario.inner_version) <= 1.23:
        inverted_flags = 0
        for trigger in scenario.triggers:
            for condition in trigger.conditions:
                if len(condition.fields) > 16 and condition.fields[16] == -1:
                    condition.fields[16] = 0
                    inverted_flags += 1
        if inverted_flags:
            scenario.findings.append(
                Finding(
                    "UPGRADE.CONDITION_INVERTED_FLAG",
                    Severity.INFO,
                    f"Normalized {inverted_flags} pre-HD4 condition inversion flags from -1 to 0",
                    original=-1,
                    repaired=0,
                    applied=True,
                )
            )

    if float(scenario.inner_version) <= 1.22:
        terrain_41_count = sum(1 for terrain_id, _elevation in scenario.terrain if terrain_id == 41)
        if terrain_41_count:
            scenario.findings.append(
                Finding(
                    "UPGRADE.CLASSIC_TERRAIN_41",
                    Severity.INFO,
                    f"Mapped {terrain_41_count} classic terrain 41 tiles to the DE equivalent",
                    original=41,
                    repaired=47,
                    applied=True,
                )
            )

    if not _valid_order(scenario.trigger_order, len(scenario.triggers)):
        original = list(scenario.trigger_order)
        scenario.trigger_order = list(range(len(scenario.triggers)))
        scenario.findings.append(
            Finding(
                "REPAIR.TRIGGER_DISPLAY_ORDER",
                Severity.WARNING,
                "Invalid trigger display order was rebuilt in trigger-ID order",
                original=original,
                repaired=scenario.trigger_order,
                applied=True,
            )
        )

    reserved_names = {
        trigger.name.strip().casefold()
        for trigger in scenario.triggers
        if trigger.name.strip()
    }
    renamed_triggers: list[dict[str, int | str]] = []
    next_name_number = 1
    for display_position, trigger_index in enumerate(scenario.trigger_order, start=1):
        trigger = scenario.triggers[trigger_index]
        if trigger.name.strip():
            continue
        while f"trigger {next_name_number}" in reserved_names:
            next_name_number += 1
        generated_name = f"Trigger {next_name_number}"
        trigger.name = generated_name
        reserved_names.add(generated_name.casefold())
        renamed_triggers.append(
            {
                "trigger_id": trigger_index,
                "display_position": display_position,
                "name": generated_name,
            }
        )
        next_name_number += 1
    if renamed_triggers:
        scenario.findings.append(
            Finding(
                "UPGRADE.UNNAMED_TRIGGER_NAMES",
                Severity.INFO,
                f"Named {len(renamed_triggers)} unnamed triggers in display order",
                "trigger_display_order",
                {"unnamed_triggers": len(renamed_triggers)},
                {
                    "first": renamed_triggers[0],
                    "last": renamed_triggers[-1],
                },
                True,
            )
        )

    for trigger_index, trigger in enumerate(scenario.triggers):
        if not _valid_order(trigger.effect_order, len(trigger.effects)):
            original = list(trigger.effect_order)
            trigger.effect_order = list(range(len(trigger.effects)))
            scenario.findings.append(
                Finding(
                    "REPAIR.EFFECT_ORDER",
                    Severity.WARNING,
                    f"Trigger {trigger_index} effect order was rebuilt",
                    f"trigger:{trigger_index}",
                    original,
                    trigger.effect_order,
                    True,
                )
            )
        if not _valid_order(trigger.condition_order, len(trigger.conditions)):
            original = list(trigger.condition_order)
            trigger.condition_order = list(range(len(trigger.conditions)))
            scenario.findings.append(
                Finding(
                    "REPAIR.CONDITION_ORDER",
                    Severity.WARNING,
                    f"Trigger {trigger_index} condition order was rebuilt",
                    f"trigger:{trigger_index}",
                    original,
                    trigger.condition_order,
                    True,
                )
            )
        for effect_index, effect in enumerate(trigger.effects):
            if not 0 <= effect.effect_type <= 36:
                raise ScenarioFormatError(
                    f"Trigger {trigger_index} effect {effect_index} uses unsupported legacy type "
                    f"{effect.effect_type}"
                )
            if effect.effect_type in (8, 9) and len(effect.fields) > 13:
                target = effect.fields[13]
                if target != -1 and not 0 <= target < len(scenario.triggers):
                    raise ScenarioFormatError(
                        f"Trigger {trigger_index} effect {effect_index} references missing trigger {target}"
                    )
        for condition_index, condition in enumerate(trigger.conditions):
            if not 0 <= condition.condition_type <= 20:
                raise ScenarioFormatError(
                    f"Trigger {trigger_index} condition {condition_index} uses unsupported legacy type "
                    f"{condition.condition_type}"
                )

    used: set[int] = set()
    duplicates = []
    next_reference = max(
        scenario.next_uid,
        max((unit.reference_id for unit in scenario.units), default=-1) + 1,
    )
    for unit in scenario.units:
        if unit.reference_id not in used:
            used.add(unit.reference_id)
            continue
        if not aggressive:
            duplicates.append(unit.reference_id)
            continue
        old = unit.reference_id
        while next_reference in used:
            next_reference += 1
        unit.reference_id = next_reference
        used.add(next_reference)
        scenario.findings.append(
            Finding(
                "REPAIR.DUPLICATE_UNIT_REFERENCE",
                Severity.ERROR,
                "A duplicate unit reference ID was remapped in aggressive mode",
                f"decompressed:0x{unit.offset:X}",
                old,
                next_reference,
                True,
            )
        )
        next_reference += 1
    if duplicates:
        values = ", ".join(str(value) for value in sorted(set(duplicates)))
        raise ScenarioFormatError(
            f"Duplicate unit reference IDs require --aggressive-repair: {values}"
        )

    valid_ids = {unit.reference_id for unit in scenario.units}
    for unit in scenario.units:
        if unit.garrisoned_in_id in (-1, 0xFFFFFFFF):
            unit.garrisoned_in_id = -1
        elif unit.garrisoned_in_id not in valid_ids:
            original = unit.garrisoned_in_id
            unit.garrisoned_in_id = -1
            scenario.findings.append(
                Finding(
                    "REPAIR.MISSING_GARRISON_HOST",
                    Severity.WARNING,
                    f"Unit {unit.reference_id} referenced a missing garrison host",
                    f"unit:{unit.reference_id}",
                    original,
                    -1,
                    True,
                )
            )

    if scenario.map_width != scenario.map_height:
        raise ScenarioFormatError(
            f"Non-square legacy maps are not supported by AoE2 DE ({scenario.map_width}x{scenario.map_height})"
        )


def blocking_findings(scenario: LegacyScenario) -> list[Finding]:
    return [finding for finding in scenario.findings if finding.severity == Severity.ERROR and not finding.applied]
