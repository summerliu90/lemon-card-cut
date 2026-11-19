# 执行质量契约 v1

本契约约束新制作与返工，不自动认证历史视频。主入口、00学习、01分镜、02素材、03配音、04构建/预览/交付共用本契约。图片细节另见[画风契约](visual-style-contract.md)，动效细节见[动效契约](motion-contract.md)。

## 设计边界

主视频语言来自用户指定的整体参考，例如《测试2》中的清爽底色、角色、构图、连线、场景动作和连续讲解。先确认实际参考路径，再提取参考；不要假装已观看不存在的文件。风格.md及知识类参考仅作用于部分素材：按语义使用思维导图、信息图、知识卡片、对象示意和实例图，不把画风升级为全片皮肤。顶层图片系列参数只约束插图候选，逐图ID约束实际插图。主视频与局部素材保持协调，允许插图风格多样，不要求每镜换风格。

严禁静态场景画当全片壁纸、长期固定右侧框、纯文字页串联、靠整页淡入/缩放冒充知识动态。纯色底允许。用对象、关系和状态解释内容；文字承担标签、结论和字幕，不替代承诺的插画。3—5秒是局部事件建议，语义场景按理解需要保持8—15秒或更久；先停稳，再局部推进，不能强制全页频繁切换。

小黑只能沿用实际参考/已认可素材及其一致姿态，不按文字描述临时用多边形重画。无标准参考时标记待补，不能制造一个“标准IP”。禁止自行增加“华华·测试实战”“教学示例”等品牌或无关脚注。生成的UI示意如需说明真实性，用正常项目审核说明，不擅自加画面页脚。

## 01冻结的执行单

01-presentation-plan.json保留既有visual_beats和visual_design，新增execution_contract：

```json
{
  "version": 1,
  "main_video_language": "用户整体参考的文件、构图、字体、运动规则；与插图画风分开说明",
  "insert_style_scope": "selected_assets_only",
  "background_policy": "solid_or_changing_scene_no_static_scene_wallpaper",
  "character": {"mode": "none"},
  "pilot_scene_ids": ["S01"],
  "scenes": [{
    "id": "S01", "start_s": 0, "end_s": 12,
    "learning_goal": "理解输入、操作、预期的关系",
    "subject": "实际表单与检查动作，不能只做三个文字框",
    "composition": "表单主场景，局部插图按需进入",
    "continuity": "检查标记延续到下一场景",
    "reading_window_s": [3, 9],
    "asset_requirements": [{"id": "I01", "type": "illustration", "brief": "表单实例插画，不允许用文字矩形代替"}],
    "content_actions": [{"id": "A01", "target_ids": ["I01"], "description": "定位输入字段后显示与预期的连接，保留阅读窗口"}]
  }]
}
```

时间为场景绝对起止，reading_window_s为场景内偏移。source顶层duration_s必须覆盖全部场景。角色mode为xiaohei/lemoner时，character还须reference_file、reference_sha256（相对01文件）。插图仍按visual_design.image_designs保存图型、画风、比例、上屏面积、独立双图和阅读规则。原生设计可用native_text/native_shape/native_line，必须在01就约定；不能制作后把illustration改成native_shape求过检。

## 02→04身份保持

asset-manifest.json新增execution_assets数组，每项design_id与01素材ID一致，type不可替换。文件型素材保存file（相对manifest）和sha256；character额外保存identity_reference_sha256和identity_review_notes。保留原images、layers、videos等清单，以兼容图片尺寸及剪辑门禁。

edit-plan每个相关clip记录scene_id、design_asset_id、content_action_ids；文件必须与02已审核文件hash一致。动作ID映射只是结构追踪，代理必须逐项核对真实关键帧、分层变化或实际视频内容，不能写ID后认为动作已经实现。build摘要保留这些ID，可追溯至原生segment_id。素材拆层、裁切、动效视频派生需要在01/02登记独立资产与来源后重审，不能直接换文件。

01执行validate_plan.py与validate_execution.py --stage 01；02执行validate_visual_design.py既有检查及validate_execution.py --stage 02 --manifest。04 build_video.py和render_preview.py共同调用visual_gate.gate；audit_delivery.py调用audit_evidence。缺项必须报错，不得使用测试入口、原生特效测试标记或自定义审计脚本跳过门禁。

## 样片与最终交付

edit-plan.execution_phase为pilot时只渲染pilot_scene_ids指定场景，总时长须与样片场景总长一致，剪辑时间从0重排；选择连续的代表场景，必须包含实际角色、主要素材和关键内容动作。图片门禁仍要求承诺素材齐备，因此样片不得靠临时删除源设计出片。先观看实际样片再扩展全片。

final必须提供pilot_review_file（相对edit-plan），内容包括：source_sha256（整个01 JSON按ensure_ascii=False、sort_keys=True序列化后SHA256）、scene_ids、accepted=true、reviewer、具体notes、video/video_sha256、render_summary/render_summary_sha256。文件都相对edit-plan。样片制作过程与审看必须真实；改01后样片证据失效。要求用户审核的项目须等用户明确认可，其他项目由执行代理实际审看并记录，不额外制造确认流程。

最终visual-execution-report.json保留原plan_sha256/mp4_sha256/images，增加scene_reviews：逐scene_id记录subject_matches、character_consistent、style_scope_correct、content_motion_visible、reading_comfortable、continuous_playback_checked为true，reviewer、具体notes和至少三张真实入场/稳定/离场evidence_frames。逐段连续播放核对，重点检查开头至1:26等曾失败区段；不可只检查最后几张图。工程验收和视觉验收分开报告，不可把布尔值、hash或文件存在解释成高级设计已获自动认证。

## 变更与禁止降级

缺资产、阅读面积不够、角色失真、动作没实现时返回01或02解决，保留未完成状态。不允许将多项承诺统一指向少量不相关素材，或改冻结计划删需求、伪造审看证明。必要变更保存新版本、原因及受影响ID，重新审看；用户批准的背景/字幕覆盖记录在输入接入与新01中，渲染和审计使用同一有效配置，不能各自读不同默认值。

人工审看须确认：主体与语音匹配、类型不降级、角色不变形、插图不篡改主风格、内容动作有解释作用、阅读舒适、字幕无遮挡、素材真实出现且完整。当前脚本能拒绝缺契约、缺资产、替换文件、缺映射及缺审看证据；不能自动判断审美、运动语义、虚构审看或画面中是否偷偷添加文字。不得声称完全自动保证这些主观质量。

## 逐镜参数完整性

全片有效解释素材分布按[素材规划标准](material-planning-standard.md)规划。04共用门禁逐项比对action_specs与实际clip关键帧的属性、起止时间及数值；动作object_id可直接对应clip ID，否则以对象asset_id及action_id定位。当前执行路线为数值关键帧，其他动作需先明确并实现可验证适配，不能只写语义ID。最终审计逐文字片段检查原生关键帧及真实字体缺字，保留人工/代理视觉验收。

以上v1示例仅展示契约外层，实际计划还必须按[逐镜细节规范](storyboard-spec.md)补齐narration_excerpt、timing_status、objects、action_specs和acceptance_checks。validate_scene_detail.py已接入validate_execution.py，01命令入口和04共用门禁都会检查；只有subject/composition/content_actions描述的旧计划不再通过。该检查验证参数完整、引用、时序及非空状态变化，不证明实际渲染按预期执行；最终仍要逐镜核对画面。

## 表情主次与最终尺寸

必需M进入场景资产和实际片段；最终像素、落点和停稳时间统一按[表情编排契约](meme-staging-contract.md)。
