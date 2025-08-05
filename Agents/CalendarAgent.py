# =================================================================
# AGENT QUẢN LÝ GOOGLE CALENDAR
# =================================================================
import os.path
import datetime
from typing import Annotated, Sequence, TypedDict, Optional, List

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from langchain_core.messages import BaseMessage, ToolMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI

# Tải biến môi trường
load_dotenv()

# --- PHẦN CẤU HÌNH VÀ XÁC THỰC ---

# THAY ĐỔI QUAN TRỌNG: Scope cho Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
# ID của lịch. 'primary' là một giá trị đặc biệt, đại diện cho lịch chính của người dùng đã đăng nhập.
CALENDAR_ID = 'primary'

def get_google_calendar_service():
    """Xác thực với Google và trả về một đối tượng service để tương tác với Calendar API."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError("Lỗi: Không tìm thấy file credentials.json.")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Lỗi khi xây dựng service Google Calendar: {e}")
        return None

# --- CÁC TOOLS CHO GOOGLE CALENDAR ---

@tool
def list_events(start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
    """
    Liệt kê các sự kiện trong một khoảng thời gian cụ thể.
    Nếu không cung cấp thời gian, hàm sẽ tự động lấy các sự kiện trong 7 ngày tới.
    'start_time' và 'end_time' phải ở định dạng ISO 8601 (ví dụ: '2025-08-06T00:00:00+07:00').
    Hàm này trả về tóm tắt, thời gian bắt đầu, và ID của mỗi sự kiện.    """
    try:
        service = get_google_calendar_service()
        
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
        service = get_google_calendar_service()
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
        service = get_google_calendar_service()
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
        service = get_google_calendar_service()
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return f"Đã xóa thành công sự kiện với ID: {event_id}."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy sự kiện với ID '{event_id}' để xóa."
        return f"Lỗi HTTP khi xóa sự kiện: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi xóa sự kiện: {e}"

# --- PHẦN XÂY DỰNG AGENT VỚI LANGGRAPH ---

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

tools = [list_events, create_event, update_event, delete_event]
tool_node = ToolNode(tools)
# Sử dụng model có khả năng suy luận tốt
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3).bind_tools(tools)

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return "end"
    return "continue"

def call_model(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
workflow.add_edge("tools", "agent")
app = workflow.compile()

# --- VÒNG LẶP CHÍNH ĐỂ TƯƠNG TÁC ---
def main():
    current_time = datetime.datetime.now()
    current_time_str = current_time.isoformat()
    start_of_day = current_time.replace(hour=0, minute=0, second=0).isoformat()
    
    system_prompt_content = f"""## Tổng quan
Bạn là Calendar Execution Agent TỐC ĐỘ CAO. Nhiệm vụ của bạn là thực thi các yêu cầu về lịch (tạo, cập nhật, xóa sự kiện) một cách nhanh chóng và chính xác.

___

## CÁC CÔNG CỤ (TOOLS)

### Công cụ Google Calendar

- `list_events`, `create_event`, `delete_event`, `update_event`
** Nếu có email người tham dự ** thì sử dụng:
- `create_event` với tham số `attendees`, `update_event` với tham số `new_attendees`

## Xử lý thời gian
- Tuân thủ chuẩn RFC 3339 timestamp.
- Thời lượng sự kiện mặc định là **1 giờ** nếu không được chỉ định.
- Quy đổi ngôn ngữ tự nhiên ("hôm nay", "ngày mai","tuần này") dựa trên `{current_time_str}`.

---
## QUY TẮC XỬ LÝ KẾT QUẢ TÌM KIẾM 

### 1. Xử lý Yêu cầu Chung chung
- **QUY TẮC:** Nếu yêu cầu của người dùng chỉ là "kiểm tra lịch" hoặc "xem lịch của tôi" mà không có thời gian cụ thể:
- **Hành động BẮT BUỘC:**
    1.  Mặc định dùng `list_events` để lấy các sự kiện trong **7 ngày tới** (từ `{start_of_day}`).
    2.  Trình bày kết quả tìm được (hoặc báo là không có sự kiện nào).
    3.  **DỪNG LẠI.** Nhiệm vụ của bạn đã hoàn thành.

___

## KỊCH BẢN THỰC THI TỐI ƯU (ĐÃ SỬA LỖI LOGIC)

### 1. Tạo Sự Kiện
- **Logic:** `Chuẩn hóa thời gian -> list_events (kiểm tra xung đột) -> create_event... 
- **Hành động:**
    *   **Nếu có xung đột:** DỪNG LẠI và báo cho người dùng.
    *   **Nếu không có lịch nào trong thời gian này:** Thực thi chuỗi `create_event...`

### 2. Cập nhật hoặc Xóa Sự Kiện 

#### Bước 1: Tìm kiếm Sự kiện Mục tiêu
- **Hành động:** Dùng `list_events` với các từ khóa từ yêu cầu của người dùng (ví dụ: tên sự kiện, thời gian gần đúng).

#### Bước 2: Xử lý Kết quả Tìm kiếm
- **NẾU** kết quả trả về là **1 sự kiện duy nhất**:
    - Chuyển sang Bước 3.
- **NẾU** kết quả trả về là **NHIỀU hơn 1 sự kiện**:
    - DỪNG LẠI. Liệt kê các sự kiện tìm thấy và hỏi người dùng để xác nhận.
- **NẾU** kết quả trả về là **danh sách rỗng `[]`**:
    - DỪNG LẠI. Báo cho người dùng: "Tôi không tìm thấy sự kiện nào khớp với yêu cầu của bạn."

#### Bước 3: Thực thi 
- (Chỉ thực hiện nếu Bước 2 tìm thấy 1 sự kiện duy nhất)
- **Hành động:**
    1.  Thực hiện `update_event` hoặc `delete_event` với `eventId` đã tìm được.
    """
    
    # Convert system message to human message to avoid deprecation warning
    system_as_human = SystemMessage(content=f"SYSTEM INSTRUCTIONS: {system_prompt_content}")
    conversation_history = [system_as_human]

    print("Chào bạn, tôi là trợ lý Lịch Google. (gõ 'exit' để thoát)")

    while True:
        user_input = input(">> Bạn: ")
        if user_input.lower() == "exit":
            print("Tạm biệt!")
            break

        conversation_history.append(HumanMessage(content=user_input))
        messages_for_graph = conversation_history
        inputs = {"messages": messages_for_graph}
        
        final_state = app.invoke(inputs)
        ai_response = final_state['messages'][-1]
        
        print(f">> Agent: {ai_response.content}")
        conversation_history.append(ai_response)

if __name__ == "__main__":
    main()