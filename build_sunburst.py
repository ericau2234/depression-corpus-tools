#!/usr/bin/env python3
"""Assemble the 3-level sunburst (HTML) from sub_results_v3.json + fine_*_fine.json."""
import json, os
BASE = os.path.dirname(os.path.abspath(__file__))
v3 = json.load(open(os.path.join(BASE, "sub_results_v3.json"), encoding="utf-8"))
TOTALS, COUNTS = v3["totals"], v3["counts"]
CLASSIFIED = 446532

FINE = {
 "rent": ("经济窘迫(严)", "房租/住房/房贷"),
 "income": ("经济窘迫(严)", "没收入/失业断粮"),
 "loans": ("经济窘迫(严)", "学生贷款"),
 "debt": ("经济窘迫(严)", "债务(非学贷)"),
 "medcost": ("经济窘迫(严)", "看不起病/药费"),
 "famconf": ("家庭/父母", "家暴/父母冲突"),
 "study": ("工作/学业", "学业/考试压力"),
 "breakup": ("亲密关系", "分手/被拒"),
 "divorce": ("亲密关系", "离婚/分居"),
 "cheat": ("亲密关系", "出轨/背叛"),
 "nofriends": ("孤独/孤立", "没朋友"),
 "emoabuse": ("童年创伤/虐待", "情感虐待/贬低"),
 "sa": ("童年创伤/虐待", "性虐待"),
 "alc": ("童年创伤/虐待", "父母酗酒/成瘾"),
 "mom": ("丧亲/丧失", "丧母"),
 "dad": ("丧亲/丧失", "丧父"),
 "pain": ("疾病/疼痛", "慢性疼痛"),
}
fine_by_sub = {}
for prefix, (cat, sub) in FINE.items():
    p = os.path.join(BASE, f"fine_{prefix}_fine.json")
    if os.path.exists(p):
        fine_by_sub[(cat, sub)] = json.load(open(p, encoding="utf-8"))

def build():
    root = {"name": f"已分类帖", "value": CLASSIFIED, "children": []}
    for cat, tot in sorted(TOTALS.items(), key=lambda kv: -kv[1]):
        cnode = {"name": cat, "value": tot, "children": []}
        for sub, c in sorted(COUNTS.get(cat, {}).items(), key=lambda kv: -kv[1]):
            snode = {"name": sub, "value": c, "children": []}
            fb = fine_by_sub.get((cat, sub))
            if fb:
                ssum = 0
                for item, ic in sorted(fb["counts"].items(), key=lambda kv: -kv[1]):
                    if ic > 0:
                        snode["children"].append({"name": item, "value": ic})
                        ssum += ic
                rem = fb["n"] - ssum
                if rem > 0:
                    snode["children"].append({"name": "池内其他（未明文细述）", "value": rem, "other": True})
                snode["pool"] = fb["n"]
            if snode["children"]:
                cnode["children"].append(snode)
            else:
                cnode["children"].append({"name": sub, "value": c})
        root["children"].append(cnode)
    return root

