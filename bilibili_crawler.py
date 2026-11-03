#!/usr/bin/env python3
"""Bilibili depression-corpus crawler (pure API, guest spi cookies).

Flow proven live 2026-11-03 from this VM:
1. GET api.bilibili.com/x/frontend/finger/spi -> buvid3/buvid4 cookies
2. GET x/web-interface/search/type (search_type=video) -> works with those cookies
3. GET x/v2/reply/main (mode=3 hot) with same cookies -> guest cursor has an upper limit

Stores JSONL: data/bilibili_videos.jsonl, data/bilibili_comments.jsonl
Polite: 1.2s between requests, retries with backoff on network stalls.
"""
import json, time, sys, os
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Referer": "https://www.bilibili.com/"}

KEYWORDS = ["抑郁症", "抑郁症自述", "为什么会得抑郁症", "抑郁症的原因", "原生家庭 抑郁",
            "抑郁症经历", "走出抑郁症", "抑郁 发病原因", "抑郁症 陪伴", "重度抑郁"]
PAGES_PER_KW = 5          # 50 results/page max in search API -> up to ~250/kw before dedup
COMMENT_VIDEO_TOPN = 60   # fetch hot comments for the most-played self-narrative videos
SLEEP = 1.2

def get_session():
    s = requests.Session(); s.headers.update(H)
    for attempt in range(5):
        try:
            r = s.get("https://api.bilibili.com/x/frontend/finger/spi", timeout=20)
            d = r.json()["data"]
            s.cookies.set("buvid3", d["b_3"], domain=".bilibili.com")
            s.cookies.set("buvid4", d["b_4"], domain=".bilibili.com")
            return s
        except Exception as e:
            print("spi retry", attempt, e); time.sleep(3 * (attempt + 1))
    raise RuntimeError("spi failed")

def get_json(s, url, params, tries=4):
    for a in range(tries):
        try:
            r = s.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            print("http", r.status_code, url, params.get("keyword", ""))
        except Exception as e:
            print("net retry", a, type(e).__name__)
        time.sleep(2.5 * (a + 1))
    return None

def crawl_videos(s):
    seen, out = set(), []
    for kw in KEYWORDS:
        for page in range(1, PAGES_PER_KW + 1):
            j = get_json(s, "https://api.bilibili.com/x/web-interface/search/type",
                         {"search_type": "video", "keyword": kw, "page": page, "page_size": 42, "order": "totalrank"})
            if not j or j.get("code") != 0:
                print("search stop", kw, page, (j or {}).get("code")); break
            res = (j.get("data") or {}).get("result") or []
            if not res: break
            for v in res:
                bvid = v.get("bvid")
                if bvid in seen: continue
                seen.add(bvid)
                out.append({"bvid": bvid, "aid": v.get("aid") or v.get("id"), "title": v.get("title"),
                            "description": v.get("description"), "author": v.get("author"),
                            "play": v.get("play"), "danmaku": v.get("danmaku"), "review": v.get("review"),
                            "favorites": v.get("favorites"), "like": v.get("like"),
                            "pubdate": v.get("pubdate"), "duration": v.get("duration"),
                            "tag": v.get("tag"), "keyword": kw})
            time.sleep(SLEEP)
        print(f"kw done: {kw} total_unique={len(out)}")
    with open(os.path.join(DATA, "bilibili_videos.jsonl"), "w", encoding="utf-8") as f:
        for v in out: f.write(json.dumps(v, ensure_ascii=False) + "\n")
    return out

def crawl_comments(s, videos):
    cands = sorted(videos, key=lambda v: (v.get("play") or 0), reverse=True)[:COMMENT_VIDEO_TOPN]
    total = 0
    with open(os.path.join(DATA, "bilibili_comments.jsonl"), "w", encoding="utf-8") as f:
        for v in cands:
            oid = v.get("aid")
            if not oid: continue
            cursor = ""
            for _ in range(6):  # guest cursor limit: stop when is_end or empty
                j = get_json(s, "https://api.bilibili.com/x/v2/reply/main",
                             {"oid": oid, "type": 1, "mode": 3, "pagination_str": json.dumps({"offset": cursor})})
                if not j or j.get("code") != 0:
                    print("reply stop", v["bvid"], (j or {}).get("code")); break
                d = j.get("data") or {}
                for rep in d.get("replies") or []:
                    msg = ((rep.get("content") or {}).get("message") or "").strip()
                    if not msg: continue
                    f.write(json.dumps({"bvid": v["bvid"], "video_title": v.get("title"),
                                        "user": (rep.get("member") or {}).get("uname"),
                                        "like": rep.get("like"), "text": msg}, ensure_ascii=False) + "\n")
                    total += 1
                cur = (d.get("cursor") or {})
                if cur.get("is_end"): break
                cursor = ((cur.get("pagination_reply") or {}).get("next_offset") or "")
                if not cursor: break
                time.sleep(SLEEP)
            print("comments done", v["bvid"], "total", total)
            time.sleep(SLEEP)
    return total

if __name__ == "__main__":
    s = get_session()
    videos = crawl_videos(s)
    print("VIDEOS", len(videos))
    n = crawl_comments(s, videos)
    print("COMMENTS", n)
