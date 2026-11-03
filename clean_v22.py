#!/usr/bin/env python3
"""v2.2 cleaning: extends clean_corpus.py with the deep-dive wave sources.
Reddit posts = original files + broad wave + deep2 windows (dedup by id).
Reddit comments = broad + deep2 (streamed, dedup by id + text hash).
Beyond Blue / 5ch / Patient merged across wave1+wave2 files. Adds LiveJournal.
Writes the same *_clean.jsonl names as supersets + reddit_comments_clean.jsonl
+ livejournal_clean.jsonl, and cleaning_report_v22.json."""
import json, os, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clean_corpus as cc

DATA, OUT = cc.DATA, cc.OUT
norm, lang_of = cc.norm, cc.lang_of
stats = {}

def stream_emit(key, row_gen, fout):
    seen_id, seen_hash = set(), set()
    st = {"in": 0, "kept": 0, "drop_id_dup": 0, "drop_text_dup": 0, "chars": 0}
    with open(os.path.join(OUT, fout), "w", encoding="utf-8") as f:
        for r in row_gen:
            st["in"] += 1
            if r["id"] in seen_id: st["drop_id_dup"] += 1; continue
            h = cc.thash(r.get("author"), r["text"] or r.get("title") or "")
            if h in seen_hash: st["drop_text_dup"] += 1; continue
            seen_id.add(r["id"]); seen_hash.add(h)
            st["kept"] += 1; st["chars"] += len(r["text"])
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats[key] = st
    print(key, st, flush=True)

def load_rel(rel):
    return cc.load(rel)

def reddit_post_row(d, kind):
    body = norm(d.get("selftext"))
    if body in ("[removed]", "[deleted]"): body = ""
    if d.get("author") in ("[deleted]", "AutoModerator"): return None
    title = norm(d.get("title"))
    return {"platform": "reddit", "kind": kind, "id": str(d.get("id")),
            "title": title, "text": body, "author": d.get("author"),
            "lang": lang_of(body or title, "en"), "chars": len(body),
            "created": d.get("created_utc"), "url": d.get("url"),
            "subreddit": d.get("subreddit"), "score": d.get("score")}

def reddit_posts_all():
    rows = cc.reddit()
    for pat, kind in [("reddit_broad_posts_*.jsonl", "reddit_broad"),
                      ("deep2/posts_*.jsonl", "reddit_deep2")]:
        for fn in sorted(glob.glob(os.path.join(DATA, pat))):
            for d in load_rel(os.path.relpath(fn, DATA)):
                r = reddit_post_row(d, kind)
                if r: rows.append(r)
    return rows

def reddit_comments_gen():
    for pat in ["reddit_broad_comments_*.jsonl", "deep2/comments_*.jsonl"]:
        for fn in sorted(glob.glob(os.path.join(DATA, pat))):
            for d in load_rel(os.path.relpath(fn, DATA)):
                body = norm(d.get("body"))
                if body in ("[removed]", "[deleted]"): continue
                if d.get("author") in ("[deleted]", "AutoModerator"): continue
                if len(body) < 10: continue
                yield {"platform": "reddit_comments", "kind": "reddit_comments",
                       "id": str(d.get("id")), "title": "", "text": body,
                       "author": d.get("author"), "lang": lang_of(body, "en"),
                       "chars": len(body), "created": d.get("created_utc"),
                       "url": None, "subreddit": d.get("subreddit"),
                       "score": d.get("score")}

def merged_generic(files, platform, lang, **kw):
    rows = []
    for fn in files:
        rows.extend(cc.generic(fn, platform, lang, **kw))
    return rows

def main():
    stream_emit("reddit", iter(reddit_posts_all()), "reddit_clean.jsonl")
    stream_emit("reddit_comments", reddit_comments_gen(), "reddit_comments_clean.jsonl")
    jobs = []
    jobs.append(("youtube_comments", cc.youtube(), "youtube_comments_clean.jsonl"))
    jobs.append(("patient", merged_generic(["patient_posts.jsonl", "patient2_posts.jsonl"], "patient", "en"), "patient_clean.jsonl"))
    jobs.append(("mastodon", cc.mastodon(), "mastodon_clean.jsonl"))
    jobs.append(("lemmy", cc.lemmy(), "lemmy_clean.jsonl"))
    bv, ba, bc = cc.bilibili()
    jobs.append(("bilibili_videos", bv, "bilibili_videos_clean.jsonl"))
    jobs.append(("bilibili_articles", ba, "bilibili_articles_clean.jsonl"))
    jobs.append(("bilibili_comments", bc, "bilibili_comments_clean.jsonl"))
    jobs.append(("huggingface", cc.huggingface(), "huggingface_clean.jsonl"))
    jobs.append(("hilferuf", cc.hilferuf(), "hilferuf_clean.jsonl"))
    jobs.append(("fivech", merged_generic(
        ["fivech_posts.jsonl", "fivech_body_posts.jsonl", "fivech_hosp_posts.jsonl",
         "fivech_jinsei_posts.jsonl", "fivech_psycho_posts.jsonl"],
        "fivech", "ja", title_key="thread_title", minlen=5, strip_ext=True), "fivech_clean.jsonl"))
    jobs.append(("dcinside", cc.dcinside(), "dcinside_clean.jsonl"))
    jobs.append(("lihkg", cc.lihkg(), "lihkg_clean.jsonl"))
    jobs.append(("twoch", cc.twoch(), "twoch_clean.jsonl"))
    jobs.append(("beyondblue", merged_generic(["beyondblue_posts.jsonl", "beyondblue2_posts.jsonl"],
                                              "beyondblue", "en"), "beyondblue_clean.jsonl"))
    jobs.append(("dcard", cc.dcard(), "dcard_clean.jsonl"))
    jobs.append(("psychforums", cc.psychforums(), "psychforums_clean.jsonl"))
    jobs.append(("mhf", cc.mhf(), "mhf_clean.jsonl"))
    jobs.append(("chiebukuro", cc.generic("chiebukuro_posts.jsonl", "chiebukuro", "ja"), "chiebukuro_clean.jsonl"))
    jobs.append(("okwave", cc.generic("okwave_posts.jsonl", "okwave", "ja"), "okwave_clean.jsonl"))
    jobs.append(("kin", cc.generic("kin_posts.jsonl", "kin", "ko"), "kin_clean.jsonl"))
    jobs.append(("livejournal", cc.generic("lj_posts.jsonl", "livejournal", "en"), "livejournal_clean.jsonl"))
    jobs.append(("threads", cc.generic("threads_posts.jsonl", "threads", "en"), "threads_clean.jsonl"))
    jobs.append(("hf_solomonk", cc.generic("hf_solomonk.jsonl", "huggingface", "en"), "hf_solomonk_clean.jsonl"))
    jobs.append(("hf_jsfactory", cc.generic("hf_jsfactory.jsonl", "huggingface", "en"), "hf_jsfactory_clean.jsonl"))
    for key, rows, fout in jobs:
        stream_emit(key, iter(rows), fout)
    total_kept = sum(s["kept"] for s in stats.values())
    total_chars = sum(s["chars"] for s in stats.values())
    stats["TOTAL"] = {"kept": total_kept, "chars": total_chars}
    json.dump(stats, open(os.path.join(OUT, "cleaning_report_v22.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("TOTAL", total_kept, total_chars)

if __name__ == "__main__":
    main()
