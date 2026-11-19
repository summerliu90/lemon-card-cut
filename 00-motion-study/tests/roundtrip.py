#!/usr/bin/env python3
"""仅使用临时库和合成测试视频验证00→01，不向正式学习库添加伪学习条目。"""
import tempfile,json,subprocess,sys,copy,hashlib
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/motion_library.py'
def run(library,*args,ok=True):
 r=subprocess.run([sys.executable,str(SCRIPT),'--library',str(library),*map(str,args)],text=True,capture_output=True)
 assert (r.returncode==0)==ok,(r.stdout,r.stderr)
 return r

def main():
 with tempfile.TemporaryDirectory(prefix='motion-study-test-') as tmp:
  root=Path(tmp);library=root/'library';library.mkdir();(library/'index.json').write_text(json.dumps({'schema_version':1,'revision':0,'entries':[]}));project=root/'project';video=root/'synthetic-test.mp4'
  subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=12','-t','2','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True)
  run(library,'select','--project',project,'--style','xiaohei');snap=project/'01-shot-list/motion-library-snapshot.json';assert not json.loads(snap.read_text())['candidates']
  run(library,'prepare','--video',video,'--start','0','--end','3','--out',root/'invalid',ok=False)
  study=root/'study';run(library,'prepare','--video',video,'--start','0','--end','2','--out',study,'--interval','.5');source=json.loads((study/'source.json').read_text());assert len(source['frame_files'])==4 and (study/'contact-sheet.jpg').is_file()
  recipe={'analysis_status':'analyzed','source_sha256':source['source_sha256'],'motions':[{'id':'synthetic-study-fixture','name':'Synthetic fixture only','source_span_s':[0,2],'timing_precision':'estimated_from_frames','intents':['steps'],'styles':['all'],'requires_character':False,'layout':'fixture layout','layers':['node'],'visual_change':'fixture focus change','steps':[{'phase':'enter','duration_s':.3,'action':'test'},{'phase':'hold','duration_s':1.7,'action':'test'}],'asset_requirements':['independent layer'],'implementation':{'provider':'keyframes','validation':'unverified'},'avoid_when':['fixture only']}]};rp=study/'recipe.json';rp.write_text(json.dumps(recipe))
  bad=copy.deepcopy(recipe);bad['source_sha256']='wrong';(study/'bad.json').write_text(json.dumps(bad));run(library,'publish','--study',study,'--recipe',study/'bad.json',ok=False)
  run(library,'publish','--study',study,'--recipe',rp,'--project',project,'--style','xiaohei');first=json.loads(snap.read_text());assert len(first['candidates'])==1 and first['candidates'][0]['requires_implementation_validation'];pinned=project/first['immutable_snapshot'];old=pinned.read_bytes();assert (project/'00-motion-study/handoff.json').is_file()
  run(library,'publish','--study',study,'--recipe',rp);assert json.loads((library/'index.json').read_text())['revision']==1
  recipe['motions'][0]['name']='Updated fixture';rp.write_text(json.dumps(recipe));run(library,'publish','--study',study,'--recipe',rp,'--project',project,'--style','xiaohei');assert json.loads(snap.read_text())['candidates'][0]['version']==2 and pinned.read_bytes()==old
  run(library,'select','--project',project,'--style','xiaohei','--intent','comparison');assert not json.loads(snap.read_text())['candidates']
  recipe['motions'][0]['requires_character']=True;recipe['motions'][0]['implementation']={'provider':'jianying_native','resource_id':'fixture-not-real','validation':'unverified'};rp.write_text(json.dumps(recipe));run(library,'publish','--study',study,'--recipe',rp)
  run(library,'select','--project',project,'--style','no-character');assert not json.loads(snap.read_text())['candidates']
  run(library,'select','--project',project,'--style','xiaohei','--target','mp4');assert not json.loads(snap.read_text())['candidates'][0]['execution_ready_for_target']
 print('PASS: frame evidence, invalid span/hash rejection, publish→01 automatic handoff, duplicate no-op, immutable version snapshots, style/intent filters, unverified native effect blocked for MP4')
if __name__=='__main__':main()
