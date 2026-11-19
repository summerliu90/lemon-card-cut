"""Fail closed on missing scene/assets/character/pilot handoffs. Not aesthetic certification."""
import argparse
import hashlib
import json
from pathlib import Path
from validate_scene_detail import validate_scene
from validate_action_execution import validate_actions
from validate_meme_staging import validate as validate_meme_staging


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(source, base, stage='01', manifest=None, manifest_root=None, edit=None, edit_root=None):
    errors=validate_meme_staging(source,edit if stage=='04' else None)
    c=source.get('execution_contract', {})
    if c.get('version') != 1:
        return ['execution_contract v1 missing; migrate legacy design, do not fabricate acceptance']
    for key in ('main_video_language','insert_style_scope','background_policy','character','scenes','pilot_scene_ids'):
        if not c.get(key):errors.append('execution_contract missing '+key)
    if c.get('insert_style_scope') != 'selected_assets_only':errors.append('insert styles must be scoped to selected_assets_only')
    if c.get('background_policy') != 'solid_or_changing_scene_no_static_scene_wallpaper':errors.append('static scene wallpaper prohibited')
    scenes=c.get('scenes',[]);ids=set();requirements={};cursor=0
    for s in scenes:
        ident=s.get('id');start=s.get('start_s',-1);end=s.get('end_s',-1)
        if not ident or ident in ids:errors.append('missing/duplicate scene ID')
        ids.add(ident)
        if abs(start-cursor)>.002 or end<=start:errors.append(str(ident)+': invalid scene timeline')
        cursor=end
        errors += validate_scene(s, source.get('narration_text',''))
        for k in ('learning_goal','subject','composition','continuity','reading_window_s','asset_requirements','content_actions'):
            if not s.get(k):errors.append(str(ident)+': missing '+k)
        window=s.get('reading_window_s',[])
        if len(window)!=2 or not 0<=window[0]<window[1]<=end-start:errors.append(str(ident)+': invalid stable reading window')
        for a in s.get('asset_requirements',[]):
            if not all(a.get(k) for k in ('id','type','brief')):errors.append(str(ident)+': incomplete required asset')
            if a.get('id') in requirements and requirements[a['id']]['type']!=a.get('type'):errors.append('asset identity changed type')
            requirements[a.get('id')]=a
    if abs(cursor-source.get('duration_s',-1))>.002:errors.append('scenes do not cover duration_s')
    for scene in scenes:
        for obj in scene.get('objects',[]):
            if obj.get('exit_policy') == 'carry' and (obj.get('next_scene_id') not in ids or obj.get('next_scene_id') == scene.get('id')):
                errors.append(str(scene.get('id'))+': invalid carry destination')
    pilots=c.get('pilot_scene_ids',[])
    if not pilots or not set(pilots)<=ids:errors.append('pilot scene IDs invalid')
    character=c.get('character',{})
    if character.get('mode') not in ('none','xiaohei','lemoner'):errors.append('character mode missing/invalid')
    if character.get('mode')!='none':
        ref=Path(base)/character.get('reference_file','__missing__')
        if not ref.is_file() or sha(ref)!=character.get('reference_sha256'):errors.append('character reference missing/stale; no improvised replacement')
    if stage=='01':return errors
    assets={a.get('design_id'):a for a in (manifest or {}).get('execution_assets',[])}
    for ident,req in requirements.items():
        a=assets.get(ident,{})
        if a.get('type')!=req.get('type'):errors.append(str(ident)+': required asset missing/type downgraded')
        if req.get('type') not in ('native_text','native_shape','native_line'):
            f=Path(manifest_root or base)/a.get('file','__missing__')
            if not f.is_file() or sha(f)!=a.get('sha256'):errors.append(str(ident)+': actual asset missing/stale')
        if req.get('type')=='character' and (a.get('identity_reference_sha256')!=character.get('reference_sha256') or not a.get('identity_review_notes')):errors.append(str(ident)+': character identity review missing')
    if stage=='02':return errors
    edit=edit or {};root=Path(edit_root or base);phase=edit.get('execution_phase')
    if phase not in ('pilot','final'):errors.append('execution_phase must be pilot or final')
    active=[s for s in scenes if phase!='pilot' or s['id'] in pilots]
    if phase=='pilot' and abs(edit.get('duration_s',-1)-sum(s['end_s']-s['start_s'] for s in active))>.002:errors.append('pilot must cover precisely the selected scenes')
    clips=edit.get('clips',[])
    for s in active:
        mapped=[x for x in clips if x.get('scene_id')==s['id']]
        errors += validate_actions(s, mapped)
        for req in s.get('asset_requirements',[]):
            matches=[x for x in mapped if x.get('design_asset_id')==req['id']]
            if not matches:errors.append(req['id']+': promised asset absent from scene')
            for clip in matches:
                a=assets.get(req['id'],{})
                if a.get('file'):
                    f=root/clip.get('file','__missing__')
                    if not f.is_file() or sha(f)!=a.get('sha256'):errors.append(req['id']+': clip differs from approved asset')
        for action in s.get('content_actions',[]):
            if not action.get('id') or not action.get('description') or not action.get('target_ids'):errors.append(s['id']+': incomplete semantic action');continue
            actionclips=[x for x in mapped if action['id'] in x.get('content_action_ids',[])]
            if not set(action['target_ids'])<={x.get('design_asset_id') for x in actionclips}:errors.append(action['id']+': content action target not implemented')
    if phase=='final':
        reportfile=root/edit.get('pilot_review_file','__missing__')
        try:
            report=json.loads(reportfile.read_text())
            if report.get('source_sha256')!=hashlib.sha256(json.dumps(source,ensure_ascii=False,sort_keys=True).encode()).hexdigest():errors.append('pilot source hash stale')
            if report.get('scene_ids')!=pilots or not report.get('reviewer') or not report.get('notes') or report.get('accepted') is not True:errors.append('pilot actual review incomplete')
            for k in ('video','render_summary'):
                f=root/report.get(k,'__missing__')
                if not f.is_file() or sha(f)!=report.get(k+'_sha256'):errors.append('pilot '+k+' evidence missing/stale')
        except (OSError,ValueError):errors.append('accepted pilot review missing')
    return errors


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--stage',choices=['01','02'],default='01');p.add_argument('--manifest',type=Path);a=p.parse_args()
    m=json.loads(a.manifest.read_text()) if a.manifest else None
    errors=validate(json.loads(a.plan.read_text()),a.plan.parent,a.stage,m,a.manifest.parent if a.manifest else None)
    print(json.dumps({'valid':not errors,'errors':errors,'aesthetic_quality_verified':False},ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
if __name__=='__main__':main()
