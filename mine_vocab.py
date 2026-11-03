#!/usr/bin/env python3
"""Mine per-category vocabulary from the corpus itself: for posts classified
into each parent category, count content words + bigrams. Output top lists
used to expand the sub-cause dictionaries with real corpus phrasing."""
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

STOP = set("""the a an and or but if then else when at by for with about against between into through during before after above below to from up down in out on off over under again further once here there all any both each few more most other some such no nor not only own same so than too very can will just don should now i me my we our you your he him his she her it its they them this that these those am is are was were be been being have has had having do does did doing would could shall may might must i'm i've i'll i'd you you're we've they're don't doesn't didn't can't won't isn't aren't wasn't weren't hasn't haven't hadn't doesn't get got getting really like one two even still back way well much many feel feeling felt life time people know think going go went come came make made see saw look get day year years old something anything nothing everything someone anyone everyone thing things way ways lot bit kind sort part point case fact hand part place world week month today night morning home work job school family mom dad mother father parents friend friends help need want wanted take took give gave said say says told tell ask asked try tried keep kept let lets put set end following found find sure mean meant rather quite also almost enough nearly mostly especially probably actually finally already yet ever never always often sometimes though although since unless until per via upon within without across behind beyond plus except amid toward towards onto yeah yes okay ok hi hello thanks thank please sorry maybe literally basically honestly seriously kinda sorta gonna wanna gotta lot stuff guy guys girl girls man woman people person someone somebody read reading post posts subreddit edit update throwaway account using deleted removed body text long story short tldr vent rant advice support listen hear sharing share experience experiences similar anyone else else's"""
.split())
TOK = re.compile(r"[a-z][a-z']{2,}")
CAP = 60000

def main():
    A = ahocorasick.Automaton()
    for k, ws in EN.items():
        for w in ws:
            wl = w.lower()
            if wl in A: A.get(wl).add(k)
            else: A.add_word(wl, {k})
    A.make_automaton()
    uni = {k: Counter() for k in EN}
    bi = {k: Counter() for k in EN}
    ncat = Counter()
    p = os.path.join(BASE, "data_clean", "reddit_clean.jsonl")
    for l in open(p, encoding="utf-8"):
        try: d = json.loads(l)
        except Exception: continue
        if (d.get("chars") or len(d.get("text") or "")) < 200: continue
        t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
        cats = set()
        for _e, v in A.iter(t): cats |= v
        toks = [w for w in TOK.findall(t) if w not in STOP]
        for c in cats:
            if ncat[c] >= CAP: continue
            ncat[c] += 1
            uni[c].update(toks)
            bi[c].update(a + " " + b for a, b in zip(toks, toks[1:]))
    for c in EN:
        print(f"\n### {c} (sampled {ncat[c]})")
        print("WORDS:", ", ".join(f"{w}:{n}" for w, n in uni[c].most_common(70)))
        print("BIGRAMS:", ", ".join(f"{w}:{n}" for w, n in bi[c].most_common(50)))

if __name__ == "__main__":
    main()
