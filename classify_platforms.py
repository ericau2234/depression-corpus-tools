#!/usr/bin/env python3
"""Level-1 cause classification for the non-Reddit English platforms.

Same dictionaries and calibers as classify_v22.py / classify_by_year.py:
- dictionaries imported from classify_v22 (EN2 only, as classify_v22.analyze
  uses for these platforms), plus TRACE_EN2 (money trace) and TRAPPED.
- posts: body length >= 200 chars (record `chars`, fallback len(text)).
- matching text = title + " " + text, lowercased, Aho-Corasick.
- categories multi-label; percentages per 100 of the CLASSIFIED base
  (records hitting >= 1 of the 13 cause categories).
- money: strict = 经济窘迫(严) hit; wide = strict, or (trapped tag AND hit
  in {工作/学业, 家庭/父母, 亲密关系}); trace = any TRACE_EN2 word, counted
  over all long rows (pipeline convention) and also over classified rows.
- NONCAUSE buckets are tallied (per 100 of long) for boilerplate sanity
  checks only; they never enter the classified base.
Writes platform_classify.json; prints 2 classified examples per platform.
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

import classify_v22 as cv

CAUSES = cv.CAUSES
CAUSE_SET = set(CAUSES)
WIDE_TRAP_BASE = {"工作/学业", "家庭/父母", "亲密关系"}
MINC = 200

PLATFORMS = [
    ("patient", "patient_clean.jsonl", False),
    ("beyondblue", "beyondblue_clean.jsonl", False),
    ("mhf", "mhf_clean.jsonl", False),
    ("livejournal", "livejournal_clean.jsonl", True),  # crawl still running
]


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
        for w in cv.EN2.get(k) or []:
            add(w, k)
    for w in cv.TRACE_EN2:
        add(w, "__trace__")
    for w in cv.TRAPPED:
        add(w, "__trapped__")
    for k, ws in cv.NONCAUSE.items():
        for w in ws:
            add(w, "NC:" + k)
    A.make_automaton()
    return A


def run(name, fn, partial, A):
    path = os.path.join(BASE, "data_clean", fn)
    total = 0
    n_long = 0
    classified = 0
    counts = Counter()
    nc = Counter()
    strict = wide = trace_all = trace_classified = 0
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            total += 1
            if (d.get("chars") or len(d.get("text") or "")) < MINC:
                continue
            n_long += 1
            t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
            tags = set()
            for _end, val in A.iter(t):
                tags |= val
            hits = tags & CAUSE_SET
            for k in hits:
                counts[k] += 1
            for tg in tags:
                if tg.startswith("NC:"):
                    nc[tg[3:]] += 1
            if "__trace__" in tags:
                trace_all += 1
            if hits:
                classified += 1
                if "__trace__" in tags:
                    trace_classified += 1
                if "经济窘迫(严)" in hits:
                    strict += 1
                    wide += 1
                elif "__trapped__" in tags and hits & WIDE_TRAP_BASE:
                    wide += 1
                if len(examples) < 2:
                    examples.append({
                        "id": d.get("id"),
                        "title": d.get("title") or "",
                        "hits": sorted(hits),
                        "snippet": (d.get("text") or "")[:300],
                    })
    base = classified

    def p100c(x):
        return round(100 * x / base, 1) if base else 0.0

    def p100l(x):
        return round(100 * x / n_long, 1) if n_long else 0.0

    out = {
        "file": fn,
        "partial_crawl_still_running": partial,
        "total_records": total,
        "n_long_ge200": n_long,
        "n_classified": classified,
        "classified_pct_of_long": round(100 * classified / n_long, 1) if n_long else 0.0,
        "counts": {k: counts.get(k, 0) for k in CAUSES},
        "per100_classified": {k: p100c(counts.get(k, 0)) for k in CAUSES},
        "money": {
            "strict_count": strict, "strict_per100_classified": p100c(strict),
            "wide_count": wide, "wide_per100_classified": p100c(wide),
            "trace_count_all_long": trace_all,
            "trace_per100_classified_pipeline": p100c(trace_all),
            "trace_count_classified": trace_classified,
            "trace_per100_of_classified_hits": p100c(trace_classified),
        },
        "noncause_per100_of_long": {k: p100l(v) for k, v in nc.most_common()},
        "examples_classified": examples,
    }
    print(f"{name}: total={total} n_long={n_long} classified={classified} "
          f"({out['classified_pct_of_long']}%)", flush=True)
    return out


def main():
    A = build_automaton()
    merge_stats = None
    mp = os.path.join(BASE, "patient_merge_stats.json")
    if os.path.exists(mp):
        merge_stats = json.load(open(mp, encoding="utf-8"))
    result = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "method": {
            "source": "classify_v22.py dictionaries (EN2, TRACE_EN2, TRAPPED, NONCAUSE)",
            "min_chars": MINC,
            "base": "per-100 of classified (records hitting >=1 cause category)",
            "money_wide": "strict, or trapped tag + hit in {工作/学业, 家庭/父母, 亲密关系}",
            "trace_convention": "trace counted over all long rows, expressed per classified base (pipeline convention); trace among classified hits also recorded",
        },
        "patient_merge": merge_stats,
        "platforms": {},
    }
    for name, fn, partial in PLATFORMS:
        result["platforms"][name] = run(name, fn, partial, A)
    outp = os.path.join(BASE, "platform_classify.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("wrote", outp, flush=True)


if __name__ == "__main__":
    main()
