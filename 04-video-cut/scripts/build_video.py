#!/usr/bin/env python3
"""从已校准edit-plan生成可编辑本地剪映草稿，不触发TTS、云渲染或覆盖已有草稿。"""
import argparse,json,os,sys,hashlib,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['JY_SKILL_ROOT']=str(ROOT)
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'scripts/vendor'))
from visual_gate import gate
from frame_contract import verify_backgrounds, fps_value
from jy_wrapper import JyProject
import pyJianYingDraft as jy

def rgb(v):return tuple(int(v.lstrip('#')[i:i+2],16)/255 for i in (0,2,4))
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args();planpath=args.plan.resolve();p=json.loads(planpath.read_text());base=planpath.parent;out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
 gate(p,base)
 verify_backgrounds(p,base,p.get('fps',24))
 W,H=p.get('canvas',[1920,1080]);ids=set()
 for x in p['clips']:
  if x['id'] in ids:raise ValueError('重复clip ID '+x['id'])
  ids.add(x['id'])
  if not(0<=x['start_s']<x['end_s']<=p['duration_s']+.01):raise ValueError('时间越界 '+x['id'])
  if x['kind'] in ('image','video','audio') and not(base/x['file']).is_file():raise FileNotFoundError(x['file'])
  for prop,keys in x.get('keyframes',{}).items():
   if any(not(0<=t<=x['end_s']-x['start_s']+.001) for t,v in keys):raise ValueError('关键帧越界 '+x['id'])
 drafts=out/'drafts';draftdir=drafts/p['name']
 if draftdir.exists():raise FileExistsError('请使用新版本草稿名，不覆盖 '+str(draftdir))
 project=JyProject(p['name'],width=W,height=H,drafts_root=str(drafts),overwrite=False)
 # The library defaults to 30fps; the draft must share the edit-plan/render clock.
 project.script.content['fps']=float(fps_value(p.get('fps',24)))
 # Preserve requested canvas even when the first asset is a narrow divider.
 project._explicit_res=True
 project.script.content['id']=str(uuid.uuid4()).upper()
 result=[];track_bins={}
 for index,x in enumerate(sorted(p['clips'],key=lambda c:c.get('z',0))):
  start=round(x['start_s']*1e6);dur=round(x['end_s']*1e6)-start;center=x.get('center',[.5,.5]);tx,ty=2*center[0]-1,1-2*center[1];kind=x['kind'];track=f'{index:03}-{x.get("track",x["id"])}'
  if p.get('pack_tracks',False):
   group=(x.get('z',0),kind);bins=track_bins.setdefault(group,[]);chosen=None
   for b in bins:
    if all(start+dur<=lo or start>=hi for lo,hi in b['ranges']):chosen=b;break
   if chosen is None:
    chosen={'name':f'Z{x.get("z",0):04}-{kind}-{len(bins):02}','ranges':[]};bins.append(chosen)
   chosen['ranges'].append((start,start+dur));track=chosen['name']
  scale=1
  if kind in ('image','video'):
   seg=project.add_media_safe(str((base/x['file']).resolve()),start,dur,track,source_start=round(x.get('source_start_s',0)*1e6))
   if seg is None:raise RuntimeError('媒体导入失败 '+x['id'])
   from PIL import Image
   if kind=='image':iw,ih=Image.open(base/x['file']).size
   else:iw,ih=x['media_size']
   size=x.get('size',[1,1]);basefit=min(W/iw,H/ih);scale=(max if x.get('fit')=='cover' else min)(W*size[0]/iw,H*size[1]/ih)/basefit
   if kind=='video':seg.volume=0 if x.get('muted') or x.get('track')=='background' else x.get('volume',0)
   seg.clip_settings=jy.ClipSettings(scale_x=scale,scale_y=scale,transform_x=tx,transform_y=ty,alpha=x.get('alpha',1))
  elif kind=='text':
   clip=jy.ClipSettings(transform_x=tx,transform_y=ty)
   seg=project.add_text_simple(x['text'],start,dur,track,font=getattr(jy.FontType,x['font_name']) if x.get('font_name') else None,style=jy.TextStyle(size=x.get('jianying_font_size',x.get('font_px',46)/8),color=rgb(x.get('color','#151515')),bold=x.get('bold',False),auto_wrapping=x.get('auto_wrapping',False)),clip_settings=clip,border=jy.TextBorder(color=rgb(x.get('stroke_color','#000000')),width=x.get('native_border_width',0)))
  elif kind=='audio':
   seg=project.add_audio_safe(str((base/x['file']).resolve()),start,dur,track);seg.volume=x.get('volume',1)
  elif kind=='sticker':
   if not x.get('verified'):raise ValueError('贴纸未验证 '+x['id'])
   project._ensure_track(jy.TrackType.sticker,track);seg=jy.StickerSegment(x['resource_id'],jy.Timerange(start,dur),clip_settings=jy.ClipSettings(transform_x=tx,transform_y=ty));project.script.add_segment(seg,track)
  else:raise ValueError('不支持kind '+kind)
  for effect in x.get('native_animations',[])+x.get('native_effects',[]):
   enum_type=effect['enum_type']
   allowed={'TextIntro','TextOutro','TextLoopAnim'} if kind=='text' else {'IntroType','OutroType','GroupAnimationType','VideoSceneEffectType','VideoCharacterEffectType'} if kind in ('image','video') else set()
   if enum_type not in allowed:raise ValueError('不支持该层原生效果 '+x['id'])
   member=getattr(getattr(jy,enum_type),effect['name'])
   if str(member.value.resource_id)!=str(effect['resource_id']):raise ValueError('原生效果ID不匹配 '+x['id'])
   if effect.get('validation_status')!='native_verified' and not p.get('native_effect_test_only'):raise ValueError('原生效果尚未验证 '+x['id'])
   if effect.get('validation_status')=='native_verified' and not (base/effect.get('evidence','__missing__')).is_file():raise ValueError('原生效果缺少验证证据 '+x['id'])
   if enum_type=='TextLoopAnim' and x['id'].startswith('SUB-'):raise ValueError('普通字幕禁止循环动画')
   if enum_type.endswith('EffectType'):seg.add_effect(member,params=effect.get('params'))
   else:
    seconds=effect['duration_s']
    if not 0<seconds<=dur/1e6:raise ValueError('原生动画时间越界')
    seg.add_animation(member,duration=round(seconds*1e6))
  native_keys=dict(x.get('keyframes',{}))
  if kind=='image':
   # Explicitly hold both axes: some editor versions do not preserve the static
   # transform consistently once only the other axis has a keyframe channel.
   native_keys.setdefault('position_x',[[0,tx],[dur/1e6,tx]])
   native_keys.setdefault('position_y',[[0,ty],[dur/1e6,ty]])
  for prop,keys in native_keys.items():
   if kind=='text' and prop=='alpha':raise ValueError('文本不支持alpha关键帧，请使用文字动画或分段')
   # Use native linear keyframes; CSS cubic-bezier handles are not a Jianying format.
   keys=list(keys)
   if keys and keys[-1][0]<(dur/1e6)-.000001:keys.append([dur/1e6,keys[-1][1]])
   for t,v in keys:
    if prop=='relative_scale':prop_key=jy.KeyframeProperty.uniform_scale;v=v*scale
    else:prop_key=getattr(jy.KeyframeProperty,prop)
    seg.add_keyframe(prop_key,min(dur,round(t*1e6)),v,curve_type='Line')
  result.append({'clip_id':x['id'],'segment_id':seg.segment_id,'kind':kind,'image_design_id':x.get('image_design_id'),'design_asset_id':x.get('design_asset_id'),'scene_id':x.get('scene_id'),'content_action_ids':x.get('content_action_ids',[]),'layer_id':x.get('layer_id'),'role':x.get('role'),'meme_id':x.get('meme_id'),'sfx_id':x.get('sfx_id'),'track':track,'start_us':start,'duration_us':dur})
 project.save()
 fontpaths={x['font_name']:str((base/x['font_file']).resolve()) for x in p['clips'] if x.get('font_name') and x.get('font_file')}
 for draftfile in [draftdir/'draft_info.json',draftdir/'draft_content.json']:
  if not draftfile.exists():continue
  saved=json.loads(draftfile.read_text())
  # project.save() regenerates content with the library's default fps.
  saved['fps']=float(fps_value(p.get('fps',24)))
  for text in saved.get('materials',{}).get('texts',[]):
   content=json.loads(text.get('content','{}'))
   for style in content.get('styles',[]):
    for name,path in fontpaths.items():
     if str(style.get('font',{}).get('id'))==str(getattr(jy.FontType,name).value.resource_id):
      if not Path(path).is_file():raise FileNotFoundError(path)
      style['font']['path']=path
   text['content']=json.dumps(content,ensure_ascii=False)
  draftfile.write_text(json.dumps(saved,ensure_ascii=False))
 meta_path=draftdir/'draft_meta_info.json'
 if meta_path.exists():
  meta=json.loads(meta_path.read_text());meta.update({'draft_id':project.script.content['id'],'draft_name':p['name'],'draft_fold_path':str(draftdir),'draft_root_path':str(drafts),'tm_duration':round(p['duration_s']*1e6)});meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 actual_layers=sorted({x['layer_id'] for x in result if x.get('layer_id')});missing=set(p.get('required_layer_ids',[]))-set(actual_layers);unresolved=p.get('unresolved',[])+list(missing)
 summary={'plan_sha256':hashlib.sha256(planpath.read_bytes()).hexdigest(),'status':'draft_ready' if not unresolved else 'partial','draft_path':str(draftdir),'duration_s':p['duration_s'],'counts':{k:sum(x['kind']==k for x in result) for k in ['image','video','text','audio','sticker']},'required_layer_ids':p.get('required_layer_ids',[]),'implemented_layer_ids':actual_layers,'meme_count':len({x['meme_id'] for x in result if x.get('meme_id')}),'sfx_count':len({x['sfx_id'] for x in result if x.get('sfx_id')}),'unresolved':unresolved,'segments':result,'timing_status':p.get('timing_status'),'track_count':len(project.script.tracks),'keyframe_curve':'Line','rendered':False,'previewed_in_jianying':False}
 (out/'build-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 # 检查保存后的真实草稿片段数、时长和本地素材路径。
 draftfile=next((f for f in [draftdir/'draft_info.json',draftdir/'draft_content.json'] if f.exists()),None)
 d=json.loads(draftfile.read_text());segments=[s for t in d['tracks'] for s in t.get('segments',[])];assert len(segments)==len(result)
 badpaths=[a['path'] for k in ['videos','audios'] for a in d.get('materials',{}).get(k,[]) if a.get('path') and not Path(a['path']).exists()]
 if badpaths:raise FileNotFoundError(str(badpaths))
 (out/'timeline-check.json').write_text(json.dumps({'saved_draft_segments':len(segments),'expected_segments':len(result),'missing_materials':badpaths,'max_end_us':max(s['target_timerange']['start']+s['target_timerange']['duration'] for s in segments),'word_alignment_verified':False},ensure_ascii=False,indent=2)+'\n')
 print('草稿构建完成',draftdir)
if __name__=='__main__':main()
