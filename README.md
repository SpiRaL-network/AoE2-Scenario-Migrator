# AoE2 Scenario Migrator

[![CI](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/actions/workflows/ci.yml/badge.svg)](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/SpiRaL-network/AoE2-Scenario-Migrator)](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AoE2 Scenario Migrator converts classic **Age of Kings**, **The Conquerors**, and **Age of Empires II HD Edition** scenarios to **Age of Empires II: Definitive Edition** on Windows.

It preserves scenario content, repairs known structural migration defects, writes to the newest DE scenario revision supported by the installed conversion engine, and validates the result before keeping it.

## Quick start

1. Download `AoE2ScenarioMigrator-vX.Y.Z-windows-x64.zip` from the [latest release](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/releases/latest).
2. Extract the complete ZIP. Do not move the executable away from its accompanying `_internal` folder.
3. Run `AoE2ScenarioMigrator.exe`.
4. Select **Add scenarios** or **Add folder**.
5. Optionally choose one output folder. Leaving it empty saves each result beside its source.
6. Keep the safe defaults, then select **Convert and validate**.
7. A scenario is ready only when its status becomes **Validated**. Use the HTML report for a readable summary and the JSON report for technical details.

The original file is never modified. The output name ends in `_DE_LATEST.aoe2scenario`.

## Supported scenarios

| Source game | Accepted extensions | Recognized inner formats | Output |
| --- | --- | --- | --- |
| Age of Empires II: The Age of Kings | `.scn`, `.scx` | 1.18, 1.19, 1.20, 1.21 | Latest supported DE format |
| Age of Empires II: The Conquerors | `.scx` | 1.22 | Latest supported DE format |
| Age of Empires II HD Edition | `.scx`, `.scx2`, `.aoe2scenario` | 1.23, 1.24, 1.26 | Latest supported DE format |

The latest HD format also uses the `.aoe2scenario` extension. Detection is based on file contents, not only the filename. A true DE `.aoe2scenario` is already converted and is intentionally rejected as an input.

Star Wars: Galactic Battlegrounds scenarios are not supported because they use a different data model.

## Preserved content

The converter carries the following legacy content into the DE scenario:

- map size, terrain IDs, elevation and tile layout;
- player names, civilizations, resources, diplomacy, team settings and disabled content lists;
- units, owners, coordinates, altitude, rotation, state, animation frame, garrisons and reference IDs;
- triggers, effects, conditions, selected objects and execution/display order;
- instructions, hints, history, scouts, victory/loss text and cinematics;
- embedded AI scripts and included files supported by the DE container.

## Structural repairs

Repairs are rule-based and recorded in both reports with the original value, repaired value, location and rule ID.

| Problem | Repair | Mode |
| --- | --- | --- |
| Negative or oversized disabled-technology, disabled-unit or disabled-building count | Clamp the count to the valid fixed-array range while preserving valid entries | Safe default |
| Invalid trigger display order | Rebuild the table in trigger ID order | Safe default |
| Invalid effect or condition order | Rebuild the affected order table | Safe default |
| Obsolete pre-HD4 condition inversion value | Normalize the legacy `-1` sentinel to the DE value | Safe default |
| Classic terrain ID 41 | Map it to the DE equivalent | Safe default |
| Unit references a missing garrison host | Preserve the unit and remove the invalid garrison link | Safe default |
| Duplicate unit reference IDs | Assign deterministic new IDs | **Aggressive repair**, opt-in |

Unsupported or ambiguous damage is rejected instead of guessed. Examples include unknown legacy trigger types, effects targeting a missing trigger, impossible record counts, truncated data and non-square maps.

## What it does not repair

The tool does not redesign gameplay. It cannot determine that a valid trigger has the wrong game logic, invent a missing trigger, move an incorrectly placed object, rebalance units, restore unavailable custom data mods or guarantee compatibility with every mod dependency.

Those problems require inspection by the scenario author in the DE editor.

## Validation and safety

Each conversion follows this sequence:

1. Read and diagnose the legacy binary without modifying it.
2. Apply deterministic structural repairs.
3. Build the DE scenario in a temporary file.
4. Reopen that file with the DE parser.
5. Compare map size, every terrain tile and elevation, units and their core properties, trigger/effect/condition counts and order, and scenario messages.
6. Move the file to its final name only when every validation check passes.

JSON and HTML reports include source/output SHA-256 hashes, detected source format, selected DE target revision, applied repairs and all validation results. Overwrite mode is opt-in and creates a `.bak` backup first.

## Command line

Install the project, then inspect a scenario without creating an output:

```powershell
aoe2sm inspect "legacy.scx"
```

Convert one or more files:

```powershell
aoe2sm convert "legacy.scx" -o ".\converted"
aoe2sm convert ".\one.scn" ".\two.scx" ".\three.scx2" -o ".\converted"
```

Use `--overwrite` for recoverable replacement with a `.bak` backup. Use `--aggressive-repair` only when duplicate unit reference IDs prevent safe conversion.

## Run from source

Python 3.11 or newer is required.

```powershell
git clone https://github.com/SpiRaL-network/AoE2-Scenario-Migrator.git
cd AoE2-Scenario-Migrator
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
.\.venv\Scripts\aoe2sm-gui.exe
```

## Build and test

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\ruff check src tests
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

The portable build is created at `dist\AoE2ScenarioMigrator\AoE2ScenarioMigrator.exe` and includes the project and third-party notices.

## Version history

See [CHANGELOG.md](CHANGELOG.md) for the complete release history and categorized changes.

## Credits

- [AoE2ScenarioParser](https://github.com/KSneijders/AoE2ScenarioParser) writes the DE scenario and performs the independent reopening/validation pass.
- [AOK Trigger Studio](https://github.com/mwhiter/aokts) served as a public reference for the legacy Genie scenario layout. No AOK Trigger Studio source code is included or linked into this project.
- [Python](https://www.python.org/), [Tcl/Tk](https://www.tcl-lang.org/) and [PyInstaller](https://pyinstaller.org/) provide the runtime, desktop interface and Windows packaging.

Their authors deserve credit for making community scenario tooling possible. See [NOTICE.md](NOTICE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for roles and license references.

## Contributing and security

Bug reports and contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting scenario files, and use the private process described in [SECURITY.md](SECURITY.md) for security issues.

This independent community project is not affiliated with or endorsed by Microsoft, Xbox Game Studios, Forgotten Empires or World's Edge.
