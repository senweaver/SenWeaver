from pathlib import Path

import typer

from jinja2 import Environment, FileSystemLoader
from pydantic.alias_generators import to_pascal
from sqlalchemy import MetaData
from sqlalchemy.types import (
    ARRAY,
    BIGINT,
    BINARY,
    BLOB,
    BOOLEAN,
    CHAR,
    CLOB,
    DATE,
    DATETIME,
    DECIMAL,
    DOUBLE,
    DOUBLE_PRECISION,
    FLOAT,
    INT,
    INTEGER,
    JSON,
    NCHAR,
    NULLTYPE,
    NUMERIC,
    NVARCHAR,
    REAL,
    SMALLINT,
    STRINGTYPE,
    TEXT,
    TIME,
    TIMESTAMP,
    UUID,
    VARBINARY,
    VARCHAR,
    BigInteger,
    Boolean,
    Concatenable,
    Date,
    DateTime,
    Enum,
    Float,
    Indexable,
    Integer,
    Interval,
    LargeBinary,
    MatchType,
    NullType,
    Numeric,
    PickleType,
    SchemaType,
    SmallInteger,
    String,
    Text,
    Time,
    TupleType,
    TypeDecorator,
    Unicode,
    UnicodeText,
    Uuid,
)

from senweaver.core.models import Field, SQLModel
from senweaver.helper import is_module_name


