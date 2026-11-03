#!/usr/bin/env python3
"""Full-corpus classification + economic-trace measurement, all cleaned platforms.
Adds JA/KO/RU/DE dictionaries to the EN/ZH ones from classify_causes.py.
Long posts only (chars>=200) except bilibili articles/dcard short sets (minc=0 noted)."""
import json, os

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "classify_causes.py")).read().split("def main")[0])

JA = {
    "经济窘迫(严)": ["借金", "負債", "失業", "無職", "金欠", "貧乏", "返済できない", "生活苦", "ローンの返済"],
    "工作/学业": ["仕事", "会社", "上司", "残業", "学校", "勉強", "受験", "職場", "ブラック企業"],
    "家庭/父母": ["家族", "両親", "母親", "父親", "実家", "毒親", "親"],
    "童年创伤/虐待": ["子供の頃", "幼少期", "虐待", "ネグレクト", "いじめられ"],
    "亲密关系": ["離婚", "彼氏", "彼女", "夫", "妻", "浮気", "別れた"],
    "孤独/孤立": ["孤独", "寂しい", "友達がいない", "一人ぼっち"],
    "疾病/疼痛": ["痛み", "癌", "病気", "障害", "持病", "通院"],
    "丧亲/丧失": ["亡くな", "死別", "葬式", "喪失感"],
    "睡眠": ["不眠", "眠れない", "睡眠障害"],
    "产后": ["産後"],
    "无缘无故": ["理由がない", "原因不明", "突然", "なぜか分からない"],
    "遗传/家族史": ["遺伝", "家系"],
    "困住/逃不掉": ["辞められない", "逃げられない", "追い詰め", "行き詰ま", "どうしようもない"],
}
TRACE_JA = ["お金", "金銭", "給料", "年収", "月収", "家賃", "生活費", "貯金", "借金", "ローン", "支払い",
            "料金", "費用", "収入", "保険料", "年金", "高い", "バイト"]
KO = {
    "经济窘迫(严)": ["빚", "채무", "실업", "무직", "돈이 없", "가난", "대출금", "생활고"],
    "工作/学业": ["직장", "회사", "상사", "야근", "학교", "공부", "시험", "취업"],
    "家庭/父母": ["가족", "부모", "어머니", "아버지", "엄마", "아빠"],
    "童年创伤/虐待": ["어린 시절", "학대", "방치", "왕따"],
    "亲密关系": ["이혼", "헤어졌", "남자친구", "여자친구", "남편", "아내", "결혼"],
    "孤独/孤立": ["외로", "고립", "친구가 없"],
    "疾病/疼痛": ["통증", "암", "질병", "장애", "만성"],
    "丧亲/丧失": ["돌아가신", "장례", "사별", "상실"],
    "睡眠": ["불면", "잠이 안", "수면장애"],
    "产后": ["산후"],
    "无缘无故": ["이유 없이", "원인 모", "갑자기"],
    "遗传/家族史": ["유전", "가족력"],
    "困住/逃不掉": ["그만둘 수 없", "도망칠", "벗어날 수 없", "막막"],
}
TRACE_KO = ["돈", "월급", "연봉", "월세", "전세", "대출", "생활비", "저축", "빚", "비용", "수입", "알바", "보험료", "비싸"]
RU = {
    "经济窘迫(严)": ["долги", "долг", "безработ", "нет денег", "бедност", "нищет", "кредит не"],
    "工作/学业": ["работа", "начальник", "учёба", "школа", "университет", "экзамены"],
    "家庭/父母": ["семья", "родители", "мать", "отец", "мама", "папа"],
    "童年创伤/虐待": ["детство", "детстве", "насилие", "издевательства"],
    "亲密关系": ["развод", "расстались", "жена", "муж", "девушка", "парень", "измена"],
    "孤独/孤立": ["одиночество", "одиноко", "нет друзей", "изоляция"],
    "疾病/疼痛": ["боль", "рак", "болезнь", "инвалид", "хроническ"],
    "丧亲/丧失": ["умер", "похороны", "потерял", "горе"],
    "睡眠": ["бессонница", "не могу спать"],
    "产后": ["послеродов"],
    "无缘无故": ["без причины", "непонятно почему", "внезапно"],
    "遗传/家族史": ["наследствен", "генетич"],
    "困住/逃不掉": ["в ловушке", "нет выхода", "не могу уволиться", "вынужден"],
}
TRACE_RU = ["деньги", "денег", "зарплата", "аренда", "ипотека", "кредит", "счета", "цены", "дорого",
            "доход", "сбережения", "платить", "стоимость"]
