# intelligent_agent_platform/tools/common_auth.py

import os
import streamlit as st  # <-- THÊM IMPORT NÀY
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES, TOKEN_FILE, CREDENTIALS_FILE

def get_google_service(service_name: str, version: str):
    """
    Xác thực và xây dựng một đối tượng service của Google.
    Sử dụng st.session_state để cache service một cách an toàn cho mỗi session người dùng.
    """
    # Khởi tạo kho chứa services trong session_state nếu chưa có
    if 'services' not in st.session_state:
        st.session_state.services = {}

    # Kiểm tra cache trong session_state
    if service_name in st.session_state.services:
        return st.session_state.services[service_name]

    # --- Phần code xác thực giữ nguyên ---
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Hiển thị thông báo trên giao diện khi đang làm mới token
            with st.spinner(f"Đang làm mới quyền truy cập cho Google {service_name.capitalize()}..."):
                creds.refresh(Request())
        else:
            # Logic này sẽ không chạy tốt trên server Streamlit đã deploy
            # vì nó yêu cầu tương tác cục bộ. Nó chỉ hoạt động khi bạn chạy trên máy.
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Lỗi: Không tìm thấy file {CREDENTIALS_FILE}.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Lưu lại token mới
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    
    try:
        # Build service
        service = build(service_name, version, credentials=creds)
        # Lưu vào cache của session_state
        st.session_state.services[service_name] = service
        return service
    except Exception as e:
        st.error(f"Lỗi khi xây dựng service Google {service_name.capitalize()}: {e}")
        return None