def create_module(module_path: Path, name: str, template_dir: Path, variables: dict = {}) -> bool:
    if len(name) < 2:
        raise typer.BadParameter(
            'The module name must be at least 2 characters long.',
            param_hint='--name',
        )
    temp_variables = {'module_name': name, 'model_class_name': to_pascal(name)}
    variables = {**temp_variables, **variables}
    if not is_module_name(name):
        typer.echo(typer.style(f"The module name'{name}' is invalid.", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)
    if not module_path.exists():
        try:
            module_path.mkdir(parents=False, exist_ok=False)
            typer.echo(typer.style(f"目录 '{module_path}' 创建成功。", fg=typer.colors.GREEN, bold=True))

            # 准备 Jinja2 环境
            env = Environment(loader=FileSystemLoader(template_dir))
            # 准备生成目录的路径
            output_dir = module_path  # 替换成你希望生成的目录路径
            # 遍历模板目录中的文件并渲染生成
            for template_path in template_dir.rglob('*.j2'):
                relative_path = template_path.relative_to(template_dir)  # 获取相对路径
                # 处理文件名替换
                relative_path_name = str(relative_path.with_suffix(''))  # 去掉 .j2 扩展名
                for key, value in variables.items():
                    relative_path_name = relative_path_name.replace(f'{{{{ {key} }}}}', value)
                output_path = output_dir / relative_path_name
                # 创建生成目录
                output_path.parent.mkdir(parents=True, exist_ok=True)
                # 渲染模板文件
                template = env.get_template(str(relative_path.as_posix()))
                rendered_content = template.render(variables)
                # 写入生成文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)
            typer.echo(f"模块 '{name}' 生成完成，存放在 '{output_dir}'.")
            return True
        except FileExistsError:
            typer.echo(
                typer.style(
                    f"目录 '{module_path}' 已经存在。",
                    fg=typer.colors.YELLOW,
                    bold=True,
                )
            )
    else:
        typer.echo(typer.style(f"目录 '{module_path}' 已经存在。", fg=typer.colors.YELLOW, bold=True))
    return False


def map_column_type(column_type):
    # (py_type, import_stmt)
    type_mapping = {
        ARRAY: ('list', '', None),
        BIGINT: ('int', 'from sqlmodel import BIGINT', 'BIGINT'),
        BigInteger: ('int', 'from sqlmodel import BigInteger', 'BigInteger'),
        BINARY: ('bytes', 'from sqlmodel import BINARY', None),
        BLOB: ('bytes', 'from sqlmodel import BLOB', None),
        BOOLEAN: ('bool', '', None),
        Boolean: ('bool', '', None),
        CHAR: ('str', '', None),
        CLOB: ('str', '', None),
        Concatenable: ('str', '', None),  # TODO
        DATE: ('date', 'from datetime import date', None),
        Date: ('date', 'from datetime import date', None),
        DATETIME: ('datetime', 'from datetime import datetime', None),
        DateTime: ('datetime', 'from datetime import datetime', None),
        DECIMAL: ('Decimal', 'from decimal import Decimal', None),
        DOUBLE: ('float', '', None),
        DOUBLE_PRECISION: ('float', '', None),
        Enum: ('Enum', 'from enum import Enum', None),
        FLOAT: ('float', '', None),
        Float: ('float', '', None),
        Indexable: ('any', '', None),  # TODO
        INT: ('int', '', None),
        INTEGER: ('int', '', None),
        Integer: ('int', '', None),
        Interval: ('any', '', None),  # TODO
        JSON: ('dict', 'from sqlmodel import JSON', 'JSON'),
        LargeBinary: ('bytes', '', None),
        MatchType: ('any', '', None),  # TODO
        NCHAR: ('str', '', None),
        NULLTYPE: ('any', '', None),  # TODO
        NullType: ('any', '', None),  # TODO
        NUMERIC: ('Decimal', '', None),
        Numeric: ('Decimal', '', None),
        NVARCHAR: ('str', '', None),
        PickleType: ('any', '', None),  # TODO
        REAL: ('float', '', None),
        SchemaType: ('any', '', None),  # TODO
        SMALLINT: ('int', '', None),
        SmallInteger: ('int', '', None),
        String: ('str', '', None),
        STRINGTYPE: ('str', '', None),  # TODO
        TEXT: ('str', 'from sqlmodel import Text', 'Text'),
        Text: ('str', 'from sqlmodel import Text', 'Text'),
        TIME: ('time', 'from datetime import time', None),
        Time: ('time', 'from datetime import time', None),
        TIMESTAMP: ('datetime', '', None),
        TupleType: ('str', '', None),  # TODO
        Unicode: ('str', '', None),
        UnicodeText: ('str', '', None),
        TypeDecorator: ('str', '', None),  # TODO
        UUID: ('UUID', 'from uuid import UUID', None),
        Uuid: ('UUID', 'from uuid import UUID', None),
        VARBINARY: ('bytes', '', None),
        VARCHAR: ('str', '', None),
    }
    for sql_type, (py_type, import_stmt, sa_type) in type_mapping.items():
        if isinstance(column_type, sql_type):
            max_length = getattr(column_type, 'length', None)
            return {
                'type': py_type,
                'import_stmt': import_stmt,
                'max_length': max_length,
                'sa_type': sa_type,
            }

    # Default to str if type is unknown
    return {'type': 'str', 'import_stmt': '', 'max_length': None, 'sa_type': None}


async def get_tables(tables: str, db_url: str | None = None) -> dict:
    tables = tables.split(',') if tables else None
    from senweaver.db.session import create_engine_by_url

    engine = create_engine_by_url(db_url)
    try:
        # 创建元数据对象
        from sqlalchemy import Inspector, inspect

        metadata = MetaData()
        async with engine.begin() as conn:
            await conn.run_sync(
                metadata.reflect,
                # bind=conn.sync_engine,
                # schema=[None],
                only=tables,
            )

            def fetch_table_info(sync_conn):
                table_dict = {}
                for table_name, table in metadata.tables.items():
                    inspector: Inspector = inspect(sync_conn)
                    columns = inspector.get_columns(table_name)
                    primary_keys = inspector.get_pk_constraint(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    indexes = inspector.get_indexes(table_name)
                    unique_constraints = inspector.get_unique_constraints(table_name)
                    imports = {'from sqlmodel import Field, SQLModel'}
                    unique_constraints_names = {
                        col_name for index in unique_constraints for col_name in index['column_names']
                    }
                    indexes_names = {col_name for index in indexes for col_name in index['column_names']}
                    column_dict = {}

                    for column in columns:
                        column_name = column['name']
                        column['primary_key'] = column['name'] in primary_keys['constrained_columns']
                        column['unique'] = column['name'] in unique_constraints_names
                        column['index'] = column['name'] in indexes_names
                        column_dict[column_name] = column

                    for _column in table.columns:
                        column = column_dict[_column.name]
                        field_info = map_column_type(_column.type)
                        optional = not _column.primary_key and _column.nullable
                        type_annotation = field_info['type']
                        if optional:
                            type_annotation = f'{type_annotation} | None'
                        column['max_length'] = field_info['max_length']
                        column['sa_type'] = field_info['sa_type']
                        column['type_annotation'] = type_annotation
                        column['optional'] = optional
                        # 添加必要的import语句
                        imports.add(field_info['import_stmt'])
                    not_prefix_table = table_name
                    if '_' in table_name:
                        not_prefix_table = table_name.split('_', 1)[-1]
                    table_dict[table_name] = {
                        'table': table,
                        'table_name': table_name,
                        'table_comment': table.comment if table.comment else '',
                        'model_name': to_pascal(table_name),
                        'api_name': not_prefix_table,
                        'logic_name': not_prefix_table,
                        'logic_class_name': to_pascal(not_prefix_table),
                        'columns': columns,
                        'imports': sorted(imports),
                        'primary_keys': primary_keys,
                        'foreign_keys': foreign_keys,
                        'indexes': indexes,
                        'unique_constraints': unique_constraints,
                        'check_constraints': inspector.get_check_constraints(table_name),
                    }
                return table_dict

            info = await conn.run_sync(fetch_table_info)
            return info
    except Exception:
        return None


def generate_sqlmodel_class(table):
    class_attrs = {
        '__tablename__': table.name,
        '__table_args__': {'comment': table.comment} if table.comment else {},
        '__annotations__': {},
    }

    for column in table.columns:
        default = column.default.arg if column.default is not None else None
        field_type = map_column_type(column.type)
        field = Field(
            default=default,
            primary_key=column.primary_key,
            foreign_key=(list(column.foreign_keys)[0]._colspec if column.foreign_keys else None),
            index=column.index,
            unique=column.unique,
            description=column.comment,
        )
        class_attrs['__annotations__'][column.name] = field_type | None
        class_attrs[column.name] = field

    return type(table.name.capitalize(), (SQLModel,), class_attrs)
