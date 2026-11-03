#!/usr/bin/env python3
"""Q&A wave: Yahoo Chiebukuro (JP), OKWave (JP), Naver Kin (KR).
Search pages -> question detail pages -> question + answers as one text blob."""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
     "Accept-Language": "ja,ko;q=0.8,en;q=0.5"}

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or ""); t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get(url, tries=4):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.text
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def junescape(s):
    try: return json.loads('"' + s.replace('"', '\\"') + '"')
    except Exception: return s

# ---------- Chiebukuro ----------
def chie_links(term, pages=60):
    ids = []
    for p in range(pages):
        u = f"https://chiebukuro.yahoo.co.jp/search/?p={requests.utils.quote(term)}&flg=3&b={1 + p * 10}"
        txt = get(u)
        if not txt: break
        new = [q for q in dict.fromkeys(re.findall(r"/qa/question_detail/(q\d+)", txt)) if q not in ids]
        ids += new
        print("chie", term, "page", p + 1, "total", len(ids), flush=True)
        if not new: break
        time.sleep(0.4)
    return ids

def chie_fetch(qid):
    txt = get(f"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/{qid}")
    if not txt: return None
    og = re.search(r'<meta property="og:description" content="([^"]+)"', txt)
    parts = []
    for m in re.finditer(r'"(?:questionText|answerText|contentText)":"((?:[^"\\]|\\.)*)"', txt):
        s = junescape(m.group(1)).strip()
        if len(s) >= 10 and s not in parts: parts.append(s)
    if not parts and og: parts = [html.unescape(og.group(1))]
    body = "\n".join(parts)
    if len(body) < 30: return None
    return {"id": qid, "platform_q": "chiebukuro", "title": "", "text": body,
            "url": f"https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/{qid}"}

# ---------- OKWave ----------
def okw_links(term, pages=40):
    ids = []
    for p in range(1, pages + 1):
        u = f"https://okwave.jp/search?word={requests.utils.quote(term)}&page={p}"
        txt = get(u)
        if not txt: break
        new = [q for q in dict.fromkeys(re.findall(r"/qa/q(\d+)\.html", txt)) if q not in ids]
        ids += new
        print("okw", term, "page", p, "total", len(ids), flush=True)
        if not new: break
        time.sleep(0.4)
    return ids

def okw_fetch(qid):
    txt = get(f"https://okwave.jp/qa/q{qid}.html")
    if not txt: return None
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", txt, re.S)
    title = strip(h1.group(1)) if h1 else ""
    parts = [title] if title else []
    for m in re.finditer(r'class="answers_body"[^>]*>(.*?)</div>\s*</div>', txt, re.S):
        s = strip(m.group(1))
        if len(s) >= 10: parts.append(s)
    if len(parts) < 2:
        for m in re.finditer(r'class="answers_contents[^"]*"[^>]*>(.*?)</div>', txt, re.S):
            s = strip(m.group(1))
            if len(s) >= 30: parts.append(s)
    body = "\n".join(parts)
    if len(body) < 40: return None
    return {"id": qid, "platform_q": "okwave", "title": title, "text": body,
            "url": f"https://okwave.jp/qa/q{qid}.html"}

# ---------- Naver Kin ----------
def kin_links(term, pages=40):
    links = []
    for p in range(1, pages + 1):
        u = f"https://kin.naver.com/search/list.naver?query={requests.utils.quote(term)}&page={p}"
        txt = get(u)
        if not txt: break
        new = []
        for m in re.finditer(r'href="(https://kin\.naver\.com/qna/detail\.naver\?[^"]+)"', txt):
            href = html.unescape(m.group(1))
            if href not in links and href not in new: new.append(href)
        links += new
        print("kin", term, "page", p, "total", len(links), flush=True)
        if not new: break
        time.sleep(0.4)
    return links

def kin_fetch(url):
    txt = get(url)
    if not txt or "삭제된 게시물" in txt: return None
    title = ""
    tm = re.search(r'class="title"[^>]*>(.*?)</', txt, re.S)
    if tm: title = strip(tm.group(1))
    parts = [title] if title else []
    for cls in ("se-main-container", "_questionContents", "question-content", "_answerContents", "answer-content"):
        for m in re.finditer(r'class="[^"]*' + cls + r'[^"]*"[^>]*>(.*?)</div>', txt, re.S):
            s = strip(m.group(1))
            if len(s) >= 20 and s not in parts: parts.append(s)
    body = "\n".join(parts)
    doc = re.search(r"docId=(\d+)", url)
    if len(body) < 40: return None
    return {"id": doc.group(1) if doc else url, "platform_q": "kin", "title": title, "text": body, "url": url}

def run(name, links, fetch, outfile, workers=5):
    print(name, "targets:", len(links), flush=True)
    cnt = {"n": 0}
    def work(x):
        try:
            row = fetch(x)
            if row:
                with open(os.path.join(DATA, outfile), "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                cnt["n"] += 1
                if cnt["n"] % 100 == 0: print(name, "fetched", cnt["n"], flush=True)
        except Exception:
            pass
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, links))
    print(name, "DONE", cnt["n"], flush=True)

def main():
    jobs = []
    chie_ids = []
    for term in ["うつ病", "抑うつ"]:
        chie_ids += [i for i in chie_links(term, 50) if i not in chie_ids]
    jobs.append(("CHIEBUKURO", chie_ids, chie_fetch, "chiebukuro_posts.jsonl"))
    okw_ids = []
    for term in ["うつ病", "抑うつ"]:
        okw_ids += [i for i in okw_links(term, 30) if i not in okw_ids]
    jobs.append(("OKWAVE", okw_ids, okw_fetch, "okwave_posts.jsonl"))
    kin_ls = []
    for term in ["우울증", "우울"]:
        kin_ls += [l for l in kin_links(term, 30) if l not in kin_ls]
    jobs.append(("KIN", kin_ls, kin_fetch, "kin_posts.jsonl"))
    for name, links, fetch, outfile in jobs:
        run(name, links, fetch, outfile)
    print("QNA WAVE DONE")

if __name__ == "__main__":
    main()
