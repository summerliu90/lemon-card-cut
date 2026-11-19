import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from audit_text_motion import audit_text_motion


class NativeTextMotionTest(unittest.TestCase):
    def setUp(self):
        self.plan = {'clips': [dict(id='T1', kind='text', text='title', keyframes={'uniform_scale': [[0,.8],[.4,1]]})]}
        self.summary = {'segments': [dict(clip_id='T1', segment_id='S1')]}
        self.draft = {'tracks': [{'segments': [dict(id='S1', common_keyframes=[dict(property_type='KFTypeScaleX', keyframe_list=[
            dict(time_offset=0, values=[.8], curveType='Line'), dict(time_offset=400000, values=[1], curveType='Line')])])]}]}
    def check(self):
        return audit_text_motion(self.plan, Path('.'), self.summary, self.draft)
    def test_valid(self):
        self.assertEqual(self.check(), [])
    def test_removed_native_motion(self):
        self.draft['tracks'][0]['segments'][0]['common_keyframes']=[]
        self.assertTrue(self.check())
    def test_wrong_value_with_same_motion_count(self):
        self.draft['tracks'][0]['segments'][0]['common_keyframes'][0]['keyframe_list'][1]['values']=[1.4]
        self.assertTrue(self.check())
    def test_mapping_cannot_point_to_other_segment(self):
        self.summary['segments'][0]['segment_id']='other'
        self.assertTrue(self.check())
    def test_wrong_native_time(self):
        self.draft['tracks'][0]['segments'][0]['common_keyframes'][0]['keyframe_list'][1]['time_offset']=500000
        self.assertTrue(self.check())
    def test_unverified_curve(self):
        self.draft['tracks'][0]['segments'][0]['common_keyframes'][0]['keyframe_list'][1]['curveType']='Bezier'
        self.assertTrue(self.check())

if __name__ == '__main__':
    unittest.main()
