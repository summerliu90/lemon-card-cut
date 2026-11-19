#!/usr/bin/env python3
"""将同一edit-plan的图片/原生文字/关键帧与旁白渲染为本地MP4；不上传。"""
import argparse,json,math,subprocess,bisect,hashlib
from visual_gate import gate
from mix_audio import mix_plan
from frame_contract import frame_count, verify_backgrounds, fps_value
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

EASING='linear'
def interpolate(keys,t,default):
 if not keys:return default
 if t<=keys[0][0]:return keys[0][1]
 for (a,v),(b,w) in zip(keys,keys[1:]):
  if t<=b:
   f=(t-a)/max(1e-9,b-a)
   if EASING!='linear':f=f*f*(3-2*f)
   return v+(w-v)*f
 return keys[-1][1]
def main():
 global EASING
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--plan',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--fps',type=int,default=None);a.add_argument('--font',type=Path,default=Path('/System/Library/Fonts/STHeiti Medium.ttc'));a.add_argument('--omit-subtitles',action='store_true',help='渲染兼容草稿的动态画面底片，字幕由剪映原生轨道承载');args=a.parse_args();p=json.loads(args.plan.read_text());base=args.plan.resolve().parent;W,H=p['canvas'];clips=sorted(p['clips'],key=lambda c:c.get('z',0));audio=[x for x in clips if x['kind']=='audio'];visual=[x for x in clips if x['kind']!='audio']
 gate(p,base)
 omitted_subtitles=[x['id'] for x in visual if x.get('role')=='subtitle' or x['id'].startswith('SUB-')] if args.omit_subtitles else []
 if args.omit_subtitles:visual=[x for x in visual if x['id'] not in set(omitted_subtitles)]
 if any(x.get('native_animations') or x.get('native_effects') for x in visual):raise ValueError('原生效果无法本地等价渲染，请另交付明确标注的关键帧近似计划')
 args.fps=args.fps if args.fps is not None else p.get('fps',24)
 fps_value(args.fps)
 args.fps=float(fps_value(args.fps))
 background_checks=verify_backgrounds(p,base,args.fps)
 EASING=p.get('keyframe_interpolation','linear')
 if any(x['kind'] not in ['image','text','video'] for x in visual):raise ValueError('原生贴纸ID需先验证并提供真实本地动画；不能使用PNG预览冒充动态图')
 args.output.parent.mkdir(parents=True,exist_ok=True);cache={};images={};animations={};video_dirs={};background_streams={}
 mixed=args.output.parent/'mixed-audio.wav';mixreport=mix_plan(p,base,mixed)
 for x in visual:
  if x['kind']=='video' and x.get('track')=='background':
   # 连续读rawvideo，避免把全片1080p背景展开成数千PNG。
   stream=subprocess.Popen(['ffmpeg','-v','error','-ss',str(x.get('source_start_s',0)),'-i',str(base/x['file']),'-vf',f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={args.fps}','-frames:v',str(math.ceil((x['end_s']-x['start_s'])*args.fps)),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
   background_streams[x['id']]=stream
  elif x['kind']=='video':
   folder=args.output.parent/'decoded-video'/x['id'];folder.mkdir(parents=True,exist_ok=True)
   for oldframe in folder.glob('*.png'):oldframe.unlink()
   subprocess.run(['ffmpeg','-v','error','-y','-ss',str(x.get('source_start_s',0)),'-i',str(base/x['file']),'-t',str(x['end_s']-x['start_s']),'-vf',f'fps={args.fps}',str(folder/'%05d.png')],check=True)
   paths=sorted(folder.glob('*.png'))
   if len(paths)<2:raise ValueError('视频没有多个有效帧 '+x['id'])
   video_dirs[x['id']]=paths
  elif x['kind']=='image':
   raw=Image.open(base/x['file']);images[x['id']]=raw.convert('RGBA')
   if getattr(raw,'n_frames',1)>1:
    frames=[];ends=[];total_ms=0
    for q in range(raw.n_frames):
     raw.seek(q);frames.append(raw.convert('RGBA'));total_ms+=max(10,raw.info.get('duration',100));ends.append(total_ms/1000)
    animations[x['id']]=(frames,ends,total_ms/1000)
  else:
   fontpath=(base/x['font_file']).resolve() if x.get('font_file') else args.font
   if x.get('font_name') and not x.get('font_file'):raise ValueError('命名字体需要真实font_file '+x['id'])
   if not fontpath.is_file():raise FileNotFoundError(fontpath)
   font=ImageFont.truetype(str(fontpath),round(x.get('font_px',46)));bb=font.getbbox(x['text']);tw=bb[2]-bb[0]+20;th=bb[3]-bb[1]+24;im=Image.new('RGBA',(tw,th));d=ImageDraw.Draw(im);d.text((10-bb[0],12-bb[1]),x['text'],font=font,fill=x.get('color','#151515'),stroke_width=x.get('stroke_width_px',0),stroke_fill=x.get('stroke_color','#000000'));images[x['id']]=im
 cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(args.fps),'-i','pipe:0','-i',str(mixed),'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t',str(p['duration_s']),'-movflags','+faststart',str(args.output)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 total=frame_count(p['duration_s'],args.fps)
 try:
  for n in range(total):
   t=n/args.fps;frame=Image.new('RGB',(W,H),p.get('background','#FFFFFF'))
   for x in visual:
    if not(x['start_s']<=t<x['end_s']):continue
    if x['id'] in background_streams:
     stream=background_streams[x['id']];data=stream.stdout.read(W*H*3)
     if len(data)!=W*H*3:raise ValueError('背景有效帧不足 '+x['id'])
     frame=Image.frombytes('RGB',(W,H),data);continue
    local=t-x['start_s'];kf=x.get('keyframes',{});cx,cy=x.get('center',[.5,.5]);cx=(interpolate(kf.get('position_x'),local,2*cx-1)+1)/2;cy=(1-interpolate(kf.get('position_y'),local,1-2*cy))/2
    if x['id'] in video_dirs:
     paths=video_dirs[x['id']];ix=min(len(paths)-1,int(local*args.fps));im=Image.open(paths[ix]).convert('RGBA')
    elif x['id'] in animations:
     frames,ends,total_ms=animations[x['id']];ix=min(len(frames)-1,bisect.bisect_right(ends,local%total_ms));im=frames[ix]
    else:im=images[x['id']]
    if x['kind'] in ['image','video']:
     dw,dh=x.get('size',[1,1]);factor=(max if x.get('fit')=='cover' else min)(dw*W/im.width,dh*H/im.height)*interpolate(kf.get('relative_scale'),local,1)
    else:factor=interpolate(kf.get('uniform_scale'),local,1)
    ww=max(1,round(im.width*factor));hh=max(1,round(im.height*factor));key=(x['id'],ww,hh,ix if x['id'] in video_dirs or x['id'] in animations else 0)
    if key not in cache:
     if len(cache)>500:cache.clear()
     cache[key]=im.resize((ww,hh),Image.Resampling.LANCZOS)
    ready=cache[key];alpha=interpolate(kf.get('alpha'),local,x.get('alpha',1))
    if alpha<.999:
     ready=ready.copy();ready.putalpha(ready.getchannel('A').point(lambda v:round(v*max(0,min(1,alpha)))))
    frame.paste(ready,(round(cx*W-ww/2),round(cy*H-hh/2)),ready)
   proc.stdin.write(frame.tobytes())
   if n%args.fps==0 and n%(args.fps*10)==0:print(f'render {n/args.fps:.0f}/{p["duration_s"]:.1f}s',flush=True)
 finally:
  proc.stdin.close()
  for stream in background_streams.values():
   stream.stdout.close();stream.terminate();stream.wait()
 if proc.wait()!=0:raise RuntimeError('ffmpeg渲染失败')
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(args.output)],text=True));video=next(x for x in probe['streams'] if x['codec_type']=='video');aud=next(x for x in probe['streams'] if x['codec_type']=='audio')
 (args.output.parent/'render-check.json').write_text(json.dumps({'file':args.output.name,'duration_s':float(probe['format']['duration']),'video':[video['width'],video['height'],video['codec_name']],'audio':aud['codec_name'],'subtitle_word_alignment':'estimated','font':str(args.font),'same_edit_plan':str(args.plan.resolve()),'omitted_native_subtitles':omitted_subtitles,'purpose':'dynamic_plate_for_native_subtitle_draft' if args.omit_subtitles else 'full_preview','plan_sha256':hashlib.sha256(args.plan.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'fps':str(args.fps),'background_frame_checks':background_checks,'audio_listened':False,'mixed_audio':'mixed-audio.wav','audio_tracks':len(audio),'sfx_count':mixreport['sfx_count'],'animated_backgrounds':len(background_streams),'animated_video_clips':len(video_dirs),'animated_gifs':len(animations)},ensure_ascii=False,indent=2)+'\n')
 print('MP4已渲染',args.output)
if __name__=='__main__':main()
