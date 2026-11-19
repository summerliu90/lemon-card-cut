#!/usr/bin/env python3
"""
TTS 生成脚本（可配置 Provider）

当前支持：
- edge-tts（默认，兼容现有流程）
- minimax（音色复刻 + 同步语音合成）

MiniMax 音色管理流程（推荐）：
    1. 将复刻源音频放入 clone_input/<name>/source.mp3
    2. 首次复刻（生成并保存 voice_id）：
         python .claude/skills/tutor/scripts/clone_voice.py <name>
    3. .env 配置当前使用哪位老师：
         MINIMAX_ACTIVE_VOICE=<name>
    4. 正常运行 generate_tts.py，voice_id 自动从 voice_id.txt 读取

.env 最小配置：
    TUTOR_TTS_PROVIDER=minimax
    MINIMAX_API_KEY=...
    MINIMAX_ACTIVE_VOICE=teacher1
"""

import asyncio
import csv
import io
import json
import os
import re
import ssl
import struct
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


# 修复 Windows GBK 终端下中文/emoji 输出问题
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def fix_streaming_wav_header(path: str) -> None:
    """修复 MiniMax（及其他流式 TTS）写出的 WAV 文件头部。

    问题：MiniMax 以 WebSocket 流式传输时，WAV 头部的 RIFF/data chunk size
    字段为 0xFFFFFFFF（流式标记，表示"长度未知"）。wave/mutagen 读取后返回
    约 67108.86s 的错误时长，导致 SRT 字幕时间轴完全错误。

    修复逻辑：
    1. 定位 'data' chunk（在二进制中搜索 b'data'）
    2. 用文件实际大小计算真实 data size
    3. 回写 RIFF chunk size（offset 4）、LIST chunk size（若存在）、data chunk size
    """
    try:
        fsize = os.path.getsize(path)
        with open(path, "rb") as f:
            header = f.read(200)  # WAV 头部不超过 200 字节

        data_pos = header.find(b"data")
        if data_pos == -1:
            return  # 非标准 WAV，跳过

        audio_data_start = data_pos + 8  # 'data'(4) + size(4)
        # MiniMax may append a valid AIGC provenance chunk after PCM data while
        # keeping the streaming data size as 0xFFFFFFFF. Treating the whole
        # file tail as PCM turns the JSON provenance bytes into loud clicks.
        # Stop the data chunk at the AIGC chunk boundary when present.
        with open(path, "rb") as f:
            payload = f.read()
        aigc_pos = payload.find(b"AIGC", audio_data_start)
        actual_data_size = (
            aigc_pos - audio_data_start if aigc_pos != -1 else fsize - audio_data_start
        )
        if actual_data_size <= 0:
            return

        with open(path, "r+b") as f:
            # 修复 RIFF chunk size（offset 4，= 文件总大小 - 8）
            f.seek(4)
            f.write(struct.pack("<I", fsize - 8))
            # 修复 LIST chunk size（若存在，且在 data chunk 之前）
            list_pos = header.find(b"LIST")
            if list_pos != -1 and list_pos < data_pos:
                list_size = data_pos - (list_pos + 8)
                f.seek(list_pos + 4)
                f.write(struct.pack("<I", list_size))
            # 修复 data chunk size（offset = data_pos + 4）
            f.seek(data_pos + 4)
            f.write(struct.pack("<I", actual_data_size))
    except Exception as e:
        print(f"  Warning: fix_streaming_wav_header failed for {path}: {e}")


# 每幕 FadeOut 固定时长（秒）——以 subtitle_utils.SCENE_GAP_DEFAULT 为唯一权威源，
# script.py 端的 SCENE_GAP 常量与之保持一致（避免字幕从第二幕起累积漂移）
try:
    _SCRIPTS_DIR = Path(__file__).resolve().parent
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    from subtitle_utils import SCENE_GAP_DEFAULT as SCENE_GAP  # noqa: E402
except Exception:
    SCENE_GAP = 0.5

SUPPORTED_PROVIDERS = {"edge-tts", "minimax"}
DEFAULT_PROVIDER = "edge-tts"

# Edge 声音映射表
VOICE_MAP = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunyang": "zh-CN-YunyangNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "xiaoxiao-dialect": "zh-CN-XiaoxiaoNeural",
    "xiaoxiao-multilingual": "zh-CN-XiaoxiaoMultilingualNeural",
}


def parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def find_project_root() -> Path:
    """流水线根（含 .env）。clone_input 在 04-voiceover/。"""
    _stage = Path(__file__).resolve().parent.parent
    if str(_stage) not in sys.path:
        sys.path.insert(0, str(_stage))
    try:
        from project_paths import find_pipeline_root
        return find_pipeline_root()
    except ImportError:
        pass
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "01-article").is_dir() and (p / "04-voiceover").is_dir():
            return p
    return Path.cwd()


