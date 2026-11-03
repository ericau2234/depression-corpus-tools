#!/usr/bin/env python3
"""v2.2 classification (eric's caliber).
Percentages are reported on the CLASSIFIED base (posts hitting >=1 cause
category) as primary, full base alongside. Causes = 13 attribution
categories. Non-cause buckets (symptoms / treatment / adjacent diagnoses /
void / suicidal-no-cause) are reported separately and do not count toward
the classified base. Money: strict (expanded dict), wide (strict union
trapped-with-cause), trace. Non-English Reddit posts are also scanned with
PT/ES and FR dictionaries. Compiled-regex matching (fast).
"""
import json, os, re, sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
_hdr = open(os.path.join(BASE, "classify_all.py")).read().split("def run")[0]
exec(_hdr)  # defines EN, JA, ZH, KO, DE, RU, TRACE_*, classify()

EXTRA_STRICT_EN = ["paycheck to paycheck", "scraping by", "barely getting by", "second job",
                   "two jobs", "laid off", "got fired", "lost my job", "food stamps",
                   "food bank", "minimum wage", "on benefits", "disability payments",
                   "eviction notice", "hours were cut"]
EN2 = {k: list(v) for k, v in EN.items()}
EN2["经济窘迫(严)"] = EN["经济窘迫(严)"] + EXTRA_STRICT_EN

PT_ES = {
 "工作/学业": ["trabalho", "emprego", "faculdade", "escola", "trabajo", "universidad", "escuela", "estudios", "trampo"],
 "家庭/父母": ["mãe", "pai", "família", "madre", "padre", "familia", "meus pais", "mis padres"],
 "亲密关系": ["namorado", "namorada", "relacionamento", "relación", "pareja", "novio", "novia", "casamento", "matrimonio"],
 "孤独/孤立": ["sozinho", "sozinha", "solidão", "soledad", "sin amigos", "sem amigos"],
 "疾病/疼痛": ["doença", "dor crônica", "enfermedad", "dolor crónico", "câncer", "cáncer"],
 "丧亲/丧失": ["morreu", "morte de", "murió", "muerte de", "perdi meu", "perdi minha"],
 "睡眠": ["insônia", "insomnio", "sem dormir", "sin dormir"],
 "童年创伤/虐待": ["infância", "infancia", "abuso"],
 "经济窘迫(严)": ["dinheiro", "dívida", "dividas", "desempregado", "desemprego", "aluguel", "dinero", "deuda", "desempleado", "alquiler", "sem dinheiro", "sin dinero"],
 "遗传/家族史": ["genética", "genetica", "hereditário", "hereditario"],
 "无缘无故": ["sem motivo", "sem razão", "sin motivo", "sin razón", "do nada"],
 "困住/逃不掉": ["preso", "sem saída", "atrapado", "sin salida"],
}
FRD = {
 "工作/学业": ["travail", "boulot", "études", "école", "université", "emploi"],
 "家庭/父母": ["mère", "père", "famille", "parents", "mon père", "ma mère"],
 "亲密关系": ["copain", "copine", "relation", "rupture", "mari", "femme"],
 "孤独/孤立": ["seul", "seule", "solitude", "amis", "personne"],
 "疾病/疼痛": ["maladie", "douleur", "cancer", "malade"],
 "丧亲/丧失": ["mort", "décès", "deuil", "perdu mon", "perdu ma"],
 "睡眠": ["sommeil", "insomnie", "dormir"],
 "童年创伤/虐待": ["enfance", "abus", "traumatisme"],
 "经济窘迫(严)": ["argent", "dette", "dettes", "chômage", "loyer", "pas d'argent", "factures"],
 "遗传/家族史": ["génétique", "héréditaire"],
 "无缘无故": ["sans raison", "sans motif"],
 "困住/逃不掉": ["coincé", "pas d'issue"],
}
NONCAUSE = {
 "症状/感受": ["hate myself", "feel empty", "feeling empty", "numb", "tired of everything", "tired of living",
   "no motivation", "can't feel", "cannot feel", "overthinking", "self-hate", "hating myself"],
 "治疗/药物": ["therapy", "therapist", "medication", "medications", "antidepressant", "antidepressants",
   "withdrawal", "psychiatrist", "zoloft", "sertraline", "prozac", "lexapro", "wellbutrin", "trazodone", "counseling", "cbt"],
 "邻近诊断": ["bpd", "borderline", "ptsd", "ocd", "adhd", "autism", "autistic", "social anxiety",
   "anxiety disorder", "panic attack", "schizophren", "bipolar", "eating disorder", "anorexia"],
 "虚无": ["no purpose", "no meaning", "meaningless", "what's the point", "whats the point",
   "nothing matters", "no dreams", "no future"],
 "想死(未述因)": ["kill myself", "kms", "end it all", "want to die", "wanna die", "suicidal",
   "end my life", "don't want to live", "dont want to live"],
}
CAUSES = ["工作/学业", "家庭/父母", "亲密关系", "孤独/孤立", "疾病/疼痛", "童年创伤/虐待",
          "丧亲/丧失", "睡眠", "产后", "无缘无故", "困住/逃不掉", "经济窘迫(严)", "遗传/家族史"]
