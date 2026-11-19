"""Check actionable scene detail, not just prose intent. No aesthetic certification."""

def validate_scene(scene, narration):
    errors=[];name=str(scene.get('id','?'));length=scene.get('end_s',0)-scene.get('start_s',0)
    def fail(message):errors.append(name+': '+message)
    text=scene.get('narration_excerpt')
    if not text or text not in narration:fail('narration_excerpt missing/not in source narration')
    if scene.get('timing_status') not in ('estimated','audio_aligned'):fail('timing_status must distinguish estimated/audio_aligned')
    objects=scene.get('objects',[]);requirements={a.get('id') for a in scene.get('asset_requirements',[])};ids=set()
    for obj in objects:
        ident=obj.get('id')
        if not ident or ident in ids:fail('missing/duplicate object ID')
        ids.add(ident)
        if obj.get('asset_id') not in requirements:fail('object references undeclared asset')
        for k in ('center','size'):
            v=obj.get(k,[])
            if not isinstance(v,list) or len(v)!=2 or not all(isinstance(n,(int,float)) for n in v):fail('object '+str(ident)+' invalid '+k)
            elif k=='size' and any(n<=0 or n>1 for n in v):fail('object size must be normalized, positive and <=1')
        if not isinstance(obj.get('z'),(int,float)):fail('object z missing')
        if not isinstance(obj.get('text'),str):fail('object exact text missing; use empty string for no text')
        if not obj.get('initial_state') or not obj.get('end_state'):fail('object initial/end state missing')
        if obj.get('exit_policy') not in ('remove','carry','replace'):fail('object exit_policy missing')
        if obj.get('exit_policy')=='carry' and not obj.get('next_scene_id'):fail('carried object needs next_scene_id')
        start=obj.get('visible_start_s',-1);end=obj.get('visible_end_s',-1)
        if not 0<=start<end<=length:fail('object visibility outside scene')
    if not objects or not requirements<={o.get('asset_id') for o in objects}:fail('every required asset needs a concrete object layout')
    actions={a.get('id'):a for a in scene.get('content_actions',[])};covered=set()
    for spec in scene.get('action_specs',[]):
        action=actions.get(spec.get('action_id'));target=next((o for o in objects if o.get('id')==spec.get('object_id')),None)
        if not action or not target:fail('action spec has unknown action/object');continue
        if target.get('asset_id') not in action.get('target_ids',[]):fail('action spec targets wrong asset')
        covered.add((spec['action_id'],target['asset_id']))
        for k in ('property','from','to','easing','expected_result'):
            if k not in spec or spec[k] is None or spec[k]=='':fail('action spec missing '+k)
        start=spec.get('start_s',-1);duration=spec.get('duration_s',0)
        if start<0 or duration<=0 or start+duration>length+.002:fail('action timing outside scene')
        if spec.get('from')==spec.get('to'):fail('content action has no state change')
    for ident,action in actions.items():
        for asset in action.get('target_ids',[]):
            if (ident,asset) not in covered:fail('semantic action lacks concrete parameters: '+str(ident)+'/'+str(asset))
    if not scene.get('acceptance_checks'):fail('scene-specific observable acceptance checks missing')
    return errors
