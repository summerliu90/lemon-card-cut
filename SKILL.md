---
name: lemon-card-cut
description: 将中文口播制作成动态知识卡片视频素材，支持参考视频动效学习入库并衔接分镜：00-motion-study提炼动效配方，01-shot-list规划知识图片设计、图文视频搭配和动态分镜，02-images制作图片并准备视频和表情素材，03-voice-clone复用或克隆音色并配音，04-video-cut按真实音频合成可编辑视频草稿。适用于知识讲解、学习路线、面试复盘、方法步骤与资料展示。
---

分镜先执行[关系驱动的剪辑规划](01-shot-list/references/relation-first-storyboarding.md)：通读全文，分析段落与子关系，再决定画面单元、重点文字、图片及关系动效；不可先套情境或固定镜头数。



# Lemon Card Cut

按阶段承接口播、分镜与素材，保留I/C/S/L/M/E及V/BG编号与数据关系。01设计图型、局部表现风格、全片图片/视频搭配及互动意图，02制作图片并准备真实视频素材，03测配音时长，04先导演编排再合成。

## 阶段路由

从飞书生产表选择制作流程时先按[统一执行入口](../视频制作统一执行.md)读取「视频制作模型选择」；「2 动态分镜规划」进入本skill，「1 ppt样式」交给gzh_to_video，空值/未知值不回退。该入口只决定路径，不替代本skill的输入与审核门禁。

- 学习参考视频中的构图、换镜、文字/卡片/表情动效：读取 [00-motion-study](00-motion-study/workflow.md)。学习结果入共享库；有目标文案时衔接01，无文案时只入库。01的输入接入负责内容参数，00-motion-study负责表现方法，二者在01汇合。
- 每次01规划都读取最新共享动效库，保存带版本/hash的候选快照；不要求每个视频重新学习。

- 飞书文案、审核门禁、制作模型选择、背景/风格/音色参数：在01开始时先读[飞书与本地输入接入](01-shot-list/references/source-intake.md)。当前新任务仅支持小黑、小柠檬、无人物动态卡片；制作模型为ppt样式时交给gzh_to_video。
- 本地文案同样先明确三种风格之一并锁定配置；无人物模式关闭角色和表情包，小黑/小柠檬的语义表情目标随机5—10处，固定seed，重试不重抽。

- 分镜、卡片数量、动态、知识图片设计及情境/背景/屏录视频规划：读取 [01-shot-list](01-shot-list/workflow.md)。按信息关系选择图型，再做整片素材搭配，不默认同一矩形卡片模板。
- 选择画风、设计/生成图片、准备视频及表情、承接01：读取 [02-images](02-images/workflow.md)。真人实拍按01独立footage_policy决定，默认关闭；显式开启不改变生成图的角色规则。
- 音色、声音克隆、配音、TTS：读取 [03-voice-clone](03-voice-clone/workflow.md)。
- 视频音频合成、剪映草稿、动效与贴纸：读取 [04-video-cut](04-video-cut/workflow.md)。
- 用户仅要求01时不自动进入后续；明确要求完整视频合成时检查并完成01→02→03→04，复用已有且合格的阶段产物。修改skill本身不自动触发付费合成。
- 用户明确指定阶段或只修改某项时保持范围，不重新生成其他已合格内容。

## 固定项目结构

```text
项目目录/
├── 00-feishu-source/         # 01写入的兼容输入目录：task/narration/state（本地或飞书）
├── 00-motion-study/          # 学习证据、配方、交接（有参考时）
├── 01-shot-list/
│   ├── 01-shot-list.md
│   ├── 01-image-briefs.md
│   ├── 01-video-briefs.md        # V/BG任务书；未采用视频时注明原因
│   ├── 01-presentation-plan.json # 逐镜字体/颜色/图文/M/E意图
│   └── current.json             # 有版本时指向当前01
├── 02-asset-manifest.md
├── 02-images/v1/
│   ├── style-lock.json
│   ├── prompts/
│   ├── sources/
│   ├── images/
│   ├── videos/                 # 已取得并验证的视频素材
│   ├── videos.json
│   ├── layers.json
│   ├── stickers.json
│   ├── asset-manifest.json
│   └── design-report.md
├── 03-voice-clone/v1/          # 音色设置、真实配音、字幕、实测镜头时长
├── 03-voice-manifest.md
├── 04-video-cut/v1/            # direction-plan、执行计划、混音、草稿和成片
└── 04-video-manifest.md
```

