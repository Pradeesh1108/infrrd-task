"""Normalizes extracted field values into the exact format score.py expects.

Mirrors score.py's normalize() function so predictions are correctly
formatted before comparison — we don't rely on the scorer's own
normalization leniency (e.g. its date parser doesn't handle DD/MM/YYYY,
so we must emit ISO dates ourselves; see _normalize_date below).
"""
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from score import FIELD_TYPES  # noqa: E402


_CURRENCY_JUNK = re.compile(r"[$€£₹,\s]|(?i:rs\.?)|(?i:\b(usd|eur|gbp|inr)\b)")

# Month names across the five dataset languages, for parsing dates written
# out in words rather than numerals.
_MONTHS = {
    # English
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # German
    "januar": 1, "februar": 2, "märz": 3, "mai": 5, "juni": 6, "juli": 7,
    "oktober": 10, "dezember": 12,
    # French
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    # Spanish
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    # Dutch
    "januari": 1, "februari": 2, "maart": 3, "mei": 5, "juni": 6, "juli": 7,
    "augustus": 8, "oktober": 10, "december": 12,
}

_CURRENCY_LOCALE = {
    "USD": "month_first",
    "GBP": "day_first",
    "INR": "day_first",
    "EUR": "day_first",
}


def normalize_amount(value: str) -> str | None:
    """Strip currency symbols/junk, handle INR lakh grouping and EU decimal
    commas, return a 2-decimal string. Returns None if unparseable."""
    if value is None:
        return None
    raw = str(value).strip()

    # EU style: 1.234,56 or 1 234,56 -> decimal comma, dot/space as thousands
    if re.search(r",\d{2}$", raw) and ("." in raw or " " in raw):
        raw = raw.replace(".", "").replace(" ", "").replace(",", ".")
    else:
        # INR lakh grouping (1,23,456.00) and standard US grouping (1,234.00)
        # both just need commas stripped — Python float() handles the rest.
        raw = _CURRENCY_JUNK.sub("", raw)
        raw = raw.replace(",", "")

    raw = _CURRENCY_JUNK.sub("", raw).strip()
    try:
        return f"{float(raw):.2f}"
    except ValueError:
        return None


def _try_month_name_date(text: str) -> str | None:
    """Parse dates like '14 March 2026', 'March 14, 2026', '14. März 2026'."""
    match = re.search(
        r"(\d{1,2})\D{1,3}([A-Za-zÀ-ÿ]+)\D{1,3}(\d{4})", text
    )
    if match:
        day, month_word, year = match.groups()
        month = _MONTHS.get(month_word.lower())
        if month:
            try:
                return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
            except ValueError:
                pass

    match = re.search(
        r"([A-Za-zÀ-ÿ]+)\D{1,3}(\d{1,2})\D{1,3}(\d{4})", text
    )
    if match:
        month_word, day, year = match.groups()
        month = _MONTHS.get(month_word.lower())
        if month:
            try:
                return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def normalize_date(value: str, currency_hint: str | None = None) -> str | None:
    """Normalize a date to YYYY-MM-DD.

    currency_hint decides numeric DD/MM vs MM/DD ambiguity per README's
    locale rule: USD documents are month-first, GBP/INR/EUR are day-first.
    Returns None if unparseable.
    """
    if value is None:
        return None
    text = str(value).strip()

    # already ISO
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    # numeric with separators: DD/MM/YYYY, MM/DD/YYYY, DD.MM.YYYY, DD-MM-YYYY
    match = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", text)
    if match:
        a, b, year = (int(x) for x in match.groups())
        month_first = _CURRENCY_LOCALE.get(currency_hint, "day_first") == "month_first"
        try:
            if month_first:
                return datetime(year, a, b).strftime("%Y-%m-%d")
            return datetime(year, b, a).strftime("%Y-%m-%d")
        except ValueError:
            # fall through — try the other order in case locale guess was wrong
            try:
                if month_first:
                    return datetime(year, b, a).strftime("%Y-%m-%d")
                return datetime(year, a, b).strftime("%Y-%m-%d")
            except ValueError:
                return None

    # month name form, any of the five languages
    named = _try_month_name_date(text)
    if named:
        return named

    return None


def normalize_text(value: str) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).split())


def normalize_code_or_enum(value: str) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).split()).upper()


def normalize_field(field: str, value: str, currency_hint: str | None = None) -> str | None:
    """Dispatch to the right normalizer based on the field's type
    (from score.py's FIELD_TYPES). Returns None if value is None or
    unparseable — caller decides what None means for abstention."""
    if value is None:
        return None
    ftype = FIELD_TYPES[field]
    if ftype == "amount":
        return normalize_amount(value)
    if ftype == "date":
        return normalize_date(value, currency_hint=currency_hint)
    if ftype in ("code", "enum"):
        return normalize_code_or_enum(value)
    return normalize_text(value)


if __name__ == "__main__":
    # quick manual checks
    tests_amount = ["$1,840.00", "1.234,56", "1,23,456.00", "89879.66", "Rs. 5,000"]
    tests_date_usd = ["03/14/2026", "March 14, 2026", "2026-03-14"]
    tests_date_inr = ["14/03/2026", "14.03.2026", "14 March 2026"]

    print("-- amounts --")
    for t in tests_amount:
        print(f"{t!r:20} -> {normalize_amount(t)}")

    print("-- dates (USD, month-first) --")
    for t in tests_date_usd:
        print(f"{t!r:20} -> {normalize_date(t, currency_hint='USD')}")

    print("-- dates (INR, day-first) --")
    for t in tests_date_inr:
        print(f"{t!r:20} -> {normalize_date(t, currency_hint='INR')}")