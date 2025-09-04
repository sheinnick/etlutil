# ETL Utilities

A lightweight Python toolkit with reusable helpers and wrappers for everyday ETL tasks. Built for clarity, speed, and reuse.

## Features

- **Date Processing**:
  - Generate date arrays similar to BigQuery's `GENERATE_DATE_ARRAY`
  - Format dates to year-month strings (`YYYY-MM` format)
  - Get relative date ranges (current/previous/next periods)
- **Data Cleaning**:
  - Recursive pruning for common containers (dict/list/tuple/set/frozenset) via `prune_data`
  - Dictionary normalization with whitelist filtering via `move_unknown_keys_to_extra`
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

### Dictionary Normalization (move_unknown_keys_to_extra)

```python
from etlutil import move_unknown_keys_to_extra

# Basic whitelist filtering
data = {"id": 123, "name": "alex", "age": 30, "city": "berlin"}
result, moved = move_unknown_keys_to_extra(data, ["id", "name"])
# Result: {'extra_collected': {'age': 30, 'city': 'berlin'}, 'id': 123, 'name': 'alex'}
# Moved: ['age', 'city']

# Custom extra key name
result, moved = move_unknown_keys_to_extra(data, ["id"], extra_key="metadata")
# Result: {'id': 123, 'metadata': {'age': 30, 'city': 'berlin', 'name': 'alex'}}

# API response cleanup - keep only business fields
api_data = {
    "id": 123,
    "name": "user",
    "email": "user@example.com", 
    "internal_id": "xyz",
    "debug_info": {"trace": "..."},
    "temp_session": "abc123"
}

business_fields = ["id", "name", "email"]
clean_data, internal_fields = move_unknown_keys_to_extra(api_data, business_fields)
# Result: clean API response with internal fields moved to 'extra_collected'

# Handle key collisions (different types, same string representation)
collision_data = {"1": "string_key", 1: "int_key"}
result, moved = move_unknown_keys_to_extra(collision_data, ["1"])
# Result: {'1': 'string_key', 'extra_collected': {'1__int': 'int_key'}}
# String keys get priority, non-string keys get type suffixes

# Discard extra items (don't collect them)
result, moved = move_unknown_keys_to_extra(data, ["id", "name"], extra_key=None)
# Result: {'id': 123, 'name': 'alex'} - age and city discarded

# Handle None inputs gracefully
result, moved = move_unknown_keys_to_extra(data, allowed_keys=None, extra_key=None)
# Result: {} - all keys discarded when no whitelist provided
```

Key points:

- **Whitelist-based filtering**: Only allowed keys remain at top level
- **Key collision resolution**: String keys get priority, others get type suffixes (`1__int`, `1__decimal`)
- **Extra key collision handling**: If `extra_key` exists in data, it gets renamed (`extra_collected_original`)
- **Flexible output**: Set `extra_key=None` to discard unknown keys instead of collecting
- **Lexicographic sorting**: All keys sorted consistently for deterministic output
- **Immutable operation**: Original data unchanged, returns new dictionary
- **Type conversion**: All keys converted to strings for consistent processing

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

### Relative Date Ranges

