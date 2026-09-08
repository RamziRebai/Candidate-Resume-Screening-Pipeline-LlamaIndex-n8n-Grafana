# backend/bootstrap_drive_auth.py
"""Run ONCE to mint token.json:  python bootstrap_drive_auth.py"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

BASE = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS = os.path.join(BASE, "credentials.json")
TOKEN = os.path.join(BASE, "token.json")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]   # must match GOOGLE_DRIVE_SCOPES

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

def upload_drive():
    with open(TOKEN, "w") as f:
        f.write(creds.to_json())

    print(f"✓ token.json written to {TOKEN}")
    print(f"  refresh_token present: {bool(creds.refresh_token)}")


if __name__=="__main__":
    upload_drive()