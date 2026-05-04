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

load_dotenv()
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
fred = Fred(api_key=os.getenv("FRED_API_KEY"))

START_DATE = "2026-04-27"
RISK_POSITION = "B15"

# Representative sample of large caps across sectors
sample = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",  # Tech
    "JPM", "BAC", "GS", "WFC", "MS",            # Finance
    "JNJ", "UNH", "PFE", "MRK", "ABT",          # Healthcare
    "XOM", "CVX", "COP", "SLB", "EOG",          # Energy
    "WMT", "HD", "MCD", "NKE", "SBUX",          # Consumer
    "CAT", "BA", "GE", "MMM", "HON",            # Industrial
    "NEE", "DUK", "SO", "D", "AEP",              # Utilities
    "ENPH", "SEDG", "RUN", "ARRY",    # solar/clean energy
    "AFRM", "UPST", "LC", "SOFI", "NU",        # fintech
    "DKNG", "PENN", "CZR", "MGM", "WYNN",      # gaming/leisure
    "AAL", "UAL", "DAL", "LUV", "ALK",         # airlines
    "RKT", "OPEN", "Z", "TREX"         # housing adjacent
]

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
    end = pd.to_datetime(for_date) + pd.Timedelta(days=4) if for_date else None
    hist = t.history(start=for_date, end=end)["Close"]
    return hist.iloc[0]

def get_credit_spread(for_date=None, retries=3):
    for i in range(retries):
        try:
            return fred.get_series('BAMLH0A0HYM2', observation_end=for_date).iloc[-1]
        except ValueError:
            if i < retries - 1:
                time.sleep(2)
    raise RuntimeError("FRED API unavailable after retries")

def get_breadth(for_date=None):
    end = pd.to_datetime(for_date) + pd.Timedelta(days=4) if for_date else None
    start = pd.to_datetime(for_date) - pd.Timedelta(days=365) if for_date else None

    results = []
    weights = []
    for ticker in sample:
        try:
            hist = yf.Ticker(ticker).history(start=start, end=end, period=None if for_date else "1y")["Close"]
            if len(hist) >= 200:
                vol = hist.pct_change().std()
                above = int(hist.iloc[-1] > hist.rolling(200).mean().iloc[-1])
                results.append(above)
                weights.append(vol)
        except:
            continue

    weights = np.array(weights)
    weights = weights / weights.sum()
    return round(float(np.dot(results, weights) * 100), 1)

def input_data(for_date=None):
    if for_date is None:
        for_date = date.today()
    for_date = pd.to_datetime(for_date).date()

    SP500 = round(get_price("^GSPC", for_date), 2)
    TenYear = round(get_price("^TNX", for_date), 2)
    YieldCurve = round(get_price("^TNX", for_date) - get_price("^IRX", for_date), 2)
    CreditSpread = round(get_credit_spread(for_date), 2)
    Breadth = round(get_breadth(for_date), 2)

    print(f"SP500: {SP500}, TenYear: {TenYear}, YieldCurve: {YieldCurve}, CreditSpread: {CreditSpread}, Breadth: {Breadth}")

    batch_update_values(
        SPREADSHEET_ID,
        "B5:B9",
        "USER_ENTERED",
        [[SP500], [TenYear], [YieldCurve], [CreditSpread], [Breadth]],
    )

    risk_score = batch_get_values(SPREADSHEET_ID, RISK_POSITION)["valueRanges"][0].get("values", [["0"]])[0][0]
    date_diff = (pd.to_datetime(for_date) - pd.to_datetime(START_DATE)).days
    graph_position = f"F{2 + date_diff}:G{2 + date_diff}"

    batch_update_values(
        SPREADSHEET_ID,
        graph_position,
        "USER_ENTERED",
        [[for_date.strftime("%Y-%m-%d"), risk_score]],
    )

if __name__ == "__main__":
    import sys
    input_data(sys.argv[1] if len(sys.argv) > 1 else None)