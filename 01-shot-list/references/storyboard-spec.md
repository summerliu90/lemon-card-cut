# 分镜交付规范

## 交付顺序

1. 一段全片方案：内容结构、预估时长、画幅、底板、强调色、卡片系统及节奏；给出图片/情境/氛围/屏录搭配理由和footage_policy。
2. 总览表：镜号、起止时间、原文/口播片段、画面任务、可见卡片ID与数量、I/V/BG引用、media_role、图型与表现风格、布局、转场。
3. 逐镜执行描述：屏幕文字原文、素材内容、布局坐标、动态事件、字幕和离场状态。
4. 图片数量汇总和卡片—图片映射：区分独立设计图、复用图、程序排版/绘制、现有素材、透明动态层和预计导出文件数。
5. 逐张图片设计任务书：按 [图片设计交接规范](image-design-spec.md) 写明图型、具体内容、构图、逐字文案、风格、尺寸、分层与独立设计指令。不能只提供“流程图一张”这样的素材名称。
6. `01-video-briefs.md`按[视频素材规范](video-asset-spec.md)给V任务书、BG关系和获取状态；没有视频也注明原因。视频数与图数分开，源视频跨镜复用不重复计数。
7. 简短列出需配音校准或缺少素材的项目。用户只要简版时压缩表达，但保留卡片数量、内容和运动逻辑。

## 新增设计交接字段

保留既有narration_segments、visual_beats及动效引用结构。在01-presentation-plan增加：

- `footage_policy`：allow_live_action布尔值、selection_source、选择理由；默认false。
- `visual_design.image_designs`（唯一位置，画风选择及双图字段见visual-style-contract.md）：I编号及shots/beat_ids、learning_goal、diagram_type、visual_treatment、selection_reason、content_basis、完整任务书定位、独立L层与展示方式。
- `video_assets`：V编号及shots/beat_ids、trigger_text、media_role、动作/景别/机位、检索词、来源计划、目标画幅、预计长度、人物要求、处理/衔接与planned/unresolved状态；实测值由02提供。
- `media_mix`：逐拍对应图型、素材角色、I/V/BG引用、为何改变或保留当前构图。video_assets为空是合法选择，写清不采用原因，不强制随机或素材比例。

每拍的asset_requirements引用同一I/V/BG/L编号，区分image/video/background/dynamic_layer；非卡片全屏视频不必编造C编号。motion_events的layer_id可指视频层，动作仍遵循既有事件协议。新增字段是代理设计与交接约定，validate_plan.py入口同时检查节拍与execution_contract，validate_scene_detail.py检查逐镜细节；仍不能把其通过称为画面质量已验证；01需人工/代理复核编号、语义、可读性及开关。

## 坐标和时间

默认画布1920×1080，位置用中心点归一化坐标：左上(0,0)、右下(1,1)。宽高写占画布比例，旋转写角度。单独注明锚点与超画布起点，避免与剪辑软件坐标系混用。

一般把顶部约5%–15%留给标题，底部约85%–95%留给字幕，主体放中间；这是初始布局，按素材比例与实际字幕尺寸检查。所有关键文字距边缘留安全边距，重排不可穿过字幕区。

有音频用全局时间加口播触发词；无音频用预估全局时间和镜内相对时间。相邻镜头时间连续，每个事件不得超过所属镜头。叠化如有重叠，明确重叠长度。

## 单镜示例（新方案演示，并非参考视频实测）

**S03｜预估00:08–00:15｜口播：“先理解模型，再掌握提示词，最后学会调用API。”**

画面任务：基础概念逐步扩展为应用能力。顶部左侧保持“第一步：打基础”；底部同步原口播字幕。

- C01 模型原理图：中心(0.36,0.46)，尺寸(0.23,0.52)。
- C02 提示词结构图：中心(0.64,0.46)，尺寸(0.23,0.52)。
- C03 API请求/响应示意：中心(0.62,0.52)，尺寸(0.26,0.52)。缺真实素材时用自制示意占位，不编造截图。

| 镜内时间/触发 | 事件 | 结束状态 |
|---|---|---|
| +0.00，“模型” | C01从中心(0.36,1.30)滑到(0.36,0.46)，0.35秒，ease-out，透明度0→1 | 1张卡稳定 |
| +2.00，“提示词” | C02从(1.20,0.46)滑入，0.35秒，ease-out | 两卡并排，2张可见 |
| +4.20，“API” | 旧两卡整体亮度降至55%，0.20秒；C03从(1.20,0.52)进入，0.40秒；C01保留左侧，C02在后方 | 3张可见，C03为焦点 |
| +6.65 | 卡片组淡出0.35秒，背景保留 | 进入下一章，无遗留卡片 |

卡片封面不额外塞入整段口播；如需教学API细节，应延长或另开局部镜头，不能在此7秒内要求读懂三页资料。

