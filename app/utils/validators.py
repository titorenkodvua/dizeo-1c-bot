from decimal import Decimal


def is_valid_rko_amount(amount: Decimal) -> bool:
    return amount > 0
