#!/usr/bin/env python3
"""Process the queue one batch at a time, saving each finished batch. Stop at any time; rerunning continues where it left off, with any adapter.
  23_extract.py --adapter codex --model gpt-6-luna --workers 8 --max-credits 50
  23_extract.py --adapter anthropic --model claude-haiku-5-5 --budget-usd 20
Defaults (50 comments per batch, medium effort) come from the sweep in analysis/eval; see README.
Before each Codex batch the account is re-read, and the run stops on any rule in extract_lib.stop_reason."""
import argparse, concurrent.futures as cf, json, os, queue, subprocess, sys, tempfile, threading, time
sys.path.insert(0, "scripts")
import extract_lib as L

ap = argparse.ArgumentParser()
ap.add_argument("--queue", default="data/extract/queue.parquet")
ap.add_argument("--out", default="extract/out", help="result folder; also the record of what is done")
ap.add_argument("--also-done", action="append", default=[], help="other result folders whose comments should be skipped")
ap.add_argument("--adapter", choices=["codex", "anthropic"], required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--batch-size", type=int, default=50)
ap.add_argument("--effort", default="medium")
ap.add_argument("--workers", type=int, default=1)
ap.add_argument("--max-batches", type=int)
ap.add_argument("--floor", type=float, default=100, help="codex: stop below this credit balance")
ap.add_argument("--max-credits", type=float, help="codex: stop after this many credits in this run")
ap.add_argument("--budget-usd", type=float, help="anthropic: stop after this many dollars in this run")
ap.add_argument("--timeout", type=int, default=1200)
a = ap.parse_args()
MAX_ATTEMPTS, MAX_CONSECUTIVE_FAILS = 2, 3
HAIKU_USD = (0.10, 0.50)


def read_account():
    """Read-only: asks the local Codex app server for the balance. Runs no model."""
    p = subprocess.Popen(["codex", "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(x) for x in p.stdout], daemon=True).start()

    def call(i, method, params=None):
        msg = {"method": method, "id": i}
        if params is not None:
            msg["params"] = params
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()
        end = time.time() + 45
        while time.time() < end:
            try:
                d = json.loads(lines.get(timeout=1))
            except queue.Empty:
                continue
            except json.JSONDecodeError:
                continue
            if d.get("id") == i and "method" not in d:
                return d
        return {"error": "timeout"}
    try:
        call(1, "initialize", {"clientInfo": {"name": "hackerbuys-extract", "version": "1"}, "capabilities": {}})
        p.stdin.write(json.dumps({"method": "initialized"}) + "\n")
        p.stdin.flush()
        return L.normalize_status(call(2, "account/rateLimits/read"))
    finally:
        p.terminate()


def run_codex(rows):
    with tempfile.TemporaryDirectory() as tmp:
        work, result = os.path.join(tmp, "w"), os.path.join(tmp, "result.json")
        os.mkdir(work)
        r = subprocess.run(L.codex_command(a.model, a.effort, work, SCHEMA_FILE, result, INSTRUCTIONS_FILE), input=L.payload(rows),
                           capture_output=True, text=True, timeout=a.timeout)
        usage = L.usage_from_events(r.stdout)
        if r.returncode != 0 or not os.path.exists(result):
            raise RuntimeError(f"codex exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}")
        with open(result) as f:
            return f.read(), usage, L.credits_for(usage, a.model)


def run_anthropic(rows):
    import anthropic
    if a.model != "claude-haiku-5-5":
        sys.exit("only claude-haiku-5-5 is configured: other Claude models need different thinking and refusal settings")
    m = anthropic.Anthropic(max_retries=4, timeout=a.timeout).messages.create(
        model=a.model, max_tokens=16000, system=L.SYSTEM, messages=[{"role": "user", "content": L.payload(rows)}],
        thinking={"type": "disabled"}, output_config={"effort": "low", "format": {"type": "json_schema", "schema": L.SCHEMA}})
    if m.stop_reason != "end_turn":
        raise RuntimeError(f"stop_reason {m.stop_reason}")
    usage = {"input_tokens": m.usage.input_tokens, "cached_input_tokens": 0, "output_tokens": m.usage.output_tokens, "reasoning_output_tokens": 0}
    cost = (m.usage.input_tokens * HAIKU_USD[0] + m.usage.output_tokens * HAIKU_USD[1]) / 1e6
    return next(b.text for b in m.content if b.type == "text"), usage, cost


# The same files for every batch give each run an identical prefix, which is what the prompt cache needs.
_shared = tempfile.mkdtemp(prefix="hb-extract-")
SCHEMA_FILE, INSTRUCTIONS_FILE = os.path.join(_shared, "schema.json"), os.path.join(_shared, "instructions.md")
with open(SCHEMA_FILE, "w") as f:
    json.dump(L.SCHEMA, f)
with open(INSTRUCTIONS_FILE, "w") as f:
    f.write(L.INSTRUCTIONS)
RUN = run_codex if a.adapter == "codex" else run_anthropic
done = L.load_done(a.out)
for d in a.also_done:
    done |= L.load_done(d)
print(f"queue {L.queue_size(a.queue)}, already done {len(done)}, adapter {a.adapter}, model {a.model}, batch size {a.batch_size}", flush=True)

st = {"spent": 0.0, "ok": 0, "fail": 0, "consecutive": 0, "tok": {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}, "stop": None}
lock = threading.Lock()
start = last = None
if a.adapter == "codex":
    s0 = read_account()
    start = last = s0["balance"]
    print("account", s0, flush=True)


def guard():
    """Decide whether another batch may start."""
    global last
    if st["stop"]:
        return False
    if a.max_batches is not None and st["ok"] + st["fail"] >= a.max_batches:
        st["stop"] = f"max batches {a.max_batches}"
        return False
    if st["consecutive"] >= MAX_CONSECUTIVE_FAILS:
        st["stop"] = f"{MAX_CONSECUTIVE_FAILS} batches failed in a row"
        return False
    if a.adapter == "codex":
        s = read_account()
        reason = L.stop_reason(s, start=start, last=last, floor=a.floor, max_credits=a.max_credits, estimated=st["spent"])
        if s["balance"] is not None:
            last = s["balance"]
        st["stop"] = reason
        return reason is None
    if a.budget_usd is not None and st["spent"] >= a.budget_usd:
        st["stop"] = f"budget {a.budget_usd} reached"
        return False
    return True


def work(rows):
    t = time.time()
    err = None
    for attempt in range(MAX_ATTEMPTS):
        usage = None
        try:
            text, usage, spent = RUN(rows)
            with lock:  # output that fails validation was still paid for
                st["spent"] += spent
                for k in st["tok"]:
                    st["tok"][k] += usage.get(k, 0)
            results = L.parse_results(text, rows)
            L.write_result(a.out, [r["id"] for r in rows], results, dict(model=a.model, effort=a.effort, adapter=a.adapter, prompt_version=L.PROMPT_VERSION,
                           batch_size=len(rows), usage=usage, spent=spent, seconds=round(time.time() - t, 1), attempt=attempt + 1))
            with lock:
                st["ok"] += 1
                st["consecutive"] = 0
                print(f"ok {st['ok']} comments {st['ok'] * a.batch_size} found {len(results)}/{len(rows)} spent {st['spent']:.2f} tok {usage['input_tokens']}/{usage['cached_input_tokens']}/{usage['output_tokens']} {time.time() - t:.0f}s", flush=True)
            return
        except (ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
            err = str(e)[:300]
    with lock:
        st["fail"] += 1
        st["consecutive"] += 1
    with open(os.path.join(a.out, "failed.log"), "a") as f:
        f.write(json.dumps({"first_id": rows[0]["id"], "n": len(rows), "error": err, "at": time.strftime("%FT%T")}) + "\n")
    print("FAILED batch", rows[0]["id"], err, flush=True)


os.makedirs(a.out, exist_ok=True)
pending = set()
with cf.ThreadPoolExecutor(a.workers) as ex:
    for batch in L.batches(L.read_queue(a.queue), done, a.batch_size):
        while len(pending) >= a.workers:
            finished, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
            for f in finished:
                f.result()
        if not guard():
            break
        pending.add(ex.submit(work, batch))
    else:
        st["stop"] = "queue finished"
print("STOPPED:", st["stop"], {k: st[k] for k in ("spent", "ok", "fail", "tok")}, flush=True)
if a.adapter == "codex":
    print("account", read_account(), flush=True)
