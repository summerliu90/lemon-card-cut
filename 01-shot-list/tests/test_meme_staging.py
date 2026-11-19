import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from validate_meme_staging import validate
class MemeStagingTest(unittest.TestCase):
 def setUp(self):
  slot=dict(id='M01',scene_id='S01',trigger_text='问题',intent='疑问',placement='center_takeover',center=[.5,.46],size_px=[512,512],hold_s=2.5,context_handling='已读对象退后，保留字幕',start_s=0,end_s=3,required=True)
  self.source=dict(canvas=[1920,1080],narration_text='问题',meme_policy={'enabled':True,'required_count':1},meme_slots=[slot],execution_contract={'scenes':[dict(id='S01',start_s=0,end_s=3,asset_requirements=[{'id':'M01'}])],'pilot_scene_ids':['S01']})
  self.edit=dict(execution_phase='final',clips=[dict(meme_id='M01',design_asset_id='M01',center=[.5,.46],size=[512/1920,512/1080],start_s=0,end_s=3,display_scale_applied=1)])
 def test_exact_layout(self):self.assertEqual(validate(self.source,self.edit),[])
 def test_small_requires_reason(self):
  self.source['meme_slots'][0]['size_px']=[190,190];self.assertTrue(validate(self.source))
 def test_missing_slots_not_excused_by_reason(self):
  self.source['meme_slots']=[];self.source['shortfall_reason']='character used instead';self.assertTrue(validate(self.source))
 def test_runtime_shrink_rejected(self):
  self.edit['clips'][0]['size']=[.1,.15];self.assertTrue(validate(self.source,self.edit))
 def test_runtime_corner_replacement_rejected(self):
  self.edit['clips'][0]['center']=[.9,.7];self.assertTrue(validate(self.source,self.edit))
 def test_double_scale_rejected(self):
  self.edit['clips'][0]['display_scale_applied']=1.3;self.assertTrue(validate(self.source,self.edit))
 def test_missing_required_scene_asset(self):
  self.source['execution_contract']['scenes'][0]['asset_requirements']=[];self.assertTrue(validate(self.source))
if __name__=='__main__':unittest.main()
