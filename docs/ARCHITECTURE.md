# Architecture & Design Decisions

Diagrams (Week 3): `docs/diagrams/Architecture_3Tier.png`, `DFD_Level0.png`, `DFD_Level1.png`.
Full architecture document: three-tier design, cloud topology and stack justification, data flows f1-f25.

## Pipeline
```
upload -> preprocess -> EXTRACT (OCR / vision LLM) -> normalize names -> user verifies
       -> RULE ENGINE flags low/normal/high -> LLM explains flagged rows only
       -> safety filter -> question checklist -> results / PDF
```
Implemented so far: normalizer, rule engine, `/api/v1/analyze`, synthetic data generator (see the diagrams for the full planned design).
Next: extraction (Gemini vision behind an interface), explainer, safety filter, frontend.

## Decisions (ADRs)
| # | Decision | Why |
|---|---|---|
| 1 | Flags are decided by code (`rules.py`), never by the LLM | Deterministic, testable, removes the biggest safety risk (an LLM mislabelling a value) |
| 2 | Use the reference range printed on the report; no built-in fallback ranges yet | Ranges differ by lab, age and sex. If unreadable the flag is `unknown` |
| 3 | Fuzzy matching only against aliases of 5+ characters, whole-string similarity | A test found partial matching mapped "Patient Name" to sodium ("na"). Wrong match is worse than no match |
| 4 | No real patient data anywhere in development or tests | Privacy and ethics. Synthetic reports are generated with ground truth |
| 5 | Synthetic generator (3 layouts + phone-photo degradation) | Free, reproducible test set; allows exact extraction-accuracy measurement |
| 6 | Extraction behind an interface (`Extractor`) | Swap Gemini vision / Google Vision / PaddleOCR without touching the rest |
| 7 | Disclaimer returned by the API on every analysis | Safety requirement, cannot be forgotten by a frontend |
| 8 | Three tiers: Next.js on Vercel, FastAPI on Render, Supabase for data | Free tiers, one managed service for database, auth and storage, deploys from GitHub |
| 9 | Ownership is checked in code on every report route; database row-level security is an extra layer | A forgotten check in one route must not expose another user's data |
| 10 | Image kept only until the user confirms the table, deleted within 1 hour of last activity | The verification screen needs the image; health data is kept minimal |
| 11 | Only the flagged value and biomarker text go to the AI for explanations | Minimal data to a third party |
| 12 | Authentication is implemented in the FastAPI app (bcrypt password hashes, signed JWT sessions); Supabase is the managed Postgres database and private storage | Matches the brief's authentication requirement literally and keeps Supabase as the named data service |
| 13 | Text-based PDFs are read locally with PyMuPDF; photos and scans use the Gemini API | Less data sent to a third party, and a free, deterministic path for the simplest input |

## Limitations (state these in the viva)
- Evaluated on synthetic and public sample reports only; no clinical validation.
- Synthetic layouts approximate, but do not cover, every real lab format.
- English reports only. MRI scan analysis is out of scope.
| 14 | Passwords hashed with bcrypt; sessions are signed JWTs valid for 60 minutes; the role is read from the database on each request | Matches the brief's authentication requirement; a role change applies at once |
| 15 | The login token is kept in sessionStorage in the browser | Simple and cleared with the tab; trade-off and mitigations are in docs/AUTH.md |
| 16 | Database changes only through Alembic migrations; configuration only through environment variables, and the app refuses to start without a strong JWT secret | Reproducible schema, no secrets in the repository |
