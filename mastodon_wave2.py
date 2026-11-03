#!/usr/bin/env python3
"""Mastodon wave 2: more hashtags incl. other languages, mastodon.social public tag timelines."""
import requests, re, json, os, time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "research-corpus/1.0"}
TAGS = ["depresion", "depressao", "antidepressants", "depressionhelp", "mentalhealthmatters",
        "depressionisreal", "endthestigma", "itsokaytonotbeokay", "suicideprevention",
        "bipolar", "ptsd", "burnout"]

def strip(html):
    t = re.sub(r"<br\s*/?>", "\n", html or "")
    t = re.sub(r"</p>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"[ \t]+", " ", t).strip()

def run(tag):
    out, url = [], f"https://mastodon.social/api/v1/timelines/tag/{tag}"
    params = {"limit": 40}
    for _ in range(15):
        try:
            r = requests.get(url, params=params, headers=H, timeout=30)
            if r.status_code != 200: break
            batch = r.json()
            if not batch: break
            for s in batch:
                out.append({"id": s.get("id"), "tag": tag, "created_at": s.get("created_at"),
                            "lang": s.get("language"), "text": strip(s.get("content")), "url": s.get("url")})
            nxt = None
            for part in (r.headers.get("Link") or "").split(","):
                if 'rel="next"' in part:
                    nxt = part.split(";")[0].strip().strip("<>")
            if not nxt: break
            url, params = nxt, {}
            time.sleep(0.8)
        except Exception:
            break
    return out

def main():
    total = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for part in ex.map(run, TAGS):
            total.extend(part); print("tag done, cumulative", len(total), flush=True)
    with open(os.path.join(DATA, "mastodon_wave2.jsonl"), "w", encoding="utf-8") as f:
        for s in total: f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print("MASTODON WAVE2 DONE total", len(total))

if __name__ == "__main__":
    main()
