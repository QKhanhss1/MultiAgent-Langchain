import datetime
from typing import Optional, List
import requests
import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import tool

# Import cấu hình từ file config.py
from config import CALENDAR_ID

# --- CÁC TOOLS CHO GOOGLE CALENDAR ---
SERVICE_NAME = "calendar"
VERSION = "v3"

# InCard App API Configuration
INCARD_BASE_URL = "https://stage.incard.biz/api/public-appointments"
DEFAULT_USER_ID = 5089  # Default user ID for InCard app

def call_incard_api(endpoint: str, data: dict) -> bool:
    """Call InCard API with given endpoint and data."""
    try:
        url = f"{INCARD_BASE_URL}/{endpoint}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"InCard API call failed: {e}")
        return False

def extract_time_from_datetime(datetime_str: str) -> str:
    """Extract time in HH:MM format from ISO datetime string."""
    try:
        dt = datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%H:%M")
    except:
        return "09:00"  # Default time

def extract_date_from_datetime(datetime_str: str) -> str:
    """Extract date in YYYY-MM-DD format from ISO datetime string."""
    try:
        dt = datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d")
    except:
        return datetime.date.today().strftime("%Y-%m-%d")  # Default to today

def get_calendar_service_with_token(access_token: str):
    """Create Google Calendar service using access token."""
    try:
        # Create credentials object from access token
        credentials = Credentials(token=access_token)
        service = build(SERVICE_NAME, VERSION, credentials=credentials)
        return service
    except Exception as e:
        raise Exception(f"Failed to create calendar service: {str(e)}")

@tool
def list_events(access_token: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """
    Liệt kê các sự kiện trong một khoảng thời gian cụ thể.
    'access_token' là Google OAuth access token.
    'start_time' và 'end_time' phải ở định dạng ISO 8601.
    """
    try:
        service = get_calendar_service_with_token(access_token)
        
        # Cải tiến: Nếu không có thời gian, mặc định lấy 7 ngày tới
        vn_timezone = datetime.timezone(datetime.timedelta(hours=7))
        if not start_time:
            start_dt = datetime.datetime.now(vn_timezone)
            start_time = start_dt.replace(hour=0, minute=0, second=1).isoformat()
        else:
            start_dt = datetime.datetime.fromisoformat(start_time)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=vn_timezone)
            start_time = start_dt.isoformat()

        if not end_time:
            end_dt = start_dt + datetime.timedelta(days=7)
            end_time = end_dt.isoformat()
        else:
            end_dt = datetime.datetime.fromisoformat(end_time)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=vn_timezone)
            end_time = end_dt.isoformat()

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get("items", [])
        if not events:
            return "Không có sự kiện nào được tìm thấy trong khoảng thời gian này."

        formatted_events = []
        for event in events:
            event_id = event.get("id", "Không có ID")
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "Không có tiêu đề")
            notes = event.get("description", "Không có mô tả")
            
            formatted_events.append(
                f"- ID: {event_id}\n  Tóm tắt: {summary}\n  Thời gian: {start}\n  Ghi chú: {notes}"
            )
        
        return "Đây là các sự kiện được tìm thấy:\n" + "\n\n".join(formatted_events)
    except Exception as e:
        return f"Lỗi khi liệt kê sự kiện: {e}. Hãy chắc chắn access token còn hiệu lực."

