# Portfolio 4: actual NoSQL results

Run: `20261003T223205428931Z`

TinyDB 4.9.0; 516 persisted item/month documents; 3528 reconciled observations.

| Query | Matching documents | Independent SQL check |
|---|---:|---|
| D01_December_focus | 1 | PASS |
| D02_December_with_national | 42 | PASS |
| D03_without_national | 12 | PASS |
| D04_without_zones | 12 | PASS |
| D05_national_at_least_100000_kobo | 453 | PASS |
| D06_focus_all_months | 12 | PASS |

All original source fields, including provenance, matched after closing and reopening storage.
Fictional review insert/read/update/delete and persistence checks passed; snapshot documents were unchanged.
The original SQLite file hash is unchanged. Full checksums and reference SQL are in the JSON evidence.
