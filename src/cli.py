import typer

from typing import Annotated

app = typer.Typer()

@app.command()

def add(
        ticker: str,
        date: str
):
    print(f"Hello {ticker} world")

if __name__ == "__main__":
    app()