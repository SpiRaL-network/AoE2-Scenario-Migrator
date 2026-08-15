from __future__ import annotations

import pytest
from legacy_fixture import build_legacy_fixture

from aoe2_scenario_migrator.legacy import read_legacy_scenario
from aoe2_scenario_migrator.models import (
    LegacyCondition,
    LegacyEffect,
    LegacyTrigger,
    LegacyUnit,
    ScenarioFormatError,
)
from aoe2_scenario_migrator.repairs import apply_safe_repairs


def _scenario(tmp_path, code: int = 122):
    return read_legacy_scenario(build_legacy_fixture(tmp_path / "fixture.scx", code))


def test_classic_terrain_upgrade_is_reported_without_changing_team_policy(tmp_path):
    scenario = _scenario(tmp_path)
    scenario.allow_players_choose_teams = 0

    apply_safe_repairs(scenario)

    finding = next(
        item for item in scenario.findings if item.rule_id == "UPGRADE.CLASSIC_TERRAIN_41"
    )
    assert finding.original == 41
    assert finding.repaired == 47
    assert finding.applied is True
    assert scenario.allow_players_choose_teams == 0


def test_trigger_orders_are_rebuilt_deterministically(tmp_path):
    scenario = _scenario(tmp_path)
    scenario.triggers = [
        LegacyTrigger(
            name="broken order",
            description="",
            enabled=1,
            looping=0,
            objective=0,
            objective_order=0,
            objective_string_id=-1,
            effects=[LegacyEffect(0, []), LegacyEffect(0, [])],
            effect_order=[0, 0],
            conditions=[LegacyCondition(0, []), LegacyCondition(0, [])],
            condition_order=[1, 1],
        )
    ]
    scenario.trigger_order = [4]

    apply_safe_repairs(scenario)

    assert scenario.trigger_order == [0]
    assert scenario.triggers[0].effect_order == [0, 1]
    assert scenario.triggers[0].condition_order == [0, 1]


def test_unnamed_triggers_are_named_in_display_order(tmp_path):
    scenario = _scenario(tmp_path)
    scenario.triggers = [
        LegacyTrigger("", "", 1, 0, 0, 0, -1, [], [], [], []),
        LegacyTrigger("Already named", "", 1, 0, 0, 0, -1, [], [], [], []),
        LegacyTrigger("   ", "", 1, 0, 0, 0, -1, [], [], [], []),
    ]
    scenario.trigger_order = [2, 1, 0]

    apply_safe_repairs(scenario)

    assert scenario.triggers[2].name == "Trigger 1"
    assert scenario.triggers[1].name == "Already named"
    assert scenario.triggers[0].name == "Trigger 2"
    finding = next(
        item for item in scenario.findings if item.rule_id == "UPGRADE.UNNAMED_TRIGGER_NAMES"
    )
    assert finding.applied is True
    assert finding.original == {"unnamed_triggers": 2}


def test_generated_trigger_names_do_not_duplicate_existing_names(tmp_path):
    scenario = _scenario(tmp_path)
    scenario.triggers = [
        LegacyTrigger("Trigger 1", "", 1, 0, 0, 0, -1, [], [], [], []),
        LegacyTrigger("", "", 1, 0, 0, 0, -1, [], [], [], []),
    ]
    scenario.trigger_order = [0, 1]

    apply_safe_repairs(scenario)

    assert scenario.triggers[1].name == "Trigger 2"


def test_missing_garrison_host_is_safely_removed(tmp_path):
    scenario = _scenario(tmp_path)
    scenario.units = [LegacyUnit(0, 1, 1, 0, 10, 83, 2, 0, 0, 999)]

    apply_safe_repairs(scenario)

    assert scenario.units[0].garrisoned_in_id == -1
    assert any(item.rule_id == "REPAIR.MISSING_GARRISON_HOST" for item in scenario.findings)


def test_duplicate_unit_ids_require_explicit_aggressive_mode(tmp_path):
    scenario = _scenario(tmp_path)
    scenario.next_uid = 100
    scenario.units = [
        LegacyUnit(0, 1, 1, 0, 10, 83, 2, 0, 0, -1),
        LegacyUnit(0, 2, 2, 0, 10, 83, 2, 0, 0, -1),
    ]

    with pytest.raises(ScenarioFormatError, match="--aggressive-repair"):
        apply_safe_repairs(scenario)

    apply_safe_repairs(scenario, aggressive=True)
    assert [unit.reference_id for unit in scenario.units] == [10, 100]
