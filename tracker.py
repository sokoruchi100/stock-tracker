import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from auth import get_credentials
from googleapiclient.discovery import build


def create(title):
    """
    Creates the Sheet the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = get_credentials()
    # pylint: disable=maybe-no-member
    try:
        service = build("sheets", "v4", credentials=creds)
        spreadsheet = {"properties": {"title": title}}
        spreadsheet = (
            service.spreadsheets()
            .create(body=spreadsheet, fields="spreadsheetId")
            .execute()
        )
        print(f"Spreadsheet ID: {(spreadsheet.get('spreadsheetId'))}")
        return spreadsheet.get("spreadsheetId")
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error

def get(spreadsheet_id):
    """
    Gets the spreadsheet with the given ID.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = get_credentials()
    # pylint: disable=maybe-no-member
    try:
        service = build("sheets", "v4", credentials=creds)
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        print(f"Spreadsheet ID: {spreadsheet.get('spreadsheetId')}")
        return spreadsheet
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error

if __name__ == "__main__":
    # Pass: spreadsheet_id
    spreadsheet = get("188mL3GzAb6EdMejSIdKvQnA8yWLWn9jmmFdeqedksxE")
    print(spreadsheet)