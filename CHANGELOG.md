# Changelog

All notable changes to AoE2 Scenario Migrator are documented here.

The project follows [Semantic Versioning](https://semver.org/). Dates use the `YYYY-MM-DD` format.

## [Unreleased]

No unreleased changes.

## [0.1.0] - 2026-08-15

### Added

- Native Windows GUI with individual-file and recursive-folder selection, batch status and output-folder access.
- Command-line `inspect` and `convert` workflows for automation and diagnostics.
- Readers for Age of Kings 1.18–1.21, The Conquerors 1.22 and HD 1.23/1.24/1.26.
- Content-based recognition of HD `.scx`, `.scx2` and `.aoe2scenario` files.
- Dynamic output to the newest DE scenario revision supported by the installed conversion engine.
- JSON and HTML reports containing SHA-256 provenance, detected format, repairs and validation results.
- Trigger, effect and condition totals in the GUI completion status and HTML scenario summary.
- Portable Windows x64 build that includes the project license and third-party notices.
- Public CI, issue template, contribution guide and security policy.

### Preserved

- Map terrain and elevation, player configuration, diplomacy, resources and disabled content.
- Units, owners, positions, rotation, animation state, garrison links and reference IDs.
- Classic triggers, conditions, effects, selected objects and order tables.
- Scenario messages, cinematics, embedded AI text and supported included files.

### Repaired

- Negative or oversized fixed-array counts for disabled technologies, units and buildings.
- Invalid trigger, effect and condition order tables.
- Missing trigger names, assigned as `Trigger 1`, `Trigger 2`, and so on in top-to-bottom display order without changing existing names.
- Obsolete pre-HD4 condition inversion sentinel values.
- Classic terrain ID 41 compatibility.
- Missing garrison-host references.
- Duplicate unit reference IDs through an explicit aggressive repair option.

### Safety and validation

- Source files are read-only and never modified.
- Outputs are written atomically through a temporary file.
- Optional overwrite creates a recoverable `.bak` backup.
- Every result is reopened and compared for map, terrain, units, trigger structure and messages before it is accepted.
- Unsupported or ambiguous structural damage is rejected instead of silently guessed.

### Validation coverage

- Synthetic fixtures cover every supported legacy format family.
- Four large community HD scenarios confirmed the recurring negative disabled-content count defect and passed full post-conversion validation.
- The test suite contains 20 automated regression tests in this release.

[Unreleased]: https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SpiRaL-network/AoE2-Scenario-Migrator/releases/tag/v0.1.0
