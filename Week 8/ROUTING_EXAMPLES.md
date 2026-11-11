# Routing examples for the demo (Week 8)

**Coverage** (the bars on the routing slide) = share of questions where every tool the question needs was called (no tool, for the questions that should be blocked). **It is not accuracy**: calling the right tools does not make the final answer right. Answer accuracy needs the reader (round 1).

**Which method gives which number** (155 questions): every tool 94.8% coverage at 3.00 calls per question (it misses only the 8 questions that need no tool); keyword router 83.9% at 1.05 calls; text only 20.0% at 1.00. The 95% is every tool, not the keyword router plus text only.

**Where the keyword router sits**: it is Eval's baseline for comparison, not part of the pipeline. The Agents' orchestrator does the real routing and can be scored on the same questions: `python scripts/run_routing_baselines.py --router name=your_module.py:route` (a function `route(question, session_ticker)` returning tool names) or `--calls name=calls.jsonl` (logged calls, one `{"qid": ..., "tools": [...]}` per line).

Router definitions:
- **text_only**: every question goes to RAG text search (the demo path before routing).
- **keyword**: Eval's rule-based stand-in for the Agents' orchestrator (regular expressions, no LLM). The scope gate runs first; if it blocks, no tool is called. Otherwise a relationship word (subsidiary, Exhibit 21, acquire, own, parent, rename) sends it to GraphRAG; a number word (how much, revenue, margin, percent, total, calculate) to SQL; an explanation word (why, explain, describe, risk, policy) to RAG text; both kinds of word to SQL + RAG; neither to RAG text.
- **combined**: every question goes to all three tools.

**Unneeded call**: a tool the router called that the question's expected route does not need (sql needs SQL; text needs RAG; graph needs GraphRAG; multi needs SQL + RAG; none needs no tool). Unneeded calls per question = total unneeded calls / 155 questions. It counts calls outside the expected route; it does not mean "text search alone could have answered".

All rates are on the current 155 Gold Set v2 questions only (104 sql, 31 text, 11 graph, 8 none, 1 multi), with routes labelled by Eval. They will move as questions are added.

## number from a statement (GSv0-MSFT-001)

> What was Microsoft’s total revenue for the three months ended March 31, 2026? State the amount in USD millions.

Expected route: **sql** (needs: SQL (Data finance views)). Keyword router: number word 'total' -> SQL.

| Router | Calls | Needed tools called | Unneeded calls |
| --- | --- | --- | --- |
| text_only | RAG text search | no | 1 |
| keyword | SQL (Data finance views) | yes | 0 |
| combined | GraphRAG, SQL (Data finance views), RAG text search | yes | 2 |

## explanation from the text (GSv0-MSFT-004)

> Name Microsoft’s reportable segments in this filing.

Expected route: **text** (needs: RAG text search). Keyword router: no number word -> RAG text search.

| Router | Calls | Needed tools called | Unneeded calls |
| --- | --- | --- | --- |
| text_only | RAG text search | yes | 0 |
| keyword | RAG text search | yes | 0 |
| combined | GraphRAG, SQL (Data finance views), RAG text search | yes | 2 |

## relationship (Exhibit 21) (EV3-001)

> In the Exhibit 21 of its fiscal 2026 annual report, how many subsidiaries does Micron list, and how many of them are organized outside the United States?

Expected route: **graph** (needs: GraphRAG). Keyword router: relationship word 'Exhibit 21' -> GraphRAG.

| Router | Calls | Needed tools called | Unneeded calls |
| --- | --- | --- | --- |
| text_only | RAG text search | no | 1 |
| keyword | GraphRAG | yes | 0 |
| combined | GraphRAG, SQL (Data finance views), RAG text search | yes | 2 |

## number plus its explanation: keyword router misses SQL (EV1R-003)

> How did Microsoft's net gains or losses from its investments in OpenAI change between the nine months ended March 31, 2025 and the nine months ended March 31, 2026, and what event drove the change?

Expected route: **multi** (needs: SQL (Data finance views), RAG text search). Keyword router: no number word -> RAG text search.

| Router | Calls | Needed tools called | Unneeded calls |
| --- | --- | --- | --- |
| text_only | RAG text search | no | 0 |
| keyword | RAG text search | no | 0 |
| combined | GraphRAG, SQL (Data finance views), RAG text search | yes | 1 |

## out of scope: market data (EV1-062)

> What was Microsoft's share price at the close on March 31, 2026?

Expected route: **none** (needs: no tool). Keyword router: scope gate decides 'abstain', no tool.

| Router | Calls | Needed tools called | Unneeded calls |
| --- | --- | --- | --- |
| text_only | RAG text search | no | 1 |
| keyword | none | yes | 0 |
| combined | GraphRAG, SQL (Data finance views), RAG text search | no | 3 |

## keyword router gets it wrong (GSv0-MSFT-009)

> What does revenue allocated to remaining performance obligations include?

Expected route: **text** (needs: RAG text search). Keyword router: number word 'revenue' -> SQL.

| Router | Calls | Needed tools called | Unneeded calls |
| --- | --- | --- | --- |
| text_only | RAG text search | yes | 0 |
| keyword | SQL (Data finance views) | no | 1 |
| combined | GraphRAG, SQL (Data finance views), RAG text search | yes | 2 |

## keyword router calls one extra tool (GSv0-MSFT-014)

> For the nine months ended March 31 in 2026 and 2025, calculate operating cash flow less cash additions to property and equipment. Use that specific definition, not a company-defined non-GAAP measure. Did this cash surplus increase or decrease?

Expected route: **sql** (needs: SQL (Data finance views)). Keyword router: number word 'calculate' and explanation word 'defin' -> SQL + RAG.

| Router | Calls | Needed tools called | Unneeded calls |
| --- | --- | --- | --- |
| text_only | RAG text search | no | 1 |
| keyword | SQL (Data finance views), RAG text search | yes | 1 |
| combined | GraphRAG, SQL (Data finance views), RAG text search | yes | 2 |
