"""Mandatory visual-design gate shared by build/render/audit."""
import copy
import hashlib
import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[2] / '01-shot-list/scripts'
sys.path.insert(0, str(SCRIPTS))
from validate_visual_design import validate, digest
from validate_execution import validate as validate_execution
from subtitle_contract import validate_subtitles, audit_native_subtitles
from audit_text_motion import audit_text_motion


def gate(plan, base):
    inputs = plan.get('visual_inputs', {})
    if not inputs.get('presentation_plan') or not inputs.get('asset_manifest'):
        raise ValueError('visual_inputs.presentation_plan/asset_manifest required; migrate legacy plan before build')
    paths = {key: (base / inputs[key]).resolve() for key in ('presentation_plan','asset_manifest')}
    source = json.loads(paths['presentation_plan'].read_text())
    manifest = json.loads(paths['asset_manifest'].read_text())
    for key,path in paths.items():
        if inputs.get(key+'_sha256') != digest(path):
            raise ValueError('visual input missing/stale hash: '+key)
    errors = validate_subtitles(plan,base)
    errors += validate_execution(source, paths['presentation_plan'].parent, '04', manifest, paths['asset_manifest'].parent, plan, base)
    # Validate the complete asset delivery, then only the pilot's active on-screen images.
    errors += validate(source, '02', manifest, paths['asset_manifest'].parent)
    active_source=source
    if plan.get('execution_phase') == 'pilot':
        active_source=copy.deepcopy(source)
        contract=source.get('execution_contract',{})
        active_ids={a['id'] for s in contract.get('scenes',[]) if s.get('id') in contract.get('pilot_scene_ids',[]) for a in s.get('asset_requirements',[])}
        design=active_source.get('visual_design',{})
        design['image_designs']=[x for x in design.get('image_designs',[]) if x.get('id') in active_ids]
        design['composition_groups']=[g for g in design.get('composition_groups',[]) if set(g.get('image_ids',[]))<=active_ids]
    errors += validate(active_source, '04', manifest, paths['asset_manifest'].parent, plan, base)
    if errors:
        raise ValueError('visual design gate failed: '+json.dumps(errors,ensure_ascii=False))
    return source, manifest, paths


def audit_evidence(plan, base, summary, draft, mp4):
    source, manifest, paths = gate(plan,base)
    if plan.get('execution_phase') != 'final':return ['pilot is not a final deliverable']
    reportpath = base / 'visual-execution-report.json'
    if not reportpath.is_file():return ['visual execution report missing']
    report=json.loads(reportpath.read_text());errors=audit_native_subtitles(plan,summary,draft)
    errors += audit_text_motion(plan,base,summary,draft)
    if report.get('plan_sha256') != summary.get('plan_sha256'):
        errors.append('visual report plan hash missing/stale')
    if report.get('mp4_sha256') != digest(mp4):errors.append('visual report MP4 hash missing/stale')
    reviews={x.get('scene_id'):x for x in report.get('scene_reviews',[])}
    for scene in source['execution_contract']['scenes']:
        review=reviews.get(scene['id'],{})
        for field in ('subject_matches','character_consistent','style_scope_correct','content_motion_visible','reading_comfortable','continuous_playback_checked'):
            if review.get(field) is not True:errors.append(scene['id']+': incomplete scene review '+field)
        if not review.get('reviewer') or not review.get('notes'):errors.append(scene['id']+': require reviewer and concrete review notes')
        frames=review.get('evidence_frames',[])
        if len(frames)<3 or not all((base/f).is_file() for f in frames):errors.append(scene['id']+': missing scene entry/stable/exit evidence')
    mapping={x['clip_id']:x for x in summary['segments']}
    segments={s['id']:s for t in draft['tracks'] for s in t.get('segments',[])}
    materials={m['id']:m for m in draft.get('materials',{}).get('videos',[])}
    entries={x['image_design_id']:x for x in report.get('images',[])}
    for item in source['visual_design']['image_designs']:
        if not item.get('required',True):continue
        ident=item['id'];clips=[c for c in plan['clips'] if c.get('image_design_id')==ident]
        entry=entries.get(ident,{})
        if not all(entry.get(k) is True for k in ('readable','subtitle_clear','content_checked','motion_checked')):
            errors.append(ident+': actual frame/motion review incomplete')
        evidence=entry.get('evidence_frames',[])
        if len(evidence)<3 or not all((base/f).is_file() for f in evidence):errors.append(ident+': require actual entry/stable/exit frame evidence')
        for clip in clips:
            row=mapping.get(clip['id'],{});seg=segments.get(row.get('segment_id'),{})
            if row.get('image_design_id')!=ident:errors.append(ident+': summary lost image identity')
            material=materials.get(seg.get('material_id'),{})
            path=Path(material.get('path',''))
            if not path.is_file() or digest(path)!=digest(base/clip['file']):errors.append(ident+': actual draft media differs from image clip')
            if row.get('segment_id') not in entry.get('segment_ids',[]):errors.append(ident+': report missing actual segment ID')
    return errors
