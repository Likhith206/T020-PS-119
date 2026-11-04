"""
TENDERLENS — Money Utilities
Strictly adheres to Python Decimal arithmetic for public procurement monetary calculations.
No floating-point arithmetic is permitted for prices, percentages, or penalties.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Any

# Standard 2 decimal places quantizer for currency
CURRENCY_QUANTIZE = Decimal("0.01")
PERCENT_QUANTIZE = Decimal("0.01")
SCORE_QUANTIZE = Decimal("0.01")


def to_decimal(value: Any, default: str = "0.00") -> Decimal:
    """Safely converts an int, float, string, or Decimal to Decimal with high precision."""
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        # String conversion avoids binary floating point representation issues
        val_str = str(value).strip().replace(",", "")
        return Decimal(val_str)
    except (InvalidOperation, ValueError, TypeError) as err:
        raise ValueError(f"Cannot convert '{value}' to Decimal: {err}") from err


def quantize_money(amount: Union[Decimal, str, int]) -> Decimal:
    """Quantize to 2 decimal places using standard ROUND_HALF_UP."""
    dec = to_decimal(amount)
    return dec.quantize(CURRENCY_QUANTIZE, rounding=ROUND_HALF_UP)


def quantize_percent(pct: Union[Decimal, str, int]) -> Decimal:
    """Quantize percentage to 2 decimal places."""
    dec = to_decimal(pct)
    return dec.quantize(PERCENT_QUANTIZE, rounding=ROUND_HALF_UP)


def format_inr(amount: Union[Decimal, str, int]) -> str:
    """
    Format a Decimal as Indian Rupee string (e.g. ₹5,00,00,000.00).
    Follows Indian numbering system: lakhs and crores.
    """
    dec = quantize_money(amount)
    sign = "-" if dec < Decimal("0.00") else ""
    abs_dec = abs(dec)
    s = f"{abs_dec:.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group in 2s
        groups = []
        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        formatted_int = ",".join(groups) + "," + last3

    return f"{sign}₹{formatted_int}.{decimal_part}"


def calc_percentage(base_amount: Union[Decimal, str], percentage: Union[Decimal, str]) -> Decimal:
    """Calculate percentage amount: (base * pct) / 100."""
    base = to_decimal(base_amount)
    pct = to_decimal(percentage)
    return quantize_money((base * pct) / Decimal("100.00"))


def calc_percent_difference(original: Union[Decimal, str], comparison: Union[Decimal, str]) -> Decimal:
    """
    Calculate percent difference relative to original:
    ((comparison - original) / original) * 100
    """
    orig = to_decimal(original)
    comp = to_decimal(comparison)
    if orig == Decimal("0.00"):
        return Decimal("0.00")
    diff = ((comp - orig) / orig) * Decimal("100.00")
    return quantize_percent(diff)