DATA = build()
html = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>抑郁成因 · 三层圈图</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<style>
body{font-family:-apple-system,"PingFang HK","Microsoft YaHei",sans-serif;margin:0;background:#faf8f5;color:#222}
#wrap{display:flex;gap:8px;max-width:1280px;margin:0 auto;padding:16px}
#chart{flex:0 0 760px}
#panel{flex:1;padding:18px 8px}
#panel h1{font-size:20px;margin:0 0 6px}
#panel .sub{color:#666;font-size:13px;line-height:1.7}
#info{margin-top:16px;background:#fff;border:1px solid #e5ded4;border-radius:10px;padding:14px 16px;min-height:120px}
#info .path{font-size:15px;font-weight:600;line-height:1.6}
#info .num{font-size:14px;color:#444;line-height:1.9;margin-top:6px}
.note{font-size:12px;color:#888;line-height:1.8;margin-top:14px}
text{pointer-events:none}
</style></head><body>
<div id="wrap"><div id="chart"></div><div id="panel">
<h1>人为什么会抑郁 · 三层圈图</h1>
<div class="sub">中心向外：一级大类 → 二级细项 → 三级具体原因。<br>点任何一格可以放大嗰一支，再点中心返出嚟；鼠标停喺格上，右边会出成条路径同数字。</div>
<div id="info"><div class="path">将鼠标移到图上</div><div class="num">分母口径：一级 = 每一百篇已分类帖；二级 = 每一百篇该大类帖；三级 = 每一百篇该细项帖。</div></div>
<div class="note">注：多标签计数（一帖可入多类），环宽按命中帖数计，非互斥切分。二级共现类数字为上限估计（实数约六七成）；三级为明文短语计数，系下限。数据为 2026-11-03 中期清洗快照（Reddit 长帖）；三级已完成 17 支，其余各支会在最终版补齐，届时全图以最终清洗数重出。</div>
</div></div>
<script>
const DATA = __DATA__;
const CLASSIFIED = __CLS__;
const width = 760, radius = width/2;
const color = d3.scaleOrdinal(d3.quantize(d3.interpolateRainbow, DATA.children.length+1));
const svg = d3.select("#chart").append("svg").attr("width",width).attr("height",width)
  .style("font","11px sans-serif");
const g = svg.append("g").attr("transform",`translate(${radius},${radius})`);
const partition = d3.partition().size([2*Math.PI, radius]);
const root0 = d3.hierarchy(DATA).sum(d=>d.children?0:d.value).sort((a,b)=>b.value-a.value);
partition(root0);
root0.each(d=>d.current=d);
const arc = d3.arc().startAngle(d=>d.x0).endAngle(d=>d.x1)
  .padAngle(d=>Math.min((d.x1-d.x0)/2,0.005)).padRadius(radius/2)
  .innerRadius(d=>d.y0).outerRadius(d=>d.y1-1);
function col(d){ while(d.depth>1) d=d.parent; return color(d.data.name); }
const path = g.selectAll("path").data(root0.descendants().slice(1)).join("path")
  .attr("fill", d=> d.data.other ? "#ddd6cc" : col(d))
  .attr("fill-opacity", d=> d.depth===3?0.75:(d.depth===2?0.88:1))
  .attr("d", d=>arc(d.current))
  .style("cursor","pointer")
  .on("click", clicked).on("mouseover", hover);
const label = g.append("g").attr("text-anchor","middle").selectAll("text")
  .data(root0.descendants().slice(1)).join("text")
  .attr("transform", d=>labelTransform(d.current))
  .attr("dy","0.35em").text(d=> (d.x1-d.x0)>0.035 ? d
...[truncated 2524 chars].data.name.slice(0,7) : "");
function labelTransform(d){ const x=(d.x0+d.x1)/2*180/Math.PI, y=(d.y0+d.y1)/2; return `rotate(${x-90}) translate(${y},0) rotate(${x<180?0:180})`; }
const center = g.append("circle").attr("r", root0.y1/3.2).attr("fill","#fff").style("cursor","pointer").on("click", clicked);
const ctext = g.append("text").attr("text-anchor","middle").attr("dy","0.35em").style("font-size","15px").style("font-weight","600").text("已分类帖");
function hover(event,d){
  const chain=[]; let n=d;
  while(n && n.depth>0){ chain.unshift(n); n=n.parent; }
  const parts = chain.map(n=>n.data.name);
  let num;
  if(d.depth===1) num = `占已分类帖：每一百篇有 ${Math.round(1000*d.data.value/CLASSIFIED)/10} 篇（共 ${d.data.value.toLocaleString()} 篇）`;
  else if(d.depth===2) num = `占所属大类：每一百篇有 ${Math.round(1000*d.data.value/d.parent.data.value)/10} 篇（共 ${d.data.value.toLocaleString()} 篇）`;
  else num = `占所属细项帖池：每一百篇有 ${Math.round(1000*d.data.value/(d.parent.data.pool||d.parent.data.value))/10} 篇（共 ${d.data.value.toLocaleString()} 篇）`;
  document.getElementById("info").innerHTML = `<div class="path">${parts.join(" › ")}</div><div class="num">${num}</div>`;
}
function clicked(event, p){
  root0.each(d=> d.target = {
    x0: (d.x0 - p.x0) / (p.x1 - p.x0) * 2 * Math.PI,
    x1: (d.x1 - p.x0) / (p.x1 - p.x0) * 2 * Math.PI,
    y0: Math.max(0, d.y0 - p.depth), y1: Math.max(0, d.y1 - p.depth) });
  const t = svg.transition().duration(650);
  path.transition(t).attrTween("d", d=>{ const i = d3.interpolate(d.current, d.target); return tt => (d.current = i(tt), arc(d.current)); });
  label.transition(t).attrTween("transform", d=>{ const i = d3.interpolate(d.current, d.target); return tt => labelTransform(i(tt)); });
  ctext.text(p.depth===0 ? "已分类帖" : p.data.name.slice(0,8));
}
</script></body></html>
"""
html = html.replace("__DATA__", json.dumps(DATA, ensure_ascii=False)).replace("__CLS__", str(CLASSIFIED))
out = os.path.expanduser("~/workspace/your_files/忧郁成因三层圈图.html")
open(out, "w", encoding="utf-8").write(html)
print("wrote", out)
