# `tests/` — Test Suite Overview

This directory contains the project’s automated tests (pytest). It includes unit tests for core modules and dedicated per-metric tests.

## How to run
```bash
./run test         # helper script
# or
pytest -q          # quiet mode
coverage run -m pytest && coverage report
```

## Layout
- **test_basic.py** — smoke tests and sanity checks.
- **test_main.py** — CLI entry behavior, argument parsing, exit codes.
- **test_model.py** — `Model` composition, NetScore aggregation, metric orchestration.
- **test_model_catalogue.py** — batch processing of input lines, NDJSON formatting.
- **test_url_utils.py** — URL classification/grouping behavior.
- **metric_tests/** — per-metric tests (see its README).

## Conventions
- Use **pytest** style tests and **fixtures** for shared objects.
- Prefer deterministic, **offline** fixtures over live network calls.
- Assert both **value** and **type/range** (e.g., 0 ≤ score ≤ 1).
- Include **edge cases**: missing URLs, private repos, empty README, etc.

## Fixtures & Fakes
- Provide representative metadata dicts (GitHub repo info, HF model card text).
- Simulate rate limits/network errors for resilience tests.
- Keep fixtures small and focused; add docstrings explaining assumptions.

## Adding tests
1. Create `test_<module>.py` or extend an existing file.
2. Import the target module and craft small, focused tests.
3. For new metrics, add tests in `metric_tests/` (see below).
4. Run `pytest -q` and ensure coverage not regressing.


