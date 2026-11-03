#!/usr/bin/env python3
"""v2 theme analysis over CLEANED corpora (danmaku excluded per eric).
Same dictionaries as v1 analyze.py for comparability. Mentions != causes.
Adds: per-subreddit Reddit split, multilingual YouTube split, HF datasets incl. Chinese OESD.
Outputs analysis_v2.json.
"""
import json, os, collections
from analyze import EN_THEMES, CN_THEMES, analyze

BASE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(BASE, "data_clean")

def load(name):
    p = os.path.join(CLEAN, name)
    if not os.path.exists(p): return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def texts(rows, min_chars=0):
    return [(r.get("title", "") + " " + r.get("text", "")).strip() for r in rows if (r.get("chars") or 0) >= min_chars]

def main():
    out = {}
    reddit = load("reddit_clean.jsonl")
    core = [r for r in reddit if r.get("subreddit") in ("depression", "mentalhealth", "depression_help")]
    adj = [r for r in reddit if r.get("subreddit") not in ("depression", "mentalhealth", "depression_help")]
    out["reddit_all"] = analyze(texts(reddit), EN_THEMES)
    out["reddit_core_subs"] = analyze(texts(core), EN_THEMES)
    out["reddit_adjacent_subs"] = analyze(texts(adj), EN_THEMES)
    out["reddit_meta"] = {"total": len(reddit), "core": len(core), "adjacent": len(adj),
                          "by_subreddit": collections.Counter(r.get("subreddit") for r in reddit),
                          "selftext_ge200": sum(1 for r in reddit if (r.get("chars") or 0) >= 200)}

    patient = load("patient_clean.jsonl")
    out["patient"] = analyze(texts(patient), EN_THEMES)

    lemmy = load("lemmy_clean.jsonl")
    out["lemmy"] = analyze(texts(lemmy), EN_THEMES)

    masto = load("mastodon_clean.jsonl")
    masto_en = [r for r in masto if r.get("lang") == "en"]
    out["mastodon_en"] = analyze(texts(masto_en), EN_THEMES)
    out["mastodon_meta"] = {"total": len(masto), "en": len(masto_en),
                            "langs": collections.Counter(r.get("lang") for r in masto).most_common(12)}

    yt = load("youtube_comments_clean.jsonl")
    yt_en = [r for r in yt if r.get("lang") == "other"]
    yt_zh = [r for r in yt if r.get("lang") == "zh"]
    out["youtube_en"] = analyze(texts(yt_en), EN_THEMES)
    out["youtube_zh"] = analyze(texts(yt_zh), CN_THEMES)
    out["youtube_meta"] = {"total": len(yt), "en_like": len(yt_en), "zh": len(yt_zh)}

    bv = load("bilibili_videos_clean.jsonl"); ba = load("bilibili_articles_clean.jsonl")
    out["bilibili_videos"] = analyze(texts(bv), CN_THEMES)
    out["bilibili_articles"] = analyze(texts(ba), CN_THEMES)
    out["bilibili_meta"] = {"videos": len(bv), "articles": len(ba),
                            "article_desc_ge100": sum(1 for r in ba if (r.get("chars") or 0) >= 100)}

    hf = load("huggingface_clean.jsonl")
    oesd = [r for r in hf if "OESD" in (r.get("kind") or "")]
    hf_en = [r for r in hf if "OESD" not in (r.get("kind") or "")]
    out["hf_oesd_zh"] = analyze(texts(oesd), CN_THEMES)
    out["hf_english_sets"] = analyze(texts(hf_en), EN_THEMES)
    out["hf_meta"] = {"total": len(hf), "oesd": len(oesd), "english_sets": len(hf_en),
                      "by_dataset": collections.Counter(r.get("kind") for r in hf)}

    hil = load("hilferuf_clean.jsonl")
    out["hilferuf_meta"] = {"total": len(hil)}

    with open(os.path.join(BASE, "analysis_v2.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))

if __name__ == "__main__":
    main()
