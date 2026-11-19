# 03-voice-clone｜音色与配音

承接01逐镜口播，生成真实配音、原文字幕及实测镜头时长。名称包含clone，但复用已有voice_id时不新建克隆。用户提供样本并明确要克隆时才运行clone_voice.py；没有音色偏好先读取已有项目设置/配置，未配置时推荐目录中的“播客男”。

## 路径与迁移

脚本移植自gzh_to_video/04-voiceover，保留MiniMax/Edge合成、WAV修复和音色克隆；适配为本阶段独立目录与音色catalog，9份现有voice_id映射已迁移。没有复制.env密钥或用户声音样本。

配置从环境或 `LEMON_VOICE_CONFIG_ROOT/.env` 读取，默认是lemon-card-cut根目录.env；如复用原配置，运行时显式 `--config-root <gzh_to_video目录>`。这是可选外部配置路径，不是硬编码依赖。源脚本中的旧gzh/tutor路径仅为历史注释，以本流程为准。`LEMON_CLONE_INPUT_DIR`可指定项目克隆样本目录。

## 工作流程

1. 读取 `01-shot-list/01-shot-list.md` 的逐镜口播，以及02的style-lock和图片manifest；不从卡面文字拼旁白，不读镜头操作指令。先生成 `segments_input.json` 和 `tts.csv`，保留原文text与发音speak_text两份。
2. 只改speak_text读法：AI→A I，666→六六六；状态码逐位读、数量正常读、百分比/日期按语义展开。其他术语逐项核对。原文text用于字幕，不能被TTS读音替换。
3. 记录provider、voice_label、voice_id、语速、模型和配置来源；只合成所选声音，禁止失败后默默切provider/声音。复用已有ID优先。新克隆的source/prompt、结果ID写入项目，不动共享已有ID。
4. 使用 `scripts/run_voiceover.py` 准备与合成。仅有准备文件不是配音完成。按文案＋音色设置摘要复用音频；只重做变更段。源generate_tts的自动Edge回退在适配器中关闭。
5. 对每段ffprobe测时、解码为32kHz单声道PCM WAV，剔除非音频尾部数据；无默认0.5秒镜间空白。累计真实时长得到S镜起止，末尾默认留1秒完整画面。不得仍沿用01估算76秒。
6. 保存原文SRT和subtitles.json。若没有真正词级时间戳，标记 `estimated_within_measured_shot`，不把按字数均分冒充强制对齐。句内动作可先按比例适配并标记；交付前试听AI、六六六和段落边界。不能检测音频就谎称已试听。
7. 写 `segments_audio.json` 和项目根 `03-voice-manifest.md`。保留01的S编号；04以本文件真实时长为准；保留01估算版并创建音频校准的新版本，不重跑TTS覆盖03。

## 命令

```bash
# 先准备，绝不自动调用网络服务
python3 <skill>/03-voice-clone/scripts/run_voiceover.py --project <项目目录>
# 合成并实测、拼接、保存交接
python3 <skill>/03-voice-clone/scripts/run_voiceover.py --project <项目目录> --config-root <配置目录> --synthesize
# 只接入已经完成的逐段音频
python3 <skill>/03-voice-clone/scripts/run_voiceover.py --project <项目目录> --finalize
```

版本参数 `--version v2` 保留旧版本。依赖见requirements.txt，另外需要ffmpeg/ffprobe。API失败保留输入与失败状态，不用无声替代旁白。不得在报告、JSON或日志中打印API Key。

## 给导演编排的时间信息

向04传递原文触发词与时间精度：优先实际词级边界，没有时按镜内语义片段估算并保留标记。不要为了容纳表情/音效改读白；原音频可以复用。M/E的具体时间在04导演编排决定，并按字幕和阅读窗口检查冲突。

## 输出

`03-voice-clone/vN/`：segments_input.json、tts.csv、voice-settings.json、audio/Sxx.wav、audio/Sxx-pcm.wav、narration.wav、segments_audio.json、subtitles.srt、subtitles.json。输入/配置摘要与音频逐段关联；记录听审与时间对齐状态。目录中只有完整真实音频才可交给04。

版本读取：如项目01-shot-list/current.json存在，先按其中shot_list/image_briefs/presentation_plan定位当前版本，不固定读取旧的根目录v1文件。

## 飞书锁定音色

有00-feishu-source/task.json时run_voiceover.py自动采用task.voice对应MiniMax音色，校验实际voice_id；与--voice或--provider冲突时报错，不回落到默认播客男或Edge。批准的口播原文是唯一配音来源，分镜逐镜text拼接需覆盖原文，不能为了5—10个表情改写口播。

## 动态分镜执行契约 v2

执行本阶段前读取[动效、视觉节拍与字幕交接契约](../01-shot-list/references/motion-contract.md)，继承01固定的动效版本与素材要求；不能在后续阶段重新猜测构图或替换未验证效果。

输入来源和冻结规则见01的[飞书与本地输入接入](../01-shot-list/references/source-intake.md)。项目00-feishu-source/task.json由01生成，现有消费路径保持不变；它不是另一个必需的skill阶段。

## 跨阶段质量交接（必读）

遵守[执行质量契约](../01-shot-list/references/execution-quality-contract.md)。只调整实测时间；不得删减必需视觉设计。时长改变须回写01的新版本、重排阅读窗，重新检查01/02交接。

## 已确认制作规则入口

每次执行先读取[制作规则总表](../01-shot-list/references/production-rules.md)。字幕固定为剪映原生可编辑字幕、新青年体、字号7、#FFDE00；以production-profile.json及实际草稿检查为准，不以本地预览像素代替剪映字号。

用户2026-10-27已明确默认授权将本工作流已审核口播发送至MiniMax生成表内指定音色，无需逐条重新确认；项目voice-settings或task保存authorization来源与时间。授权不包含更换服务、新建克隆或上传发布。
