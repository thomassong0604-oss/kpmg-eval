# SEC reads behind the 10-company facts

| File | Source | Read |
|---|---|---|
| `read1_companyconcept.tsv` | data.sec.gov companyconcept API, window read | 2026-10-29 |
| `read2_targeted.tsv` | same API, filtered by end date (independent second read) | 2026-10-29 |
| `read1b_filing_statements.tsv` | Micron FY2026 10-K (0000723125-26-000023) R3.htm, statement of operations, read 1 | 2026-11-05 |
| `read2b_filing_statements.tsv` | same page, read 2 | 2026-11-05 |
| `filing_statements_2026-11-05.json` | income statements (R pages) of all ten latest 10-Ks: printed labels, scale, values | 2026-11-05 |
| `exhibit21_2026-11-05.json` | Exhibit 21 of the latest 10-K, short lists in full and targeted lookups, each read twice | 2026-11-05 |

Why the Micron filing is read from the filing and not the API: on 2026-11-05 the companyconcept API still returned no
facts from Micron's FY2026 10-K (filed 2026-10-09), and its latest `filed` date was 2026-06-25. That gap is why Eval said
on 10/29 that Micron's newest annual report was not in the corpus; it is, and Data's database holds it.
