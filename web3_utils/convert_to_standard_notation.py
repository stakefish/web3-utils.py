from __future__ import annotations

from decimal import Decimal


def convert_to_standard_notation(val: int | float | Decimal) -> str:
    return "{:0.0f}".format(val)
