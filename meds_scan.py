# -*- coding: utf-8 -*-
"""Meds & side-effects branch scout: full scan of the 5 English clean files.
- Drug mentions: posts mentioning each drug (brand+generic merged), per platform.
- Side effects / effectiveness: phrase occurrence attributed to a drug when a mention
  of that drug is within +/-200 chars (span gap <= 200). Post-level, multi-label.
- Exemplars: up to 3 verbatim snippets per (drug, side-effect) pair.
Writes meds_fine.json and prints summary tables."""
import sys, json, re, collections, time
sys.path.insert(0, 'pylibs')
sys.path.insert(0, '.')
import ahocorasick
from meds_dict import DRUGS, SIDE_EFFECTS, EFFECTIVENESS

FILES = {
    "patient": "data_clean/patient_clean.jsonl",
    "reddit": "data_clean/reddit_clean.jsonl",
    "beyondblue": "data_clean/beyondblue_clean.jsonl",
    "mhf": "data_clean/mhf_clean.jsonl",
    "livejournal": "data_clean/livejournal_clean.jsonl",
}
WIN = 200
SE_MIN_DRUG_MENTIONS = 500      # full SE/effectiveness analysis threshold
EXEMPLAR_PAIR_MIN = 30          # keep exemplars for pairs with >= this many posts
t0 = time.time()

def build(mapping):
    A = ahocorasick.Automaton()
    for pat, val in mapping.items():
        A.add_word(pat, (pat, val))
    A.make_automaton()
    return A

alias2drug = {}
for drug, (cls, aliases) in DRUGS.items():
    for a in aliases:
        alias2drug[a] = drug
DA = build(alias2drug)

se_map = {}
for cat, phrases in SIDE_EFFECTS.items():
    for p in phrases:
        se_map[p] = cat
SEA = build(se_map)

eff_map = {}
for cat, phrases in EFFECTIVENESS.items():
    for p in phrases:
        eff_map[p] = cat
EFFA = build(eff_map)

def find_spans(A, low):
    """yield (start, end, value) with alphanumeric boundary check."""
    out = []
    n = len(low)
    for e, (pat, val) in A.iter(low):
        s = e - len(pat) + 1
        if s > 0 and low[s - 1].isalnum():
            continue
        if e + 1 < n and low[e + 1].isalnum():
            continue
        out.append((s, e + 1, val))
    return out

def gap(a_s, a_e, b_s, b_e):
    if a_e <= b_s:
        return b_s - a_e
    if b_e <= a_s:
        return a_s - b_e
    return 0

WS = re.compile(r"\s+")
def snippet(orig, low, s, e, drug_spans_flat):
    lo = max(0, s - 260); hi = min(len(orig), e + 260)
    sn = WS.sub(' ', orig[lo:hi]).strip()
    return sn[:460]

# aggregates
plat = {}                      # platform -> dict of counters
drug_posts = collections.defaultdict(collections.Counter)   # drug -> platform -> posts
drug_occs = collections.Counter()                            # drug -> raw occurrences
drug_codrug = collections.Counter()                          # drug -> posts also mentioning another drug
se_pair_posts = collections.defaultdict(collections.Counter) # drug -> se_cat -> posts
eff_pair_posts = collections.defaultdict(collections.Counter)
exemplars = collections.defaultdict(list)                    # (drug, se_cat) -> [snippets]
se_span_stats = collections.Counter()   # total SE spans in med posts / attributed / multi-attributed
class_posts = collections.defaultdict(collections.Counter)  # class -> platform -> posts (multi-count)

for platform, path in FILES.items():
    P = collections.Counter()
    plat[platform] = P
    with open(path, encoding='utf-8') as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                P['bad_json'] += 1
                continue
            P['posts'] += 1
            text_orig = (d.get('title') or '') + ' ' + (d.get('text') or '')
            chars = d.get('chars')
            if chars is None:
                chars = len(d.get('text') or '')
            is_long = chars >= 200
            if is_long:
                P['long_posts'] += 1
            low = text_orig.lower()
            dmatch = find_spans(DA, low)
            if not dmatch:
                continue
            P['med_posts'] += 1
            if is_long:
                P['med_long_posts'] += 1
            spans_by_drug = collections.defaultdict(list)
            for s, e, drug in dmatch:
                spans_by_drug[drug].append((s, e))
                drug_occs[drug] += 1
            drugs_here = list(spans_by_drug.keys())
            for drug in drugs_here:
                drug_posts[drug][platform] += 1
                class_posts[DRUGS[drug][0]][platform] += 1
                if len(drugs_here) > 1:
                    drug_codrug[drug] += 1
            # side effects
            se_match = find_spans(SEA, low)
            if se_match:
                flat = [(s, e, dr) for dr, ss in spans_by_drug.items() for (s, e) in ss]
                pair_span = {}   # (drug, cat) -> first attributed SE span, THIS post only
                for s, e, cat in se_match:
                    se_span_stats['se_spans_in_med_posts'] += 1
                    near = set()
                    for ds, de, dr in flat:
                        if gap(s, e, ds, de) <= WIN:
                            near.add(dr)
                    if near:
                        se_span_stats['se_spans_attributed'] += 1
                        if len(near) > 1:
                            se_span_stats['se_spans_multi_attributed'] += 1
                        for dr in near:
                            if (dr, cat) not in pair_span:
                                pair_span[(dr, cat)] = (s, e)
                    else:
                        se_span_stats['se_spans_unattributed'] += 1
                for (dr, cat), (s, e) in pair_span.items():
                    se_pair_posts[dr][cat] += 1
                    key = (dr, cat)
                    if len(exemplars[key]) < 3:
                        sn = snippet(text_orig, low, s, e, flat)
                        if sn not in exemplars[key]:
                            exemplars[key].append(sn)
            # effectiveness
            eff_match = find_spans(EFFA, low)
            if eff_match:
                flat = [(s, e, dr) for dr, ss in spans_by_drug.items() for (s, e) in ss]
                pairset = set()
                for s, e, cat in eff_match:
                    for ds, de, dr in flat:
                        if gap(s, e, ds, de) <= WIN:
                            pairset.add((dr, cat))
                for dr, cat in pairset:
                    eff_pair_posts[dr][cat] += 1
    print(f"[{platform}] done {P['posts']} posts, {P['med_posts']} med posts, {time.time()-t0:.0f}s", flush=True)

