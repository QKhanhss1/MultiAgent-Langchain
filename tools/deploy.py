import os
import json
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES

_services = {}

def get_google_service(service_name: str, version: str):
    """
    Xác thực và xây dựng một đối tượng service của Google.
    Hàm này ưu tiên đọc cấu hình OAuth từ Streamlit Secrets (biến môi trường),
    và quay về đọc file 'credentials.json' khi chạy local.
    """
    if service_name in _services:
        return _services[service_name]

    creds = None
    if 'google_credentials' in st.session_state:
        creds = st.session_state.google_credentials
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = None
            try:
                # --- LOGIC MỚI: Ưu tiên đọc từ st.secrets ---
                client_config = {
                    "web": {
                        "client_id": st.secrets["G_CLIENT_ID"],
                        "project_id": st.secrets["G_PROJECT_ID"],
                        "auth_uri": st.secrets["G_AUTH_URI"],
                        "token_uri": st.secrets["G_TOKEN_URI"],
                        "client_secret": st.secrets["G_CLIENT_SECRET"],
                        "redirect_uris": [st.secrets["G_REDIRECT_URI"]]
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            except (AttributeError, KeyError):
                # Nếu không có secrets (chạy local), quay về đọc file
                print("DEBUG: Không tìm thấy secrets của Google, đang đọc từ file credentials.json...")
                if not os.path.exists("credentials.json"):
                    raise FileNotFoundError("Chạy ở local nhưng không tìm thấy file credentials.json.")
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            
            # Chạy luồng xác thực. Trên Streamlit Cloud, nó sẽ tự động xử lý chuyển hướng.
            # Trên local, nó sẽ mở trình duyệt.
            creds = flow.run_local_server(port=0)

        st.session_state.google_credentials = creds
    
    try:
        service = build(service_name, version, credentials=creds)
        _services[service_name] = service
        return service
    except Exception as e:
        print(f"Lỗi khi xây dựng service Google {service_name.capitalize()}: {e}")
        return None