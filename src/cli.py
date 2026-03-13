import typer
import csv
import pandas as pd
from datetime import datetime

import main
from main import add
from config import INPUT_FILE, OUTPUT_FILE

app = typer.Typer()

@app.command("parse")
def parse_input_file(input_file: str = INPUT_FILE):
    with open(input_file, mode='r') as file:
        reader = csv.DictReader(file)

        # delete old output.csv if it exists
        OUTPUT_FILE.unlink(missing_ok=True)

        # add ticker row by row
        for row in reader:
            ticker = row['ticker']
            date = row['date']
            print()
            print(f"ticker: {ticker} {date}", end="\t")
            try:
                add(ticker.lower(), datetime.strptime(date, "%Y-%m-%d"))
            except FileNotFoundError as e:
                print(e, end="")
            except ValueError as e:
                print(f"could not convert date: {date}", end="")


@app.command("add")
def add_ticker(
        ticker: str,
        date: datetime = typer.Argument(..., formats=["%Y-%m-%d"]) # converts to datetime.strptime()
):
    print(f"adding:\t\t{ticker} {date.date()}")
    try:
        add(ticker, date)
        #print(f"ticker added")
    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    app()