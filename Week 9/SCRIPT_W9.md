# Week 9 script (11/19): 6 slides

About 680 words, roughly 5.3 minutes at a measured pace. The same text is in each slide's speaker notes. Slides 7 and 8 are the appendix, for questions.

## Slide 1: Executive summary (1.5 min)

This week moved from measuring the systems to checking whether our measurements can be trusted. Three things happened. First, RAG sent us three versions of its answers on the same 38 questions. Its next version, which writes fuller answers, states every required point on 34 of 38 questions, up from 26, and all 80 figures in those answers are supported by a cited passage. Second, we compared our judge with RAG's judge, and they agree on 72 of 74 points. Third, we wrote a sealed test of 40 new questions that no team has seen, and published its hash. The rest of the deck is the evidence, and the dates for what is still open.

## Slide 2: Narrative answers (2 min)

The table compares three RAG versions. The frozen version passes 26 of 38 questions. A retrieval variant passes 28, and the fuller-answers version passes 34. The last column is the important one. Longer answers are where a model usually starts inventing detail, so we checked every figure against the passages the answer cites. In the fuller answers, 80 of 80 are either printed in a cited passage or computed correctly from printed numbers. Eight questions gained and none were lost. What is still missing is narrow: the line item under a segment, and after-tax amounts. One caution. These are the questions RAG tuned on, so this is a development result. The sealed test is what will confirm it.

## Slide 3: Can we trust the judge? (2 min)

These scores come from an LLM judge, so the judge needs its own check. RAG ran our judge script with one model, and we judged the same answers independently. On the frozen version the two agree on 71 of 74 points, and on the fuller answers on 72 of 74. The middle row is the useful one. For the retrieval variant, our judge showed a gain of two questions and RAG's showed none. Because the judges disagreed, we reported no measurable change, and RAG dropped that variant. The gain for fuller answers holds under both judges. What is not done yet is the human check. Two of us are labelling 87 points and RAG is labelling 20 questions blind, both by November 18.

## Slide 4: A test nobody tuned on (2 min)

Every number you have seen from any team was tuned on the same 155 questions. So this week we wrote holdout batch A: 40 new questions, 30 numeric, 5 narrative and 5 unanswerable. Ten are on Microsoft, which is 25 percent, against more than 60 percent in the development set. Fourteen are stress questions, such as misspelled company names and analyst wording. The answers come from the Data team's fact store, and none reuses a fact from a development question. The file's hash is public and the questions are not. RAG will check the hash, run its frozen version once without opening the file, and send the answers back for us to score. RAG also pre-registered a larger test plan and asked us to hold those questions too. We reviewed it and proposed five changes.

## Slide 5: GraphRAG (1.5 min)

We read GraphRAG's live graph directly for the first time this week. Exhibit 21, the list of subsidiaries, is now loaded: 752 subsidiaries across all ten companies. We checked three companies against our reference answers, and Microsoft, Micron and Casey's all match. That matters because seven relationship questions could not be answered by any system in round 1, and they can now be scored. Separately, GraphRAG's ranking fixes took the right figure at rank one from 26 to 60 of 93 questions. The next step is for GraphRAG to re-run graph search on the current gold set.

## Slide 6: Next steps (1 min)

Six tests remain before the code freeze on November 30, each with an owner and a date. Hand labels by the 18th. Batch A goes to RAG on the 20th. The Agents' API, the graph re-run, and cost and latency per question by the 24th. Batch B on RAG's next version by the 29th. I want to thank the RAG team in particular. They froze their settings before asking for a test, wrote their plan down in advance, and invited us to change any rule that favoured them. That is what will make the final numbers believable.
