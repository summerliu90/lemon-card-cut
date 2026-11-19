"""Synthetic evidence for wiring tests only; never a real design acceptance."""
import hashlib

def add_contract(source,manifest,edit,base):
    duration=edit['duration_s'];req=[];assets=[]
    for clip in edit['clips']:
        if not clip.get('image_design_id'):continue
        ident=clip['image_design_id'];clip.update(scene_id='S01',design_asset_id=ident,content_action_ids=['A01'])
        req.append(dict(id=ident,type='illustration',brief='test fixture'))
        f=base/clip['file'];assets.append(dict(design_id=ident,type='illustration',file=clip['file'],sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    source['duration_s']=duration
    source['execution_contract']=dict(version=1,main_video_language='synthetic wiring test',insert_style_scope='selected_assets_only',background_policy='solid_or_changing_scene_no_static_scene_wallpaper',character={'mode':'none'},pilot_scene_ids=['S01'],scenes=[dict(id='S01',start_s=0,end_s=duration,learning_goal='fixture',subject='fixture',composition='fixture',continuity='fixture',reading_window_s=[duration*.2,duration*.8],asset_requirements=req,content_actions=[dict(id='A01',target_ids=[a['id'] for a in req],description='fixture mapping only')])])
    manifest['execution_assets']=assets;edit['execution_phase']='pilot'

    source['narration_text']='synthetic fixture narration'
    scene=source['execution_contract']['scenes'][0]
    scene.update(narration_excerpt='synthetic fixture narration',timing_status='estimated',acceptance_checks=['Synthetic parameter mapping only'])
    scene['objects']=[dict(id=a['id'],asset_id=a['id'],center=[.5,.5],size=[.5,.5],z=1,text='',initial_state='hidden',end_state='visible',exit_policy='remove',visible_start_s=0,visible_end_s=duration) for a in req]
    scene['action_specs']=[dict(action_id='A01',object_id=a['id'],start_s=0,duration_s=duration*.05,property='alpha',**{'from':0,'to':1},easing='linear',expected_result='Test state change only') for a in req]
    for clip in edit['clips']:
        if clip.get('image_design_id'):
            clip.setdefault('start_s', 0)
            clip.setdefault('end_s', duration)
            clip.setdefault('keyframes', {})['alpha'] = [[0, 0], [duration*.05, 1]]
