#!/usr/bin/env python3
"""Sub-cause classification v3: v2 + WINDOWED co-occurrence (A/B terms must appear within 150 chars, not anywhere in the post) + phrase-only child-loss. v2 spot-check showed whole-post co-occurrence precision too low.
Two match modes per sub-cause:
  P = phrase list (substring)
  C = co-occurrence: any term from group A AND any term from group B in text.
Percentages: per 100 posts in the PARENT category. Reddit posts >=200 chars."""
import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
try:
    import ahocorasick
except ImportError:
    sys.path.insert(0, os.path.join(BASE, "pylibs")); import ahocorasick
_hdr = open(os.path.join(BASE, "classify_all.py")).read().split("def run")[0]
exec(_hdr)
sys.path.insert(0, BASE)
from classify_sub import SUBS as SUBS_V1

MOM = ["mom", "mother", "mum", "mama"]
DAD = ["dad", "father", "papa"]
PARENTS = MOM + DAD + ["parents", "stepdad", "stepmom", "stepfather", "stepmother"]
KIN = PARENTS + ["brother", "sister", "grandma", "grandpa", "grandmother", "grandfather", "wife", "husband", "son", "daughter", "uncle", "aunt", "cousin"]
DIED = ["died", "passed away", "funeral", "buried", "death of", "killed himself", "killed herself"]  # v2.1: bare "dead"/"death"/"suicide" removed (idiom + poster-own-ideation false positives)

