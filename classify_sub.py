#!/usr/bin/env python3
"""Sub-cause breakdown within each top category (Reddit posts, >=200 chars).
Percentages: per 100 posts classified into the PARENT category.
Multi-label inside categories too. EN dicts primary (Reddit layer)."""
import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
try:
    import ahocorasick
except ImportError:
    sys.path.insert(0, os.path.join(BASE, "pylibs"))
    import ahocorasick
_hdr = open(os.path.join(BASE, "classify_all.py")).read().split("def run")[0]
exec(_hdr)  # EN dict for parent classification

SUBS = {
 "家庭/父母": {
  "父母控制/高压": ["controlling parents", "controlling mother", "controlling father", "strict parents", "helicopter parent", "tiger mom", "my parents control", "control my life", "控制欲", "逼我", "管得严"],
  "家暴/父母冲突": ["abusive father", "abusive mother", "my dad hit", "my mom hit", "parents fighting", "parents fought", "yelled at me", "screaming at me", "家暴", "打我", "父母吵架"],
  "冷漠/忽视": ["emotionally unavailable", "neglected", "never hugged", "never said i love", "cold mother", "cold father", "didn't care about me", "不管我", "冷漠", "忽视"],
  "父母离异/缺位": ["parents divorced", "parents' divorce", "single mother", "single father", "dad left", "father left", "absent father", "父母离婚", "单亲", "爸爸走了"],
  "期望/比较压力": ["parents' expectations", "high expectations", "disappointed in me", "compared me to", "never good enough for my parents", "望子成龙", "不如别人", "对我失望"],
  "照顾患病家人": ["caregiver", "taking care of my mom", "taking care of my dad", "caring for my mother", "caring for my father", "my mom's dementia", "照顾我妈", "照顾我爸", "看护"],
 },
 "工作/学业": {
  "过劳/倦怠": ["burnout", "burned out", "overworked", "no work-life", "60 hours", "overtime every", "加班", "过劳", "996", "倦怠"],
  "失业/求职失败": ["unemployed", "can't find a job", "cannot find a job", "got fired", "laid off", "lost my job", "job hunting", "失业", "找不到工作", "被裁"],
  "上司/同事/职场霸凌": ["my boss", "toxic boss", "bullied at work", "workplace bullying", "coworkers hate", "上司", "职场霸凌", "被同事"],
  "学业/考试压力": ["exam", "grades", "failed my", "thesis", "gpa", "finals", "考试", "成绩", "论文", "挂科", "高考"],
  "校园霸凌": ["bullied at school", "bullied by classmates", "school bullying", "校园霸凌", "被同学欺负", "霸凌"],
  "厌恶工作/无意义": ["hate my job", "hate my major", "meaningless job", "soul-crushing", "讨厌工作", "不想上班", "工作没意义"],
 },
 "亲密关系": {
  "分手/被拒": ["breakup", "broke up", "dumped me", "she left me", "he left me", "rejected me", "分手", "被甩", "被拒绝"],
  "出轨/背叛": ["cheated on me", "she cheated", "he cheated", "betrayed", "betrayal", "出轨", "背叛", "绿我"],
  "伴侣虐待/控制": ["abusive boyfriend", "abusive girlfriend", "abusive husband", "abusive wife", "abusive partner", "he hits me", "she hits me", "控制欲男友", "家暴男友"],
  "离婚/分居": ["divorce", "divorced", "ex-wife", "ex-husband", "separated", "离婚", "前妻", "前夫"],
  "长期单身/求偶失败": ["never had a girlfriend", "never had a boyfriend", "forever alone", "no one wants me", "incel", "母胎单身", "没人要", "单身久了"],
  "异地/感情变淡": ["long distance", "long-distance", "lost feelings", "fell out of love", "异地恋", "没感觉了", "感情淡了"],
 },
 "孤独/孤立": {
  "没朋友": ["no friends", "friendless", "have no friends", "zero friends", "没朋友", "一个朋友都没有"],
  "独居/迁居隔离": ["live alone", "living alone", "moved to a new city", "moved away", "no one to talk to", "独居", "搬到新城市", "没人说话"],
  "格格不入/被排斥": ["don't fit in", "do not fit in", "outcast", "left out", "excluded", "融不进去", "被排斥", "格格不入"],
 },
 "疾病/疼痛": {
  "慢性疼痛": ["chronic pain", "back pain", "fibromyalgia", "migraine", "慢性疼痛", "腰痛", "偏头痛"],
  "重病确诊": ["diagnosed with cancer", "i have cancer", "terminal", "diagnosed with ms", "癌症", "确诊", "绝症"],
  "残障/行动受限": ["disability", "disabled", "wheelchair", "can't walk", "残疾", "坐轮椅", "行动不便"],
  "长期慢性病": ["chronic illness", "diabetes", "autoimmune", "chronic fatigue", "慢性病", "糖尿病", "自身免疫"],
 },
 "童年创伤/虐待": {
  "身体虐待": ["physically abused", "used to beat me", "beat me", "spanked", "hit me as a child", "打骂", "体罚", "揍我"],
  "性虐待": ["sexually abused", "molested", "sexual abuse", "raped as", "性侵", "猥亵", "性虐待"],
  "情感虐待/贬低": ["emotionally abusive", "called me worthless", "called me stupid", "belittled", "verbal abuse", "冷暴力", "骂我废物", "贬低"],
  "童年忽视": ["neglected as a child", "childhood neglect", "left alone as a kid", "no one took care", "小时候没人管", "被忽视"],
  "目睹家暴/家庭破裂": ["watched my dad hit", "saw my father hit", "parents fought all the time", "violent home", "目睹家暴", "父母天天吵架"],
 },
 "丧亲/丧失": {
  "丧父/丧母": ["lost my mom", "lost my dad", "my mother died", "my father died", "mom passed away", "dad passed away", "妈妈去世", "爸爸去世", "母亲过世"],
  "丧偶": ["lost my wife", "lost my husband", "my wife died", "my husband died", "widow", "widower", "丧偶", "老婆去世", "老公去世"],
  "丧子/流产": ["lost my baby", "lost my child", "miscarriage", "my son died", "my daughter died", "流产", "孩子去世", "丧子"],
  "亲友自杀身亡": ["friend killed himself", "brother killed himself", "friend's suicide", "lost my friend to suicide", "朋友自杀", "哥哥自杀"],
  "宠物离世": ["lost my dog", "my dog died", "my cat died", "put my dog down", "狗去世", "猫去世", "宠物走了"],
 },
 "经济窘迫(严)": {
  "债务": ["in debt", "credit card debt", "student loan debt", "owe money", "欠债", "网贷", "负债", "信用卡欠"],
  "房租/住房/房贷": ["can't pay rent", "cannot pay rent", "eviction", "evicted", "homeless", "mortgage", "交不起房租", "房贷", "无家可归", "被房东赶"],
  "没收入/失业断粮": ["no income", "no money at all", "can't afford food", "food bank", "food stamps", "没收入", "没钱吃饭", "断粮"],
  "看不起病/药费": ["can't afford therapy", "cannot afford therapy", "can't afford my medication", "can't afford medication", "medical bills", "看不起病", "买不起药", "药费"],
  "低薪贫困": ["minimum wage", "low pay", "poor family", "grew up poor", "工资低", "家里穷", "穷人"],
 },
 "困住/逃不掉": {
  "照顾责任走不开": ["can't leave because of my kids", "have to take care of", "can't leave my mom", "can't leave my dad", "走不开", "要照顾", "孩子还小"],
  "经济上走不开": ["can't afford to leave", "can't afford to quit", "financially trapped", "辞不起", "离不开这份工", "没积蓄"],
  "关系里走不开": ["can't leave him", "can't leave her", "trapped in this marriage", "trapped in a relationship", "离不开他", "离不开她", "婚姻困住"],
 },
 "遗传/家族史": {
  "家族多人有病": ["runs in my family", "my mom has depression", "my mother has depression", "my dad has depression", "family history of depression", "妈妈也有抑郁症", "家族里", "遗传的"],
  "基因/检测提及": ["genetic", "genes", "23andme", "gene test", "基因", "遗传因素"],
 },
 "无缘无故": {
  "什么都有却抑郁": ["i have everything", "good life but", "great life but", "no reason to be depressed", "should be happy", "什么都有", "条件很好却", "不该抑郁"],
  "莫名发作": ["for no reason", "no reason at all", "out of nowhere", "just feel sad", "莫名其妙", "没理由", "突然就"],
 },
}

