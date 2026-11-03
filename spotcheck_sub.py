#!/usr/bin/env python3
"""Precision spot-check: sample random hits for the riskiest co-occurrence
sub-causes and print title+snippet for manual review."""
import json, os, random, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
_raw = json.load(open(os.path.join(BASE, "sub_dicts.json"), encoding="utf-8"))
spec = _raw["spec"] if "spec" in _raw else _raw
WIN = _raw.get("window_chars", 150)
_hdr = open(os.path.join(BASE, "classify_all.py")).read().split("def run")[0]
exec(_hdr)

TARGETS = {
 "丧亲/丧失": ["丧母", "丧子/流产"],
 "困住/逃不掉": ["困在工作"],
 "家庭/父母": ["家暴/父母冲突"],
 "经济窘迫(严)": ["看不起病/药费"],
}
random.seed(7)

def match_sub(t, cat, sname):
    s = spec[cat][sname]
    for w in s.get("P") or []:
        if w.lower() in t: return True
    for ga, gb in s.get("C") or []:
        pa, pb = [], []
        for w in ga:
            i = t.find(w.lower())
            while i >= 0: pa.append(i); i = t.find(w.lower(), i + 1)
        for w in gb:
            i = t.find(w.lower())
            while i >= 0: pb.append(i); i = t.find(w.lower(), i + 1)
        if pa and pb and min(abs(a - b) for a in pa for b in pb) <= WIN: return True
    return False

def parent_match(t, cat):
    return any(w.lower() in t for w in EN[cat])

def main():
    pools = {(c, s): [] for c, subs in TARGETS.items() for s in subs}
    p = os.path.join(BASE, "data_clean", "reddit_clean.jsonl")
    for l in open(p, encoding="utf-8"):
        try: d = json.loads(l)
        except Exception: continue
        if (d.get("chars") or len(d.get("text") or "")) < 200: continue
        t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
        for (c, s) in pools:
            if parent_match(t, c) and match_sub(t, c, s):
                pools[(c, s)].append(d)
    for (c, s), rows in pools.items():
        print(f"\n===== {c} / {s}: pool {len(rows)} 篇，抽 10 篇")
        for d in random.sample(rows, min(10, len(rows))):
            title = (d.get("title") or "")[:90]
            snip = (d.get("text") or "").replace("\n", " ")[:200]
            print(f"- [{title}] {snip}")

if __name__ == "__main__":
    main()
