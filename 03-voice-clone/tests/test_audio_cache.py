import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_voiceover import audio_input_digest
class Cache(unittest.TestCase):
 def test_authorization_does_not_resynthesize(self):
  settings={'voice_id':'approved_voice','speed':1.2};self.assertEqual(audio_input_digest('正文',settings),audio_input_digest('正文',{**settings,'authorization':{'date':'2026-10-27'}}))
 def test_audio_changes_do_resynthesize(self):
  settings={'voice_id':'approved_voice','speed':1.2};old=audio_input_digest('正文',settings)
  self.assertNotEqual(old,audio_input_digest('新正文',settings));self.assertNotEqual(old,audio_input_digest('正文',{**settings,'speed':1.3}));self.assertNotEqual(old,audio_input_digest('正文',{**settings,'voice_id':'other'}))
if __name__=='__main__':unittest.main()
