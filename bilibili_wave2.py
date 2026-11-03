#!/usr/bin/env python3
"""Bilibili wave 2: more keywords for videos + articles (spi cookie flow). No danmaku (de-prioritised)."""
import requests, json, os, time, re

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Referer": "https://www.bilibili.com/"}
KEYWORDS = ["焦虑症", "抑郁症康复", "抑郁症休学", "产后抑郁", "青少年抑郁", "双相情感障碍自述",
            "抑郁症吃药", "抑郁症家人怎么办", "抑郁症复发", "失眠抑郁"]
PAGES = 8

def clean(s):
    return re.sub(r"<[^>]+>", "", s or "")

def session():
    s = requests.Session(); s.headers.update(H)
    d = s.get("https://api.bilibili.com/x/frontend/finger/spi", timeout=15).json()["data"]
    s.cookies.set("buvid3", d["b_3"], domain=".bilibili.com")
    s.cookies.set("buvid4", d["b_4"], domain=".bilibili.com")
    return s

def main():
    s = session()
    vout = open(os.path.join(DATA, "bilibili_wave2_videos.jsonl"), "w", encoding="utf-8")
    aout = open(os.path.join(DATA, "bilibili_wave2_articles.jsonl"), "w", encoding="utf-8")
    nv = na = 0
    for kw in KEYWORDS:
        for typ, out in (("video", vout), ("article", aout)):
            for page in range(1, PAGES + 1):
                try:
                    r = s.get("https://api.bilibili.com/x/web-interface/search/type",
                              params={"search_type": typ, "keyword": kw, "page": page, "page_size": 42}, timeout=20)
                    j = r.json()
                    if j.get("code") != 0: time.sleep(3); break
                    res = (j.get("data") or {}).get("result") or []
                    if not res: break
                    for it in res:
                        if typ == "video":
                            row = {"bvid": it.get("bvid"), "aid": it.get("aid"), "title": clean(it.get("title")),
                                   "description": it.get("description"), "author": it.get("author"),
                                   "play": it.get("play"), "review": it.get("review"), "like": it.get("like"),
                                   "pubdate": it.get("pubdate"), "tag": it.get("tag"), "keyword": kw}
                            out.write(json.dumps(row, ensure_ascii=False) + "\n"); nv += 1
                        else:
                            row = {"id": it.get("id"), "title": clean(it.get("title")), "desc": it.get("desc"),
                                   "author": it.get("author"), "view": it.get("view"), "like": it.get("like"),
                                   "reply": it.get("reply_count"), "pubdate": it.get("publish_time"),
                                   "keyword": kw, "url": f"https://www.bilibili.com/read/cv{it.get('id')}"}
                            out.write(json.dumps(row, ensure_ascii=False) + "\n"); na += 1
                    out.flush(); time.sleep(1.2)
                except Exception:
                    time.sleep(3)
        print(kw, "videos", nv, "articles", na, flush=True)
    vout.close(); aout.close()
    print("BILI WAVE2 DONE videos", nv, "articles", na)

if __name__ == "__main__":
    main()
