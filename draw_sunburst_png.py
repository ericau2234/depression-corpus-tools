#!/usr/bin/env python3
"""Static PNG rendering of the 3-level sunburst (for in-chat viewing)."""
import json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
from matplotlib import font_manager

BASE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "Noto Sans CJK JP"

v3 = json.load(open(os.path.join(BASE, "sub_results_v3.json"), encoding="utf-8"))
TOTALS, COUNTS = v3["totals"], v3["counts"]
CLASSIFIED = 446532
FINE = {
 "rent": ("经济窘迫(严)", "房租/住房/房贷"), "income": ("经济窘迫(严)", "没收入/失业断粮"),
 "loans": ("经济窘迫(严)", "学生贷款"), "debt": ("经济窘迫(严)", "债务(非学贷)"),
 "medcost": ("经济窘迫(严)", "看不起病/药费"), "famconf": ("家庭/父母", "家暴/父母冲突"),
 "study": ("工作/学业", "学业/考试压力"), "breakup": ("亲密关系", "分手/被拒"),
 "divorce": ("亲密关系", "离婚/分居"), "cheat": ("亲密关系", "出轨/背叛"),
 "nofriends": ("孤独/孤立", "没朋友"), "emoabuse": ("童年创伤/虐待", "情感虐待/贬低"),
 "sa": ("童年创伤/虐待", "性虐待"), "alc": ("童年创伤/虐待", "父母酗酒/成瘾"),
 "mom": ("丧亲/丧失", "丧母"), "dad": ("丧亲/丧失", "丧父"), "pain": ("疾病/疼痛", "慢性疼痛"),
}
fine_by_sub = {}
for prefix, key in FINE.items():
    p = os.path.join(BASE, f"fine_{prefix}_fine.json")
    if os.path.exists(p): fine_by_sub[key] = json.load(open(p, encoding="utf-8"))

def node_val(cat, sub):
    fb = fine_by_sub.get((cat, sub))
    return fb["n"] if fb else COUNTS[cat][sub]

# layout: returns list of (name, depth, a0, a1, value, cat_root)
segs = []
def layout_cat(cat, a0, a1):
    subs = sorted(COUNTS.get(cat, {}).items(), key=lambda kv: -node_val(cat, kv[0]))
    tot = sum(node_val(cat, s) for s, _ in subs) or 1
    a = a0
    for sub, _ in subs:
        v = node_val(cat, sub)
        b = a + (a1 - a0) * v / tot
        segs.append((sub, 2, a, b, v, cat))
        fb = fine_by_sub.get((cat, sub))
        if fb:
            items = sorted(fb["counts"].items(), key=lambda kv: -kv[1])
            ssum = sum(max(c, 0) for _, c in items if c > 0)
            x = a
            for name, c in items:
                if c <= 0: continue
                y = x + (b - a) * c / fb["n"]
                segs.append((name, 3, x, y, c, cat))
                x = y
            rem = fb["n"] - ssum
            if rem > 0:
                segs.append(("池内其他", 3, x, b, rem, cat))
        a = b

cats = sorted(TOTALS.items(), key=lambda kv: -sum(node_val(kv[0], s) for s in COUNTS.get(kv[0], {})))
grand = sum(sum(node_val(c, s) for s in COUNTS.get(c, {})) for c, _ in cats)
a = 90.0
cat_spans = {}
for cat, _ in cats:
    v = sum(node_val(cat, s) for s in COUNTS.get(cat, {}))
    b = a - 360.0 * v / grand
    cat_spans[cat] = (b, a)
    segs.append((cat, 1, b, a, TOTALS[cat], cat))
    a = b
for cat, _ in cats:
    lo, hi = cat_spans[cat]
    layout_cat(cat, lo, hi)

BASE_COLORS = {}
cmap = plt.get_cmap("tab20")
for i, (cat, _) in enumerate(cats):
    BASE_COLORS[cat] = cmap(i % 20)

def shade(cat, depth, other=False):
    if other: return (0.82, 0.80, 0.76, 1.0)
    r, g, bl, _ = BASE_COLORS[cat]
    f = {1: 0.0, 2: 0.25, 3: 0.48}[depth]
    return (r + (1 - r) * f, g + (1 - g) * f, bl + (1 - bl) * f, 1.0)

R = {1: (0.34, 0.55), 2: (0.55, 0.76), 3: (0.76, 1.0)}
fig, ax = plt.subplots(figsize=(26, 29), dpi=100)
ax.set_xlim(-1.12, 1.12); ax.set_ylim(-1.24, 1.14); ax.set_aspect("equal"); ax.axis("off")
for name, depth, a0, a1, val, cat in segs:
    r0, r1 = R[depth]
    w = Wedge((0, 0), r1, a0, a1, width=r1 - r0,
              facecolor=shade(cat, depth, name == "池内其他"),
              edgecolor="white", linewidth=1.1 if depth < 3 else 0.5)
    ax.add_patch(w)
    ang = a1 - a0
    mid = math.radians((a0 + a1) / 2)
    rm = (r0 + r1) / 2
    x, y = rm * math.cos(mid), rm * math.sin(mid)
    deg = (a0 + a1) / 2
    if depth == 1 and ang > 4:
        rot = deg - 90 if 90 < deg % 360 < 270 else deg + 90
        if not (90 < deg % 360 < 270): rot = deg - 90
        ax.text(x, y, f"{name}\n{round(100*val/CLASSIFIED,1)}%", ha="center", va="center",
                rotation=deg + 90 if 90 < deg % 360 < 270 else deg - 90,
                fontsize=17, fontweight="bold", color="#1a1a1a")
    elif depth == 2 and ang > 1.6:
        ax.text(x, y, name, ha="center", va="center",
                rotation=deg if deg % 360 <= 180 else deg + 180,
                fontsize=13.5, color="#222")
    elif depth == 3 and ang > 2.4 and name != "池内其他":
        ax.text(x, y, name, ha="center", va="center",
                rotation=deg if deg % 360 <= 180 else deg + 180,
                fontsize=11.5, color="#333")
ax.text(0, 0.05, "已分类帖", ha="center", va="center", fontsize=26, fontweight="bold")
ax.text(0, -0.09, f"{CLASSIFIED:,}", ha="center", va="center", fontsize=20, color="#444")
ax.text(0, 1.10, "人为什么会抑郁 · 三层圈图（第一圈大类 → 第二圈细项 → 最外圈具体原因）",
        ha="center", va="center", fontsize=23, fontweight="bold")
ax.text(0, -1.17, "多标签计数，环宽按命中帖数；二级共现类为上限估计，三级为明文短语下限；数据为中期快照，三级已完成 17 支，其余最终版补齐。",
        ha="center", va="center", fontsize=14, color="#777")
out = os.path.expanduser("~/workspace/your_files/忧郁成因三层圈图.png")
fig.savefig(out, bbox_inches="tight", facecolor="#faf8f5")
print("wrote", out)
