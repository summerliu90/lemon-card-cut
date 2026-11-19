# 图片画风选择与跨阶段执行契约

01规划、02图片制作和04剪辑验收共同读取。原始风格来源为[风格.md](../风格.md)，索引为[画风目录](image-style-catalog.json)。索引用于筛选，采用后读取原文件对应标题和相关变体，提炼实际参数，不照搬示例文案、参数占位符、强制提问或不存在的外部模板路径。目录包含11类去重画风；“对比信息图”独立作为图型模板。后续原文件新增内容应同步索引。

## 当前三风格的优先覆盖（2026-11-18）

新任务先执行[稳定系列规划](series-visual-standard.md)和[固定profile](series-profiles.json)。xiaohei、lemoner、no-character默认是已有明确设计方向，采用authored_per_asset保存固定材质/配色/参考与本稿理由；不进入无方向的semantic_random分支。逐素材可改变图型和知识内容，不能借authored_per_asset每镜另造画风。以下随机规则/JSON示例保留给历史项目及用户明确要求重新选择画风的情况，不是当前三风格的新任务默认。

## 三个独立维度

- `style_id`保留现有xiaohei/lemoner/no-character角色模式，不把新画风ID写进生产配置的角色字段。
- `visual_style_id`决定纸张、笔触、色彩、材质与排版气质；`diagram_type`决定概念、流程、组成、对比或实例等信息关系。
- 人物政策优先于模板：no-character不生成手、脸、IP、拟人图标；笔记摄影采用无手变体，手绘模板不自动加吉祥物。小黑/小柠檬保留标准身份，不因画风重新设计角色。摄影质感生成图不冒充真实照片，UI示意不冒充截图。

## 01：按内容筛选后选择，而非固定默认

操作者明确指定画风/参考优先，默认只作用于选定插图，逐图可覆盖；全片主视频语言独立锁定，只有用户明确要求才整体覆盖；使用原名称或稳定ID均可。指定画风与内容不适配时先尝试拆页、精简、局部展示；确有冲突时说明，不静默换风格。在历史兼容或用户明确重选、且没有选定稳定profile时才使用`semantic_random`：先根据文案信息关系、阅读量、来源素材、角色和背景限制筛选适用候选，再在同等适配候选中按项目seed抽选。候选只有一个也可采用并说明原因，不为随机强行使用不适配画风。

主视频保持统一的构图主次、角色和运动语言；当前三风格知识插图按语义选择思维导图、知识卡片、信息图或实例图，材质与色彩继承同一系列profile。现有顶层visual_style_id只是插图系列候选基准，不是全视频风格；逐图visual_style_id才是实际素材画风。不得将插图铺满全片或把所有镜头替换为文字页。已有近期选择记录时优先减少无理由重复，没有记录如实写明。保存候选、排除理由、seed、最终结果和参数，重试复用结果；只有操作者要求重选或文案/限制发生实质变化才重新选择。禁止每次回退“默认网格卡片”。

在01-presentation-plan.json增加`visual_design`：
```json
{
  "schema_version": 1,
  "selection_mode": "semantic_random",
  "seed": 248,
  "visual_style_id": "blue-red-notebook",
  "candidates": [
    "blue-red-notebook",
    "ivory-diagram"
  ],
  "selection_reason": "文案讲需求检查与案例字段，纸面批注便于对应对象",
  "series_parameters": {
    "paper": "米白横线纸",
    "ink": "深蓝",
    "accent": "暗红与淡黄",
    "typography": "清晰手写感"
  },
  "image_designs": [
    {
      "id": "I01",
      "shots": [
        "S02"
      ],
      "trigger_text": "测试用例由哪些部分组成",
      "learning_goal": "对应字段与具体案例",
      "diagram_type": "anatomy",
      "visual_style_id": "blue-red-notebook",
      "route": "imagegen",
      "required": true,
      "aspect_ratio": [
        3,
        4
      ],
      "target_px": [
        1200,
        1600
      ],
      "content_basis": "标明的说明性示例",
      "display": {
        "center": [
          0.32,
          0.49
        ],
        "size": [
          0.292,
          0.692
        ]
      },
      "motion_intent": "左图先进入，停稳后逐项标注",
      "text_plan": "准确字段和批注为独立文字层",
      "layer_ids": [
        "L01"
      ],
      "prompt_file": "prompts/I01.md"
    }
  ],
  "repetition_review": "逐拍核对图型、构图与有效焦点，连续相似注明教学理由",
  "selection_algorithm": "sha256-sorted-candidates-v1",
  "candidate_reasons": {
    "blue-red-notebook": "适合需求检查和字段案例批注",
    "ivory-diagram": "适合需求检查和字段案例批注"
  }
}
```
此示例只含一张记录；如果规划双图，必须另列I02及完整任务书，不把示例当最终分镜。随机只作用于兼容表现，不生成技术事实。01纯规划时route为设计路线，不声称文件已生成。

