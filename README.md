<div align="center">

<img src="docs/images/logo.svg" width="72" alt="HackerBuys logo: orange, grey and blue verdict bars">

# HackerBuys

**The stuff Hacker News actually recommends.**

Physical products ranked by the Hacker News commenters who own them, with every opinion linked to its comment.

[**Visit the site**](https://hn.shellbear.me) · [Keyboards](https://hn.shellbear.me/c/keyboards) · [Buy it for life](https://hn.shellbear.me/t/bifl) · [How it works](#how-it-works)

[![Site](https://img.shields.io/badge/site-hn.shellbear.me-F26A00)](https://hn.shellbear.me)
[![Code license: MIT](https://img.shields.io/badge/code-MIT-2340B8)](LICENSE)
[![Data: ODC-BY](https://img.shields.io/badge/source%20data-ODC--BY-8D968E)](https://huggingface.co/datasets/open-index/hacker-news)

<img src="docs/images/home.jpg" alt="HackerBuys home page: products ranked by owner verdicts, with orange, grey and blue bars" width="900">

</div>

## Why

Hacker News is full of people describing gear they've used for years, like the keyboard they've typed on for a decade or the laptop they regret. Those opinions are buried across millions of threads.

HackerBuys reads those comments and asks three questions: which product is this, did this person actually use it, and what do they think of it? It then ranks products by distinct owners, so one loud commenter counts once.

## Features

- **Rankings four ways:** most loved, most owned, recommended lately and long-haul.
- **Verdicts adjusted for sample size:** 93% from 170 owners can beat 100% from 19.
- **Sources for everything:** each opinion links to the original comment.
- **Ownership details:** years owned, whether it's still going, and which products people moved to or from.
- **Tags from the data:** Buy it for life, People switch to this, Divisive and Skip some generations.
- **Instant search and navigation:** a static site with no server, and nothing you type leaves your browser.

<table>
<tr>
<td width="50%"><img src="docs/images/product.jpg" alt="Kinesis Advantage page: 180 owners, 93% of verdicts positive, 32 years longest happy owner"><br><sub><b>Product pages:</b> verdicts, ownership length and where people moved.</sub></td>
<td width="50%"><img src="docs/images/category.jpg" alt="Keyboards category sorted by most owned"><br><sub><b>Categories:</b> with sortable columns.</sub></td>
</tr>
<tr>
<td colspan="2"><img src="docs/images/search.jpg" alt="Search results for standing desk, including products without those words in their names"><br><sub><b>Search:</b> matches product types, so "standing desk" also finds Fully Jarvis and Uplift.</sub></td>
</tr>
</table>

## Status

Extraction runs newest first, and the site updates as it progresses.

| | As of November 6, 2026 |
|---|---|
| Comments scanned | 828,493 of about 41 million |
| Complete years | 2022 to 2026 (through November 4), among comments that match the product filter |
| Second pass | 18,783 comments from 2023 to 2026 that the filter rejected but that name a known product and carry an opinion signal |
| Earlier years | A sample chosen to favor likely product opinions |
| Product mentions | 177,261 |
| Ranked products | 2,886 with 3 or more owners, plus 1,534 model pages |
| Models | gpt-6-luna for 2023 to November 3, 2026; Claude Haiku 5.5 for 2022 and the daily updates |
| Updates | Daily, through a [GitHub Actions job](#daily-updates) |

## How it works

```mermaid
flowchart LR
    A["Hacker News archive<br/>plus recent days"] --> B["Keyword filter<br/>about 4-5% of comments"]
    B --> C["LLM extraction<br/>product, verdict, ownership"]
    C --> D["Results by comment id<br/>resumable by any model"]
    D --> E["Build<br/>rank, tag, render"]
    E --> F["Static pages<br/>on Cloudflare"]
```

1. **Collect:** the [`open-index/hacker-news`](https://huggingface.co/datasets/open-index/hacker-news) archive through August 2026, then later days from the ClickHouse public demo.
2. **Filter:** regular expressions keep comments that mention a product category or brand. This keeps the cost manageable, but it misses opinions that use none of those words.
3. **Extract:** a model reads comments in batches and returns validated JSON: brand, line, model, type, verdict, first-hand use, years owned, pros, cons and a verbatim quote.
4. **Rank:** the Wilson lower bound over first-hand verdicts, counting each owner once, with neutral verdicts left out.
5. **Publish:** each product and category becomes a real HTML page, with JavaScript adding sorting, search and instant navigation.

### Accuracy

Extraction is automated and makes mistakes, so treat the site as a starting point. Every comment links to its source.

On 400 labeled comments, scored against labels from Claude Sonnet, the current settings reached about **88% precision and 82% recall**, with a margin of about ±7 points. About 97% of extracted quotes appear word for word in their comments.

- Comments that pass the filter but aren't clearly reviews are the noisiest, so rankings rely on first-hand verdicts.
- A blind audit of 150 random kept mentions per model, judged by Claude Sonnet, found the first-hand verdicts that drive rankings correct about 84% of the time for Haiku (2022) and 80% for gpt-6-luna (2023), within ±8 points. Mentions by non-owners are right only about a third of the time for both, and Haiku keeps more of them.
- Rising and Fading tags stay hidden until 2019–2026 are all fully scanned, because comparing years with different coverage would mislead.

## Run it yourself

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+. Everyday tasks are in the [`Makefile`](Makefile): run `make` to list them.

```bash
make install    # uv sync
make build      # build the site into site/, about 20 seconds
make serve      # preview it with wrangler dev
make test       # Python and JavaScript tests
```

Raw data is about 15 GB and isn't in this repo. See [`scripts/01_funnel.py`](scripts/01_funnel.py) and [`scripts/02_enrich.py`](scripts/02_enrich.py) for the filter stage.

```bash
uv sync

# Fetch missing days, newest first (the ClickHouse demo allows 60,000 rows an hour)
.venv/bin/python scripts/21_backfill.py 2026-08-22 2026-11-03

# Queue candidates, newest year first
.venv/bin/python scripts/22_build_queue.py data/extract/queue.parquet

# Extract: stop any time, and rerunning continues where it left off
.venv/bin/python scripts/23_extract.py --adapter codex --model gpt-6-luna --workers 8 --max-credits 50
.venv/bin/python scripts/23_extract.py --adapter claude --model claude-haiku-5-5 --effort low --workers 16 --min-year 2022 --max-year 2022
.venv/bin/python scripts/26_progress.py

# Build the site (with the local queue present, this also refreshes corpus/archive), then preview it
make build
make serve

# Test
make test
```

The Codex adapter re-reads your balance before each batch. It stops below `--floor`, at `--max-credits`, if the balance rises, or on a spending limit.

The `claude` adapter runs Haiku through the Claude Code CLI on a logged-in subscription, with no tools, settings or MCP servers. Thinking can't be turned off there, so a batch takes about 75 seconds; use more workers. On the 400 labeled comments it reached 79% precision and 97% recall, against 88% and 80% for gpt-6-luna, so it keeps more borderline comments. Three failed batches in a row, for example at a usage limit, stop the run.

Pushes to `main` deploy to Cloudflare Workers through [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml): it runs the tests, builds the site from the committed data in about 20 seconds, and runs `wrangler deploy`. Generated pages are not committed. It needs the `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` repository secrets.

Each page's last-changed date lives in `state/lastmod.json`, which the deploy commits back. A page's date only moves when its text changes, so this file is the build's only memory. Local builds read it but never write it. `make verify-live` checks that the live site serves exactly what a local build produces.

### Daily updates

[`.github/workflows/daily.yml`](.github/workflows/daily.yml) runs [`scripts/31_daily.py`](scripts/31_daily.py) every morning. It fetches each finished day after the last one covered, queues it with [`scripts/30_daily_queue.py`](scripts/30_daily_queue.py), extracts it with Haiku, pushes the new data, and starts the deploy. It works from a plain checkout because everything the site needs is in `corpus/`:

- `corpus/archive/<month>.parquet`: text and details of the comments already processed from the full local queue
- `corpus/totals.json`: candidates per year in the full queue, and its last day
- `corpus/daily/<day>.parquet`: the queue for each day after that

The workflow needs a `CLAUDE_CODE_OAUTH_TOKEN` repository secret, made with `claude setup-token`. Leftover comments, for example after a usage limit, are picked up the next day.

The 15 GB archive and `data/extract/queue.parquet` stay local and are only needed to process older years. After a local extraction run, build the site to refresh `corpus/archive`, then commit it.

## Project layout

```text
scripts/    filter, queue, extraction and site build
site/       app.js, sort.js, style.css and icons; the build writes the pages here
state/      each page's last-changed date, kept between builds
extract/    extraction results, one JSON file per batch
corpus/     comment text for the site build and the daily queues
analysis/   feasibility report, evaluation sets and labels
tests/      Python and JavaScript tests
```

Early findings are in [`analysis/REPORT.md`](analysis/REPORT.md).

## Credits

- Comments by the Hacker News community, through [`open-index/hacker-news`](https://huggingface.co/datasets/open-index/hacker-news) (ODC-BY) and the [ClickHouse public demo](https://sql-clickhouse.clickhouse.com).
- Inspired by HackerBooks and HackerTube.
- Not affiliated with Y Combinator.

## License

Code is [MIT](LICENSE). Hacker News data keeps its own license and belongs to its authors.

Made by [shellbear](https://shellbear.me).
