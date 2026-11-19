# 共享动效资产库

2026-10-23：已从两条实际参考视频学习32条配方；索引修订r2，各配方v001。来源hash、时间码及连续帧在references；motions存不可变版本。

## 使用状态

- `learned_recipe_not_necessarily_renderable`：分析与入库完成；全部具体实现仍为`unverified`。
- 01可选择并规划；04需验证关键帧、遮罩、形变与MP4/草稿支持后才能认定可交付。
- 两个参考文件都没有音轨；`sound-design-suggestions.json`的8类声音仅为设计建议，未创建音频资产。
- 不把参考截图、人物、日期、结果数字或口令直接当成新素材/新事实。

## 01检索

先看全片结构与语义关系，再读所选配方，最后写镜头事件。不要把全部动效都套进每条视频。

```sh
python3 .cursor/skills/lemon-card-cut/00-motion-study/scripts/motion_library.py select --project <项目目录> --style <xiaohei|lemoner|no-character> --intent enumeration --intent card-reflow --target draft
```

首次通览所有适配候选时显式传`--limit 64`，以免默认12条截断候选；之后按语义筛选。候选快照不等于分镜。无人物风格同时更换所有有人实拍/截图为不含人的图示或界面，若核心关系依赖角色则不选该配方。

检索词：narrative-arc、roadmap、steps、chapter、navigation、enumeration、card-reflow、progression、layering、focus-transfer、detail-to-whole、diagram、proof、takeaway、practice、document-pan、document-scroll、collection、closing。

## 八类主目录

| 类别 | 配方数 |
|---|---|
| 全片构造与节奏 | 4 |
| 章节导航与切换 | 3 |
| 卡片入场、重排与递进 | 6 |
| 文字、图标与重点强调 | 7 |
| 图示聚焦与语义标注 | 3 |
| 人物、隐喻与反应 | 4 |
| 证据与作品呈现 | 2 |
| 资料窗口、浏览与合集 | 3 |

按语义和图层关系复用；下面的细分类用于进一步定位。

## 分类目录

### 全片构造

- [全片结构：代入→路线→分阶段→项目→合集](motions/roadmap-narrative-arc/v001.json) — `roadmap-narrative-arc`；narrative-arc, roadmap, steps
- [全片结构：证据钩子→认知转折→三步→实战→合集](motions/proof-knowledge-practice-collection-arc/v001.json) — `proof-knowledge-practice-collection-arc`；narrative-arc, proof, steps, practice

### 文字入场

- [实拍底上的分层标题与关键词落版](motions/hook-text-progressive-hierarchy/v001.json) — `hook-text-progressive-hierarchy`；hook, text-hierarchy, keyword-emphasis

### 文字与图标

- [左右条件与正反图标逐项出现](motions/qualification-two-column-verdict/v001.json) — `qualification-two-column-verdict`；contrast, qualification, verdict

### 卡片构图

- [双资料封面建立路线总览](motions/dual-document-preview/v001.json) — `dual-document-preview`；overview, pair, proof

### 表情与素材关系

- [资料不动，时钟与人物隐喻接力](motions/metaphor-overlay-swap/v001.json) — `metaphor-overlay-swap`；metaphor, reaction, outcome

### 章节转场

- [章节清场→大标题→小标题归位](motions/chapter-reset-and-dock/v001.json) — `chapter-reset-and-dock`；chapter, navigation, attention-reset
- [提问短句→步骤胶囊标题](motions/question-to-chapter-pill/v001.json) — `question-to-chapter-pill`；chapter, question, steps

### 卡片递进

- [旧卡压暗留后，新卡从下方前置](motions/dim-old-cards-promote-new/v001.json) — `dim-old-cards-promote-new`；progression, layering, focus-transfer

### 卡片入场

- [关联概念双卡先后展开](motions/pair-reveal-for-related-concepts/v001.json) — `pair-reveal-for-related-concepts`；pair, related-concepts, enumeration
- [卡片逐张加入，旧卡横移重排成一行](motions/card-add-and-reflow-row/v001.json) — `card-add-and-reflow-row`；enumeration, card-reflow, comparison

### 文字动态

