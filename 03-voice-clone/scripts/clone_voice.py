#!/usr/bin/env python3
"""
MiniMax 音色复刻工具

用途：
    将 clone_input/<name>/ 目录下的 source.mp3 复刻为 MiniMax voice_id，
    结果写入 clone_input/<name>/voice_id.txt，后续合成直接从该文件读取，
    无需重复复刻。

目录约定：
    clone_input/
    ├── teacher1/
    │   ├── source.mp3      ← 必须：复刻源音频（10s ~ 5min，<20MB）
    │   ├── prompt.mp3      ← 可选：参考音频（<8s，增强音色相似度）
    │   ├── prompt_text.txt ← 可选：prompt.mp3 对应文字（与 prompt.mp3 配合使用）
    │   └── voice_id.txt    ← 自动生成：复刻成功后写入，内容为 voice_id
    └── teacher2/
        ├── source.mp3
        └── voice_id.txt

使用：
    # 复刻 teacher1（首次，或 --force 强制重新复刻）
    python .claude/skills/tutor/scripts/clone_voice.py teacher1

    # 强制重新复刻（会覆盖已有 voice_id.txt）
    python .claude/skills/tutor/scripts/clone_voice.py teacher1 --force

    # 列出所有已知音色
    python .claude/skills/tutor/scripts/clone_voice.py --list

需要环境变量（.env 或系统环境）：
    MINIMAX_API_KEY=...

可选环境变量（也可写在 clone_input/<name>/prompt_text.txt）：
    MINIMAX_CLONE_PREVIEW_TEXT=大兄弟，听您口音不是本地人...
    MINIMAX_CLONE_MODEL=speech-2.8-hd
"""

import io
import json
import os
import sys
from pathlib import Path

# 修复 Windows GBK 终端乱码
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_STAGE_ROOT = Path(__file__).resolve().parent.parent
if str(_STAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_STAGE_ROOT))
from project_paths import PIPELINE_ROOT, clone_input_dir

CLONE_INPUT_DIR = clone_input_dir()
DEFAULT_CLONE_MODEL = "speech-2.8-hd"
DEFAULT_PREVIEW_TEXT = "大家好，欢迎来到本期IT技术教学视频，今天我们一起来学习这个技术主题。"

MINIMAX_UPLOAD_URL = "https://api.minimaxi.com/v1/files/upload"
MINIMAX_CLONE_URL = "https://api.minimaxi.com/v1/voice_clone"


def load_dotenv(dotenv_path=None):
    env_file = Path(dotenv_path) if dotenv_path else PIPELINE_ROOT / ".env"
    if not env_file.is_absolute():
        env_file = PIPELINE_ROOT / env_file
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


def minimax_headers(api_key, json_body=False):
    """构建 MiniMax 请求头；可选 MINIMAX_GROUP_ID（账户中心复制）。"""
    headers = {"Authorization": f"Bearer {api_key}"}
    group_id = os.getenv("MINIMAX_GROUP_ID", "").strip()
    if group_id:
        headers["Group-Id"] = group_id
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def upload_file(api_key, file_path, purpose):
    import requests

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    print(f"  上传 {p.name} ({p.stat().st_size // 1024} KB) ...")
    with open(p, "rb") as f:
        resp = requests.post(
            MINIMAX_UPLOAD_URL,
            headers=minimax_headers(api_key),
            data={"purpose": purpose},
            files={"file": (p.name, f)},
            timeout=180,
        )
    resp.raise_for_status()
    payload = resp.json()
    file_id = (payload.get("file") or {}).get("file_id") or payload.get("file_id")
    if not file_id:
        raise RuntimeError(f"上传失败，返回缺少 file_id: {payload}")
    print(f"  ✓ 上传成功，file_id: {file_id}")
    return file_id


