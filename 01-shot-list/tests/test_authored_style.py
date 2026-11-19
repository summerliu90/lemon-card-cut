import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from validate_visual_design import validate


class AuthoredStyleTest(unittest.TestCase):
    def setUp(self):
        item = dict(id='I01', shots=['S01'], trigger_text='request', learning_goal='explain dependency',
                    diagram_type='object', visual_style_id='custom-clay', route='imagegen',
                    aspect_ratio=[2,3], target_px=[1024,1536], content_basis='illustration',
                    display={'center':[.3,.5],'size':[.3,.5]}, motion_intent='enter then hold', text_plan='separate labels')
        self.plan = {'visual_design':dict(selection_mode='authored_per_asset', visual_style_id='custom-clay',
            selection_reason='specific dependency object', series_parameters={'accent':'blue'}, image_designs=[item],
            authored_treatments={'custom-clay':dict(medium='clay',palette='blue and amber',semantic_reason='access dependency',reference_policy='original local asset')})}
    def test_explicit_authored_style(self):
        self.assertEqual(validate(self.plan, '01'), [])
    def test_incomplete_declaration(self):
        self.plan['visual_design']['authored_treatments']['custom-clay'].pop('palette')
        self.assertTrue(validate(self.plan, '01'))
    def test_each_image_needs_its_own_declared_style(self):
        self.plan['visual_design']['image_designs'][0]['visual_style_id']='undeclared'
        self.assertTrue(validate(self.plan, '01'))
    def test_user_mode_still_rejects_unknown_catalog_style(self):
        self.plan['visual_design']['selection_mode']='user'
        self.assertTrue(validate(self.plan, '01'))

if __name__ == '__main__':
    unittest.main()
