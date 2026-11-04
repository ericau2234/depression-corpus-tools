#!/bin/bash
# Batch-3 L3 pool extraction driver: runs extract_fine.py 3-way parallel.
cd ~/workspace/depression-corpus || exit 1
run_one() {
  python3 extract_fine.py "$1" "$2" "fine_$3" > "fine_$3.mine" 2>&1
  echo "done $3: $(head -1 fine_$3.mine)"
}
export -f run_one
cat <<'EOF' | xargs -P 3 -L 1 bash -c 'run_one "$@"' _
家庭/父母 期望/比较压力 famexpect
家庭/父母 父母离异/缺位 famdivorce
家庭/父母 冷漠/忽视 famcold
家庭/父母 照顾患病家人 famcare
工作/学业 失业/求职失败 jobless
工作/学业 上司/同事/职场霸凌 bossbully
工作/学业 过劳/倦怠 burnout
亲密关系 异地/感情变淡 longdist
亲密关系 长期单身/求偶失败 single
孤独/孤立 自我隔离/退缩 selfiso
孤独/孤立 独居/迁居隔离 livealone
孤独/孤立 社交焦虑导致 socanx
孤独/孤立 格格不入/被排斥 misfit
疾病/疼痛 癌症 cancer
疾病/疼痛 残障/行动受限 disabled
疾病/疼痛 确诊抑郁/精神病本身 depitself
疾病/疼痛 长期慢性病 chronic
童年创伤/虐待 目睹家暴/家庭破裂 witnessdv
童年创伤/虐待 身体虐待 physabuse
童年创伤/虐待 童年忽视 childneglect
丧亲/丧失 丧偶 widow
丧亲/丧失 宠物离世 pet
丧亲/丧失 丧祖辈 grandpar
丧亲/丧失 丧兄弟姐妹 sibling
丧亲/丧失 亲友自杀身亡 suiloss
困住/逃不掉 困在身体/疾病 trapbody
困住/逃不掉 困在工作 trapwork
困住/逃不掉 困在住处/小镇 trapplace
困住/逃不掉 困在照顾责任 trapcare
困住/逃不掉 困在关系/婚姻 traprel
困住/逃不掉 经济上走不开 trapmoney
睡眠 睡眠时间不足 sleepshort
睡眠 药物助眠/药物影响 sleepmeds
睡眠 噩梦 nightmare
睡眠 作息紊乱/夜班 nightshift
产后 育儿压力/婴儿睡眠 ppstress
无缘无故 莫名发作 noreason
经济窘迫(严) 账单/生活费 bills
经济窘迫(严) 低薪贫困 lowpay
EOF
echo ALL_EXTRACTS_DONE
