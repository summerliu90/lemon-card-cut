# -*- coding: utf-8 -*-
"""Validate planned visual assets; does not certify native segments or visual quality."""
import argparse
import json
import hashlib
import math
from select_visual_style import choose, ALGORITHM, CATALOG
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(plan, stage, manifest=None, manifest_root=None, edit=None, edit_root=None):
    errors = []
    design = plan.get('visual_design', {})
    for key in ('selection_mode', 'visual_style_id', 'selection_reason', 'series_parameters', 'image_designs'):
        if key == 'image_designs' and isinstance(design.get(key), list):
            continue
        if not design.get(key):
            errors.append('visual_design missing: ' + key)
    if design.get('selection_mode') not in ('user', 'semantic_random', 'authored_per_asset'):
        errors.append('selection_mode must be user, semantic_random or authored_per_asset')
    if design.get('selection_mode') == 'semantic_random':
        if design.get('seed') is None or not design.get('candidates'):
            errors.append('semantic_random requires saved seed and filtered candidates')
        elif design.get('visual_style_id') not in design['candidates']:
            errors.append('selected style absent from candidates')
    images = design.get('image_designs', [])
    ids = [x.get('id') for x in images]
    if len(set(ids)) != len(ids):
        errors.append('duplicate image design IDs')
    assets = {x.get('id'): x for x in (manifest or {}).get('images', [])}
    for item in images:
        ident = item.get('id', '?')
        for key in ('id', 'shots', 'trigger_text', 'learning_goal', 'diagram_type', 'visual_style_id', 'route', 'aspect_ratio', 'target_px', 'content_basis', 'display', 'motion_intent', 'text_plan'):
            if not item.get(key):
                errors.append(f'{ident}: missing {key}')
        ratio = item.get('aspect_ratio', [])
        target = item.get('target_px', [])
        if not (len(ratio) == len(target) == 2 and all(isinstance(x, (float, int)) and x > 0 for x in ratio + target)):
            errors.append(f'{ident}: invalid ratio/target dimensions')
        elif abs((target[0]/target[1])/(ratio[0]/ratio[1])-1) > .03:
            errors.append(f'{ident}: target dimensions disagree with ratio')
        if stage == '01' or not item.get('required', True):
            continue
        asset = assets.get(ident, {})
        if asset.get('status') != 'ready':
            errors.append(f'{ident}: missing ready asset')
            continue
        file = Path(manifest_root) / asset.get('file', '')
        if not file.is_file():
            errors.append(f'{ident}: missing actual file')
        else:
            try:
                from PIL import Image
                with Image.open(file) as image:
                    width, height = image.size
                    image.verify()
                if (width, height) != (asset.get('width'), asset.get('height')):
                    errors.append(f'{ident}: recorded dimensions disagree with file')
                if len(ratio) == 2 and ratio[1] and abs((width/height)/(ratio[0]/ratio[1])-1) > .04:
                    errors.append(f'{ident}: actual file ratio disagrees with design')
            except Exception as exc:
                errors.append(f'{ident}: cannot verify raster image: {exc}')
        if asset.get('visual_style_id') != item.get('visual_style_id'):
            errors.append(f'{ident}: style differs from design')
        if item.get('route') == 'imagegen' and asset.get('route') != 'imagegen':
            errors.append(f'{ident}: planned image generation replaced without revised design')
        if not all(asset.get('qa', {}).get(k) is True for k in ('viewed', 'text_checked', 'structure_checked')):
            errors.append(f'{ident}: incomplete declared image QA')
        if stage == '04':
            clips = [c for c in (edit or {}).get('clips', []) if c.get('image_design_id') == ident]
            if not clips:
                errors.append(f'{ident}: absent from edit plan')
            for clip in clips:
                if clip.get('kind') not in ('image', 'video') or clip.get('end_s', 0) <= clip.get('start_s', 0):
                    errors.append(f'{ident}: invalid visual clip')
                if not (Path(edit_root) / clip.get('file', '')).is_file():
                    errors.append(f'{ident}: clip file missing')
                if not clip.get('size') or not clip.get('center'):
                    errors.append(f'{ident}: clip display geometry missing')
    errors.extend(validate_extended(plan, stage, manifest, manifest_root, edit, edit_root))
    return errors


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def valid_pair(value):
    return isinstance(value, list) and len(value) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in value)


def at(keys, t, default):
    if not keys:
        return default
    if t <= keys[0][0]:
        return keys[0][1]
    for (a, v), (b, w) in zip(keys, keys[1:]):
        if t <= b:
            return v + (w-v)*(t-a)/max(b-a, 1e-9)
    return keys[-1][1]


