# 动态分镜执行契约 v2

01同时交付 narration_segments、visual_beats 和 execution_contract.scenes。3—5秒只是局部事件的建议间隔，不是强制换镜频率；语义场景可持续8—15秒或按阅读需要延长。场景内通过对象移动、连线、状态推进和局部强调解释内容，保留停稳阅读窗。禁止同图重新入场、微缩放或换文字冒充内容推进。相邻相同构图可合为一个节拍，在其中保存多次局部动作。完整执行要求见[执行质量契约](execution-quality-contract.md)。

优先按语义选择学习库配方。motion_ref使用id/version/recipe_sha256，必须能在01保存的 motion-library-snapshot.json中解析，并校验配方文件SHA256。没有匹配项时 motion_ref=null、origin=original，写明原创，不虚构学习成果。motion_events逐项给layer_id、phase、start_s、duration_s、property、from/to；asset_requirements必须能映射02素材编号和图层。trigger_text原样取自文案，selection_reason说明语义关系。implementation_route选择keyframes或jianying_native，validation_status记录unverified/render_verified/native_verified和证据文件。未验证不能写ready。

02按每拍输出构图：可选扇形资料拼贴、气泡与长条输出、撕纸对照、放大镜证据、径向字段图；让形状服务信息关系，避免全片重复左右矩形卡。分别交付人物插图、结构底板、独立中文、箭头连线和表情，注明文件数与生图数。已有插画可换构图复用，但不能把同一左侧插画连续固定几十秒。

字幕使用production-profile.json：新青年体、#FFDE00、剪映字号7、无字幕底条；1080p本地预览56px是渲染换算，不是剪映字号。font_file指向本机真实字体，缺字/缺文件时报错，不静默替换。普通字幕不循环弹跳。M表情按[表情编排契约](meme-staging-contract.md)保存最终size_px：通常512像素，重点反应可更大，允许居中及下角；停稳约2—3秒后退出。显式最终尺寸不再乘1.3；背景让位与结果保留在01设计，无人物风格不添加表情。

03复用已确认音频，视觉换镜不触发重新配音。04按真实音频校准visual_beats，采用线性关键帧、入场后稳定停留，不对字幕逐帧反复入场。

剪映原生动效使用native_animations:[{enum_type,name,resource_id,duration_s,validation_status,evidence}]；enum_type为TextIntro/TextOutro/TextLoopAnim/IntroType/OutroType/GroupAnimationType。native_effects使用VideoSceneEffectType或VideoCharacterEffectType及params。名称与resource_id必须和本地枚举同时匹配，禁止模糊匹配；未验证只能用于明确标注的测试草稿。原生效果不能直接由Pillow重现，MP4预览遇到这些字段应报错；另编译明确说明差异的关键帧近似计划，分别交付，不能声称两者完全一致。循环动画不得用于普通字幕。

执行检查：python3 01-shot-list/scripts/validate_plan.py --plan <01-presentation-plan.json>。旧版无visual_beats的计划需要迁移，不能以旧计划合格代替新验收。01通过后02/04仍需检查实际图片、视频抽帧及原生草稿；本脚本只验证交接数据。

## 固定引用示例与下游执行

01的motion_snapshot填写select生成的immutable_snapshot所指文件（路径相对当前计划目录，或绝对路径），避免后续select改变旧分镜候选。对有匹配项的镜头：

```json
{
  "motion_ref": {
    "id": "实际候选的motion_id",
    "version": 1,
    "recipe_sha256": "实际候选的recipe_sha256",
    "recipe_file": "/实际候选的recipe_file"
  },
  "selection_reason": "口播为并列对比，采用双区稳定对照",
  "trigger_text": "逐字引用当前文案",
  "layout": "split_comparison",
  "motion_events": [{"layer_id":"L01","phase":"enter","start_s":0,"duration_s":0.3,"property":"alpha","from":0,"to":1}],
  "asset_requirements": [{"id":"L01","type":"comparison_plate","separate_text":true}],
  "implementation_route": "keyframes",
  "validation_status": "unverified"
}
```

上例是字段说明，不能把示例ID/hash直接放入项目。02交付清单使用同一layer_id；04从motion_ref的固定recipe_file读取动作，适配时长后逐项保存到edit-plan，编译记录clip_id到原生segment_id的映射。任何自定义适配都写偏差原因。计划验证通过、MP4渲染通过、剪映界面播放通过是三种独立状态，分别记录，不能互相替代。


## 图片与视频的设计多样性交接

按[图片选型与全片搭配](visual-design-catalog.md)设计知识图和素材混合，按[视频素材规范](video-asset-spec.md)规划V/BG。01提供image_designs、video_assets、media_mix和footage_policy，02保留图型/局部表现差异并交付真实videos.json，04落实选段/窗口/前后状态。人物开关默认false；显式开启仅允许真人视频，no-character生成图仍无人、M=0。现有validate_plan不自动核验这些新增字段或识别人像，需阶段复核。

一张结构图或实例可跨多个局部事件，逐拍给不同可读区域或批注/实例焦点；不能为了换镜重生成近似全图，也不能为了“丰富”切成与当前技术句无关的实拍。当前layout_families是候选不是白名单，允许按知识关系设计新构图；原图型/图层与动效引用须保持可追溯。
