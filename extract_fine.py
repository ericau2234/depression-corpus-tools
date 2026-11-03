#!/usr/bin/env python3
"""Level-3 mining: given a parent category + sub-cause, rebuild its hit pool
with the v3 rules (phrase + windowed co-occurrence), mine content phrases
inside the pool, and dump the pool for exemplar extraction.
Usage: extract_fine.py <parent_cat> <sub_name> <out_prefix>"""
import json, os, re, sys
from collections import Counter
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
try:
    import ahocorasick
except ImportError:
    sys.path.insert(0, os.path.join(BASE, "pylibs")); import ahocorasick
_hdr = open(os.path.join(BASE, "classify_all.py")).read().split("def run")[0]
exec(_hdr)

CAT, SUB, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
_raw = json.load(open(os.path.join(BASE, "sub_dicts.json"), encoding="utf-8"))
SPEC = _raw["spec"] if "spec" in _raw else _raw
WIN = _raw.get("window_chars", 150)

def build(mapping):
    A = ahocorasick.Automaton()
    for tag, words in mapping.items():
        for w in words:
            wl = w.lower()
            if wl in A: A.get(wl).add(tag)
            else: A.add_word(wl, {tag})
    A.make_automaton(); return A

parentA = build({CAT: EN[CAT]})
s = SPEC[CAT][SUB]
mapping = {}
if s.get("P"): mapping["HIT"] = s["P"]
for ga, gb in s.get("C") or []:
    mapping["\x00A"] = ga; mapping["\x00B"] = gb
subA = build(mapping)

STOP = set("""i'm im ive id ill you're youre he's shes it's its we're theyre don't dont can't cant won't wont didn't didnt doesn't doesnt isn't isnt aren't arent wasn't wasnt weren't werent haven't havent hasn't hasnt hadn't couldnt couldn't shouldnt shouldn't wouldnt wouldn't lets let's thats that's whats there's heres dont im gonna wanna gotta aint aint yeah yes no ok okay like just really very much many get got getting go going gone went come came know knew think thought feel feels felt feeling make made take took see saw say said tell told way even still back now one two three first time times day days week weeks month months year years today night last long life people person someone anyone everyone something anything nothing everything thing things lot bit kind sort part point case fact hand head eyes eye face place world home work job school money problem problems help need want wanted try tried trying keep keeps look looks looking looked seem seems seemed tell around away towards upon among within without across behind beyond plus except per via toward onto also however therefore thus hence meanwhile instead otherwise besides furthermore although though since unless whether either neither both each every any some none more most other others another same such own too so as at by for from in into of off on out over to under up with about after before between through during against along following behind i'm""".split())
WORD = re.compile(r"[a-z][a-z']{2,}")

def toks(t):
    return [w for w in WORD.findall(t) if w not in STOP and not w.startswith("'")]

def main():
    pool = []
    p = os.path.join(BASE, "data_clean", "reddit_clean.jsonl")
    for l in open(p, encoding="utf-8"):
        try: d = json.loads(l)
        except Exception: continue
        if (d.get("chars") or len(d.get("text") or "")) < 200: continue
        t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
        if not any(True for _ in parentA.iter(t)): continue
        tags = set(); pa, pb = [], []
        for e, v in subA.iter(t):
            tags |= v
            if "\x00A" in v: pa.append(e)
            if "\x00B" in v: pb.append(e)
        hit = "HIT" in tags
        if not hit and pa and pb:
            pa.sort(); pb.sort()
            i = j = 0
            while i < len(pa) and j < len(pb):
                if abs(pa[i] - pb[j]) <= WIN: hit = True; break
                if pa[i] < pb[j]: i += 1
                else: j += 1
        if hit: pool.append(d)
    print(f"POOL {CAT}/{SUB}: {len(pool)}")
    with open(os.path.join(BASE, OUT + "_pool.jsonl"), "w", encoding="utf-8") as f:
        for d in pool: f.write(json.dumps(d, ensure_ascii=False) + "\n")
    bg, tg = Counter(), Counter()
    for d in pool:
        tk = toks(((d.get("title") or "") + " " + (d.get("text") or "")).lower())
        bg.update(zip(tk, tk[1:])); tg.update(zip(tk, tk[1:], tk[2:]))
    print("BIGRAMS:", ", ".join(f"{' '.join(k)}:{v}" for k, v in bg.most_common(120) if v >= 20))
    print("TRIGRAMS:", ", ".join(f"{' '.join(k)}:{v}" for k, v in tg.most_common(120) if v >= 15))

if __name__ == "__main__":
    main()
