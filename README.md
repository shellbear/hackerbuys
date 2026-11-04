# HackerBuys

Physical products ranked by the Hacker News commenters who own them. Findings so far are in `analysis/REPORT.md`.

## Extraction pipeline

Data: `open-index/hacker-news` Parquet files through 2026-08-21, then `data/daily` from the ClickHouse public demo (60,000 rows an hour). Both are gitignored; results in `extract/` are tracked.

```bash
.venv/bin/python scripts/21_backfill.py 2026-08-22 2026-11-03     # missing days, newest first; waits out the quota
.venv/bin/python scripts/22_build_queue.py data/extract/queue.parquet   # newest year first, funnel first within a year
.venv/bin/python scripts/23_extract.py --adapter codex --model gpt-6-luna --workers 8 --max-credits 50
.venv/bin/python scripts/25_merge_extract.py data/extract/queue.parquet data/extract/merged extract/out
.venv/bin/python -m unittest tests.test_extract_lib
```

Stop `23_extract.py` at any time. Rerunning skips every comment id already in the result folder, whichever model processed it. Each result records its model and prompt version. Rebuild the queue whenever new days arrive.

Codex runs re-read the account before each batch and stop below `--floor` (default 100 credits), if the balance rises, or on a spending limit. The Haiku adapter has not been run yet: it needs `ANTHROPIC_API_KEY`.

## Settings

From `analysis/eval`: 400 labeled comments, scored against Sonnet labels, on `gpt-6-luna`. With 117 positives, differences under about 7 points are noise.

| Batch, effort | Precision | Recall | Credits per 1,000 comments |
|---|---|---|---|
| 25, medium | 83.5% | 86.3% | 1.41 |
| **50, medium (default)** | 87.3%, 90.1% (two runs) | 82.1%, 85.5% | 1.29, 1.15 |
| 50, low | 84.8% | 76.1% | 1.19 |
| 100, medium | 95.1% | 82.9% | 1.24 |
| 100, low | 81.2% | 81.2% | 1.04 |

Tags and product groupings are computed from stored fields, so changing them needs no LLM pass. Only changing which comments qualify, such as including cars, needs comments re-read.
