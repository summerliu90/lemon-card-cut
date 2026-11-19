#!/usr/bin/env python3
"""将已审核的语义表情锚点和任务背景编译进edit-plan；输入计划保留为独立版本。"""
import argparse,hashlib,json,math,random,shutil,subprocess,re
from pathlib import Path
from PIL import Image
from frame_contract import frame_count, decoded_frames, fps_value

def probe(path):
 d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],text=True));v=next(x for x in d['streams'] if x['codec_type']=='video');return int(v['width']),int(v['height']),float(d['format']['duration'])
def prepare_background(source,output,duration,canvas,fps=24):
 w,h=canvas
 frames=frame_count(duration,fps)+1
 # 预先循环并cover，草稿和本地渲染共享真实静音视频，时间从头连续。
 subprocess.run(['ffmpeg','-v','error','-y','-stream_loop','-1','-i',str(source),'-frames:v',str(frames),'-vf',f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(output)],check=True)
 actual=decoded_frames(output,fps)
 if actual<frames:raise ValueError(f'背景有效帧不足 {actual}/{frames}')
 return probe(output)
def motion(name,duration,cx,cy):
 tx,ty=2*cx-1,1-2*cy;entry=min(.32,duration/4);exit_at=duration-min(.2,duration/4)
 k={'alpha':[[0,0],[entry,1],[exit_at,1],[duration,0]]}
 if name=='pop':k['relative_scale']=[[0,.55],[entry*.7,1.10],[entry,1],[exit_at,1],[duration,.88]]
 elif name=='slide-left':k['position_x']=[[0,tx-.32],[entry,tx],[exit_at,tx],[duration,tx-.12]]
 elif name=='slide-right':k['position_x']=[[0,tx+.32],[entry,tx],[exit_at,tx],[duration,tx+.12]]
 elif name=='rise':k['position_y']=[[0,ty-.25],[entry,ty],[exit_at,ty],[duration,ty-.1]]
 else:raise ValueError('未知入场动效 '+name)
 return k

def resolve_meme_geometry(anchor,canvas):
 # size_px and normalized size are FINAL containment boxes, never multiplied again.
 W,H=canvas;center=anchor.get('center',[.5,.5]);scale=1.0
 if 'size_px' in anchor:
  pixels=anchor['size_px'];mode='final_pixels'
  if not isinstance(pixels,list) or len(pixels)!=2:raise ValueError('size_px must contain width/height')
  size=[pixels[0]/W,pixels[1]/H]
 elif 'size' in anchor:size=anchor['size'];mode='final_normalized'
 elif 'base_size' in anchor:
  scale=1.3;size=[v*scale for v in anchor['base_size']];mode='legacy_base_size'
 else:
  side=min(512,W*.8,H*.8);size=[side/W,side/H];mode='default_512px'
 values=list(center)+list(size)
 if len(center)!=2 or len(size)!=2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in values):raise ValueError('invalid meme geometry')
 if any(v<=0 or v>=1 for v in size):raise ValueError('meme cannot fill the canvas; redesign its containment box')
 if any(c-v/2<0 or c+v/2>1 for c,v in zip(center,size)):raise ValueError('meme steady box outside canvas; move it instead of silently shrinking')
 return center,[round(v,9) for v in size],scale,mode

