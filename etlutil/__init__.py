"""
ETL Utilities Package

A lightweight Python toolkit with reusable helpers and wrappers for everyday ETL tasks.
Built for clarity, speed, and reuse.
"""

from .data_structures import (
    clean_dict,
    convert_dict_types,
    convert_to_json_string,
    flatten_dict,
    move_unknown_keys_to_extra,
    normalize_date_fields,
    prune_data,
    walk,
)
from .date import (
    DateLike,
    DateRange,
    DateRanges,
    format_year_month,
    generate_date_array,
    get_relative_date_frame,
    to_date,
    to_date_iso_str,
)

__version__ = "0.1.0"
__author__ = "Nikita Shein"
__email__ = "shein.nikita@gmail.com"
__all__ = [
    # Date helpers
    "DateLike",
    "to_date",
    "to_date_iso_str",
    "DateRange",
    "DateRanges",
    "generate_date_array",
    "format_year_month",
    "get_relative_date_frame",
    # Container helpers
    "clean_dict",
    "convert_dict_types",
    "convert_to_json_string",
    "flatten_dict",
    "move_unknown_keys_to_extra",
    "normalize_date_fields",
    "prune_data",
    "walk",
]
