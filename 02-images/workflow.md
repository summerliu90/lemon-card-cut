# 02-images｜图片设计、视频准备与素材交接

三种风格先读取[稳定系列规划与三套提示词](../01-shot-list/references/series-visual-standard.md)及[固定系列参数](../01-shot-list/references/series-profiles.json)。新任务按style_id继承同一profile/version，不再因换文案或kb seed重抽整套画风；先审静态构图、主视觉和关系层，再审样片。用户本次明确覆盖优先。


执行前读取[素材拆层、底色与画面连续性](../01-shot-list/references/asset-layer-continuity.md)：分别运动的对象优先独立素材；复用前过**语义合格**门（遮标签测试＋关系表＋实体对齐），工程合格不够；白底不自动去白，整图不按预设区域盲切；阅读期保留已组装对象，切换完整图前核对同位置同尺度。旧项目脚本需单独核对，文档更新不自动修正旧产物。


仅 `no-character` 读取[无人物动态卡片分镜规则](../01-shot-list/references/no-character-storyboard.md)，交付无角色API插图、可独立运动对象、原生准确文字及所需几何表格底板，记录来源；不以表格替代已规划的知识插图。

仅 `xiaohei` 读取并执行[小黑对象分层分镜](../01-shot-list/references/xiaohei-layered-storyboard.md)中的API出图、角色参考和独立拆层要求；该风格下这些明确要求优先于本页通用的图像工具选择。需要分别运动的知识对象必须交付可独立使用的真实素材，不用移动铅笔代替。

仅 `lemoner` 读取[小柠檬IP分镜规则](../01-shot-list/references/lemoner-storyboard.md)，落实已冻结分镜、标准角色参考、用户API插图、完整对象拆层及来源记录。该风格的明确API要求优先于本页通用工具选择；不得先出图再倒推分镜。

将01的设计任务落成真实可用的图片与视频资源。继承01的I/C/S/L/V/BG编号、图型、文案、关系和分层要求，风格只决定表现，不可擅自删节点、改流程或把结构图改成无信息的插画。

## 入口与输入

定位用户当前项目的 `01-shot-list/01-shot-list.md` 和 `01-shot-list/01-image-briefs.md`（兼容旧项目根目录同名文件），先读两份。兼容同文件内完整任务书。已有02产物时先读清单；仅复用**同时通过工程合格与语义合格**的素材，并在清单写明遮标签结论；语义不合格或关系/系列规则已升级时对新主视觉出图或换图，不得整包照搬上版图标零件。

没有01文件但当前对话有完整规划时先落盘；缺少图片内容或对应镜头时列出具体缺项，只暂停受影响图片，继续其他明确项。不要拿原文重新猜测图片任务。沿用01项目目录，不把产物写入skill目录或gzh_to_video原目录。

## 丰富信息图与互动素材

同时读取01-presentation-plan.json（旧项目缺少时根据01补齐并记录）。插画和准确信息分开制作：角色/情境/道具需要画面表现时使用生图或匹配资源，文字/箭头/节点独立排版。不要把所有图都降级为相同框线图。保存章节色、重点字样式和每张图的具体对象。SVG嵌入栅格图时标明hybrid，不声称插画可以逐笔编辑。

M表情位逐项落实：查看候选多帧，保留原动画、resource_id与本地文件映射；只有预览文件的原生ID不可伪报已验证，允许按真实可用GIF/PNG离线交付，注明local_file_with_catalog_id。导出02-presentation-assets.json，绑定I/M/E设计意图与实际资源/缺项。无素材写unresolved，不能静默删掉01已规划的必要互动项。

## 执行流程

