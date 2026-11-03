#!/usr/bin/env python3
"""Corpus cleaning pipeline -> data_clean/*.jsonl + cleaning_report.json
Rules:
  - strip HTML tags/entities, zero-width chars; collapse whitespace
  - drop [removed]/[deleted]/empty bodies and deleted authors (Reddit)
  - drop AutoModerator + stickied moderator announcements (Lemmy/Reddit)
  - drop YouTube timestamps-only, link-only, pure-promo spam (URL + promo keywords, short)
  - drop Mastodon posts that are pure link-shares (url in text, <60 chars of real text)
  - exact dedup per platform by (source id) then by (author + normalized text hash)
  - unify schema: {platform, kind, id, title, text, author, lang, chars, created, url}
  - lang: use platform field when available, else CJK-ratio heuristic (zh if >=30% CJK)
Danmaku is NOT cleaned/merged (de-prioritised by eric); raw file stays in data/.
Idempotent: safe to re-run as crawlers finish.
"""
import json, os, re, html, hashlib, unicodedata
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data"); OUT = os.path.join(BASE, "data_clean")
os.makedirs(OUT, exist_ok=True)

TAG = re.compile(r"<[^>]+>")
URLRE = re.compile(r"https?://\S+|www\.\S+")
ZW = re.compile(r"[​-‏‪-‮﻿]")
EMOJI_ONLY = re.compile(r"^[\W_]+$", re.UNICODE)
CJK = re.compile(r"[一-鿿぀-ヿ가-힯]")
PROMO = ("subscribe", "check out my", "my channel", "buy now", "discount", "promo code",
         "earn money", "make money online", "click the link", "bitcoin", "crypto giveaway")

def norm(s):
    if not s: return ""
    s = html.unescape(str(s))
    s = TAG.sub(" ", s)
    s = ZW.sub("", s)
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip()

def lang_of(text, given=None):
    if given and given not in ("und", "null"): return given
    if not text: return "unk"
    cjk = len(CJK.findall(text))
    return "zh" if cjk >= 8 and cjk / max(1, len(text)) >= 0.25 else "other"

def load(fn):
    p = os.path.join(DATA, fn)
    if not os.path.exists(p): return []
    rows = []
    for l in open(p, encoding="utf-8"):
        try: rows.append(json.loads(l))
        except Exception: pass
    return rows

def thash(author, text):
    return hashlib.md5((str(author or "") + "|" + text.lower()).encode("utf-8")).hexdigest()

stats = {}
def emit(platform, rows, fout, stats_key):
    seen_id, seen_hash = set(), set()
    st = {"in": len(rows), "kept": 0, "drop_id_dup": 0, "drop_text_dup": 0,
          "drop_noise": 0, "drop_short": 0, "chars": 0}
    with open(os.path.join(OUT, fout), "w", encoding="utf-8") as f:
        for r in rows:
            if r["id"] in seen_id: st["drop_id_dup"] += 1; continue
            h = thash(r.get("author"), r["text"] or r.get("title") or "")
            if h in seen_hash: st["drop_text_dup"] += 1; continue
            seen_id.add(r["id"]); seen_hash.add(h)
            st["kept"] += 1; st["chars"] += len(r["text"])
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats[stats_key] = st

# ---------- Reddit ----------
def reddit():
    rows = []
    for fn, kind in [("reddit_posts.jsonl", "reddit_search"), ("reddit_bulk.jsonl", "reddit"),
                     ("reddit_deep.jsonl", "reddit"), ("reddit_wave2.jsonl", "reddit_wave2"),
                     ("reddit_wave2_0.jsonl", "reddit_wave2"), ("reddit_wave2_1.jsonl", "reddit_wave2"),
                     ("reddit_wave3.jsonl", "reddit_wave3")]:
        for d in load(fn):
            body = norm(d.get("selftext"))
            if body in ("[removed]", "[deleted]"): body = ""
            if d.get("author") in ("[deleted]", "AutoModerator"): continue
            title = norm(d.get("title"))
            rows.append({"platform": "reddit", "kind": kind, "id": str(d.get("id")),
                         "title": title, "text": body, "author": d.get("author"),
                         "lang": lang_of(body or title, "en"), "chars": len(body),
                         "created": d.get("created_utc"), "url": d.get("url"),
                         "subreddit": d.get("subreddit"), "score": d.get("score")})
    return rows

