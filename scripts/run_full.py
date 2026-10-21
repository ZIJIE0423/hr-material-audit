"""Local Excel audit -> authenticated Feishu sync -> full verification -> message to self."""
import argparse,hashlib,json,os,shutil,subprocess,sys,uuid
from datetime import datetime
from pathlib import Path
from feishu_sync_tools import ROOT,DATA,build,dump,load,records,index,verify,SELECTS,MAPPING,DATES

def cli_path():
 explicit=os.environ.get('LARK_CLI_PATH')
 candidates=[explicit,shutil.which('lark-cli.exe'),shutil.which('lark-cli'),str(Path(os.environ.get('APPDATA',''))/'npm/node_modules/@larksuite/cli/bin/lark-cli.exe')]
 for p in candidates:
  if p and Path(p).is_file() and Path(p).suffix.lower() not in ('.ps1','.cmd','.bat'): return p
 raise RuntimeError('未找到CLI：先安装，或设置LARK_CLI_PATH为lark-cli.exe完整路径')

def unwrap(obj):
 if isinstance(obj,dict) and obj.get('ok') is False: raise RuntimeError('CLI返回失败，请查看本次错误文件')
 return obj.get('data',obj) if isinstance(obj,dict) else obj

def find_value(obj,key):
 if isinstance(obj,dict):
  if obj.get(key) is not None: return obj[key]
  for v in obj.values():
   result=find_value(v,key)
   if result is not None: return result
 elif isinstance(obj,list):
  for v in obj:
   result=find_value(v,key)
   if result is not None: return result
 return None

def fields_from(obj):
 found={}
 def walk(o):
  if isinstance(o,dict):
   n=o.get('name') or o.get('field_name');t=o.get('type') or o.get('field_type')
   if n and t: found[n]=o
   else:
    for v in o.values(): walk(v)
  elif isinstance(o,list):
   for v in o: walk(v)
 walk(unwrap(obj))
 if not found: raise ValueError('未能解析线上字段结构，停止而不猜测字段类型')
 return found