# ---------------- assemble output ----------------
drugs_out = {}
for drug, (cls, aliases) in DRUGS.items():
    total = sum(drug_posts[drug].values())
    entry = {
        "class": cls,
        "aliases": aliases,
        "mention_posts_total": total,
        "mention_posts_by_platform": dict(drug_posts[drug]),
        "mention_occurrences_total": drug_occs[drug],
        "codrug_posts": drug_codrug[drug],
        "codrug_share_pct": round(100.0 * drug_codrug[drug] / total, 1) if total else 0.0,
    }
    if total >= SE_MIN_DRUG_MENTIONS:
        se_out = {}
        for cat, c in se_pair_posts[drug].most_common():
            item = {"posts": c, "per100_drug_posts": round(100.0 * c / total, 1)}
            ex = exemplars.get((drug, cat))
            if ex and c >= EXEMPLAR_PAIR_MIN:
                item["exemplars"] = ex
            se_out[cat] = item
        entry["side_effects"] = se_out
        eff_out = {}
        for cat, c in eff_pair_posts[drug].most_common():
            eff_out[cat] = {"posts": c, "per100_drug_posts": round(100.0 * c / total, 1)}
        entry["effectiveness"] = eff_out
    drugs_out[drug] = entry

platforms_out = {}
for platform, P in plat.items():
    platforms_out[platform] = {
        "posts": P['posts'],
        "long_posts_ge200c": P['long_posts'],
        "med_posts_any_len": P['med_posts'],
        "med_posts_long": P['med_long_posts'],
        "med_share_of_long_pct": round(100.0 * P['med_long_posts'] / P['long_posts'], 1) if P['long_posts'] else 0.0,
        "med_share_of_all_pct": round(100.0 * P['med_posts'] / P['posts'], 1) if P['posts'] else 0.0,
    }

overall_se = collections.Counter()
for drug, ctr in se_pair_posts.items():
    if sum(drug_posts[drug].values()) >= SE_MIN_DRUG_MENTIONS:
        for cat, c in ctr.items():
            overall_se[cat] += c

out = {
    "generated_by": "meds_scan.py",
    "caliber": {
        "mention": "posts mentioning the drug (brand+generic merged, word-boundary match); occurrences counted separately",
        "long_post": "chars >= 200 (clean-file 'chars' field)",
        "side_effect_attribution": f"side-effect phrase within +/-{WIN} chars (span gap) of a mention of that drug in the same post; post-level, multi-label",
        "effectiveness": f"explicit phrase within +/-{WIN} chars of a drug mention; phrase-count lower bounds",
        "se_analysis_threshold": f"drugs with >= {SE_MIN_DRUG_MENTIONS} mention-posts corpus-wide",
    },
    "platforms": platforms_out,
    "classes": {cls: dict(ctr) for cls, ctr in class_posts.items()},
    "se_span_stats": dict(se_span_stats),
    "overall_side_effects_top_drugs_only": dict(overall_se.most_common()),
    "drugs": drugs_out,
}
with open('meds_fine.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# ---------------- print summary ----------------
tot_posts = sum(p['posts'] for p in platforms_out.values())
tot_long = sum(p['long_posts_ge200c'] for p in platforms_out.values())
tot_med_long = sum(p['med_posts_long'] for p in platforms_out.values())
print("\n=== PLATFORMS ===")
for name, p in platforms_out.items():
    print(f"{name:12s} posts {p['posts']:8d}  long {p['long_posts_ge200c']:8d}  med(long) {p['med_posts_long']:7d}  med% of long {p['med_share_of_long_pct']}%")
print(f"TOTAL posts {tot_posts}  long {tot_long}  med(long) {tot_med_long}  ({100.0*tot_med_long/tot_long:.1f}% of long)")
print("\n=== SE SPAN STATS ===", dict(se_span_stats))
print("\n=== TOP 30 DRUGS (mention posts) ===")
for drug, e in sorted(drugs_out.items(), key=lambda kv: -kv[1]['mention_posts_total'])[:30]:
    print(f"{e['mention_posts_total']:8d}  {drug:28s} {e['class']:26s} codrug% {e['codrug_share_pct']}")
print("\n=== OVERALL SIDE EFFECTS (posts, top drugs only, multi-label sums) ===")
for cat, c in overall_se.most_common():
    print(f"{c:8d}  {cat}")
print(f"\nelapsed {time.time()-t0:.0f}s -> meds_fine.json")
