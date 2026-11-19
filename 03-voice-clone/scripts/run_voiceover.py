#!/usr/bin/env python3
"""01分镜→配音输入→音频与原文字幕交接；不改写01和02。默认仅准备，--synthesize才调用TTS。"""
import argparse,asyncio,csv,hashlib,json,os,re,subprocess,sys,wave
from pathlib import Path
STAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STAGE));sys.path.insert(0,str(STAGE/'scripts'))

def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def audio_input_digest(text,settings):
 return hashlib.sha256(json.dumps({'text':text,'voice':{k:v for k,v in settings.items() if k!='authorization'}},ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def time_s(s):
 a=s.split(':');return sum(float(v)*60**i for i,v in enumerate(reversed(a)))
def parse_plan(p):
 text=p.read_text();items=[]
 for match in re.finditer(r'^### (S\d+)｜([^\n]+)\n(.*?)(?=^### S\d+｜|^## |\Z)',text,re.M|re.S):
  sid,span,body=match.groups();raw=re.search(r'^口播：(.*)$',body,re.M)
  if not raw:continue
  start,end=[time_s(t) for t in span.split('–')]
  items.append({'id':sid,'text':raw[1].strip(),'speak_text':raw[1].strip(),'planned_start_s':start,'planned_duration_s':end-start})
 if not items:
  for m in re.finditer(r'^\|\s*(S\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|',text,re.M):
   sid,span,raw=m.groups();start,end=[time_s(t.strip()) for t in span.strip().split('–')];items.append({'id':sid,'text':raw.strip(),'speak_text':raw.strip(),'planned_start_s':start,'planned_duration_s':end-start})
 if not items:raise ValueError('未找到逐镜口播，必须先补齐01的S编号与口播字段')
 if len({x['id'] for x in items})!=len(items):raise ValueError('镜号重复')
 return items

def speak(raw):
 # 只处理本流程已明确的缩写与引流暗号，其余读音由speak_text逐项人工校正。
 text=re.sub(r'\bAI\b','A I',raw)
 text=re.sub(r'(?<!\d)666(?!\d)','六六六',text)
 return text.replace('“','').replace('”','')

def duration(path):
 return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],text=True).strip())
