"""Rule engine: decides whether a lab value is low, normal or high.

Design rule: this is plain Python logic. The AI model never decides whether a
value is abnormal. It only explains results that this module has already flagged.
"""
import re

Range = tuple[float | None, float | None]

_NUM = r"(\d+(?:\.\d+)?)"
_SEP = r"\s*(?:-|\u2013|\u2014|to)\s*"


def parse_reference_range(text: str) -> Range:
    """Turn a printed reference range into (low, high). None means no bound.

    Supported: "13.0 - 17.0", "13 to 17", "< 200", "<= 200", "> 40", ">= 40".
    Returns (None, None) when the text cannot be understood.
    """
    if not text:
        return (None, None)
    t = text.strip().replace(",", "")

    m = re.fullmatch(_NUM + _SEP + _NUM, t)
    if m:
        low, high = float(m.group(1)), float(m.group(2))
        return (low, high) if low <= high else (None, None)

    m = re.fullmatch(r"(<=?|\u2264)\s*" + _NUM, t)
    if m:
        return (None, float(m.group(2)))

    m = re.fullmatch(r"(>=?|\u2265)\s*" + _NUM, t)
    if m:
        return (float(m.group(2)), None)

    return (None, None)


def flag_value(value, low: float | None, high: float | None) -> str:
    """Return 'low', 'normal', 'high' or 'unknown'. Boundary values are normal."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if low is None and high is None:
        return "unknown"
    if low is not None and v < low:
        return "low"
    if high is not None and v > high:
        return "high"
    return "normal"


def flag_result(value, range_text: str) -> str:
    """Convenience: parse the printed range, then flag the value."""
    low, high = parse_reference_range(range_text)
    return flag_value(value, low, high)
