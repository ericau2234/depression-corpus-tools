#!/usr/bin/env python3
"""HuggingFace public datasets via datasets-server rows API (no auth).
Provenance kept per row. Output: hf_<name>.jsonl
"""
import requests, json, os, time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "research-corpus/1.0"}
SETS = ["mrjunos/depression-reddit-cleaned", "hugginglearners/reddit-depression-cleaned",
        "ziq/depression_tweet", "joangaes/depression", "depression-icu/OESD-GG-zh_cn-1",
        "ShreyaR/DepressionDetection"]
CAP = 30000

def get(url, params=None, tries=4):
    for a in range(tries):
        try:
            r = requests.get(url, params=params, headers=H, timeout=45)
            if r.status_code == 200: return r.json()
            time.sleep(3 * (a + 1))
        except Exception:
            time.sleep(3 * (a + 1))
    return None

def text_of(row):
    for k in ("text", "clean_text", "selftext", "content", "tweet", "Text", "post", "title_text"):
        v = row.get(k)
        if isinstance(v, str) and len(v) > 3: return v
    strs = [v for v in row.values() if isinstance(v, str)]
    return max(strs, key=len) if strs else ""

DS = "https://datasets-server.huggingface.co"

def one(ds):
        name = ds.replace("/", "_")
        info = get(f"{DS}/splits", params={"dataset": ds})
        if not info:
            print(ds, "no splits (gated?)", flush=True); return
        splits = []
        for s in info.get("splits") or []:
            splits.append((s["config"], s["split"]))
        if not splits:
            print(ds, "empty splits", flush=True); return
        cfg, split = splits[0]
        out = open(os.path.join(DATA, f"hf_{name}.jsonl"), "w", encoding="utf-8")
        n = 0; offset = 0
        while n < CAP:
            j = get(f"{DS}/rows",
                    params={"dataset": ds, "config": cfg, "split": split, "offset": offset, "length": 100})
            if not j or not j.get("rows"): break
            for r in j["rows"]:
                row = r["row"]
                out.write(json.dumps({"dataset": ds, "text": text_of(row), "raw": row},
                                     ensure_ascii=False) + "\n")
                n += 1
            offset += len(j["rows"])
            print(ds, "rows", n, flush=True)
            if len(j["rows"]) < 100: break
        out.close()
        print(ds, "DONE", n, flush=True)

def main():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(one, SETS))
    print("HF ALL DONE", flush=True)

if __name__ == "__main__":
    main()
