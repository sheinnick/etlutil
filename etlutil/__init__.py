"""
ETL Utilities Package

A lightweight Python toolkit with reusable helpers and wrappers for everyday ETL tasks.
Built for clarity, speed, and reuse.
"""

from .data_structures import convert_dict_types, move_unknown_keys_to_extra, prune_data, walk
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
    "convert_dict_types",
    "move_unknown_keys_to_extra",
    "prune_data",
    "walk",
]
