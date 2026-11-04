#!/usr/bin/env python3
"""Batch-3 helper: sample posts from a fine pool + mine content n-grams with a
real stopword list (extract_fine's internal miner is broken).
Usage: sample_pool.py <pool.jsonl> [n_samples]"""
import json, os, random, re, sys
from collections import Counter
BASE = os.path.dirname(os.path.abspath(__file__))
pool = [json.loads(l) for l in open(os.path.join(BASE, sys.argv[1]), encoding="utf-8")]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
random.seed(42)
print(f"POOL {sys.argv[1]} n={len(pool)}")
for d in random.sample(pool, min(n, len(pool))):
    t = ((d.get("title") or "") + " || " + (d.get("text") or "")).replace("\n", " ")
    print("-", t[:420])
STOP = set("""the a an and or but if then else when at by for with about against between into through during before after above below to from up down in out on off over under again further once here there all any both each few more most other some such no nor not only own same so than too very can will just don should now i me my we our you your he him his she her it its they them their this that these those am is are was were be been being have has had having do does did doing would could shall may might must i'm i've i'll i'd you're you've you'll you'd he's she's it's we're they're i am you are he is she is it is we are they are isn't aren't wasn't weren't hasn't haven't hadn't doesn't didn't won't wouldn't shan't shouldn't can't cannot couldn't mustn't let's that's who's whats what's here's there's when's where's why's how's s t d ll re ve m ain one two get got go going went come came make made take took see saw know knew think thought feel felt feels feeling want wanted need needs like really much many way even still back now just also ever never always often sometimes get gets getting thing things stuff lot bit kind sort part day days time year years week weeks month months today night morning life people person someone anyone everyone something anything nothing everything way ways right left first last new old good bad better best long little big great sure able keep keeps kept put say said tell told look looks looking seem seems seemed try tried trying let lets let’s don’t i’m i've cant can't wont won't didnt didn't doesnt doesn't isn isn’t aren aren't wasn wasn't weren weren't havent hasn't hadn couldn couldn't shouldn shouldn't wouldn wouldn't gonna wanna gotta yeah yes ok okay well actually basically literally probably maybe perhaps though although since unless whether either neither per via towards onto upon among within without across behind beyond plus except following during against along around away toward""".split())
WORD = re.compile(r"[a-z][a-z']{2,}")
def toks(t):
    return [w for w in WORD.findall(t) if w not in STOP and not w.startswith("'") and len(w) > 2]
bg, tg, ug = Counter(), Counter(), Counter()
for d in pool:
    tk = toks(((d.get("title") or "") + " " + (d.get("text") or "")).lower())
    ug.update(tk); bg.update(zip(tk, tk[1:])); tg.update(zip(tk, tk[1:], tk[2:]))
print("WORDS:", ", ".join(f"{k}:{v}" for k, v in ug.most_common(60) if v >= 30))
print("BIGRAMS:", ", ".join(f"{' '.join(k)}:{v}" for k, v in bg.most_common(100) if v >= 25))
print("TRIGRAMS:", ", ".join(f"{' '.join(k)}:{v}" for k, v in tg.most_common(100) if v >= 18))