- [流程词纵向逐个累积](motions/process-words-vertical-build/v001.json) — `process-words-vertical-build`；process, sequence, text-build

### 文字强调

- [资料前的单句大字强调](motions/central-keyword-over-document/v001.json) — `central-keyword-over-document`；keyword-emphasis, takeaway, focus-transfer

### 遮罩与聚焦

- [圆形局部聚焦→完整结构图](motions/circle-focus-to-full-diagram/v001.json) — `circle-focus-to-full-diagram`；focus, detail-to-whole, diagram

### 图示标注

- [结构图上多列竖标签逐条生长](motions/diagram-vertical-label-stagger/v001.json) — `diagram-vertical-label-stagger`；annotation, components, diagram

### 概念到应用

- [结构图换案例，人物提示用途](motions/concept-to-application-character/v001.json) — `concept-to-application-character`；application, example, metaphor

### 图文关系

- [框架资料双卡＋角色标签逐级加入](motions/framework-and-role-badges/v001.json) — `framework-and-role-badges`；roles, framework, enumeration

### 成果展示

- [项目图标→具体项目资料→结果强调](motions/project-icon-to-proof-card/v001.json) — `project-icon-to-proof-card`；project, proof, takeaway

### 资料浏览

- [一主两辅窗口：大图内部平移浏览](motions/collection-main-two-support-pan/v001.json) — `collection-main-two-support-pan`；collection, document-pan, closing
- [版式不动，主文档在裁切窗内向上滚](motions/fixed-window-document-scroll/v001.json) — `fixed-window-document-scroll`；document-scroll, collection, long-content

### 证据构图

- [多张证据截图错位叠放，结论字保持前景](motions/proof-stack-with-anchor-headline/v001.json) — `proof-stack-with-anchor-headline`；proof, hook, layering

### 判断转折

- [误区大字＋否定叉号覆盖](motions/verdict-cross-overlay/v001.json) — `verdict-cross-overlay`；misconception, verdict, contrast

### 焦点转移

- [证据墙退淡，结论文字前置](motions/evidence-wall-to-takeaway/v001.json) — `evidence-wall-to-takeaway`；proof, takeaway, focus-transfer

### 场景与人物

- [情境实拍模糊后叠讲解人物与问号](motions/blurred-scenario-with-explainer/v001.json) — `blurred-scenario-with-explainer`；scenario, question, metaphor

### 素材切换

- [工具屏录作能力与实践之间的桥段](motions/interface-demo-bridge/v001.json) — `interface-demo-bridge`；demo, practice, breathing-space

### 章节导航

- [步骤标题切为顶部常驻主题](motions/pill-to-pinned-topic/v001.json) — `pill-to-pinned-topic`；navigation, topic, enumeration

### 卡片转入

- [新卡以模糊形变进入，随后展开落稳](motions/blurred-card-unfold-settle/v001.json) — `blurred-card-unfold-settle`；card-entry, focus-transfer, unfold

### 表情与节奏

- [知识卡组稳定后插一次反应贴纸](motions/reaction-on-stable-knowledge-group/v001.json) — `reaction-on-stable-knowledge-group`；reaction, warning, misconception

### 总览到细分

- [工具分类总览→分专题多卡集合](motions/tool-overview-to-card-cluster/v001.json) — `tool-overview-to-card-cluster`；overview, taxonomy, layering, card-cluster

### 实拍节奏

- [知识卡→操作实拍→项目卡→工作情境](motions/live-practice-breathing-cut/v001.json) — `live-practice-breathing-cut`；practice, breathing-space, project, cutaway

### 资料转场

- [卷页状形变展开成一主两辅资料窗](motions/page-curl-to-three-window-collection/v001.json) — `page-curl-to-three-window-collection`；collection, page-curl, transition

### 结尾强调

- [稳定合集前，单个短词收尾](motions/closing-sticker-single-punch/v001.json) — `closing-sticker-single-punch`；closing, callout, keyword-emphasis

## 可追溯分析

完整学习报告位于工作区`outputs/motion-study-20261023/学习报告.md`。两条源参考的结构时间轴和逐项分析也在各references目录的structure.json与ANALYSIS.md。
