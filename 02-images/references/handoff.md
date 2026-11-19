# 01 → 02 → 剪辑交接协议

## 01输入冻结

02先保存输入文件路径和摘要（可用SHA256），沿用I/C/S/L/V/BG编号。所有图片必须可追溯到01；新增M表情编号记录其对应台词和镜头。风格调整只改表现，结构、文案、尺寸、分层如需变更要列入design-report，不悄悄改01原文。

01同时存在人读说明与结构化数据时核对是否一致；冲突项标明，不由模型随机选一边。旧项目只有Markdown时，由执行代理按原文迁移完整结构化计划并复核；缺具体信息须保留未完成，不能绕过执行契约进入制作。无需要求用户手填JSON。

## style-lock.json

至少包含footage_policy、schema_version、style_id、选择来源(user/01/recommended)、选择理由、画布、背景(颜色/路径/运动及状态)、palette、字体及实际替代、图标语言、IP参考路径、文字制作路线。将选中的角色标准参考复制到项目sources/references，避免交接后失去身份参照。风格不只是名字，还要保存实际参数。

## asset-manifest.json

路径以manifest所在版本目录为根，写相对路径；禁止只留skill库原路径作为最终素材路径。实际文件必须存在。推荐结构：

```json
{
  "schema_version": 1,
  "stage": "02-images",
  "status": "partial",
  "inputs": {"shot_list": "../../01-shot-list/01-shot-list.md", "image_briefs": "../../01-shot-list/01-image-briefs.md"},
  "style_lock": "style-lock.json",
  "images": [
    {
      "id": "I01", "cards": ["C01"], "shots": ["S01", "S02"],
      "diagram_type": "ui-mockup", "style_id": "card-grid",
      "route": "svg-layout", "prompt": "prompts/I01.md",
      "source": "sources/i01-case-generator.svg",
      "file": "images/i01-case-generator.png",
      "width": 1400, "height": 600, "alpha": false,
      "text_mode": "typeset", "layer_ids": ["L01", "L02"],
      "focus_regions": [{"label": "按钮区域", "box": [0.29,0.36,0.42,0.16]}],
      "status": "ready", "qa": {"viewed": true, "text_checked": true, "structure_checked": true},
      "notes": "按钮与记录独立，不含在底图"
    }
  ],
  "layers_file": "layers.json",
  "stickers_file": "stickers.json",
  "counts": {"planned_images": 8, "ready_images": 1, "raster_layers": 0, "ready_stickers": 0},
  "unresolved": ["I02–I08待制作"]
}
```

示例是字段示范，不能原样冒充实际产物。status使用planned/generating/ready/failed/unresolved；整体使用ready/partial。ready必须满足存在、可打开、尺寸正确、人工/代理已查看；局部未完成则整体partial。focus_regions坐标是图片内左上x/y与宽/高比例，和01中心坐标区分。

## layers.json

按L编号列出关联I/C/S，类型native_text/native_shape/mask/raster，原生内容必须写准确文字、字体字号、颜色、几何、锚点、坐标系；raster另写真实文件路径、尺寸和alpha。开始/结束状态、01中的触发词和时间、缓动保持不丢。不是制作原生剪映图层，而是保存下一步可以构建的完整参数。

## stickers.json

允许空数组，并说明没有选用的原因。非空项至少：

```json
{
  "id": "M01", "intent": "confused", "matched_text": "但能生成，不等于能落地",
  "match_reason": "对应对一键落地的质疑反应，需在查看素材后填写具体理由",
  "provider": "local", "source": "来源库中的原始路径",
  "file": "stickers/M01.gif", "preview": "stickers/M01-preview.png",
  "resource_id": null, "verified_in_jianying": false,
  "format": "gif", "width": 0, "height": 0, "duration_ms": null, "frames": null,
  "shots": ["S02"], "timing": {"trigger": "不等于", "start_s": null, "end_s": null, "status": "待配音校准"},
  "placement": {"coordinate_system": "canvas-center-normalized", "center": [0.8,0.5], "size": [0.15,0.2]},
  "animation_intent": "短暂疑惑反应", "status": "unresolved"
}
```

尺寸为0等是示例占位，真实ready项必须读取实际值。原生provider=jianying时可没有动画本地文件，但必须保存预览/描述及resource_id，标明是native-reference；只有经过实际渲染验证才计ready。剪辑步骤按原生贴纸添加，不能把预览当最终资源。无资源验证能力时保留unresolved；可继续完成图片。

## 图片设计与视频清单扩展

image条目保存01的learning_goal、diagram_type、visual_treatment、selection_reason、content_basis与原任务书定位；不得因统一排版丢失图型差异。新增视频按[视频素材规范](../../01-shot-list/references/video-asset-spec.md)交付videos.json，asset-manifest增加videos_file、footage_policy及planned_videos/ready_videos计数；未采用视频时videos为空并记录原因，旧项目无videos_file按无视频处理。

每个V保存源文件/来源链接、许可、实际probe、选段、准备文件、用途、绑定镜头、人物检查与QA。全片base背景与镜头V覆盖分别记录；人物开关不改变生成图的角色限制。01设计字段和02实际资源映射都进入02-presentation-assets.json，未找到素材保留unresolved，不能将链接或原生预览计为ready。

## 剪辑读取顺序

先01-shot-list → 再02-asset-manifest.md定位版本 → style-lock → asset-manifest → layers/stickers/videos。图片按I绑定卡片，不按文件夹排序猜镜头；复用按原编号，独立层按L事件，表情按M匹配的台词触发。只消费ready项，缺失项明确列出；不因文件名存在就认为素材可用。

顶层02-asset-manifest.md链接本版本manifest、风格锁、设计报告，简列数量、路径、缺项。design-report写选定风格、逐张QA、表情选用理由、01变更、工具限制。交付时说明实际完成几张，不把未生成部分算进去。

新项目逐图增加visual_style_id、aspect_ratio、target_px和source_brief；style-lock保留角色style_id，另存visual_style_id、selection_mode、seed、series_parameters。见[图片画风执行契约](../../01-shot-list/references/visual-style-contract.md)。

跨阶段素材身份、角色参考、样片及最终审看要求统一见[执行质量契约](../../01-shot-list/references/execution-quality-contract.md)。

## 表情主次与最终尺寸

stickers与meme-anchors保留最终size_px、center、placement和context_handling；读取[表情编排契约](../../01-shot-list/references/meme-staging-contract.md)。
