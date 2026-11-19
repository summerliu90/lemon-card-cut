from pathlib import Path
import re,json
r=Path(__file__).resolve().parents[2]
broken=[];count=0
for p in sorted(r.rglob('*.md')):
 s=re.sub(r'```.*?```','',p.read_text(),flags=re.S)
 for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',s):
  target=target.strip('<>');target=target.split('#')[0]
  if not target or '://' in target or target.startswith('mailto:'):continue
  count+=1
  if not (p.parent/target).exists():broken.append([str(p.relative_to(r)),target])
print(json.dumps({'markdown_files':len(list(r.rglob('*.md'))),'local_links':count,'broken':broken},ensure_ascii=False,indent=2))

raise SystemExit(bool(broken))
