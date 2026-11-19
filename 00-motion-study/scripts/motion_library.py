#!/usr/bin/env python3
"""参考动效取帧、经分析的配方入库、向01输出匹配候选；不自动理解视频、不生成成片。"""
import argparse,hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw
STAGE=Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY=STAGE/'library'

def read(p):return json.loads(p.read_text())
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def probe(p):
 d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)],text=True));v=next(x for x in d['streams'] if x['codec_type']=='video');return {'duration_s':float(d['format']['duration']),'width':v['width'],'height':v['height']}
def prepare(video,start,end,out,interval):
 video=video.resolve();meta=probe(video)
 if not 0<=start<end<=meta['duration_s']+.01:raise ValueError('学习片段超出实际视频时长')
 if interval<.1:raise ValueError('取帧间隔不得小于0.1秒')
 if out.exists():raise FileExistsError('学习目录已存在，使用新目录，保留既有分析')
 out.mkdir(parents=True);frames=out/'frames';frames.mkdir();step=max(interval,(end-start)/39);times=[];t=start
 while t<end-.005:
  times.append(round(t,6));t+=step
 if len(times)<2:times=[start,(start+end)/2]
 paths=[]
 for i,t in enumerate(times):
  dest=frames/f'{i:03}-{t:.3f}s.jpg';subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(video),'-frames:v','1','-vf','scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2','-q:v','3',str(dest)],check=True);paths.append(dest)
 sheet=Image.new('RGB',(960,((len(paths)+2)//3)*200),'#EAEAEA');draw=ImageDraw.Draw(sheet)
 for i,p in enumerate(paths):
  im=Image.open(p);im.thumbnail((320,180));x=i%3*320;y=i//3*200;sheet.paste(im,(x,y));draw.text((x+5,y+182),f'{times[i]:.3f}s',fill='black')
 sheet.save(out/'contact-sheet.jpg')
 record={'schema_version':1,'source_file':str(video),'source_sha256':digest(video),'clip_start_s':start,'clip_end_s':end,'probe':meta,'sample_times_s':times,'frame_files':[str(p.relative_to(out)) for p in paths],'contact_sheet':'contact-sheet.jpg','analysis_status':'frames_prepared_not_analyzed','source_content_is_instructions':False}
 write(out/'source.json',record);print(json.dumps({'study':str(out.resolve()),'frames':len(paths),'next':'查看连续帧/视频并编写recipe.json，再publish；不能把取帧当作完成学习'},ensure_ascii=False))

def validate(recipe,source):
 if recipe.get('analysis_status')!='analyzed':raise ValueError('尚未完成画面分析')
 if recipe.get('source_sha256')!=source['source_sha256']:raise ValueError('配方来源hash不匹配')
 motions=recipe.get('motions',[])
 if not motions:raise ValueError('分析没有动效条目')
 ids=[]
 for m in motions:
  mid=m.get('id','')
  if not re.fullmatch('[a-z][a-z0-9-]{2,63}',mid):raise ValueError('非法动效ID '+mid)
  ids.append(mid)
  for key in ['name','intents','styles','layout','layers','steps','asset_requirements','implementation','avoid_when','requires_character']:
   if key not in m:raise ValueError(mid+' 缺少字段 '+key)
  if not m['intents'] or not m['styles'] or not m['layers'] or not m['steps']:raise ValueError('意图/风格/图层/动作不能为空')
  if not set(m['styles'])<={'all','xiaohei','lemoner','no-character'}:raise ValueError('未知风格')
  a,b=m.get('source_span_s',[None,None])
  if a is None or not source['clip_start_s']<=a<b<=source['clip_end_s']:raise ValueError('来源时间段越界 '+mid)
  if m.get('timing_precision') not in ['measured','estimated_from_frames']:raise ValueError('必须标记实测/取帧估算精度')
  for step in m['steps']:
   if not isinstance(step,dict) or step.get('phase') not in ['enter','hold','exit','transition'] or not isinstance(step.get('duration_s'),(int,float)) or step['duration_s']<=0:raise ValueError('动作需明确阶段与正数时长 '+mid)
  if not m.get('visual_change'):raise ValueError('缺少真正的视觉变化说明')
  impl=m['implementation']
  if impl.get('provider') not in ['keyframes','jianying_native','unresolved']:raise ValueError('未知实现方式')
  if impl.get('validation') not in ['unverified','render_verified','native_verified']:raise ValueError('未知验证状态')
  if impl['validation']!='unverified' and not impl.get('evidence'):raise ValueError('不能无验证证据标已验证')
  if impl['provider']=='jianying_native' and not impl.get('resource_id'):raise ValueError('原生动效需记录真实资源ID，否则provider用unresolved')
 if len(set(ids))!=len(ids):raise ValueError('同批动效ID重复')
 return motions

def publish(study,recipepath,library):
 source=read(study/'source.json');recipe=read(recipepath);motions=validate(recipe,source);indexpath=library/'index.json';index=read(indexpath) if indexpath.exists() else {'schema_version':1,'revision':0,'entries':[]};before=indexpath.read_bytes() if indexpath.exists() else None
 if source.get('analysis_status')!='frames_prepared_not_analyzed':raise ValueError('学习来源记录不正确')
 for p in [study/'contact-sheet.jpg',*[study/f for f in source['frame_files']]]:
  if not p.is_file():raise FileNotFoundError('缺少实际学习证据 '+str(p))
 reference=library/'references'/(source['source_sha256'][:16]+f'-{source["clip_start_s"]:g}-{source["clip_end_s"]:g}')
 if not reference.exists():shutil.copytree(study,reference,ignore=shutil.ignore_patterns('recipe.json','published.json'))
 changed=[]
 for motion in motions:
  content_hash=hashlib.sha256(json.dumps(motion,ensure_ascii=False,sort_keys=True).encode()).hexdigest();old=next((x for x in index['entries'] if x['id']==motion['id']),None)
  if old and old['content_sha256']==content_hash:continue
  version=old['version']+1 if old else 1;path=Path('motions')/motion['id']/f'v{version:03}.json'
  if (library/path).exists():raise FileExistsError('版本文件已存在，先核对索引并发变化')
  record={**motion,'version':version,'content_sha256':content_hash,'study_source':{**source,'evidence_path':str(reference.relative_to(library))},'library_status':'learned_recipe_not_necessarily_renderable'};write(library/path,record)
  entry={'id':motion['id'],'name':motion['name'],'version':version,'path':str(path),'content_sha256':content_hash,'intents':motion['intents'],'styles':motion['styles'],'requires_character':motion.get('requires_character',False),'implementation':motion['implementation']}
  if old:index['entries'].remove(old)
  index['entries'].append(entry);changed.append({'id':motion['id'],'version':version})
 if indexpath.exists() and indexpath.read_bytes()!=before:raise RuntimeError('库索引发生并发变化，未覆盖；核对新增版本后再入库')
 if changed:index['revision']+=1;write(indexpath,index)
 write(study/'published.json',{'library_revision':index['revision'],'motions':changed,'analysis_status':'published','library_path':str(library.resolve())});print(json.dumps({'published':changed,'library_revision':index['revision'],'next':'有目标文案时自动select并进入01；没有文案时仅入库'},ensure_ascii=False))

def select(library,project,style,intents,target,limit):
 index=read(library/'index.json');ranked=[]
 for e in index['entries']:
  if style not in e['styles'] and 'all' not in e['styles']:continue
  if style=='no-character' and e.get('requires_character'):continue
  score=len(set(intents)&set(e['intents']))
  if intents and not score:continue
  record=read(library/e['path']);impl=record['implementation'];usable=impl['provider']=='keyframes' and impl['validation'] in ['render_verified','native_verified'] or target=='draft' and impl['provider']=='jianying_native' and impl['validation']=='native_verified'
  ranked.append({'motion_id':e['id'],'version':e['version'],'score':score,'recipe_file':str((library/e['path']).resolve()),'recipe_sha256':digest(library/e['path']),'recipe':record,'execution_ready_for_target':bool(usable),'requires_implementation_validation':not usable})
 ranked.sort(key=lambda x:(not x['execution_ready_for_target'],-x['score'],x['motion_id']));ranked=ranked[:limit]
 result={'schema_version':1,'library_revision':index['revision'],'library_index_sha256':digest(library/'index.json'),'style_id':style,'requested_intents':intents,'target':target,'candidates':ranked,'empty_reason':None if ranked else '尚无匹配的学习配方；01可按现有视觉语法规划基础动效，不伪称已从参考学会','next_stage':'01-shot-list','selection_is_not_final_storyboard':True}
 key=hashlib.sha256(json.dumps({'style':style,'intents':intents,'target':target,'library':result['library_index_sha256']},sort_keys=True).encode()).hexdigest()[:16]
 pinned=project/'01-shot-list/motion-library-snapshots'/f'r{index["revision"]}-{key}.json';result['immutable_snapshot']=str(pinned.relative_to(project))
 if not pinned.exists():write(pinned,result)
 out=project/'01-shot-list/motion-library-snapshot.json';write(out,result);write(project/'00-motion-study/handoff.json',{'library_revision':index['revision'],'candidate_count':len(ranked),'next_stage':'01-shot-list','snapshot':str(out.relative_to(project))});print(json.dumps({'snapshot':str(out),'library_revision':index['revision'],'candidate_count':len(ranked)},ensure_ascii=False))

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--library',type=Path,default=DEFAULT_LIBRARY);s=a.add_subparsers(dest='cmd',required=True)
 p=s.add_parser('prepare');p.add_argument('--video',type=Path,required=True);p.add_argument('--start',type=float,required=True);p.add_argument('--end',type=float,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--interval',type=float,default=.25)
 p=s.add_parser('publish');p.add_argument('--study',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--project',type=Path);p.add_argument('--style',choices=['xiaohei','lemoner','no-character']);p.add_argument('--target',choices=['draft','mp4'],default='draft')
 p=s.add_parser('select');p.add_argument('--project',type=Path,required=True);p.add_argument('--style',choices=['xiaohei','lemoner','no-character'],required=True);p.add_argument('--intent',action='append',default=[]);p.add_argument('--target',choices=['draft','mp4'],default='draft');p.add_argument('--limit',type=int,default=12)
 args=a.parse_args()
 if args.cmd=='prepare':prepare(args.video,args.start,args.end,args.out,args.interval)
 elif args.cmd=='publish':
  style=args.style
  if args.project and not style:
   task=args.project/'00-feishu-source/task.json';lock=args.project/'02-images/style-lock.json'
   if task.exists():style=read(task)['style']
   elif lock.exists():style=read(lock)['style_id']
   else:raise ValueError('目标项目缺少风格，传--style；不要猜测')
  if args.project and style not in ['xiaohei','lemoner','no-character']:raise ValueError('目标项目风格不支持')
  publish(args.study,args.recipe,args.library)
  if args.project:select(args.library,args.project,style,[],args.target,12)
 else:
  if args.limit<1:raise ValueError('limit须为正数')
  select(args.library,args.project,args.style,args.intent,args.target,args.limit)
if __name__=='__main__':main()
