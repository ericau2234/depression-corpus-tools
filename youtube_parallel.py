#!/usr/bin/env python3
"""YouTube comments, parallel version: 4 concurrent yt-dlp subprocesses.
Writes youtube_comments_par.jsonl (merge + dedup happens in analysis).
Skips videos already present in youtube_comments.jsonl.
Run with .venv/bin/python.
"""
import json, os, subprocess, glob, threading
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
TMP = os.path.join(BASE, "yt_tmp_par")
os.makedirs(TMP, exist_ok=True)
YTDLP = os.path.join(BASE, ".venv", "bin", "yt-dlp")
WORKERS = 4
TOP = 70
lock = threading.Lock()
counter = {"done": 0, "comments": 0}

def main():
    vids = [json.loads(l) for l in open(os.path.join(DATA, "youtube_videos.jsonl"), encoding="utf-8")]
    done_ids = set()
    old = os.path.join(DATA, "youtube_comments.jsonl")
    if os.path.exists(old):
        for l in open(old, encoding="utf-8"):
            try: done_ids.add(json.loads(l)["video_id"])
            except Exception: pass
    todo = [v for v in vids[:TOP] if v["id"] not in done_ids]
    print("videos total", len(vids), "already commented", len(done_ids), "todo", len(todo), flush=True)
    out = open(os.path.join(DATA, "youtube_comments_par.jsonl"), "w", encoding="utf-8")

    def work(v):
        vid = v["id"]
        fn = os.path.join(TMP, f"{vid}.info.json")
        try:
            subprocess.run([YTDLP, "--no-warnings", "--skip-download", "--write-comments",
                            "--write-info-json", "--no-write-thumbnail",
                            "--extractor-args", "youtube:max_comments=200,all,all",
                            "-o", os.path.join(TMP, "%(id)s"), v["url"]],
                           capture_output=True, text=True, timeout=420)
        except Exception as e:
            print("fail", vid, type(e).__name__, flush=True); return
        if not os.path.exists(fn): print("no info", vid, flush=True); return
        try: d = json.load(open(fn, encoding="utf-8"))
        except Exception: return
        rows = []
        for c in d.get("comments") or []:
            text = (c.get("text") or "").strip()
            if text:
                rows.append({"video_id": vid, "video_title": v.get("title"),
                             "author": c.get("author"), "like_count": c.get("like_count"), "text": text})
        with lock:
            for r in rows: out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            counter["done"] += 1; counter["comments"] += len(rows)
            print("done", counter["done"], "comments", counter["comments"], flush=True)
        os.remove(fn)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(work, todo))
    out.close()
    print("YT PARALLEL DONE", counter)

if __name__ == "__main__":
    main()