def compile_plan(plan,base,task,project,anchors,outdir):
 if not task.get('eligible'):raise ValueError('任务配置未通过入口校验')
 if plan.get('style_id') and plan['style_id']!=task['style']:raise ValueError('基础分镜风格与任务锁定风格冲突，先修正01/02')
 for x in plan['clips']:
  if x.get('file'):x['file']=str((base/x['file']).resolve())
 if plan.get('pilot_review_file'):plan['pilot_review_file']=str((base/plan['pilot_review_file']).resolve())
 for key in ('presentation_plan','asset_manifest'):
  if plan.get('visual_inputs',{}).get(key):plan['visual_inputs'][key]=str((base/plan['visual_inputs'][key]).resolve())
 # 编译器接管背景和表情，防止在旧片上重复叠加；其它内容和音效沿用。
 plan['clips']=[x for x in plan['clips'] if x.get('track')!='background' and not x.get('meme_id')]
 plan.setdefault('fps',24);fps_value(plan['fps'])
 duration=plan['duration_s'];W,H=plan['canvas'];bg=task['background'];assets=outdir/'presentation-media';assets.mkdir(parents=True,exist_ok=True)
 if bg.get('mode')=='loop-video':
  src=project/bg['file'];dest=assets/'background-loop.mp4';w,h,actual=prepare_background(src,dest,duration,[W,H],fps=plan['fps']);plan['clips'].append({'id':'BG-CONTINUOUS','kind':'video','file':str(dest.resolve()),'track':'background','role':'background','start_s':0,'end_s':duration,'z':-100,'size':[1,1],'center':[.5,.5],'fit':'cover','media_size':[w,h],'volume':0,'muted':True,'source_duration_s':actual})
 else:plan['background']=bg['color']
 policy=task['meme_policy'];rng=random.Random(task['random_seed']);used_files=set();selected=[];invalid=[]
 if policy['enabled']:
  candidates=list(anchors);rng.shuffle(candidates)
  for a in candidates:
   # 01/02提供的锚点必须已有明确语义审核，不能按名字随机硬贴。
   if a.get('semantic_approved') is not True or not a.get('intent') or not a.get('trigger_text'):invalid.append(a.get('id','missing-id'));continue
   if a['trigger_text'] not in task['script']:invalid.append(a.get('id'));continue
   start=float(a['start_s']);end=float(a['end_s']);file=(project/a['file']).resolve()
   if not(0<=start<end<=duration) or end-start<.65 or not file.is_file():invalid.append(a.get('id'));continue
   if str(file) in used_files:continue
   if any(start<b['end_s']+.35 and end+.35>b['start_s'] for b in selected):continue
   if (a.get('contains_666') or re.search('666|六六六',file.name)) and not re.search('666|六六六',a['trigger_text']):invalid.append(a['id']);continue
   selected.append(a);used_files.add(str(file))
   if len(selected)>=policy['target_count']:break
 selected.sort(key=lambda x:x['start_s'])
 mapping=[]
 for i,a in enumerate(selected,1):
  source=(project/a['file']).resolve();dest=assets/(f'M{i:02}-'+source.name);shutil.copy2(source,dest);kind='video' if source.suffix.lower() in ['.mp4','.mov','.webm'] else 'image';center,size,display_scale,geometry_source=resolve_meme_geometry(a,[W,H]);base_size=a.get('base_size');name=a.get('entrance') or rng.choice(['pop','slide-left','slide-right','rise']);dur=a['end_s']-a['start_s'];mid=a['id'] if re.fullmatch(r'M\d+',a.get('id','')) else f'M{i:02}'
  x={'scene_id':a.get('scene_id'),'design_asset_id':a.get('design_asset_id'),'content_action_ids':a.get('content_action_ids',[]),'id':mid,'meme_id':mid,'kind':kind,'file':str(dest.resolve()),'track':'memes','role':'meme','start_s':a['start_s'],'end_s':a['end_s'],'center':center,'size':size,'base_size':base_size,'display_scale_applied':display_scale,'geometry_source':geometry_source,'size_px':[round(size[0]*W,3),round(size[1]*H,3)],'z':70,'keyframes':motion(name,dur,*center),'muted':True,'volume':0,'intent':a['intent'],'trigger_text':a['trigger_text'],'resource_id':a.get('resource_id'),'provider':'local_file_with_catalog_id' if a.get('resource_id') else 'local_file'}
  if kind=='image':
   with Image.open(dest) as image:frames=getattr(image,'n_frames',1);iw,ih=image.size
   if frames>1:
    original=dest;dest=dest.with_suffix('.loop.mp4');matte=a.get('matte','#FFFFFF').replace('#','0x')
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c={matte}:s={iw+(iw%2)}x{ih+(ih%2)}:r=24','-stream_loop','-1','-i',str(original),'-filter_complex','[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[out]','-map','[out]','-t',str(dur),'-an','-c:v','libx264','-crf','16',str(dest)],check=True)
    kind='video';x.update({'kind':'video','file':str(dest.resolve()),'source_file':str(original.resolve()),'source_frames':frames,'matte':a.get('matte','#FFFFFF'),'alpha_preserved':False})
  if kind=='video':
   w,h,seconds=probe(dest)
   if seconds+.05<dur:raise ValueError('表情视频太短，先用prepare_stickers循环 '+a['id'])
   x['media_size']=[w,h]
  plan['clips'].append(x);mapping.append({'meme_id':mid,'anchor_id':a['id'],'entrance':name,'file':str(dest.resolve()),'start_s':a['start_s'],'end_s':a['end_s']})
 reason=None
 if len(selected)<policy['target_count'] and policy['enabled']:reason='语义匹配素材或可读时间窗口不足，不凑数；需在导演报告说明或补充候选'
 plan['input_sha256']=task['input_sha256'];plan['style_id']=task['style'];plan['meme_policy']=policy;plan['presentation_report']={'seed':task['random_seed'],'target_count':policy['target_count'],'actual_count':len(selected),'shortfall_reason':reason,'invalid_anchor_ids':invalid,'mapping':mapping,'background':bg,'sfx_independent':True}
 if any(__import__('subtitle_contract').is_subtitle(c) for c in plan['clips']):
  from subtitle_contract import apply_subtitles
  subtitle=plan.get('subtitle_policy') or task.get('subtitle_policy') or {}
  font=subtitle.get('font_file')
  if not font:raise ValueError('字幕缺少真实新青年体font_file，请先冻结subtitle_policy')
  apply_subtitles(plan,(base/font).resolve())
 return plan

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--project',type=Path,required=True);a.add_argument('--plan',type=Path,required=True);a.add_argument('--anchors',type=Path);a.add_argument('--output',type=Path,required=True);args=a.parse_args();project=args.project.resolve();task=json.loads((project/'00-feishu-source/task.json').read_text());plan=json.loads(args.plan.read_text());anchors=json.loads(args.anchors.read_text())['anchors'] if args.anchors else []
 if args.output.resolve()==args.plan.resolve():raise ValueError('输出须使用新文件，不覆盖输入计划')
 args.output.parent.mkdir(parents=True,exist_ok=True);result=compile_plan(plan,args.plan.resolve().parent,task,project,anchors,args.output.resolve().parent);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(args.output.parent/'presentation-report.json').write_text(json.dumps(result['presentation_report'],ensure_ascii=False,indent=2)+'\n');print('已编译背景与表情',result['presentation_report']['actual_count'],'/',task['meme_policy']['target_count'])
if __name__=='__main__':main()