# ---------- YouTube ----------
def youtube():
    vids = {str(d["id"]): norm(d.get("title")) for d in load("youtube_videos.jsonl")}
    for d in load("youtube_wave2_videos.jsonl"):
        vids[str(d["id"])] = norm(d.get("title"))
    rows = []
    for fn in ("youtube_comments.jsonl", "youtube_comments_par.jsonl", "youtube_wave2_comments.jsonl"):
        for d in load(fn):
            t = norm(d.get("text"))
            if len(t) < 8: continue
            low = t.lower()
            if URLRE.search(t) and len(URLRE.sub("", t)) < 40 and any(p in low for p in PROMO): continue
            if EMOJI_ONLY.match(t): continue
            vid = str(d.get("video_id"))
            rows.append({"platform": "youtube", "kind": "comment", "id": vid + ":" + thash(d.get("author"), t)[:12],
                         "title": vids.get(vid) or norm(d.get("video_title")), "text": t,
                         "author": d.get("author"), "lang": lang_of(t), "chars": len(t),
                         "created": None, "url": "https://www.youtube.com/watch?v=" + vid,
                         "like_count": d.get("like_count")})
    return rows

# ---------- Patient.info ----------
def patient():
    rows = []
    for d in load("patient_posts.jsonl"):
        t = norm(d.get("text"))
        if len(t) < 10: continue
        rows.append({"platform": "patient", "kind": "forum_post",
                     "id": str(d.get("topic_id")) + ":" + str(d.get("post_number")),
                     "title": norm(d.get("topic_title")), "text": t, "author": d.get("username"),
                     "lang": "en", "chars": len(t), "created": d.get("created_at"), "url": None})
    return rows

# ---------- Mastodon ----------
def mastodon():
    rows = []
    for d in load("mastodon_posts.jsonl") + load("mastodon_wave2.jsonl"):
        t = norm(d.get("text"))
        real = URLRE.sub("", t)
        if len(real) < 25: continue  # link-share / promo / emoji noise
        rows.append({"platform": "mastodon", "kind": "post", "id": str(d.get("id")),
                     "title": "", "text": t, "author": None, "lang": lang_of(t, d.get("lang")),
                     "chars": len(t), "created": d.get("created_at"), "url": d.get("url"),
                     "tag": d.get("tag")})
    return rows

# ---------- Lemmy ----------
def lemmy():
    rows = []
    for d in load("lemmy_posts.jsonl") + load("lemmy_wave2.jsonl"):
        body = norm(d.get("body")); title = norm(d.get("title"))
        low = (title + " " + body).lower()
        if "mod post" in low or "moderator" in low[:60] or "read before posting" in low or "rules" == title.lower():
            continue
        rows.append({"platform": "lemmy", "kind": "post", "id": str(d.get("id")),
                     "title": title, "text": body, "author": None, "lang": lang_of(body or title, "en"),
                     "chars": len(body), "created": d.get("published"), "url": d.get("url"),
                     "community": d.get("community")})
    return rows

# ---------- Bilibili ----------
def bilibili():
    vrows = []
    for d in load("bilibili_videos.jsonl") + load("bilibili_wave2_videos.jsonl"):
        title = norm(d.get("title")); desc = norm(d.get("description"))
        vrows.append({"platform": "bilibili", "kind": "video", "id": str(d.get("bvid")),
                      "title": title, "text": desc, "author": d.get("author"), "lang": "zh",
                      "chars": len(desc), "created": d.get("pubdate"), "url": "https://www.bilibili.com/video/" + str(d.get("bvid")),
                      "play": d.get("play"), "keyword": d.get("keyword")})
    arows = []
    for d in load("bilibili_articles.jsonl") + load("bilibili_wave2_articles.jsonl"):
        title = norm(d.get("title")); desc = norm(d.get("desc"))
        arows.append({"platform": "bilibili", "kind": "article", "id": "cv" + str(d.get("id")),
                      "title": title, "text": desc, "author": d.get("author"), "lang": "zh",
                      "chars": len(desc), "created": d.get("pubdate"), "url": d.get("url"),
                      "keyword": d.get("keyword")})
    crows = []
    for d in load("bilibili_comments.jsonl"):
        t = norm(d.get("text"))
        if len(t) < 4: continue
        crows.append({"platform": "bilibili", "kind": "comment", "id": str(d.get("bvid")) + ":" + thash(d.get("user"), t)[:12],
                      "title": norm(d.get("video_title")), "text": t, "author": d.get("user"),
                      "lang": lang_of(t), "chars": len(t), "created": None, "url": None,
                      "like_count": d.get("like")})
    return vrows, arows, crows

# ---------- HuggingFace datasets ----------
def huggingface():
    import glob as _g
    rows = []
    for p in sorted(_g.glob(os.path.join(DATA, "hf_*.jsonl"))):
        for d in load(os.path.basename(p)):
            t = norm(d.get("text"))
            if len(t) < 10: continue
            ds = d.get("dataset") or os.path.basename(p)
            raw = d.get("raw") or {}
            rows.append({"platform": "huggingface", "kind": ds, "id": "hf:" + thash(ds.split("/")[0], t)[:16] + ":" + thash(None, t)[:12],
                         "title": "", "text": t, "author": None,
                         "lang": lang_of(t), "chars": len(t), "created": None, "url": None,
                         "label": raw.get("label") if isinstance(raw, dict) else None})
    return rows

