from __future__ import annotations

import pytest
from legacy_fixture import build_legacy_fixture

from aoe2_scenario_migrator.service import ConversionOptions, convert_file


@pytest.mark.parametrize("code", [118, 122, 123, 124, 126])
def test_profile_converts_and_reopens_as_latest_de(tmp_path, code):
    source = build_legacy_fixture(tmp_path / f"legacy_{code}.scx", code)
    output = tmp_path / "converted"
    report = convert_file(
        source,
        ConversionOptions(output_dir=output, json_report=False, html_report=False),
    )
    assert report["validation"]["ok"] is True
    assert report["validation"]["checks"]["terrain"] is True
    assert report["validation"]["actual"]["scenario_version"] == report["target_version"]


def test_mislabeled_hd_scenario_with_de_extension_converts(tmp_path):
    source = build_legacy_fixture(tmp_path / "legacy.aoe2scenario", 126)
    report = convert_file(
        source,
        ConversionOptions(output_dir=tmp_path / "converted", json_report=False, html_report=False),
    )
    assert report["source"]["format"] == "AoE2 HD Patch 6"
    assert report["validation"]["ok"] is True
