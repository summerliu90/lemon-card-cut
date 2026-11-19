#!/usr/bin/env python3
"""检查项目表情真实文件，保留原GIF并准备可用于剪映/本地渲染的循环视频。"""
import argparse,json,re,subprocess
from pathlib import Path
from PIL import Image

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--manifest',type=Path,required=True);a.add_argument('--min-duration',type=float,default=3);a.add_argument('--fps',type=int,default=24);args=a.parse_args();m=args.manifest.resolve();base=m.parent;d=json.loads(m.read_text());items=d.get('items',[])
 if args.min_duration<=0 or args.fps<1:raise ValueError('时长和帧率必须为正数')
 for x in items:
  if not re.fullmatch(r'M\d+',x['id']):raise ValueError('非法M编号')
  p=(base/x['file']).resolve()
  if not p.is_relative_to(base) or not p.is_file():raise ValueError('素材必须是项目内实际文件 '+str(p))
  if p.suffix.lower() in ['.mp4','.mov','.webm']:
   x['render_file']=x['file'];x['render_format']='mp4';continue
  im=Image.open(p);n=getattr(im,'n_frames',1);duration=0
  for f in range(n):im.seek(f);duration+=im.info.get('duration',0)
  x.update({'width':im.width,'height':im.height,'frames':n,'duration_ms':duration if n>1 else None,'local_decode_verified':True})
  if n>1:
   out=p.with_name(x['id']+'-loop.mp4')
   subprocess.run(['ffmpeg','-v','error','-y','-stream_loop','-1','-i',str(p),'-t',str(args.min_duration),'-vf',f'fps={args.fps},pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p','-an','-c:v','libx264','-crf','16',str(out)],check=True)
   x.update({'render_file':str(out.relative_to(base)),'render_format':'mp4','loop_prepared_s':args.min_duration})
  else:x.update({'render_file':x['file'],'render_format':'png' if p.suffix.lower()=='.png' else p.suffix.lstrip('.')})
  # Catalog ID availability is not inferred from local file decoding.
  x['status']='ready'
 d['ready_count']=sum(x.get('status')=='ready' for x in items);m.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print('已准备',d['ready_count'],'个本地表情')
if __name__=='__main__':main()