# v2 additions/overrides: cat -> sub -> {"P": [...], "C": [(A,B), ...]}
V2 = {
 "家庭/父母": {
  "家暴/父母冲突": {"P": SUBS_V1["家庭/父母"]["家暴/父母冲突"],
    "C": [(PARENTS, ["hit me", "hitting", "beat me", "beating", "yelled", "yelling", "screamed", "screaming", "threw", "punched", "slapped", "fighting", "fought", "argument every", "abusive", "violent", "drunk", "alcoholic", "alcohol problem", "rage"]) ]},
  "父母控制/高压": {"P": SUBS_V1["家庭/父母"]["父母控制/高压"] + ["strict mom", "strict dad", "strict mother", "strict father", "my parents won't let", "my mom won't let", "my dad won't let", "not allowed to", "grounded me"],
    "C": [(PARENTS, ["control", "controlling", "won't let me", "wouldn't let me", "not allowed", "forbade", "forced me to", "made me quit", "checks my phone", "tracks my"])]},
  "冷漠/忽视": {"P": SUBS_V1["家庭/父母"]["冷漠/忽视"] + ["never there for me", "emotionally distant", "never showed affection", "love was conditional"],
    "C": [(PARENTS, ["never loved", "didn't love", "never cared", "didn't care about me", "ignored me", "neglect", "absent", "never hugged", "never proud"])]},
  "父母离异/缺位": {"P": SUBS_V1["家庭/父母"]["父母离异/缺位"],
    "C": [(PARENTS, ["divorced", "divorce", "left us", "left when", "walked out", "never around", "wasn't there", "single parent"])]},
  "期望/比较压力": {"P": SUBS_V1["家庭/父母"]["期望/比较压力"],
    "C": [(PARENTS, ["expectations", "expected me", "disappointed", "disappointment", "pressure to", "compared", "never good enough", "proud of me"])]},
  "照顾患病家人": {"P": SUBS_V1["家庭/父母"]["照顾患病家人"] + ["taking care of my", "care for my mom", "care for my dad", "mom has dementia", "dad has dementia", "mom's cancer", "dad's cancer", "mom is sick", "dad is sick"],
    "C": [(PARENTS, ["taking care of", "caregiver", "dementia", "alzheimer", "terminally ill", "bedridden"])]},
  "兄弟姐妹问题": {"P": ["my sister is", "my brother is", "sister has depression", "brother has depression", "sibling rivalry", "golden child", "my sister hates", "my brother hates"],
    "C": [(["brother", "sister", "sibling"], ["abusive", "toxic", "bully", "bullied me", "jealous", "fights", "fighting", "hate each other"])]},
 },
 "经济窘迫(严)": {
  "债务(非学贷)": {"P": ["in debt", "credit card debt", "credit cards debt", "card debt", "owe money", "owe $", "debt collectors", "bankruptcy", "欠债", "网贷", "负债"],
    "C": [(["debt", "owe", "loans"], ["credit card", "collectors", "bankrupt", "payments", "paying off"])]},
  "学生贷款": {"P": ["student loan", "student loans", "student debt", "sallie mae", "navient", "学贷"],
    "C": []},
  "房租/住房/房贷": {"P": SUBS_V1["经济窘迫(严)"]["房租/住房/房贷"] + ["pay rent", "paying rent", "rent is", "rent due", "behind on rent", "can't pay my rent", "cannot pay my rent"],
    "C": [(["rent", "landlord", "apartment", "mortgage", "eviction"], ["can't pay", "cannot pay", "couldn't pay", "behind", "due", "raised", "evicted", "kicked out"])]},
  "账单/生活费": {"P": ["pay bills", "paying bills", "can't pay my bills", "utility bills", "electric bill", "phone bill", "水电费", "生活费"],
    "C": [(["bills", "utilities"], ["can't pay", "cannot pay", "behind", "piling up", "overdue"])]},
  "看不起病/药费": {"P": SUBS_V1["经济窘迫(严)"]["看不起病/药费"],
    "C": [(["afford"], ["therapy", "therapist", "medication", "meds", "doctor", "treatment", "insurance", "hospital"])]},
  "没收入/失业断粮": {"P": SUBS_V1["经济窘迫(严)"]["没收入/失业断粮"] + ["no job", "no savings", "broke", "bank account is empty", "overdraft"],
    "C": [(["no money", "no income", "no savings", "broke"], ["food", "eat", "rent", "bills", "starving"])]},
  "低薪贫困": {"P": SUBS_V1["经济窘迫(严)"]["低薪贫困"], "C": []},
 },
 "丧亲/丧失": {
  "丧母": {"P": ["lost my mom", "lost my mother", "my mom died", "my mother died", "mom passed away", "mother passed away", "妈妈去世", "母亲过世"],
    "C": [(MOM, DIED)]},
  "丧父": {"P": ["lost my dad", "lost my father", "my dad died", "my father died", "dad passed away", "father passed away", "爸爸去世", "父亲过世"],
    "C": [(DAD, DIED)]},
  "丧兄弟姐妹": {"P": ["lost my brother", "lost my sister", "my brother died", "my sister died"],
    "C": [(["brother", "sister"], DIED)]},
  "丧偶": {"P": SUBS_V1["丧亲/丧失"]["丧偶"], "C": [(["wife", "husband", "spouse", "partner"], DIED)]},
  "丧子/流产": {"P": ["lost my baby", "lost my son", "lost my daughter", "lost my child", "lost our baby",
    "my baby died", "my son died", "my daughter died", "my child died", "baby passed away", "son passed away",
    "daughter passed away", "miscarriage", "miscarried", "stillborn", "stillbirth", "lost my pregnancy",
    "lost the baby", "lost my unborn", "流产", "小产", "孩子去世", "儿子去世", "女儿去世"],
    "C": []},
  "丧祖辈": {"P": ["lost my grandma", "lost my grandpa", "grandma died", "grandpa died", "grandmother died", "grandfather died"],
    "C": [(["grandma", "grandpa", "grandmother", "grandfather", "nana"], DIED)]},
  "亲友自杀身亡": {"P": SUBS_V1["丧亲/丧失"]["亲友自杀身亡"],
    "C": [(["friend", "brother", "sister", "cousin", "boyfriend", "girlfriend"], ["suicide", "killed himself", "killed herself", "took his own life", "took her own life", "hanged himself", "overdosed"])]},
  "宠物离世": {"P": SUBS_V1["丧亲/丧失"]["宠物离世"], "C": [(["dog", "cat", "pet"], DIED + ["put down", "euthanized"])]},
 },
 "困住/逃不掉": {
  "困在工作": {"P": ["trapped in my job", "stuck in my job", "stuck at my job", "can't quit my job", "hate my job but"],
    "C": [(["trapped", "stuck"], ["job", "work", "career"])]},
  "困在关系/婚姻": {"P": SUBS_V1["困住/逃不掉"]["关系里走不开"] + ["stuck in my marriage", "stuck in this relationship", "trapped in my marriage"],
    "C": [(["trapped", "stuck"], ["marriage", "relationship", "boyfriend", "girlfriend", "husband", "wife"])]},
  "困在照顾责任": {"P": SUBS_V1["困住/逃不掉"]["照顾责任走不开"],
    "C": [(["trapped", "stuck", "can't leave"], ["kids", "children", "my mom", "my dad", "my mother", "my father", "care for", "taking care"])]},
  "困在住处/小镇": {"P": ["stuck in this town", "trapped in this house", "stuck living with", "can't move out", "stuck at home"],
    "C": [(["trapped", "stuck"], ["town", "city", "house", "home", "parents' house", "living with my parents"])]},
  "困在身体/疾病": {"P": ["trapped in my body", "stuck in bed", "trapped inside my mind"],
    "C": [(["trapped", "stuck"], ["body", "pain", "illness", "bed", "mind", "head"])]},
  "经济上走不开": {"P": SUBS_V1["困住/逃不掉"]["经济上走不开"],
    "C": [(["can't leave", "can't quit", "cannot leave", "cannot quit"], ["money", "afford", "bills", "rent", "debt"])]},
 },
 "童年创伤/虐待": {
  "身体虐待": {"P": SUBS_V1["童年创伤/虐待"]["身体虐待"] + ["hit me with", "beat me with", "belt", "spanked me"],
    "C": [(PARENTS + ["stepdad", "stepfather"], ["beat me", "hit me", "hitting me", "spanked", "whipped", "belt", "bruises"])]},
  "性虐待": {"P": SUBS_V1["童年创伤/虐待"]["性虐待"] + ["touched me", "abused me sexually", "csa"],
    "C": [(["uncle", "cousin", "stepdad", "stepfather", "grandfather", "family friend", "babysitter", "neighbor"], ["molested", "touched me", "sexual", "raped", "abused me"])]},
  "情感虐待/贬低": {"P": SUBS_V1["童年创伤/虐待"]["情感虐待/贬低"] + ["walking on eggshells", "screamed at me", "always yelling"],
    "C": [(PARENTS, ["yelled", "screamed", "called me", "worthless", "stupid", "useless", "blamed me", "silent treatment", "gaslight", "narcissist", "narcissistic"])]},
  "童年忽视": {"P": SUBS_V1["童年创伤/虐待"]["童年忽视"] + ["raised myself", "had to raise myself", "parentified", " latchkey"],
    "C": [(["as a kid", "as a child", "growing up", "childhood"], ["neglected", "left alone", "on my own", "no one cared", "ignored", "abandoned"])]},
  "目睹家暴/家庭破裂": {"P": SUBS_V1["童年创伤/虐待"]["目睹家暴/家庭破裂"] + ["grew up in a house", "household was", "walking on eggshells"],
    "C": [(["growing up", "as a kid", "childhood", "at home"], ["fighting", "violence", "violent", "screaming", "drunk", "alcoholic", "chaos", "chaotic", "unstable"])]},
  "父母酗酒/成瘾": {"P": ["alcoholic father", "alcoholic mother", "alcoholic dad", "alcoholic mom", "dad was an alcoholic", "mom was an alcoholic", "parent's drinking", "drug addict father", "drug addict mother"],
    "C": [(PARENTS, ["alcoholic", "drinking problem", "addict", "addiction", "drunk every", "rehab"])]},
 },
 "孤独/孤立": {
  "没朋友": {"P": SUBS_V1["孤独/孤立"]["没朋友"], "C": []},
  "自我隔离/退缩": {"P": ["isolated myself", "isolate myself", "isolating myself", "withdrawn", "stopped talking to everyone", "cut everyone off", "pushed everyone away", "自我隔离", "断了联系"],
    "C": [(["isolated", "isolating", "withdrawn"], ["myself", "from everyone", "from people"])]},
  "独居/迁居隔离": {"P": SUBS_V1["孤独/孤立"]["独居/迁居隔离"], "C": []},
  "格格不入/被排斥": {"P": SUBS_V1["孤独/孤立"]["格格不入/被排斥"] + ["no one invites me", "never invited", "always the outsider", "feel invisible", "nobody notices"],
    "C": []},
  "社交焦虑导致": {"P": ["social anxiety", "too anxious to talk", "scared to talk to people", "can't talk to people", "afraid of people", "社交焦虑", "社恐"],
    "C": []},
 },
 "疾病/疼痛": {
  "慢性疼痛": {"P": SUBS_V1["疾病/疼痛"]["慢性疼痛"] + ["chronic pain", "nerve pain", "joint pain", "pain every day", "constant pain"], "C": []},
  "癌症": {"P": ["cancer", "chemo", "chemotherapy", "tumor", "tumour", "oncolog", "癌症", "化疗"], "C": []},
  "残障/行动受限": {"P": SUBS_V1["疾病/疼痛"]["残障/行动受限"], "C": []},
  "长期慢性病": {"P": SUBS_V1["疾病/疼痛"]["长期慢性病"] + ["chronic illness", "health problems", "health issues", "auto immune"], "C": []},
  "确诊抑郁/精神病本身": {"P": ["diagnosed with depression", "diagnosed depression", "major depressive disorder", "mdd", "depressive disorder", "diagnosed with mdd", "临床抑郁", "重度抑郁"], "C": []},
 },
 "睡眠": {
  "入睡困难/失眠": {"P": ["insomnia", "can't fall asleep", "cannot fall asleep", "trouble falling asleep", "can't sleep", "cannot sleep", "sleepless", "失眠", "睡不着"], "C": []},
  "睡眠时间不足": {"P": ["hours of sleep", "hours sleep", "barely sleep", "sleep deprivation", "sleep deprived", "no sleep", "睡眠不足"], "C": []},
  "作息紊乱/夜班": {"P": ["sleep schedule", "night shift", "sleep cycle", "circadian", "sleep pattern", "夜班", "日夜颠倒"], "C": []},
  "药物助眠/药物影响": {"P": ["sleeping pills", "sleep aids", "melatonin", "安眠药", "助眠"], "C": []},
  "噩梦": {"P": ["nightmares", "night terrors", "bad dreams", "噩梦"], "C": []},
 },
 "产后": {
  "产后抑郁(自述)": {"P": ["postpartum depression", "postnatal depression", "ppd", "产后抑郁"], "C": []},
  "分娩后发病(时间)": {"P": ["after giving birth", "after my baby was born", "since giving birth", "months postpartum", "weeks postpartum", "after childbirth", "生完孩子"], "C": []},
  "育儿压力/婴儿睡眠": {"P": ["baby won't sleep", "newborn", "breastfeeding", "pumping", "baby cries", "带娃", "喂奶", "宝宝不睡"], "C": []},
 },
}