DE = {
    "经济窘迫(严)": ["schulden", "arbeitslos", "kein geld", "armut", "bürgergeld", "hartz"],
    "工作/学业": ["arbeit", "job", "chef", "schule", "studium", "prüfung"],
    "家庭/父母": ["familie", "eltern", "mutter", "vater"],
    "童年创伤/虐待": ["kindheit", "missbrauch", "vernachlässigung"],
    "亲密关系": ["scheidung", "getrennt", "freundin", "ehemann", "ehefrau", "betrogen"],
    "孤独/孤立": ["einsam", "einsamkeit", "keine freunde"],
    "疾病/疼痛": ["schmerzen", "krebs", "krankheit", "behinderung", "chronisch"],
    "丧亲/丧失": ["verstorben", "beerdigung", "trauer"],
    "睡眠": ["schlaflosigkeit", "kann nicht schlafen", "schlafprobleme"],
    "产后": ["nach der geburt", "wochenbett"],
    "无缘无故": ["ohne grund", "aus dem nichts", "weiß nicht warum"],
    "遗传/家族史": ["vererbung", "genetisch", "familiär"],
    "困住/逃不掉": ["gefangen", "kein ausweg", "festgefahren"],
}
TRACE_DE = ["geld", "gehalt", "miete", "rechnungen", "schulden", "kosten", "teuer", "sparen",
            "einkommen", "versicherung", "lohn"]
TRACE_EN2 = ["money", "salary", "wage", "wages", "paycheck", "rent", "mortgage", "bills", "groceries",
             "tuition", "loan", "loans", "insurance", "expensive", "cheap", "afford", "budget", "savings",
             "save up", "overtime", "second job", "part-time", "part time", "minimum wage", "income",
             "financial", "broke", "debt", "payment", "cost of", "costs", "pay for", "side hustle",
             "cost of living", "unemployed", "fired", "laid off", "price", "prices", "dollars", "earn a living"]
TRACE_ZH2 = ["钱", "工资", "收入", "房租", "房贷", "贷款", "账单", "学费", "生活费", "物价", "省钱",
             "存钱", "借钱", "还钱", "兼职", "打工", "赚钱", "花销", "开支", "费用", "医药费",
             "治疗费", "月薪", "年薪", "奖金", "经济", "贵", "便宜"]

def run(name, fn, lang_filter, dicts, trace, lower, minc=200):
    rows = load(fn, minc=minc, lang=lang_filter)
    if not rows:
        print(f"===== {name} n=0 SKIP", flush=True)
        return name, 0, {}
    n, out = classify(rows, dicts, lower)
    tr = 0
    for r in rows:
        t = (r.get("title") or "") + " " + (r.get("text") or "")
        if lower: t = t.lower()
        if any(w in t for w in trace): tr += 1
    out["_经济痕迹(宽)"] = round(100 * tr / max(1, n), 1)
    print(f"===== {name} n={n}")
    for k, v in sorted(out.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}%")
    print(flush=True)
    return name, n, out

def main():
    res = {}
    extra = [
        ("5ch短帖口径(≥30字)", "fivech_clean.jsonl", None, JA, TRACE_JA, False, 30),
        ("LIHKG短帖口径(≥30字)", "lihkg_clean.jsonl", None, ZH, TRACE_ZH2, False, 30),
        ("2ch短帖口径(≥30字)", "twoch_clean.jsonl", None, RU, TRACE_RU, True, 30),
        ("DC短帖口径(≥30字)", "dcinside_clean.jsonl", None, KO, TRACE_KO, False, 30),
    ]
    for args in [
        ("Reddit长帖", "reddit_clean.jsonl", None, EN, TRACE_EN2, True),
        ("BeyondBlue长帖", "beyondblue_clean.jsonl", None, EN, TRACE_EN2, True),
        ("MHF长帖", "mhf_clean.jsonl", None, EN, TRACE_EN2, True),
        ("PsychForums长帖", "psychforums_clean.jsonl", None, EN, TRACE_EN2, True),
        ("Patient长帖", "patient_clean.jsonl", None, EN, TRACE_EN2, True),
        ("中文HF长帖", "huggingface_clean.jsonl", "zh", ZH, TRACE_ZH2, False),
        ("LIHKG长帖(粤)", "lihkg_clean.jsonl", None, ZH, TRACE_ZH2, False),
        ("5ch长帖(日)", "fivech_clean.jsonl", None, JA, TRACE_JA, False),
        ("知恵袋(日)", "chiebukuro_clean.jsonl", None, JA, TRACE_JA, False),
        ("OKWave(日·短文本)", "okwave_clean.jsonl", None, JA, TRACE_JA, False, 0),
        ("DCInside长帖(韩)", "dcinside_clean.jsonl", None, KO, TRACE_KO, False),
        ("NaverKin(韩)", "kin_clean.jsonl", None, KO, TRACE_KO, False),
        ("2ch长帖(俄)", "twoch_clean.jsonl", None, RU, TRACE_RU, True),
        ("Hilferuf长帖(德)", "hilferuf_clean.jsonl", None, DE, TRACE_DE, True),
    ]:
        name, n, out = run(*args)
        res[name] = {"n": n, "pct": out}
    for args in extra:
        name, n, out = run(*args)
        res[name] = {"n": n, "pct": out}
    name, n, out = run("B站专栏(短)", "bilibili_articles_clean.jsonl", None, ZH, TRACE_ZH2, False, minc=0)
    res[name] = {"n": n, "pct": out}
    name, n, out = run("Dcard(台)", "dcard_clean.jsonl", None, ZH, TRACE_ZH2, False, minc=0)
    res[name] = {"n": n, "pct": out}
    with open(os.path.join(BASE, "classification_all.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("CLASSIFY ALL DONE")

if __name__ == "__main__":
    main()
