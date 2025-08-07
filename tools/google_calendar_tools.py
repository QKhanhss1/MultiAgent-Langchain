import os.path
import datetime
from typing import Optional, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import tool

# Import cấu hình từ file config.py
from config import SCOPES, CALENDAR_ID, TOKEN_FILE, CREDENTIALS_FILE
# from .common_auth import get_google_service
from tools.auth.deploy import get_google_service
# --- CÁC TOOLS CHO GOOGLE CALENDAR ---
SERVICE_NAME = "calendar"
VERSION = "v3"
@tool
def list_events(start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """
    Liệt kê các sự kiện trong một khoảng thời gian cụ thể.
    Nếu không cung cấp thời gian, hàm sẽ tự động lấy các sự kiện trong 7 ngày tới.
    'start_time' và 'end_time' phải ở định dạng ISO 8601 (ví dụ: '2025-08-06T00:00:00+07:00').
    Hàm này trả về tóm tắt, thời gian bắt đầu, và ID của mỗi sự kiện.    """
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        
        # Cải tiến: Nếu không có thời gian, mặc định lấy 7 ngày tới
        if not start_time:
            start_dt = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
            start_time = start_dt.replace(hour=0, minute=0, second=1).isoformat()  # RFC 3339
        else:
            # Chuyển đổi string thành datetime có timezone
            start_dt = datetime.datetime.fromisoformat(start_time)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
            start_time = start_dt.replace(hour=0, minute=0, second=1).isoformat()

        if not end_time:
            end_dt = start_dt + datetime.timedelta(days=7)
            end_time = end_dt.isoformat()
        else:
            end_dt = datetime.datetime.fromisoformat(end_time)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
            end_time = end_dt.isoformat()

        print(f"DEBUG: Tìm kiếm sự kiện từ {start_time} đến {end_time}")


        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get("items", [])
        if not events:
            return f"Không có sự kiện nào được tìm thấy trong khoảng thời gian này."

        formatted_events = []
        for event in events:
            id = event.get("id", "Không có ID")
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "Không có tiêu đề")
            notes = event.get("description", "Không có mô tả")
            formatted_events.append(
                f"- ID: {id}\n  Tóm tắt: {summary}\n  Thời gian: {start}\n  Ghi chú: {notes}"
            )
        return "Đây là các sự kiện được tìm thấy:\n" + "\n\n".join(formatted_events)
    except Exception as e:
        return f"Lỗi khi liệt kê sự kiện: {e}. Hãy chắc chắn định dạng thời gian là đúng (YYYY-MM-DDTHH:MM:SS)."

@tool
def create_event(summary: str, start_time: str, end_time: str, description: Optional[str] = None, location: Optional[str] = None, reminders: Optional[dict] = None, attendees: Optional[List[str]] = None) -> str:
    """
    Tạo một sự kiện mới trong lịch chính.
    'summary' là tiêu đề của sự kiện.
    'attendees' là danh sách email của người tham dự (nếu có).
    'start_time' và 'end_time' là thời gian bắt đầu và kết thúc, BẮT BUỘC phải có định dạng ISO 8601 (ví dụ: '2025-08-06T15:00:00' hoặc '2025-08-06T15:00:00+07:00' cho múi giờ Việt Nam).
    'description', 'location' và reminders là các thông tin tùy chọn.
    """
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        event_body = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "end": {"dateTime": end_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "reminders": reminders if reminders else {"useDefault": True},
            "attendees": [{"email": email} for email in attendees] if attendees else []
        }
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
        return f"Đã tạo thành công sự kiện '{created_event.get('summary')}' vào lúc {created_event['start'].get('dateTime')}."
    except Exception as e:
        return f"Lỗi khi tạo sự kiện: {e}. Hãy chắc chắn định dạng thời gian là đúng (YYYY-MM-DDTHH:MM:SS)."

@tool
def update_event(event_id: str, new_summary: Optional[str] = None, new_start_time: Optional[str] = None, new_end_time: Optional[str] = None, new_description: Optional[str] = None, new_location: Optional[str] = None, new_reminders: Optional[dict] = None, new_attendees: Optional[List[str]] = None) -> str:
    """
    Cập nhật một sự kiện đã có bằng ID của nó.
    Bạn có thể cung cấp các giá trị mới cho 'new_summary', 'new_start_time', 'new_end_time', 'new_description', 'new_location', 'new_reminders', 'new_attendees'.
    Định dạng thời gian mới phải là ISO 8601.
    """
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        # Đầu tiên, lấy sự kiện hiện tại để không ghi đè mất các thông tin khác
        event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()

        if new_summary:
            event['summary'] = new_summary
        if new_start_time:
            event['start']['dateTime'] = new_start_time
        if new_end_time:
            event['end']['dateTime'] = new_end_time
        if new_description:
            event['description'] = new_description
        if new_location:
            event['location'] = new_location
        if new_reminders:
            event['reminders'] = new_reminders
        if new_attendees:
            event['attendees'] = [{"email": email} for email in new_attendees]

        updated_event = service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=event).execute()
        return f"Đã cập nhật thành công sự kiện '{updated_event.get('summary')}'."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy sự kiện với ID '{event_id}'."
        return f"Lỗi HTTP khi cập nhật sự kiện: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi cập nhật sự kiện: {e}"

@tool
def delete_event(event_id: str) -> str:
    """Xóa một sự kiện bằng ID của nó. Hành động này không thể hoàn tác."""
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return f"Đã xóa thành công sự kiện với ID: {event_id}."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy sự kiện với ID '{event_id}' để xóa."
        return f"Lỗi HTTP khi xóa sự kiện: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi xóa sự kiện: {e}"

calendar_tools = [list_events, create_event, update_event, delete_event]