# 人力运营AI赋能实习生\-笔试题

## 你需要完成什么？

你要模拟一个人力运营审核同学

|步骤|你要做什么|
|---|---|
|**① 材料获取**|通过 [员工工号](https://bytedance.larkoffice.com/docx/VN1sdBhezoTw9rxgnE1cdTqZnHb#doxcnJAF6ZQrM7CQGy5jsNIglLe)，从[模拟](https://bytedance.larkoffice.com/share/base/query/shrcnWnDm7aUzxEhkuaP0xVRADe)网站批量下载 20 个员工的3类附件（身份证、学历证书、劳动合同）|
|**② 信息提取**|从 3 类附件中提取 [指定字段](https://bytedance.larkoffice.com/docx/VN1sdBhezoTw9rxgnE1cdTqZnHb#doxcnvCcz5JanLs2sX3tNz67L5g)（姓名、性别、学历、合同期限等共 17 个字段）|
|**③ 规则审核**|对提取的信息做 5 项 [规则校验](https://bytedance.larkoffice.com/docx/VN1sdBhezoTw9rxgnE1cdTqZnHb#doxcn8nVLYr8NqLilZUy0kfeBHf)（姓名比对、证件过期、年龄范围、百家姓 TOP20、是否戴眼镜）|
|**④ 异常闭环**|把[有问题的](https://bytedance.larkoffice.com/docx/VN1sdBhezoTw9rxgnE1cdTqZnHb#doxcn6eIYRcl0sioPeKluBauKCd)员工汇总，给自己发消息通知|



### 员工信息（模拟系统信息）

[materials\_table\.xlsx](图片和附件/materials_table.xlsx)



### **信息提取**

需要提取的字段如下

|附件类型|提取字段|
|---|---|
|身份证<br>|- 法定姓名<br>- 性别<br>- 出生日期<br>- 证件开始日期<br>- 证件到期日期|
|学历证书<br>|- 姓名<br>- 学历<br>- 学校<br>- 专业<br>- 毕业日期<br>- 毕业证书编号|
|劳动合同<br>|- 用人单位<br>- 员工姓名<br>- 工号<br>- 岗位<br>- 合同期限<br>- 试用期|



### **规则审核**

基于身份证覆盖 5 个审核点：

|序号|审核点|
|---|---|
|1|证件中的提取到的法定姓名，与系统中法定姓名进行比对，输出是否一致|
|2|证件是否过期（有效期截至日 vs 当前日期）|
|3|**年龄是否在 22–60 之间**（包含边界）|
|4|**员工的姓氏是否属于 百家姓TOP20**<br>> "赵","钱","孙","李","周","吴","郑","王","冯","陈","褚","卫","蒋","沈","韩","杨","朱","秦","尤","许"<br>> <br>> |
|5|**是否戴眼镜**（从身份证照片判断）|



### 异常闭环

对规则审核异常的数据，在飞书内给自己发送一个消息，告诉自己其中xx条有问题，把问题的员工id发给自己







## 最终需要交付什么？

1. 运行流程\-\-能够体现出循环下载员工的附件

2. 你手搓的多维表链接\-\-最终体现出20个员工文件中提取出的字段、定位到不符合审核规则的具体内容

3. 给自己发出的消息













