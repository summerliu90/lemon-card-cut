# -*- coding: utf-8 -*-
"""
字幕合并与规范化。

默认 split：约 28 字/行 + 句内词级时间对齐。
可选 passthrough：整句一条（字多时用 --passthrough）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

TARGET_CHARS_PER_LINE = 18
# 单行约 18–24 字；超过则在逗号/短语边界拆行（视频最佳实践：中文每行不超过 24 字）
SOFT_MAX_CHARS_PER_LINE = 24
HARD_MAX_CHARS_PER_LINE = 30
MIN_CUE_DURATION_SEC = 0.4
MIN_GAP_SEC = 0.01
# 仅合并极短碎片（如单独「、」），避免把多句并成一行过长
MIN_PHRASE_CHARS_TO_MERGE = 6
# 字幕略早于词开始、显示到下一句开口（秒）
SUBTITLE_LEAD_IN_SEC = 0.08
SUBTITLE_END_AT_NEXT_SPEECH = True
# 句内最后一段保底占母 cue 时长的比例（降低避免尾句长时间冻结）
MIN_LAST_SEGMENT_RATIO = 0.08
TICKS_PER_SECOND = 10_000_000
# 每幕 FadeOut 固定时长（秒）——与 script.py SCENE_GAP 保持一致
# 字幕偏移 = audio_duration + SCENE_GAP_DEFAULT，确保下一幕字幕时间轴与视频一致
SCENE_GAP_DEFAULT = 0.5

# 合并模式：split = 拆行+词级同步（默认）；passthrough = 整句不拆
MERGE_MODE_PASSTHROUGH = 'passthrough'
MERGE_MODE_SPLIT = 'split'
DEFAULT_MERGE_MODE = MERGE_MODE_SPLIT

_PUNCT = set('，。；、！？,.;!?：:')
_SENT_END = re.compile(r'(?<=[。！？!?])[""」』]?')
_PHRASE_SPLIT = re.compile(r'(?<=[，、；：,;])[""」』]?')
_TOKEN_RE = re.compile(
    r'[A-Za-z][A-Za-z0-9]*|'
    r'[\u4e00-\u9fff]|'
    r'[，。；、！？,.;!?：:]+'
)


def _is_punct_only(s: str) -> bool:
    return bool(s) and all(c in _PUNCT or c.isspace() for c in s)


def tick_to_seconds(tick: float) -> float:
    return float(tick) / TICKS_PER_SECOND


def clean_display_text(text: str) -> str:
    text = text.replace('\n', ' ').strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_match_key(text: str) -> str:
    return re.sub(r'\s+', '', text).lower()


def parse_srt_time(t: str) -> float:
    t = t.strip()
    hh, mm, rest = t.split(':')
    ss, ms = rest.split(',')
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def format_srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms = int(round((seconds % 1) * 1000))
    total = int(seconds)
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    return f'{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}'


def format_ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    cs = int(round((seconds % 1) * 100))
    total = int(seconds)
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    return f'{hh}:{mm:02d}:{ss:02d}.{cs:02d}'


def _split_by_pattern(text: str, pattern: re.Pattern) -> List[str]:
    parts = pattern.split(text)
    parts = [p for p in parts if p]
    if not parts:
        return [text] if text else []
    return parts


def split_by_sentences(text: str) -> List[str]:
    parts = _split_by_pattern(text, _SENT_END)
    return parts if len(parts) > 1 else [text]


def split_by_phrases(text: str) -> List[str]:
    parts = _split_by_pattern(text, _PHRASE_SPLIT)
    return parts if len(parts) > 1 else [text]


def tokenize_subtitle_text(text: str) -> List[str]:
    compact = re.sub(r'\s+', '', text.replace('\n', '').strip())
    if not compact:
        return []
    return _TOKEN_RE.findall(compact)


def split_by_tokens(
    text: str,
    target: int = TARGET_CHARS_PER_LINE,
    soft_max: int = SOFT_MAX_CHARS_PER_LINE,
    hard_max: int = HARD_MAX_CHARS_PER_LINE,
) -> List[str]:
    tokens = tokenize_subtitle_text(text)
    if not tokens:
        return []

    joined = ''.join(tokens)
    if len(joined) <= soft_max:
        return [joined]

    lines: List[str] = []
    current = ''

    def flush():
        nonlocal current
        if current:
            lines.append(current)
            current = ''

    for tok in tokens:
        tok_len = len(tok)
        if tok_len > hard_max:
            flush()
            lines.append(tok)
            continue
        if not current:
            current = tok
            continue
        if len(current) + tok_len <= target or len(current) + tok_len <= soft_max:
            current += tok
            continue
        flush()
        current = tok
    flush()

    merged: List[str] = []
    for line in lines:
        if _is_punct_only(line) and merged:
            if len(merged[-1]) + len(line) <= soft_max:
                merged[-1] += line
            else:
                merged.append(line)
        elif line:
            merged.append(line)
    return merged


def split_for_display(
    text: str,
    soft_max: int = SOFT_MAX_CHARS_PER_LINE,
    hard_max: int = HARD_MAX_CHARS_PER_LINE,
) -> List[str]:
    text = clean_display_text(text)
    if not text:
        return []
    if len(text) <= soft_max:
        return [text]

    result: List[str] = []
    for sentence in split_by_sentences(text):
        if len(sentence) <= soft_max:
            result.append(sentence)
            continue
        for phrase in split_by_phrases(sentence):
            if len(phrase) <= soft_max:
                result.append(phrase)
            else:
                result.extend(split_by_tokens(phrase, soft_max=soft_max, hard_max=hard_max))

    merged: List[str] = []
    for seg in result:
        seg = seg.strip()
        if not seg:
            continue
        if _is_punct_only(seg) and merged:
            merged[-1] += seg
        else:
            merged.append(seg)
    merged = coalesce_short_phrases(merged, soft_max=soft_max)
    return merged if merged else [text]


def coalesce_short_phrases(
    segments: List[str],
    soft_max: int = SOFT_MAX_CHARS_PER_LINE,
    min_phrase_len: int = MIN_PHRASE_CHARS_TO_MERGE,
) -> List[str]:
    """合并过短逗号分句，减少「字幕消失 → 才开口」的空窗。"""
    if len(segments) <= 1:
        return segments
    out: List[str] = []
    buf = ''
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if not buf:
            buf = seg
            continue
        combined = buf + seg
        if (
            len(buf) < min_phrase_len
            or len(seg) < min_phrase_len
        ) and len(combined) <= soft_max:
            buf = combined
            continue
        out.append(buf)
        buf = seg
    if buf:
        out.append(buf)
    return out


def words_for_tts_cue(
    words: List[dict],
    local_start: float,
    local_end: float,
    pad: float = 0.15,
) -> List[dict]:
    """只取落在当前 TTS 句 [local_start, local_end] 内的词（避免从幕首重新匹配）。"""
    subset: List[dict] = []
    for w in words:
        t0 = tick_to_seconds(w['offset'])
        t1 = tick_to_seconds(w['offset'] + w['duration'])
        if t1 >= local_start - pad and t0 <= local_end + pad:
            subset.append(w)
    return subset


def _match_segment_words(
    words: List[dict],
    wi: int,
    segment: str,
    scene_offset: float,
) -> Optional[Tuple[int, float, float]]:
    """在 words[wi:] 中顺序匹配一个显示段（words 应已是当前 TTS 句切片）。"""
    target = normalize_match_key(segment)
    if not target:
        return None
    acc = ''
    seg_start: Optional[float] = None
    seg_end: Optional[float] = None
    while wi < len(words) and len(acc) < len(target):
        w = words[wi]
        piece = normalize_match_key(w.get('text', ''))
        if not piece:
            wi += 1
            continue
        if seg_start is None:
            seg_start = tick_to_seconds(w['offset']) + scene_offset
        seg_end = tick_to_seconds(w['offset'] + w['duration']) + scene_offset
        acc += piece
        wi += 1
        if acc == target:
            return wi, seg_start, seg_end
    return None


def align_single_segment_with_words(
    words: List[dict],
    segment: str,
    parent_start: float,
    parent_end: float,
    scene_offset: float,
) -> Optional[Tuple[float, float, str]]:
    """整句一条字幕：用该句内全部匹配词的首尾时间，结束时间固定为 TTS 句末。"""
    subset = words_for_tts_cue(
        words, parent_start - scene_offset, parent_end - scene_offset,
    )
    if not subset:
        return None
    matched = _match_segment_words(subset, 0, segment, scene_offset)
    if matched:
        _, ws, _we = matched
        s = max(parent_start, ws - SUBTITLE_LEAD_IN_SEC)
        return (s, parent_end, segment)
    # 兜底：句内所有词的包络
    ws = tick_to_seconds(subset[0]['offset']) + scene_offset
    we = tick_to_seconds(subset[-1]['offset'] + subset[-1]['duration']) + scene_offset
    if we - ws < MIN_CUE_DURATION_SEC:
        return None
    return (max(parent_start, ws - SUBTITLE_LEAD_IN_SEC), parent_end, segment)


def load_words_json(path: Path) -> Optional[List[dict]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data.get('words') if isinstance(data, dict) else data
    except (json.JSONDecodeError, OSError):
        return None


def align_segments_with_words(
    segments: List[str],
    words: List[dict],
    parent_start: float,
    parent_end: float,
    scene_offset: float = 0.0,
) -> Optional[List[Tuple[float, float, str]]]:
    """
    仅在当前 TTS 句时间窗内的词上对齐；每段显示到下一句第一个词开口前。
    """
    if not segments or not words:
        return None

    local_s = parent_start - scene_offset
    local_e = parent_end - scene_offset
    cue_words = words_for_tts_cue(words, local_s, local_e)
    if not cue_words:
        return None

    timings: List[Tuple[float, float, str]] = []
    wi = 0
    for seg in segments:
        matched = _match_segment_words(cue_words, wi, seg, scene_offset)
        if not matched:
            return None
        wi, ws, we = matched
        timings.append((ws, we, seg))

    if len(timings) != len(segments):
        return None

    out: List[Tuple[float, float, str]] = []
    for i, (ws, we, seg) in enumerate(timings):
        lead = SUBTITLE_LEAD_IN_SEC if i > 0 else 0.0
        s = ws - lead if i > 0 else max(parent_start, ws - lead)
        if SUBTITLE_END_AT_NEXT_SPEECH and i < len(timings) - 1:
            next_ws = timings[i + 1][0]
            e = max(we, next_ws - MIN_GAP_SEC)
        else:
            e = parent_end
        if e <= s:
            e = s + MIN_CUE_DURATION_SEC
        out.append((s, min(e, parent_end), seg))

    # 用词级尾时间+小尾量代替强制延伸到幕末，避免尾句冻结
    last_ws, last_we, _ = timings[-1]
    natural_tail = min(last_we + 0.4, parent_end)
    out[-1] = (out[-1][0], natural_tail, out[-1][2])
    return out


def allocate_timing_within_cue(
    start: float,
    end: float,
    segments: List[str],
    min_duration: float = MIN_CUE_DURATION_SEC,
) -> List[Tuple[float, float, str]]:
    """
    尾锚分配：保证最后一段有足够时长；每段结束不早于下一段开始。
  前段略压缩，避免后段未播完字幕已切走。
    """
    if not segments:
        return []
    if len(segments) == 1:
        return [(start, end, segments[0])]

    n = len(segments)
    total = max(end - start, min_duration * n)
    end = start + total

    last_min = max(min_duration, total * MIN_LAST_SEGMENT_RATIO)
    remain = max(total - last_min, min_duration * (n - 1))

    weights = [max(len(s), 1) ** 0.85 for s in segments[:-1]]
    wsum = sum(weights) or 1.0

    starts = [start]
    for i in range(n - 1):
        dur = max(min_duration, remain * weights[i] / wsum)
        starts.append(min(starts[-1] + dur, end - last_min - min_duration * (n - 2 - i)))

    starts.append(end - last_min)
    if starts[-1] < starts[-2]:
        starts[-1] = starts[-2] + min_duration

    out: List[Tuple[float, float, str]] = []
    for i, seg in enumerate(segments):
        s = starts[i]
        e = end if i == n - 1 else starts[i + 1]
        if e <= s:
            e = s + min_duration
        out.append((s, min(e, end), seg))

    # 按字符比例估算尾段自然时长，避免强制延伸到幕末造成长时间冻结
    last_weight = max(len(segments[-1]), 1) ** 0.85
    wsum_all = (wsum + last_weight) or 1.0
    last_natural_dur = max(min_duration, total * last_weight / wsum_all)
    last_natural_end = min(starts[-1] + last_natural_dur * 1.3, end)
    out[-1] = (out[-1][0], last_natural_end, out[-1][2])
    for i in range(len(out) - 1):
        ps, pe, pt = out[i]
        ns, _, _ = out[i + 1]
        out[i] = (ps, max(pe, ns - MIN_GAP_SEC), pt)
    return out


def extend_cue_ends_to_next(
    cues: List[Tuple[float, float, str]],
) -> List[Tuple[float, float, str]]:
    """每条字幕显示到「下一条开始出现」为止，减少提前消失。"""
    if len(cues) < 2:
        return cues
    out: List[Tuple[float, float, str]] = []
    for i, (s, e, t) in enumerate(cues):
        if i < len(cues) - 1:
            next_start = cues[i + 1][0]
            e = max(e, next_start - MIN_GAP_SEC)
        out.append((s, e, t))
    return out


def fix_passthrough_cues(
    cues: List[Tuple[float, float, str]],
    min_gap: float = MIN_GAP_SEC,
) -> List[Tuple[float, float, str]]:
    """
    透传模式：只消除 cue 间空窗与微重叠，不延长到下一 cue 的 TTS 结束时间之外。
    不调用 extend_cue_ends_to_next，保留 edge-tts 句级 end。
    """
    if not cues:
        return []
    sorted_cues = sorted(cues, key=lambda c: (c[0], c[1]))
    fixed: List[Tuple[float, float, str]] = []
    for start, end, text in sorted_cues:
        if fixed:
            prev_s, prev_e, prev_t = fixed[-1]
            if start < prev_e:
                fixed[-1] = (prev_s, start, prev_t)
            elif start > prev_e + min_gap * 2:
                fixed[-1] = (prev_s, start, prev_t)
            if end <= start:
                end = start + MIN_CUE_DURATION_SEC
        fixed.append((start, end, text))
    return fixed


def fix_cue_overlaps(
    cues: List[Tuple[float, float, str]],
    min_gap: float = MIN_GAP_SEC,
) -> List[Tuple[float, float, str]]:
    """拆行模式：重叠/空窗处理 + 延长显示至下一条开始出现。"""
    if not cues:
        return []
    sorted_cues = sorted(cues, key=lambda c: (c[0], c[1]))
    fixed: List[Tuple[float, float, str]] = []
    for start, end, text in sorted_cues:
        if fixed:
            prev_s, prev_e, prev_t = fixed[-1]
            if start < prev_e:
                # TTS 句间微重叠：上一条显示到本条出现
                fixed[-1] = (prev_s, max(prev_e, start), prev_t)
            elif start > prev_e + min_gap * 2:
                # 空窗：上一条延长到本条开始，避免「字幕没了才开口」
                fixed[-1] = (prev_s, start, prev_t)
            if end <= start:
                end = start + MIN_CUE_DURATION_SEC
        fixed.append((start, end, text))
    return extend_cue_ends_to_next(fixed)


def normalize_tts_cue(
    start: float,
    end: float,
    text: str,
    soft_max: int = SOFT_MAX_CHARS_PER_LINE,
    words: Optional[List[dict]] = None,
    scene_offset: float = 0.0,
) -> List[Tuple[float, float, str]]:
    text = clean_display_text(text)
    if not text:
        return []

    segments = split_for_display(text, soft_max=soft_max)
    text_seg = segments[0] if segments else text

    if len(segments) <= 1:
        if words:
            one = align_single_segment_with_words(
                words, text_seg, start, end, scene_offset,
            )
            if one:
                return [one]
        return [(start, end, text_seg)]

    aligned = None
    if words:
        aligned = align_segments_with_words(
            segments, words, start, end, scene_offset=scene_offset,
        )
    if aligned:
        return aligned

    return allocate_timing_within_cue(start, end, segments)


def parse_srt_blocks(content: str) -> List[Tuple[float, float, str]]:
    cues = []
    for block in content.strip().split('\n\n'):
        block = block.strip()
        if not block:
            continue
        lines = [ln for ln in block.split('\n') if ln.strip()]
        if len(lines) < 2:
            continue
        time_idx = 1 if lines[0].strip().isdigit() else 0
        if time_idx >= len(lines):
            continue
        time_line = lines[time_idx]
        if '-->' not in time_line:
            continue
        start_s, end_s = [p.strip() for p in time_line.split('-->')]
        text = ' '.join(lines[time_idx + 1:]).strip()
        if not text:
            continue
        cues.append((parse_srt_time(start_s), parse_srt_time(end_s), text))
    return cues


def write_srt(
    cues: List[Tuple[float, float, str]],
    path: str,
    merge_mode: str = DEFAULT_MERGE_MODE,
) -> int:
    if merge_mode == MERGE_MODE_PASSTHROUGH:
        cues = fix_passthrough_cues(cues)
    else:
        cues = fix_cue_overlaps(cues)
    with open(path, 'w', encoding='utf-8') as f:
        for i, (start, end, text) in enumerate(cues, 1):
            f.write(f'{i}\n')
            f.write(f'{format_srt_time(start)} --> {format_srt_time(end)}\n')
            f.write(f'{text}\n\n')
    return len(cues)


def write_ass(
    cues: List[Tuple[float, float, str]],
    path: str,
    play_res_x: int,
    play_res_y: int,
    margin_v: int,
    font_size: int,
    font_name: str = 'Microsoft YaHei',
    outline: int = 3,
) -> int:
    cues = fix_cue_overlaps(cues)
    style_line = (
        f'Style: Default,{font_name},{font_size},'
        f'&H00FFFFFF,&H00000000,&H00000000,&H80000000,'
        f'0,0,0,0,100,100,0,0,1,{outline},0,2,10,10,{margin_v},1'
    )
    header = (
        '[Script Info]\n'
        'Title: Tutor\n'
        'ScriptType: v4.00+\n'
        'WrapStyle: 2\n'
        'ScaledBorderAndShadow: yes\n'
        f'PlayResX: {play_res_x}\n'
        f'PlayResY: {play_res_y}\n'
        '\n'
        '[V4+ Styles]\n'
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, '
        'OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, '
        'ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, '
        'Alignment, MarginL, MarginR, MarginV, Encoding\n'
        f'{style_line}\n'
        '\n'
        '[Events]\n'
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    )
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(header)
        for start, end, text in cues:
            # \an2 override 强制底中对齐，防止样式漂移导致位置不稳定
            t = '{\\an2}' + text.replace('\n', '\\N')
            f.write(
                f'Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},'
                f'Default,,0,0,0,,{t}\n'
            )
    return len(cues)


def merge_project_cues_passthrough(
    subtitles_dir,
    audio_files,
) -> List[Tuple[float, float, str]]:
    """透传合并：一条 TTS SentenceBoundary = 一条字幕，仅加幕级时间偏移。

    偏移 = audio_duration + scene_gap（FadeOut 时间）
    这确保下一幕字幕时间轴与视频时间轴一致，消除幕间累积误差。
    """
    subtitles_dir = Path(subtitles_dir)
    raw: List[Tuple[float, float, str]] = []
    offset = 0.0

    for item in sorted(audio_files, key=lambda x: x.get('scene', 0)):
        stem = Path(item['file']).stem
        srt_path = subtitles_dir / f'{stem}.srt'
        if srt_path.exists():
            content = srt_path.read_text(encoding='utf-8')
            for start, end, text in parse_srt_blocks(content):
                text = clean_display_text(text)
                if text:
                    raw.append((start + offset, end + offset, text))
        # 偏移 = 音频时长 + FadeOut 时长，与 Manim 实际幕时长一致
        offset += float(item.get('duration', 0)) + float(item.get('scene_gap', SCENE_GAP_DEFAULT))

    return fix_passthrough_cues(raw)


def merge_project_cues_split(
    subtitles_dir,
    audio_files,
    soft_max: int = SOFT_MAX_CHARS_PER_LINE,
) -> List[Tuple[float, float, str]]:
    """拆行合并：长句按短语拆行 + 词级时间对齐。

    偏移 = audio_duration + scene_gap（FadeOut 时间）
    确保下一幕字幕时间轴与视频时间轴一致，消除幕间累积误差。
    """
    subtitles_dir = Path(subtitles_dir)
    raw: List[Tuple[float, float, str]] = []
    offset = 0.0

    for item in sorted(audio_files, key=lambda x: x.get('scene', 0)):
        stem = Path(item['file']).stem
        srt_path = subtitles_dir / f'{stem}.srt'
        words = load_words_json(subtitles_dir / f'{stem}.words.json')

        if srt_path.exists():
            content = srt_path.read_text(encoding='utf-8')
            scene_off = offset
            for start, end, text in parse_srt_blocks(content):
                for cs, ce, ct in normalize_tts_cue(
                    start + scene_off, end + scene_off, text,
                    soft_max=soft_max, words=words, scene_offset=scene_off,
                ):
                    raw.append((cs, ce, ct))

        # 偏移 = 音频时长 + FadeOut 时长，与 Manim 实际幕时长一致
        offset += float(item.get('duration', 0)) + float(item.get('scene_gap', SCENE_GAP_DEFAULT))

    return fix_cue_overlaps(raw)


def merge_project_cues(
    subtitles_dir,
    audio_files,
    mode: str = DEFAULT_MERGE_MODE,
    soft_max: int = SOFT_MAX_CHARS_PER_LINE,
) -> List[Tuple[float, float, str]]:
    if mode == MERGE_MODE_SPLIT:
        return merge_project_cues_split(subtitles_dir, audio_files, soft_max=soft_max)
    return merge_project_cues_passthrough(subtitles_dir, audio_files)


def split_text_lines(text: str, **kwargs) -> List[str]:
    return split_for_display(text, **kwargs)


def split_cue_timing(start: float, end: float, text: str, **kwargs) -> List[Tuple[float, float, str]]:
    return normalize_tts_cue(start, end, text, **kwargs)
