import typer

from senweaver.server import run_app, start_command

cli_app = typer.Typer()


@cli_app.command(help="Run the FastAPI app")
def run():
    typer.echo("This is the default command.")
    run_app()


if __name__ == "__main__":
    start_command(cli_app)
    cli_app()
