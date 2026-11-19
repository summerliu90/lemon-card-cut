import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).parents[2]/'04-video-cut/tests'))
from validate_execution import validate
from execution_fixture import add_contract

class ExecutionTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        (self.base/'image.png').write_bytes(b'actual asset hash fixture')
        self.source={};self.manifest={};self.edit={'duration_s':12,'clips':[dict(id='C01',image_design_id='I01',file='image.png')]}
        add_contract(self.source,self.manifest,self.edit,self.base)
    def tearDown(self):self.temp.cleanup()
    def check(self):return validate(self.source,self.base,'04',self.manifest,self.base,self.edit,self.base)
    def test_valid_pilot(self):self.assertEqual(self.check(),[])
    def test_missing_contract(self):self.assertTrue(validate({},self.base))
    def test_asset_downgrade(self):
        self.manifest['execution_assets'][0]['type']='native_shape';self.assertTrue(self.check())
    def test_missing_clip(self):self.edit['clips']=[];self.assertTrue(self.check())
    def test_changed_file(self):
        (self.base/'image.png').write_bytes(b'changed');self.assertTrue(self.check())
    def test_missing_action(self):
        self.edit['clips'][0]['content_action_ids']=[];self.assertTrue(self.check())
    def test_action_id_without_keyframes_rejected(self):
        self.edit['clips'][0]['keyframes']={};self.assertTrue(self.check())
    def test_wrong_keyframe_value_rejected(self):
        self.edit['clips'][0]['keyframes']['alpha'][-1][1]=.5;self.assertTrue(self.check())
    def test_wrong_keyframe_time_rejected(self):
        self.edit['clips'][0]['keyframes']['alpha'][-1][0]=2;self.assertTrue(self.check())
    def test_wrong_keyframe_property_rejected(self):
        self.edit['clips'][0]['keyframes']={'position_x':[[0,0],[1.2,1]]};self.assertTrue(self.check())
    def test_missing_character_reference(self):
        self.source['execution_contract']['character']={'mode':'xiaohei'};self.assertTrue(self.check())
    def test_no_final_without_pilot(self):
        self.edit['execution_phase']='final';self.assertTrue(self.check())
    def test_real_pilot_hash_required(self):
        self.edit.update(execution_phase='final',pilot_review_file='review.json')
        report=dict(source_sha256=hashlib.sha256(json.dumps(self.source,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),scene_ids=['S01'],accepted=True,reviewer='test',notes='Synthetic structural fixture only')
        for k in ('video','render_summary'):
            f=self.base/(k+'.data');f.write_bytes(b'evidence');report[k]=f.name;report[k+'_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
        (self.base/'review.json').write_text(json.dumps(report));self.assertEqual(self.check(),[])
        (self.base/report['video']).write_bytes(b'stale');self.assertTrue(self.check())
    def test_wallpaper_and_global_insert_style_rejected(self):
        self.source['execution_contract']['background_policy']='static_image';self.source['execution_contract']['insert_style_scope']='whole_video';self.assertTrue(self.check())
    def test_missing_object_layout(self):
        self.source['execution_contract']['scenes'][0].pop('objects');self.assertTrue(self.check())
    def test_missing_concrete_action(self):
        self.source['execution_contract']['scenes'][0]['action_specs']=[];self.assertTrue(self.check())
    def test_unknown_action_object(self):
        self.source['execution_contract']['scenes'][0]['action_specs'][0]['object_id']='invented';self.assertTrue(self.check())
    def test_action_no_change(self):
        self.source['execution_contract']['scenes'][0]['action_specs'][0]['to']=0;self.assertTrue(self.check())
    def test_action_outside_scene(self):
        self.source['execution_contract']['scenes'][0]['action_specs'][0]['duration_s']=20;self.assertTrue(self.check())
    def test_wrong_narration(self):
        self.source['execution_contract']['scenes'][0]['narration_excerpt']='invented';self.assertTrue(self.check())
    def test_missing_exact_text(self):
        self.source['execution_contract']['scenes'][0]['objects'][0].pop('text');self.assertTrue(self.check())
    def test_carried_object_needs_destination(self):
        self.source['execution_contract']['scenes'][0]['objects'][0]['exit_policy']='carry';self.assertTrue(self.check())
if __name__=='__main__':unittest.main()
