"""Run the Excel audit; optionally prepare updates using a fresh readback."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--as-of');p.add_argument('--input',type=Path);p.add_argument('--readback',type=Path);a=p.parse_args()
 cmd=[sys.executable,str(ROOT/'scripts/hr_audit_pipeline.py')]
 if a.as_of: cmd+=['--as-of',a.as_of]
 if a.input: cmd+=['--input',str(a.input)]
 subprocess.run(cmd,check=True)
 if a.readback:
  subprocess.run([sys.executable,str(ROOT/'scripts/feishu_sync_tools.py'),'prepare','--readback',str(a.readback)],check=True)
 print('本地审核与导出完成。未同步飞书、未发送消息。完整模式请运行scripts/run_full.py。')
if __name__=='__main__': main()