1. 对照01建立I→C→S映射，核对独立图数、复用、动态图层和来源。每条拟复用项先做遮标签语义判断；不通过则标需新出/换图。不把卡片数量当图片数量，也不把「复用次数」或「新出图=0」当完成。
2. 读取 [风格与表情选材](references/styles-and-stickers.md) 和 [风格配置](references/style-profiles.json)。用户指定优先；其次继承01固定系列profile；缺少profile时返回01补齐，不在02临时按内容另选一套。保存 `style-lock.json`，记录具体颜色、字体、背景、图标/角色、文字路线和参考图。全片不随机混用角色或系列。
3. 按每个I任务书完善最终设计指令，保存到 `prompts/Ixx.md`；记录源任务书、静态内容、独立文字、动态图层及禁止项。准确中文和复杂流程优先SVG/HTML排版；照片、角色隐喻等可AI生图，实际生成时遵循可用图像工具及其skill规范。禁止只交提示词就称为完成图片设计。
4. 按任务书尺寸制作，保存原图、可编辑源文件和可用输出。AI生图时选定风格，用当前可用图像工具，不绑定旧脚本的模型名、私有API或账号配置。编辑参考图片前先查看；小柠檬必须使用本地标准立绘/锁定板作为参考。工具不可用时标清未完成项，不以提示词充当图片。
5. L层按01的对象策略准备，白底/透明及安全裁切条件遵守素材连续性契约，不默认从整张关系图切出所有层：原生文字/路径保存到 `layers.json`，写形状、坐标、文字、颜色和关联镜头；确需图片则透明PNG导出到 `layers/`。底图不合并需要移动、修改或单独揭示的元素。复杂文字后期排版，既保留无字底图，也保存字层位置和准确文本。
6. 根据01已有表情需求或当前明确台词中的软反应，检索本地库/原生贴纸候选，查看后决定。采用新增表情时记录对01的增补，不覆盖核心知识画面，不自行延长片长。将选定资源真实复制进项目 `stickers/`，并保存 `stickers.json`；不能只留skill库路径，避免下游移目录失效。无匹配可为空，不凑占比。
7. 查看每张最终图片及表情预览，检查字、结构、裁切和角色一致性；按视频实际显示尺寸检查可读性。透明素材检查白底/暗底效果，动图检查多个帧及持续时间，不把一张缩略图当完整动画。修正发现的问题；连续两次修正仍未解决的项标为需处理，继续其他素材。
8. 按 [交付协议](references/handoff.md) 保存manifest与报告，核验文件实际存在、I映射完整、图片尺寸真实、动态资源未丢动画。不得声称未经验证的原生resource_id可渲染。完成图片设计不代表完成配音、剪辑或发布。

## 图片多样性与视频选材

按[素材规划标准](../01-shot-list/references/material-planning-standard.md)逐组落实01分布表，继承逐素材样式及颜色；同时报告计划/实际独立图数、有效解释组和复用。authored_per_asset继承明确材质/配色/语义理由，不再随机选风格，不将原生文字框计作生成图。

先按01的image_designs与[图片选型库](../01-shot-list/references/visual-design-catalog.md)检查每张图的理解目标、图型、表现风格及实例。精确文字走排版，情境/角色/道具走适合的生图或素材路线，再分层组合；不要把丰富插画任务统一降级为框线图。仅在原语义适配的候选中选择或按保存seed变化，不能临时重抽全片风格。密集竖版参考按01重排/拆模块/局部浏览，不直接缩成不可读小卡。

若01规划V，先读01-video-briefs及[视频素材规范](../01-shot-list/references/video-asset-spec.md)，按任务选自有素材、已验证剪映本地资源或合适图库视频，保存本项目videos/与videos.json。实际probe、看多帧、校对动作/选段/裁切及人物策略；记录来源、许可和就绪状态。仅资源ID/搜索链接/封面不算ready。01只要求图片或用户限制联网时遵守范围，视频需求列缺项而不擅自采购或变更方案。

style-lock继承01的footage_policy、base背景及镜头覆盖规则。默认不采用真人/手部；用户明确开启后可加入真人视频，生成图仍沿用原风格角色规则，无人物风格仍M=0。具体例外和混合模式名称按视频规范记录；不通过默认风格名猜人物开关。片段素材时长不足时报告替代候选或需改镜头，不拉长静帧冒充视频，也不任意循环人物动作。

## 保存布局

```text
项目目录/
├── 01-shot-list/
│   ├── 01-shot-list.md
│   └── 01-image-briefs.md
├── 02-asset-manifest.md          # 指向本次版本的人读索引
└── 02-images/v1/                # 已有v1时使用新版本或明确局部更新
    ├── style-lock.json
    ├── prompts/I01.md …
    ├── sources/                # SVG/分层源图/生成原图
    ├── images/                 # I编号的剪辑用最终PNG
    ├── videos/                 # V编号本地原素材/准备选段（有规划时）
    ├── videos.json             # 源、许可、probe、选段、构图与就绪状态
    ├── layers/                 # 仅确需位图的独立动态层
    ├── layers.json
    ├── stickers/               # 选中的GIF/PNG/MOV/原生预览
    ├── stickers.json
    ├── asset-manifest.json
    └── design-report.md
```