def load_dotenv_if_present(dotenv_path=None):
    """
    轻量 .env 读取：仅填充当前未设置的环境变量。
    默认从项目根目录加载，避免在 output/{时间戳}/ 子目录运行时读不到配置。
    不依赖 python-dotenv，避免新增运行时依赖。
    """
    root = find_project_root()
    env_file = Path(dotenv_path) if dotenv_path else root / ".env"
    if not env_file.is_absolute():
        env_file = root / env_file
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def find_ffmpeg():
    """查找 ffmpeg：先 PATH，再项目 tools/bin"""
    import shutil

    if shutil.which("ffmpeg"):
        return "ffmpeg"

    candidates = [
        Path(__file__).parent.parent.parent.parent / "tools" / "bin" / "ffmpeg.exe",
        Path(__file__).parent.parent.parent.parent / "tools" / "bin" / "ffmpeg",
        Path.cwd() / "tools" / "bin" / "ffmpeg.exe",
        Path.cwd() / "tools" / "bin" / "ffmpeg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "ffmpeg"


def convert_to_pcm_wav(file_path):
    """edge-tts 默认输出 MP3 数据，转成 PCM WAV 供后续工具稳定读取。"""
    import shutil
    import subprocess
    import tempfile

    ffmpeg = find_ffmpeg()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", file_path, "-acodec", "pcm_s16le", tmp.name],
            check=True,
        )
        shutil.move(tmp.name, file_path)
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


def _format_srt_time(seconds):
    if seconds < 0:
        seconds = 0
    ms = int(round((seconds % 1) * 1000))
    total = int(seconds)
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def write_single_line_srt(srt_path, text, duration):
    """为不提供 sentence boundary 的 TTS 兜底生成单句 SRT。"""
    os.makedirs(os.path.dirname(srt_path), exist_ok=True)
    end = max(float(duration or 0), 0.5)
    with open(srt_path, "w", encoding="utf-8") as sf:
        sf.write("1\n")
        sf.write(f"00:00:00,000 --> {_format_srt_time(end)}\n")
        sf.write(f"{text.strip()}\n\n")


def _find_clone_input_dir():
    _stage = Path(__file__).resolve().parent.parent
    if str(_stage) not in sys.path:
        sys.path.insert(0, str(_stage))
    try:
        from project_paths import clone_input_dir
        return clone_input_dir()
    except ImportError:
        return Path(__file__).resolve().parent.parent / "clone_input"


def _voice_catalog_match(name):
    if not name:
        return None
    catalog_path = Path(__file__).resolve().parents[1] / "references" / "voice_catalog.json"
    if not catalog_path.exists():
        return None
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    needle = str(name).strip().lower()
    for item in catalog.get("voices", []):
        candidates = [item.get("label"), item.get("id"), item.get("voice_id")]
        candidates.extend(item.get("aliases") or [])
        if needle in {str(value or "").strip().lower() for value in candidates}:
            return item
    return None


def resolve_minimax_voice_id(requested_voice=None):
    """
    按优先级解析 MiniMax voice_id：

    1. MINIMAX_ACTIVE_VOICE=<name>
       → 读取 clone_input/<name>/voice_id.txt 中保存的 voice_id
    2. MINIMAX_VOICE_ID=<id>（直接指定，跳过文件读取）
    3. 两者都没有 → 返回空字符串，由 ensure_minimax_voice 负责报错
    """
    active_voice = str(requested_voice or os.getenv("MINIMAX_ACTIVE_VOICE", "")).strip()
    if active_voice:
        catalog_item = _voice_catalog_match(active_voice)
        if catalog_item and catalog_item.get("voice_id"):
            return catalog_item["voice_id"]
        clone_dir = _find_clone_input_dir() / active_voice
        vid_file = clone_dir / "voice_id.txt"
        if vid_file.exists():
            vid = vid_file.read_text(encoding="utf-8").strip()
            if vid:
                return vid
        # voice_id.txt 不存在，说明还没复刻
        return ""

    return os.getenv("MINIMAX_VOICE_ID", "").strip()


def build_minimax_config(cli_voice=None):
    active_voice = str(cli_voice or os.getenv("MINIMAX_ACTIVE_VOICE", "")).strip()
    voice_id = resolve_minimax_voice_id(cli_voice)

    return {
        "api_key": os.getenv("MINIMAX_API_KEY", "").strip(),
        "voice_id": voice_id,
        "active_voice": active_voice,
        "tts_model": os.getenv("MINIMAX_TTS_MODEL", "speech-2.8-hd").strip(),
        "sample_rate": int(os.getenv("MINIMAX_TTS_SAMPLE_RATE", "32000")),
        "bitrate": int(os.getenv("MINIMAX_TTS_BITRATE", "128000")),
        "channel": int(os.getenv("MINIMAX_TTS_CHANNEL", "1")),
        "speed": float(os.getenv("MINIMAX_TTS_SPEED", "1")),
        "vol": float(os.getenv("MINIMAX_TTS_VOL", "1")),
        "pitch": int(float(os.getenv("MINIMAX_TTS_PITCH", "0"))),
        "default_format": os.getenv("MINIMAX_TTS_FORMAT", "wav").strip().lower() or "wav",
    }


