# Gold Set v1 scorecard

Versions: benchmark `377bf5af94e3e6cb`, RAG `5bfafeb`, index `ffaa8efb4d5d`, eval `3d5bed7`. 54 questions pending (peer / 10-K chunks not yet shared).

| System | Numeric accuracy | Evidence recall@10 | Refusal (balanced) | Citation support |
|---|---|---|---|---|
| oracle | 1.00 (n=50) | 0.89 | 1.00 | 1.00 |
| refuse_all | 0.00 (n=50) | n/a | 0.50 | n/a |
| baseline_no_llm | 0.32 (n=50) | 0.81 | 0.89 | 0.92 |

Diagnostics per system are in the json scorecards.