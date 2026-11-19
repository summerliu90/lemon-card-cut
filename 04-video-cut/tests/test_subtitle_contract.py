import copy,json,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from subtitle_contract import apply_subtitles,validate_subtitles,audit_native_subtitles
class SubtitleContract(unittest.TestCase):
 def setUp(self):
  self.font_mock=patch('subtitle_contract.font_family',return_value='WenYue XinQingNianTi (Non-Commercial Use)');self.font_mock.start()
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.font=self.root/'font.ttf';self.font.write_bytes(b'font-fixture');self.p={'canvas':[1920,1080],'clips':[dict(id='SUB-1',kind='text',text='字幕',track='Subtitles')]};apply_subtitles(self.p,self.font)
 def tearDown(self):self.temp.cleanup();self.font_mock.stop()
 def test_final_style(self):
  self.assertEqual(validate_subtitles(self.p,self.root),[]);c=self.p['clips'][0];self.assertEqual((c['jianying_font_size'],c['font_px'],c['color']),(7,56,'#FFDE00'))
 def test_wrong_size_font_color_rejected(self):
  for k,v in [('font_name','黑体'),('jianying_font_size',5),('color','#20262B'),('kind','image'),('auto_wrapping',False)]:
   p=copy.deepcopy(self.p);p['clips'][0][k]=v;self.assertTrue(validate_subtitles(p,self.root),k)
 def test_font_changed_rejected(self):
  self.font.write_bytes(b'other');self.assertTrue(validate_subtitles(self.p,self.root))
 def test_black_font_with_correct_label_rejected(self):
  with patch('subtitle_contract.font_family',return_value='Heiti'):
   self.assertTrue(validate_subtitles(self.p,self.root))
   with self.assertRaises(ValueError):apply_subtitles(self.p,self.font)
 def test_saved_material_audit(self):
  c=self.p['clips'][0];summary={'segments':[dict(clip_id='SUB-1',segment_id='s')]};style={'font':{'id':'6740435892441190919','path':str(self.font.resolve())},'size':7,'fill':{'content':{'solid':{'color':[1,222/255,0]}}}};m={'id':'m','type':'subtitle','content':json.dumps({'text':'字幕','styles':[style]})};d={'tracks':[{'segments':[dict(id='s',material_id='m')]}],'materials':{'texts':[m]}}
  self.assertEqual(audit_native_subtitles(self.p,summary,d),[]);m['type']='text';self.assertTrue(audit_native_subtitles(self.p,summary,d));m['type']='subtitle';style['size']=5;m['content']=json.dumps({'text':'字幕','styles':[style]});self.assertTrue(audit_native_subtitles(self.p,summary,d))
if __name__=='__main__':unittest.main()