def ensure_minimax_voice(minimax_cfg, _preview_text=None):
    """
    校验 voice_id 是否已就绪。
    复刻操作由独立脚本 clone_voice.py 完成，此处只做校验和友好提示。
    """
    if not minimax_cfg.get("api_key"):
        raise RuntimeError("MINIMAX_API_KEY 未配置，请在 .env 中添加")

    if minimax_cfg.get("voice_id"):
        active = minimax_cfg.get("active_voice")
        label = f"（来自 clone_input/{active}/voice_id.txt）" if active else ""
        print(f"使用 MiniMax voice_id: {minimax_cfg['voice_id']} {label}")
        return

    # voice_id 为空，给出明确指引
    active = minimax_cfg.get("active_voice")
    if active:
        raise RuntimeError(
            f"clone_input/{active}/voice_id.txt 不存在或为空，请先复刻：\n"
            f"  python .claude/skills/tutor/scripts/clone_voice.py {active}"
        )
    raise RuntimeError(
        "MiniMax voice_id 未配置，请：\n"
        "  方式①（推荐）：配置 MINIMAX_ACTIVE_VOICE=<name>，并运行 clone_voice.py <name> 复刻\n"
        "  方式②：直接配置 MINIMAX_VOICE_ID=<已有音色id>"
    )


async def collect_word_boundaries(text, voice_id):
    """备用：独立请求收集词级时间戳（仅 edge 流中未收到 WordBoundary 时使用）。"""
    words = []
    try:
        import edge_tts
    except ImportError:
        return words

    try:
        communicate = edge_tts.Communicate(text, voice_id)
        async for chunk in communicate.stream():
            if chunk["type"] == "WordBoundary":
                words.append(
                    {
                        "offset": chunk["offset"],
                        "duration": chunk["duration"],
                        "text": chunk["text"],
                    }
                )
    except Exception:
        pass
    return words


async def generate_audio_edge(text, output_path, voice="xiaoxiao", srt_path=None, words_path=None):
    try:
        import edge_tts
        from edge_tts.submaker import SubMaker
    except ImportError:
        raise RuntimeError("edge-tts 未安装，请运行: uv pip install edge-tts")

    voice_id = VOICE_MAP.get(voice, VOICE_MAP["xiaoxiao"])
    communicate = edge_tts.Communicate(text, voice_id)
    submaker = SubMaker()
    words_in_stream = []

    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                submaker.feed(chunk)
            elif chunk["type"] == "WordBoundary" and words_path:
                words_in_stream.append(
                    {
                        "offset": chunk["offset"],
                        "duration": chunk["duration"],
                        "text": chunk["text"],
                    }
                )

    convert_to_pcm_wav(output_path)

    if srt_path:
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)
        with open(srt_path, "w", encoding="utf-8") as sf:
            sf.write(submaker.get_srt())

    if words_path:
        words = words_in_stream if words_in_stream else await collect_word_boundaries(text, voice_id)
        os.makedirs(os.path.dirname(words_path), exist_ok=True)
        with open(words_path, "w", encoding="utf-8") as wf:
            json.dump({"words": words}, wf, ensure_ascii=False)

    duration = await get_audio_duration(output_path)
    return True, duration


def _minimax_raise_on_error(message: dict) -> None:
    """解析 MiniMax WebSocket 错误响应。"""
    if not isinstance(message, dict):
        return
    base = message.get("base_resp") or {}
    code = base.get("status_code")
    if code not in (None, 0, "0"):
        raise RuntimeError(f"MiniMax API 错误 ({code}): {base.get('status_msg', message)}")
    if message.get("event") in {"task_failed", "error"}:
        raise RuntimeError(f"MiniMax 合成失败: {message}")


def _minimax_request_headers(api_key: str, json_body: bool = False) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"}
    group_id = os.getenv("MINIMAX_GROUP_ID", "").strip()
    if group_id:
        headers["Group-Id"] = group_id
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _minimax_http_urls() -> list[str]:
    base = os.getenv("MINIMAX_TTS_BASE_URL", "").strip().rstrip("/")
    if base:
        return [f"{base}/v1/t2a_v2"]
    return [
        "https://api.minimaxi.com/v1/t2a_v2",
        "https://api.minimax.io/v1/t2a_v2",
    ]


def _minimax_ws_urls() -> list[str]:
    base = os.getenv("MINIMAX_TTS_BASE_URL", "").strip().rstrip("/")
    if base:
        host = base.replace("https://", "wss://").replace("http://", "ws://")
        return [f"{host}/ws/v1/t2a_v2"]
    return [
        "wss://api.minimaxi.com/ws/v1/t2a_v2",
        "wss://api.minimax.io/ws/v1/t2a_v2",
    ]


