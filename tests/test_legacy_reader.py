from __future__ import annotations

import pytest
from legacy_fixture import build_legacy_fixture

from aoe2_scenario_migrator.legacy import read_legacy_scenario


@pytest.mark.parametrize(
    ("code", "format_name"),
    [
        (118, "Age of Kings"),
        (121, "Age of Kings"),
        (122, "The Conquerors"),
        (123, "AoE2 HD"),
        (124, "AoE2 HD Patch 4"),
        (126, "AoE2 HD Patch 6"),
    ],
)
def test_all_supported_legacy_profiles(tmp_path, code, format_name):
    path = build_legacy_fixture(tmp_path / f"v{code}.scx", code)
    scenario = read_legacy_scenario(path)
    assert scenario.format_name == format_name
    assert scenario.map_width == 2
    assert scenario.map_height == 2
    assert scenario.terrain[-1] == (41, 0)
    assert scenario.trailing_bytes == 0


def test_invalid_disable_count_is_recorded_and_repaired(tmp_path):
    path = build_legacy_fixture(tmp_path / "broken.scx", 126, invalid_unit_count=True)
    scenario = read_legacy_scenario(path)
    finding = next(item for item in scenario.findings if item.rule_id == "REPAIR.DISABLED_COUNT_RANGE")
    assert finding.original == -1
    assert finding.repaired == 0
    assert finding.applied is True
    assert scenario.players[0].disabled_units == []
