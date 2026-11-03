#!/usr/bin/env python3
"""Value extraction over the CLEANED v2 corpus: where does the signal actually live?
- length distribution (value concentrates in long first-person posts)
- lived-experience dictionaries (onset / barriers / side-effects&stopping / what helped /
  meds / no-reason onset), reported per 1,000 LONG posts (chars>=200)
- a verbatim sample bank for eyeball verification
Mentions are text patterns, not clinical coding — same honesty rule as before."""
import json, os, re, random, statistics

BASE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(BASE, "data_clean")

EN = {
    "onset_narrative": ["started when", "began when", "ever since", "it started after", "triggered by", "after my divorce", "after i lost"],
    "barriers": ["can't afford", "cannot afford", "too expensive", "ashamed", "stigma", "embarrassed", "insurance won't", "waiting list", "waitlist", "afraid to tell"],
    "sidefx_or_stopped": ["side effect", "stopped taking", "quit taking", "withdrawal", "weight gain", "brain zap", "sexual side", "taper"],
    "it_helped": ["helped me", "saved my life", "feeling better", "turned my life around", "works for me", "finally feel"],
    "medication": ["sertraline", "zoloft", "fluoxetine", "prozac", "escitalopram", "lexapro", "venlafaxine", "effexor", "duloxetine", "cymbalta", "mirtazapine", "bupropion", "wellbutrin", "paroxetine", "citalopram", "quetiapine", "lamotrigine"],
    "therapy": ["my therapist", "therapy session", "cbt", "counseling", "counselling"],
    "no_reason_onset": ["no reason", "for no reason", "nothing happened", "out of nowhere", "no idea why", "don't know why i"],
}
ZH = {
    "onset_narrative": ["自从", "发病", "那次之后", "确诊之后", "从那以后"],
    "barriers": ["没钱", "看不起病", "不敢告诉", "怕被", "挂号", "排队", "家人不理解", "不敢让"],
    "sidefx_or_stopped": ["副作用", "停药", "戒断", "发胖", "性欲", "头晕", "嗜睡"],
    "it_helped": ["好转", "好多了", "救了我", "有用了", "控制住了", "稳定下来"],
    "medication": ["舍曲林", "氟西汀", "帕罗西汀", "文拉法辛", "度洛西汀", "艾司西酞普兰", "米氮平", "安非他酮", "喹硫平", "西酞普兰", "阿戈美拉汀", "伏硫西汀"],
    "therapy": ["心理咨询", "咨询师", "心理治疗", "心理医生"],
    "no_reason_onset": ["没有原因", "没发生什么", "莫名其妙", "无缘无故", "不知道为什么"],
}

def scan(path, lang_mode):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try: rows.append(json.loads(line))
            except Exception: pass
    chars = [r.get("chars", len(r.get("text") or "")) for r in rows]
    long_rows = [r for r in rows if (r.get("chars", 0) >= 200)]
    stats = {"n": len(rows), "median_chars": int(statistics.median(chars)) if chars else 0,
             "pct_ge500": round(100 * sum(1 for c in chars if c >= 500) / max(1, len(chars)), 1),
             "pct_ge1000": round(100 * sum(1 for c in chars if c >= 1000) / max(1, len(chars)), 1),
             "n_long": len(long_rows)}
    dicts = {}
    if lang_mode in ("en", "both"):
        dicts.update({f"en_{k}": v for k, v in EN.items()})
    if lang_mode in ("zh", "both"):
        dicts.update({f"zh_{k}": v for k, v in ZH.items()})
    hits = {k: 0 for k in dicts}
    for r in long_rows:
        t = (r.get("title") or "") + " " + (r.get("text") or "")
        tl = t.lower()
        for k, words in dicts.items():
            src = tl if k.startswith("en_") else t
            if any(w in src for w in words): hits[k] += 1
    per1000 = {k: round(1000 * v / max(1, len(long_rows)), 1) for k, v in hits.items()}
    return stats, per1000, long_rows

def main():
    random.seed(42)
    report = {}
    samples = []
    jobs = [("reddit", "reddit_clean.jsonl", "en", 10),
            ("patient", "patient_clean.jsonl", "en", 4),
            ("bilibili_articles", "bilibili_articles_clean.jsonl", "zh", 4),
            ("huggingface", "huggingface_clean.jsonl", "both", 8)]
    for name, fn, mode, nsamp in jobs:
        stats, per1000, long_rows = scan(os.path.join(CLEAN, fn), mode)
        report[name] = {"stats": stats, "per1000_long": per1000}
        print(name, stats, flush=True)
        pool = [r for r in long_rows if (r.get("chars", 0) >= 500)]
        for r in random.sample(pool, min(nsamp, len(pool))):
            txt = re.sub(r"\s+", " ", (r.get("text") or ""))[:420]
            samples.append({"platform": name, "chars": r.get("chars"), "title": (r.get("title") or "")[:80], "excerpt": txt})
    with open(os.path.join(BASE, "value_report.json"), "w", encoding="utf-8") as f:
        json.dump({"report": report, "samples": samples}, f, ensure_ascii=False, indent=1)
    print("VALUE DONE")

if __name__ == "__main__":
    main()
