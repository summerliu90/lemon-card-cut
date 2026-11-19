# 04-video-cut｜分镜、图片与配音合成

三种风格先读取[稳定系列规划与三套提示词](../01-shot-list/references/series-visual-standard.md)及[固定系列参数](../01-shot-list/references/series-profiles.json)。新任务按style_id继承同一profile/version，不再因换文案或kb seed重抽整套画风；先审静态构图、主视觉和关系层，再审样片。用户本次明确覆盖优先。


执行前读取[素材拆层、底色与画面连续性](../01-shot-list/references/asset-layer-continuity.md)：分别运动的对象优先独立素材；样片须做语义抽帧（遮标签仍能懂），图标墙或与上版同 sha 的伪返工不得进全片；白底不自动去白，整图不按预设区域盲切；阅读期保留已组装对象，切换完整图前核对同位置同尺度。旧项目脚本需单独核对，文档更新不自动修正旧产物。


仅 `no-character` 额外执行[无人物动态卡片分镜规则](../01-shot-list/references/no-character-storyboard.md)，落实逐行比较、字段传递及目标值更新；检查完整阅读窗、文字与背板对比、脚注边界和字幕避让。没有语义需要时不强加表格。

仅 `xiaohei` 额外执行[小黑对象分层分镜](../01-shot-list/references/xiaohei-layered-storyboard.md)的动作编译、拆层边界、字幕安全区及实际画面验收。知识对象本身必须按01发生变化；不能用整图微缩放或统一铅笔横移交付该风格的动态分镜。其他风格继续使用各自设计。

仅 `lemoner` 额外执行[小柠檬IP分镜规则](../01-shot-list/references/lemoner-storyboard.md)，编译01已定义的对象、关系、状态动作，核对标签与对象逐项对应、进入过程避让字幕、完整结果停稳。沿用同一计划构建草稿与MP4；不能把只换标签的三列图或角色贴角当成内容动作。

只读取03已有配音，不调用剪映内置TTS重做。继承01的信息关系与动效、02实际素材/风格/图层，再以03真实镜头时间编排。默认输出可编辑剪映草稿；用户要求成片时另输出MP4，不能把草稿叫成已渲染视频。

## 迁移的能力

从gzh_to_video/05-edit复制JyProject运行时、vendor、资源检索、草稿检查、动画/贴纸/滤镜/转场索引及语义动画池，保留原LICENSE。代码在本目录独立运行；不要调用原gzh总控，也不依赖飞书领用人字段。主入口仍只有上层SKILL.md，当前文件是阶段说明。

## 导演编排（先于合成）

先读01-presentation-plan和02-presentation-assets，再写 `direction-plan.json`：逐镜绑定I/C/L、M实际文件/原生ID、E实际音效文件，落实字体颜色、准确强调词、入出时点和语音触发精度。direction-plan是01设计的执行适配，不能自立第二套内容分镜。保存每个计划意图到最终clip/segment的映射。

表情GIF/本地视频须真实播放多帧，不能只取首帧。不能渲染原生ID时可采用已确认本地动画并保留ID来源，明示provider。旁白与E音效必须多轨混音，原生草稿保留各轨；音效较旁白低，避免密集或遮盖。统计实际M数、E数、文件及最终存在的segment，不凭manifest自报数量验收。

## 编排步骤

