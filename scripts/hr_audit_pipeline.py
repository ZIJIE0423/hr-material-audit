#!/usr/bin/env python3
"""Excel-only HR audit. No OCR, attachment retrieval or invented employee values."""
import argparse,csv,hashlib,json,logging,sys
from collections import Counter
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
TOP20=set('赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许')
ROOT=Path(__file__).resolve().parents[1]
COLUMNS=['工号','系统姓名','系统性别','身份证姓名','身份证性别','出生日期','证件有效期起','证件有效期止','学历证书姓名','学历','毕业学校','专业','毕业日期','毕业证书编号','合同员工姓名','合同提取工号','用人单位','岗位','合同期限起','合同期限止','试用期','年龄','规则1-姓名比对','规则2-证件过期','规则3-年龄范围','规则4-百家姓TOP20','规则5-是否戴眼镜','异常汇总','审核日期','数据来源状态','异常依据','待复核原因','审核结论','姓名来源说明','眼镜来源说明','源表异常标记','规则标记差异']
def read_excel(path):
 ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
 with ZipFile(path) as z:
  wb=ET.fromstring(z.read('xl/workbook.xml')); rel=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
  rid=wb.find('m:sheets/m:sheet',ns).get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
  target=next(r.get('Target') for r in rel if r.get('Id')==rid)
  target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
  ss=[]
  if 'xl/sharedStrings.xml' in z.namelist(): ss=[''.join(t.text or '' for t in s.findall('.//m:t',ns)) for s in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
  rows=[]
  for row in ET.fromstring(z.read(target)).findall('m:sheetData/m:row',ns):
   d={}
   for c in row:
    v=c.find('m:v',ns);value=v.text if v is not None else ''
    if c.get('t')=='s': value=ss[int(value)]
    elif c.get('t')=='inlineStr': value=''.join(t.text or '' for t in c.findall('.//m:t',ns))
    d[''.join(ch for ch in c.attrib['r'] if ch.isalpha())]=value
   rows.append(d)
  if not rows: raise ValueError('Excel为空')
  result=[{key:r.get(col,'') for col,key in rows[0].items()} for r in rows[1:] if any(r.values())]
  for r in result:
   for k in ['dob','id_valid_from','id_valid_to','degree_date','contract_from','contract_to']:
    value=r.get(k,'')
    if value:
     try: r[k]=(datetime(1899,12,30)+timedelta(days=float(value))).date().isoformat()
     except ValueError: pass
  return result

def age_on(d,t): return t.year-d.year-((t.month,t.day)<(d.month,d.day))
def audit(r,today,photo_policy='closed-world'):
 issues=[];pending=[];hits=set();name=str(r.get('name') or '').strip()
 # Only one name exists in the Excel: mapped fields are explicitly derived, never independent extraction.
 out={'工号':r['emp_id'],'系统姓名':name,'身份证姓名':name,'学历证书姓名':name,'合同员工姓名':name,'合同提取工号':r['emp_id'],'系统性别':r.get('gender',''),'身份证性别':r.get('gender',''),'年龄':None,'审核日期':today.isoformat(),'数据来源状态':'Excel唯一数据源','姓名来源说明':'四个姓名字段均映射自Excel.name；合同工号映射自emp_id；不构成独立证件比对','源表异常标记':r.get('rules_hit','')}
 mapping={'出生日期':'dob','证件有效期起':'id_valid_from','证件有效期止':'id_valid_to','学历':'degree_level','毕业学校':'degree_school','专业':'degree_major','毕业日期':'degree_date','毕业证书编号':'degree_no','用人单位':'company','岗位':'title','合同期限起':'contract_from','合同期限止':'contract_to','试用期':'probation'}
 for k,v in mapping.items(): out[k]=r.get(v,'')
 out['规则1-姓名比对']='不适用（单一姓名来源）' if name else '待复核（姓名缺失）'
 try:
  start=date.fromisoformat(r.get('id_valid_from',''));endstr=r.get('id_valid_to','');end=None if endstr in ('长期','长期有效') else date.fromisoformat(endstr)
  if start>today or (end and start>end): raise ValueError('有效期矛盾或尚未生效')
  expired=bool(end and end<today);out['规则2-证件过期']='已过期' if expired else '有效'
  if expired: hits.add('ID_EXPIRED');issues.append(f'证件截至{end}，早于审核日{today}')
 except (ValueError,TypeError): out['规则2-证件过期']='待复核';pending.append('有效期缺失或无效')
 try:
  dob=date.fromisoformat(r.get('dob',''))
  if dob>today: raise ValueError('未来出生日期')
  age=age_on(dob,today);out['年龄']=age;out['规则3-年龄范围']='正常' if 22<=age<=60 else '超出范围'
  if not 22<=age<=60: hits.add('AGE_OUT_OF_RANGE');issues.append(f'出生{dob}，{today}时为{age}周岁，不在22–60岁（含）')
 except (ValueError,TypeError): out['规则3-年龄范围']='待复核';pending.append('出生日期缺失或无效')
 if name:
  surname=next((s for s in ['欧阳','端木','司马','上官','诸葛','夏侯','皇甫','尉迟','公孙','慕容','司徒','司空'] if name.startswith(s)),name[:1])
  out['规则4-百家姓TOP20']='属于' if surname in TOP20 else '不属于'
  if surname not in TOP20: hits.add('SURNAME_NOT_TOP20');issues.append(f'姓氏{surname}不在题目指定20姓中')
 else: out['规则4-百家姓TOP20']='待复核';pending.append('姓名缺失')
 source_hits={x.strip() for x in str(r.get('rules_hit') or '').split(';') if x.strip()}
 if 'PHOTO_GLASSES' in source_hits:
  out['规则5-是否戴眼镜']='戴眼镜（Excel标记）';hits.add('PHOTO_GLASSES');issues.append('Excel.rules_hit含PHOTO_GLASSES，按本项目策略计为异常')
 elif photo_policy=='closed-world': out['规则5-是否戴眼镜']='未标记戴眼镜（按未戴处理）'
 else: out['规则5-是否戴眼镜']='待复核';pending.append('rules_hit无眼镜标记，不推断未戴')
 out['眼镜来源说明']='只读取rules_hit：PHOTO_GLASSES=戴；无标记'+('按未戴处理（演练假设）' if photo_policy=='closed-world' else '待复核')+'；未做视觉识别'
 out['异常汇总']='；'.join(issues) if issues else '未发现可判定规则异常'
 out['异常依据']=out['异常汇总'];out['待复核原因']='；'.join(pending) or '无'
 out['审核结论']=('异常并待复核' if pending else '异常') if issues else ('待复核' if pending else '通过')
 missing=hits-source_hits;extra=source_hits-hits
 out['规则标记差异']='；'.join(([f'重算新增:{",".join(sorted(missing))}'] if missing else [])+([f'源标记未重现:{",".join(sorted(extra))}'] if extra else [])) or '一致'
 return out,hits

def dump(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=ROOT/'materials/图片和附件/materials_table.xlsx');p.add_argument('--output',type=Path,default=ROOT/'data');p.add_argument('--as-of',type=date.fromisoformat,default=datetime.now(timezone(timedelta(hours=8))).date());p.add_argument('--photo-policy',choices=['closed-world','unknown'],default='closed-world');a=p.parse_args()
 rows=read_excel(a.input);ids=Counter(r.get('emp_id') for r in rows)
 if any(not k or n>1 for k,n in ids.items()): raise ValueError('工号缺失或重复，停止处理')
 if not rows: raise ValueError('没有员工数据')
 a.output.mkdir(parents=True,exist_ok=True)
 logging.basicConfig(level=logging.INFO,format='%(message)s',handlers=[logging.FileHandler(a.output/'run.log',mode='w',encoding='utf-8'),logging.StreamHandler(sys.stdout)],force=True)
 out=[];abnormal=[];counts=Counter()
 for i,r in enumerate(rows,1):
  item,hits=audit(r,a.as_of,a.photo_policy);out.append(item);counts.update(hits)
  if hits: abnormal.append(r['emp_id'])
  logging.info('[%s/%s] %s | %s',i,len(rows),r['emp_id'],item['审核结论'])
 summary={'审核日期':str(a.as_of),'数据源':str(a.input.resolve()),'源文件SHA256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'员工数':len(out),'异常员工数':len(abnormal),'异常项数':sum(counts.values()),'无异常员工数':sum(r['审核结论']=='通过' for r in out),'姓名比对不适用人数':sum(r['规则1-姓名比对'].startswith('不适用') for r in out),'待复核员工数':sum(r['待复核原因']!='无' for r in out),'异常工号':abnormal,'规则命中':dict(counts),'眼镜策略':a.photo_policy,'执行范围':'Excel读取、映射、审核、导出；不执行OCR或外部材料获取','飞书已同步':False,'通知已发送':False}
 dump(a.output/'audit_summary.json',summary);dump(a.output/'records.json',{'create_records':out})
 dump(a.output/'batch_create.json',{'fields':COLUMNS,'rows':[[r.get(k) for k in COLUMNS] for r in out]})
 # Text schema is deliberate: avoids stale select options and payload mismatches.
 dump(a.output/'fields.json',[{'name':k,'type':'number' if k=='年龄' else 'datetime' if k in ('出生日期','证件有效期起','证件有效期止','毕业日期','合同期限起','合同期限止','审核日期') else 'text'} for k in COLUMNS])
 with (a.output/'audit_records.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(out)
 message=f'员工材料审核结果（Excel数据模式）\n审核日：{a.as_of}\n共{len(out)}人，异常{len(abnormal)}人、{sum(counts.values())}项；待复核{summary["待复核员工数"]}人（与异常可重叠）。\n异常工号：'+', '.join(abnormal)+'\n姓名比对不适用，不计入待复核；仅统计适用规则；眼镜依据Excel标记及已声明假设。\n此文件为通知草稿，尚未发送。'
 (a.output/'notification_draft.txt').write_text(message,encoding='utf-8');logging.info(json.dumps(summary,ensure_ascii=False))
 report='# Excel模式审核运行报告\n\n'+ '\n'.join(f'- {k}：{v}' for k,v in summary.items())+'\n\n## 口径\n\n所有字段仅来自输入Excel。17项所需字段均有映射，其中三类材料姓名及合同工号为同源派生，不代表原件提取。姓名比对不适用，不计入待复核，也不视为独立比对通过。审核结论仅针对适用规则。年龄从dob按审核日重算；有效期截止当天仍有效；姓氏使用题目名单，复姓先完整匹配。眼镜只读PHOTO_GLASSES；默认无标记按未戴处理，可用--photo-policy unknown改为待复核。既有rules_hit只作眼镜输入和其他规则差异核对，不作为年龄、姓氏、有效期的答案。\n\n## 同步状态\n\n本次为本地运行，没有线上写入或发送消息。生成batch_create.json供新表导入，已有表先按工号核对再更新，不应重复创建。字段方案用于新表；旧表字段类型可能不同，不应直接覆盖。\n'
 (ROOT/'docs').mkdir(exist_ok=True);(ROOT/'docs/delivery_doc.md').write_text(report,encoding='utf-8')
if __name__=='__main__': main()
