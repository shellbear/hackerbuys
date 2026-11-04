#!/usr/bin/env python3
"""Score a test run against the 400 labeled comments and report real token overhead. usage: 24_eval_extract.py analysis/eval/queue_eval.parquet analysis/eval/luna_b50 ..."""
import collections as C, json, sys
sys.path.insert(0, "scripts")
import duckdb
from rapidfuzz import fuzz
import extract_lib as L

CHARS_PER_TOKEN = 4.64  # measured on 51k comments with o200k_base
queue, dirs = sys.argv[1], sys.argv[2:]
rows = {r[0]: r for r in duckdb.sql(f"""select id,tier,"text",thread,parent from '{queue}'""").fetchall()}
with open("analysis/eval/labels_sonnet.jsonl") as f:
    gold = {d["id"]: d for d in map(json.loads, f)}


def name(p):
    return " ".join(x for x in (p["brand"], p["line"], p["model"]) if x)


for d in dirs:
    docs = list(L.iter_results(d))
    pred = {r["id"]: r["products"] for doc in docs for r in doc["results"]}
    ids = [i for doc in docs for i in doc["ids"] if i in gold]
    tp = sum(gold[i]["relevant"] and i in pred for i in ids)
    fp = [i for i in ids if not gold[i]["relevant"] and i in pred]
    fn = [i for i in ids if gold[i]["relevant"] and i not in pred]
    matched = same = 0
    for i in ids:
        if gold[i]["relevant"] and i in pred:
            for g in gold[i]["products"]:
                best = max(pred[i], key=lambda p: fuzz.token_set_ratio(g["name"], name(p)))
                if fuzz.token_set_ratio(g["name"], name(best)) >= 80:
                    matched += 1
                    same += g["stance"] == best["stance"]
    gold_products = sum(len(gold[i]["products"]) for i in ids if gold[i]["relevant"] and i in pred)
    ps = [p for v in pred.values() for p in v]
    n = max(len(ps), 1)
    u = C.Counter()
    for doc in docs:
        u.update(doc["usage"])
    spent = sum(doc["spent"] for doc in docs)
    pay_tok = sum(len(L.payload([{"id": i, "y": 0, "thread": rows[i][3], "parent": rows[i][4], "text": rows[i][2]}])) for i in ids) / CHARS_PER_TOKEN
    overhead = (u["input_tokens"] - pay_tok) / max(len(docs), 1)
    print(f"\n== {d}: {len(ids)} comments in {len(docs)} batches, model {docs[0]['model'] if docs else '?'}")
    print(f"relevance vs Sonnet labels: precision {tp / max(tp + len(fp), 1):.1%}, recall {tp / max(tp + len(fn), 1):.1%} (tp {tp}, fp {len(fp)}, fn {len(fn)})")
    print(f"products matched {matched}/{gold_products}, same stance {same}/{max(matched, 1)} ({same / max(matched, 1):.1%}), products/comment {len(ps) / max(len(pred), 1):.2f}")
    print(f"quotes found verbatim {sum(L.quote_in_text(p['quote'], rows[i][2]) for i, v in pred.items() for p in v) / n:.1%}")
    print("fill:", {k: f"{sum(bool(p[k]) for p in ps) / n:.0%}" for k in ("line", "model", "generation", "product_type", "use_case", "pros", "cons", "switched_from")},
          "tenure", f"{sum(p['tenure_years'] is not None for p in ps) / n:.0%}", "status", C.Counter(p["status"] for p in ps).most_common())
    print(f"tokens: input {u['input_tokens']} (cached {u['cached_input_tokens']}), output {u['output_tokens']} (reasoning {u['reasoning_output_tokens']}); payload about {pay_tok:.0f}")
    print(f"overhead about {overhead:.0f} input tokens per batch; output {u['output_tokens'] / max(len(pred), 1):.0f} tokens per qualifying comment; spent {spent:.3f} ({spent / max(len(ids), 1) * 1000:.2f} per 1,000 comments); {sum(doc['seconds'] for doc in docs):.0f}s total")
    print("false positives:", [(i, [name(p) for p in pred[i]][:2]) for i in fp[:12]])
    print("false negatives:", [(i, [g["name"] for g in gold[i]["products"]][:2]) for i in fn[:12]])