def build_automaton(mapping):
    A = ahocorasick.Automaton()
    for tag, words in mapping.items():
        for w in words:
            wl = w.lower()
            if wl in A: A.get(wl).add(tag)
            else: A.add_word(wl, {tag})
    A.make_automaton()
    return A

def main():
    parentA = build_automaton({k: v for k, v in EN.items()})
    # merged spec: start from V2, fall back to v1 phrase-only for cats not overridden
    spec = {}
    for cat, subs in SUBS_V1.items():
        spec[cat] = {}
        for sname, ws in subs.items():
            spec[cat][sname] = {"P": ws, "C": []}
    for cat, subs in V2.items():
        spec.setdefault(cat, {})
        for sname, s in subs.items():
            spec[cat][sname] = s
    # phrase automaton per cat: tag = sub name; co-occurrence groups also via phrase hits on group terms
    cat_phraseA = {}
    cat_co = {}
    for cat, subs in spec.items():
        mapping = {}
        co = []
        for sname, s in subs.items():
            if s["P"]: mapping[sname] = s["P"]
            for (ga, gb) in s["C"]:
                co.append((sname, ga, gb))
                mapping[f"\x00A:{sname}"] = ga
                mapping[f"\x00B:{sname}"] = gb
        cat_phraseA[cat] = build_automaton(mapping) if mapping else None
        cat_co[cat] = co
    # archive the merged dictionary spec for reuse/versioning
    try:
        json.dump({"window_chars": 150, "spec": spec}, open(os.path.join(BASE, "sub_dicts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as e:
        print("spec dump failed", e)
    from collections import Counter
    counts = {cat: Counter() for cat in spec}
    totals = Counter()
    covered = {cat: set() for cat in spec}
    p = os.path.join(BASE, "data_clean", "reddit_clean.jsonl")
    for l in open(p, encoding="utf-8"):
        try: d = json.loads(l)
        except Exception: continue
        if (d.get("chars") or len(d.get("text") or "")) < 200: continue
        t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
        parents = set()
        for _e, v in parentA.iter(t): parents |= v
        for cat in parents:
            if cat not in spec: continue
            totals[cat] += 1
            A = cat_phraseA[cat]
            if A is None: continue
            tags = set()
            posA, posB = {}, {}
            for _e, v in A.iter(t):
                tags |= v
                for tg in v:
                    if tg.startswith("\x00A:"): posA.setdefault(tg[3:], []).append(_e)
                    elif tg.startswith("\x00B:"): posB.setdefault(tg[3:], []).append(_e)
            hits = {x for x in tags if not x.startswith("\x00")}
            W = 150
            for (sname, ga, gb) in cat_co[cat]:
                la, lb = posA.get(sname), posB.get(sname)
                if la and lb:
                    la.sort(); lb.sort()
                    i = j = 0; ok = False
                    while i < len(la) and j < len(lb):
                        d = la[i] - lb[j]
                        if abs(d) <= W: ok = True; break
                        if d < 0: i += 1
                        else: j += 1
                    if ok: hits.add(sname)
            for h in hits: counts[cat][h] += 1
            covered[cat] |= set()
    try:
        json.dump({"totals": dict(totals), "counts": {c: dict(counts[c]) for c in counts}},
                  open(os.path.join(BASE, "sub_results_v3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as e:
        print("results dump failed", e)
    for cat in spec:
        tot = totals[cat]
        if not tot: continue
        cov = sum(1 for _ in [0])
        print(f"\n### {cat}（母类 {tot} 篇，每 100 篇该类帖中，v2）")
        for sname, c in counts[cat].most_common():
            print(f"  {sname}: {round(100*c/tot,1)}")

if __name__ == "__main__":
    main()
