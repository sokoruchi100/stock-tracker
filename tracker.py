from wsgiref import headers

from auth import get_credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from dotenv import load_dotenv
import yfinance as yf
from fredapi import Fred
import time
import pandas as pd
import numpy as np
from datetime import date
from email_messager import send_alert
import sys

load_dotenv()

START_DATE = "2026-04-27"
RISK_POSITION = "B15"
VALUED_POSITION = "B21"

def get_config():
    result = batch_get_values(os.getenv("SPREADSHEET_ID"), "Config!A1:B4")
    rows = result["valueRanges"][0].get("values", [])
    raw = {row[0]: row[1] for row in rows if len(row) >= 2}
    return {
        "UPPER_RISK_THRESHOLD":  float(raw["UPPER RISK THRESHOLD"]),
        "LOWER_RISK_THRESHOLD":  float(raw["LOWER RISK THRESHOLD"]),
        "OVERVALUED_THRESHOLD":  float(raw["OVERVALUED THRESHOLD"]),
        "UNDERVALUED_THRESHOLD": float(raw["UNDERVALUED THRESHOLD"]),
    }

def batch_update_values(
    spreadsheet_id, range_name, value_input_option, _values
):
    """
    Creates the batch_update the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = get_credentials()
    # pylint: disable=maybe-no-member
    try:
        service = build("sheets", "v4", credentials=creds)

        values = _values
        data = [
            {"range": range_name, "values": values},
        ]
        body = {"valueInputOption": value_input_option, "data": data}
        result = (
            service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
            .execute()
        )
        print(f"{(result.get('totalUpdatedCells'))} cells updated.")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error
    
def batch_get_values(spreadsheet_id, *_range_names):
    """
    Creates the batch_update the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = get_credentials()
    # pylint: disable=maybe-no-member
    try:
        service = build("sheets", "v4", credentials=creds)
        range_names = [name for name in _range_names]
        result = (
            service.spreadsheets()
            .values()
            .batchGet(spreadsheetId=spreadsheet_id, ranges=range_names)
            .execute()
        )
        ranges = result.get("valueRanges", [])
        print(f"{len(ranges)} ranges retrieved")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error

def get_price(ticker, for_date=None):
    t = yf.Ticker(ticker)
    if for_date is None or pd.to_datetime(for_date).date() == date.today():
        price = t.fast_info.get("last_price")
        if price is not None:
            return price
        return t.history(period="5d")["Close"].iloc[-1]
    end = pd.to_datetime(for_date) + pd.Timedelta(days=4)
    hist = t.history(start=for_date, end=end)["Close"]
    return hist.iloc[0]

def get_10y_2y_yield_curve(for_date=None, retries=3):
    fred = Fred(api_key=os.environ.get("FRED_API_KEY"))
    for i in range(retries):
        try:
            return fred.get_series('T10Y2Y', observation_end=for_date).iloc[-1]
        except ValueError:
            if i < retries - 1:
                time.sleep(2)
    raise RuntimeError("FRED API unavailable after retries")

def get_credit_spread(for_date=None, retries=3):
    fred = Fred(api_key=os.environ.get("FRED_API_KEY"))
    for i in range(retries):
        try:
            return fred.get_series('BAMLH0A0HYM2', observation_end=for_date).iloc[-1]
        except ValueError:
            if i < retries - 1:
                time.sleep(2)
    raise RuntimeError("FRED API unavailable after retries")

def get_sp500_tickers():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    table = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        storage_options={"User-Agent": headers["User-Agent"]}
    )[0]
    return table["Symbol"].str.replace(".", "-", regex=False).tolist()


def get_breadth(tickers=None, for_date=None, weighting="equal"):
    if tickers is None:
        tickers = get_sp500_tickers()

    end = pd.to_datetime(for_date) + pd.Timedelta(days=4) if for_date else None
    start = pd.to_datetime(for_date) - pd.Timedelta(days=365) if for_date else None

    above_200 = []
    failed = []

    prices = yf.download(tickers, period="1y", group_by="ticker", auto_adjust=True, progress=False)

    for ticker in tickers:
        try:
            hist = prices[ticker]["Close"] if ticker in prices else yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)["Close"]

            if len(hist) < 200:
                continue

            ma200 = hist.rolling(200).mean().iloc[-1]
            price = hist.iloc[-1]
            above_200.append(int(price > ma200))

        except Exception as e:
            failed.append(ticker)
            continue

    if not above_200:
        raise ValueError("No valid data returned.")

    breadth = round(sum(above_200) / len(above_200) * 100, 1)

    if failed:
        print(f"[warn] {len(failed)} tickers failed: {failed[:10]}{'...' if len(failed) > 10 else ''}")

    print(f"[info] {sum(above_200)}/{len(above_200)} stocks above 200DMA")
    return breadth

def input_data(for_date=None):
    if for_date is None:
        for_date = date.today()
    for_date = pd.to_datetime(for_date).date()

    SP500 = round(get_price("^GSPC", for_date), 2)
    TenYear = round(get_price("^TNX", for_date), 2)
    YieldCurve = round(get_10y_2y_yield_curve(for_date=for_date), 2)
    CreditSpread = round(get_credit_spread(for_date=for_date), 2)
    Breadth = round(get_breadth(for_date=for_date), 2)

    print(f"SP500: {SP500}, TenYear: {TenYear}, YieldCurve: {YieldCurve}, CreditSpread: {CreditSpread}, Breadth: {Breadth}")

    batch_update_values(
        os.getenv("SPREADSHEET_ID"),
        "B5:B9",
        "USER_ENTERED",
        [[SP500], [TenYear], [YieldCurve], [CreditSpread], [Breadth]],
    )

    risk_score = batch_get_values(os.getenv("SPREADSHEET_ID"), RISK_POSITION)["valueRanges"][0].get("values", [["0"]])[0][0]
    valued_score = batch_get_values(os.getenv("SPREADSHEET_ID"), VALUED_POSITION)["valueRanges"][0].get("values", [["0"]])[0][0]

    date_diff = (pd.to_datetime(for_date) - pd.to_datetime(START_DATE)).days
    graph_position = f"F{2 + date_diff}:G{2 + date_diff}"

    batch_update_values(
        os.getenv("SPREADSHEET_ID"),
        graph_position,
        "USER_ENTERED",
        [[for_date.strftime("%Y-%m-%d"), risk_score]],
    )

    config = get_config()
    print(config)

    if float(risk_score) >= config["UPPER_RISK_THRESHOLD"] or float(risk_score) <= config["LOWER_RISK_THRESHOLD"] or float(valued_score) >= config["OVERVALUED_THRESHOLD"] or float(valued_score) <= config["UNDERVALUED_THRESHOLD"]:
        send_alert(risk_score, valued_score)

if __name__ == "__main__":
    input_data(sys.argv[1] if len(sys.argv) > 1 else None)