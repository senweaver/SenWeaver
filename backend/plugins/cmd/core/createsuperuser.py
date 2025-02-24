import asyncio

import typer

from config.settings import settings
from senweaver.helper import import_class_module
from senweaver.module.manager import module_manager


def concole(app: typer.Typer):
    @app.command()
    def createsuperuser(
        username: str = typer.Option(..., prompt=True),
        email: str = typer.Option(
            ...,
            prompt=True,
            help="The email address for the new superuser. Example: admin@senweaver.com",
        ),
        password: str = typer.Option(..., prompt=True, hide_input=True),
        confirm_password: str = typer.Option(
            ..., prompt="Confirm password", hide_input=True
        ),
    ):
        if password != confirm_password:
            typer.echo("Passwords do not match.")
            raise typer.Exit(code=1)

        asyncio.run(
            module_manager.auth_module.create_superuser(username, password, email)
        )
        typer.echo(
            f"Superuser created successfully: {
                   username}, Email: {email}"
        )
