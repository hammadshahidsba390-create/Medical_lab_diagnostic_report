"""Map the test names printed on a report to canonical biomarkers.

Strategy: exact alias lookup first (fast, no false positives), then fuzzy matching
with a conservative cut-off. A wrong match is worse than no match, so below the
cut-off the row is returned as unmatched and the user corrects it on screen.
"""
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

DATA_FILE = Path(__file__).parent / "data" / "biomarkers.json"
FUZZY_CUTOFF = 88.0
MIN_FUZZY_ALIAS_LEN = 5


@dataclass(frozen=True)
class Match:
    biomarker_id: str | None
    biomarker_name: str | None
    score: float


def clean(text: str) -> str:
    """Lowercase, drop punctuation and collapse spaces: 'Haemoglobin (Hb)' -> 'haemoglobin hb'."""
    text = re.sub(r"[^a-z0-9+ ]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def load_biomarkers() -> dict:
    with DATA_FILE.open(encoding="utf-8") as f:
        return {b["id"]: b for b in json.load(f)["biomarkers"]}


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for b in load_biomarkers().values():
        for name in [b["name"], *b["aliases"]]:
            index[clean(name)] = b["id"]
    return index


def match_biomarker(raw_name: str) -> Match:
    key = clean(raw_name)
    index = _alias_index()
    if key in index:
        b = load_biomarkers()[index[key]]
        return Match(b["id"], b["name"], 100.0)

    # Very short keys (e.g. 'k', 'na') must match exactly; fuzzy matching them is unsafe.
    if len(key) < 4:
        return Match(None, None, 0.0)

    # Only long aliases are fuzzy candidates, and whole-string similarity (not partial) is used:
    # partial matching made "Patient Name" match the alias "na" (sodium) at 90%.
    candidates = [a for a in index if len(a) >= MIN_FUZZY_ALIAS_LEN]
    best = process.extractOne(key, candidates, scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
    if best is None:
        return Match(None, None, 0.0)
    alias, score, _ = best
    b = load_biomarkers()[index[alias]]
    return Match(b["id"], b["name"], round(float(score), 1))
