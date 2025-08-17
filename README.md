# ETL Utilities

A lightweight Python toolkit with reusable helpers and wrappers for everyday ETL tasks. Built for clarity, speed, and reuse.

## Features

- **Date Processing**:
  - Generate date arrays similar to BigQuery's `GENERATE_DATE_ARRAY`
  - Format dates to year-month strings (`YYYY-MM` format)
- **Data Cleaning**:
  - Recursive pruning for common containers (dict/list/tuple/set/frozenset) via `prune_data`
- **Data Structure Visualization**:
  - Tree-style visualization and data collection via `walk`

## Installation

### Basic Installation (from GitHub)

```bash
pip install "etlutil @ git+https://github.com/sheinnick/etlutil.git"
```

### With Development Dependencies (from GitHub)

```bash
pip install "etlutil[dev] @ git+https://github.com/sheinnick/etlutil.git"
```

### Using uv (Recommended)

```bash
uv add git+https://github.com/sheinnick/etlutil.git
```

## Quick Start

### Data Cleaning (prune_data)

```python
from etlutil import prune_data

data = {
    "import_top": 1,
    "keep": "hello test@test.test. how are you?",
    "nested": {"secret": 1, "x": []},
    "arr": [{"secret": 2}, {"field": "timespent"}],
}

# 1) Remove keys recursively
clean = prune_data(data, keys_to_remove=["secret"])  # keys: list or predicate (lambda key: ...)

# 2) Remove by value predicate (e.g., keep only strings with emails)
import re
pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
keep_emails = lambda v: not (isinstance(v, str) and pattern.search(v))
only_emails = prune_data(data, keys_to_remove=None, values_to_remove=keep_emails, remove_empty=True)

# 3) Remove keys by prefix (safe for non-string keys)
only_non_import = prune_data(data, keys_to_remove=lambda k: isinstance(k, str) and k.startswith("import_"))

# 4) Depth control: counts all container levels (dict/list/tuple/set)
limited = prune_data(data, keys_to_remove=["secret"], max_depth=1)
```

Key points:

- `keys_to_remove`: `Iterable[Hashable] | Callable[[Hashable], bool] | None`
- `values_to_remove`: `Iterable[Any] | Callable[[Any], bool] | None`
- `remove_empty=True` removes: `None`, empty string, empty containers; keeps `0` and `False`
- `max_depth=None` no limit; `0` top-level only; `>=1` counts all container levels
- Root container type is preserved (dict/list/tuple/set/frozenset)

### Data Structure Visualization (walk)

```python
from etlutil import walk

# Complex nested data
data = {
    "users": [
        {"id": 1, "name": "Alice", "tags": {"admin", "active"}},
        {"id": 2, "name": "Bob", "tags": {"user", "inactive"}}
    ],
    "settings": {"theme": "dark", "debug": True}
}

# 1) Print tree structure and return collected data
result = walk(data, show_types=True, show_lengths=True)
# Output:
# [dict len=2]
# ├─ settings [dict len=2]
# │  ├─ debug: True (bool)
# │  └─ theme: dark (str)
# └─ users [list len=2]
#    ├─ [0] [dict len=3]
#    │  ├─ id: 1 (int)
#    │  ├─ name: Alice (str)
#    │  └─ tags [set size=2]
#    │     ├─ [0]: active (str)
#    │     └─ [1]: admin (str)
#    └─ [1] [dict len=3]
#       ├─ id: 2 (int)
#       ├─ name: Bob (str)
#       └─ tags [set size=2]
#          ├─ [0]: inactive (str)
#          └─ [1]: user (str)

# 2) Collect data without printing
collected = walk(data, print_output=False, max_depth=2)
# Returns: processed data with depth limit applied

# 3) Limit items per container (affects sequences/sets only)
limited = walk(data, max_items_per_container=1, show_lengths=True)

# 4) Control depth and collect processed structure
processed = walk(data, max_depth=1, max_items_per_container=2)
# Returns: {'users': [], 'settings': {}} - empty containers at depth limit
```

Key points:

- **Always returns processed data** with applied limits (`max_depth`, `max_items_per_container`)
- **Optional printing** via `print_output=True` (default) - set to `False` for silent collection
- **Depth consistency**: collection behavior mirrors printing - containers become empty at depth limit
- **Container-specific limits**: `max_items_per_container` affects sequences/sets, not mappings
- **Tree visualization** with ASCII art connectors and type annotations
- **Flexible output**: custom writer functions, sorting, truncation options

### Date Array Generation

```python
from etlutil import generate_date_array
from datetime import date

# Basic usage - daily intervals
dates = generate_date_array("2024-01-01", "2024-01-05")
# Result: [2024-01-01, 2024-01-02, 2024-01-03, 2024-01-04, 2024-01-05]

# Custom interval
dates = generate_date_array("2024-01-01", "2024-01-10", 2, "DAY")
# Result: [2024-01-01, 2024-01-03, 2024-01-05, 2024-01-07, 2024-01-09]

# Monthly intervals
dates = generate_date_array("2024-01-01", "2024-06-01", 1, "MONTH")
# Result: [2024-01-01, 2024-02-01, 2024-03-01, 2024-04-01, 2024-05-01, 2024-06-01]

# Negative intervals (backward generation)
dates = generate_date_array("2024-01-05", "2024-01-01", -1, "DAY")
# Result: [2024-01-05, 2024-01-04, 2024-01-03, 2024-01-02, 2024-01-01]

# Negative monthly intervals
dates = generate_date_array("2024-06-01", "2024-01-01", -1, "MONTH")
# Result: [2024-06-01, 2024-05-01, 2024-04-01, 2024-03-01, 2024-02-01, 2024-01-01]
```

### Date Formatting

```python
from etlutil import format_year_month
from datetime import date

# Format date to year-month string
year_month = format_year_month(date(2024, 3, 16))
# Result: "2024-03"

# Works with date strings too
year_month = format_year_month("2024-03-16")
# Result: "2024-03"

# Handles different months correctly
format_year_month(date(2024, 1, 15))   # "2024-01" (with leading zero)
format_year_month(date(2024, 12, 31))  # "2024-12"
```

## Supported Date Parts

- `"DAY"` - Daily intervals
- `"WEEK"` - Weekly intervals  
- `"MONTH"` - Monthly intervals
- `"QUARTER"` - Quarterly intervals
- `"YEAR"` - Yearly intervals

## Input Formats

Dates can be provided as:

- `date` objects: `date(2024, 1, 1)`
- ISO format strings: `"2024-01-01"`

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/sheinnick/etlutil.git
cd etlutil

# Install with uv
uv sync --extra dev
```

### Running Tests

```bash
# Install dev deps
uv sync --extra dev

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=etlutil

# Run a specific file / test
uv run pytest tests/test_data_structures.py::test_keep_only_int_keys -q

# Run tests by keyword
uv run pytest -k "email or import_prefix" -q

# Re-run only last failures
uv run pytest --last-failed -q

# Verbose output and shorter tracebacks
uv run pytest -vv --tb=short

# Coverage
uv run pytest --cov=etlutil --cov-report=term-missing

# Property-based tests (optional)
# If Hypothesis не установлен, файл пропускается автоматически.
uv run pytest tests/test_data_structures_property.py -q

```

### Code Quality

```bash
# Format and lint code
uv run ruff check --fix etlutil/ tests/
uv run ruff format etlutil/ tests/

# Or run both at once
uv run ruff check etlutil/ tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
