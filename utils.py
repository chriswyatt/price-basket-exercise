from decimal import Decimal, ROUND_HALF_EVEN
from math import log10

_INT_ZERO = 0
_GBP_SMALLEST_DENOMINATION = Decimal("0.01")
_GBP_DECIMAL_PLACES = abs(int(log10(_GBP_SMALLEST_DENOMINATION)))

_format_base_10 = "{:d}".format


def format_currency_gbp(dec):
    """
    Convert Decimal object to a custom string representation. Examples:

    Decimal(1) => £1.00
    Decimal(1.2) => £1.20
    Decimal(1.23) => £1.23
    Decimal(1.234) => £1.23
    Decimal(1.235) => £1.24
    Decimal(0.2) => 20p
    Decimal(0.23) => 23p
    Decimal(0.234) => 23p
    Decimal(0.235) => 24p
    """

    quantized_dec = dec.quantize(
        _GBP_SMALLEST_DENOMINATION,
        rounding=ROUND_HALF_EVEN,
    )

    sign, digits, exponent = quantized_dec.as_tuple()
    sign_str = ("", "-")[sign]

    left_digits = digits[:exponent]
    right_digits = digits[exponent:]

    lt_1 = all(map(_INT_ZERO.__eq__, left_digits))

    currency_prefix_str = "" if lt_1 else "£"
    decimal_point_str = "" if lt_1 else "."
    currency_suffix_str = "p" if lt_1 else ""

    left_digits_str = "" if lt_1 else "".join(map(
        _format_base_10,
        left_digits,
    ))

    right_digits_str = (
        "".join(map(_format_base_10, right_digits)).ljust(
            _GBP_DECIMAL_PLACES,
            "0",
        ))

    return "".join((
        sign_str,
        currency_prefix_str,
        left_digits_str,
        decimal_point_str,
        right_digits_str,
        currency_suffix_str,
    ))
