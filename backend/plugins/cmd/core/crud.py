import asyncio
from pathlib import Path

import typer
from jinja2 import Environment, FileSystemLoader
from pydantic.alias_generators import to_camel, to_pascal
from sqlalchemy import MetaData, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from typer import Option, Typer

from config.settings import settings
from senweaver.db.session import async_engine

from ..helper import get_tables, map_column_type
from ..sqlacodegen.generators import SQLModelGenerator

sub_app = Typer(invoke_without_command=True)

# 定义自定义过滤器


async def sqlacodegen_crud(tables: str, force: bool, output: str, db_url: str) -> None:
    # 准备生成目录的路径
    output_dir = settings.ROOT_PATH.joinpath(output)  # 替换成你希望生成的目录路径
    if not output_dir.exists():
        typer.echo(typer.style(f"{output_dir} 不存在", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)

    module_name = output.split("/")[-1]
    template_dir = (
        Path(__file__).resolve().parent.parent.joinpath("resource/template/crud")
    )
    # 准备 Jinja2 环境
    env = Environment(loader=FileSystemLoader(template_dir))
    tables = tables.split(",") if tables else None
    async_session = AsyncSession(async_engine)
    for table_name in tables:
        metadata = MetaData()
        async with async_engine.begin() as conn:
            await conn.run_sync(
                metadata.reflect,
                # bind=conn.sync_engine,
                # schema=[None],
                only=[table_name],
            )
        generator = SQLModelGenerator(
            metadata=metadata, bind=async_session.get_bind(), options={}
        )
        variables = generator.generate_one()
        not_prefix_table = table_name
        if "_" in table_name:
            not_prefix_table = table_name.split("_", 1)[-1]
        pascal_name = to_pascal(not_prefix_table)
        camel_table_name = to_camel(table_name)
        pascal_table_name = to_pascal(table_name)
        variables["model_name"] = pascal_name  # 去掉前缀
        variables["table_name"] = table_name
        variables["camel_table_name"] = camel_table_name
        variables["pascal_table_name"] = pascal_table_name
        variables["api_name"] = not_prefix_table
        variables["logic_name"] = not_prefix_table
        variables["model_file_name"] = not_prefix_table
        variables["module_name"] = module_name
        variables["web_module_name"] = module_name
        variables["web_module_path_name"] = f"/{module_name}"
        variables["base_api"] = f"{module_name}/{not_prefix_table}"

        variables["web_locale_name"] = f"{camel_table_name}"
        variables["resource_name"] = f"{module_name}:{not_prefix_table}"
        # if table_name.startswith("sys_"):
        #     variables["web_module_name"] = "system"
        #     variables["web_module_path_name"] = f"//system"
        #     variables["web_locale_name"] = f"system{pascal_name}"
        variables["logic_class_name"] = pascal_name
        template_files = template_dir.rglob("*.j2")
        for template_path in template_files:
            relative_path = template_path.relative_to(template_dir)  # 获取相对路径
            # 处理文件名替换
            relative_path_name = str(relative_path.with_suffix(""))  # 去掉 .j2 扩展名
            for key, value in variables.items():
                if isinstance(value, str):
                    relative_path_name = relative_path_name.replace(
                        f"{{{{ {key} }}}}", value
                    )
            output_path = output_dir / relative_path_name
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # 渲染模板文件
            template = env.get_template(str(relative_path.as_posix()))
            rendered_content = template.render(variables)
            # 写入生成文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_content)


async def create_crud(tables: str, force: bool, output: str, db_url: str) -> None:
    # 准备生成目录的路径
    output_dir = settings.ROOT_PATH.joinpath(output)  # 替换成你希望生成的目录路径
    if not output_dir.exists():
        typer.echo(typer.style(f"{output_dir} 不存在", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)

    table_dict = await get_tables(tables, db_url)
    if table_dict is None:
        typer.echo(
            typer.style(
                f"The table '{tables}' is invalid.", fg=typer.colors.RED, bold=True
            )
        )
        raise typer.Exit(code=1)
    template_dir = (
        Path(__file__).resolve().parent.parent.joinpath("resource/template/crud")
    )
    for table in table_dict.values():
        variables = table
        variables["force"] = force

        # 准备 Jinja2 环境
        env = Environment(loader=FileSystemLoader(template_dir))
        # 遍历模板目录中的文件并渲染生成
        for template_path in template_dir.rglob("*.j2"):
            relative_path = template_path.relative_to(template_dir)  # 获取相对路径
            # 处理文件名替换
            relative_path_name = str(relative_path.with_suffix(""))  # 去掉 .j2 扩展名
            for key, value in variables.items():
                if isinstance(value, str):
                    relative_path_name = relative_path_name.replace(
                        f"{{{{ {key} }}}}", value
                    )
            output_path = output_dir / relative_path_name
            # 渲染模板文件
            template = env.get_template(str(relative_path.as_posix()))
            rendered_content = template.render(variables)
            # 写入生成文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_content)


@sub_app.callback()
def crud(
    tables: str = typer.Option(
        ..., "--table", "-t", help="tables to generate,comma-separated"
    ),
    output: str = typer.Option(..., "--out", "-o", help="output path"),
    force: bool = typer.Option(None, "--force", "-f", help="force overwrite"),
    db_url: str = typer.Option(None, "--db_url", "-url", help="async database url"),
):
    asyncio.run(sqlacodegen_crud(tables, force, output, db_url))


def concole(app: typer.Typer):
    app.add_typer(sub_app, name="crud")
    pass
