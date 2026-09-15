# Contributing

Bug reports, mathematical corrections, and focused pull requests are welcome.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Before opening a pull request, run:

```bash
python -m ruff check src tests
python -m pytest
```

Please include a regression test for changes to mathematical logic. Numerical
experiments should state tolerances and should not be presented as exact proofs.
