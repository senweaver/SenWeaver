import sys
import time

import typer

app = typer.Typer()
start_time = time.time()


@app.command()
def run():
    """Run the FastAPI application."""
    from senweaver.server import run_app

    typer.echo("Starting SenWeaver application...")
    run_app()


if __name__ == "__main__":
    from senweaver.command import register_commands

    register_commands(app)
    if len(sys.argv) == 1:
        # 如果没有参数，默认执行 run 命令
        sys.argv.append("run")
    app()
