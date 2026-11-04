# HackerBuys feasibility: physical-product recommendations from Hacker News

Data: `open-index/hacker-news`, 239 monthly Parquet files, 12 GB, 49.3M items, ending 2026-08-22 (the mirror stopped updating; about 10 weeks missing).
Reproduce: `scripts/01_funnel.py` → `02_enrich.py` → `04_sample.py` → `06_leaderboard.py` → `07_score.py` → `08_eval.py` → `09_final_eval.py`.

## Verdict
Feasible, and the data is rich enough. Three things differ from the original idea:
1. **Upvotes do not exist.** All 43,051,020 comment rows have score 0. Rank by distinct owners instead.
2. **Regex finds candidates but can't judge them.** It is about 29% precise, and it caught 5 of the 18 comments Sonnet labeled negative.
3. **Identifying products is harder than for books.** There is no ISBN or Open Library equivalent, so the catalog needs its own canonical product step.

## Funnel (measured)
| Stage | Comments | Notes |
|---|---|---|
| Live comments | 41,308,650 | |
| Category/brand word match ("candidates") | 1,854,514 | ~256M tokens (chars/4) |
| Plus first-person/recommendation signal ("funnel") | 416,489 | ~72M tokens, 1.0% of comments |
| Estimated real product opinions in funnel | 115k ± 31k | 29% precision (stratified, about 50 per tier) |
| Estimated real opinions in rejected candidates | 175k ± 131k | 6 of 50 sampled |

Funnel recall within candidates is about 40% (95% range 27-73%). Comments that matched no lexicon word (about 39M) were not measured.

| Tier | Population | Precision (± 95%) |
|---|---|---|
| Ask HN recommendation threads | 11,928 | 57% ± 14 |
| Tenure + ownership language | 4,799 | 50% ± 14 |
| "my <product>" | 179,602 | 37% ± 14 |
| Recommend language only | 27,423 | 30% ± 13 |
| Ownership language only | 160,497 | 19% ± 11 |
| Retail link only | 11,578 | 10% ± 8 (mostly books) |

## Model comparison (400 comments, 2 subagents)
- They agreed on 84.5% of relevance labels and 75% of stances on the first product.
- I adjudicated all 62 disagreements: Sonnet was right on about 58. 24 were books Haiku included, which the schema did not explicitly exclude.
- The reference set starts from Sonnet's labels, so its own score (99%/97%) is inflated. Haiku's 68% precision is a floor until it is retested with "no books" in the prompt. A random audit of 40 comments where both agreed found nothing clearly wrong.
- Sonnet's output: 1.38 products per relevant comment, 12% of products with an explicit ownership duration, 88% first-hand, 12% negative stance.

## Upvote proxy
`kids` order preserves HN's ranking (under 1% of lists are chronological).
Top-quintile comments average 2.90 replies vs 0.62 in the fourth quintile; the bottom quintile rises to 0.79, which suggests buried controversial comments.
Only comments with siblings have a rank. It can't be checked against real points because those aren't published, so use it as a tie-breaker at most.

## Scoring backtest (mentions through 2021 predict positive authors from 2022 on; 184 products)
| Signal | Spearman | Top-20 overlap |
|---|---|---|
| Raw mentions | 0.790 | 14 |
| Distinct authors | 0.790 | 14 |
| Weighted score | 0.784 | 14 |
| Weighted score, 2019-21 only | 0.833 | 15 |

The weighted formula adds nothing; recency does. Caveats: I picked the products in 2026 (hindsight inflates all of these), and the formula used regex sentiment. Re-run with LLM stance before finalizing weights.

## Baseline mentions (distinct authors, hand-picked list; mentions, not recommendations)
- Laptops: MacBook Pro 16,035; ThinkPad 9,471; MacBook Air 8,165
- Other leaders: Raspberry Pi 12,797; Kindle 12,699; Apple Watch 6,475
- Chairs: Aeron 1,360; Embody 231; Steelcase Leap 197
- Keyboards: Kinesis Advantage 887; IBM Model M 875; ErgoDox 836; HHKB 668
- Headphones: AirPods 5,111; AirPods Pro 1,286; Bose QC 527; Sony WH-1000XM 480
- Thin categories: desks (53 at most per product), bags (114), sleep (90). These need merged pages or a recall pass.

