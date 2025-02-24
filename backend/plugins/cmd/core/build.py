import typer
from typer import Option, Typer

sub_app = Typer()


def concole(app: typer.Typer):
    app.add_typer(sub_app, name="build")
    pass
