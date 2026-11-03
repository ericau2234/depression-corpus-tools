#!/usr/bin/env python3
"""YouTube corpus via yt-dlp (venv install; search + comments, no API key).
Live-proven 2026-11-03: search works, --write-comments extracted 60 comments
from a depression-story video. Saves data/youtube_videos.jsonl (title+desc)
and data/youtube_comments.jsonl.
Run with the venv python: .venv/bin/python youtube_crawler.py
"""
import json, os, subprocess, sys, glob

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
TMP = os.path.join(BASE, "yt_tmp")
os.makedirs(TMP, exist_ok=True)
YTDLP = os.path.join(BASE, ".venv", "bin", "yt-dlp")
QUERIES = ["my depression story", "why am I depressed my story", "how my depression started",
           "living with depression my story", "depression ruined my life story",
           "抑郁症 我的经历", "抑郁症自述 经历", "为什么会得抑郁症"]
PER_QUERY = 20
TOP_VIDEOS = 70
MAX_COMMENTS = 200

def run(args, timeout=300):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr

def search():
    vids = {}
    for q in QUERIES:
        out, _ = run([YTDLP, "--no-warnings", "--skip-download", "-J", "--flat-playlist",
                      f"ytsearch{PER_QUERY}:{q}"], timeout=240)
        try:
            entries = (json.loads(out) or {}).get("entries") or []
        except Exception:
            entries = []
        for e in entries:
            vid = e.get("id")
            if vid and vid not in vids:
                vids[vid] = {"id": vid, "title": e.get("title"), "view_count": e.get("view_count"),
                             "query": q, "url": f"https://www.youtube.com/watch?v={vid}"}
        print("search done", q, "unique", len(vids), flush=True)
    return sorted(vids.values(), key=lambda v: (v.get("view_count") or 0), reverse=True)

def main():
    vids = search()
    with open(os.path.join(DATA, "youtube_videos.jsonl"), "w", encoding="utf-8") as f:
        for v in vids: f.write(json.dumps(v, ensure_ascii=False) + "\n")
    print("VIDEOS", len(vids), flush=True)
    total = 0
    with open(os.path.join(DATA, "youtube_comments.jsonl"), "w", encoding="utf-8") as cf:
        for v in vids[:TOP_VIDEOS]:
            vid = v["id"]
            for old in glob.glob(os.path.join(TMP, f"{vid}.info.json")): os.remove(old)
            try:
                run([YTDLP, "--no-warnings", "--skip-download", "--write-comments",
                     "--write-info-json", "--no-write-thumbnail",
                     "--extractor-args", f"youtube:max_comments={MAX_COMMENTS},all,all",
                     "-o", os.path.join(TMP, "%(id)s"), v["url"]], timeout=420)
            except Exception as e:
                print("video fail", vid, type(e).__name__, flush=True); continue
            fn = os.path.join(TMP, f"{vid}.info.json")
            if not os.path.exists(fn): print("no info", vid, flush=True); continue
            d = json.load(open(fn, encoding="utf-8"))
            # enrich video record with description
            v["description"] = d.get("description")
            v["comment_count_meta"] = d.get("comment_count")
            kept = 0
            for c in d.get("comments") or []:
                text = (c.get("text") or "").strip()
                if not text: continue
                cf.write(json.dumps({"video_id": vid, "video_title": v.get("title"),
                                     "author": c.get("author"), "like_count": c.get("like_count"),
                                     "text": text}, ensure_ascii=False) + "\n")
                kept += 1; total += 1
            print("comments done", vid, kept, "total", total, flush=True)
            os.remove(fn)
    # rewrite videos with descriptions
    with open(os.path.join(DATA, "youtube_videos.jsonl"), "w", encoding="utf-8") as f:
        for v in vids: f.write(json.dumps(v, ensure_ascii=False) + "\n")
    print("COMMENTS", total)

if __name__ == "__main__":
    main()
