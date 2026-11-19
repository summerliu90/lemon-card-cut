"""Native metadata smoke test; deliberately does not claim app playback validation."""
import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image
from execution_fixture import add_contract

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as folder:
    base = Path(folder)
    Image.new('RGB', (320, 180), 'white').save(base / 'plate.png')
    native = {'enum_type': 'TextIntro', 'name': '冲屏位移', 'resource_id': '7078181271393800711', 'duration_s': .3, 'validation_status': 'unverified'}
    plan = {'name': 'native-metadata-test', 'canvas': [1920, 1080], 'duration_s': 2, 'native_effect_test_only': True, 'clips': [{'id': 'TITLE', 'kind': 'text', 'text': '验证', 'start_s': 0, 'end_s': 2, 'native_animations': [native]}, {'id': 'PLATE', 'kind': 'image', 'file': str(base / 'plate.png'), 'start_s': 0, 'end_s': 2, 'native_effects': [{'enum_type': 'VideoSceneEffectType', 'name': '_1998', 'resource_id': '6981791065204331044', 'validation_status': 'unverified'}]}]}
    style='ivory-diagram'
    item=dict(id='I01',shots=['S01'],trigger_text='验证',learning_goal='示例',diagram_type='concept',visual_style_id=style,route='svg-layout',aspect_ratio=[16,9],target_px=[320,180],content_basis='示意',display={'center':[.5,.5],'size':[.5,.5]},motion_intent='稳定',text_plan='独立标题')
    source={'visual_design':dict(selection_mode='user',visual_style_id=style,selection_reason='测试指定',series_parameters={'paper':'ivory'},image_designs=[item])}
    asset=dict(id='I01',file='plate.png',status='ready',width=320,height=180,visual_style_id=style,route='svg-layout',qa=dict(viewed=True,text_checked=True,structure_checked=True))
    plan['clips'][1]['image_design_id']='I01'
    manifest={'images':[asset]}
    add_contract(source,manifest,plan,base)
    for name,data in [('source.json',source),('assets.json',manifest)]:
        (base/name).write_text(json.dumps(data,ensure_ascii=False))
    plan['visual_inputs']={}
    for key,name in [('presentation_plan','source.json'),('asset_manifest','assets.json')]:
        plan['visual_inputs'][key]=name
        plan['visual_inputs'][key+'_sha256']=hashlib.sha256((base/name).read_bytes()).hexdigest()
    plan['clips'][1].update(image_design_id='I01',size=[.5,.5],center=[.5,.5],reading_window_s=[.4,1.6])
    file = base / 'plan.json'
    file.write_text(json.dumps(plan, ensure_ascii=False))
    env = dict(os.environ, PYTHONPYCACHEPREFIX='/tmp/lemon-pycache')
    def build(destination: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(root / 'scripts/build_video.py'), '--plan', str(file), '--out', str(base / destination)], capture_output=True, text=True, env=env)
    result = build('accepted')
    assert result.returncode == 0, result.stderr
    draft = json.loads(next((base / 'accepted/drafts').glob('*/draft_info.json')).read_text())
    assert draft['materials']['material_animations'], 'Native animation was silently dropped'
    assert draft['materials']['video_effects'], 'Native effect was silently dropped'
    native['resource_id'] = 'wrong-id'
    file.write_text(json.dumps(plan, ensure_ascii=False))
    assert build('bad-id').returncode != 0, 'Wrong native ID accepted'
    native['resource_id'] = '7078181271393800711'
    plan['native_effect_test_only'] = False
    file.write_text(json.dumps(plan, ensure_ascii=False))
    assert build('unverified-production').returncode != 0, 'Unverified native production accepted'
    result = subprocess.run([sys.executable, str(root / 'scripts/render_preview.py'), '--plan', str(file), '--output', str(base / 'unexpected.mp4')], capture_output=True, text=True, env=env)
    assert result.returncode != 0 and not (base / 'unexpected.mp4').exists(), 'Native effect was silently omitted in MP4'
print('PASS: native metadata exported; wrong IDs, unverified production, and silent MP4 omission rejected. App playback remains unverified.')
