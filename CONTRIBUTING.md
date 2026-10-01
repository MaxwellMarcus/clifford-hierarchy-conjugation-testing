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
python -m ruff check src tests examples
python -m pytest
```

Release-facing changes should additionally run every script under `examples/`
and build and inspect both distributions as described in
[`docs/release-process.md`](docs/release-process.md). The checked release
workflow does not publish packages or hold publication credentials.

Please include a regression test for changes to mathematical logic. Numerical
experiments should state tolerances and should not be presented as exact proofs.
