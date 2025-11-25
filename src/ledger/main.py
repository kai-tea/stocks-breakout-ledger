from datetime import datetime
from typing import Annotated

import storage
import typer

app = typer.Typer()

# TODO:
#   - link with storage.py
#   - cleanup

@app.command()
def add(
        ticker: Annotated[str, typer.Option("--ticker", "-t", help="MM DD YYYY")],
        date: Annotated[str, typer.Option("--date", "-d")]
):
    from date_util import parse_date
    from storage import add_entry

    ticker = ticker.upper()
    print(f"ticker: {ticker}")

    d = parse_date(date)
    if d is None:
        typer.secho(f"Invalid date: '{date}'. Expected 'mm dd yyyy'")
        raise typer.Exit(code=2)

    if add_entry(ticker, d) is False:
        typer.secho(f"Could not add ticker '{ticker}'")
        raise typer.Exit(code=2)

    print(f"added: {ticker}, {date}")

if __name__ == "__main__":
    app()