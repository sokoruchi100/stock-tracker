import base64
from email.message import EmailMessage

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import auth
import os
from dotenv import load_dotenv

load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")

def gmail_send_message(risk_score, overvalued_score):
    """Create and send an email message
    Print the returned  message id
    Returns: Message object, including message id

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = auth.get_credentials()

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()

        message.set_content(f"You have a new notification from the Stock Tracker!\n\nRisk Score: {risk_score}\nOvervalued Score: {overvalued_score}")

        message["To"] = EMAIL_ADDRESS
        message["From"] = EMAIL_ADDRESS
        message["Subject"] = "Stock Tracker Notification!"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        print(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None
    return send_message


if __name__ == "__main__":
    gmail_send_message(6.5, 75)