#!/usr/bin/env python3
"""INTERIM merge: deep2 snapshot (.deep2_snap/, only .done windows) cleaned
with the exact rules of clean_v22.py and cross-deduped against the existing
clean sets. Existing clean rows are copied verbatim FIRST (they win dedup,
same as clean_v22's stream order); newly kept deep2 rows are appended.
Outputs data_clean/reddit_interim_clean.jsonl and
data_clean/reddit_comments_interim_clean.jsonl. Existing clean files are
NOT modified. Dedup: by id, then by thash(author, text or title) -- the
same two keys as clean_v22.stream_emit (md5 digest bytes used instead of
hexdigest; equality semantics identical).
"""
import json, os, glob, sys, gc, hashlib
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import clean_corpus as cc
import clean_v22 as cv2

norm, lang_of = cc.norm, cc.lang_of
SNAP = os.path.join(BASE, ".deep2_snap")
OUT = cc.OUT


def digest(author, text):
    return hashlib.md5((str(author or "") + "|" + (text or "").lower()).encode("utf-8")).digest()


def load_existing(path, fout):
    """Copy existing clean file verbatim to fout; return (n, id_set, hash_set)."""
    ids, hashes = set(), set()
    n = 0
    with open(path, encoding="utf-8") as fin, open(fout, "w", encoding="utf-8") as fo:
        for line in fin:
            fo.write(line)
            try:
                d = json.loads(line)
            except Exception:
                continue
            n += 1
            ids.add(d["id"])
            hashes.add(digest(d.get("author"), d["text"] or d.get("title") or ""))
    return n, ids, hashes


def dedupe_new(row, ex_ids, ex_hashes, new_ids, new_hashes, st):
    h = digest(row.get("author"), row["text"] or row.get("title") or "")
    if row["id"] in ex_ids:
        st["dup_existing_id"] += 1; return False
    if h in ex_hashes:
        st["dup_existing_hash"] += 1; return False
    if row["id"] in new_ids:
        st["dup_within_id"] += 1; return False
    if h in new_hashes:
        st["dup_within_hash"] += 1; return False
    new_ids.add(row["id"]); new_hashes.add(h)
    return True


def run_posts():
    st = {"snapshot_rows_in": 0, "parse_fail": 0, "drop_author_filter": 0,
          "dup_existing_id": 0, "dup_existing_hash": 0,
          "dup_within_id": 0, "dup_within_hash": 0, "kept_new": 0}
    fout = os.path.join(OUT, "reddit_interim_clean.jsonl")
    ex_n, ex_ids, ex_hashes = load_existing(os.path.join(OUT, "reddit_clean.jsonl"), fout)
    st["existing_rows"] = ex_n
    new_ids, new_hashes = set(), set()
    with open(fout, "a", encoding="utf-8") as fo:
        for fn in sorted(glob.glob(os.path.join(SNAP, "posts_*.jsonl"))):
            with open(fn, encoding="utf-8") as f:
                for line in f:
                    st["snapshot_rows_in"] += 1
                    try:
                        d = json.loads(line)
                    except Exception:
                        st["parse_fail"] += 1; continue
                    r = cv2.reddit_post_row(d, "reddit_deep2")
                    if r is None:
                        st["drop_author_filter"] += 1; continue
                    if dedupe_new(r, ex_ids, ex_hashes, new_ids, new_hashes, st):
                        st["kept_new"] += 1
                        fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            print("posts done file", os.path.basename(fn), st["kept_new"], flush=True)
    st["merged_total"] = ex_n + st["kept_new"]
    print("POSTS", json.dumps(st), flush=True)
    del ex_ids, ex_hashes, new_ids, new_hashes
    gc.collect()
    return st


def comment_row(d):
    """Identical logic to clean_v22.reddit_comments_gen; returns (row, drop_reason)."""
    body = norm(d.get("body"))
    if body in ("[removed]", "[deleted]"):
        return None, "drop_removed"
    if d.get("author") in ("[deleted]", "AutoModerator"):
        return None, "drop_author_filter"
    if len(body) < 10:
        return None, "drop_short"
    return {"platform": "reddit_comments", "kind": "reddit_comments",
            "id": str(d.get("id")), "title": "", "text": body,
            "author": d.get("author"), "lang": lang_of(body, "en"),
            "chars": len(body), "created": d.get("created_utc"),
            "url": None, "subreddit": d.get("subreddit"),
            "score": d.get("score")}, None


def run_comments():
    st = {"snapshot_rows_in": 0, "parse_fail": 0, "drop_removed": 0,
          "drop_author_filter": 0, "drop_short": 0,
          "dup_existing_id": 0, "dup_existing_hash": 0,
          "dup_within_id": 0, "dup_within_hash": 0, "kept_new": 0}
    fout = os.path.join(OUT, "reddit_comments_interim_clean.jsonl")
    ex_n, ex_ids, ex_hashes = load_existing(os.path.join(OUT, "reddit_comments_clean.jsonl"), fout)
    st["existing_rows"] = ex_n
    new_ids, new_hashes = set(), set()
    with open(fout, "a", encoding="utf-8") as fo:
        for fn in sorted(glob.glob(os.path.join(SNAP, "comments_*.jsonl"))):
            with open(fn, encoding="utf-8") as f:
                for line in f:
                    st["snapshot_rows_in"] += 1
                    try:
                        d = json.loads(line)
                    except Exception:
                        st["parse_fail"] += 1; continue
                    r, why = comment_row(d)
                    if r is None:
                        st[why] += 1; continue
                    if dedupe_new(r, ex_ids, ex_hashes, new_ids, new_hashes, st):
                        st["kept_new"] += 1
                        fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            print("comments done file", os.path.basename(fn), st["kept_new"], flush=True)
    st["merged_total"] = ex_n + st["kept_new"]
    print("COMMENTS", json.dumps(st), flush=True)
    del ex_ids, ex_hashes, new_ids, new_hashes
    gc.collect()
    return st


def main():
    stats = {"posts": run_posts(), "comments": run_comments()}
    with open(os.path.join(BASE, "interim_clean_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print("WROTE interim_clean_stats.json", flush=True)


if __name__ == "__main__":
    main()
