# ETL Utilities

A lightweight Python toolkit with reusable helpers and wrappers for everyday ETL tasks. Built for clarity, speed, and reuse.

## Features

- **Date Processing**: 
    - Generate date arrays similar to BigQuery's `GENERATE_DATE_ARRAY`
    - Format dates to year-month strings (`YYYY-MM` format)


## Installation

### Basic Installation
```bash
pip install etlutil
```

### With Development Dependencies
```bash
pip install etlutil[dev]
```

### Using uv (Recommended)
```bash
uv add etlutil
```

## Quick Start

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
uv sync

# Install in development mode
uv pip install -e .
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=etlutil

# Run specific test file
uv run pytest tests/test_date.py
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