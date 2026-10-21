# 飞书CLI与复现

## 调用原理

Python使用subprocess启动官方lark-cli.exe。用户身份通过--as user显式指定；CLI负责授权和开放平台请求。主程序先读取字段和记录，按工号查record_id；更新后全字段回读一致才发送通知。接收人取当前授权用户openId，不硬编码旧应用的用户ID。消息正文包括异常统计、工号和结果表链接。

## 安装与授权

官方仓库：https://github.com/larksuite/cli

```powershell
npx @larksuite/cli@latest install
lark-cli config init
lark-cli auth login --scope 'base:app:read base:table:read base:field:read base:record:read base:record:update im:message im:message.send_as_user auth:user.id:read offline_access'
lark-cli auth status --json --verify
```

## 启动

```powershell
python scripts/run_project.py --as-of 2026-10-21
python scripts/run_full.py --check-only
python scripts/run_full.py --as-of 2026-10-21
```

第一条只生成本地结果；第二条只检查登录与目标表读取；第三条会修改目标表并给当前用户发送汇总。默认目标为已有作业表，程序要求线上工号集合与本地完全相同；不会自动建新表、增删员工或覆写字段结构。

目标可用--base-token和--table-id指定。应确认目标表37字段存在、类型正确、学历含硕士。单选参数数组是已验证CLI 1.0.98批量更新的约定，不推广为所有接口通用格式。CLI位置可通过LARK_CLI_PATH指定，程序会尝试PATH和Windows全局npm默认位置。

## 回执与失败

每次完整模式输出data/runs/时间_随机后缀：字段信息、更新前后记录、更新请求、核验报告、通知内容及回执。用户授权失败在写入前停止；缺字段/选项、重复工号、更新失败或核验不一致时不发消息。不自动切换机器人。

同一数据、同一表和同一接收人已有成功通知时跳过重复发送；需要重发可用--force-notify。发送超时或回执缺少消息ID时，先检查飞书，不盲目重发。

## 部署边界


## 姓名口径更新
姓名比对为不适用（单一姓名来源），不计入待复核。当前为12人异常、8人无异常、0人待复核，结论只覆盖适用规则。同步时保留旧选项，补充新选项后再运行；不得把不适用映射为一致或待复核。


## 最终运行状态

2026-10-21 16:53:40已完成姓名新口径同步，20人37字段全量回读零差异，12人异常、8人通过、0人待复核，消息已发送。回执见evidence/latest_run。换机器需要自行安装和授权CLI，并具有目标表权限。
