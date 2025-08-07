
import datetime
from typing import Annotated, Sequence, TypedDict, Optional, List

from googleapiclient.errors import HttpError

from langchain_core.tools import tool

# Import hàm xác thực chung và cấu hình
# from .common_auth import get_google_service
from tools.auth.deploy import get_google_service
from config import TASK_LIST_ID
SERVICE_NAME = "tasks"
VERSION = "v1"
def _format_due_date(date_str: str) -> Optional[str]:
    """Chuyển đổi ngày YYYY-MM-DD thành định dạng RFC3339 mà Google API yêu cầu."""
    try:
        # Giả sử người dùng nhập ngày, chúng ta đặt giờ là nửa đêm UTC
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.isoformat() + "Z"
    except (ValueError, TypeError):
        # Nếu định dạng sai hoặc date_str là None
        return None


@tool
def list_tasks() -> str:
    """
    Liệt kê các công việc trong danh sách mặc định.
    """
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        results = service.tasks().list(
            tasklist=TASK_LIST_ID, 
            showCompleted='true',
            showHidden='true',
        ).execute()
        
        items = results.get("items", [])
        if not items:
            return f"Bạn không có công việc nào."

        formatted_tasks = []
        for item in items:
            taskId = item.get('id', 'Không có ID')
            status = item.get('status', 'needsAction')
            title = item.get('title', 'Không có tiêu đề')
            due_date = item.get('due', 'Không có hạn').split('T')[0] # Chỉ lấy phần ngày
            formatted_tasks.append(f"-  ID: {taskId}\n  Tiêu đề: {title}\n  Hạn chót: {due_date}\n  Trạng thái: {status}")

        return "Đây là danh sách các công việc của bạn:\n" + "\n\n".join(formatted_tasks)
    except Exception as e:
        return f"Lỗi khi liệt kê công việc: {e}"

@tool
def create_task(title: str, notes: Optional[str] = None, due_date: Optional[str] = None) -> str:
    """
    Tạo một công việc mới.
    'title' là bắt buộc.
    'notes' là mô tả chi tiết cho công việc.
    'due_date' phải có định dạng 'YYYY-MM-DD'.
    """
    if not title:
        return "Lỗi: Không thể tạo task mà không có tiêu đề."
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        task_body = {"title": title}
        if notes:
            task_body["notes"] = notes
        if due_date:
            formatted_due = _format_due_date(due_date)
            if formatted_due:
                task_body["due"] = formatted_due
            else:
                return f"Lỗi: Định dạng ngày '{due_date}' không hợp lệ. Vui lòng dùng YYYY-MM-DD."

        created_task = service.tasks().insert(tasklist=TASK_LIST_ID, body=task_body).execute()
        return f"Đã tạo thành công công việc: '{created_task.get('title')}'."
    except Exception as e:
        return f"Lỗi khi tạo công việc: {e}"

@tool
def update_task(task_id: str, new_title: Optional[str] = None, new_notes: Optional[str] = None, new_status: Optional[str] = None) -> str:
    """
    Cập nhật một công việc đã có bằng ID của nó.
    Bạn phải cung cấp 'task_id'.
    Cung cấp 'new_title' để đổi tiêu đề.
    Cung cấp 'new_notes' để đổi mô tả.
    Cung cấp 'new_status' là 'completed' để đánh dấu hoàn thành hoặc 'needsAction' để đánh dấu chưa hoàn thành.
    """
    if not task_id:
        return "Lỗi: Cần phải có ID của công việc để cập nhật."
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        update_body = {}
        if new_title:
            update_body['title'] = new_title
        if new_notes:
            update_body['notes'] = new_notes
        if new_status:
            if new_status not in ['completed', 'needsAction']:
                return "Lỗi: Trạng thái mới phải là 'completed' hoặc 'needsAction'."
            update_body['status'] = new_status
        
        if not update_body:
            return "Lỗi: Không có thông tin gì để cập nhật."

        updated_task = service.tasks().patch(tasklist=TASK_LIST_ID, task=task_id, body=update_body).execute()
        return f"Đã cập nhật thành công công việc ID {task_id}. Tiêu đề mới: '{updated_task.get('title')}'."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy công việc với ID '{task_id}'."
        return f"Lỗi HTTP khi cập nhật công việc: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi cập nhật công việc: {e}"

@tool
def delete_task(task_id: str) -> str:
    """Xóa một công việc bằng ID của nó. Hành động này không thể hoàn tác."""
    if not task_id:
        return "Lỗi: Cần phải có ID của công việc để xóa."
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        service.tasks().delete(tasklist=TASK_LIST_ID, task=task_id).execute()
        return f"Đã xóa thành công công việc với ID: {task_id}."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy công việc với ID '{task_id}' để xóa."
        return f"Lỗi HTTP khi xóa công việc: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi xóa công việc: {e}"

tasks_tools = [list_tasks, create_task, update_task, delete_task]