#!/usr/bin/env python3
"""Cause classification over cleaned LONG posts (chars>=200), per platform.
Categories are non-exclusive (a post can carry several). EN patterns are phrase/
word-boundary based (the rent-in-parent substring trap is designed out).
Also computes: no-hit rate, multi-hit rate, and an 'economic-involved (broad)'
composite = strict-economics OR (work/family/relationship hit AND trapped/no-exit
or money marker present) — the closest measurable proxy for the layer-2 claim."""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(BASE, "data_clean")

EN = {
    "经济窘迫(严)": ["debt", "debts", "unemployed", "unemployment", "lost my job", "got fired", "laid off",
                    "poverty", "can't afford", "cannot afford", "evicted", "eviction", "homeless", "bankrupt",
                    "student loan", "no money", "financial stress", "financial problems", "money problems",
                    "money issues", "struggling financially", "bills piling", "behind on my"],
    "工作/学业": ["my job", "at work", "my boss", "coworker", "workplace", "burnout", "burned out",
                  "my work", "school", "college", "university", "exam", "exams", "studying", "homework"],
    "家庭/父母": ["my family", "my parents", "my mother", "my father", "my mom", "my dad", "parents"],
    "童年创伤/虐待": ["childhood trauma", "childhood abuse", "was abused", "were abused", "molested",
                      "my childhood", "growing up", "neglected as a child", "traumatic childhood"],
    "亲密关系": ["divorce", "divorced", "broke up", "breakup", "break up", "my wife", "my husband",
                 "girlfriend", "boyfriend", "cheated on", "toxic relationship", "abusive relationship"],
    "孤独/孤立": ["lonely", "loneliness", "no friends", "feel alone", "all alone", "isolated", "isolation"],
    "疾病/疼痛": ["chronic pain", "chronic illness", "cancer", "disability", "disabled", "diagnosed with",
                  "health problems", "in pain", "illness"],
    "丧亲/丧失": ["passed away", "funeral", "grief", "grieving", "died", "death of my", "lost my mom",
                  "lost my dad", "lost my mother", "lost my father"],
    "睡眠": ["insomnia", "can't sleep", "cannot sleep", "sleep problems", "no sleep", "sleepless"],
    "产后": ["postpartum", "after giving birth", "gave birth", "my baby was born"],
    "无缘无故": ["no reason", "for no reason", "out of nowhere", "nothing happened", "don't know why",
                 "cant explain", "can't explain"],
    "遗传/家族史": ["runs in my family", "family history", "genetic", "genetics", "hereditary",
                    "my mom was depressed", "my mother was depressed", "depression runs"],
    "困住/逃不掉": ["can't quit", "cannot quit", "can't leave", "cannot leave", "trapped", "feel stuck",
                    "no way out", "can't escape", "have to stay", "no choice but"],
}
ZH = {
    "经济窘迫(严)": ["没钱", "欠债", "债务", "负债", "房租", "房贷", "失业", "经济压力", "还不起", "欠钱",
                    "穷", "月光", "工资低", "收入低", "没工作", "找不到工作"],
    "工作/学业": ["工作", "加班", "老板", "上司", "上学", "考试", "学习", "内卷", "职场", "读书"],
    "家庭/父母": ["原生家庭", "我爸", "我妈", "父母", "我父亲", "我母亲", "家里人"],
    "童年创伤/虐待": ["小时候", "童年", "家暴", "虐待", "被打", "留守", "从小就"],
    "亲密关系": ["分手", "离婚", "对象", "男朋友", "女朋友", "出轨", "老公", "老婆", "婚姻"],
    "孤独/孤立": ["孤独", "孤单", "没朋友", "没有朋友", "一个人扛"],
    "疾病/疼痛": ["疼痛", "癌症", "残疾", "慢性病", "身体不好", "生病了", "住院"],
    "丧亲/丧失": ["去世", "过世", "走了", "丧亲", "离世"],
    "睡眠": ["失眠", "睡不着", "睡眠不好", "整夜睡不着"],
    "产后": ["产后", "生完孩子", "坐月子"],
    "无缘无故": ["莫名其妙", "没有原因", "没发生什么", "不知道为什么", "无缘无故"],
    "遗传/家族史": ["遗传", "家族史", "我妈也抑郁", "妈妈也有抑郁", "家族遗传"],
    "困住/逃不掉": ["辞不起", "不敢辞职", "走不了", "离不开", "逃不掉", "困在", "没办法辞职", "没有退路", "被困"],
}

def load(fn, minc=200, lang=None):
    rows = []
    with open(os.path.join(CLEAN, fn), encoding="utf-8") as f:
        for line in f:
            try: r = json.loads(line)
            except Exception: continue
            if r.get("chars", 0) >= minc and (lang is None or r.get("lang") == lang):
                rows.append(r)
    return rows

def classify(rows, dicts, lower):
    n = len(rows)
    hits = {k: 0 for k in dicts}
    nhit = 0; multi = 0; econ_broad = 0
    keys = list(dicts)
    econ_k, trap_k = keys[0], keys[-1]
    mid_keys = keys[1:4]  # 工作/学业, 家庭/父母, 童年 — layer-2 carriers; plus 亲密关系 index 4
    for r in rows:
        t = (r.get("title") or "") + " " + (r.get("text") or "")
        if lower: t = t.lower()
        h = {k: any(w in t for w in ws) for k, ws in dicts.items()}
        cnt = sum(h.values())
        if cnt == 0: nhit += 1
        if cnt >= 2: multi += 1
        for k, v in h.items():
            if v: hits[k] += 1
        if h[econ_k] or ((h[keys[1]] or h[keys[2]] or h[keys[4]]) and (h[trap_k] or h[econ_k])):
            econ_broad += 1
    out = {k: round(100 * v / n, 1) for k, v in hits.items()}
    out["_没有任何一类"] = round(100 * nhit / n, 1)
    out["_两类或以上"] = round(100 * multi / n, 1)
    out["_经济相关(宽:严口径∪被困住的工作/家庭/关系)"] = round(100 * econ_broad / n, 1)
    return n, out

def main():
    jobs = [("Reddit长帖(EN)", "reddit_clean.jsonl", None, EN, True),
            ("Patient长帖(EN)", "patient_clean.jsonl", None, EN, True),
            ("中文HF长帖(含OESD)", "huggingface_clean.jsonl", "zh", ZH, False),
            ("B站专栏(全部·短文本)", "bilibili_articles_clean.jsonl", None, ZH, False)]
    result = {}
    for name, fn, lang, dicts, lower in jobs:
        rows = load(fn, minc=200 if "B站" not in name else 0, lang=lang)
        n, out = classify(rows, dicts, lower)
        result[name] = {"n": n, "pct": out}
        print(f"===== {name}  n={n}")
        for k, v in sorted(out.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}%")
        print(flush=True)
    with open(os.path.join(BASE, "classification_report.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("CLASSIFY DONE")

if __name__ == "__main__":
    main()
