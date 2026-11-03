#!/usr/bin/env python3
"""YouTube wave 2: multilingual depression-story searches, comments in parallel.
Run with .venv/bin/python. Output: youtube_wave3_videos.jsonl + youtube_wave3_comments.jsonl
"""
import subprocess, json, os, threading
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data"); TMP = os.path.join(BASE, "yt_tmp_w2")
os.makedirs(TMP, exist_ok=True); os.makedirs(DATA, exist_ok=True)
YTDLP = os.path.join(BASE, ".venv", "bin", "yt-dlp")
QUERIES = [
    ("en", "antidepressants my experience side effects"),
    ("en", "burnout my story I quit my job"),
    ("en", "living with depression daily life vlog"),
    ("en", "grief losing my parent story"),
    ("en", "anxiety ruined my life story"),
    ("zh", "抑郁症吃药经历副作用"),
    ("zh", "焦虑症自述经历"),
    ("zh", "双相情感障碍经历分享"),
    ("ja", "うつ病 仕事 辞めた 体験"),
    ("ja", "抗うつ薬 体験 副作用"),
    ("ko", "우울증 약 복용 후기"),
    ("ko", "번아웃 퇴사 이야기"),
    ("es", "antidepresivos mi experiencia efectos"),
    ("pt", "antidepressivo minha experiência efeitos"),
    ("de", "Antidepressiva meine Erfahrung Nebenwirkungen"),
    ("fr", "antidépresseurs mon expérience effets"),
    ("ru", "антидепрессанты мой опыт побочки"),
    ("tr", "depresyon hikayem nasıl yendim"),
    ("pl", "depresja moja historia leczenie"),
    ("vi", "trầm cảm câu chuyện của tôi"),
]
PER = 12
TOP = 200
lock = threading.Lock(); counter = {"v": 0, "c": 0}

def search(lang, q):
    out = []
    try:
        p = subprocess.run([YTDLP, "--no-warnings", "--flat-playlist", "-J",
                            f"ytsearch{PER}:{q}"], capture_output=True, text=True, timeout=300)
        d = json.loads(p.stdout)
        for e in d.get("entries") or []:
            if e.get("id"):
                out.append({"id": e["id"], "title": e.get("title"), "view_count": e.get("view_count"),
                            "query": q, "lang_query": lang, "url": "https://www.youtube.com/watch?v=" + e["id"]})
    except Exception as e:
        print("search fail", lang, type(e).__name__, flush=True)
    return out

def main():
    vids, seen = [], set()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(lambda t: search(*t), QUERIES):
            for v in res:
                if v["id"] not in seen:
                    seen.add(v["id"]); vids.append(v)
    old = set()
    op = os.path.join(DATA, "youtube_videos.jsonl")
    if os.path.exists(op):
        for l in open(op, encoding="utf-8"):
            try: old.add(json.loads(l)["id"])
            except Exception: pass
    vids = [v for v in vids if v["id"] not in old]
    vids.sort(key=lambda v: v.get("view_count") or 0, reverse=True)
    with open(os.path.join(DATA, "youtube_wave3_videos.jsonl"), "w", encoding="utf-8") as f:
        for v in vids: f.write(json.dumps(v, ensure_ascii=False) + "\n")
    print("wave2 new videos:", len(vids), "taking top", TOP, flush=True)
    out = open(os.path.join(DATA, "youtube_wave3_comments.jsonl"), "w", encoding="utf-8")

    def work(v):
        vid = v["id"]; fn = os.path.join(TMP, f"{vid}.info.json")
        try:
            subprocess.run([YTDLP, "--no-warnings", "--skip-download", "--write-comments",
                            "--write-info-json", "--no-write-thumbnail",
                            "--extractor-args", "youtube:max_comments=200,all,all",
                            "-o", os.path.join(TMP, "%(id)s"), v["url"]],
                           capture_output=True, text=True, timeout=420)
            if not os.path.exists(fn): return
            d = json.load(open(fn, encoding="utf-8"))
            rows = []
            for c in d.get("comments") or []:
                text = (c.get("text") or "").strip()
                if text: rows.append({"video_id": vid, "video_title": v.get("title"),
                                      "author": c.get("author"), "like_count": c.get("like_count"), "text": text})
            with lock:
                for r in rows: out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush(); counter["v"] += 1; counter["c"] += len(rows)
                print("done", counter["v"], "comments", counter["c"], flush=True)
            os.remove(fn)
        except Exception as e:
            print("fail", vid, type(e).__name__, flush=True)

    with ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(work, vids[:TOP]))
    out.close(); print("WAVE2 DONE", counter)

if __name__ == "__main__":
    main()