1. 读取01两份任务书、02顶层索引和所指版本中的style-lock/asset-manifest/layers/stickers，再读03 segments_audio/subtitles。核对所有I/C/S/L/M引用和真实文件；不把PNG总览当素材，不跳过必要L层。
2. 校准：S镜边界使用03实测值。01镜内时间按真实时长与估算时长比例重排；有真实触发词时间时优先使用。镜内动作必须落在镜长内，先缩短无信息停留，不压缩必要阅读时间；无法容纳时写明需改分镜，不拉伸旁白凑76秒。未有词级对齐时保留估算标记。
3. 形成项目脚本 `scripts/compile_edit_plan.py`，输出本阶段 `edit-plan.json`，而非每次重新硬编码素材路径。用户项目专属脚本放项目目录，skill scripts只存可复用运行时。计划写真实素材路径、全局秒、轨道、透明度、位置、尺寸、动画、关键帧、图层ID及来源镜头。schema与坐标见 [技术协议](references/edit-contract.md)。
4. 构建顺序：风格背景→卡片/图片→必要动态图层→原生标题/正文→底部原文字幕→旁白→可选低音量音效。保留S03/S07等多卡并排；不要机械一图一镜。字幕、章节、判断字、领取口令必须独立可编辑。流程复杂的形状可保存透明叠层，但字仍单独排版。
5. 使用 `scripts/build_video.py --plan ... --out ...` 调用本地复制的JyProject写新草稿，草稿及材料先保存到项目内。保存前不覆盖同名已有草稿。要导入系统剪映目录时检查实际路径并复制新草稿，不自动删除/修复已有项目。真实素材复制到草稿materials使之自包含。
6. 动效优先01指定语义和关键帧：进入/淡出、卡片重排、参数沿线、错误高亮、长图窗口滚动、标题归位。库资源可用时检索实际ID；无可用动画时用自定义关键帧实现相同语义并记录，不能悄悄忽略。长图滚动应在固定窗口裁切，禁止整页滑过字幕。
7. 贴纸读取02已选M项；需要补充时可从02库按台词语义选并保存本项目副本与记录。未验证原生ID不直接当可渲染；本地GIF保留动画，参数与台词一一关联。不凑固定占比，不强制所有镜3–5秒；同一语义不叠多种花哨动画。
8. 音效按复制的global_sfx_policy做密度参考，同一位置仅一个主音效，旁白优先；未选BGM时不自动加云端音乐。资源不可用时记录未完成项；只有用户明确同意的替代方案才能变更冻结计划，不得静默降级或随机加声。
9. 保存后检查真实draft_info/draft_content：1920×1080、旁白长度、全片覆盖、轨道重叠、I映射、L完成数量、贴纸验证状态、关键词出现时间。每个计划必需层应对应实际segment；缺层要写partial，不能只生成图片轮播后标完成。查看关键帧/章节/结尾，记录已检查与未检查项。

## 图片与视频素材混合编排

先读[视频素材交接](../01-shot-list/references/video-asset-spec.md)及02的videos.json，只消费ready的V资源。direction-plan绑定V/BG编号、media_role、源入点、使用时长、fit与裁切、静音、footage_policy和base背景恢复状态；不按文件夹顺序或关键词随机找视频。情境镜头表达情境，操作演示必须匹配操作与结果，知识点的图型/实例不能被无关实拍替换。

底层连续背景保持track=background。局部情境/屏录视频放独立轨（例如SceneVideo/DemoVideo），按01置于底板之上、标题字幕之下；窗口视频还需保留卡片边框/裁切关系。apply_presentation会重建background轨，不能把局部V误放该轨再被全片背景覆盖。显式全程背景要求下，V采用窗口而不是全屏遮盖。

裁切/压暗/虚化/循环先确认运行时实际支持；需要时准备本地视频选段再供草稿与MP4共用。现有kind=video支持file/source_start_s及静音，但规划中的处理字段不是自动生效的滤镜参数。保留原源和处理记录，不能让原生草稿和MP4使用两套不同选段。默认静音，需环境声时另作明确音轨设计并避开旁白。

交付回读实际视频segment与选段，抽帧检查动作连续、画幅裁切、知识可读区、字幕遮挡、人物开关和镜后背景恢复。显式开启真人实拍而style_id=no-character时，注明“无人物图文＋真人实拍混合”，M仍为0；不开启时包括手部都不能加入。新增规划字段不会被现有audit自动验证，不把机器检查通过当成人物/语义/许可检查通过。

## 成片与导出

macOS运行时的auto_exporter可能不支持无人值守MP4导出：实际检测能力，不能仅凭脚本存在承诺成功。用户要求MP4可用项目渲染器按同一edit-plan合成并使用03 narration.wav；须包含计划内动态层与字幕，不能用静态轮播冒充。可用本地渲染器命令：`python3 <skill>/04-video-cut/scripts/render_preview.py --plan <edit-plan.json> --output <final.mp4>`。当前渲染器支持静态/裁切帧图片、可变帧时长GIF、本地视频叠层、文字及关键帧，并按edit-plan混合旁白和多条音效。原生贴纸ID必须验证或提供真实本地动画，不支持的ID会显式报错，不静默丢弃。字体可用`--font`指定，非macOS必须提供实际可用中文字体。云渲染/上传另需用户提出，不自动发布。

## 输出

项目 `04-video-cut/vN/`：edit-plan.json、drafts/<新草稿名>/、build-summary.json、timeline-check.json、preview/，可选final.mp4。项目根 `04-video-manifest.md`链接草稿/预览/成片与限制，区分draft_ready、rendered、partial，说明语义动画实际使用数和保留的估算时间。

