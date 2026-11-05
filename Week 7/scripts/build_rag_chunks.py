"""Chunk the MSFT Q3 FY2026 10-Q with the RAG team's own parser/chunker (rag.chunk.chunk_filing @ 1996e72).

    python scripts/build_rag_chunks.py upstream/KPMG_RAG upstream/data_engineering_kpmg/data/raw/sec/0001193125-26-191507/msft-20260331.htm data/rag_chunks_msft_10q.jsonl

Lets Eval check every gold evidence anchor against the exact text RAG indexes, and run RAG's real BM25
retriever offline. Output follows RAG's chunks.jsonl format.
"""
import warnings
warnings.filterwarnings("ignore")
import sys, json
from pathlib import Path
rag_root, htm, out = sys.argv[1:4]
sys.path.insert(0, rag_root)
from rag.chunk import chunk_filing
meta = {"ticker":"MSFT","cik":789019,"company":"MICROSOFT CORP","form":"10-Q","fiscal_year":2026,"fiscal_period":"Q3",
        "period_of_report":"2026-03-31","filing_date":"2026-04-29","accession":"0001193125-26-191507",
        "source_url":"https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm"}
recs, rep = chunk_filing(meta, Path(htm).read_bytes())
Path(out).write_text("".join(json.dumps(r)+"\n" for r in recs))
print(json.dumps(rep))
