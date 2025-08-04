import os.path
import datetime
from typing import Optional, List

# --- Các thư viện của Google ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Các thư viện của LangChain & Pydantic ---
from langchain_core.tools import tool
from pydantic.v1 import BaseModel, Field

# Định nghĩa Scopes - chúng ta chỉ cần quyền quản lý tasks
SCOPES = ["https://www.googleapis.com/auth/tasks"]

# --- HÀM HỖ TRỢ XÁC THỰC ---
def get_tasks_service():
    """
    Xác thực với Google API và trả về một đối tượng service 
    để tương tác với Google Tasks.
    """
    creds = None
    # File token.json lưu trữ token truy cập của người dùng.
    # Nó được tạo tự động sau lần xác thực đầu tiên.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # Nếu không có credentials hợp lệ, yêu cầu người dùng đăng nhập.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Hãy chắc chắn bạn đã tải file credentials.json từ Google Cloud Console
            # và đặt nó vào cùng thư mục.
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                print("LỖI: Không tìm thấy file 'credentials.json'. Vui lòng tải về và đặt vào thư mục dự án.")
                return None

        # Lưu credentials cho lần chạy tiếp theo
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # Xây dựng và trả về service object
    service = build("tasks", "v1", credentials=creds)
    return service

# --- ĐỊNH NGHĨA CÁC TOOL CHO AGENT ---

# Tool 1: Tạo một công việc mới
class CreateTaskInput(BaseModel):
    title: str = Field(..., description="Tiêu đề của công việc. Đây là tham số bắt buộc.")
    notes: Optional[str] = Field(None, description="Ghi chú hoặc mô tả chi tiết cho công việc.")
    due_date: Optional[str] = Field(None, description="Ngày hết hạn của công việc theo định dạng YYYY-MM-DD.")

@tool("create_google_task", args_schema=CreateTaskInput)
def create_task(title: str, notes: Optional[str] = None, due_date: Optional[str] = None) -> str:
    """Sử dụng tool này để tạo một công việc mới trong Google Tasks. Cung cấp tiêu đề, và tùy chọn ghi chú hoặc ngày hết hạn."""
    try:
        service = get_tasks_service()
        if not service: return "Lỗi xác thực Google."

        # Logic kiểm tra task trùng lặp
        existing_tasks = service.tasks().list(tasklist='@default', showCompleted=False).execute().get('items', [])
        for task in existing_tasks:
            if task.get('title', '').lower() == title.lower():
                return f"Cảnh báo: Một công việc với tiêu đề '{title}' đã tồn tại. Không tạo task mới."

        task_body = {"title": title}
        if notes:
            task_body["notes"] = notes
        if due_date:
            # Chuyển đổi YYYY-MM-DD sang định dạng RFC3339 mà Google API yêu cầu
            # Ví dụ: 2025-08-15 -> 2025-08-15T00:00:00.000Z
            task_body["due"] = f"{due_date}T00:00:00.000Z"
            
        result = service.tasks().insert(tasklist="@default", body=task_body).execute()
        return f"Tạo công việc thành công! Tên: '{result['title']}', ID: {result['id']}"
    except HttpError as error:
        return f"Đã xảy ra lỗi khi tạo công việc: {error}"


# Tool 2: Tìm kiếm công việc theo từ khóa
class SearchTaskInput(BaseModel):
    query: str = Field(..., description="Từ khóa để tìm kiếm trong tiêu đề hoặc ghi chú của công việc.")

@tool("search_google_tasks", args_schema=SearchTaskInput)
def search_tasks(query: str) -> List[dict]:
    """Sử dụng tool này để tìm kiếm các công việc dựa trên một từ khóa. Nó sẽ tìm trong cả tiêu đề và ghi chú."""
    try:
        service = get_tasks_service()
        if not service: return "Lỗi xác thực Google."
        
        all_tasks = service.tasks().list(tasklist='@default', showCompleted=False).execute().get('items', [])
        
        # Lọc các task bằng Python vì API không hỗ trợ tìm kiếm toàn văn bản
        matching_tasks = [
            task for task in all_tasks 
            if query.lower() in task.get('title', '').lower() or query.lower() in task.get('notes', '').lower()
        ]
        
        if not matching_tasks:
            return "Không tìm thấy công việc nào khớp với từ khóa của bạn."

        # Chỉ trả về thông tin cần thiết để LLM dễ xử lý
        return [
            {"id": task["id"], "title": task["title"], "due": task.get("due", "Không có")}
            for task in matching_tasks
        ]
    except HttpError as error:
        return f"Đã xảy ra lỗi khi tìm kiếm công việc: {error}"


# Tool 3: Tìm các công việc sắp hết hạn
class FindNearDueDateInput(BaseModel):
    days: int = Field(7, description="Số ngày tính từ hôm nay để tìm các công việc sắp hết hạn. Mặc định là 7 ngày.")

@tool("find_near_due_date_tasks", args_schema=FindNearDueDateInput)
def find_near_due_date_tasks(days: int = 7) -> List[dict]:
    """Sử dụng tool này để tìm các công việc sắp hết hạn trong vòng X ngày tới. Ví dụ 'việc gì cần làm trong tuần này?'."""
    try:
        service = get_tasks_service()
        if not service: return "Lỗi xác thực Google."

        now = datetime.datetime.utcnow()
        due_max_dt = now + datetime.timedelta(days=days)
        
        # Định dạng thời gian theo RFC3339 cho API
        due_min_str = now.isoformat() + "Z"
        due_max_str = due_max_dt.isoformat() + "Z"

        results = service.tasks().list(
            tasklist="@default",
            dueMin=due_min_str,
            dueMax=due_max_str,
            showCompleted=False
        ).execute()
        
        tasks = results.get("items", [])
        if not tasks:
            return f"Không có công việc nào sắp hết hạn trong vòng {days} ngày tới."

        return [
            {"id": task["id"], "title": task["title"], "due": task.get("due")}
            for task in tasks
        ]
    except HttpError as error:
        return f"Đã xảy ra lỗi khi tìm công việc sắp hết hạn: {error}"

# Chúng ta sẽ thêm tool `mark_task_as_completed` sau khi xây dựng agent cơ bản.