## 长图滑动示例

“左侧路线文档”并不等于“图片滑动”。执行说明应写成：窗口中心(0.33,0.48)、尺寸(0.46,0.60)，圆角裁切；图片等宽适配，内容从顶部开始，在2.0–4.0秒将内容向上移动窗口高度的0.7倍，ease-in-out；在‘项目练习’小节停留1.2秒。右侧两张辅卡不动。超出素材实际高度时缩短距离，不出现空白；缺素材高度时标注滚动距离待测，不捏造像素值。

## 最终复核

- 一张卡对应一个稳定ID；同一卡跨镜复用不重复计为新素材。
- 分清“同时可见几张”与“全片需要几张”。装饰、背景和字幕不混算成知识卡片。
- 每次新卡进入说明旧卡去向；滑动/滚动有起点、终点、时长和停顿。
- 时间与文案一一覆盖，预估值明确；单张卡至少获得辨认主题的停留时间。
- 用户未提供音效时可建议轻入场/章节提示音，但不指定未经确认存在的素材文件。
- 相邻镜头不是仅换字/换色的同模板；保持相似若有教学理由应说明，不能为多样性破坏同维度对照。
- 教学图说明具体知识、实例和阅读区域；情境视频只建立情境，操作演示可核对内容与结果。
- 真人/手部素材符合footage_policy；V的预计时长和未获取状态没有冒充真实probe或ready。

跨阶段素材身份、角色参考、样片及最终审看要求统一见[执行质量契约](../../01-shot-list/references/execution-quality-contract.md)。

## 可直接制作的逐镜细节（强制）

“知识点＋素材名称＋弹入”不算完成分镜。每个execution_contract.scenes条目还必须填写以下数据，validate_scene_detail.py由01及04共同门禁调用：

- narration_excerpt：原口播逐字片段，必须能在narration_text中定位；timing_status明确estimated或audio_aligned。未配音的秒数都是估算，不能假称精确。
- objects：该镜全部必需素材的对象布局。每项保存id、asset_id、center、size、z、text（准确上屏文字；无文字填空串）、visible_start_s、visible_end_s、initial_state、end_state、exit_policy。全部时间为镜内偏移，位置/尺寸为画布归一化值，z越大越靠前。exit_policy为remove/carry/replace；carry必须写next_scene_id。文字对象在任务书额外写实际字体、字号、颜色和对齐；角色写姿态参考，不许下一步再设计人物。
- action_specs：每个content_actions的每个目标必须落到实际对象，保存action_id、object_id、start_s、duration_s、property、from、to、easing、expected_result。不能只填“出现/放大”。property与实际工具能力对应，不支持的路径/遮罩先明确预处理方案，不发明渲染器字段。
- acceptance_checks：本镜可观察的验收结果，例如“错误标记移动到预期结果列，输入列仍可读”；不能只写“高级、美观、动态丰富”。

例如12秒场景中，I01为已独立设计的测试用例实例图，L01为另外制作的定位标记；两个对象均进入asset_requirements。下例只展示其中一个对象的参数格式，不能直接当成完整分镜：

```json
{
  "narration_excerpt": "先看预期结果，再检查实际结果",
  "timing_status": "estimated",
  "objects": [{
    "id": "O-L01", "asset_id": "L01",
    "center": [0.32, 0.48], "size": [0.12, 0.08], "z": 30,
    "text": "", "visible_start_s": 0, "visible_end_s": 12,
    "initial_state": "定位标记在预期结果列", "end_state": "定位标记到实际结果列",
    "exit_policy": "remove"
  }],
  "action_specs": [{
    "action_id": "A01", "object_id": "O-L01",
    "start_s": 7, "duration_s": 0.6,
    "property": "position_x", "from": -0.36, "to": 0.36,
    "easing": "linear", "expected_result": "标记从左列移动到右列，底图不动"
  }],
  "acceptance_checks": ["I01完整可读，L01对应口播从预期列移至实际列，字幕无遮挡"]
}
```

注意position_x示例采用当前执行器的-1到1坐标；objects.center采用0到1。center(0.32,0.48)映射至position(-0.36,0.04)，纵轴还需翻转。每个动作声明实际属性坐标系，不把这两种坐标混用。该示例需补齐I01对象、A01语义目标及阅读窗后才能过检。

人读01-shot-list.md必须展开同一组数据，不能只在JSON中详细、Markdown只列摘要。图片自包含设计指令仍按image-design-spec.md逐图交付；视频选段、声音与原生效果按专项契约交付，不能把分镜动作参数当图片提示词。最终检查01→02→04：素材身份、准确文字、图层拆分、对象摆位、动作顺序和跨镜状态逐项对应。

## 表情主次与最终尺寸

逐镜交付meme_slots与对应objects/action_specs，按最终像素编排；读取[表情编排契约](meme-staging-contract.md)。