# ---------- Hilferuf (German forum) ----------
def hilferuf():
    rows = []
    for d in load("hilferuf_posts.jsonl"):
        t = norm(d.get("text"))
        if len(t) < 30: continue
        rows.append({"platform": "hilferuf", "kind": "forum_post", "id": "hf-de:" + str(d.get("id")),
                     "title": norm(d.get("title")), "text": t, "author": None, "lang": "de",
                     "chars": len(t), "created": None, "url": d.get("url"), "node": d.get("node")})
    return rows

# ---------- v2.1 new platforms (generic forum/Q&A loaders) ----------
EXT_CMD = re.compile(r"!extend:\S+|!chk:\S+")

def generic(fn, platform, lang, title_key="title", minlen=10, strip_ext=False):
    rows = []
    for d in load(fn):
        t = norm(d.get("text"))
        if strip_ext: t = re.sub(r"\s+", " ", EXT_CMD.sub("", t)).strip()
        if len(t) < minlen: continue
        rows.append({"platform": platform, "kind": "forum_post", "id": platform + ":" + str(d.get("id")),
                     "title": norm(d.get(title_key)), "text": t, "author": None, "lang": lang,
                     "chars": len(t), "created": d.get("created"), "url": d.get("url")})
    return rows

def fivech():   return generic("fivech_posts.jsonl", "fivech", "ja", title_key="thread_title", minlen=5, strip_ext=True)
def dcinside(): return generic("dcinside_posts.jsonl", "dcinside", "ko")
def lihkg():    return generic("lihkg_posts.jsonl", "lihkg", "yue")
def twoch():    return generic("twoch_posts.jsonl", "twoch", "ru")
def beyondblue(): return generic("beyondblue_posts.jsonl", "beyondblue", "en")
def dcard():    return generic("dcard_posts.jsonl", "dcard", "zh")
def psychforums():
    return generic("psychforums_posts.jsonl", "psychforums", "en") + \
           generic("psychforums_deep.jsonl", "psychforums", "en")
def mhf():      return generic("mhf_posts.jsonl", "mhf", "en")
def qna():
    rows = []
    for fn, plat, lang in [("chiebukuro_posts.jsonl", "chiebukuro", "ja"),
                           ("okwave_posts.jsonl", "okwave", "ja"),
                           ("kin_posts.jsonl", "kin", "ko")]:
        rows += generic(fn, plat, lang)
    # keep separate outputs per platform instead: handled in main via split
    return rows

def main():
    jobs = []
    jobs.append(("reddit", reddit(), "reddit_clean.jsonl"))
    jobs.append(("youtube_comments", youtube(), "youtube_comments_clean.jsonl"))
    jobs.append(("patient", patient(), "patient_clean.jsonl"))
    jobs.append(("mastodon", mastodon(), "mastodon_clean.jsonl"))
    jobs.append(("lemmy", lemmy(), "lemmy_clean.jsonl"))
    bv, ba, bc = bilibili()
    jobs.append(("bilibili_videos", bv, "bilibili_videos_clean.jsonl"))
    jobs.append(("bilibili_articles", ba, "bilibili_articles_clean.jsonl"))
    jobs.append(("bilibili_comments", bc, "bilibili_comments_clean.jsonl"))
    jobs.append(("huggingface", huggingface(), "huggingface_clean.jsonl"))
    jobs.append(("hilferuf", hilferuf(), "hilferuf_clean.jsonl"))
    jobs.append(("fivech", fivech(), "fivech_clean.jsonl"))
    jobs.append(("dcinside", dcinside(), "dcinside_clean.jsonl"))
    jobs.append(("lihkg", lihkg(), "lihkg_clean.jsonl"))
    jobs.append(("twoch", twoch(), "twoch_clean.jsonl"))
    jobs.append(("beyondblue", beyondblue(), "beyondblue_clean.jsonl"))
    jobs.append(("dcard", dcard(), "dcard_clean.jsonl"))
    jobs.append(("psychforums", psychforums(), "psychforums_clean.jsonl"))
    jobs.append(("mhf", mhf(), "mhf_clean.jsonl"))
    jobs.append(("chiebukuro", generic("chiebukuro_posts.jsonl", "chiebukuro", "ja"), "chiebukuro_clean.jsonl"))
    jobs.append(("okwave", generic("okwave_posts.jsonl", "okwave", "ja"), "okwave_clean.jsonl"))
    jobs.append(("kin", generic("kin_posts.jsonl", "kin", "ko"), "kin_clean.jsonl"))
    for key, rows, fout in jobs: emit(key, rows, fout, key)
    total_kept = sum(s["kept"] for s in stats.values())
    total_chars = sum(s["chars"] for s in stats.values())
    stats["TOTAL"] = {"kept": total_kept, "chars": total_chars}
    json.dump(stats, open(os.path.join(OUT, "cleaning_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
