# AoE2 Scenario Migrator

[![CI](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/actions/workflows/ci.yml/badge.svg)](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/SpiRaL-network/AoE2-Scenario-Migrator)](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AoE2 Scenario Migrator is a safe, all-in-one Windows tool for moving classic **Age of Kings**, **The Conquerors**, and **Age of Empires II HD** scenarios to **Age of Empires II: Definitive Edition**.

The application is not tied to a hard-coded DE version number. At conversion time it selects the newest DE scenario format supported by its installed conversion engine. Updating the engine lets future releases follow new DE scenario revisions without changing the legacy reader.

## Supported scenarios

| Source | Files | Recognized inner formats | Result |
| --- | --- | --- | --- |
| Age of Empires II: The Age of Kings | `.scn`, `.scx` | 1.18–1.21 | Current supported DE format |
| Age of Empires II: The Conquerors | `.scx` | 1.22 | Current supported DE format |
| Age of Empires II HD Edition | `.scx`, `.scx2` | 1.23, 1.24, 1.26 | Current supported DE format |

Real DE `.aoe2scenario` files are already converted and are intentionally left untouched. Some HD Workshop scenarios were published with an `.aoe2scenario` extension even though their contents are still HD data; the application detects those mislabeled files by content and can migrate them. Star Wars: Galactic Battlegrounds uses a different data model and is not supported.

## What it migrates

- AoK inner formats 1.18, 1.19, 1.20 and 1.21 (`.scn`/`.scx`)
- AoC inner format 1.22 (`.scx`)
- HD inner formats 1.23, 1.24 and 1.26 (`.scx`/`.scx2`)
- map terrain and elevation, player data, diplomacy, resources and disable lists
- units, ownership, rotation, animation state, garrisons and stable reference IDs
- classic triggers, conditions, effects, selected objects and display orders
- instructions, hints, history, scouts, victory/loss text and cinematics
- embedded AI text and included files supported by the DE container

## What it can repair

The repair engine fixes structural migration problems that can make an old scenario unreadable or cause DE to crash:

- invalid negative or oversized counts in the fixed legacy disabled-technology, disabled-unit and disabled-building arrays;
- invalid trigger display order, effect order and condition order tables;
- obsolete pre-HD4 condition inversion sentinel values;
- classic terrain ID 41 remapping required by DE;
- units pointing to a garrison host that no longer exists;
- duplicate unit reference IDs, only when the explicit aggressive repair option is enabled;
- legacy sentinel/default values that need a valid DE representation.

Unsafe or unknown damage is rejected instead of being guessed. This includes unsupported trigger types, missing trigger targets, impossible record counts, truncated files and non-square maps.

The tool does **not** redesign gameplay. It does not invent missing triggers, correct a trigger whose game logic is wrong, move misplaced map objects, rebalance units, or repair a scenario that depends on unavailable custom data mods. Those cases still need a scenario author.

## Safety model

The source is never edited. Conversion is written to a temporary file, reopened with the current DE parser, compared to the source model, and moved to its final name only after validation passes.

Every conversion produces optional JSON and HTML reports. Repairs have stable rule IDs, record the original and repaired values, and distinguish deterministic fixes from ambiguous damage. Overwriting is opt-in and first creates a `.bak` backup.

The converted scenario is checked for map size, every terrain tile and elevation, unit identity/ownership/position/garrison, trigger/effect/condition counts and ordering, messages, and successful reopening by the current DE parser. Reports include the chosen DE target revision so every result remains auditable.

## Windows GUI

Download the portable Windows package from the [latest release](https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/releases/latest), extract the ZIP, and run `AoE2ScenarioMigrator.exe`.

To run it from source instead:

```powershell
cd AoE2-Scenario-Migrator
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
.\.venv\Scripts\aoe2sm-gui.exe
```

Add individual scenarios or a complete folder, optionally select one common output directory, then choose **Convert and validate**.

## Command line

Inspect without producing a DE file:

```powershell
aoe2sm inspect "legacy.scx"
```

Convert one file:

```powershell
aoe2sm convert "legacy.scx" -o ".\converted"
```

Batch conversion:

```powershell
aoe2sm convert ".\one.scn" ".\two.scx" ".\three.scx2" -o ".\converted"
```

Use `--overwrite` for a recoverable replacement with `.bak`, or `--aggressive-repair` to remap duplicate unit reference IDs.

## Build the distributable `.exe`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

The result is `dist\AoE2ScenarioMigrator\AoE2ScenarioMigrator.exe`. The folder is portable and does not require Python on the destination computer.

## Development and tests

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\ruff check src tests
```

The binary reader is an original implementation based on the publicly documented Genie scenario layout. See `NOTICE.md` for credits.

Bug reports and contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Démarrage rapide en français

L’outil accepte les scénarios AoK, AoC et HD listés ci-dessus et les convertit vers le format DE le plus récent connu par le moteur installé. Il ne modifie jamais le scénario original. Ajoute les fichiers `.scn`, `.scx` ou `.scx2`, choisis éventuellement un dossier de sortie, puis clique sur **Convert and validate**. Le fichier DE, un rapport lisible en HTML et un rapport technique JSON sont créés uniquement si la relecture de contrôle réussit.

Il répare les corruptions de structure connues (comme les compteurs invalides qui faisaient planter notre scénario HD), les ordres de triggers invalides, certaines anciennes valeurs sentinelles, les références de garnison absentes et, sur demande, les identifiants d’unités dupliqués. Il conserve les objets, leurs positions et la logique des triggers. Un bug de conception du scénario doit donc toujours être corrigé dans l’éditeur.