skill目录存阶段规范与共享素材，outputs项目目录存执行产物，二者不混放。01完成后同时保存两份文件；02按路径读取，不凭聊天记忆重猜。兼容历史项目根目录的同名01文件；新任务统一按上述结构保存。风格依用户要求覆盖表现，图片内容、关系与分层继承01；变更写报告。用户要求配音/视频合成时继续03/04；新克隆使用用户指定样本与音色，已有voice_id优先复用。云上传和发布不随本地合成自动进行。

当前制作配置及跨阶段验收以[动态分镜执行契约](01-shot-list/references/motion-contract.md)和[生产配置](01-shot-list/references/production-profile.json)为准。01必须保存语义场景、局部动作及可追溯动效引用；3—5秒是局部事件建议间隔；是否真的换镜由实际画面验收。

## 图片画风与执行门禁

三种风格先读取[稳定系列规划与三套提示词](01-shot-list/references/series-visual-standard.md)及[固定系列参数](01-shot-list/references/series-profiles.json)。新任务按style_id继承同一profile/version，不再因换文案或kb seed重抽整套画风；先审静态构图、主视觉和关系层，再审样片。用户本次明确覆盖优先。

执行前读取[素材拆层、底色与画面连续性](01-shot-list/references/asset-layer-continuity.md)：分别运动的对象优先独立素材；**复用须工程合格且语义合格**（遮标签仍能懂、对得上关系表），禁止无关图标拼盘冒充解释；白底不自动去白，整图不按预设区域盲切；阅读期保留已组装对象，切换完整图前核对同位置同尺度。旧项目脚本需单独核对，文档更新不自动修正旧产物。视觉返工不以「新出图=0」或与上版同 sha 为成功。

当冻结的 `task.style` / 计划 `style_id` 为 `xiaohei`（飞书「7 小黑手绘」）时，01、02、04必须读取[小黑对象分层分镜](01-shot-list/references/xiaohei-layered-storyboard.md)，按其中九类语义设计选择对象动作并交接独立素材。该补充只作用于小黑，不给小柠檬、无人物或PPT路线套用这些设计；未知风格先解析，不猜选小黑。

当冻结风格为 `lemoner`（飞书「8 小柠檬IP」）时，01、02、04必须读取[小柠檬IP分镜规则](01-shot-list/references/lemoner-storyboard.md)，先完成分镜与对象动作交接，再制作图片和合成视频。该规则是小柠檬的默认规划方法；不套用小黑角色与专用分镜，也不固定照搬kb-049的场景数、图数或三列布局。

当冻结风格为 `no-character`（飞书「10 无人物动态卡片」）时，01、02、04必须读取[无人物动态卡片分镜规则](01-shot-list/references/no-character-storyboard.md)，先按知识关系规划对象、表格或表单，再准备素材与合成。该规则固定无人物叙事、同维度对照、字段传递、原生文字与实际画面验收；按文案选用，不固定kb-050的镜头数、表数或背景。

01和图片制作阶段必须读取[图片画风选择与跨阶段执行契约](01-shot-list/references/visual-style-contract.md)：操作者指定优先；当前三种风格以稳定系列profile作为明确设计方向，使用authored_per_asset记录固定材质/配色/参考与本稿语义理由，不按kb seed重抽整套画风；历史随机路线仅在用户明确重选或兼容旧项目时使用。角色style_id、图片visual_style_id和图型分别保存。图片制作编号保持02；用户称“03图片设计”时接入02能力，03仍配音。01明确独立图片内容/比例/上屏布局，02落实真实图片，04核验实际入轨与成片可读性。修改skill不会自动重做现有视频。

## 防止制作降级的强制交接

各阶段先读[执行质量契约](01-shot-list/references/execution-quality-contract.md)。主视频语言与局部插图画风分别锁定；素材ID、角色参考和内容动作必须从01贯穿02、04。构建及预览共用 visual_gate，缺执行契约的历史计划必须迁移。完成代表样片实际审看后再制作全片；成片审核还需逐场景连续观看证据。字段通过不等于审美通过。

## 表情主次与最终尺寸

分镜与视频执行都先读[表情编排契约](01-shot-list/references/meme-staging-contract.md)。

## 已确认制作规则入口

每次执行先读取[制作规则总表](01-shot-list/references/production-rules.md)。字幕固定为剪映原生可编辑字幕、新青年体、字号7、#FFDE00；以production-profile.json及实际草稿检查为准，不以本地预览像素代替剪映字号。

素材数量、分布及局部多样性按[素材规划标准](01-shot-list/references/material-planning-standard.md)执行：以解释任务规划素材组，继承“素材增强_v3”的方法，不固定复制其图片数量或物件。

普通字幕采用用户黄字黑描边预设；具体参数及截图识别边界见 [04合成规则](04-video-cut/workflow.md#普通字幕默认预设黄字黑描边)，机器配置见 production-profile.json。
