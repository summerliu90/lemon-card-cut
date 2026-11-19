"""Compare authored numeric actions with executable clip keyframes."""
import math


def validate_actions(scene: dict, clips: list) -> list[str]:
    errors: list[str] = []
    objects = {obj['id']: obj for obj in scene.get('objects', [])}
    for action in scene.get('action_specs', []):
        if (not action.get('property') or not all(isinstance(action.get(key), (int, float))
                and not isinstance(action.get(key), bool) and math.isfinite(action[key])
                for key in ('start_s', 'duration_s', 'from', 'to'))):
            errors.append(str(action.get('action_id')) + ': executable action needs finite numeric parameters')
            continue
        obj = objects.get(action.get('object_id'), {})
        matches = [clip for clip in clips if clip.get('design_asset_id') == obj.get('asset_id')
                   and action.get('action_id') in clip.get('content_action_ids', [])]
        # An explicit object/clip identity resolves repeated uses of the same asset.
        exact = [clip for clip in matches if clip.get('id') == action.get('object_id')]
        matches = exact or matches
        implemented = False
        for clip in matches:
            if not all(key in clip for key in ('start_s', 'end_s')):
                continue
            start = scene['start_s'] + action['start_s'] - clip['start_s']
            end = start + action['duration_s']
            keys = clip.get('keyframes', {}).get(action['property'], [])
            def contains(time: float, value: float) -> bool:
                return any(isinstance(v, (int, float)) and isinstance(value, (int, float))
                           and math.isfinite(v) and math.isfinite(value)
                           and abs(t-time) <= .002 and abs(v-value) <= 1e-6 for t, v in keys)
            if start >= -.002 and end <= clip['end_s']-clip['start_s']+.002:
                implemented = contains(start, action['from']) and contains(end, action['to'])
            if implemented:
                break
        if not implemented:
            errors.append(str(action.get('action_id')) + ': authored action keyframe time/value/property differs from clip')
    return errors
