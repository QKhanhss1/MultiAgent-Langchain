# google_calendar_agent/config.py

# --- Cấu hình API của Google ---
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.readonly"
]
# ID đặc biệt cho các service
TASK_LIST_ID = '@default'
CALENDAR_ID = 'primary'

# Tên file xác thực
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'
# --- Cấu hình Model ---
# Chọn model mạnh mẽ để xử lý các yêu cầu phức tạp về thời gian
MODEL_NAME = "gemini-2.5-flash" 
MODEL_TEMPERATURE = 0.2