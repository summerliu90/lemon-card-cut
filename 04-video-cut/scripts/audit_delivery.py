#!/usr/bin/env python3
"""检查真实MP4、保存的草稿片段与执行计划，生成飞书finish所需交付凭据。"""
import argparse,json,subprocess,hashlib
from pathlib import Path
from visual_gate import audit_evidence
from frame_contract import verify_backgrounds

def audit(project,planpath,mp4,draft,summarypath):
 task=json.loads((project/'00-feishu-source/task.json').read_text());p=json.loads(planpath.read_text());summary=json.loads(summarypath.read_text());problems=[]
 digest=hashlib.sha256(planpath.read_bytes()).hexdigest();render=json.loads((mp4.parent/'render-check.json').read_text())
 if render.get('plan_sha256')!=digest or summary.get('plan_sha256')!=digest:problems.append('render_or_draft_plan_hash_mismatch')
 if render.get('output_sha256')!=hashlib.sha256(mp4.read_bytes()).hexdigest():problems.append('rendered_output_hash_mismatch')
 if p.get('input_sha256')!=task['input_sha256']:problems.append('source_hash_mismatch')
 if p.get('style_id')!=task['style']:problems.append('style_mismatch')
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(mp4)],text=True));vs=[x for x in probe['streams'] if x['codec_type']=='video'];aus=[x for x in probe['streams'] if x['codec_type']=='audio']
 if not vs or not aus:problems.append('missing_video_or_audio_stream')
 if vs and [vs[0]['width'],vs[0]['height']]!=p['canvas']:problems.append('canvas_mismatch')
 if abs(float(probe['format']['duration'])-p['duration_s'])>.15:problems.append('duration_mismatch')
 df=next((x for x in [draft/'draft_info.json',draft/'draft_content.json'] if x.exists()),None)
 if df is None:raise ValueError('缺少真实草稿文件')
 d=json.loads(df.read_text());segments={s['id']:s for t in d['tracks'] for s in t.get('segments',[])}
 mapping={x['clip_id']:x for x in summary['segments']}
 for x in p['clips']:
  if x['id'] not in mapping or mapping[x['id']]['segment_id'] not in segments:problems.append('missing_segment_'+x['id'])
  if x.get('file') and not (planpath.parent/x['file']).is_file():problems.append('missing_media_'+x['id'])
 for group in ['videos','audios']:
  for m in d.get('materials',{}).get(group,[]):
   if m.get('path') and not Path(m['path']).exists():problems.append('draft_missing_media')
 memes=[x for x in p['clips'] if x.get('meme_id')]
 if not task['meme_policy']['enabled'] and memes:problems.append('memes_in_character_free_mode')
 for x in memes:
  real=segments.get(mapping.get(x['id'],{}).get('segment_id'),{})
  if not real.get('common_keyframes'):problems.append('missing_meme_motion_'+x['id'])
 report=p.get('presentation_report',{})
 if len(memes)<task['meme_policy']['target_count'] and not report.get('shortfall_reason'):problems.append('unexplained_meme_shortfall')
 if task['background'].get('mode')=='loop-video':
  b=[x for x in p['clips'] if x.get('track')=='background']
  if len(b)!=1 or b[0]['kind']!='video' or b[0]['start_s']!=0 or b[0]['end_s']<p['duration_s']:problems.append('background_coverage_incomplete')
  elif segments.get(mapping.get(b[0]['id'],{}).get('segment_id'),{}).get('volume',0)!=0:problems.append('background_not_muted')
 try:
  verify_backgrounds(p,planpath.parent,p.get('fps',24))
  problems+=audit_evidence(p,planpath.parent,summary,d,mp4)
 except (ValueError,OSError,KeyError,TypeError) as exc:problems.append('visual_gate: '+str(exc))
 problems+=summary.get('unresolved',[])
 problems+=p.get('unresolved',[])
 result={'schema_version':1,'input_sha256':task['input_sha256'],'mp4':str(mp4.relative_to(project)),'draft':str(draft.relative_to(project)),'plan':str(planpath.relative_to(project)),'build_summary':str(summarypath.relative_to(project)),'unresolved':sorted(set(problems)),'meme_count':len(memes),'target_count':task['meme_policy']['target_count'],'shortfall_reason':report.get('shortfall_reason'),'actual_draft_segments':len(segments),'audio_listened':False,'previewed_in_jianying':False}
 return result

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--project',type=Path,required=True);a.add_argument('--plan',type=Path,required=True);a.add_argument('--mp4',type=Path,required=True);a.add_argument('--draft',type=Path,required=True);a.add_argument('--build-summary',type=Path,required=True);args=a.parse_args();project=args.project.resolve()
 for f in [args.plan,args.mp4,args.draft,args.build_summary]:
  if not f.resolve().is_relative_to(project):raise ValueError('交付文件必须位于项目内')
 result=audit(project,args.plan.resolve(),args.mp4.resolve(),args.draft.resolve(),args.build_summary.resolve());out=project/'04-video-cut/delivery.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
 if result['unresolved']:raise SystemExit(1)
if __name__=='__main__':main()
