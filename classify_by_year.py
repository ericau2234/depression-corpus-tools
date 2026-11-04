#!/usr/bin/env python3
"""Year-by-year level-1 cause classification of the clean Reddit corpus.

Same caliber as classify_v22.py (eric's caliber):
- posts: body length >= 200 chars; comments: >= 100 chars
  (length = record's `chars` field, falling back to len(text), as in
  classify_v22.loadc).
- Matching text = title + " " + text, lowercased, Aho-Corasick over the
  exact same dictionaries as classify_v22.analyze for Reddit:
  [EN2, PT_ES, FRD], trace words TRACE_EN2, trapped list TRAPPED.
- Categories are multi-label; percentages are per 100 of the CLASSIFIED
  base (records hitting >= 1 of the 13 cause categories).
- Money three calibers, counted exactly as classify_v22.analyze:
  strict = hits contain 经济窘迫(严);
  wide   = strict, or (trapped tag AND hits overlap {工作/学业, 家庭/父母,
           亲密关系});
  trace  = any TRACE_EN2 word. classify_v22 counts trace over ALL long
           rows and expresses it per classified base; both trace_all and
           trace_classified counts are recorded here so either base can
           be reproduced.
- Year = UTC year of the record's `created` epoch (fallback `created_utc`).
  Records with no usable timestamp land in an "unknown" bucket so totals
  reconcile with the whole-file numbers.
NONCAUSE tags from classify_v22 are omitted: they never intersect the
cause / trace / trapped tag sets, so no output number can change.
"""
import json, os, sys, datetime
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
try:
    import ahocorasick
except ImportError:
    sys.path.insert(0, os.path.join(BASE, "pylibs"))
    import ahocorasick

import classify_v22 as cv  # reuses EN2, PT_ES, FRD, CAUSES, TRAPPED, TRACE_EN2

CAUSES = cv.CAUSES
CAUSE_SET = set(CAUSES)
WIDE_TRAP_BASE = {"工作/学业", "家庭/父母", "亲密关系"}


def build_automaton():
    A = ahocorasick.Automaton()

    def add(word, tag):
        w = word.lower()
        if not w:
            return
        if w in A:
            A.get(w).add(tag)
        else:
            A.add_word(w, {tag})

    for k in CAUSES:
        for dic in (cv.EN2, cv.PT_ES, cv.FRD):
            for w in dic.get(k) or []:
                add(w, k)
    for w in cv.TRACE_EN2:
        add(w, "__trace__")
    for w in cv.TRAPPED:
        add(w, "__trapped__")
    A.make_automaton()
    return A


def year_of(d):
    c = d.get("created", d.get("created_utc"))
    if isinstance(c, (int, float)) and c > 0:
        try:
            return str(datetime.datetime.fromtimestamp(c, datetime.timezone.utc).year)
        except (OverflowError, OSError, ValueError):
            return "unknown"
    return "unknown"


def new_bucket():
    return {"n_long": 0, "n_classified": 0,
            "counts": Counter(), "strict": 0, "wide": 0,
            "trace_all": 0, "trace_classified": 0}


def finalize(b):
    base = b["n_classified"]

    def p100(x):
        return round(100 * x / base, 1) if base else 0.0

    return {
        "n_long": b["n_long"],
        "n_classified": b["n_classified"],
        "classified_pct_of_long": round(100 * base / b["n_long"], 1) if b["n_long"] else 0.0,
        "counts": {k: b["counts"].get(k, 0) for k in CAUSES},
        "per100_classified": {k: p100(b["counts"].get(k, 0)) for k in CAUSES},
        "money": {
            "strict": b["strict"],
            "wide": b["wide"],
            "trace_all": b["trace_all"],
            "trace_classified": b["trace_classified"],
            "strict_per100_classified": p100(b["strict"]),
            "wide_per100_classified": p100(b["wide"]),
            "trace_per100_classified_pipeline": p100(b["trace_all"]),
            "trace_per100_of_classified_hits": p100(b["trace_classified"]),
        },
    }


def run(fn, minc, A):
    path = os.path.join(BASE, "data_clean", fn)
    years = {}
    total = new_bucket()
    n_rows = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            n_rows += 1
            try:
                d = json.loads(line)
            except Exception:
                continue
            if (d.get("chars") or len(d.get("text") or "")) < minc:
                continue
            y = year_of(d)
            b = years.setdefault(y, new_bucket())
            t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
            tags = set()
            for _end, val in A.iter(t):
                tags |= val
            hits = tags & CAUSE_SET
            for bkt in (b, total):
                bkt["n_long"] += 1
                for k in hits:
                    bkt["counts"][k] += 1
                if "__trace__" in tags:
                    bkt["trace_all"] += 1
                if hits:
                    bkt["n_classified"] += 1
                    if "__trace__" in tags:
                        bkt["trace_classified"] += 1
                    if "经济窘迫(严)" in hits:
                        bkt["strict"] += 1
                        bkt["wide"] += 1
                    elif "__trapped__" in tags and hits & WIDE_TRAP_BASE:
                        bkt["wide"] += 1
            if n_rows % 200000 == 0:
                print(f"  {fn}: {n_rows} rows scanned", flush=True)
    out = {"n_rows_total": n_rows, "totals": finalize(total),
           "years": {y: finalize(years[y]) for y in sorted(years)}}
    return out


def main():
    A = build_automaton()
    result = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "method": {
            "source": "classify_v22.py dictionaries (EN2+PT_ES+FRD, TRACE_EN2, TRAPPED)",
            "posts_min_chars": 200, "comments_min_chars": 100,
            "base": "per-100 of classified (records hitting >=1 cause category)",
            "year": "UTC year of `created` epoch",
        },
        "posts": run("reddit_clean.jsonl", 200, A),
        "comments": run("reddit_comments_clean.jsonl", 100, A),
    }
    outp = os.path.join(BASE, "year_matrix.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    for name in ("posts", "comments"):
        t = result[name]["totals"]
        print(f"{name}: rows={result[name]['n_rows_total']} n_long={t['n_long']} "
              f"n_classified={t['n_classified']}")
    print("wrote", outp, flush=True)


if __name__ == "__main__":
    main()