```python
from etlutil import get_relative_date_frame

# Current periods (n=0)
current_month = get_relative_date_frame("MONTH", 0)
# Result: ("2024-06-01", "2024-06-30") - current month boundaries

current_quarter = get_relative_date_frame("QUARTER", 0)
# Result: ("2024-04-01", "2024-06-30") - Q2 2024 if current date is in Q2

current_year = get_relative_date_frame("YEAR", 0)
# Result: ("2024-01-01", "2024-12-31") - current year

# Previous periods (n=-1)
last_month = get_relative_date_frame("MONTH", -1)
# Result: ("2024-05-01", "2024-05-31") - previous month

last_quarter = get_relative_date_frame("QUARTER", -1)
# Result: ("2024-01-01", "2024-03-31") - Q1 2024 if current is Q2

# Next periods (n=1)
next_week = get_relative_date_frame("WEEK", 1)
# Result: ("2024-06-17", "2024-06-23") - next week (Monday to Sunday)

next_year = get_relative_date_frame("YEAR", 1)
# Result: ("2025-01-01", "2025-12-31") - next year

# Multiple periods
six_months_ago = get_relative_date_frame("MONTH", -6)
# Result: ("2023-12-01", "2023-12-31") - 6 months ago

# Default parameters (MONTH, n=0)
this_month = get_relative_date_frame()
# Result: same as get_relative_date_frame("MONTH", 0)

# Use cases for ETL/Analytics
def get_data_for_period(period_type="MONTH", offset=-1):
    """Get data for relative time period."""
    start_date, end_date = get_relative_date_frame(period_type, offset)
    return f"SELECT * FROM events WHERE date BETWEEN '{start_date}' AND '{end_date}'"

# Examples:
get_data_for_period("MONTH", -1)    # Last month's data
get_data_for_period("QUARTER", 0)   # Current quarter's data
get_data_for_period("WEEK", -4)     # 4 weeks ago data
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

### Type Conversion

Convert dictionary values to proper Python types based on a schema. Essential for ETL workflows where data comes as strings from APIs, CSVs, or databases.

```python
from etlutil import convert_dict_types
from etlutil.data_structures import ConvertType

# Basic type conversion
data = {"count": "42", "price": "3.14", "active": "true", "created": "2024-12-25"}
schema = {
    "count": "int",
    "price": "float", 
    "active": "bool",
    "created": "date"
}

result = convert_dict_types(data, schema)
# Result: {"count": 42, "price": 3.14, "active": True, "created": date(2024, 12, 25)}

# Using enum types for better IDE support
schema = {
    "count": ConvertType.INT,
    "price": ConvertType.FLOAT,
    "active": ConvertType.BOOL,
    "created": ConvertType.DATE
}

# Unix timestamp conversion
data = {"created_at": "1735056631", "updated_at": 1735056631}
schema = {
    "created_at": "timestamp",        # → datetime object
    "updated_at": "timestamp_to_iso"  # → ISO string "2024-12-24T20:10:31"
}

# Recursive processing for nested data
nested_data = {
    "user_id": "123",
    "items": [
        {"price": "29.99", "quantity": "2"},
        {"price": "15.50", "quantity": "1"}
    ]
}

schema = {"user_id": "int", "price": "float", "quantity": "int"}
result = convert_dict_types(nested_data, schema, recursive=True)
# Converts values in nested dictionaries and lists

# Strict mode for validation
try:
    convert_dict_types({"invalid": "not_a_number"}, {"invalid": "int"}, strict=True)
except ValueError:
    print("Conversion failed - use for data validation")

# Custom datetime formats
data = {"event_time": "25/12/2024 15:30"}
schema = {"event_time": "datetime"}
custom_formats = ["%d/%m/%Y %H:%M"]

result = convert_dict_types(data, schema, datetime_formats=custom_formats)

# Empty string handling
data = {"value": "", "other": "42"}
schema = {"value": "int", "other": "int"}

# Convert empty strings to None
result = convert_dict_types(data, schema, empty_string_to_none=True)
# Result: {"value": None, "other": 42}
```

**Supported Types:**

- `"int"` - Integer conversion (handles floats, booleans, strings)
- `"float"` - Float conversion
- `"bool"` - Boolean conversion ("true", "1", "yes", "on" → True)
- `"str"` - String conversion
- `"date"` - Date objects from "YYYY-MM-DD" strings
- `"datetime"` - Datetime objects with configurable formats
- `"timestamp"` - Unix timestamp → datetime object
- `"timestamp_to_iso"` - Unix timestamp → ISO string

**Key Features:**

- **Recursive processing** - Handle nested dictionaries and lists
- **Strict mode** - Raise exceptions on conversion errors for validation
- **Flexible datetime parsing** - Custom format support
- **Empty string handling** - Convert to None when needed
- **Type safety** - Use ConvertType enum for better IDE support
- **Error tolerance** - Non-strict mode preserves original values on errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
