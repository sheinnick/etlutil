"""
ETL Utilities Package

A lightweight Python toolkit with reusable helpers and wrappers for everyday ETL tasks.
Built for clarity, speed, and reuse.
"""

from .data_structures import prune_data
from .date import format_year_month, generate_date_array

__version__ = "0.1.0"
__author__ = "Nikita Shein"
__email__ = "shein.nikita@gmail.com"

__all__ = [
    # Date helpers
    "generate_date_array",
    "format_year_month",
    # Container helpers
    "prune_data",
]
