from __future__ import annotations

from decimal import Decimal, InvalidOperation


def split_amount_and_rest(line: str) -> tuple[str, str]:
    line = line.strip()
    if not line:
        return "", ""
    parts = line.split(maxsplit=1)
    first = parts[0]
    rest = parts[1].strip() if len(parts) > 1 else ""
    return first, rest


def parse_decimal_token(token: str) -> Decimal | None:
    normalized = token.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None
