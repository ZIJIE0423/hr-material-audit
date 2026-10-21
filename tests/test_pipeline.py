import sys,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hr_audit_pipeline import age_on,audit,read_excel
class AuditTests(unittest.TestCase):
 def setUp(self): self.r={'emp_id':'EMP0001','name':'王一凡','dob':'1994-03-12','id_valid_from':'2020-01-01','id_valid_to':'2035-01-01','rules_hit':''};self.t=date(2026,10,21)
 def test_age_boundaries(self):
  for d,age in [('2004-10-21',22),('2004-10-22',21),('1966-01-01',60),('1965-10-21',61)]: self.assertEqual(age_on(date.fromisoformat(d),self.t),age)
 def test_single_source_name(self): self.assertEqual(audit(self.r,self.t)[0]['规则1-姓名比对'],'不适用（单一姓名来源）');self.assertEqual(audit(self.r,self.t)[0]['待复核原因'],'无');self.assertEqual(audit(self.r,self.t)[0]['审核结论'],'通过')
 def test_expiry_today(self): self.assertNotIn('ID_EXPIRED',audit(dict(self.r,id_valid_to='2026-10-21'),self.t)[1])
 def test_expired(self): self.assertIn('ID_EXPIRED',audit(dict(self.r,id_valid_to='2026-10-20'),self.t)[1])
 def test_long_validity(self): self.assertEqual(audit(dict(self.r,id_valid_to='长期'),self.t)[0]['规则2-证件过期'],'有效')
 def test_bad_dates(self): self.assertEqual(audit(dict(self.r,dob='bad'),self.t)[0]['规则3-年龄范围'],'待复核')
 def test_compound_surname(self): self.assertIn('SURNAME_NOT_TOP20',audit(dict(self.r,name='欧阳辰'),self.t)[1])
 def test_photo_source(self): self.assertIn('PHOTO_GLASSES',audit(dict(self.r,rules_hit='PHOTO_GLASSES'),self.t)[1])
 def test_photo_unknown(self): self.assertEqual(audit(self.r,self.t,'unknown')[0]['规则5-是否戴眼镜'],'待复核')
 def test_source_not_rule_answer(self): self.assertIn('SURNAME_NOT_TOP20',audit(dict(self.r,name='张三',rules_hit=''),self.t)[1])
if __name__=='__main__': unittest.main(verbosity=2)
