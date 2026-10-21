# 人力运营材料审核｜最终交付（Excel输入版）

先阅读docs/笔试交付说明.md。

## 本次结果

审核日期2026-10-21：20人、37字段，12人命中17项异常、8人通过（适用规则）、0人待复核。姓名比对不适用，不冒充独立比对通过。学历保留本科10、硕士5、大专5。

已完成飞书同步、全字段回读零差异、给本人发消息。消息ID：om_x100b62b3978644a8dc08d0055ab2c79，时间2026-10-21 16:53:40。保存的真实执行证据在evidence/latest_run。

结果表：https://larkcommunity.feishu.cn/base/FBJtb3WkvaNQdvsYmShcrhqjn3W?table=tbl8t60l02IsTpS1

## 复现

Python 3.9+，仅标准库。本地审核不需要飞书授权：

```powershell
python scripts/run_project.py --as-of 2026-10-21
python -m unittest discover -s tests -v
```

完整模式需要安装官方lark-cli、完成用户授权并拥有目标表编辑权限：

```powershell
python scripts/run_full.py --check-only
python scripts/run_full.py --as-of 2026-10-21
```

运行审核.bat只运行本地审核；运行完整流程.bat会同步飞书并发送消息。两个双击入口默认按当天上海日期执行。固定--as-of用于复现本次结果。重新本地运行会重置本次输出同步状态，历史成功证据仍保存在evidence。

## 文件

- docs/：交付说明、字段规则、CLI与复现。
- scripts/：审核、同步、核验和运行入口。
- tests/：24项测试。
- materials/：题目原文与唯一输入Excel。
- data/：当前结果CSV、JSON与统计。
- evidence/：最终运行回执、回读数据、消息回执、独立检查及测试结果。

## 范围

按Excel唯一数据源方案实现，不做附件下载、OCR或身份证照片识别；与原题这些要求的差距已在交付说明列明。眼镜来自Excel标记，姓名因单一来源不适用。通过只针对适用规则。没有打包登录态、密钥或授权二维码；接收者需要自己的飞书授权及资源权限。
