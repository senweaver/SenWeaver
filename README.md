<p align="center">
  <a href="https://www.senweaver.com" target="_blank">
    <img width="200" src="https://www.senweaver.com/img/senweaver-logo.png" alt="SenWeaver Enterprise Framework">
  </a>
</p>

<h3 align="center">SenWeaver - 企业级快速开发框架</h3>

<p align="center">
 <a href="https://github.com/senweaver/SenWeaver">
    <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/senweaver/SenWeaver?style=flat-square&logo=github">
  </a>
  <a href="https://gitee.com/senweaver/SenWeaver">
    <img alt="Gitee Repo stars" src="https://gitee.com/senweaver/SenWeaver/badge/star.svg?theme=flat">
  </a>
   <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square">
  <a href="https://demo.senweaver.com/">
    <img alt="Online Demo" src="https://img.shields.io/badge/demo-online-brightgreen?style=flat-square">
  </a>
</p>

---

## 🚀 核心特性

**SenWeaver** 是基于现代Python技术栈构建的企业级开发框架，采用 **FastAPI** + **SQLModel** + **Pydantic V2** 架构，具备以下核心优势：

- **智能ORM扩展**  
  动态条件检测、复合排序支持、双模式分页（偏移量/游标）优化数据操作效率

- **细粒度权限控制**  
  支持行级数据权限、字段级访问控制、RBAC权限模型的多维度安全体系

- **模块化架构设计**  
  支持应用/插件/组件的动态加载机制，实现业务功能解耦与复用

- **自动化开发工具链**  
  提供从模型定义到API接口、前端组件的全流程代码生成能力

---

## 📚 文档资源

- [官方文档](https://www.senweaver.com/) - 完整开发指南与API参考
- [在线演示](https://demo.senweaver.com/)  
  _测试账号: admin / senweaver123_

---

## 🛠️ 功能矩阵

### 系统管理
- **组织架构**：多层级部门管理（公司-部门-小组）
- **用户管理**：支持创建、编辑和删除用户，同时可以为每个用户分配不同的角色
- **菜单管理**：灵活定义系统的导航菜单，包括一级菜单、二级菜单及其子项。
- **角色管理**：为不同角色配置可访问的菜单和页面，实现基于角色的访问控制。
- **权限管理**：功能权限+数据权限（行权限和字段权限）
- **日志审计**：完整操作日志追踪与登录行为分析

### 开发支持
- **代码生成器**：模型驱动开发（MDD），自动生成CRUD接口
- **API文档**：自动生成OpenAPI 3.0规范文档
- **模块系统**：支持热插拔式插件开发

### 业务功能
- **文件管理**：安全文件存储与权限验证系统
- **消息中心**：多通道通知系统
- **命令管理**：命令行控制工具
- ...

---

## ⚡ 极速CRUD实现

通过声明式配置快速构建完整业务模块：

```python
from senweaver.core import (
    SenWeaverFilter,
    RelationConfig,
    FieldConfig,
    senweaver_router
)
from fastapi import APIRouter
from ..model.example import Example

# 定义数据过滤器配置
filter_config = SenWeaverFilter(
    filters={"title__contains": None, "level": None},
    table_fields=['id', 'title', 'notice_type', 'created_time'],
    ordering_fields=['-created_time'],
    relationships=[
        RelationConfig(
            rel=Example.notice_user,
            attrs=['id', 'username'],
            input_type="api-search-user",
            label="通知用户"
        )
    ],
    extra_fields=[
        FieldConfig(
            key="user_count",
            annotation=int,
            label="用户统计",
            callbacks={"select": ExampleLogic.get_user_count}
        )
    ]
)

# 自动生成CRUD路由
router = senweaver_router(
    model=Example,
    path="/examples",
    filter_config=filter_config,
    callbacks={"save": ExampleLogic.custom_save}
)
```

## 鸣谢

- [fastcrud](https://github.com/igorbenav/fastcrud).
- [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template).
- [fastapi-cache](https://github.com/long2ice/fastapi-cache).
- [fastapi-async-sqlalchemy](https://github.com/h0rn3t/fastapi-async-sqlalchemy).
- [xadmin-server](https://github.com/nineaiyu/xadmin-server).
- [fastapi](https://github.com/fastapi/fastapi).
- [sqlmodel](https://github.com/fastapi/sqlmodel).
- [pydantic](https://github.com/pydantic/pydantic).

## 联系我们

关注我们的微信公众号或加入我们的交流群：

<table>
  <tbody>
    <tr>
      <td align="center" valign="middle" style="width:50%">
        <img src="https://www.senweaver.com/img/qrcode/wxq.png" class="no-zoom" style="width:120px;margin: 10px">
        <p>SenWeaver微信群(添加微信备注"进群")</p>
      </td>
      <td align="center" valign="middle"  style="width:50%">
        <img src="https://www.senweaver.com/img/qrcode/gzh.jpg" alt="微信号: senweaver" class="no-zoom" style="width:120px;margin: 10px;">
        <p>SenWeaver微信公众号</p>
      </td>
    </tr>
  </tbody>
</table>