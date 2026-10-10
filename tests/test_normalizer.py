import pytest

from app.normalizer import clean, load_biomarkers, match_biomarker


def test_clean():
    assert clean("Haemoglobin (Hb)") == "haemoglobin hb"
    assert clean("  LDL-C  ") == "ldl c"


@pytest.mark.parametrize("raw,expected", [
    ("Hb", "hemoglobin"),
    ("HGB", "hemoglobin"),
    ("Haemoglobin (Hb)", "hemoglobin"),
    ("SGPT", "alt"),
    ("SGOT", "ast"),
    ("TLC", "wbc"),
    ("FBS", "glucose_fasting"),
    ("LDL-C", "ldl"),
    ("Na+", "sodium"),
    ("K", "potassium"),
])
def test_exact_aliases(raw, expected):
    assert match_biomarker(raw).biomarker_id == expected


def test_fuzzy_typo_matches():
    m = match_biomarker("Hemoglobine")
    assert m.biomarker_id == "hemoglobin"
    assert 88 <= m.score < 100


@pytest.mark.parametrize("raw", ["Random Text", "Patient Name", "xyz", "Ca"])
def test_unknown_names_do_not_match(raw):
    assert match_biomarker(raw).biomarker_id is None


def test_every_alias_maps_back_to_its_biomarker():
    for b in load_biomarkers().values():
        for name in [b["name"], *b["aliases"]]:
            assert match_biomarker(name).biomarker_id == b["id"], name


def test_short_aliases_are_never_fuzzy_matched():
    """Regression: 'Patient Name' used to match the sodium alias 'na' via partial matching."""
    assert match_biomarker("Patient Name").biomarker_id is None
    assert match_biomarker("Sample No").biomarker_id is None