def _minimax_transport_plan() -> list[tuple[str, str]]:
    mode = os.getenv("MINIMAX_TTS_TRANSPORT", "auto").strip().lower() or "auto"
    plan: list[tuple[str, str]] = []
    if mode in {"auto", "http"}:
        for url in _minimax_http_urls():
            plan.append(("http", url))
    if mode in {"auto", "ws", "websocket"}:
        for url in _minimax_ws_urls():
            plan.append(("ws", url))
    if not plan:
        raise RuntimeError(f"无效的 MINIMAX_TTS_TRANSPORT: {mode}")
    return plan


def _minimax_open_timeout() -> float:
    try:
        return float(os.getenv("MINIMAX_TTS_OPEN_TIMEOUT", "15"))
    except ValueError:
        return 45.0


def _minimax_http_timeout() -> tuple[float, float]:
    try:
        connect = float(os.getenv("MINIMAX_TTS_HTTP_CONNECT_TIMEOUT", "8"))
    except ValueError:
        connect = 15.0
    try:
        read = float(os.getenv("MINIMAX_TTS_HTTP_READ_TIMEOUT", "180"))
    except ValueError:
        read = 180.0
    return connect, read


async def _minimax_after_save(output_path, text, srt_path=None, words_path=None):
    fix_streaming_wav_header(output_path)
    duration = await get_audio_duration(output_path)
    if srt_path:
        write_single_line_srt(srt_path, text, duration)
    if words_path:
        os.makedirs(os.path.dirname(words_path), exist_ok=True)
        with open(words_path, "w", encoding="utf-8") as wf:
            json.dump({"words": []}, wf, ensure_ascii=False)
    return duration


async def generate_audio_minimax_http_once(text, output_path, minimax_cfg, http_url, srt_path=None, words_path=None):
    import requests

    output_ext = Path(output_path).suffix.lower().replace(".", "")
    audio_format = output_ext if output_ext in {"wav", "mp3"} else minimax_cfg["default_format"]
    connect_timeout, read_timeout = _minimax_http_timeout()
    payload = {
        "model": minimax_cfg["tts_model"],
        "text": text,
        "stream": False,
        "output_format": "hex",
        "voice_setting": {
            "voice_id": minimax_cfg["voice_id"],
            "speed": minimax_cfg["speed"],
            "vol": minimax_cfg["vol"],
            "pitch": minimax_cfg["pitch"],
            "english_normalization": False,
        },
        "audio_setting": {
            "sample_rate": minimax_cfg["sample_rate"],
            "bitrate": minimax_cfg["bitrate"],
            "format": audio_format,
            "channel": minimax_cfg["channel"],
        },
    }
    resp = requests.post(
        http_url,
        headers=_minimax_request_headers(minimax_cfg["api_key"], json_body=True),
        json=payload,
        timeout=(connect_timeout, read_timeout),
    )
    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"MiniMax HTTP 响应解析失败 ({http_url}): {resp.status_code} {resp.text[:200]}") from exc

    _minimax_raise_on_error(data)
    audio_hex = ((data.get("data") or {}).get("audio")) if isinstance(data, dict) else None
    if not audio_hex:
        raise RuntimeError(f"MiniMax HTTP 未返回音频 ({http_url})")

    with open(output_path, "wb") as f:
        f.write(bytes.fromhex(audio_hex))

    duration = await _minimax_after_save(output_path, text, srt_path=srt_path, words_path=words_path)
    return True, duration


async def generate_audio_minimax_ws_once(text, output_path, minimax_cfg, ws_url, srt_path=None, words_path=None):
    import websockets

    output_ext = Path(output_path).suffix.lower().replace(".", "")
    audio_format = output_ext if output_ext in {"wav", "mp3"} else minimax_cfg["default_format"]

    headers = {"Authorization": f"Bearer {minimax_cfg['api_key']}"}
    ssl_context = ssl.create_default_context()
    ws = await websockets.connect(
        ws_url,
        additional_headers=headers,
        ssl=ssl_context,
        max_size=32 * 1024 * 1024,
        ping_interval=20,
        ping_timeout=20,
        open_timeout=_minimax_open_timeout(),
        close_timeout=10,
    )

    try:
        connected = json.loads(await ws.recv())
        _minimax_raise_on_error(connected)
        if connected.get("event") != "connected_success":
            raise RuntimeError(f"MiniMax 连接失败: {connected}")

        await ws.send(
            json.dumps(
                {
                    "event": "task_start",
                    "model": minimax_cfg["tts_model"],
                    "voice_setting": {
                        "voice_id": minimax_cfg["voice_id"],
                        "speed": minimax_cfg["speed"],
                        "vol": minimax_cfg["vol"],
                        "pitch": minimax_cfg["pitch"],
                        "english_normalization": False,
                    },
                    "audio_setting": {
                        "sample_rate": minimax_cfg["sample_rate"],
                        "bitrate": minimax_cfg["bitrate"],
                        "format": audio_format,
                        "channel": minimax_cfg["channel"],
                    },
                }
            )
        )
        started = json.loads(await ws.recv())
        _minimax_raise_on_error(started)
        if started.get("event") != "task_started":
            raise RuntimeError(f"MiniMax task_start 失败: {started}")

        await ws.send(json.dumps({"event": "task_continue", "text": text}))

        audio_data = bytearray()
        while True:
            raw = await ws.recv()
            message = json.loads(raw)
            _minimax_raise_on_error(message)
            audio_hex = ((message.get("data") or {}).get("audio")) if isinstance(message, dict) else None
            if audio_hex:
                audio_data.extend(bytes.fromhex(audio_hex))
            if message.get("is_final"):
                break

        if not audio_data:
            raise RuntimeError("MiniMax 未返回音频数据")

        with open(output_path, "wb") as f:
            f.write(audio_data)

        fix_streaming_wav_header(output_path)
        duration = await get_audio_duration(output_path)

        if srt_path:
            write_single_line_srt(srt_path, text, duration)
        if words_path:
            os.makedirs(os.path.dirname(words_path), exist_ok=True)
            with open(words_path, "w", encoding="utf-8") as wf:
                json.dump({"words": []}, wf, ensure_ascii=False)

        return True, duration
    finally:
        try:
            await ws.send(json.dumps({"event": "task_finish"}))
            try:
                await asyncio.wait_for(ws.recv(), timeout=5)
            except (asyncio.TimeoutError, Exception):
                pass
        except Exception:
            pass
        await ws.close()


