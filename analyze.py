#!/usr/bin/env python3
"""Keyword-dictionary theme analysis over the collected corpora.
Method honesty: dictionary matching counts MENTIONS, not verified causes.
A post can hit multiple themes; percentages use corpus size as denominator.
Outputs analysis_results.json + prints a summary table.
"""
import json, os, re, collections

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

EN_THEMES = {
    "family_parents": ["parent", "mother", "father", "mom", "dad", "family"],
    "childhood_trauma_abuse": ["childhood", "trauma", "abuse", "abused", "neglect", "bullied", "bullying"],
    "work_school_stress": ["work", "job stress", "school", "college", "exam", "boss", "burnout"],
    "jobloss_money": ["lost my job", "fired", "unemployed", "money", "debt", "bills", "financial"],
    "relationship": ["breakup", "broke up", "girlfriend", "boyfriend", "divorce", "wife", "husband", "relationship"],
    "loneliness_isolation": ["lonely", "loneliness", "alone", "no friends", "isolated", "isolation"],
    "grief_loss": ["died", "death of", "passed away", "grief", "lost my"],
    "physical_illness_pain": ["pain", "illness", "sick", "cancer", "diabetes", "chronic", "disability", "health problems"],
    "sleep": ["sleep", "insomnia", "can't sleep", "cant sleep", "tired all the time"],
    "genetics_family_history": ["genetic", "runs in my family", "family history", "hereditary"],
    "brain_chemical": ["chemical imbalance", "serotonin", "brain", "dopamine"],
    "no_reason_confusion": ["no reason", "don't know why", "dont know why", "for no reason", "i don't know why", "nothing happened"],
    "substance": ["alcohol", "drinking", "drug", "weed", "addiction"],
    "self_blame_personality": ["i hate myself", "worthless", "failure", "my fault", "weak", "lazy"],
    "covid": ["covid", "pandemic", "lockdown"],
}
CN_THEMES = {
    "原生家庭_父母": ["原生家庭", "父母", "妈妈", "爸爸", "父亲", "母亲", "家里", "家庭"],
    "童年_创伤": ["童年", "创伤", "阴影", "打骂", "家暴", "欺凌", "霸凌"],
    "学业_工作压力": ["高考", "考研", "学业", "上学", "工作", "职场", "内卷", "压力大", "加班"],
    "恋爱_婚姻": ["男朋友", "女朋友", "分手", "离婚", "老公", "老婆", "结婚", "对象"],
    "孤独": ["孤独", "孤单", "没朋友", "一个人"],
    "身体疾病_疼痛": ["癌", "病痛", "疼痛", "慢性", "糖尿病", "甲状腺", "身体不好"],
    "睡眠": ["失眠", "睡不着", "熬夜", "睡眠"],
    "遗传": ["遗传", "家族"],
    "经济": ["没钱", "欠债", "房贷", "失业", "找不到工作", "赚钱"],
    "无明确原因_困惑": ["不知道为什么", "没理由", "莫名其妙", "突然就", "毫无征兆"],
    "药物_治疗": ["吃药", "药物", "看医生", "确诊", "治疗", "住院"],
}

def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p): return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def analyze(texts, themes):
    n = len(texts)
    hits = collections.Counter()
    any_hit = 0
    for t in texts:
        low = t.lower()
        hit_any = False
        for theme, kws in themes.items():
            if any(k in low for k in kws):
                hits[theme] += 1; hit_any = True
        if hit_any: any_hit += 1
    return {"n": n, "any_theme_hit_pct": round(100 * any_hit / n, 1) if n else 0,
            "themes": {k: {"count": v, "pct": round(100 * v / n, 1) if n else 0}
                       for k, v in hits.most_common()}}

def main():
    out = {}
    reddit = load("reddit_posts.jsonl") + load("reddit_bulk.jsonl")
    rtexts = [((p.get("title") or "") + " " + (p.get("selftext") or "")) for p in reddit]
    out["reddit_posts"] = analyze(rtexts, EN_THEMES)
    out["reddit_meta"] = {"total_posts": len(reddit),
                          "with_selftext_len>=200": sum(1 for p in reddit if len(p.get("selftext") or "") >= 200),
                          "subreddits": collections.Counter(p.get("subreddit") for p in reddit)}

    vids = load("bilibili_videos.jsonl")
    vtexts = [((v.get("title") or "") + " " + (v.get("description") or "")) for v in vids]
    out["bilibili_videos"] = analyze(vtexts, CN_THEMES)
    out["bilibili_videos_meta"] = {"total": len(vids),
                                   "by_keyword": collections.Counter(v.get("keyword") for v in vids),
                                   "total_play": sum(v.get("play") or 0 for v in vids)}

    comments = load("bilibili_comments.jsonl")
    out["bilibili_comments"] = analyze([c.get("text") or "" for c in comments], CN_THEMES)

    dm = load("bilibili_danmaku.jsonl")
    out["bilibili_danmaku"] = analyze([d.get("text") or "" for d in dm], CN_THEMES)
    out["bilibili_danmaku_meta"] = {"total": len(dm), "unique_texts": len(set(d.get("text") for d in dm))}

    with open(os.path.join(BASE, "analysis_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))

if __name__ == "__main__":
    main()
