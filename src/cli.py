import typer
import pandas as pd
from datetime import datetime

import main
from main import add


app = typer.Typer()

@app.command()
def add(
        ticker: str,
        date: datetime = typer.Argument(..., formats=["%Y-%m-%d"]) # converts to datetime.strptime()
):
    print(f"adding:\t\t{ticker}\t{date}")
    try:
        main.add(ticker, date)
        #print(f"ticker added")
    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    app()