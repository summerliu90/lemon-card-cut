#!/usr/bin/env python3
"""按edit-plan的真实音频文件、入点与音量混音；不生成或替换旁白。"""
import json,subprocess,wave,audioop,math
from pathlib import Path

def mix_plan(plan,base,output):
 clips=[x for x in plan['clips'] if x['kind']=='audio']
 if not clips:raise ValueError('计划缺少音频，不能输出无声成片')
 cmd=['ffmpeg','-v','error','-y'];filters=[];labels=[];rows=[]
 for i,x in enumerate(clips):
  p=(base/x['file']).resolve()
  if not p.is_file():raise FileNotFoundError(p)
  cmd+=['-i',str(p)];duration=x['end_s']-x['start_s'];delay=round(x['start_s']*1000);volume=x.get('volume',1)
  filters.append(f'[{i}:a]atrim=start={x.get("source_start_s",0)}:duration={duration},asetpts=PTS-STARTPTS,aresample=48000,volume={volume},adelay={delay}:all=1[a{i}]');labels.append(f'[a{i}]')
  rows.append({'id':x['id'],'role':x.get('role','audio'),'source':str(p),'start_s':x['start_s'],'end_s':x['end_s'],'volume':volume,'sfx_id':x.get('sfx_id')})
 filters.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,apad=whole_dur={plan["duration_s"]},atrim=duration={plan["duration_s"]},alimiter=limit=0.95:level=false:latency=true[out]')
 cmd+=['-filter_complex',';'.join(filters),'-map','[out]','-ac','1','-ar','48000','-c:a','pcm_s16le',str(output)]
 subprocess.run(cmd,check=True)
 with wave.open(str(output),'rb') as wf:
  data=wf.readframes(wf.getnframes());dur=wf.getnframes()/wf.getframerate();width=wf.getsampwidth()
 peak=audioop.max(data,width);rms=audioop.rms(data,width)
 sfx=[x for x in rows if x.get('sfx_id')];starts=sorted(x['start_s'] for x in sfx)
 report={'tracks':rows,'sfx_count':len(sfx),'duration_s':dur,'peak_dbfs':20*math.log10(max(1,peak)/32768),'rms_dbfs':20*math.log10(max(1,rms)/32768),'clip_free':peak<32767,'max_sfx_starts_per_10s':max([sum(t<=u<t+10 for u in starts) for t in starts] or [0]),'min_sfx_gap_s':min([b-a for a,b in zip(starts,starts[1:])] or [0]),'listened':False}
 output.with_suffix('.mix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 return report
