# gmail_service.py
# -*- coding: utf-8 -*-
import os.path
import logging
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Ensure stdout uses utf-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

class GmailService:
    """A class to interact with the Gmail API."""

    def __init__(self, credentials_path="credentials.json", token_path="token.json"):
        """
        Initializes the GmailService.

        Args:
            credentials_path (str): The path to the credentials.json file.
            token_path (str): The path to the token.json file.
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._get_service()

    def _get_service(self):
        """
        Authenticates and returns a Gmail API service object.
        """
        creds = None
        if os.environ.get('GOOGLE_CREDENTIALS_BASE64') and os.environ.get('GOOGLE_TOKEN_BASE64'):
            creds_info = json.loads(base64.b64decode(os.environ.get('GOOGLE_CREDENTIALS_BASE64')))
            token_info = json.loads(base64.b64decode(os.environ.get('GOOGLE_TOKEN_BASE64')))
            creds = Credentials.from_authorized_user_info(info=creds_info, token=token_info)
        elif os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    creds = self._run_flow()
            else:
                creds = self._run_flow()
            
            if creds:
                with open(self.token_path, "w") as token:
                    token.write(creds.to_json())
        
        if creds:
            try:
                return build("gmail", "v1", credentials=creds)
            except HttpError as error:
                logger.error(f"An error occurred building the service: {error}")
                return None
        return None

    def _run_flow(self):
        """Runs the OAuth2 flow to get new credentials."""
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
            return creds
        except Exception as e:
            logger.error(f"Failed to run OAuth flow: {e}")
            return None

    def list_messages(self, max_results=20):
        """
        Lists the most recent messages in the user's inbox.
        """
        if not self.service:
            logger.error("Gmail service not available.")
            return

        try:
            results = self.service.users().messages().list(userId="me", labelIds=['INBOX'], maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            if not messages:
                print("No messages found in INBOX.")
                return

            print("--- Recent Messages in INBOX ---")
            for msg_info in messages:
                msg = self.service.users().messages().get(userId='me', id=msg_info['id']).execute()
                headers = msg.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
                print(f"From: {sender}\nSubject: {subject}\n---")

        except HttpError as error:
            logger.error(f"An error occurred: {error}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gmail = GmailService(
        credentials_path="C:/Users/ASRock-PC/code/credentials.json",
        token_path="C:/Users/ASRock-PC/code/token.json"
    )
    if gmail.service:
        gmail.list_messages()