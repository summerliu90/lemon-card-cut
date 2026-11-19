"""Pixel geometry is final, aspect-preserved, and never silently shrunk or multiplied twice."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from apply_presentation import resolve_meme_geometry
class MemeGeometryTest(unittest.TestCase):
 def test_final_pixels_take_priority_over_legacy_base(self):
  center,size,scale,mode=resolve_meme_geometry({'size_px':[512,512],'base_size':[.1,.14]},[1920,1080])
  self.assertEqual(center,[.5,.5]);self.assertAlmostEqual(size[0]*1920,512,5);self.assertAlmostEqual(size[1]*1080,512,5);self.assertEqual(scale,1)
 def test_normalized_size_is_final(self):
  self.assertEqual(resolve_meme_geometry({'size':[.3,.5]},[1920,1080])[1],[.3,.5])
 def test_legacy_is_explicitly_distinguished(self):
  center,size,scale,mode=resolve_meme_geometry({'base_size':[.1,.14]},[1920,1080]);self.assertEqual(scale,1.3);self.assertEqual(mode,'legacy_base_size');self.assertEqual(size,[.13,.182])
 def test_default_is_visible_512_square(self):
  center,size,scale,mode=resolve_meme_geometry({},[1920,1080]);self.assertAlmostEqual(size[0]*1920,512,5);self.assertAlmostEqual(size[1]*1080,512,5)
 def test_small_canvas_default_fits(self):
  self.assertEqual(resolve_meme_geometry({},[320,180])[1],[.45,.8])
 def test_bad_corner_layout_is_not_silently_shrunk(self):
  with self.assertRaises(ValueError):resolve_meme_geometry({'size_px':[512,512],'center':[.94,.8]},[1920,1080])
 def test_fullscreen_and_nonfinite_rejected(self):
  for size in [[1,1],[float('nan'),.5]]:
   with self.assertRaises(ValueError):resolve_meme_geometry({'size':size},[1920,1080])
if __name__=='__main__':unittest.main()