## 明确逐素材设计方向：authored_per_asset

已有具体素材设计方向时，visual_design.selection_mode可为authored_per_asset，不强制随机选择目录画风。每个顶层/逐图visual_style_id均在visual_design.authored_treatments中定义medium、palette、semantic_reason、reference_policy；分别说明材质、实际颜色、为何适配知识点、用户参考与原创设计的关系。逐图仍填写完整image_designs，不能只写一个新画风名称绕过设计。操作者指定的参考/颜色优先，不因原创模式忽略。02按此继承，不重抽；主视频语言仍独立。当前三风格以固定profile作为明确方向，不重抽；历史兼容或用户明确重选且无方向时才沿用semantic_random。详见[素材规划标准](material-planning-standard.md)。

## 比例、尺寸与双竖图

视频16:9不代表每张素材16:9。根据内容选择3:4/4:5竖图、1:1、16:9总览或长图；比例是任务书的必填决策，不继承原模板默认比例。每个I写独立内容、比例、目标像素、实际上屏中心/尺寸、可见区、阅读停留与字幕安全区。

1920×1080的双竖图可参考两张约560×747、中心x=0.32/0.68、y=0.49，保留标题与字幕空间；这只是起点，最终用真实成片像素验证。双图分别生成/排版，统一系列参数，不能把一张横图硬切为两张知识卡。既有横图可作总览或明确的局部视窗，但不冒充两项独立设计。若仍不可读，减内容、逐张放大或拆拍，不能继续缩字。

每个镜头设计图文关系：并排对照、先后进入、局部放大、实例如实批注、长图固定视窗等；注明入/停/出时机。完整栅格图只允许整图或视窗运动，需要单独揭示的字、箭头和对象必须拆L层，不声称栅格内部可编辑。

## 02：制作与真实文件验收

图片制作仍在02-images，03-voice-clone保持配音职责。操作者口头称“03图片设计”时路由到02图片能力，不创建第二条冲突流程。02继承visual_design和01任务书，不再次随机选画风。style-lock保留原角色style_id，新增visual_style_id、selection_mode、seed、series_parameters和逐图覆盖。

manifest每项新增visual_style_id、aspect_ratio、target_px、实际width/height、route、prompt、source_brief、qa。route=imagegen的任务必须有实际生成图并查看；程序绘制同色矩形或贴纸不能冒充生成图。精确中文可独立排版，但保留已规划的插图内容。技术工具不能完成时标unresolved，回报可行改镜方案，不静默取消。

检查每张内容/文字/箭头/比例/风格/角色、双图独立性、动态拆层与最终上屏可读性。记录实际完成数、计划数与缺口；数量不作为视觉质量的替代指标。贴纸只作辅助，不代替必需知识图。

## 04：素材执行与可见性验收

最终edit-plan的图片clip写`image_design_id`与真实file，保留I→镜头→clip→草稿segment映射；裁切/处理后文件记录原图来源。所有required图片在草稿实际segment和成片中都应出现，不能只存在于manifest。按真实占屏尺寸、fit和运动检查可读性，而非只看原图分辨率。

合成前运行01-shot-list/scripts/validate_visual_design.py的01/02/04模式，具体参数见--help；新增流程必须执行，旧项目没有visual_design时先补设计，不伪造已验证状态。04模式仅查执行计划，不证明真实草稿已入轨。保存visual-execution-report.json：每个I的实际文件、clip及segment ID、出现时间、占屏范围、实际视频证据帧路径、人工/代理检查状态及缺口；统计生成主图展示时长采用时间区间并集，多图并排不重复累加，不设凑数量/比例门槛。

继续原有audit_delivery对真实草稿、MP4与hash检查；再从实际成片抽取各图片稳定展示帧，双图/细节/字幕区重点检查，动效看入场、停稳、退出多帧。人工/代理查看记录可读性、字幕遮挡和构图重复，未看就写未检查。缺图/未入轨/不可读为partial，不交付完成；更新01后才允许替代。此契约不新增生图、素材采购、上传或发布的授权。

