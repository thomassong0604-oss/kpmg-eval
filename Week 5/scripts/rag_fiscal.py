"""RAG's fiscal-label rule, copied verbatim from rag/ingest.py @ 1996e72 (fiscal_label) so the benchmark builder and the
filter-accuracy check do not import RAG's network client. scripts/run_filter_accuracy.py asserts this copy and the
upstream function agree on every test case."""
from datetime import date, timedelta


def fiscal_label(period_of_report: str, fiscal_year_end: str, form: str) -> tuple[int, str]:
    y, m, d = (int(x) for x in period_of_report.split("-"))
    rep = date(y, m, d)
    fe_m, fe_d = int(fiscal_year_end[:2]), int(fiscal_year_end[2:])
    fe_d = min(fe_d, 28) if fe_m == 2 else fe_d
    fy_end_this_year = date(y, fe_m, fe_d)
    fy = y if rep <= fy_end_this_year + timedelta(days=10) else y + 1
    if form.startswith("10-K"):
        return fy, "FY"
    months_after_fy_end = (m - fe_m) % 12
    q = min(3, max(1, round(months_after_fy_end / 3)))
    return fy, f"Q{q}"
