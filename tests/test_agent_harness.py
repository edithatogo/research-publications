import contextlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts.agent_harness import check_unittest_layout, commands, load_config, public_file, run_checks


class HarnessTests(unittest.TestCase):
    def test_standalone_cases_cannot_silently_disappear_from_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_retained.py').write_text(
                'def test_replay():\n    assert False\n'
                'async def test_preservation():\n    assert False\n')
            with self.assertRaisesRegex(ValueError, 'test_retained.py:1:test_replay.*test_preservation'):
                check_unittest_layout(root)

    def test_case_methods_and_support_functions_remain_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_retained.py').write_text(
                'import unittest\ndef fixture():\n    return {}\n'
                'class Cases(unittest.TestCase):\n'
                '    def test_replay(self):\n        self.assertEqual(fixture(), {})\n')
            check_unittest_layout(root)

    def test_failure_survives_later_success_and_all_checks_run(self):
        seen = []
        def runner(command, **kwargs):
            seen.append(command)
            return SimpleNamespace(returncode=1 if len(seen) == 1 else 0)
        with contextlib.redirect_stdout(io.StringIO()):
            result = run_checks([['first'], ['second'], ['third']], runner)
        self.assertEqual(result, 1)
        self.assertEqual(len(seen), 3)

    def test_context_rejects_private_and_escaping_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ['private/receipt.json', '../secret', 'downloads/raw.json']:
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    public_file(root, relative)

    def test_all_route_includes_required_checks(self):
        checks = commands(load_config(), 'all')
        self.assertEqual(len(checks), 6)
        self.assertIn('scripts/validate_project.py', checks[1])
        self.assertIn('scripts/webfirst_contracts.py', checks[2])
        self.assertIn('scripts/validate_conductor.py', checks[3])
        self.assertIn('scripts/powerplatform_tooling.py', checks[4])
        self.assertIn('tests/test_m365_qualified.mjs', checks[5])
        self.assertEqual(checks[5][:2], ['node', '--test'])