@tool
def create_event(access_token: str, summary: str, start_time: str, end_time: str, description: Optional[str] = None, attendees: Optional[List[str]] = None) -> str:
    """
    Tạo một sự kiện mới trong lịch chính.
    'access_token' là Google OAuth access token.
    'summary' là tiêu đề của sự kiện.
    'start_time' và 'end_time' phải có định dạng ISO 8601.
    """
    try:
        service = get_calendar_service_with_token(access_token)
        event_body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "end": {"dateTime": end_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "reminders": {"useDefault": True},
            "attendees": [{"email": email} for email in attendees] if attendees else []
        }
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
        
        # Also create in InCard App
        incard_data = {
            "title": summary,
            "date": extract_date_from_datetime(start_time),
            "time": f"{extract_time_from_datetime(start_time)} {extract_time_from_datetime(end_time)}",
            "note": description or "",
            "user_id": DEFAULT_USER_ID,
            "google_calendar_id": created_event.get('id')
        }
        
        incard_success = call_incard_api("add", incard_data)
        incard_status = " và đã đồng bộ với InCard app" if incard_success else " (lỗi đồng bộ InCard app)"
        
        return f"Đã tạo thành công sự kiện '{created_event.get('summary')}' vào lúc {created_event['start'].get('dateTime')}{incard_status}."
    except Exception as e:
        return f"Lỗi khi tạo sự kiện: {e}. Hãy chắc chắn access token còn hiệu lực."

@tool
def update_event(access_token: str, event_id: str, new_summary: Optional[str] = None, new_start_time: Optional[str] = None, new_end_time: Optional[str] = None, new_description: Optional[str] = None,  new_attendees: Optional[List[str]] = None) -> str:
    """
    Cập nhật một sự kiện đã có bằng ID của nó.
    'access_token' là Google OAuth access token.
    'event_id' là ID của sự kiện cần cập nhật.
    """
    try:
        service = get_calendar_service_with_token(access_token)
        # Lấy sự kiện hiện tại
        event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()

        if new_summary:
            event['summary'] = new_summary
        if new_start_time:
            event['start']['dateTime'] = new_start_time
        if new_end_time:
            event['end']['dateTime'] = new_end_time
        if new_description:
            event['description'] = new_description
        if new_attendees:
            event['attendees'] = [{"email": email} for email in new_attendees]

        updated_event = service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=event).execute()
        
        # Also update in InCard App
        start_datetime = updated_event['start'].get('dateTime', '')
        end_datetime = updated_event['end'].get('dateTime', '')
        
        incard_data = {
            "user_id": str(DEFAULT_USER_ID),
            "note": updated_event.get('description', ''),
            "date": extract_date_from_datetime(start_datetime),
            "time": f"{extract_time_from_datetime(start_datetime)} {extract_time_from_datetime(end_datetime)}",
            "title": updated_event.get('summary', ''),
            "google_calendar_id": event_id
        }
        
        incard_success = call_incard_api("update", incard_data)
        incard_status = " và đã đồng bộ với InCard app" if incard_success else " (lỗi đồng bộ InCard app)"
        
        return f"Đã cập nhật thành công sự kiện '{updated_event.get('summary')}'{incard_status}."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy sự kiện với ID '{event_id}'."
        return f"Lỗi HTTP khi cập nhật sự kiện: {e}"
    except Exception as e:
        return f"Lỗi khi cập nhật sự kiện: {e}. Hãy chắc chắn access token còn hiệu lực."

@tool
def delete_event(access_token: str, event_id: str) -> str:
    """
    Xóa một sự kiện bằng ID của nó.
    'access_token' là Google OAuth access token.
    'event_id' là ID của sự kiện cần xóa.
    """
    try:
        service = get_calendar_service_with_token(access_token)
        
        # Delete from InCard App first (before deleting from Google Calendar)
        incard_data = {
            "user_id": DEFAULT_USER_ID,
            "created_by": DEFAULT_USER_ID,
            "google_calendar_id": event_id
        }
        
        incard_success = call_incard_api("delete", incard_data)
        
        # Then delete from Google Calendar
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        
        incard_status = " và đã xóa khỏi InCard app" if incard_success else " (lỗi xóa khỏi InCard app)"
        
        return f"Đã xóa thành công sự kiện với ID: {event_id}{incard_status}."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy sự kiện với ID '{event_id}' để xóa."
        return f"Lỗi HTTP khi xóa sự kiện: {e}"
    except Exception as e:
        return f"Lỗi khi xóa sự kiện: {e}. Hãy chắc chắn access token còn hiệu lực."

calendar_tools = [list_events, create_event, update_event, delete_event]
