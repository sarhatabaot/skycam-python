import typer
from rich import print

from skycam_common.core import hello

app = typer.Typer(help="Skycam CLI")

@app.command()
def greet(name: str = "world") -> None:
    """Print a friendly greeting."""
    print(hello(name))

def main() -> None:
    app()
