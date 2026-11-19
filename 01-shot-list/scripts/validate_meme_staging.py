"""Check final pixel meme staging and required identity; visual occlusion still needs review."""
import math

def pair(v):return isinstance(v,list) and len(v)==2 and all(isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n) for n in v)

def validate(source,edit=None):
    policy=source.get('meme_policy',{});slots=source.get('meme_slots',[]);errors=[]
    if not policy.get('enabled'):
        return ['meme slots present while meme policy disabled'] if slots else []
    if not isinstance(slots,list) or not slots:return ['enabled meme policy requires explicit meme_slots; character motion/shortfall text cannot substitute']
    canvas=source.get('canvas',[1920,1080]);W,H=canvas
    scenes={s['id']:s for s in source.get('execution_contract',{}).get('scenes',[])}
    ids=[s.get('id') for s in slots]
    if len(set(ids))!=len(ids):errors.append('duplicate meme slot IDs')
    required=[s for s in slots if s.get('required',True)]
    if len(required)<policy.get('required_count',0):errors.append('agreed required meme count reduced')
    phase=(edit or {}).get('execution_phase');active=source.get('execution_contract',{}).get('pilot_scene_ids',[]) if phase=='pilot' else list(scenes)
    offset=min((scenes[s]['start_s'] for s in active if s in scenes),default=0) if phase=='pilot' else 0
    for slot in slots:
        ident=str(slot.get('id','?'));scene=scenes.get(slot.get('scene_id'),{})
        for key in ('id','scene_id','trigger_text','intent','placement','size_px','center','hold_s','context_handling'):
            if not slot.get(key):errors.append(ident+': missing '+key)
        if slot.get('trigger_text') not in source.get('narration_text',''):errors.append(ident+': trigger absent from narration')
        size=slot.get('size_px');center=slot.get('center')
        geometry_ok=pair(size) and pair(center) and min(size)>0
        if not geometry_ok:errors.append(ident+': invalid final pixel size/center')
        else:
            normalized=[size[0]/W,size[1]/H]
            if max(normalized)>=1:errors.append(ident+': full-screen meme forbidden')
            if any(c-v/2<0 or c+v/2>1 for c,v in zip(center,normalized)):errors.append(ident+': steady meme outside canvas')
            if min(size)<min(512,.8*min(W,H)) and not slot.get('size_reason'):errors.append(ident+': smaller meme requires concrete size_reason')
        start,end=slot.get('start_s',-1),slot.get('end_s',-1);hold=slot.get('hold_s',0)
        if not (isinstance(hold,(int,float)) and 0<hold<=end-start+.002):errors.append(ident+': invalid stable hold duration')
        if not scene or not scene.get('start_s',0)<=start<end<=scene.get('end_s',0)+.002:errors.append(ident+': timing outside scene')
        if slot.get('required',True) and ident not in {a.get('id') for a in scene.get('asset_requirements',[])}:errors.append(ident+': missing required scene asset')
        if edit is None or slot.get('scene_id') not in active:continue
        matches=[c for c in edit.get('clips',[]) if c.get('design_asset_id')==slot.get('id') and c.get('meme_id')]
        if len(matches)!=1:errors.append(ident+': expected one actual meme clip');continue
        clip=matches[0]
        if geometry_ok and (not pair(clip.get('size')) or any(abs(a-b)>1 for a,b in zip([clip.get('size',[0,0])[0]*W,clip.get('size',[0,0])[1]*H],size))):errors.append(ident+': actual containment box differs from final pixels')
        if clip.get('center')!=center:errors.append(ident+': position changed after storyboard')
        if abs(clip.get('start_s',-1)-(start-offset))>.002 or abs(clip.get('end_s',-1)-(end-offset))>.002:errors.append(ident+': actual time differs from storyboard')
        if clip.get('display_scale_applied',1)!=1:errors.append(ident+': final dimensions were multiplied again')
    return errors
