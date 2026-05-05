from google.oauth2.service_account import Credentials
import json
import os

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.compose"]

def get_credentials(scopes=SCOPES):
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes,
    )
    return creds