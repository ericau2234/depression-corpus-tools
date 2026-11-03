# depression-corpus-tools

全网抑郁/情绪社群语料采集工具集：为「为什么人会忧郁」研究而建的 50 个专用爬虫 + 清洗管线 + 词典分类器。纯 API/公开接口路线，不用浏览器硬爬；全部脚本断点续跑。

方法、口径、各平台入口与踩坑记录见 **[docs/METHODS.md](docs/METHODS.md)**（这是本仓库的主要文档）；注册门槛审计见 `docs/REGISTRATION_FINDINGS.md`。

## 结构

- **采集层**（一平台一脚本）：`reddit_deep2.py`（十年窗口分片拖网）、`reddit_broad.py`（50 版块广度波）、`beyondblue_crawler.py`、`fivech_crawler.py`、`patient2.py`、`lj_crawler.py`、`lihkg_crawler.py`、`dcinside_crawler.py`、`mhf_crawler.py`、`bilibili_*.py`、`threads_harvest.py`、`hf_datasets.py` 等
- **清洗层**：`clean_corpus.py`（v1）、`clean_v22.py` —— 字段归一 + id/正文双重去重，按平台输出 clean jsonl 与可对账的清洗报告
- **分类层**：`classify_all.py`、`classify_v22.py` —— 多标签词典分类（13 归因类 + 5 非因桶，多语种词典，Aho-Corasick 单次扫描）；分母只计「已分类帖」；经济问题严/宽/痕迹三口径并行
- **守护**：`watchdog.sh` —— 机器重启后自动续跑未完的线（路径为本机绝对路径，迁移时需改）

## 用法（示例）

```bash
python3 reddit_deep2.py 0 10      # 深度拖网 worker 0/10，断点自动接续
python3 patient2.py 37593         # Patient.info 心理健康区全量
python3 clean_v22.py              # 全量重洗，产出 data_clean/ + 清洗报告
python3 classify_v22.py           # 按定版口径重分类
```

依赖：Python 3 + requests；分类器需 pyahocorasick；HF parquet 读取需 pyarrow。

## 不包含什么

- **不含语料数据本身**（原始/清洗后的帖子文本）：体量以 GB 计，且成批公开患者原文涉及平台条款与当事人隐私，是独立决定，不随代码发布。
- 脚本中的输出路径、版块清单、词典均为本次研究的配置，复用时按目标自行调整。

## 合规提示

各平台用户条款普遍禁止未授权的自动化抓取；本工具集在研究中的实际路线只用了游客可达的公开接口、没有注册任何小号。任何复用者须自行评估并承担其行为的合规责任。

- **网页模板**：[web-template/three-level-explorer/](web-template/three-level-explorer/) —— 议题中立嘅三层数据浏览器模板（列表／具体原因／按年份／圈图四视图，单一自包含 HTML，换数据即用）。
