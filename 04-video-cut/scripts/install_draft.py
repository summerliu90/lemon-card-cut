#!/usr/bin/env python3
"""将项目草稿复制并登记到本机剪映草稿库；备份索引、不覆盖同名草稿。"""
import argparse,json,shutil,hashlib,time,uuid,subprocess
from pathlib import Path

def rewrite(value,old,new):
 if isinstance(value,str):return new+value[len(old):] if value.startswith(old) else value
 if isinstance(value,list):return [rewrite(x,old,new) for x in value]
 if isinstance(value,dict):return {k:rewrite(v,old,new) for k,v in value.items()}
 return value

def install(source,root,report,cover=None):
 source=source.resolve();root=root.resolve();indexfile=root/'root_meta_info.json';before=indexfile.read_bytes();index=json.loads(before);name=source.name;dest=root/name
 infofile=source/'draft_info.json'
 if not infofile.exists():infofile=source/'draft_content.json'
 info=json.loads(infofile.read_text());meta=json.loads((source/'draft_meta_info.json').read_text());draftid=info.get('id') or meta['draft_id'];duration=info.get('duration',0)
 if not duration or not info.get('tracks'):raise ValueError('草稿时间线为空')
 if dest.exists():raise FileExistsError('已存在同名系统草稿，不覆盖：'+str(dest))
 if any(x.get('draft_id')==draftid for x in index.get('all_draft_store',[])):raise ValueError('同一draft_id已经登记，不重复安装')
 now=time.time_ns()//1000;backups=report.parent/'install-backups';backups.mkdir(parents=True,exist_ok=True);backup=backups/f'root_meta_info-{now}.json';backup.write_bytes(before)
 staging=root/('.'+name+'-install-'+uuid.uuid4().hex[:8]);shutil.copytree(source,staging)
 for p in staging.glob('*.json'):
  d=rewrite(json.loads(p.read_text()),str(source),str(dest));p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 info=json.loads((staging/infofile.name).read_text());info['name']=name;(staging/infofile.name).write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
 if cover:shutil.copy2(cover,staging/'draft_cover.jpg')
 meta=rewrite(meta,str(source),str(dest));meta.update({'draft_id':draftid,'draft_name':name,'draft_root_path':str(root),'draft_fold_path':str(dest),'draft_json_file':str(dest/infofile.name),'draft_cover':str(dest/'draft_cover.jpg') if cover else '', 'tm_duration':duration,'tm_draft_create':now,'tm_draft_modified':now,'tm_draft_removed':0,'draft_is_invisible':False})
 (staging/'draft_meta_info.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 # The copied draft must resolve every media file inside itself after relocation.
 missing=[]
 for group in ['videos','audios']:
  for m in info.get('materials',{}).get(group,[]):
   if not m.get('path'):continue
   path=Path(m['path']);check=staging/path.relative_to(dest) if path.is_relative_to(dest) else path
   if not check.is_file():missing.append(str(path))
 if missing:raise FileNotFoundError('复制后素材丢失：'+str(missing))
 if indexfile.read_bytes()!=before:raise RuntimeError('剪映索引发生并发修改，停止登记；原索引未覆盖，请重新读取后重试')
 staging.rename(dest)
 entry={k:v for k,v in meta.items() if k not in ['draft_materials','draft_materials_copied_info','draft_segment_extra_info']};entry.update({'cloud_draft_cover':False,'cloud_draft_sync':False,'streaming_edit_draft_ready':True,'draft_timeline_materials_size':sum(p.stat().st_size for p in (dest/'materials').glob('*') if p.is_file())})
 index.setdefault('all_draft_store',[]).insert(0,entry)
 # draft_ids is an app counter on this host, not a list of UUIDs.
 if isinstance(index.get('draft_ids'),int):index['draft_ids']+=1
 elif isinstance(index.get('draft_ids'),list):index['draft_ids'].append(draftid)
 index['root_path']=str(root);tmp=indexfile.with_name('root_meta_info.install.tmp');tmp.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n');tmp.replace(indexfile)
 actual=json.loads(indexfile.read_text());assert any(x.get('draft_id')==draftid and x.get('draft_name')==name for x in actual['all_draft_store'])
 result={'status':'registered_in_local_jianying_library','draft_name':name,'draft_id':draftid,'installed_path':str(dest),'index_path':str(indexfile),'index_backup':str(backup.resolve()),'duration_us':duration,'canvas':info.get('canvas_config'),'segments':sum(len(t.get('segments',[])) for t in info['tracks']),'missing_materials':missing,'ui_verified':False};report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--source',type=Path,required=True);a.add_argument('--root',type=Path,required=True);a.add_argument('--report',type=Path,required=True);a.add_argument('--cover',type=Path);args=a.parse_args();print(json.dumps(install(args.source,args.root,args.report,args.cover),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
