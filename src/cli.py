import typer
from typing import Annotated
from datetime import datetime

import main
from main import add

app = typer.Typer()

@app.command()

def add(
        ticker: str,
        date: datetime = typer.Argument(..., formats=["%Y-%m-%d"]) # converts to datetime.strptime()
):
    print(f"ticker:\t{ticker} \ndate:\t{date}")
    print(f"day: {date.day}")

    try:
        main.add(ticker, date)
        print(f"ticker added")
    except ValueError as e:
        print(f"Error: {e}")




if __name__ == "__main__":
    app()