def srt_time(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--project',type=Path,required=True);a.add_argument('--version',default='v1');a.add_argument('--synthesize',action='store_true');a.add_argument('--finalize',action='store_true');a.add_argument('--config-root',type=Path);a.add_argument('--provider',choices=['minimax','edge-tts']);a.add_argument('--voice');a.add_argument('--tail',type=float,default=1.0);args=a.parse_args()
 project=args.project.resolve();out=project/'03-voice-clone'/args.version;out.mkdir(parents=True,exist_ok=True)
 if args.config_root:os.environ['LEMON_VOICE_CONFIG_ROOT']=str(args.config_root.resolve())
 import generate_tts as tts
 tts.load_dotenv_if_present()
 # 不默默换声音；失败保留原provider的失败状态。
 os.environ['MINIMAX_TTS_FALLBACK_EDGE']='0'
 provider=args.provider or os.environ.get('TUTOR_TTS_PROVIDER','minimax');voice=args.voice or os.environ.get('MINIMAX_ACTIVE_VOICE','播客男')
 taskfile=project/'00-feishu-source/task.json';task=json.loads(taskfile.read_text()) if taskfile.exists() else None
 if task:
  if task.get('eligible') is not True:raise ValueError('制作输入未通过审核/配置门禁，不得发送配音')
  selected=task['voice']
  if args.voice and args.voice not in [selected['label'],selected['id'],selected['voice_id']]:raise ValueError('命令音色与飞书锁定音色冲突')
  if args.provider and args.provider!='minimax':raise ValueError('飞书音色目录对应MiniMax，不能静默换provider')
  provider='minimax';voice=selected['label']
 plan=project/'01-shot-list/01-shot-list.md'
 current=project/'01-shot-list/current.json'
 if current.exists():plan=project/'01-shot-list'/json.loads(current.read_text())['shot_list']
 if not plan.exists():plan=project/'01-shot-list.md'
 items=parse_plan(plan)
 if task and re.sub(r'\s+','',''.join(x['text'] for x in items))!=re.sub(r'\s+','',task['script']):raise ValueError('01逐镜口播与飞书审核原文不一致，请先修正分镜')
 existing=out/'segments_input.json'
 if existing.exists():
  old=json.loads(existing.read_text());olditems={x['id']:x for x in old['items']}
  for x in items:
   if x['id'] in olditems and olditems[x['id']]['text']==x['text']:x['speak_text']=olditems[x['id']]['speak_text']
 for x in items:
  if x['speak_text']==x['text']:x['speak_text']=speak(x['text'])
  x['filename']=x['id']+'.wav'
 dump(existing,{'schema_version':1,'source':str(plan.relative_to(project)),'source_sha256':hashlib.sha256(plan.read_bytes()).hexdigest(),'items':items})
 with (out/'tts.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['filename','text']);w.writeheader();w.writerows({'filename':x['filename'],'text':x['speak_text']} for x in items)
 cfg=tts.build_minimax_config(voice) if provider=='minimax' else None
 if task and cfg['voice_id']!=task['voice']['voice_id']:raise ValueError('TTS实际voice_id与飞书解析不一致')
 config_public={'provider':provider,'voice_label':voice,'voice_id':cfg['voice_id'] if cfg else voice,'speed':cfg['speed'] if cfg else os.environ.get('TUTOR_TTS_RATE','default'),'source_config':'external config directory' if args.config_root else 'environment or skill root .env','new_clone_created':False}
 if args.finalize and not args.synthesize and (out/'voice-settings.json').exists():
  config_public=json.loads((out/'voice-settings.json').read_text());provider=config_public['provider'];voice=config_public['voice_label']
 if task and config_public['voice_id']!=task['voice']['voice_id']:raise ValueError('已有配音版本音色与任务不一致，请使用新版本')
 if provider=='minimax':config_public['authorization']=(task or {}).get('minimax_authorization',{'source':'用户2026-10-27明确授权本工作流已审核口播发送MiniMax生成所选音色，无需逐条重复确认','scope':'approved_script_tts_only','provider':'minimax'})
 dump(out/'voice-settings.json',config_public)
 audio=out/'audio';audio.mkdir(exist_ok=True)
 if args.synthesize:
  if provider=='minimax':tts.ensure_minimax_voice(cfg)
  async def run():
   for x in items:
    path=audio/x['filename'];stamp=path.with_suffix('.input.sha256');digest=audio_input_digest(x['speak_text'],config_public)
    if path.exists() and stamp.exists() and stamp.read_text()==digest and duration(path)>0:print(x['id'],'复用已合成音频',flush=True);continue
    print(x['id'],'合成中',flush=True)
    ok,_=await tts.generate_audio(x['speak_text'],str(path),provider,voice=voice,minimax_cfg=cfg)
    if not ok:raise RuntimeError(x['id']+'配音失败；未切换provider')
    stamp.write_text(digest)
  asyncio.run(run())
 if not(args.synthesize or args.finalize):print('配音输入已准备，未调用TTS');return
 if task and args.finalize and not args.synthesize:
  for x in items:
   stamp=(audio/x['filename']).with_suffix('.input.sha256');expected=audio_input_digest(x['speak_text'],config_public)
   if not stamp.exists() or stamp.read_text()!=expected:raise ValueError('已有片段音频输入或音色未验证，不能直接finalize：'+x['id'])
 missing=[x['id'] for x in items if not (audio/x['filename']).is_file()]
 if missing:raise RuntimeError('缺音频：'+','.join(missing))
 cursor=0;subs=[];joined=[]
 for x in items:
  path=audio/x['filename'];normalized=audio/(x['id']+'-pcm.wav')
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-ar','32000','-ac','1','-c:a','pcm_s16le',str(normalized)],check=True)
  with wave.open(str(normalized),'rb') as wf:
   pcm=wf.readframes(wf.getnframes());assert wf.getnchannels()==1 and wf.getsampwidth()==2
   dur=len(pcm)/64000
  joined.append(pcm);x.update({'start_s':cursor,'end_s':cursor+dur,'duration_s':dur,'audio':str(normalized.relative_to(out)),'timing_source':'measured_audio','events_alignment':'intra-shot estimated; not word-level aligned'})
  chunks=[s.strip() for s in re.findall(r'[^，。！？；：]+[，。！？；：]?',x['text']) if s.strip()]
  # 拆字幕不超过20字；没有词级边界时明确按字符权重估算。
  chunks=[s[i:i+20] for s in chunks for i in range(0,len(s),20)]
  weight=sum(len(s) for s in chunks);offset=cursor
  for j,s in enumerate(chunks):
   end=x['end_s'] if j==len(chunks)-1 else offset+dur*len(s)/weight
   subs.append({'text':s,'start_s':offset,'end_s':end,'shot':x['id'],'timing_source':'estimated_within_measured_shot'});offset=end
  cursor+=dur
 joined.append(b'\0'*round(args.tail*64000))
 with wave.open(str(out/'narration.wav'),'wb') as wf:wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(32000);wf.writeframes(b''.join(joined))
 dump(out/'segments_audio.json',{'schema_version':1,'status':'ready_for_editing','voice':config_public,'items':items,'speech_duration_s':cursor,'tail_s':args.tail,'total_duration_s':duration(out/'narration.wav'),'qa':{'decoded':True,'listened':False,'word_alignment':'not_available','subtitle_alignment':'estimated_within_measured_shot'}})
 dump(out/'subtitles.json',{'items':subs,'timing_source':'estimated_within_measured_shot'})
 (out/'subtitles.srt').write_text(''.join(f'{i+1}\n{srt_time(x["start_s"])} --> {srt_time(x["end_s"])}\n{x["text"]}\n\n' for i,x in enumerate(subs)))
 (project/'03-voice-manifest.md').write_text(f'# 配音交接 {args.version}\n\n音色：{voice}；provider：{provider}。\n\n- [音频](03-voice-clone/{args.version}/narration.wav)\n- [真实镜头时长](03-voice-clone/{args.version}/segments_audio.json)\n- [字幕](03-voice-clone/{args.version}/subtitles.srt)\n\n句内字幕/事件时间为估算，非词级强制对齐；音频未人工试听。\n')
 print('完成配音交接',round(cursor+args.tail,3),'秒',flush=True)
if __name__=='__main__':main()
