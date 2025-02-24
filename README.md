# SenWeaver
<b>SenWeaver</b>是基于FastAPI+SQLModel+PydanticV2等技术栈构建
> 提供强大的异步CRUD操作和灵活的端点创建工具，通过诸如自动检测连接条件、动态排序以及偏移量和游标分页等高级功能进行优化。
提供强大的细粒度权限管理，允许对不同级别的资源进行精确访问控制。这包括行级和字段级的数据权限管理，确保每个用户只能访问授权的数据部分。

## 在线预览

[http://demo.senweaver.com/](http://demo.senweaver.com/)
账号密码：admin/senweaver123


## 系统功能

- 用户管理：支持创建、编辑和删除用户，同时可以为每个用户分配不同的角色
- 部门管理：支持多层级的组织结构配置（如公司、部门、小组等），方便管理和维护复杂的组织架构
- 菜单管理：灵活定义系统的导航菜单，包括一级菜单、二级菜单及其子项。
- 角色管理：为不同角色配置可访问的菜单和页面，实现基于角色的访问控制。
- 权限管理：数据权限（行权限和字段权限）
- 代码生成：后端代码自动生成：支持从模型自动生成 API 接口代码
- 模块系统：支持应用、插件、组件等动态加载
- 操作日志：详细记录所有正常和异常的操作行为，便于审计和问题排查
- 登录日志：记录用户每次登录的时间、IP 地址等信息，区分正常和异常登录尝试
- 接口文档：自动生成在线交互式 API 文档
- 通知公告：所有用户或特定用户组发布重要通知和公告
- 文件管理: 支持文件的上传、下载和管理，确保文件的安全性和完整性
- 

# 快速CRUD实现

> 本平台通过在 API 层编写少量代码，即可实现全面的前端功能自动生成，包括一对一、一对多、多对多关系的数据展示，搜索列配置，列表页生成，功能权限与数据权限管理，API 接口文档自动生成，以及完整的 CRUD 操作支持。该平台不仅显著提高了开发效率，还确保了系统的灵活性、安全性和可维护性。

```python
from senweaver.core.helper import FieldConfig
from typing import List, Union
from senweaver.core.helper import SenweaverFilter, RelationConfig
from senweaver import senweaver_router
from fastapi import APIRouter, Request
from senweaver.utils.response import ResponseBase, success_response
from ..example import module
from ..model.example import Example, ExampleRead
from ..logic.notice_logic import ExampleLogic
router = APIRouter(tags=["example"])

filter_config = SenweaverFilter(
    # 查询过滤条件
    filters={"id": None, "title__contains": None, "message__contains": None,
             "notice_type": None, "level": None, "publish": None},
    # 显示的字段
    fields=['id', 'title', 'level', "publish", 'notice_type', "notice_user", 'notice_dept', 'notice_role',
                  'message', "created_time", "user_count", "read_user_count", 'extra_json', "files"],
    # 列表展示字段
    table_fields=['id', 'title', 'notice_type',
                  "read_user_count", "publish", "created_time"],
    # 字段扩展配置
    extra_kwargs={
        'extra_json': {'read_only': True},
    },
    # 可排序字段
    ordering_fields=['updated_time', 'created_time'],
    # 关系字段
    relationships=[
        RelationConfig(rel=Example.notice_user, attrs=[
                       'id', 'username'], format="{username}", many=True, label="被通知用户", read_only=False, required=True, write_only=False, input_type="api-search-user", callbacks={"select": ExampleLogic.get_notice_user}),
        RelationConfig(
            rel=Example.notice_dept, attrs=[
                'id', 'name'], format="{name}", label="被通知部门", many=True, input_type='api-search-dept'),
        RelationConfig(
            rel=Example.notice_role, attrs=[
                'id', 'name'], format="{name}", label="被通知角色", many=True, read_only=False, input_type='api-search-role')
    ],
    # 扩展字段信息
    extra_fields=[
        FieldConfig(key="files", default=[], annotation=list, write_only=True,
                    label="上传的附件", input_type="json"),
        FieldConfig(key="user_count", default=0, label="用户数量", read_only=True,
                    annotation=int, input_type="field", callbacks={"select": ExampleLogic.get_user_count}),
        FieldConfig(key="read_user_count", default=0, annotation=int, read_only=True,
                    label="已读用户数量", input_type="field", callbacks={"select": ExampleLogic.get_read_user_count})
    ],
)
# 动态创建crud、导入导出等相关路由
_router = senweaver_router(
    module=module,
    model=Example,
    path=f"/example",
    filter_config=filter_config,
    callbacks={"save": ExampleLogic.save},
    custom_router=ExampleLogic.add_custom_router
)
router.include_router(_router)
```


## 启示与参考

- [fastcrud](https://github.com/igorbenav/fastcrud).
- [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template).
- [fastapi-cache](https://github.com/long2ice/fastapi-cache).
- [fastapi-async-sqlalchemy](https://github.com/h0rn3t/fastapi-async-sqlalchemy).
- [xadmin-server](https://github.com/nineaiyu/xadmin-server).
- [fastapi](https://github.com/fastapi/fastapi).
- [sqlmodel](https://github.com/fastapi/sqlmodel).
- [pydantic](https://github.com/pydantic/pydantic).