def clone_voice(api_key, voice_dir, force=False):
    """
    执行复刻流程：
    1. 检查是否已有 voice_id.txt（跳过或强制覆盖）
    2. 上传 source.mp3
    3. 可选上传 prompt.mp3
    4. 调用复刻 API
    5. 保存 voice_id.txt
    """
    import requests

    voice_dir = Path(voice_dir)
    voice_name = voice_dir.name
    voice_id_file = voice_dir / "voice_id.txt"
    source_audio = voice_dir / "source.mp3"
    prompt_audio = voice_dir / "prompt.mp3"
    prompt_text_file = voice_dir / "prompt_text.txt"

    # 检查已有 voice_id
    if voice_id_file.exists() and not force:
        existing = voice_id_file.read_text(encoding="utf-8").strip()
        print(f"[{voice_name}] 已有 voice_id: {existing}")
        print(f"  如需重新复刻，请加 --force 参数")
        return existing

    if not source_audio.exists():
        raise FileNotFoundError(
            f"[{voice_name}] 缺少 source.mp3，请放入: {source_audio}"
        )

    print(f"\n[{voice_name}] 开始音色复刻 ...")

    # 生成 voice_id（格式：tutor_{name}_{hex8}，确保唯一且可读）
    import hashlib, time
    uid = hashlib.md5(f"{voice_name}-{time.time()}".encode()).hexdigest()[:8]
    voice_id = f"tutor_{voice_name}_{uid}"
    print(f"  生成 voice_id: {voice_id}")

    # 上传复刻源音频
    clone_file_id = upload_file(api_key, source_audio, "voice_clone")

    # 构建请求体
    clone_model = os.getenv("MINIMAX_CLONE_MODEL", DEFAULT_CLONE_MODEL)
    # 默认跳过试听合成（text+model 会额外扣 T2A 费用）；需试听时设 MINIMAX_CLONE_PREVIEW=1
    include_preview = os.getenv("MINIMAX_CLONE_PREVIEW", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    preview_text = os.getenv("MINIMAX_CLONE_PREVIEW_TEXT", "").strip()

    payload = {
        "file_id": clone_file_id,
        "voice_id": voice_id,
    }
    if include_preview:
        if not preview_text and prompt_text_file.exists():
            preview_text = prompt_text_file.read_text(encoding="utf-8").strip()
        if not preview_text:
            preview_text = DEFAULT_PREVIEW_TEXT
        payload["text"] = preview_text
        payload["model"] = clone_model
        print(f"  含试听合成（model={clone_model}）")
    else:
        print("  仅复刻音色（无试听，省 T2A 费用）")

    # 可选：上传参考音频
    if prompt_audio.exists():
        prompt_text = ""
        if prompt_text_file.exists():
            prompt_text = prompt_text_file.read_text(encoding="utf-8").strip()
        prompt_file_id = upload_file(api_key, prompt_audio, "prompt_audio")
        payload["clone_prompt"] = {
            "prompt_audio": prompt_file_id,
            "prompt_text": prompt_text or preview_text,
        }
        print(f"  使用参考音频增强复刻效果")

    if include_preview:
        print(f"  调用复刻 API（含试听 model={clone_model}）...")
    else:
        print("  调用复刻 API（仅复刻，无试听）...")
    resp = requests.post(
        MINIMAX_CLONE_URL,
        headers=minimax_headers(api_key, json_body=True),
        json=payload,
        timeout=240,
    )
    resp.raise_for_status()
    result = resp.json()

    base = result.get("base_resp") or {}
    code = base.get("status_code")
    if code not in (None, 0, "0"):
        msg = base.get("status_msg", result)
        if str(code) == "1008" or "balance" in str(msg).lower() or "余额" in str(msg):
            raise RuntimeError(
                f"MiniMax 复刻失败 ({code}): {msg}\n"
                "  → 按量计费余额不足（非 Token Plan 积分）。请到：\n"
                "     https://platform.minimaxi.com/user-center/payment/balance 充值\n"
                "  → 或购买「语音资源包」（含快速克隆音色名额）：\n"
                "     https://platform.minimaxi.com/user-center/payment/subscription\n"
                "  → 确认已完成实名认证：\n"
                "     https://platform.minimaxi.com/user-center/basic-information\n"
                "  → 可在控制台手动复刻后，把 voice_id 写入 clone_input/<name>/voice_id.txt"
            )
        raise RuntimeError(f"MiniMax 复刻失败 ({code}): {msg}")

    # 保存 voice_id
    voice_id_file.write_text(voice_id, encoding="utf-8")
    print(f"  ✓ 复刻成功！voice_id: {voice_id}")
    print(f"  ✓ 已保存至: {voice_id_file}")

    return voice_id


def list_voices():
    """列出 clone_input/ 下所有音色及其状态。"""
    if not CLONE_INPUT_DIR.exists():
        print("clone_input/ 目录不存在")
        return

    entries = sorted(
        d for d in CLONE_INPUT_DIR.iterdir() if d.is_dir()
    )
    if not entries:
        print("clone_input/ 下暂无音色子目录")
        return

    print(f"\n{'音色名称':<20} {'状态':<10} {'voice_id'}")
    print("-" * 70)
    for d in entries:
        has_source = (d / "source.mp3").exists()
        vid_file = d / "voice_id.txt"
        has_vid = vid_file.exists()

        status = "✓ 已复刻" if has_vid else ("有源文件" if has_source else "缺 source.mp3")
        vid = vid_file.read_text(encoding="utf-8").strip() if has_vid else "-"
        print(f"{d.name:<20} {status:<10} {vid}")
    print()


def main():
    load_dotenv(".env")

    args = sys.argv[1:]

    if "--list" in args:
        list_voices()
        return

    if not args or args[0].startswith("--"):
        print("Usage:")
        print("  python clone_voice.py <voice_name>          # 复刻（已有 voice_id 则跳过）")
        print("  python clone_voice.py <voice_name> --force  # 强制重新复刻")
        print("  python clone_voice.py --list                 # 列出所有音色状态")
        print()
        print("示例:")
        print("  python .claude/skills/tutor/scripts/clone_voice.py teacher1")
        print("  python .claude/skills/tutor/scripts/clone_voice.py teacher1 --force")
        sys.exit(1)

    voice_name = args[0]
    force = "--force" in args

    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        print("Error: MINIMAX_API_KEY 未配置，请在 .env 中添加")
        sys.exit(1)

    voice_dir = CLONE_INPUT_DIR / voice_name
    if not voice_dir.exists():
        print(f"Error: 目录不存在: {voice_dir}")
        print(f"请创建目录并放入 source.mp3: clone_input/{voice_name}/source.mp3")
        sys.exit(1)

    try:
        voice_id = clone_voice(api_key, voice_dir, force=force)
        print(f"\n可将以下配置加入 .env：")
        print(f"  MINIMAX_ACTIVE_VOICE={voice_name}")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
