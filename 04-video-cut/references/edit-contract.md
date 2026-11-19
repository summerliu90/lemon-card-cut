# 合成输入技术协议

edit-plan以它所在目录为相对路径根，所有时间用全局秒，构建时仅转换一次成微秒。不要直接把秒传给整数微秒接口。

## 最小结构

```json
{
  "schema_version": 1,
  "name": "AI测试_小黑_播客男_v1",
  "canvas": [1920,1080],
  "duration_s": 61.2,
  "timing_status": "intra-shot-estimated",
  "clips": [
    {"id":"C02-S03","kind":"image","file":"../../02-images/v1/images/i02-overview-device.png","start_s":11,"end_s":15,"track":"Card02","center":[0.21,0.54],"size":[0.25,0.34],"fit":"contain","keyframes":{"position_y":[[0,-1.6],[0.35,-0.08]]}},
    {"id":"subtitle-1","kind":"text","text":"但能生成，不等于能落地。","start_s":7,"end_s":10,"track":"Subtitles","center":[0.5,0.90],"role":"subtitle","font_name":"新青年体","font_file":"项目真实字体路径","font_sha256":"实际字体文件SHA256","jianying_font_size":7,"font_px":56,"color":"#FFDE00","auto_wrapping":true},
    {"id":"narration","kind":"audio","file":"../../03-voice-clone/v1/narration.wav","start_s":0,"end_s":61.2,"track":"Narration","volume":1}
  ],
  "required_layer_ids":["L01"],
  "implemented_layer_ids":["L01"],
  "unresolved":[]
}
```

这只是字段示例，不代表当前项目音频实际时长。每个clip必须有唯一ID。image/video/audio必须file真实存在，text必须有原文。需要原生贴纸可kind=sticker、resource_id以及verified=true，必须通过本机验证。effect资源由实际运行时API查证后再添加，不猜ID。

center是左上原点的中心归一化坐标；转换Jy坐标：x=2*cx-1、y=1-2*cy。size是画布比例，image按其自身宽高与画布fit基准计算uniform_scale，保持比例，不能scale_x/scale_y乱拉伸。图片内部L坐标先转换至卡片局部，再合成至全片。字号font_px以最终画布像素描述，适配为当前库字号需要预览验证。

关键帧时间为片段起点的局部秒，**当前复制的vendor接口使用相对偏移，不是全局时间**。property支持position_x、position_y、uniform_scale、alpha、rotation，属性值使用Jy坐标/实际缩放值。alpha仅视频图片有效，文字淡入淡出用实际可用的TextIntro/TextOutro；不把错误的alpha关键帧强加文字层。

长图固定窗口可拆成多段裁切帧或用蒙版+窗口内运动，实际实现与未完成项写summary；未经明确授权不得降级替代。图片组与L层跟随同一卡片的移动/缩放，不能只动底图留下按钮。

运行：

```bash
python3 <skill>/04-video-cut/scripts/build_video.py --plan <edit-plan.json> --out <本次04输出目录>
```

运行时复制自05-edit，可用 `asset_search.py`、`draft_inspector.py`检查，不自动调用旧总控。业务编译脚本由代理根据01/02/03生成到项目scripts/，不能指望自然语言表格直接成为时间轴。

## V/BG视频编译

视频沿用kind=video、真实file、start_s/end_s、source_start_s、center/size、fit与muted/volume，源入点以实际文件为准：02已预裁片段的文件通常从0开始，不能再加一遍原片偏移。01估算时长不可冒充源片实际长度，超出素材时长先处理或回报，不任由末帧冻结。

clip增加video_asset_id与role=scene/ambient/demo用于追溯，导演计划另保留源URL/许可、人物开关、BG绑定、选段和处理方式。这些追溯字段不是渲染滤镜；不假设仅写blur、crop_anchor或loop就会生效，需准备文件或使用已验证实现。局部V不要使用track=background，该轨由apply_presentation按task重建；用独立视频轨与明确z层级，并验证标题/字幕始终在上。

## v2图文与互动协议

合成前保存direction-plan.json，绑定01-presentation-plan和02-presentation-assets。clip可以带role=sticker、meme_id、resource_id（来源关联）及provider；若使用本地动画则kind=video/image，不能把来源ID当已成功添加的原生贴纸。字幕/章节字体颜色与字号在text clip中明确写出。

音效为独立kind=audio，带role=sfx和sfx_id；start_s/end_s和volume为实际混音参数。MP4渲染先用mix_audio.py按同一计划生成mixed-audio.wav，草稿保留原旁白与各音效独立轨。render-check需记录音轨数、动画视频数与音效数，build-summary从实际segment收集M/E/L标识核验，而非仅相信计划中的数量。

新计划必须设置fps与visual_inputs（01/02路径及SHA256）；图片clip保留image_design_id和稳定reading_window_s，规则见[画风执行契约](../../01-shot-list/references/visual-style-contract.md)。构建和渲染会强制校验，最终audit另验证真实草稿和视觉证据报告。

跨阶段素材身份、角色参考、样片及最终审看要求统一见[执行质量契约](../../01-shot-list/references/execution-quality-contract.md)。

## 表情主次与最终尺寸

meme clip的size为最终容纳框；size_px→size只转换一次；读取[表情编排契约](../../01-shot-list/references/meme-staging-contract.md)。


## 剪映内稳定性与草稿箱交付

图片和文字在稳定阅读区间不能抖动、闪烁或跳位；动效存在不等于播放有缺陷，文件检查也不等于应用内验收。交付必须登记到用户实际使用的剪映草稿箱，并从首页打开、连续播放验证。ZIP 和浏览器 MP4 仅为辅助证据。无法控制剪映时明确记录阻塞和待验收状态，不标记已修复。

先验证当前 vendor 的关键帧语义：`uniform_scale` 会导出 `KFTypeScaleX` 并保持 `uniform_scale.on=true`，这是等比缩放表示，不应因没有 Y 曲线就自动判错或额外补 Y。双轴独立缩放应关闭 uniform_scale，并按实际应用版本验证；不要把未验证的“修复”批量传播到其他草稿。

用户报告抖动时，保存原工程，分别检查 native 关键帧、素材内循环动作、图层和播放性能。生成独立静止对照版时移除全部视觉关键帧和运动效果并核验剩余数量为零，名称/报告明确标注诊断用途和动效损失。未播放确认不能宣称根因已确认。其他草稿分别记录本机文件检查、源文件回退和应用内验收，不能把共同使用某参数写成共同故障。


用户需要动态效果时，静止对照只用于诊断，不作为最终修复交付。保留原分层工程，可新增“动效保留兼容版”：用原计划渲染无字幕图文底片，单视频轨承载原运动，原生字幕和音轨独立保留，视频轨静音避免双重配音。明确镜内图片/正文文字不能逐层编辑；字幕仍可编辑。兼容方案不能写成原生关键帧根因已修复。工具 render_preview.py 的 --omit-subtitles 模式先验证完整计划，再只省略 SUB-/role=subtitle 文字，render-check 会记录省略清单；草稿字幕条数必须与该清单一致。


若用户确认“剪映预览抖动，但同一草稿从剪映导出正常”，优先排查预览实时合成、缓存或渲染兼容性；具体原因未证实前不要批量删除/改写关键帧，也不要用静止或图文合成底片替代可编辑原工程。兼容版仅作为可选绕行方案。预览设置、代理或预渲染必须以目标版本实际可用界面为准。
