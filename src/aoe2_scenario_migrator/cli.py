from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import ScenarioFormatError
from .service import APP_VERSION, ConversionOptions, convert_file, inspect_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aoe2sm",
        description="Convert AoK, AoC and AoE2 HD scenarios to the newest supported AoE2 DE format.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_cmd = commands.add_parser("inspect", help="Read and diagnose a legacy scenario")
    inspect_cmd.add_argument("scenario", type=Path)
    inspect_cmd.add_argument("--aggressive-repair", action="store_true")
    convert_cmd = commands.add_parser("convert", help="Convert one or more scenarios")
    convert_cmd.add_argument("scenarios", type=Path, nargs="+")
    convert_cmd.add_argument("-o", "--output-dir", type=Path)
    convert_cmd.add_argument("--overwrite", action="store_true")
    convert_cmd.add_argument("--aggressive-repair", action="store_true")
    convert_cmd.add_argument("--no-json-report", action="store_true")
    convert_cmd.add_argument("--no-html-report", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            scenario = inspect_file(args.scenario, aggressive_repair=args.aggressive_repair)
            print(json.dumps(scenario.summary(), ensure_ascii=False, indent=2))
            return 0
        options = ConversionOptions(
            output_dir=args.output_dir,
            overwrite=args.overwrite,
            aggressive_repair=args.aggressive_repair,
            json_report=not args.no_json_report,
            html_report=not args.no_html_report,
        )
        reports = []
        for scenario in args.scenarios:
            reports.append(convert_file(scenario, options, progress=lambda text: print(text, file=sys.stderr)))
        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ScenarioFormatError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
