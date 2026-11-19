#!/usr/bin/env python3
"""Validate visual beats and immutable motion references; does not prove visual quality."""
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from validate_execution import validate as validate_execution


def validate(plan: dict[str, Any], base: Path) -> list[str]:
    errors: list[str] = []
    beats = plan.get('visual_beats', [])
    if not beats:
        return ['visual_beats缺失，需要迁移旧计划']
    cursor = 0.0
    previous = None
    identifiers: set[str] = set()
    snapshot = None
    for beat in beats:
        name = beat.get('id', '?')
        if name in identifiers:
            errors.append(f'{name}:重复编号')
        identifiers.add(name)
        start, end = beat.get('start_s', -1), beat.get('end_s', -1)
        if abs(start - cursor) > .002 or end - start <= 0:
            errors.append(f'{name}:时间不连续或时长非正数')
        cursor = end
        for field in ('composition_id', 'focus_id', 'change_reason', 'trigger_text', 'selection_reason', 'layout', 'motion_events', 'asset_requirements', 'implementation_route', 'validation_status'):
            if not beat.get(field):
                errors.append(f'{name}:缺少{field}')
        identity = (beat.get('composition_id'), beat.get('focus_id'))
        if identity == previous:
            errors.append(f'{name}:重复构图与焦点，文字变化/重新入场不计换镜')
        previous = identity
        if beat.get('trigger_text') and beat['trigger_text'] not in plan.get('narration_text', ''):
            errors.append(f'{name}:trigger_text不在原文')
        route = beat.get('implementation_route')
        if route not in ('keyframes', 'jianying_native'):
            errors.append(f'{name}:未知实现路径')
        ref = beat.get('motion_ref')
        if ref:
            try:
                if snapshot is None:
                    snapshot = json.loads((base / plan.get('motion_snapshot', 'motion-library-snapshot.json')).read_text())
                choices = snapshot.get('selected', snapshot.get('candidates', []))
                matching = [item for item in choices if item.get('motion_id', item.get('id')) == ref.get('id') and all(item.get(k) == ref.get(k) for k in ('version', 'recipe_sha256'))]
                if not matching:
                    raise ValueError('引用不在固定快照')
                recipe = Path(matching[0]['recipe_file'])
                if ref.get('recipe_file') and Path(ref['recipe_file']).resolve() != recipe.resolve():
                    raise ValueError('配方路径偏离固定快照')
                if not recipe.is_absolute():
                    recipe = base / recipe
                if hashlib.sha256(recipe.read_bytes()).hexdigest() != ref['recipe_sha256']:
                    raise ValueError('配方哈希不匹配')
            except (OSError, ValueError, KeyError) as exc:
                errors.append(f'{name}:动效引用失败 {exc}')
        elif beat.get('origin') != 'original':
            errors.append(f'{name}:无引用必须声明origin=original')
        status = beat.get('validation_status')
        if status not in ('unverified', 'render_verified', 'native_verified'):
            errors.append(f'{name}:未知验证状态')
        if status in ('render_verified', 'native_verified') and not (base / beat.get('evidence', '__missing__')).is_file():
            errors.append(f'{name}:验证证据文件缺失')
        for event in beat.get('motion_events', []):
            if not all(k in event for k in ('layer_id', 'phase', 'start_s', 'duration_s', 'property', 'from', 'to')):
                errors.append(f'{name}:动效事件不完整')
            elif event['duration_s'] <= 0 or event['start_s'] < 0 or event['start_s'] + event['duration_s'] > end - start + .002:
                errors.append(f'{name}:动效事件时间越界')
    if abs(cursor - plan.get('duration_s', -1)) > .002:
        errors.append('视觉节拍未覆盖完整时长')
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    errors = validate(plan, args.plan.resolve().parent) + validate_execution(plan, args.plan.resolve().parent)
    print(json.dumps({'valid': not errors, 'errors': errors, 'visual_quality_verified': False}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
