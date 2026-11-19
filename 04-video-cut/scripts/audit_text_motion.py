"""Read actual native text animation; does not certify design or playback."""
from pathlib import Path

PROPERTIES = {'position_x': 'KFTypePositionX', 'position_y': 'KFTypePositionY',
              'uniform_scale': 'KFTypeScaleX', 'scale_x': 'KFTypeScaleX',
              'scale_y': 'KFTypeScaleY', 'rotation': 'KFTypeRotation'}


def audit_text_motion(plan: dict, base: Path, summary: dict, draft: dict) -> list[str]:
    errors: list[str] = []
    mapping = {row['clip_id']: row['segment_id'] for row in summary.get('segments', [])}
    segments = {s['id']: s for t in draft.get('tracks', []) for s in t.get('segments', [])}
    fonts: dict = {}
    for clip in plan.get('clips', []):
        if clip.get('kind') != 'text':
            continue
        ident = clip['id']
        segment = segments.get(mapping.get(ident), {})
        groups = {g['property_type']: g.get('keyframe_list', []) for g in segment.get('common_keyframes', [])}
        for prop, keys in clip.get('keyframes', {}).items():
            actual = groups.get(PROPERTIES.get(prop), [])
            for time, value in keys:
                if not any(abs(k['time_offset']-round(time*1e6)) <= 2
                           and k.get('values') and abs(k['values'][0]-value) <= 1e-6
                           and k.get('curveType') == 'Line' for k in actual):
                    errors.append(ident + ': native text keyframe missing/changed: ' + prop)
        if not clip.get('keyframes') and groups:
            errors.append(ident + ': unexpected native text motion')
        if not clip.get('font_file'):
            continue
        file = (base / clip['font_file']).resolve()
        try:
            from PIL import ImageFont
            if file not in fonts:
                fonts[file] = ImageFont.truetype(str(file), 48)
            font = fonts[file]
            mask = font.getmask('\uffff')
            tofu = (mask.size, bytes(mask))
            for char in set(clip.get('text', '')):
                if char.isspace():
                    continue
                glyph = font.getmask(char)
                if (glyph.size, bytes(glyph)) == tofu:
                    errors.append(ident + ': font missing glyph ' + char)
        except (OSError, ValueError) as exc:
            errors.append(ident + ': cannot check actual font: ' + str(exc))
    return errors
