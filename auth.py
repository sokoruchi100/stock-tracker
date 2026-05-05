from google.oauth2.service_account import Credentials
import json
import base64
import os

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/gmail.compose"]

def get_credentials(scopes=SCOPES):
    raw = os.environ["GOOGLE_CREDENTIALS_JSON"]
    try:
        creds_dict = json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        creds_dict = json.loads(raw)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes,
    )
    return creds