
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES, TOKEN_FILE, CREDENTIALS_FILE
from dotenv import load_dotenv; load_dotenv()
# Global cache cho service để không phải build lại mỗi lần gọi tool
_services = {}
import base64
import json

def save_credentials_from_env():
    if not os.path.exists(CREDENTIALS_FILE):
        encoded = os.getenv("GOOGLE_CREDENTIALS_JSON_BASE64")
        if not encoded:
            raise Exception("Missing GOOGLE_CREDENTIALS_JSON_BASE64 env variable")
        decoded = base64.b64decode(encoded)
        with open(CREDENTIALS_FILE, "wb") as f:
            f.write(decoded)
            
def get_google_service(service_name: str, version: str):
    save_credentials_from_env()
    """
    Xác thực và xây dựng một đối tượng service của Google.
    Sử dụng cache để tăng hiệu suất.
    """
    if service_name in _services:
        return _services[service_name]

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Lỗi: Không tìm thấy file {CREDENTIALS_FILE}.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    
    try:
        service = build(service_name, version, credentials=creds)
        _services[service_name] = service # Lưu vào cache
        return service
    except Exception as e:
        print(f"Lỗi khi xây dựng service Google {service_name.capitalize()}: {e}")
        return None