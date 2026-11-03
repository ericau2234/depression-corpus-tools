#!/usr/bin/env python3
"""Level-3 counting + exemplars: given a pool jsonl and an items JSON
{name: [phrases]}, print per-100-of-pool shares and up to 3 verbatim
exemplar sentences per item.
Usage: count_fine.py <pool.jsonl> <items.json>"""
import json, os, random, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
pool = [json.loads(l) for l in open(os.path.join(BASE, sys.argv[1]), encoding="utf-8")]
items = json.load(open(os.path.join(BASE, sys.argv[2]), encoding="utf-8"))
random.seed(11)
SENT = re.compile(r"(?<=[.!?])\s+")

counts = {k: 0 for k in items}
exemplars = {k: [] for k in items}
order = list(pool); random.shuffle(order)
for d in pool:
    t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
    for k, phrases in items.items():
        if any(p in t for p in phrases): counts[k] += 1
for d in order:
    full = ((d.get("title") or "") + ". " + (d.get("text") or "")).replace("\n", " ")
    for k, phrases in items.items():
        if len(exemplars[k]) >= 3: continue
        for s in SENT.split(full):
            sl = s.lower()
            if 50 <= len(s) <= 220 and any(p in sl for p in phrases):
                exemplars[k].append(s.strip()); break
n = len(pool)
print(f"POOL n={n}")
for k in items:
    print(f"\n## {k}: {round(100*counts[k]/n,1)} （{counts[k]} 篇）")
    for e in exemplars[k]: print(f"  「{e}」")