def _minimax_error_retryable(exc: Exception) -> bool:
    """余额不足等不可恢复错误不重试。"""
    msg = str(exc).lower()
    non_retry_markers = (
        "1008",
        "insufficient balance",
        "余额不足",
        "invalid api key",
        "unauthorized",
    )
    return not any(m in msg for m in non_retry_markers)


async def generate_audio_minimax(text, output_path, minimax_cfg, srt_path=None, words_path=None):
    """MiniMax 合成：HTTP / WebSocket 多端点 + 指数退避重试。"""
    max_retries = int(os.getenv("MINIMAX_TTS_MAX_RETRIES", "2"))
    base_delay = float(os.getenv("MINIMAX_TTS_RETRY_DELAY", "1"))
    transport_plan = _minimax_transport_plan()
    last_err = None

    for attempt in range(1, max_retries + 1):
        errors = []
        for transport, url in transport_plan:
            try:
                if transport == "http":
                    return await generate_audio_minimax_http_once(
                        text, output_path, minimax_cfg, url, srt_path=srt_path, words_path=words_path
                    )
                return await generate_audio_minimax_ws_once(
                    text, output_path, minimax_cfg, url, srt_path=srt_path, words_path=words_path
                )
            except Exception as e:
                last_err = e
                errors.append(f"{transport}@{url}: {e}")
                if not _minimax_error_retryable(e):
                    print(f"    ✗ MiniMax 不可恢复错误（请检查账户/API Key）: {e}")
                    return False, 0

        if attempt < max_retries:
            wait = base_delay * attempt
            brief = errors[0] if errors else str(last_err)
            print(f"    ⚠ MiniMax 第 {attempt} 次失败，{wait:.1f}s 后重试: {brief}")
            await asyncio.sleep(wait)
        else:
            print(f"    ✗ MiniMax 已重试 {max_retries} 次仍失败: {last_err}")

    return False, 0


def _minimax_fallback_edge_enabled() -> bool:
    return os.getenv("MINIMAX_TTS_FALLBACK_EDGE", "1").strip().lower() in {"1", "true", "yes", "on"}


async def generate_audio(text, output_path, provider, voice="xiaoxiao", minimax_cfg=None, srt_path=None, words_path=None):
    try:
        if provider == "edge-tts":
            return await generate_audio_edge(text, output_path, voice, srt_path=srt_path, words_path=words_path)
        if provider == "minimax":
            ok, duration = await generate_audio_minimax(
                text, output_path, minimax_cfg, srt_path=srt_path, words_path=words_path
            )
            if ok:
                return ok, duration
            if _minimax_fallback_edge_enabled():
                fallback_voice = os.getenv("TUTOR_TTS_VOICE", voice or "xiaoxiao")
                print(
                    f"    ↪ MiniMax 不可用，回退 edge-tts（{fallback_voice}）。"
                    " 可设 MINIMAX_TTS_FALLBACK_EDGE=0 关闭，或在页面选择 Edge 音色。"
                )
                return await generate_audio_edge(
                    text, output_path, fallback_voice, srt_path=srt_path, words_path=words_path
                )
            return False, 0
        raise RuntimeError(f"不支持的 TTS provider: {provider}")
    except Exception as e:
        print(f"  Error generating {output_path}: {e}")
        return False, 0


