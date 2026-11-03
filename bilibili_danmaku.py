#!/usr/bin/env python3
"""Bilibili danmaku corpus: pagelist -> cid -> x/v1/dm/list.so (guest, spi cookies).
Live-proven 2026-11-03: returns 1200-1800 danmaku per popular video.
Note: guest comments are capped at 3/video (see bilibili_crawler), danmaku has no such cap.
Stores data/bilibili_danmaku.jsonl {bvid, video_title, text}
"""
import json, time, os, re
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Referer": "https://www.bilibili.com/"}
TOPN = 80

def get_session():
    s = requests.Session(); s.headers.update(H)
    d = s.get("https://api.bilibili.com/x/frontend/finger/spi", timeout=20).json()["data"]
    s.cookies.set("buvid3", d["b_3"], domain=".bilibili.com")
    s.cookies.set("buvid4", d["b_4"], domain=".bilibili.com")
    return s

def main():
    s = get_session()
    vids = [json.loads(l) for l in open(os.path.join(DATA, "bilibili_videos.jsonl"), encoding="utf-8")]
    vids = sorted(vids, key=lambda v: (v.get("danmaku") or 0), reverse=True)[:TOPN]
    total = 0
    with open(os.path.join(DATA, "bilibili_danmaku.jsonl"), "w", encoding="utf-8") as f:
        for v in vids:
            try:
                r = s.get("https://api.bilibili.com/x/player/pagelist", params={"bvid": v["bvid"]}, timeout=20)
                cid = r.json()["data"][0]["cid"]
                r2 = s.get("https://api.bilibili.com/x/v1/dm/list.so", params={"oid": cid}, timeout=25)
                xml = r2.content.decode("utf-8", errors="ignore")
                texts = re.findall(r"<d [^>]*>(.*?)</d>", xml)
                for t in texts:
                    t = t.strip()
                    if t:
                        f.write(json.dumps({"bvid": v["bvid"], "video_title": v.get("title"), "text": t},
                                           ensure_ascii=False) + "\n")
                        total += 1
                print("dm done", v["bvid"], len(texts), "total", total)
            except Exception as e:
                print("dm fail", v["bvid"], type(e).__name__, e)
            time.sleep(1.0)
    print("DANMAKU", total)

if __name__ == "__main__":
    main()
