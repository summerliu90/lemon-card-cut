"""Shared final subtitle styling and saved native-material verification."""
import hashlib,json
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[2]/'01-shot-list/references/production-profile.json'
def font_family(path):
    from PIL import ImageFont
    return ImageFont.truetype(str(path),16).getname()[0]
def profile():return json.loads(PROFILE.read_text())['subtitle']
def is_subtitle(c):return c.get('role')=='subtitle' or c.get('track','').lower()=='subtitles' or c.get('id','').lower().startswith(('sub-','subtitle-'))
def apply_subtitles(plan,font_file):
    font=Path(font_file).resolve()
    if not font.is_file():raise FileNotFoundError(font)
    if 'WenYue XinQingNianTi' not in font_family(font):raise ValueError('字体文件内容并非新青年体')
    p=profile();scale=plan.get('canvas',[1920,1080])[1]/1080
    plan['subtitle_policy']={**p,'font_file':str(font),'font_sha256':hashlib.sha256(font.read_bytes()).hexdigest()}
    for c in plan['clips']:
        if is_subtitle(c):c.update(role='subtitle',font_name=p['font_name'],font_file=str(font),font_sha256=plan['subtitle_policy']['font_sha256'],jianying_font_size=p['jianying_font_size'],font_px=round(p['preview_font_px']*scale),color=p['color'],stroke_color=p['stroke_color'],stroke_width_px=round(p['stroke_width_px']*scale),native_border_width=p['native_border_width'],auto_wrapping=True)
    return plan

def validate_subtitles(plan,base):
    errors=[];p=profile();subs=[c for c in plan.get('clips',[]) if is_subtitle(c)]
    if plan.get('subtitle_policy') and not subs:errors.append('subtitle policy enabled but no editable subtitle clips')
    for c in subs:
        name=c['id'];f=base/c.get('font_file','__missing__')
        if c.get('kind')!='text':errors.append(name+': subtitle must be editable native text')
        for field in ('font_name','jianying_font_size','color'):
            actual=c.get(field);expected=p[field]
            if field=='color' and isinstance(actual,str):actual=actual.upper()
            if actual!=expected:errors.append(name+': subtitle '+field+' must be '+str(expected))
        if not f.is_file():errors.append(name+': real subtitle font file missing')
        elif not c.get('font_sha256') or hashlib.sha256(f.read_bytes()).hexdigest()!=c['font_sha256']:errors.append(name+': subtitle font checksum missing/stale')
        if f.is_file():
            try:
                if 'WenYue XinQingNianTi' not in font_family(f):errors.append(name+': real font family is not 新青年体')
            except (OSError,ValueError):errors.append(name+': invalid font file')
        expected=round(p['preview_font_px']*plan.get('canvas',[1920,1080])[1]/1080)
        if c.get('font_px')!=expected:errors.append(name+': preview font size differs from subtitle policy')
        if c.get('auto_wrapping') is not True:errors.append(name+': native subtitle material required')
    return errors

def audit_native_subtitles(plan,summary,draft):
    errors=[];p=profile();rows={r['clip_id']:r for r in summary['segments']};segments={s['id']:s for t in draft['tracks'] for s in t.get('segments',[])};texts={m['id']:m for m in draft['materials'].get('texts',[])}
    for c in plan['clips']:
        if not is_subtitle(c):continue
        s=segments.get(rows.get(c['id'],{}).get('segment_id'),{});m=texts.get(s.get('material_id'),{});content=json.loads(m.get('content','{}'));styles=content.get('styles',[])
        if m.get('type')!='subtitle' or content.get('text')!=c['text']:errors.append(c['id']+': saved native subtitle missing/wrong text')
        if len(styles)!=1:errors.append(c['id']+': unexpected subtitle style count');continue
        style=styles[0];font=style.get('font',{})
        if str(font.get('id'))!=p['native_font_resource_id'] or font.get('path')!=str(Path(c['font_file']).resolve()):errors.append(c['id']+': saved native subtitle font differs')
        if abs(style.get('size',-1)-p['jianying_font_size'])>1e-5:errors.append(c['id']+': saved native subtitle size differs')
        color=style.get('fill',{}).get('content',{}).get('solid',{}).get('color',[]);expected=[int(p['color'].lstrip('#')[i:i+2],16)/255 for i in (0,2,4)]
        if len(color)!=3 or any(abs(a-b)>1e-5 for a,b in zip(color,expected)):errors.append(c['id']+': saved native subtitle color differs')
    return errors
