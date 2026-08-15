# Contributing

Thanks for helping preserve classic Age of Empires II scenarios.

## Reporting a conversion problem

Open an issue and include:

- the source game and scenario format if known;
- the AoE2 Scenario Migrator version;
- the generated JSON conversion report;
- the exact error message or the observed in-game difference.

Only attach a scenario when you have permission to redistribute it. For private or copyrighted scenarios, first share the report and a minimal reproduction.

## Development

AoE2 Scenario Migrator requires Python 3.11 or newer on Windows.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\ruff check src tests
```

Keep repairs deterministic and auditable. Every new repair should have a stable rule ID, preserve the original value in the report, and include a regression test. Ambiguous repairs must remain opt-in.

Please open a focused pull request with a clear description and tests for behavioral changes.
