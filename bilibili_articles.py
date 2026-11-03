#!/usr/bin/env python3
"""Bilibili column/article corpus via search_type=article (guest spi cookies).
Articles are long-form essays - many are patient self-narratives.
article/view full text is rate-limited (-509), so corpus = title + desc +
tags + stats from search & viewinfo. Output: data/bilibili_articles.jsonl
"""
import json, time, os, re
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Referer": "https://www.bilibili.com/"}
KEYWORDS = ["抑郁症", "抑郁症自述", "为什么会得抑郁症", "抑郁症的原因", "原生家庭 抑郁",
            "抑郁症经历", "走出抑郁症", "抑郁 发病原因", "抑郁日记", "重度抑郁"]
PAGES = 5

def clean(t):
    return re.sub(r"<[^>]+>", "", t or "").strip()

def get_session():
    s = requests.Session(); s.headers.update(H)
    d = s.get("https://api.bilibili.com/x/frontend/finger/spi", timeout=20).json()["data"]
    s.cookies.set("buvid3", d["b_3"], domain=".bilibili.com")
    s.cookies.set("buvid4", d["b_4"], domain=".bilibili.com")
    return s

def get_json(s, url, params, tries=4):
    for a in range(tries):
        try:
            r = s.get(url, params=params, timeout=25)
            if r.status_code == 200: return r.json()
        except Exception: pass
        time.sleep(2.5 * (a + 1))
    return None

def main():
    s = get_session()
    seen, out = set(), []
    for kw in KEYWORDS:
        for page in range(1, PAGES + 1):
            j = get_json(s, "https://api.bilibili.com/x/web-interface/search/type",
                         {"search_type": "article", "keyword": kw, "page": page, "page_size": 42, "order": "totalrank"})
            if not j or j.get("code") != 0: break
            res = (j.get("data") or {}).get("result") or []
            if not res: break
            for a in res:
                aid = a.get("id")
                if aid in seen: continue
                seen.add(aid)
                out.append({"id": aid, "title": clean(a.get("title")), "desc": clean(a.get("desc")),
                            "author": a.get("author"), "view": a.get("view"), "like": a.get("like"),
                            "reply": a.get("reply"), "favorite": a.get("favorite"),
                            "pubdate": a.get("pubdate"), "words": a.get("words"),
                            "category": a.get("category"), "keyword": kw,
                            "url": f"https://www.bilibili.com/read/cv{aid}"})
            time.sleep(1.2)
        print("kw done", kw, "unique", len(out))
    with open(os.path.join(DATA, "bilibili_articles.jsonl"), "w", encoding="utf-8") as f:
        for a in out: f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print("ARTICLES", len(out))

if __name__ == "__main__":
    main()
