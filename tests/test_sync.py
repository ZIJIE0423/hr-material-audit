import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from feishu_sync_tools import build,verify
class SyncTests(unittest.TestCase):
 def test_degree_preserved(self): self.assertEqual(build([{'工号':'E1','学历':'硕士'}],{'E1':'rec1'})['update_records']['rec1']['学历'],['硕士'])
 def test_degree_error_detected(self): self.assertFalse(verify([{'工号':'E1','学历':'硕士'}],[{'工号':'E1','学历':['本科']}])['全部一致'])
 def test_duplicate_id(self):
  with self.assertRaises(ValueError): build([{'工号':'E1'},{'工号':'E2'}],{'E1':'r','E2':'r'})
 def test_missing_mapping(self):
  with self.assertRaises(ValueError): build([{'工号':'E1'}],{})
 def test_all_fields(self): self.assertEqual(verify([{'工号':'E1','专业':'甲','岗位':'乙'}],[{'工号':'E1','专业':'甲','岗位':'丙'}])['错误数'],1)
 def test_normalization(self): self.assertTrue(verify([{'工号':'E1','规则4-百家姓TOP20':'属于','审核日期':'2026-10-21'}],[{'工号':'E1','规则4-百家姓TOP20':['✅ 属于'],'审核日期':'2026-10-21T00:00:00+08:00'}])['全部一致'])
 def test_extra_employee(self): self.assertFalse(verify([{'工号':'E1'}],[{'工号':'E1'},{'工号':'E2'}])['全部一致'])
if __name__=='__main__': unittest.main(verbosity=2)
