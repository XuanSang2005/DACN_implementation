"""LAYOUT-01: exercise real argument parsers without launching product suites."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


WORKSPACE = Path(__file__).resolve().parents[2]


class PackageWrappers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dacn-wrapper-regression-')
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        self.report = self.cwd / 'report'

    def invoke(self, script, arguments):
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        return subprocess.run(
            [sys.executable, '-B', str(WORKSPACE / script), *arguments],
            cwd=self.cwd, env=env, capture_output=True, text=True, timeout=10,
        )

    def required(self, tool):
        args = ['--report-dir', str(self.report)]
        if tool == 'collect_evidence':
            args += ['--wheel-dir', str(self.cwd)]
        return args

    def assert_rejected(self, result):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('unrecognized arguments:', result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertFalse(self.report.exists(), 'Rejected selector created a report')
        self.assertEqual(list(self.cwd.iterdir()), [], 'Rejected selector wrote output')

    def test_wrapper_help_omits_selector(self):
        for package in ('s01', 's02'):
            for tool in ('run_checks', 'collect_evidence'):
                with self.subTest(package=package, tool=tool):
                    result = self.invoke(f'packages/{package}/tools/{tool}.py', ['--help'])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('--report-dir', result.stdout)
                    self.assertNotIn('--package', result.stdout)
                    self.assertFalse(self.report.exists())

    def test_workspace_help_retains_selector(self):
        for tool in ('run_checks', 'collect_evidence'):
            with self.subTest(tool=tool):
                result = self.invoke(f'tools/{tool}.py', ['--help'])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('--package {s01,s02,all}', result.stdout)

    def test_workspace_rejects_abbreviation(self):
        for tool in ('run_checks', 'collect_evidence'):
            with self.subTest(tool=tool):
                self.assert_rejected(self.invoke(
                    f'tools/{tool}.py',
                    ['--package', 's01', *self.required(tool), '--pack=s02'],
                ))


def selector_case(package, tool, option, value, equals, first):
    def test(self):
        selector = [f'{option}={value}'] if equals else [option, value]
        required = self.required(tool)
        args = selector + required if first else required + selector
        self.assert_rejected(self.invoke(f'packages/{package}/tools/{tool}.py', args))
    return test


# All prefixes accepted by argparse abbreviation before the fix, both spellings,
# either position, and every workspace selector value (including the same package).
for package in ('s01', 's02'):
    for tool in ('run_checks', 'collect_evidence'):
        for length in range(1, len('package') + 1):
            option = '--' + 'package'[:length]
            for value in ('s01', 's02', 'all'):
                for equals in (False, True):
                    for first in (False, True):
                        name = f'test_{package}_{tool}_{option[2:]}_{value}_{"equals" if equals else "split"}_{"first" if first else "last"}'
                        setattr(PackageWrappers, name, selector_case(package, tool, option, value, equals, first))


if __name__ == '__main__':
    unittest.main()
