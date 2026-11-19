import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1] / "scripts"))
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('validator', Path(__file__).parents[1] / 'scripts/validate_plan.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        beat = {'id': 'V01', 'start_s': 0, 'end_s': 4, 'composition_id': 'fan', 'focus_id': 'papers', 'change_reason': 'papers to comparison', 'trigger_text': '原文', 'selection_reason': '对照关系', 'layout': 'fan', 'motion_ref': None, 'origin': 'original', 'motion_events': [{'layer_id': 'L01', 'phase': 'enter', 'start_s': 0, 'duration_s': .3, 'property': 'alpha', 'from': 0, 'to': 1}], 'asset_requirements': [{'id': 'L01'}], 'implementation_route': 'keyframes', 'validation_status': 'unverified'}
        self.plan = {'duration_s': 4, 'narration_text': '原文', 'visual_beats': [beat]}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_original_valid(self) -> None:
        self.assertEqual(module.validate(self.plan, self.base), [])

    def test_long_scene_allowed_and_false_cut_rejected(self) -> None:
        self.plan['visual_beats'][0]['end_s'] = 7
        self.plan['duration_s'] = 7
        self.assertEqual(module.validate(self.plan, self.base), [])
        self.plan['visual_beats'][0]['end_s'] = 4
        self.plan['duration_s'] = 4
        second = copy.deepcopy(self.plan['visual_beats'][0])
        second.update(id='V02', start_s=4, end_s=8)
        self.plan['visual_beats'].append(second)
        self.plan['duration_s'] = 8
        self.assertTrue(any('重复构图' in x for x in module.validate(self.plan, self.base)))

    def test_pinned_reference_and_tampering(self) -> None:
        recipe = self.base / 'recipe.json'
        recipe.write_text('{}')
        ref = {'id': 'learned-01', 'version': 1, 'recipe_sha256': hashlib.sha256(recipe.read_bytes()).hexdigest(), 'recipe_file': str(recipe)}
        (self.base / 'motion-library-snapshot.json').write_text(json.dumps({'candidates': [{'motion_id': ref['id'], 'version': 1, 'recipe_sha256': ref['recipe_sha256'], 'recipe_file': str(recipe)}]}))
        self.plan['visual_beats'][0]['motion_ref'] = ref
        self.assertEqual(module.validate(self.plan, self.base), [])
        recipe.write_text('{"changed":true}')
        self.assertTrue(any('哈希' in x for x in module.validate(self.plan, self.base)))

    def test_verified_requires_evidence(self) -> None:
        self.plan['visual_beats'][0]['validation_status'] = 'render_verified'
        self.assertTrue(any('证据' in x for x in module.validate(self.plan, self.base)))


if __name__ == '__main__':
    unittest.main()
