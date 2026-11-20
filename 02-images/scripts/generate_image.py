#!/usr/bin/env python3
"""按 .env 里的图片通道顺序生图。

每次都从第 1 条通道开始。只有当前通道无法出图或超时，才尝试下一条。成功即停。
不把密钥写入日志。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]


def skill_root(override: Path | None = None) -> Path:
    return Path(override or os.environ.get("LEMON_CARD_CUT_ROOT") or SKILL_ROOT).resolve()


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("export "):
            if line.startswith("export "):
                line = line[7:].strip()
            else:
                continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_channels(env: dict[str, str]) -> list[dict[str, str]]:
    count = int(env.get("OPENAI_IMAGE_CHANNEL_COUNT", "0") or "0")
    channels = []
    for index in range(1, count + 1):
        key = env.get(f"OPENAI_IMAGE_CHANNEL_{index}_API_KEY", "").strip()
        base = env.get(f"OPENAI_IMAGE_CHANNEL_{index}_BASE_URL", "").strip().rstrip("/")
        model = env.get(f"OPENAI_IMAGE_CHANNEL_{index}_IMAGE_MODEL", "").strip()
        if key and base and model:
            channels.append({"index": index, "api_key": key, "base_url": base, "model": model})
    if not channels:
        raise RuntimeError("没有可用图片通道。请在 .env 配置 OPENAI_IMAGE_CHANNEL_N 的密钥、地址和模型")
    return channels


def public_channel(channel: dict[str, str]) -> dict[str, object]:
    return {
        "index": channel["index"],
        "base_url": channel["base_url"],
        "model": channel["model"],
    }


def request_image(channel: dict[str, str], prompt: str, size: str, background: str, quality: str, resolution: str, timeout: float) -> bytes:
    payload = {
        "prompt": prompt,
        "model": channel["model"],
        "size": size,
        "quality": quality,
        "resolution": resolution,
        "background": background,
        "output_format": "png",
    }
    url = channel["base_url"] + "/images/generations"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + channel["api_key"], "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except TimeoutError:
        raise RuntimeError("timeout") from None
    except urllib.error.HTTPError as error:
        error.read()
        raise RuntimeError(f"http_{error.code}") from None
    except urllib.error.URLError as error:
        reason = "timeout" if isinstance(error.reason, TimeoutError) else "network_" + error.reason.__class__.__name__
        raise RuntimeError(reason) from None
    first = (body.get("data") or [None])[0] or {}
    if first.get("b64_json"):
        import base64
        return base64.b64decode(first["b64_json"])
    if first.get("url"):
        try:
            with urllib.request.urlopen(first["url"], timeout=60) as downloaded:
                content_type = downloaded.headers.get("Content-Type", "")
                data = downloaded.read()
        except TimeoutError:
            raise RuntimeError("timeout") from None
        except urllib.error.URLError as error:
            reason = "timeout" if isinstance(error.reason, TimeoutError) else "download_failed"
            raise RuntimeError(reason) from None
        if not content_type.startswith("image/"):
            raise RuntimeError("download_not_image")
        return data
    raise RuntimeError("missing_image_bytes")


def generate(prompt_file: Path, image: Path, root: Path | None = None, size: str = "1024x1536", background: str = "opaque") -> dict:
    root = skill_root(root)
    prompt_file = prompt_file.resolve()
    image = image.resolve()
    if not prompt_file.is_file():
        raise FileNotFoundError("图片提示词文件不存在")
    if image.exists():
        raise FileExistsError("不覆盖已有图片，请使用新版本路径")
    env = parse_env((root / ".env").read_text(encoding="utf-8"))
    channels = load_channels(env)
    timeout_ms = int(env.get("OPENAI_IMAGE_TIMEOUT_MS", "180000") or "180000")
    timeout = max(30, min(timeout_ms / 1000, 900))
    quality = env.get("OPENAI_IMAGE_QUALITY", "low").strip() or "low"
    resolution = env.get("OPENAI_IMAGE_RESOLUTION", "1k").strip() or "1k"
    prompt = prompt_file.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("提示词为空")
    attempts = []
    log = image.with_suffix(".attempts.json")
    image.parent.mkdir(parents=True, exist_ok=True)
    for channel in channels:
        attempt = {**public_channel(channel), "status": "started"}
        attempts.append(attempt)
        log.write_text(json.dumps({"order": "1-2-3", "attempts": attempts}, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            data = request_image(channel, prompt, size, background, quality, resolution, timeout)
        except RuntimeError as error:
            attempt["status"] = "failed"
            attempt["category"] = str(error)
            log.write_text(json.dumps({"order": "1-2-3", "attempts": attempts}, ensure_ascii=False, indent=2), encoding="utf-8")
            continue
        if not data:
            attempt["status"] = "failed"
            attempt["category"] = "empty_image"
            continue
        image.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        attempt["status"] = "succeeded"
        receipt = {
            "image": str(image),
            "image_sha256": digest,
            "prompt_file": str(prompt_file),
            "selected_channel": public_channel(channel),
            "order": "1-2-3",
            "attempts": attempts,
            "quality": quality,
            "resolution": resolution,
            "size": size,
        }
        image.with_suffix(".receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        log.write_text(json.dumps({"order": "1-2-3", "attempts": attempts}, ensure_ascii=False, indent=2), encoding="utf-8")
        return receipt
    raise RuntimeError("第 1 到第 3 条通道都未能出图，已停止。详见同名 .attempts.json，其中没有密钥")


def main() -> None:
    parser = argparse.ArgumentParser(description="从第 1 条图片通道开始生图，失败或超时才试后面的通道")
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--config-root", type=Path)
    parser.add_argument("--size", default="1024x1536")
    parser.add_argument("--background", default="opaque", choices=["transparent", "opaque", "auto"])
    args = parser.parse_args()
    print(json.dumps(generate(args.prompt_file, args.image, args.config_root, args.size, args.background), ensure_ascii=False))


if __name__ == "__main__":
    main()
