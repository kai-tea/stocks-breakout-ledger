from datetime import datetime
from typing import Annotated

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

    print(f"ticker: {ticker}")
    try:
        if "-" in date:
            d = datetime.strptime(date, "%m-%d-%y").date()
        else:
            d = parse_date(date)
    except Exception as e:
        typer.secho(f"Invalid date: {e}", fg="red")
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()