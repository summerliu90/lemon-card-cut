import sys,tempfile,copy,json,subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(r/'01-shot-list/scripts'),str(r/'04-video-cut/scripts')]
from PIL import Image
from execution_fixture import add_contract
from select_visual_style import choose,ALGORITHM
from validate_visual_design import validate,digest
from visual_gate import gate,audit_evidence
from frame_contract import frame_count,decoded_frames,verify_backgrounds
from apply_presentation import prepare_background
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for name,color in [('a','red'),('b','blue')]:Image.new('RGB',(300,400),color).save(root/(name+'.png'))
 candidates=['ivory-diagram','blue-red-notebook'];style=choose(5,candidates)
 items=[dict(id='I'+str(i),shots=['S01'],trigger_text='用例',learning_goal='组成'+str(i),diagram_type='anatomy',visual_style_id=style,route='imagegen',aspect_ratio=[3,4],target_px=[1200,1600],content_basis='示意',display={'center':[cx,.49],'size':[.29,.69]},motion_intent='进入',text_plan='分层',composition_group='pair') for i,cx in [(1,.32),(2,.68)]]
 design=dict(selection_mode='semantic_random',seed=5,selection_algorithm=ALGORITHM,visual_style_id=style,candidates=candidates,candidate_reasons={c:'适配当前案例' for c in candidates},selection_reason='适合',series_parameters={'paper':'ivory'},image_designs=items,composition_groups=[dict(id='pair',type='portrait_pair',image_ids=['I1','I2'])])
 source={'visual_design':design}
 assets=[dict(id='I'+str(i),file=n+'.png',status='ready',width=300,height=400,visual_style_id=style,route='imagegen',qa=dict(viewed=True,text_checked=True,structure_checked=True)) for i,n in [(1,'a'),(2,'b')]]
 manifest={'images':assets}
 clips=[dict(id='c'+str(i),image_design_id='I'+str(i),kind='image',file=n+'.png',start_s=0,end_s=4,size=[.29,.69],center=[cx,.49],reading_window_s=[.4,3.7]) for i,n,cx in [(1,'a',.32),(2,'b',.68)]]
 edit={'canvas':[1920,1080],'duration_s':4,'clips':clips}
 check=lambda p=source,m=manifest,e=edit:validate(p,'04',m,root,e,root)
 assert not check(),check()
 bad=copy.deepcopy(source);bad['visual_design']['visual_style_id']='fake';assert check(p=bad)
 bad=copy.deepcopy(source);bad['visual_design']['seed']=6;bad['visual_design']['visual_style_id']='fake';assert check(p=bad)
 bad=copy.deepcopy(manifest);bad['images'][1]['file']='a.png';assert check(m=bad)
 bad=copy.deepcopy(edit);bad['clips'][1]['center']=[.32,.49];assert check(e=bad)
 bad=copy.deepcopy(edit);bad['clips'][0]['center']=[.32,.9];assert check(e=bad)
 bad=copy.deepcopy(edit);bad['clips'][0]['file']='b.png';assert check(e=bad)
 bad=copy.deepcopy(edit);bad['clips'][0]['keyframes']={'position_x':[[0,-2],[.4,-.36]]};assert not check(e=bad),check(e=bad)
 add_contract(source,manifest,edit,root)
 (root/'source.json').write_text(json.dumps(source));(root/'assets.json').write_text(json.dumps(manifest))
 edit['visual_inputs']={k:str(root/n) for k,n in [('presentation_plan','source.json'),('asset_manifest','assets.json')]}
 for k in ['presentation_plan','asset_manifest']:edit['visual_inputs'][k+'_sha256']=digest(Path(edit['visual_inputs'][k]))
 gate(edit,root)
 bad=copy.deepcopy(edit);bad.pop('visual_inputs')
 try:gate(bad,root);raise AssertionError('gate bypass')
 except ValueError:pass
 print('PASS visual: valid pair, seeded selection, unknown style, duplicate images, overlap, subtitle area, wrong clip, permitted entry, mandatory gate')
 subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=blue:s=64x64:r=24','-t','0.3',str(root/'source.mp4')],check=True)
 for fps,dur in [(24,1),(24,1.013),(25,.041),(30,1.999)]:
  target=root/f'{fps}-{dur}.mp4';prepare_background(root/'source.mp4',target,dur,[64,64],fps)
  assert decoded_frames(target,fps)>=frame_count(dur,fps)+1
  p={'fps':fps,'clips':[dict(id='bg',kind='video',track='background',file=str(target),start_s=0,end_s=dur)]};verify_backgrounds(p,root,fps)
  try:verify_backgrounds(p,root,fps+1);raise AssertionError('fps mismatch allowed')
  except ValueError:pass
 p={'fps':24,'clips':[dict(id='bg',kind='video',track='background',file='source.mp4',start_s=0,end_s=2)]}
 try:verify_backgrounds(p,root,24);raise AssertionError('short source allowed')
 except ValueError:pass
 print('PASS background: integer/fractional durations, 24/25/30fps, loop short source, fps mismatch, short-frame rejection')
 # Exercise actual renderer and native builder against the same mandatory gate.
 import wave
 preview=copy.deepcopy(edit);preview.update(name='visual-pipeline-smoke',canvas=[320,180],duration_s=1.013,fps=30)
 for clip in preview['clips']:
  clip['end_s']=1.013;clip['reading_window_s']=[.1,.8]
 background=root/'30-1.013.mp4';prepare_background(root/'source.mp4',background,1.013,[320,180],30)
 preview['clips'].append(dict(id='BG',kind='video',track='background',file=str(background),start_s=0,end_s=1.013,media_size=[320,180],muted=True,z=-100))
 with wave.open(str(root/'voice.wav'),'wb') as audio:
  audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(32000);audio.writeframes(b'\0'*round(1.013*64000))
 preview['clips'].append(dict(id='voice',kind='audio',file='voice.wav',start_s=0,end_s=1.013,volume=1))
 add_contract(source,manifest,preview,root)
 (root/'source.json').write_text(json.dumps(source));(root/'assets.json').write_text(json.dumps(manifest))
 for k in ['presentation_plan','asset_manifest']:preview['visual_inputs'][k+'_sha256']=digest(Path(preview['visual_inputs'][k]))
 planpath=root/'edit.json';planpath.write_text(json.dumps(preview))
 for command in [
  [sys.executable,str(r/'04-video-cut/scripts/build_video.py'),'--plan',str(planpath),'--out',str(root/'native')],
  [sys.executable,str(r/'04-video-cut/scripts/render_preview.py'),'--plan',str(planpath),'--output',str(root/'final.mp4')]]:
  result=subprocess.run(command,capture_output=True,text=True)
  assert result.returncode==0,result.stderr
 assert decoded_frames(root/'final.mp4',30)>=frame_count(1.013,30)-1
 summary=json.loads((root/'native/build-summary.json').read_text())
 assert {x.get('image_design_id') for x in summary['segments']} >= {'I1','I2'}
 draft=json.loads(next((root/'native/drafts').glob('*/draft_info.json')).read_text())
 assert audit_evidence(preview,root,summary,draft,root/'final.mp4'), 'missing visual report accepted'
 for index,t in enumerate([0,.5,.9]):
  subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(root/'final.mp4'),'-frames:v','1',str(root/f'e{index}.png')],check=True)
 report=dict(plan_sha256=digest(planpath),mp4_sha256=digest(root/'final.mp4'),images=[])
 for ident in ['I1','I2']:
  report['images'].append(dict(image_design_id=ident,segment_ids=[x['segment_id'] for x in summary['segments'] if x.get('image_design_id')==ident],evidence_frames=['e0.png','e1.png','e2.png'],readable=True,subtitle_clear=True,content_checked=True,motion_checked=True))
 report['scene_reviews']=[dict(scene_id='S01',subject_matches=True,character_consistent=True,style_scope_correct=True,content_motion_visible=True,reading_comfortable=True,continuous_playback_checked=True,reviewer='synthetic-test',notes='Only validates wiring, no visual certification',evidence_frames=['e0.png','e1.png','e2.png'])]
 # A real rendered fixture serves as pilot evidence; structural test only.
 import hashlib
 pilot=dict(source_sha256=hashlib.sha256(json.dumps(source,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),scene_ids=['S01'],accepted=True,reviewer='synthetic-test',notes='Wiring only',video='final.mp4',video_sha256=digest(root/'final.mp4'),render_summary='native/build-summary.json',render_summary_sha256=digest(root/'native/build-summary.json'))
 (root/'pilot.json').write_text(json.dumps(pilot));preview.update(execution_phase='final',pilot_review_file='pilot.json')
 # Synthetic QA declarations exercise report wiring only, not human visual approval.
 (root/'visual-execution-report.json').write_text(json.dumps(report))
 assert not audit_evidence(preview,root,summary,draft,root/'final.mp4'), audit_evidence(preview,root,summary,draft,root/'final.mp4')
 report['mp4_sha256']='stale';(root/'visual-execution-report.json').write_text(json.dumps(report))
 assert audit_evidence(preview,root,summary,draft,root/'final.mp4')
 print('PASS actual small MP4/native build and audit report wiring; missing/stale evidence rejected')

