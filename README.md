# DataGuard — Data Quality Platform

> A rule-based, production-quality Data Quality Platform for validating datasets with configurable rules.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Features

- ✅ **Completeness** — detect NULL, empty, and whitespace-only values
- ✅ **Uniqueness** — detect duplicate rows and composite key violations
- ✅ **Validity** — validate against regex patterns, enum sets, data types, and numeric ranges
- 📄 **JSON Reports** — timestamped, machine-readable output
- 🖥️ **Rich Terminal Output** — colour-coded tables with pass/fail indicators
- ⚙️ **YAML Rule Definitions** — human-readable, version-controlled rule files
- 🔌 **Hexagonal Architecture** — clean separation of domain, application, and infrastructure

---

## Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/dataguard.git
cd dataguard

# Install (runtime only)
pip install .

# Install with dev tools (for contributors)
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Validate a CSV file against a rule set
dataguard validate --source examples/sample_invalid.csv --rules rules/example_rules.yaml

# With verbose logging
dataguard validate -s data.csv -r rules.yaml --verbose

# Custom report directory
dataguard validate -s data.csv -r rules.yaml --report-dir ./my-reports

# Show version
dataguard --version
```

### Example Output

```
╭──────────────────── DataGuard Validation Report ────────────────────╮
│ Source:     sample_invalid.csv                                       │
│ Run at:     2024-01-15 14:32:01 UTC                                  │
│ Status:     FAILED                                                   │
╰──────────────────────────────────────────────────────────────────────╯

┌──────────────────────┬──────────┬────────────┬───────┬───────────┐
│ Rule                 │ Column   │ Status     │ Score │ Threshold │
├──────────────────────┼──────────┼────────────┼───────┼───────────┤
│ email_completeness   │ email    │ ✅ PASSED  │ 0.700 │ 0.900     │
│ id_uniqueness        │ id       │ ✅ PASSED  │ 1.000 │ 1.000     │
│ status_validity      │ status   │ ❌ FAILED  │ 0.800 │ 1.000     │
│ age_range            │ age      │ ❌ FAILED  │ 0.800 │ 1.000     │
└──────────────────────┴──────────┴────────────┴───────┴───────────┘

╭─────────────────── ❌ VALIDATION FAILED ──────────────────────────╮
│ Overall Score: 0.825                                                │
│ Rules: 2 passed  2 failed  0 skipped / 4 total                     │
╰─────────────────────────────────────────────────────────────────────╯

📄 Report saved: reports/report_20240115_143201.json
```

---

## Rule Definition (YAML)

```yaml
version: "1.0"
rules:
  - id: rule_001
    name: email_completeness
    type: completeness        # completeness | uniqueness | validity
    column: email
    threshold: 0.95           # minimum quality score (0.0 – 1.0)
    severity: error           # error | warning | info

  - id: rule_002
    name: user_id_unique
    type: uniqueness
    column: user_id
    threshold: 1.0
    severity: error

  - id: rule_003
    name: status_validity
    type: validity
    column: status
    validator: enum           # enum | regex | dtype | range
    params:
      allowed_values: [active, inactive, pending]
    threshold: 1.0
    severity: warning

  - id: rule_004
    name: age_range
    type: validity
    column: age
    validator: range
    params:
      min_value: 0
      max_value: 150
    threshold: 1.0
    severity: error
```

---

## Developer Commands

```bash
make install-dev   # install all dependencies
make test          # run tests with coverage
make lint          # check code style
make format        # auto-format code
make typecheck     # run mypy strict
make check         # lint + typecheck + test (full CI)
```

---

## Architecture

DataGuard uses **Hexagonal Architecture (Ports & Adapters)** with **Domain-Driven Design**:

```
Delivery (CLI)  →  Application (Use Cases)  →  Domain (Rules, Entities)
                                             ←  Infrastructure (Readers, Writers)
```

- **Domain**: Pure Python — zero external dependencies
- **Application**: Orchestrates domain via injected ports
- **Infrastructure**: pandas, PyYAML, rich — adapters for I/O
- **Delivery**: Typer CLI — wires everything together

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All rules passed |
| `1` | One or more error-severity rules failed |
| `2` | Execution error (file not found, parse error, etc.) |

---

## License

MIT — see [LICENSE](LICENSE).