def rectangle(clip, image, canvas, local):
    from PIL import Image
    with Image.open(image) as im:
        iw, ih = im.size
    W, H = canvas
    size = clip['size']; center = clip['center']; keys = clip.get('keyframes', {})
    # Geometry of linear keyframes is the same in native and local routes.
    if keys.get('rotation') or keys.get('uniform_scale'):
        raise ValueError('image geometry requires relative_scale; rotation needs a separate verified layout route')
    scale = at(keys.get('relative_scale'), local, 1)
    factor = (max if clip.get('fit') == 'cover' else min)(size[0]*W/iw, size[1]*H/ih)*scale
    cx = (at(keys.get('position_x'), local, 2*center[0]-1)+1)/2
    cy = (1-at(keys.get('position_y'), local, 1-2*center[1]))/2
    w, h = iw*factor/W, ih*factor/H
    return [cx-w/2, cy-h/2, cx+w/2, cy+h/2]


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0])+1e-6 and min(a[3], b[3]) > max(a[1], b[1])+1e-6


def validate_extended(plan, stage, manifest, manifest_root, edit, edit_root):
    errors = []; design = plan.get('visual_design', {})
    images = design.get('image_designs', [])
    if 'image_designs' in plan and plan['image_designs'] != images:
        errors.append('conflicting legacy image_designs; migrate to visual_design.image_designs')
    known = {x['id'] for x in read(CATALOG)['styles']}
    styles = [design.get('visual_style_id')] + [x.get('visual_style_id') for x in images]
    if design.get('selection_mode') == 'authored_per_asset':
        treatments = design.get('authored_treatments', {})
        for ident in styles:
            treatment = treatments.get(ident, {})
            if not all(treatment.get(k) for k in ('medium', 'palette', 'semantic_reason', 'reference_policy')):
                errors.append('authored style requires explicit medium/palette/semantic_reason/reference_policy: '+str(ident))
    elif any(x not in known for x in styles):
        errors.append('unknown visual_style_id')
    candidates = design.get('candidates', [])
    if any(x not in known for x in candidates):
        errors.append('unknown candidate style ID')
    if design.get('selection_mode') == 'semantic_random':
        try:
            if design.get('selection_algorithm') != ALGORITHM or choose(design.get('seed'), candidates) != design.get('visual_style_id'):
                errors.append('style selection cannot be reproduced')
            if not all(design.get('candidate_reasons', {}).get(x) for x in candidates):
                errors.append('filtered candidates require per-style semantic reasons')
        except (ValueError, TypeError):
            errors.append('invalid reproducible style selection')
    assets = {x.get('id'): x for x in (manifest or {}).get('images', [])}
    if len(assets) != len((manifest or {}).get('images', [])):
        errors.append('duplicate manifest image IDs')
    groups = design.get('composition_groups', [])
    byid = {x.get('id'): x for x in images}
    for group in groups:
        if group.get('type') != 'portrait_pair':
            errors.append('unsupported explicit composition group type'); continue
        members = group.get('image_ids', [])
        if len(members) != 2 or len(set(members)) != 2 or not set(members) <= set(byid):
            errors.append('portrait_pair requires two distinct known image IDs'); continue
        for ident in members:
            item = byid[ident]; ratio = item.get('aspect_ratio', [])
            if len(ratio) != 2 or not 0 < ratio[0] < ratio[1]:
                errors.append(ident + ': portrait_pair needs portrait ratio')
        if stage != '01':
            files = [Path(manifest_root) / assets.get(i, {}).get('file', '') for i in members]
            if all(f.is_file() for f in files) and digest(files[0]) == digest(files[1]):
                errors.append('portrait_pair reuses identical file content')
            if any(assets.get(i, {}).get('derived_from') for i in members):
                errors.append('portrait_pair must be independent designs, not cropped derivatives')
    for item in images:
        display = item.get('display', {})
        if not valid_pair(display.get('center')) or not valid_pair(display.get('size')) or min(display.get('size', [0,0])) <= 0:
            errors.append(str(item.get('id')) + ': invalid planned display geometry')
        else:
            ratio=item.get('aspect_ratio',[]);canvas=plan.get('canvas',[1920,1080])
            if len(ratio)==2 and all(isinstance(x,(int,float)) and x>0 for x in ratio):
                W,H=canvas;cx,cy=display['center'];dw,dh=display['size']
                factor=min(dw*W/ratio[0],dh*H/ratio[1]);w=ratio[0]*factor/W;h=ratio[1]*factor/H
                safe=design.get('reading_safe_area',[.03,.12,.97,.85])
                if len(safe)==4 and (cx-w/2<safe[0]-1e-5 or cy-h/2<safe[1]-1e-5 or cx+w/2>safe[2]+1e-5 or cy+h/2>safe[3]+1e-5):
                    errors.append(str(item.get('id'))+': planned image exceeds reading safe area')
        group_id = item.get('composition_group')
        if group_id and not any(g.get('id') == group_id and item['id'] in g.get('image_ids', []) for g in groups):
            errors.append(str(item.get('id')) + ': missing composition group definition')
    if stage != '04':
        return errors
    canvas = edit.get('canvas', [1920,1080]); clip_rects = {}
    safe = design.get('reading_safe_area', [0.03,0.12,0.97,0.85])
    if not (isinstance(safe,list) and len(safe)==4 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in safe) and 0<=safe[0]<safe[2]<=1 and 0<=safe[1]<safe[3]<=1):
        errors.append('invalid reading_safe_area'); return errors
    for clip in edit.get('clips', []):
        ident = clip.get('image_design_id')
        if not ident:
            continue
        if ident not in byid:
            errors.append('clip references unknown image ID'); continue
        actual = Path(edit_root) / clip.get('file', '')
        asset = assets.get(ident, {}); allowed = [asset.get('file')] + asset.get('derived_files', [])
        expected = [Path(manifest_root)/x for x in allowed if x]
        if not actual.is_file() or not any(f.is_file() and digest(f)==digest(actual) for f in expected):
            errors.append(ident + ': clip file differs from registered asset/derivatives'); continue
        if not valid_pair(clip.get('center')) or not valid_pair(clip.get('size')) or min(clip.get('size',[0,0])) <= 0:
            errors.append(ident + ': invalid clip geometry'); continue
        window = clip.get('reading_window_s', [])
        duration = clip.get('end_s',0)-clip.get('start_s',0)
        if not valid_pair(window) or not 0<=window[0]<window[1]<=duration:
            errors.append(ident + ': explicit local reading_window_s required'); continue
        times = {window[0],window[1],(window[0]+window[1])/2}
        for keys in clip.get('keyframes',{}).values():
            times.update(t for t,v in keys if window[0] <= t <= window[1])
        for prop,keys in clip.get('keyframes',{}).items():
            values=[at(keys,t,1 if prop in ('relative_scale','alpha') else 0) for t in sorted(times)]
            if values and max(values)-min(values)>1e-5:
                errors.append(ident+': reading window must be stable; split moving detail into separate clip/window')
            if prop=='alpha' and values and min(values)<.99:
                errors.append(ident+': image hidden during reading window')
        bounds=[]
        try:
            for t in sorted(times):
                rect = rectangle(clip,actual,canvas,t)
                if rect[0]<safe[0]-1e-5 or rect[1]<safe[1]-1e-5 or rect[2]>safe[2]+1e-5 or rect[3]>safe[3]+1e-5:
                    errors.append(ident + ': image exceeds reading safe area')
                bounds.append(rect)
            clip_rects[clip['id']] = (ident,clip,bounds)
        except Exception as exc:
            errors.append(ident + ': geometry check failed: '+str(exc))
    for group in groups:
        if group.get('type') != 'portrait_pair':continue
        ids=group.get('image_ids',[])
        for aid,a,ar in clip_rects.values():
            for bid,b,br in clip_rects.values():
                if len(ids)!=2 or aid!=ids[0] or bid!=ids[1]:continue
                aw=a['reading_window_s'];bw=b['reading_window_s']
                lo=max(a['start_s']+aw[0],b['start_s']+bw[0]);hi=min(a['start_s']+aw[1],b['start_s']+bw[1])
                if lo>=hi:continue
                # Conservative swept bounds in stable window; intentional overlap needs redesign.
                union=lambda rs:[min(x[0] for x in rs),min(x[1] for x in rs),max(x[2] for x in rs),max(x[3] for x in rs)]
                if overlaps(union(ar),union(br)):errors.append('portrait_pair overlaps during reading')
    return errors



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['01', '02', '04'], required=True)
    parser.add_argument('--plan', required=True, help='01-presentation-plan.json')
    parser.add_argument('--manifest', help='02 asset-manifest.json; required for 02/04')
    parser.add_argument('--edit-plan', help='04 edit-plan.json; required for 04')
    args = parser.parse_args()
    if args.stage != '01' and not args.manifest:
        parser.error('--manifest required for 02/04')
    if args.stage == '04' and not args.edit_plan:
        parser.error('--edit-plan required for 04')
    errors = validate(read(args.plan), args.stage,
                      read(args.manifest) if args.manifest else None,
                      Path(args.manifest).resolve().parent if args.manifest else None,
                      read(args.edit_plan) if args.edit_plan else None,
                      Path(args.edit_plan).resolve().parent if args.edit_plan else None)
    print(json.dumps({'stage': args.stage, 'passed': not errors, 'errors': errors,
                      'scope': 'Design/files/edit plan only; native segments and actual rendered readability require review.'}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == '__main__':
    main()