## 检查命令

以skill目录为工作目录（P替换为项目绝对路径，vN替换为当前版本）：
```sh
python3 01-shot-list/scripts/validate_visual_design.py --stage 01 --plan P/01-shot-list/01-presentation-plan.json
python3 01-shot-list/scripts/validate_visual_design.py --stage 02 --plan P/01-shot-list/01-presentation-plan.json --manifest P/02-images/vN/asset-manifest.json
python3 01-shot-list/scripts/validate_visual_design.py --stage 04 --plan P/01-shot-list/01-presentation-plan.json --manifest P/02-images/vN/asset-manifest.json --edit-plan P/04-video-cut/vN/edit-plan.json
```

验证图片需可用Pillow；缺少时使用已配置的图片制作Python环境，不将无法读取视为通过。版本路径按current.json定位，不能固定读旧版。处理后裁切图仍由原I追溯，真实画面及裁切正确性单独审核。

## 可执行补充：帧数、随机与双竖图（当前门禁）

图片清单唯一位置为visual_design.image_designs。旧顶层image_designs须迁移；两份存在却不同会报错。user/semantic_random的插图系列、逐图及候选画风ID须存在于目录；authored_per_asset的实际样式须具有上述完整声明，候选目录ID仍需有效。随机筛选仍需代理按文案给理由；真正抽选使用：
```sh
python3 01-shot-list/scripts/select_visual_style.py --seed 248 --candidates blue-red-notebook ivory-diagram
```
将输出selection_algorithm、seed、candidates、visual_style_id保存到visual_design，并填写candidate_reasons（以候选ID为键的理由）、selection_reason和series_parameters。校验重算结果，不允许任填最终画风。user模式不强制随机。

双竖图明确增加composition_groups:[{id:"pair-01",type:"portrait_pair",image_ids:["I01","I02"]}]，每项I的composition_group引用同一id；分别给完整内容、竖图比例、display.center/size。02按文件摘要拦截相同文件，双图不接受derived_from裁切派生。摘要不同不证明语义独立，仍要查看两图。需裁切既有横图时按普通局部视图设计，不标独立portrait_pair。

04每个图片clip增加reading_window_s:[局部开始秒,局部结束秒]，此窗口稳定可读，入出场运动放窗口之外；移动长图可拆为多个稳定阅读视图。检查实际contain/cover尺寸和关键帧后的范围。reading_safe_area默认[0.03,0.12,0.97,0.85]，可按真实标题字幕位置显式调整并复核。双竖图同时稳定展示时不得意外重叠。当前自动几何校验不支持旋转知识图；需要旋转时另作已验证布局实现，不跳过检查。

asset-manifest中derived_files可登记同I的处理文件（相对manifest）；clip实际文件须与登记原图/处理图摘要一致。独立双图仍不允许用此方式冒充独立设计。

edit-plan新增visual_inputs，含presentation_plan、asset_manifest（相对edit-plan或绝对路径）及各自的presentation_plan_sha256、asset_manifest_sha256。先冻结输入再计算摘要。apply_presentation保留并转换路径；build、render自动调用visual_gate，旧计划缺这些信息会停止，须迁移而非绕过。

构建摘要保留image_design_id。最终audit要求visual-execution-report.json位于edit-plan同目录：plan_sha256、mp4_sha256和images数组；每项含image_design_id、segment_ids、evidence_frames（实际视频入场/稳定/退出至少三帧路径，相对报告目录）、readable/subtitle_clear/content_checked/motion_checked真实查看结果。audit比对真实草稿素材内容和clip，不只看编号。报告只可在实际看图后填写，文件存在和声明不能证明美术质量或证据来源真实性。

背景：edit-plan.fps为统一输出帧率（当前默认24），准备按ceil(duration×fps)+1帧生成静音循环素材，并真实解码核对。构建、渲染及audit预检实际可用帧；多余一帧不延长旁白/时间轴。render的--fps与计划不同时报错，需修改计划并重新准备背景。保留原始缺帧报错，不以冻结末帧掩盖损坏素材。

主视频、角色锁定和插图作用域必须另外填写[执行质量契约](execution-quality-contract.md)，旧版图片检查不能替代该契约。
