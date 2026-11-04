# -*- coding: utf-8 -*-
"""Mine frequent words/bigrams inside +/-200 char windows around drug mentions.
Sources: patient_clean (full) + reddit_clean (first 200k posts)."""
import sys, json, re, collections
sys.path.insert(0, 'pylibs')
sys.path.insert(0, '.')
import ahocorasick
from meds_dict import DRUGS

def build_automaton(alias2drug):
    A = ahocorasick.Automaton()
    for alias, drug in alias2drug.items():
        A.add_word(alias, (alias, drug))
    A.make_automaton()
    return A

alias2drug = {}
for drug, (cls, aliases) in DRUGS.items():
    for a in aliases:
        alias2drug[a] = drug
DA = build_automaton(alias2drug)

STOP = set("""the a an and or but if then else for to of in on at by with from as is was are were be been being
have has had do does did done i you he she it we they me him her us them my your his its our their mine yours
this that these those am an the and or but so because just very really much many more most other some any no not
only own same than too can will would should could may might must shall when where which who whom what how all
about into through during before after above below between out off over under again further once here there
what's im i've i'll i'd don't cant can't won't didnt didn't isnt isn't wasnt wasn't get got getting go going went
come came take took taking make made see saw feel felt feeling feels like one two also back well now day days week
weeks month months year years time first since still even ever never always often sometimes would could said say
says doctor doctors gp psychiatrist therapist hospital treatment therapy medication medications medicine meds drug
drugs dose mg daily morning night week weeks started start starting took taking take stopped stop stopping
tablet tablets pill pills capsule prescription prescribed antidepressant antidepressants depression anxiety anxious
depressed disorder mental health illness symptoms symptom problem problems experience anyone anyone else help
really lot bit things thing way ways life people person someone something everything nothing anything much many
""".split())

TOK = re.compile(r"[a-z][a-z'\-]{1,30}")

def windows(text_low, spans, w=200):
    out = []
    for s, e in spans:
        out.append(text_low[max(0, s - w): e + w])
    return out

uni = collections.Counter()
bi = collections.Counter()
n_posts = 0
n_med_posts = 0

def scan(path, limit=None):
    global n_posts, n_med_posts
    cnt = 0
    with open(path, encoding='utf-8') as f:
        for line in f:
            if limit and cnt >= limit:
                break
            cnt += 1
            n_posts += 1
            try:
                d = json.loads(line)
            except Exception:
                continue
            text = (d.get('title') or '') + ' ' + (d.get('text') or '')
            low = text.lower()
            spans = []
            for e, (alias, drug) in DA.iter(low):
                s = e - len(alias) + 1
                before = low[s - 1] if s > 0 else ' '
                after = low[e + 1] if e + 1 < len(low) else ' '
                if before.isalnum() or after.isalnum():
                    continue
                spans.append((s, e + 1))
            if not spans:
                continue
            n_med_posts += 1
            seen_uni = set(); seen_bi = set()
            for win in windows(low, spans):
                toks = [t.strip("'-") for t in TOK.findall(win)]
                toks = [t for t in toks if t and t not in alias2drug]
                for t in toks:
                    if t not in STOP:
                        seen_uni.add(t)
                for a, b in zip(toks, toks[1:]):
                    bg = a + ' ' + b
                    if a not in STOP or b not in STOP:
                        seen_bi.add(bg)
            for t in seen_uni: uni[t] += 1
            for b in seen_bi: bi[b] += 1

scan('data_clean/patient_clean.jsonl')
scan('data_clean/reddit_clean.jsonl', limit=200000)

print(f"posts scanned: {n_posts}, med posts: {n_med_posts}")
print("\n=== TOP UNIGRAMS (doc freq in drug windows) ===")
for w, c in uni.most_common(160):
    print(f"{c:7d}  {w}")
print("\n=== TOP BIGRAMS ===")
for w, c in bi.most_common(300):
    print(f"{c:7d}  {w}")
