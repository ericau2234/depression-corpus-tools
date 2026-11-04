#!/usr/bin/env python3
"""INTERIM by-year classification on the interim merged sets
(reddit_interim_clean.jsonl / reddit_comments_interim_clean.jsonl).
Reuses classify_by_year.run verbatim (same classify_v22 dictionaries,
posts >=200 chars, comments >=100, per-100 of classified base, money
three calibers). Writes year_matrix_interim.json. All numbers INTERIM:
deep2 is at 45/500 windows, unevenly distributed across subs/years."""
import json, os, sys, datetime
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import classify_by_year as cby


def main():
    A = cby.build_automaton()
    result = {
        "interim": True,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "method": {
            "source": "classify_v22.py dictionaries (EN2+PT_ES+FRD, TRACE_EN2, TRAPPED), via classify_by_year.run",
            "inputs": ["reddit_interim_clean.jsonl", "reddit_comments_interim_clean.jsonl"],
            "posts_min_chars": 200, "comments_min_chars": 100,
            "base": "per-100 of classified (records hitting >=1 cause category)",
            "year": "UTC year of `created` epoch",
        },
        "posts": cby.run("reddit_interim_clean.jsonl", 200, A),
        "comments": cby.run("reddit_comments_interim_clean.jsonl", 100, A),
    }
    outp = os.path.join(BASE, "year_matrix_interim.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    for name in ("posts", "comments"):
        t = result[name]["totals"]
        print(f"{name}: rows={result[name]['n_rows_total']} n_long={t['n_long']} "
              f"n_classified={t['n_classified']}")
    print("wrote", outp, flush=True)


if __name__ == "__main__":
    main()
