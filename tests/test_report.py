from __future__ import annotations

from aoe2_scenario_migrator.report import write_html_report


def test_html_report_displays_scenario_counts(tmp_path):
    path = tmp_path / "report.html"
    write_html_report(
        path,
        {
            "input": "source.scx",
            "output": "result.aoe2scenario",
            "target_version": "latest",
            "source": {
                "format": "AoE2 HD Patch 6",
                "inner_version": "1.26",
                "map": {"width": 220, "height": 220},
                "units": 1782,
                "triggers": 1407,
                "effects": 12779,
                "conditions": 2188,
                "findings": [],
            },
            "validation": {"ok": True},
        },
    )

    document = path.read_text(encoding="utf-8")
    assert "Scenario summary" in document
    assert "1,407" in document
    assert "12,779" in document
