# Gold Set v1 scorecard

Versions: benchmark `d584962d6ef6c6b8`, RAG `1996e72`, index `ffaa8efb4d5d`, eval `82fa054`. 14 questions pending (peer / 10-K chunks not yet shared).

| System | Numeric accuracy | Evidence recall@10 | Refusal (balanced) | Citation support |
|---|---|---|---|---|
| oracle | 1.00 (n=50) | 0.89 | 1.00 | 1.00 |
| refuse_all | 0.00 (n=50) | n/a | 0.50 | n/a |
| baseline_no_llm | 0.32 (n=50) | 0.81 | 0.89 | 0.92 |

Diagnostics per system are in the json scorecards.