音效来源：先查已有音效索引与实际可解码缓存。没有合适文件时，可按E意图制作原创短提示音并保存波形/频率/包络配方，不把一个目录ID当成本地已有音频。所有声音实际解码后才能入轨；保留音效文件与各轨音量，方便后续替换。

## 背景与5—10处动态表情编译

先按01/02和实测音频完成基础edit-plan及meme-anchors.json；有task.json时必须运行以下编译，之后build和render都使用同一个新plan：

```sh
python3 <skill>/04-video-cut/scripts/apply_presentation.py --project <项目> --plan <基础edit-plan.json> --anchors <meme-anchors.json> --output <新版本>/edit-plan.json
python3 <skill>/04-video-cut/scripts/build_video.py --plan <新版本>/edit-plan.json --out <新版本>
python3 <skill>/04-video-cut/scripts/render_preview.py --plan <新版本>/edit-plan.json --output <新版本>/final.mp4
python3 <skill>/04-video-cut/scripts/audit_delivery.py --project <项目> --plan <新版本>/edit-plan.json --mp4 <新版本>/final.mp4 --draft <新版本>/drafts/<草稿名> --build-summary <新版本>/build-summary.json
```

编译器采用保存的seed从已审核语义候选选择目标数量，默认最多一个表情同时出现、间隔至少0.35秒，选择真实入场/停留/退出关键帧。静态表情也有进出动效；GIF自身逐帧播放，两种动态分别核验。presentation-report保存目标/实际数量、动效映射、缺口原因与背景来源。不得写semantic_approved=true来绕过实际看图和语义判断。

显式背景对三种风格均生效：ffmpeg连续循环cover到画布并静音，生成项目内background-loop.mp4，剪映和渲染共用；背景在最底层，卡片/图文上叠。渲染连续读取背景帧，不将全长高清背景展开成海量PNG。原生草稿将背景音量置0。无人物模式表情数量0，保留独立信息动效。

交付audit读取真实草稿/MP4/文件及M关键帧，仍需查看关键画面、字幕安全区、循环接缝和动态多帧并听配音；机器检查不能等同人工验收。未听音或未在剪映打开须如实标明。finish前重新运行audit，产物通过后才能将飞书写为待审核。

## 本机剪映同步与可见性

项目内draft_ready不代表剪映首页可见。用户要求同步或在剪映中查看时，发现实际本机草稿库（容器路径可能与Movies路径是同一个目录），复制新草稿、重定位素材路径、补齐草稿名称/时长/封面，并备份后登记root_meta_info.json。只复制文件夹或只发项目路径不能称为已同步。

```sh
python3 <skill>/04-video-cut/scripts/install_draft.py --source <项目内草稿文件夹> --root <实际剪映草稿库> --cover <封面.jpg> --report <项目04>/jianying-install.json
```

不覆盖同名草稿，不改用户其它草稿；索引并发变化时停止，重新读取后处理。登记后检查索引条目、1920×1080画布、真实时长和全部素材路径。报告区分project_draft_ready、registered_in_local_jianying_library、ui_verified；不能把磁盘登记检查说成已在剪映界面打开。界面权限不可用时明确说明；用户可返回首页刷新，仍未出现时先保存当前编辑再重启，不擅自退出正在编辑的剪映。

## 原生草稿的动效稳定性

原生关键帧使用已实现的Line曲线，不把CSS cubic-bezier的0—1控制点直接写成剪映Bezier控制柄。入场结束后显式写保持关键帧，关键帧偏移为片段内微秒。文字以固定坐标显示；位移/缩放必须有清楚语义，不给每句标题自动弹跳。连续镜头复用同一插画时合并为持续片段，在内容切换时入场，避免一句话重新触发一次。

复杂草稿可在edit-plan指定`pack_tracks:true`，构建器按kind/z合并不重叠片段，保留重叠层及所有独立可编辑片段。段落边界按round(end)-round(start)计算微秒时长，防止分轨后出现1微秒重叠。`keyframe_interpolation:linear`让MP4与原生草稿使用同一稳定插值。交付检查原生文字关键帧数量、曲线类型、同轨重叠和保持区间；机器检查不等同实际剪映播放。

## 学习配方的执行回传

01的motion_ref与motion_events是执行依据；将引用版本、实际provider/resource_id或关键帧参数、时间适配、segment映射、验证证据回写direction-plan/交付报告。不能因为共享库有同名动效就临时替换01指定版本。原生未验证效果仍为待验证，不以候选状态计为完成；本地MP4不支持的原生效果必须列出差异。完成本机/渲染验证后可在00学习库发布新版本的验证结果，不回改旧版本记录。