async def get_audio_duration(audio_path):
    """获取音频时长（优先 mutagen，其次 wave）。"""
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(audio_path)
        if audio and getattr(audio, "info", None) and getattr(audio.info, "length", None):
            return float(audio.info.length)
    except Exception:
        pass

    try:
        import wave

        with wave.open(audio_path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        pass

    return 0


def parse_csv(csv_path):
    """
    解析 CSV 文件

    支持格式：
    - 标准 CSV: filename,text
    - 带 BOM 的 UTF-8
    - 不同分隔符（优先逗号，支持分号）
    """
    entries = []

    # 尝试不同编码
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']

    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                # 尝试检测分隔符
                sample = f.read(2048)
                f.seek(0)

                delimiter = ','
                if ';' in sample and sample.count(';') > sample.count(','):
                    delimiter = ';'

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # 支持不同的列名
                    filename = row.get('filename') or row.get('文件名') or row.get('file')
                    text = row.get('text') or row.get('对白') or row.get('content') or row.get('读白')

                    if filename and text:
                        entries.append({
                            'filename': filename,
                            'text': text.strip()
                        })

            print(f"✓ 解析 CSV 成功 ({encoding}), 共 {len(entries)} 条")
            return entries

        except Exception as e:
            continue

    # 如果都失败，尝试简单解析
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:]:  # 跳过标题行
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    entries.append({
                        'filename': parts[0].strip(),
                        'text': parts[1].strip().strip('"')
                    })
        if entries:
            print(f"✓ 简单解析 CSV 成功, 共 {len(entries)} 条")
            return entries
    except:
        pass

    print("Error: 无法解析 CSV 文件")
    return []


