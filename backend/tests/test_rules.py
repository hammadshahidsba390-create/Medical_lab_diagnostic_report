import pytest

from app.rules import flag_result, flag_value, parse_reference_range


@pytest.mark.parametrize("text,expected", [
    ("13.0 - 17.0", (13.0, 17.0)),
    ("13 to 17", (13.0, 17.0)),
    ("13\u201317", (13.0, 17.0)),
    ("< 200", (None, 200.0)),
    ("<= 5.7", (None, 5.7)),
    ("> 40", (40.0, None)),
    (">= 40", (40.0, None)),
    ("1,000 - 4,500", (1000.0, 4500.0)),
    ("", (None, None)),
    ("see comment", (None, None)),
    ("17 - 13", (None, None)),
])
def test_parse_reference_range(text, expected):
    assert parse_reference_range(text) == expected


def test_low_normal_high():
    assert flag_value(11.0, 13.0, 17.0) == "low"
    assert flag_value(15.0, 13.0, 17.0) == "normal"
    assert flag_value(18.2, 13.0, 17.0) == "high"


def test_boundaries_are_normal():
    assert flag_value(13.0, 13.0, 17.0) == "normal"
    assert flag_value(17.0, 13.0, 17.0) == "normal"


def test_one_sided_ranges():
    assert flag_result(250, "< 200") == "high"
    assert flag_result(150, "< 200") == "normal"
    assert flag_result(35, "> 40") == "low"
    assert flag_result(55, "> 40") == "normal"


def test_unknown_cases():
    assert flag_value("Negative", 1, 2) == "unknown"
    assert flag_value(None, 1, 2) == "unknown"
    assert flag_value(5, None, None) == "unknown"
    assert flag_result(5, "see comment") == "unknown"


def test_string_numbers_from_ocr():
    assert flag_result("14.2", "13.0 - 17.0") == "normal"
