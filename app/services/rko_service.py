import html
import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.constants import MSG_ONEC_UNEXPECTED, MSG_RKO_EMPTY, TELEGRAM_MAX_MESSAGE_LEN

logger = logging.getLogger(__name__)


def _group_thousands_int(n: int) -> str:
    s = str(abs(int(n)))
    parts: list[str] = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    return " ".join(reversed(parts)) if parts else "0"


def format_amount_pln(value: Any) -> str:
    """Польский вид денег: 1 234,56 zł. None / ошибка парсинга — «—» или исходная строка."""
    if value is None:
        return "—"
    raw = str(value).strip()
    if not raw:
        return "—"
    try:
        normalized = raw.replace(" ", "").replace(",", ".")
        d = Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return raw
    neg = d < 0
    d = abs(d)
    s = format(d, "f")
    if "." in s:
        whole_s, frac_s = s.split(".", 1)
        frac_s = (frac_s + "00")[:2]
    else:
        whole_s, frac_s = s, "00"
    body = f"{_group_thousands_int(int(whole_s))},{frac_s}"
    if neg:
        body = "-" + body
    return f"{body} zł"


def _str_field(value: Any, empty_as_dash: bool = True) -> str:
    if value is None:
        return "—" if empty_as_dash else ""
    s = str(value).strip()
    if not s and empty_as_dash:
        return "—"
    return s


def format_rko_item(item: dict[str, Any]) -> str:
    posted = item.get("posted")
    if posted is True:
        icon = "✅"
    elif posted is False:
        icon = "❌"
    else:
        icon = "❓"

    number = html.escape(_str_field(item.get("number"), empty_as_dash=True))
    date_s = html.escape(_str_field(item.get("date"), empty_as_dash=True))
    sum_plain = format_amount_pln(item.get("sum"))
    sum_html = html.escape(sum_plain)
    expense = html.escape(_str_field(item.get("expense_item"), empty_as_dash=True))
    cp = item.get("counterparty")
    cp_s = "" if cp is None else str(cp).strip()
    comment = item.get("comment")
    c_s = "—" if comment is None or str(comment).strip() == "" else str(comment).strip()
    c_html = html.escape(c_s)

    lines: list[str] = [
        f"{icon} {number} {date_s}",
        f"Сумма: <b>{sum_html}</b>",
        f"Статья: {expense}",
    ]
    if cp_s:
        lines.append(f"Контрагент: {html.escape(cp_s)}")
    lines.append(f"Комментарий: {c_html}")
    return "\n".join(lines)


def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    if not isinstance(items, list):
        logger.warning("1C list response: items is not a list")
        raise ValueError(MSG_ONEC_UNEXPECTED)
    out: list[dict[str, Any]] = []
    for raw in items:
        if isinstance(raw, dict):
            out.append(raw)
    return out


def _parse_rko_datetime(item: dict[str, Any]) -> datetime:
    """Парсинг даты 1С (например 29.03.2026 0:19:42). Без даты — в конец списка."""
    raw = item.get("date")
    if raw is None:
        return datetime.max
    s = str(raw).strip()
    if not s or s == "—":
        return datetime.max
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    logger.warning("Could not parse RKO date field: %r", s[:80])
    return datetime.max


def _sort_key_rko_chronological(item: dict[str, Any]) -> tuple[datetime, str]:
    return (_parse_rko_datetime(item), str(item.get("number") or ""))


def format_rko_list_messages(payload: dict[str, Any]) -> list[str]:
    items = extract_items(payload)
    if not items:
        return [MSG_RKO_EMPTY]
    items = sorted(items, key=_sort_key_rko_chronological)
    blocks = [format_rko_item(it) for it in items]
    return pack_blocks_into_telegram_messages(blocks)


def pack_blocks_into_telegram_messages(blocks: list[str]) -> list[str]:
    if not blocks:
        return [MSG_RKO_EMPTY]
    messages: list[str] = []
    buf: list[str] = []
    current_len = 0
    sep_len = 2

    for block in blocks:
        if not buf:
            buf.append(block)
            current_len = len(block)
            continue
        extra = sep_len + len(block)
        if current_len + extra > TELEGRAM_MAX_MESSAGE_LEN:
            messages.append("\n\n".join(buf))
            buf = [block]
            current_len = len(block)
        else:
            buf.append(block)
            current_len += extra

    if buf:
        messages.append("\n\n".join(buf))
    return messages


def format_confirmation_question(amount: Decimal, comment: str) -> str:
    return (
        f'Создать расход на {format_amount_pln(amount)} с комментарием "{comment}"?'
    )