## 动态分镜执行契约 v2

执行本阶段前读取[动效、视觉节拍与字幕交接契约](../01-shot-list/references/motion-contract.md)，继承01固定的动效版本与素材要求；不能在后续阶段重新猜测构图或替换未验证效果。

## 主知识图片执行门禁

先按[素材规划标准](../01-shot-list/references/material-planning-standard.md)核对全片分布，不能只看总图数。visual_gate共用validate_action_execution检查分镜action_specs与clip关键帧属性/起止数值；最终audit_evidence调用audit_text_motion回读原生文字关键帧并检查实际字体缺字。缺动作不可只补ID或修改报告放行；这些检查不代替实际审看。

必读[图片画风执行契约](../01-shot-list/references/visual-style-contract.md)。编译clip携带image_design_id，运行validate_visual_design.py --stage 04；再回读真实草稿segment并抽取实际视频各I稳定帧及运动多帧，保存visual-execution-report.json。核对required图是否真实出现、显示大小/字幕遮挡/可读性及重复构图。脚本只查计划，不代替真实草稿与成片审查；缺图/不可读时保持partial，不能用表情或通用矩形卡代替主图片。

输入来源和冻结规则见01的[飞书与本地输入接入](../01-shot-list/references/source-intake.md)。项目00-feishu-source/task.json由01生成，现有消费路径保持不变；它不是另一个必需的skill阶段。

当前build/render已自动执行visual_gate，输入缺visual_inputs或不符会停止；按画风契约补齐冻结路径及摘要。背景统一使用edit-plan.fps；改变帧率必须重新编译背景。最终audit必须有与当前计划和MP4摘要匹配的visual-execution-report.json，不能把字段自报当实际审图。

## 跨阶段质量交接（必读）

遵守[执行质量契约](../01-shot-list/references/execution-quality-contract.md)。edit-plan逐素材保存design_asset_id、scene_id，执行阶段为pilot或final。先制作契约指定样片并审看，再提交final；build/render共用门禁，audit检查逐场景审看证据。缺素材、动作或角色一致性时保持未完成，不能靠改审核记录放行。

## 表情主次与最终尺寸

按最终尺寸编译并审看大表情与图文主次切换，不擅自缩回右侧；读取[表情编排契约](../01-shot-list/references/meme-staging-contract.md)。

## 已确认制作规则入口

每次执行先读取[制作规则总表](../01-shot-list/references/production-rules.md)。字幕固定为剪映原生可编辑字幕、新青年体、字号7、#FFDE00；以production-profile.json及实际草稿检查为准，不以本地预览像素代替剪映字号。

## 字幕实际执行与验收

普通口播字幕不能由花字模板或镜内标题配置覆盖。先用subtitle_contract.apply_subtitles冻结真实字体及hash，明确native字号7、预览56px/1080p和#FFDE00。build_video生成type=subtitle的独立文字素材；render_preview按同一真实字体渲染。visual_gate对字体家族/文件摘要、字号/色值进行前检，audit对真实materials.texts的类型、文字、字体ID/路径、字号和RGB进行回读；未通过不得交付。

生产构建只走本workflow的apply_presentation→build_video/render_preview→audit_delivery。scripts中的旧smart_rough_cut、movie_commentary等移植工具不是本流程生产入口，不得用其绕过分镜、素材、样片与字幕门禁。

### 普通字幕默认预设：黄字黑描边

依据用户提供的黄色 T 图标，锁定普通口播字幕为原生可编辑字幕：新青年体（6740435892441190919）、剪映字号7、填充#FFDE00、描边#000000，无背景底板。原生 TextBorder.width 初始值40（SDK单位，不是40像素），视觉粗细需以剪映预览为准；动态路线预览可继续用约2px黑边。居中放在底部字幕安全区，沿用已有断句规则。图片风格配置不得覆盖普通字幕的字体、字号、填充或描边；知识卡片标题和花字保留独立设计。截图青色框是UI选中态，灰底是预设面板背景，均不进入成片。

此项是可复现的视觉样式预设，不冒认截图对应的官方预设名称或资源ID。若后续明确指定剪映原生预设，需从实际草稿提取真实ID及参数后再替换。验收需检查最终 Subtitles 轨的字体、字号、黄色填充及非零黑色描边；不能只检查配置。