## Trends: 2024-26 vs 2021-23, per comment volume (mention rate, includes news)
Rising: Bambu Lab ×6.2, Eight Sleep ×4.3 (small n), Beelink ×3.1, Vision Pro ×2.9, Flipper Zero ×2.9, Roborock ×2.2, Mac Studio ×2.0, Kobo ×1.9.
Falling: VanMoof ×0.16, Onewheel ×0.17, Peloton ×0.26, Dell XPS 13 ×0.32.
Overall rate is roughly flat: 8-11k per million comments, 9.6k in 2022, 8.2k in 2025.

## Prediction scorecard (see 00_predictions.md)
| # | Prediction | Result |
|---|---|---|
| P1 | Comment score unusable | Correct: 0 non-zero |
| P2 | 40-45M comments | Correct: 41.3M |
| P3 | Funnel 1.5-3% | Wrong: 1.0% |
| P4 | Funnel precision 25-40% | Correct: 29% |
| P5 | 5-15k products | Not tested; needs extraction |
| P6 | Keyboards or laptops on top | Correct: laptops |
| P7 | ThinkPad or Aeron #1 | Wrong: MacBook Pro by mentions |
| P8 | Electronics more negative | Inconclusive: regex sentiment unreliable |
| P9 | Peak 2016-20, then decline | Mostly wrong: 2012 high, about 15% decline 2022→2025 |
| P10 | Sonnet $150-600 on funnel | Estimate fits, not measured |

## Recommended pipeline
1. **Filter:** Haiku 5.5 on all 1.85M candidates, batched, with books excluded in the prompt.
2. **Extract:** Sonnet 5.5 on survivors, with thread title and parent comment (some comments say only "this was my best buy").
3. **Canonicalize:** cluster names into product → line → brand, with LLM review of the top clusters.
4. **Recall pass:** rescan the other 39M comments for newly found brand names (no LLM cost), then extract the hits.
5. **Rank:** distinct first-hand owners, Wilson lower bound on positive vs negative, a recent-window view, and a "long-haul" view from ownership duration.
6. **Backfill:** fetch Aug-Nov 2026 from the HN API.

Cost estimate (Batch, chars/4 tokens, not measured): filter about $20-25; extraction about $150-200. Sonnet on the funnel alone costs about $130-250 and would likely find far fewer opinions. A pilot should confirm this first.

## Known limitations
- About 50 comments per tier, so per-tier numbers are wide.
- The lexicon and product list are mine and tech-heavy. Long-tail items (Bic Cristal, Edwin Jagger, SNOO) appeared only in missed comments.
- Labels ran through Claude Code subagents, not the Batch API, so behavior and cost may differ.
- Dataset license is ODC-BY: attribution required.

## Update: 42.5k-comment run (Sonnet subagents, 16M tokens, 32 minutes)
Scanned 42,529 comments (0.10% of all). 13,074 qualified, giving 17,453 product mentions and 4,577 products; 163 have 10+ owners, 77 have 25+.
Rankings count this sample only. It deliberately favors likely opinions, so counts are not all-of-HN volumes.

| Tier | Scanned | Opinion rate | Population | Estimated opinions |
|---|---|---|---|---|
| Ask HN threads | 11,916 | 51.8% | 11,928 | 6.2k |
| Tenure + ownership | 6,113 | 37.5% | 6,113 | 2.3k |
| "my <product>" | 12,000 | 24.4% | 178,288 | 43k |
| Ownership only | 3,000 | 22.8% | 160,497 | 37k |
| Recommend only | 4,000 | 20.7% | 27,423 | 5.7k |
| Rejected candidates | 2,500 | 6.6% | 1,438,025 | 95k ± 14k |
| No lexicon match (probe) | 3,000 | 0.4% | 39,454,136 | 158k ± 89k |

Estimated total about 347k. The regex funnel holds about 27% of that, candidates about 54%. The rest needs Haiku on everything or an NER model trained on these labels; the labeled set from this run could train one.

MacBook Pro by generation (+/−): 2015 73/8, 2016 21/24, 2017 8/28, 2018 6/27, 2019 13/13, M1 86/14. Of 83 negative 2016-19 comments, 45 mention the keyboard and 21 the Touch Bar; of 14 M-series, 2 and 1.
Moves with a clear direction (toward/back): ThinkPad→Framework 7/0, Aeron→Leap 7/1, Kindle→Kobo 5/0, MS Natural→Kinesis Advantage 6/0, MacBook Pro→Dell XPS 9/2. Same-line moves (X-series→ThinkPad) are merge artifacts.
Audit: 28 random extractions read against comments; nearly all correct, some weak "positive" labels on mere usage. This was not a formal precision measurement.