def main():
    parentA = ahocorasick.Automaton()
    for k, ws in EN.items():
        for w in ws:
            wl = w.lower()
            if wl in parentA: parentA.get(wl).add(k)
            else: parentA.add_word(wl, {k})
    parentA.make_automaton()
    subA = {}
    for cat, subs in SUBS.items():
        A = ahocorasick.Automaton()
        for sname, ws in subs.items():
            for w in ws:
                wl = w.lower()
                if wl in A: A.get(wl).add(sname)
                else: A.add_word(wl, {sname})
        A.make_automaton(); subA[cat] = A
    from collections import Counter
    counts = {cat: Counter() for cat in SUBS}
    totals = Counter()
    p = os.path.join(BASE, "data_clean", "reddit_clean.jsonl")
    for l in open(p, encoding="utf-8"):
        try: d = json.loads(l)
        except Exception: continue
        if (d.get("chars") or len(d.get("text") or "")) < 200: continue
        t = ((d.get("title") or "") + " " + (d.get("text") or "")).lower()
        parents = set()
        for _e, v in parentA.iter(t): parents |= v
        for cat in parents:
            if cat not in SUBS: continue
            totals[cat] += 1
            hits = set()
            for _e, v in subA[cat].iter(t): hits |= v
            for h in hits: counts[cat][h] += 1
    for cat in SUBS:
        tot = totals[cat]
        if not tot: continue
        print(f"\n### {cat}（母类帖 {tot} 篇，每 100 篇该类帖中）")
        covered = set()
        for sname, c in counts[cat].most_common():
            print(f"  {sname}: {round(100*c/tot,1)}")
    print("\n（睡眠、产后两类细分词太少，未单列：睡眠≈失眠/噩梦/夜班，产后≈产后发病/育儿压力，母类本身占比小。）")

if __name__ == "__main__":
    main()
