from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json_report(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html_report(path: Path, report: dict[str, Any]) -> None:
    findings = report.get("source", {}).get("findings", [])
    rows = "".join(
        "<tr>"
        f"<td><code>{html.escape(str(item.get('rule_id', '')))}</code></td>"
        f"<td>{html.escape(str(item.get('severity', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        f"<td>{'yes' if item.get('applied') else 'no'}</td>"
        "</tr>"
        for item in findings
    ) or '<tr><td colspan="4">No findings</td></tr>'
    validation = report.get("validation", {})
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>AoE2 Scenario Migrator report</title>
<style>
body{{font:15px/1.45 system-ui,sans-serif;margin:2rem auto;max-width:1100px;padding:0 1rem;color:#18202a}}
h1{{color:#8a291b}} table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd3da;padding:.55rem;text-align:left;vertical-align:top}}
th{{background:#f1e5d4}}code{{background:#f3f4f6;padding:.12rem .3rem}}.ok{{color:#126b34;font-weight:700}}.bad{{color:#a11b1b;font-weight:700}}
</style></head><body>
<h1>AoE2 Scenario Migrator</h1>
<p class="{'ok' if validation.get('ok') else 'bad'}">Validation: {'PASSED' if validation.get('ok') else 'FAILED'}</p>
<p><b>Input:</b> {html.escape(str(report.get('input', '')))}<br>
<b>Output:</b> {html.escape(str(report.get('output', '')))}<br>
<b>Target:</b> AoE2 DE {html.escape(str(report.get('target_version', '')))}</p>
<h2>Findings and repairs</h2><table><thead><tr><th>Rule</th><th>Severity</th><th>Details</th><th>Applied</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Validation details</h2><pre>{html.escape(json.dumps(validation, ensure_ascii=False, indent=2))}</pre>
</body></html>"""
    path.write_text(document, encoding="utf-8")
