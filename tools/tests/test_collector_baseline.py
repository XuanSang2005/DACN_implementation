"""Collector version-boundary tests with synthetic wheel bytes, no product imports."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

spec=importlib.util.spec_from_file_location('collector',Path(__file__).resolve().parents[1]/'collect_evidence.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


class BaselineComparison(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def wheel(self,name,version,files,distribution='dacn-s02'):
        path=self.root/name
        with ZipFile(path,'w') as z:
            for key,data in files.items():z.writestr('dacn_s02/'+key,data)
            z.writestr(f'dacn_s02-{version}.dist-info/METADATA',f'Name: {distribution}\nVersion: {version}\n')
            z.writestr(f'dacn_s02-{version}.dist-info/WHEEL','Wheel-Version: 1.0\n')
        return path

    def test_same_version_equal(self):
        a=self.wheel('a.whl','0.1.0a2',{'events.py':b'before\n'})
        b=self.wheel('b.whl','0.1.0a2',{'events.py':b'before\n'})
        result,diff=collector.compare_baseline(b,a,'dacn_s02','0.1.0a2')
        self.assertEqual(result['mode'],'same_version_equal');self.assertEqual(diff,'')

    def test_same_version_mismatch_rejected(self):
        a=self.wheel('a.whl','0.1.0a2',{'events.py':b'before\n'})
        b=self.wheel('b.whl','0.1.0a2',{'events.py':b'after\n'})
        with self.assertRaisesRegex(AssertionError,'Same-version historical payload mismatch'):
            collector.compare_baseline(b,a,'dacn_s02','0.1.0a2')

    def test_new_version_records_complete_diff(self):
        a=self.wheel('a.whl','0.1.0a2',{'events.py':b'before\n','removed.py':b'old\n'})
        b=self.wheel('b.whl','0.1.0a3',{'events.py':b'after\n','added.py':b'new\n'})
        result,diff=collector.compare_baseline(b,a,'dacn_s02','0.1.0a3')
        self.assertEqual(result['mode'],'cross_version_diff')
        self.assertEqual(result['added'],['dacn_s02/added.py'])
        self.assertEqual(result['removed'],['dacn_s02/removed.py'])
        self.assertEqual(result['changed'],['METADATA','dacn_s02/events.py'])
        self.assertIn('-before\n+after\n',diff)
        self.assertNotEqual(result['before']['dacn_s02/events.py'],result['after']['dacn_s02/events.py'])

    def test_wrong_distribution_rejected(self):
        a=self.wheel('a.whl','0.1.0a2',{},distribution='unrelated')
        b=self.wheel('b.whl','0.1.0a3',{})
        with self.assertRaisesRegex(AssertionError,'distribution mismatch'):
            collector.compare_baseline(b,a,'dacn_s02','0.1.0a3')

    def test_current_version_mismatch_rejected(self):
        a=self.wheel('a.whl','0.1.0a2',{})
        b=self.wheel('b.whl','0.1.0a3',{})
        with self.assertRaisesRegex(AssertionError,'Current wheel version mismatch'):
            collector.compare_baseline(b,a,'dacn_s02','0.1.0a4')


if __name__=='__main__':unittest.main()
