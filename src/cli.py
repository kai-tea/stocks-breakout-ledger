import typer
import pandas as pd
from datetime import datetime

import main
from main import add

# --- PANDAS DISPLAY CONFIG ---
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
# -----------------------------

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