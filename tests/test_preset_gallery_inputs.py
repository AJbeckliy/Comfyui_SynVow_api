"""Offline gallery reference-input tests; no network, auth or GPU required."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class GalleryReferencesTest(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'py/preset_gallery/preset_gallery.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PresetGallery')
        self.tasks = Mock(return_value=['offline-result'])
        self.scope = {
            '_OPTS': ['测试预设'], '_PROMPT': {'测试预设': '/test 测试预设', '測試預設': '/test 测试预设'},
            '_g': SimpleNamespace(_param_inputs=lambda: {}, _prep_model=lambda *a: ('model', 'style', 'auto', '1K', '1:1'), _run_tasks=self.tasks),
            'synvow_auth': SimpleNamespace(read_api_key=lambda: 'offline', refresh_balance=lambda: None),
            'stack_image_tensors': lambda *a, **kw: 'image-result',
        }
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(source), 'exec'), self.scope)
        self.node = self.scope['PresetGallery']()

    def test_eight_optional_slots_without_role_fields(self):
        optional = self.node.INPUT_TYPES()['optional']
        self.assertEqual(list(optional), [f'image_{i}' for i in range(1, 9)])
        self.assertTrue(all(value == ('IMAGE',) for value in optional.values()))

    def test_zero_one_two_three_eight_in_order(self):
        for count in (0, 1, 2, 3, 8):
            with self.subTest(count=count):
                images = [object() for _ in range(count)]
                result = self.node.run('测试预设', **{f'image_{i+1}': value for i, value in enumerate(images)})
                args = self.tasks.call_args.args
                self.assertEqual(args[0], [('/test 测试预设', images)])
                self.assertEqual(args[5], bool(count))
                self.assertEqual(result, ('image-result', '/test 测试预设'))

    def test_sparse_slots_keep_order(self):
        first, third, eighth = object(), object(), object()
        self.node.run('测试预设', image_8=eighth, image_3=third, image_1=first)
        self.assertEqual(self.tasks.call_args.args[0][0][1], [first, third, eighth])

    def test_legacy_two_image_call(self):
        first, second = object(), object()
        self.node.run('测试预设', None, None, None, None, None, False, 0, first, second)
        self.assertEqual(self.tasks.call_args.args[0][0][1], [first, second])

    def test_alias_validation_preserved(self):
        self.assertIs(self.node.VALIDATE_INPUTS('測試預設'), True)
        self.assertIsNot(self.node.VALIDATE_INPUTS('不存在'), True)

    def test_generation_failure_still_raises(self):
        self.tasks.return_value = []
        with self.assertRaises(RuntimeError):
            self.node.run('测试预设')


if __name__ == '__main__':
    unittest.main()
