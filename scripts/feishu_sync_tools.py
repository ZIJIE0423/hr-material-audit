"""Build lossless update payloads and verify every field against a saved readback."""
import argparse,json,re
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
MAPPING={
 '规则2-证件过期':{'有效':'✅ 有效','已过期':'❌ 已过期'},
 '规则3-年龄范围':{'正常':'✅ 正常','超出范围':'❌ 超出范围'},
 '规则4-百家姓TOP20':{'属于':'✅ 属于','不属于':'❌ 不属于'},
 '规则5-是否戴眼镜':{'未标记戴眼镜（按未戴处理）':'✅ 未戴','戴眼镜（Excel标记）':'❌ 戴眼镜'},
 '数据来源状态':{'Excel唯一数据源':'Excel模拟数据'}}
SELECTS=set(MAPPING)|{'系统性别','身份证性别','学历','规则1-姓名比对','审核结论'}
DATES={'出生日期','证件有效期起','证件有效期止','毕业日期','合同期限起','合同期限止','审核日期'}
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,d): Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def records(p):
 p=Path(p);obj=load(p) if p.suffix!='.ndjson' else None
 if obj is None: return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
 if isinstance(obj,list): return obj
 if obj.get('has_more'): raise ValueError('回读数据未完整分页，不能核验')
 if 'record_file' in obj:
  target=Path(obj['record_file'])
  if not target.exists(): target=p.parent/target.name
  rows=records(target)
  if 'records_count' in obj and len(rows)!=obj['records_count']: raise ValueError('回读文件条数与manifest不符')
  return rows
 if 'create_records' in obj: return obj['create_records']
 raise ValueError('不支持的记录格式，请使用manifest、ndjson或记录数组')
def index(rows,key='工号'):
 result={}
 for r in rows:
  value=r.get(key)
  if isinstance(value,list): value=value[0] if len(value)==1 else None
  if not value or value in result: raise ValueError('工号缺失或重复')
  result[value]=r
 return result

def build(source,emp_map):
 index(source)
 if len(set(emp_map.values()))!=len(emp_map): raise ValueError('record_id重复，拒绝更新')
 updates={}
 for r in source:
  eid=r['工号'];rid=emp_map.get(eid)
  if not rid: raise ValueError(f'{eid}缺少record_id，先完整回读工号映射')
  fields={}
  for k,v in r.items():
   if k=='工号': continue
   # Preserve degree literally: 硕士 is never converted to 本科.
   v=MAPPING.get(k,{}).get(v,v) if isinstance(v,str) else v
   if k in SELECTS: fields[k]=[v] if v not in ('',None) else []
   elif k in DATES and isinstance(v,str) and len(v)==10: fields[k]=v+' 00:00:00'
   else: fields[k]=v
  updates[rid]=fields
 return {'update_records':updates}

def norm(k,v):
 if isinstance(v,list): v=v[0] if len(v)==1 else ('' if not v else v)
 if v is None: return ''
 if k in DATES:
  try: return (datetime(1899,12,30)+timedelta(days=float(v))).date().isoformat()
  except (ValueError,TypeError): return str(v)[:10]
 if k=='年龄': return float(v) if v!='' else ''
 if isinstance(v,str):
  for before,after in MAPPING.get(k,{}).items():
   if v==after: return before
 return v

def verify(source,readback):
 original=index(source);online=index(readback);errors=[];passed=0
 for eid,r in original.items():
  if eid not in online: errors.append({'工号':eid,'问题':'回读缺失'});continue
  rowerrors=[]
  for key,value in r.items():
   if norm(key,value)!=norm(key,online[eid].get(key)): rowerrors.append({'工号':eid,'字段':key,'期望':value,'回读':online[eid].get(key)})
  errors.extend(rowerrors)
  if not rowerrors: passed+=1
 for eid in sorted(set(online)-set(original)): errors.append({'工号':eid,'问题':'线上存在额外员工'})
 return {'核验字段范围':'全部本地结果字段','本地记录数':len(source),'回读记录数':len(readback),'核验通过数':passed,'错误数':len(errors),'错误列表':errors,'全部一致':not errors}

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','verify']);p.add_argument('--records',type=Path,default=DATA/'records.json');p.add_argument('--readback',type=Path);p.add_argument('--map',type=Path,default=DATA/'emp_record_map.json');p.add_argument('--output',type=Path);a=p.parse_args()
 source=records(a.records)
 if a.action=='prepare':
  if a.readback:
   byid=index(records(a.readback));empmap={k:r['record_id'] for k,r in byid.items()};dump(a.map,empmap)
  else: empmap=load(a.map)
  output=a.output or DATA/'batch_update_final.json';dump(output,build(source,empmap));print(f'已生成{len(source)}条更新数据：{output}（未同步）')
 else:
  if not a.readback: p.error('verify必须提供--readback，禁止默认使用旧快照冒充本次回读')
  result=verify(source,records(a.readback));result['回读文件']=str(a.readback.resolve());result['核验时间']=datetime.now().isoformat(timespec='seconds');dump(a.output or DATA/'verify_result.json',result);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['全部一致'] else 1
 return 0
if __name__=='__main__': raise SystemExit(main())
