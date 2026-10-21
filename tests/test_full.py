import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_full import adapt_payload,fields_from,find_value,unwrap
class FullTests(unittest.TestCase):
 def test_fields_envelope(self): self.assertIn('学历',fields_from({'ok':True,'data':{'fields':[{'name':'学历','type':'select'}]}}))
 def test_preserve_masters(self):
  p=adapt_payload([{'工号':'E','学历':'硕士'}],{'E':'rec'},{'学历':{'name':'学历','type':'select','options':[{'name':'硕士'}]}})
  self.assertEqual(p['update_records']['rec']['学历'],['硕士'])
 def test_missing_option_stops(self):
  with self.assertRaises(ValueError): adapt_payload([{'工号':'E','学历':'硕士'}],{'E':'rec'},{'学历':{'type':'select','options':[{'name':'本科'}]}})
 def test_text_field(self): self.assertEqual(adapt_payload([{'工号':'E','审核结论':'待复核'}],{'E':'r'},{'审核结论':{'type':'text'}})['update_records']['r']['审核结论'],'待复核')
 def test_missing_field_stops(self):
  with self.assertRaises(ValueError): adapt_payload([{'工号':'E','学历':'硕士'}],{'E':'r'}, {})
 def test_receipt(self): self.assertEqual(find_value({'ok':True,'data':{'message':{'message_id':'om_1'}}},'message_id'),'om_1')
 def test_failure_envelope(self):
  with self.assertRaises(RuntimeError): unwrap({'ok':False})
if __name__=='__main__': unittest.main()
