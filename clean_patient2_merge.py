#!/usr/bin/env python3
"""Merge Patient.info wave 2 into data_clean/patient_clean.jsonl.

Reuses clean_v22.py's patient path exactly: cc.generic("patient2_posts.jsonl",
"patient", "en") for row building, and clean_v22.stream_emit's dedupe rule
(id first, then thash(author, text or title)) seeded with the existing
wave-1 clean records. The pre-merge clean file is backed up to
patient_clean_wave1_backup.jsonl; if that backup already exists it is used
as the baseline (idempotent re-runs).
Also measures how many wave-1 raw posts (data/patient_posts.jsonl, cleaned
via cc.patient()) are textually present in the merged file.
Writes patient_merge_stats.json.
"""
import json, os, sys, shutil, hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import clean_corpus as cc

OUT = cc.OUT
CLEAN = os.path.join(OUT, "patient_clean.jsonl")
BACKUP = os.path.join(OUT, "patient_clean_wave1_backup.jsonl")


def file_rows(path):
    rows = []
    for l in open(path, encoding="utf-8"):
        try:
            rows.append(json.loads(l))
        except Exception:
            pass
    return rows


def main():
    if not os.path.exists(BACKUP):
        shutil.copyfile(CLEAN, BACKUP)
        print("backup written:", BACKUP, flush=True)
    else:
        print("backup already exists, using it as baseline:", BACKUP, flush=True)
    base_rows = file_rows(BACKUP)
    seen_id, seen_hash = set(), set()
    for r in base_rows:
        seen_id.add(r["id"])
        seen_hash.add(cc.thash(r.get("author"), r["text"] or r.get("title") or ""))

    raw_lines = sum(1 for _ in open(os.path.join(cc.DATA, "patient2_posts.jsonl"),
                                     encoding="utf-8"))
    gen_rows = cc.generic("patient2_posts.jsonl", "patient", "en")
    st = {"raw_lines": raw_lines, "generic_kept": len(gen_rows),
          "drop_short_or_bad": raw_lines - len(gen_rows),
          "drop_id_dup": 0, "drop_text_dup": 0, "new_kept": 0}
    new_rows = []
    for r in gen_rows:
        if r["id"] in seen_id:
            st["drop_id_dup"] += 1
            continue
        h = cc.thash(r.get("author"), r["text"] or r.get("title") or "")
        if h in seen_hash:
            st["drop_text_dup"] += 1
            continue
        seen_id.add(r["id"])
        seen_hash.add(h)
        new_rows.append(r)
        st["new_kept"] += 1

    with open(CLEAN, "w", encoding="utf-8") as f:
        for r in base_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        for r in new_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # wave-1 raw coverage check (cc.patient() schema rows)
    w1 = cc.patient()
    merged_texts = {((r.get("text") or "").lower()) for r in base_rows}
    merged_texts |= {(r["text"].lower()) for r in new_rows}
    w1_present = sum(1 for r in w1 if r["text"].lower() in merged_texts)

    stats = {"baseline_rows": len(base_rows), "patient2": st,
             "merged_total": len(base_rows) + st["new_kept"],
             "wave1_raw_posts_via_cc_patient": len(w1),
             "wave1_raw_textually_present_in_merged": w1_present}
    json.dump(stats, open(os.path.join(BASE, "patient_merge_stats.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