def parse_storyboard_md(md_path):
    """
    从分镜脚本 markdown 的「音频生成清单」表格中提取音频列表

    支持表格格式：
    | 幕号 | 文件名 | 读白文本 | 时长 | 说话人 | 情感 |
    | 1 | audio_001_xxx.wav | 读白文本 | | xiaoxiao | 热情 |

    用逐列解析代替正则，避免特殊字符误匹配。
    """
    entries = []
    for enc in ('utf-8', 'utf-8-sig', 'gbk'):
        try:
            with open(md_path, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        print("Error: 无法读取分镜脚本文件")
        return []

    in_table = False
    header_passed = False

    for line in lines:
        line = line.strip()

        # 定位「音频生成清单」区域
        if '音频生成清单' in line:
            in_table = True
            header_passed = False
            continue

        if not in_table:
            continue

        if not line.startswith('|'):
            # 离开表格区域（非空行才算真正结束）
            if entries or line:
                break
            continue

        # 按 | 拆分列，去掉首尾空列
        cols = [c.strip() for c in line.split('|')]
        cols = [c for c in cols if c != '']

        # 分隔行（---）
        if all(set(c) <= set('-: ') for c in cols):
            header_passed = True
            continue

        # 表头行（未到分隔行之前）
        if not header_passed:
            continue

        # 数据行：至少需要 [幕号, 文件名, 读白文本] 三列
        if len(cols) < 3:
            continue

        scene_str = cols[0]
        filename = cols[1]
        text = cols[2]

        if scene_str.isdigit() and filename.endswith('.wav') and len(text) > 5:
            entries.append({'filename': filename, 'text': text})

    if entries:
        print(f"✓ 解析分镜脚本成功, 共 {len(entries)} 条")
    else:
        print("Warning: 分镜脚本中未找到音频清单表格，请确认表格格式")
    return entries


def merge_scene_srts(audio_info_path, subtitles_dir, output_srt_path):
    """
    将各幕 SRT 按 audio_info.json 中的幕顺序与累计时长偏移，合并为整片 subtitles.srt
    """
    if not os.path.exists(audio_info_path):
        print(f"Warning: 未找到 {audio_info_path}，跳过字幕合并")
        return False

    with open(audio_info_path, 'r', encoding='utf-8') as f:
        info = json.load(f)

    files = sorted(info.get('files', []), key=lambda x: x.get('scene', 0))
    if not files:
        return False

    # 延迟导入，避免循环依赖
    script_dir = Path(__file__).parent
    merge_script = script_dir / 'merge_subtitles.py'
    if merge_script.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location('merge_subtitles', merge_script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ok = mod.merge_project_subtitles(subtitles_dir, files, output_srt_path)
        if ok:
            print(f"已合并字幕: {output_srt_path}")
        return ok

    return _merge_scene_srts_inline(files, subtitles_dir, output_srt_path)


def _parse_srt_time(t):
    """00:00:10,420 -> seconds"""
    t = t.strip()
    hh, mm, rest = t.split(':')
    ss, ms = rest.split(',')
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def _merge_scene_srts_inline(files, subtitles_dir, output_srt_path):
    """内联合并 SRT"""
    cues = []
    offset = 0.0
    idx = 1

    for item in files:
        wav_name = item['file']
        srt_name = Path(wav_name).stem + '.srt'
        srt_path = os.path.join(subtitles_dir, srt_name)
        if not os.path.exists(srt_path):
            offset += float(item.get('duration', 0))
            continue

        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        for block in content.split('\n\n'):
            block = block.strip()
            if not block:
                continue
            lines = block.split('\n')
            if len(lines) < 2:
                continue
            time_line = lines[1] if '-->' in lines[1] else lines[0]
            text_lines = lines[2:] if '-->' in lines[1] else lines[1:]
            if '-->' not in time_line and len(lines) >= 2:
                time_line = lines[1]
                text_lines = lines[2:]

            start_s, end_s = [p.strip() for p in time_line.split('-->')]
            start = _parse_srt_time(start_s) + offset
            end = _parse_srt_time(end_s) + offset
            text = '\n'.join(text_lines).strip()
            if not text:
                continue
            cues.append((idx, start, end, text))
            idx += 1

        offset += float(item.get('duration', 0))

    os.makedirs(os.path.dirname(output_srt_path) or '.', exist_ok=True)
    with open(output_srt_path, 'w', encoding='utf-8') as out:
        for i, start, end, text in cues:
            out.write(f'{i}\n')
            out.write(f'{_format_srt_time(start)} --> {_format_srt_time(end)}\n')
            out.write(f'{text}\n\n')

    print(f"已合并字幕: {output_srt_path} ({len(cues)} 条)")
    return len(cues) > 0


async def generate_all(
    input_path,
    output_dir,
    voice="xiaoxiao",
    include_words=True,
    provider=DEFAULT_PROVIDER,
    minimax_cfg=None,
):
    """批量生成音频；默认输出句级 SRT + 词级 words.json（若 provider 支持）。"""
    # 根据文件类型选择解析方式
    if input_path.endswith('.md'):
        entries = parse_storyboard_md(input_path)
    else:
        entries = parse_csv(input_path)

    if not entries:
        return False

    # provider 级准备（MiniMax 复刻 / voice_id 校验）
    if provider == "minimax":
        preview_text = entries[0].get("text", "") if entries else ""
        ensure_minimax_voice(minimax_cfg, preview_text)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    subtitles_dir = os.path.join(output_dir, 'subtitles')
    os.makedirs(subtitles_dir, exist_ok=True)

    # 生成音频
    results = []
    total = len(entries)

    scene_delay = 0.0
    if provider == "minimax":
        scene_delay = float(os.getenv("MINIMAX_TTS_SCENE_DELAY", "1.5"))
        print(f"MiniMax 幕间间隔: {scene_delay}s（可用 MINIMAX_TTS_SCENE_DELAY 调整）")

    if provider == "minimax":
        voice_label = os.getenv("MINIMAX_ACTIVE_VOICE", "").strip() or "(MiniMax voice_id 见上方日志)"
        print(f"\n开始生成音频 (provider: {provider}, MiniMax 音色: {voice_label})...")
    else:
        print(f"\n开始生成音频 (provider: {provider}, edge-tts 声音: {voice})...")
    print("="*50)

    for i, entry in enumerate(entries, 1):
        if provider == "minimax" and i > 1 and scene_delay > 0:
            await asyncio.sleep(scene_delay)
        filename = entry['filename']
        text = entry['text']

        # 确保文件扩展名正确
        if not filename.endswith(('.wav', '.mp3')):
            filename += '.wav'

        output_path = os.path.join(output_dir, filename)
        stem = Path(filename).stem
        srt_path = os.path.join(subtitles_dir, stem + '.srt')
        words_path = (
            os.path.join(subtitles_dir, stem + '.words.json') if include_words else None
        )

        print(f"[{i}/{total}] {filename}")
        print(f"    文本: {text[:50]}{'...' if len(text) > 50 else ''}")

        success, duration = await generate_audio(
            text=text,
            output_path=output_path,
            provider=provider,
            voice=voice,
            minimax_cfg=minimax_cfg,
            srt_path=srt_path,
            words_path=words_path,
        )

        if success:
            # 从文件名提取幕号
            scene_num = extract_scene_number(filename)
            results.append({
                'scene': scene_num,
                'file': filename,
                'text': text,
                'duration': round(duration, 2),
                'scene_gap': SCENE_GAP,  # FadeOut 时间，字幕合并时加入偏移
            })
            print(f"    ✓ 时长: {duration:.2f}s")
        else:
            print(f"    ✗ 失败")

        print()

    # 生成 audio_info.json
    if results:
        info = {
            'files': results,
            'total_duration': sum(r['duration'] for r in results),
            'count': len(results),
            'voice': minimax_cfg.get('voice_id') if provider == "minimax" else voice,
            'provider': provider,
        }

        info_path = os.path.join(output_dir, 'audio_info.json')
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        print(f"已生成: {info_path}")

        # 合并为项目根目录 subtitles.srt
        project_dir = Path(output_dir).parent
        if Path(output_dir).name == 'audio':
            merged_srt = project_dir / 'subtitles.srt'
        else:
            merged_srt = Path(output_dir) / 'subtitles.srt'
        merge_scene_srts(info_path, subtitles_dir, str(merged_srt))

    return len(results) == len(entries)


def extract_scene_number(filename):
    """从文件名提取幕号"""
    # 支持格式: audio_001_xxx.wav, scene_01_xxx.wav, 001_xxx.wav
    import re
    match = re.search(r'\d+', filename)
    if match:
        return int(match.group())
    return 0


def run_voiceover_gate(storyboard_path: str) -> bool:
    """步骤 3.5：口播门禁。仅 .md 分镜脚本时执行。"""
    if not storyboard_path.endswith(".md"):
        return True
    gate = Path(__file__).parent / "check_voiceover.py"
    if not gate.exists():
        print("[!] check_voiceover.py 不存在，跳过门禁")
        return True
    print("口播门禁 (check_voiceover.py)...")
    print("=" * 50)
    result = subprocess.run(
        [sys.executable, str(gate), storyboard_path],
        cwd=Path.cwd(),
    )
    print("")
    return result.returncode == 0


def main():
    load_dotenv_if_present()

    if len(sys.argv) < 2:
        print("Usage: python generate_tts.py <input> [output_dir] [options]")
        print("")
        print("参数:")
        print("  input         分镜脚本 (.md) 或 CSV 文件路径")
        print("  output_dir    输出目录 (默认: ./audio)")
        print("")
        print("选项:")
        print("  --voice VOICE   声音选择 (默认: xiaoxiao)")
        print(f"  --provider P    TTS 提供商: {', '.join(sorted(SUPPORTED_PROVIDERS))}")
        print("  --no-words     不生成 *.words.json（仅适合 merge --passthrough）")
        print("  --skip-voiceover-check  跳过口播门禁（不推荐，须用户明确要求）")
        print("")
        print("Edge 可用声音:")
        for k, v in VOICE_MAP.items():
            print(f"  {k:20s} - {v}")
        print("")
        print("示例:")
        print("  python generate_tts.py output/20260518_112500/分镜.md output/20260518_112500/audio")
        print("  python generate_tts.py audio_list.csv ./audio --voice yunyang --provider edge-tts")
        print("  python generate_tts.py audio_list.csv ./audio --provider minimax")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else "./audio"

    # 解析选项
    voice = os.getenv("TUTOR_TTS_VOICE", "xiaoxiao")
    provider = os.getenv("TUTOR_TTS_PROVIDER", DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER
    include_words = '--no-words' not in sys.argv
    skip_voiceover_check = '--skip-voiceover-check' in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == '--voice' and i + 1 < len(sys.argv):
            voice = sys.argv[i + 1]
        if arg == '--provider' and i + 1 < len(sys.argv):
            provider = sys.argv[i + 1].strip().lower()

    if provider == "qwen-tts":
        print("Error: qwen-tts provider 还未实现，请先使用 edge-tts 或 minimax")
        sys.exit(1)

    if provider not in SUPPORTED_PROVIDERS:
        print(f"Error: 不支持的 provider: {provider}")
        print(f"支持的 provider: {', '.join(sorted(SUPPORTED_PROVIDERS))}")
        sys.exit(1)

    env_provider = os.getenv("TUTOR_TTS_PROVIDER", DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER
    cli_provider_override = "--provider" in sys.argv
    if cli_provider_override and provider != env_provider:
        print(
            f"⚠️  命令行 --provider {provider} 覆盖了 .env 的 TUTOR_TTS_PROVIDER={env_provider}。"
            f"若未获用户明确要求，请去掉 --provider，使用 .env 配置。"
        )

    minimax_cfg = build_minimax_config(
        cli_voice=voice if "--voice" in sys.argv else None
    ) if provider == "minimax" else None

    # 检查文件
    if not os.path.exists(input_path):
        print(f"Error: 文件不存在: {input_path}")
        sys.exit(1)

    file_type = "分镜脚本" if input_path.endswith('.md') else "CSV 文件"
    print(f"{file_type}: {input_path}")
    print(f"输出目录: {output_dir}")
    print(f"TTS Provider: {provider}")
    if provider == "minimax":
        active = os.getenv("MINIMAX_ACTIVE_VOICE", "").strip()
        if active:
            print(f"MiniMax 音色: {active}（来自 MINIMAX_ACTIVE_VOICE）")
        print(f"MiniMax voice_id: {minimax_cfg.get('voice_id') or '(将按配置自动生成/复刻)'}")
        print("（TUTOR_TTS_VOICE 仅在 provider=edge-tts 时生效，本次忽略）")
    else:
        print(f"使用声音: {voice}")
    if include_words:
        print("词级边界: 开启（默认，供拆行同步）")
    else:
        print("词级边界: 关闭 (--no-words)")
    print("")

    if not skip_voiceover_check and input_path.endswith(".md"):
        if not run_voiceover_gate(input_path):
            print("Error: 口播门禁未通过。请按 references/script-style.md 重写 voiceover_script.md / 分镜读白。")
            print("       详见 references/voiceover-workflow.md")
            print("       若确须跳过: generate_tts.py ... --skip-voiceover-check")
            sys.exit(1)
    elif skip_voiceover_check:
        print("[!] 已跳过口播门禁 (--skip-voiceover-check)")
        print("")

    # 运行
    success = asyncio.run(
        generate_all(
            input_path=input_path,
            output_dir=output_dir,
            voice=voice,
            include_words=include_words,
            provider=provider,
            minimax_cfg=minimax_cfg,
        )
    )

    if success:
        print("\n✅ 全部生成成功！")
        sys.exit(0)
    else:
        print("\n⚠️ 部分生成失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