只有阶段产物保存到项目；skill中的表情库和角色标准图是共享来源，不直接修改。

版本读取：如项目01-shot-list/current.json存在，先按其中shot_list/image_briefs/presentation_plan定位当前版本，不固定读取旧的根目录v1文件。

动态表情准备：`python3 <skill>/02-images/scripts/prepare_stickers.py --manifest <项目02版本>/stickers.json --min-duration 3`。保留原始GIF；有动画时另导出真实循环MP4供剪映和本地渲染共同使用，不以首帧预览替代。透明GIF转换到无alpha的MP4会使用实际背景；需要保留透明时应另用支持alpha的视频方案并检查，不伪称MP4有透明度。

## 三种当前风格与项目配置

新任务仅开放xiaohei、lemoner、no-character，读取00的task和02-images/style-lock.json，阶段版本内保存同一source_hash。旧风格配置只为旧项目解释，不能自动选成新任务风格。小黑用本阶段风格规范及小黑参考；小柠檬必须查看并锁定references/lemoner/ip-canonical.png；无人物动态卡片用文字/信息图/结构图/图标，不生成角色与表情。若本地文案尚无task，先明确风格并保存本地task供后续编译，勿伪造飞书record ID。

对01语义M候选逐项看图确认；目标5—10不是从目录随机抽图。保存足够不重复候选到meme-anchors.json：

```json
{"anchors":[{"id":"M-candidate-01","shot_id":"S02","file":"02-images/v1/stickers/a.gif","intent":"质疑","trigger_text":"能生成，不等于能落地","semantic_approved":true,"start_s":3.5,"end_s":4.8,"center":[0.88,0.66],"size_px":[512,512],"placement":"center_takeover","context_handling":"已读对象让位，字幕与结果保留","resource_id":"来源ID（可选）"}]}
```

这里的时间在03后由04按实测配音更新，01不得伪称词级对齐。包含666的素材标contains_666=true并核对对应台词；无人物模式anchors为空。

背景共享库位于skill/assets/backgrounds，来源与字段映射按01的[输入接入规范](../01-shot-list/references/source-intake.md)记录在项目task中；以实际素材库存核对，不依赖缺失的背景目录映射。选中背景后保存项目本地副本，图片按01卡片区域设计；不要把动态背景烘焙进每张图。

## 学习配方的素材承接

01引用motion_ref时，读取其固定版本的asset_requirements、layout和layers，按要求交付独立图层及锚点/裁切/可见区，不将需要分别运动的对象烘焙在一张图里。某配方需要的素材不能提供时，回报具体缺项及可行替代，让01更新方案，不让04静默凑效果。

## 动态分镜执行契约 v2

执行本阶段前读取[动效、视觉节拍与字幕交接契约](../01-shot-list/references/motion-contract.md)，继承01固定的动效版本与素材要求；不能在后续阶段重新猜测构图或替换未验证效果。

## 画风继承和图片完成门禁

必读[图片画风执行契约](../01-shot-list/references/visual-style-contract.md)，以01的visual_design为准，读取所选原模板，保存实际series_parameters，禁止重新抽画风。按逐图比例和双图独立任务制作；用户所谓“03图片设计”对应本阶段。执行validate_visual_design.py --stage 02，确认真实文件、实际比例、生成路线和逐图QA。设计或工具缺口写partial，不以overlay/贴纸取代生成图后标完成。

## 跨阶段质量交接（必读）

遵守[执行质量契约](../01-shot-list/references/execution-quality-contract.md)。asset-manifest.json增加execution_assets，保持01的design_id/type；角色保存实际参考文件hash和审看记录。执行validate_execution.py --stage 02，不允许将插画交成文字框。

## 表情主次与最终尺寸

交接同一M编号、最终size_px及可见主体检查；读取[表情编排契约](../01-shot-list/references/meme-staging-contract.md)。

## 已确认制作规则入口

每次执行先读取[制作规则总表](../01-shot-list/references/production-rules.md)。字幕固定为剪映原生可编辑字幕、新青年体、字号7、#FFDE00；以production-profile.json及实际草稿检查为准，不以本地预览像素代替剪映字号。