class Client:
 def __init__(self,path,folder): self.path=path;self.folder=folder
 def call(self,label,args):
  env=os.environ.copy();env.update(LARKSUITE_CLI_NO_UPDATE_NOTIFIER='1',LARKSUITE_CLI_NO_SKILLS_NOTIFIER='1')
  print('CLI:',label,flush=True)
  p=subprocess.run([self.path,*args],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
  text=p.stdout.strip()
  try: obj=json.loads(text)
  except json.JSONDecodeError:
   if p.returncode: (self.folder/(label+'.error.txt')).write_text(p.stderr,encoding='utf-8')
   raise RuntimeError(f'{label}返回非JSON或执行失败，退出码{p.returncode}')
  if p.returncode or (isinstance(obj,dict) and obj.get('ok') is False):
   dump(self.folder/(label+'.error.json'),obj);raise RuntimeError(f'{label}失败；见本次error文件。不会继续发消息。')
  # Auth data is kept in memory; never persist credentials/status token fields.
  if label!='auth': dump(self.folder/(label+'.json'),obj)
  return obj
 def read_all(self,label,base,table):
  output=self.folder/(label+'.ndjson')
  obj=self.call(label,['base','+record-list','--base-token',base,'--table-id',table,'--format','ndjson','--output',str(output),'--overwrite','--limit','2000','--as','user'])
  body=unwrap(obj)
  if find_value(body,'has_more') is True: raise ValueError('表记录超过一次完整读取范围，需分页；本次停止避免漏读')
  manifest=self.folder/(label+'.manifest.json')
  if manifest.exists(): return records(manifest)
  if output.exists() and find_value(body,'has_more') is False: return records(output)
  file=find_value(body,'record_file')
  if file:
   return records(Path(file)) if find_value(body,'has_more') is False else (_ for _ in ()).throw(ValueError('未证明回读完整'))
  raise ValueError('缺少完整回读文件/has_more标志')

def adapt_payload(source,empmap,schema):
 payload=build(source,empmap)
 for row in payload['update_records'].values():
  for key,value in list(row.items()):
   f=schema.get(key)
   if not f: raise ValueError(f'目标表缺少字段：{key}；请先创建后重跑')
   typ=f.get('type') or f.get('field_type')
   if typ=='text' and isinstance(value,list): row[key]=value[0] if value else ''
   elif typ=='select':
    values=value if isinstance(value,list) else [value]
    options=f.get('options') or f.get('property',{}).get('options')
    # Unknown option policy is fail-closed: no lossy remapping or replacement of field schema.
    if options:
     allowed={o['name'] for o in options}
     if any(v not in allowed for v in values if v not in ('',None)): raise ValueError(f'{key}缺少选项{values}；补齐选项后重跑，不转换原值')
    row[key]=values
   elif typ not in ('text','select','number','datetime'): raise ValueError(f'{key}字段类型{typ}未支持，停止写入')
 return payload

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--as-of');p.add_argument('--input',type=Path);p.add_argument('--check-only',action='store_true');p.add_argument('--force-notify',action='store_true');p.add_argument('--base-token',default='FBJtb3WkvaNQdvsYmShcrhqjn3W');p.add_argument('--table-id',default='tbl8t60l02IsTpS1');a=p.parse_args()
 folder=DATA/'runs'/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);folder.mkdir(parents=True)
 state={'run_id':folder.name,'stage':'checking_auth','sync_success':False,'notification_success':False}
 dump(folder/'state.json',state)
 try:
  client=Client(cli_path(),folder)
  # 用contact +get-user验证身份，替代旧版auth status命令
  user_resp=client.call('auth',['contact','+get-user','--as','user'])
  user_data=user_resp.get('data',{}).get('user',{})
  recipient=user_data.get('open_id')
  if not recipient: raise RuntimeError('无法取得当前授权用户openId，请检查授权状态')
  schema=fields_from(client.call('fields',['base','+field-list','--base-token',a.base_token,'--table-id',a.table_id,'--as','user']))
  before=client.read_all('before',a.base_token,a.table_id);empmap={k:r['record_id'] for k,r in index(before).items()}
  if a.check_only:
   print('用户授权、目标表读取成功；未修改线上数据。');state['stage']='check_only_success';dump(folder/'state.json',state);return 0
  state['stage']='local_audit';dump(folder/'state.json',state)
  cmd=[sys.executable,str(ROOT/'scripts/hr_audit_pipeline.py')]
  if a.as_of: cmd+=['--as-of',a.as_of]
  if a.input: cmd+=['--input',str(a.input)]
  subprocess.run(cmd,check=True)
  source=records(DATA/'records.json');summary=load(DATA/'audit_summary.json');dump(folder/'local_records.json',source)
  if set(empmap)!=set(index(source)): raise ValueError('线上与本地工号集合不同，停止以防更新错误表；请先人工核对')
  payload=adapt_payload(source,empmap,schema);dump(folder/'update.json',payload)
  # Record readback and field preflight happen before any mutation.
  state['stage']='writing';dump(folder/'state.json',state)
  client.call('update',['base','+record-batch-update','--base-token',a.base_token,'--table-id',a.table_id,'--json','@'+str(folder/'update.json'),'--as','user'])
  after=client.read_all('after',a.base_token,a.table_id);result=verify(source,after);dump(folder/'verification.json',result);dump(DATA/'verify_result.json',result)
  if not result['全部一致']: raise ValueError(f'回读核验失败，差异{result["错误数"]}项；未发送通知')
  state.update(stage='verified',sync_success=True);dump(folder/'state.json',state)
  url=f'https://larkcommunity.feishu.cn/base/{a.base_token}?table={a.table_id}'
  summary.update(飞书已同步=True,通知已发送=False,表格链接=url,同步回执目录=str(folder));dump(DATA/'audit_summary.json',summary)
  text=f'员工材料审核完成（Excel唯一数据源）\n审核日期：{summary["审核日期"]}\n共{summary["员工数"]}人；{summary["异常员工数"]}人命中{summary["异常项数"]}项异常；{summary["待复核员工数"]}人待复核（可重叠）。\n异常工号：'+', '.join(summary['异常工号'])+'\n姓名为Excel同源映射，比对不适用，不计入待复核；眼镜来自Excel标记及声明的假设。\n结果：'+url
  (folder/'notification.txt').write_text(text,encoding='utf-8')
  key=hashlib.sha256(json.dumps({'source':source,'base':a.base_token,'table':a.table_id,'recipient':recipient},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  ledger=DATA/'notification_ledger.json';history=load(ledger) if ledger.exists() else {}
  if key in history and not a.force_notify:
   state.update(stage='completed_duplicate_notification_skipped',notification_success=True,message_id=history[key]['message_id']);summary.update(通知已发送=True,消息ID=history[key]['message_id'],通知说明='相同结果已通知，本次跳过重复发送')
  else:
   state['stage']='sending';dump(folder/'state.json',state)
   receipt=client.call('message',['im','+messages-send','--user-id',recipient,'--text',text,'--as','user'])
   mid=find_value(receipt,'message_id')
   if not mid: raise RuntimeError('消息请求已返回，但缺少message_id；不自动重试，以免重复发送，请检查回执')
   history[key]={'message_id':mid,'time':datetime.now().isoformat(timespec='seconds'),'recipient':recipient};dump(ledger,history);dump(DATA/'message_receipt.json',history[key])
   state.update(stage='completed',notification_success=True,message_id=mid);summary.update(通知已发送=True,消息ID=mid)
  dump(DATA/'audit_summary.json',summary);dump(folder/'state.json',state)
  with (ROOT/'docs/delivery_doc.md').open('a',encoding='utf-8') as f: f.write(f'\n## 本地CLI闭环回执\n\n本次同步全字段核验通过。通知状态：{state["stage"]}；消息ID：{state.get("message_id")}。回执：{folder}。\n')
  print('本地完整流程完成。表格：'+url+'\n消息ID：'+state.get('message_id',''));return 0
 except Exception as e:
  state.update(error=str(e));dump(folder/'state.json',state);print('流程停止：'+str(e)+'\n回执目录：'+str(folder),file=sys.stderr);return 1
if __name__=='__main__': raise SystemExit(main())