TRAPPED = ["辞不起", "离不开", "走不了", "逃不掉", "can't quit", "cannot quit", "can't leave",
           "cannot leave", "trapped", "stuck in", "no way out", "can't afford to leave",
           "can't afford to quit", "have to stay", "had to stay"]

def _pat(words, lower):
    ws = [w.lower() if lower else w for w in words if w]
    if not ws: return None
    return re.compile("|".join(re.escape(w) for w in ws))

def loadc(fn, minc):
    p = os.path.join(BASE, "data_clean", fn)
    if not os.path.exists(p): return []
    rows = []
    for l in open(p, encoding="utf-8"):
        try:
            d = json.loads(l)
            if (d.get("chars") or len(d.get("text") or "")) >= minc: rows.append(d)
        except Exception: pass
    return rows

def analyze(name, rows, dicts, trace_words, lower=True):
    try:
        import ahocorasick
    except ImportError:
        sys.path.insert(0, os.path.join(BASE, "pylibs"))
        import ahocorasick
    n = len(rows)
    if not n:
        print(name, "n=0", flush=True); return
    A = ahocorasick.Automaton()
    def add(word, tag):
        w = word.lower() if lower else word
        if not w: return
        if w in A: A.get(w).add(tag)
        else: A.add_word(w, {tag})
    for k in CAUSES:
        for dic in dicts:
            for w in dic.get(k) or []: add(w, k)
    for w in trace_words: add(w, "__trace__")
    for w in TRAPPED: add(w, "__trapped__")
    for k, ws in NONCAUSE.items():
        for w in ws: add(w, "NC:" + k)
    A.make_automaton()
    cause_c, nc_c = Counter(), Counter()
    classified = strict = wide = trace = 0
    for r in rows:
        t = (r.get("title") or "") + " " + (r.get("text") or "")
        if lower: t = t.lower()
        tags = set()
        for _end, val in A.iter(t):
            tags |= val
        hits = tags & set(CAUSES)
        for k in hits: cause_c[k] += 1
        if hits:
            classified += 1
            if "经济窘迫(严)" in hits:
                strict += 1; wide += 1
            elif "__trapped__" in tags and hits & {"工作/学业", "家庭/父母", "亲密关系"}:
                wide += 1
        if "__trace__" in tags: trace += 1
        for tg in tags:
            if tg.startswith("NC:"): nc_c[tg[3:]] += 1
    base = max(1, classified)
    print(f"\n### {name} n={n} 已分类 {classified} ({round(100*classified/n,1)}%)", flush=True)
    for k in CAUSES:
        print(f"  {k}: 全基 {round(100*cause_c[k]/n,1)}% | 已分类基 {round(100*cause_c[k]/base,1)}%", flush=True)
    print(f"  经济宽: 全基 {round(100*wide/n,1)}% | 已分类基 {round(100*wide/base,1)}%", flush=True)
    print(f"  经济痕迹: 全基 {round(100*trace/n,1)}% | 已分类基 {round(100*trace/base,1)}%", flush=True)
    for k, v in nc_c.most_common():
        print(f"  [非因] {k}: {round(100*v/n,1)}%", flush=True)

def main():
    analyze("Reddit帖子", loadc("reddit_clean.jsonl", 200), [EN2, PT_ES, FRD], TRACE_EN2)
    analyze("Reddit评论", loadc("reddit_comments_clean.jsonl", 100), [EN2, PT_ES, FRD], TRACE_EN2)
    analyze("BeyondBlue", loadc("beyondblue_clean.jsonl", 200), [EN2], TRACE_EN2)
    analyze("Patient", loadc("patient_clean.jsonl", 200), [EN2], TRACE_EN2)
    analyze("LiveJournal", loadc("livejournal_clean.jsonl", 200), [EN2], TRACE_EN2)
    analyze("5ch", loadc("fivech_clean.jsonl", 200), [JA], TRACE_JA, lower=False)
    analyze("Threads", loadc("threads_clean.jsonl", 30), [EN2], TRACE_EN2)

if __name__ == "__main__":
    main()
