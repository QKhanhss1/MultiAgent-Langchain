# =================================================================
# AGENT QUẢN LÝ GOOGLE CALENDAR
# =================================================================
import os.path
import datetime
from typing import Annotated, Sequence, TypedDict, Optional

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
def list_events(max_results: int = 10) -> str:
    """
    Liệt kê các sự kiện sắp tới trong lịch chính của người dùng.
    'max_results' là số lượng sự kiện tối đa cần hiển thị.
    Hàm này trả về tóm tắt, thời gian bắt đầu, và ID của mỗi sự kiện.
    """
    try:
        service = get_google_calendar_service()
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' chỉ múi giờ UTC
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        
        events = events_result.get("items", [])
        if not events:
            return "Bạn không có sự kiện nào sắp diễn ra."

        formatted_events = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "Không có tiêu đề")
            event_id = event.get("id", "Không có ID")
            formatted_events.append(
                f"- ID: {event_id}\n  Tóm tắt: {summary}\n  Thời gian: {start}"
            )
        return "Đây là các sự kiện sắp tới của bạn:\n" + "\n\n".join(formatted_events)
    except Exception as e:
        return f"Lỗi khi liệt kê sự kiện: {e}"

@tool
def create_event(summary: str, start_time: str, end_time: str, description: Optional[str] = None, location: Optional[str] = None) -> str:
    """
    Tạo một sự kiện mới trong lịch chính.
    'summary' là tiêu đề của sự kiện.
    'start_time' và 'end_time' là thời gian bắt đầu và kết thúc, BẮT BUỘC phải có định dạng ISO 8601 (ví dụ: '2025-08-06T15:00:00' hoặc '2025-08-06T15:00:00+07:00' cho múi giờ Việt Nam).
    'description' và 'location' là các thông tin tùy chọn.
    """
    try:
        service = get_google_calendar_service()
        event_body = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "end": {"dateTime": end_time, "timeZone": "Asia/Ho_Chi_Minh"},
            "reminders": {"useDefault": True},
        }
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
        return f"Đã tạo thành công sự kiện '{created_event.get('summary')}' vào lúc {created_event['start'].get('dateTime')}."
    except Exception as e:
        return f"Lỗi khi tạo sự kiện: {e}. Hãy chắc chắn định dạng thời gian là đúng (YYYY-MM-DDTHH:MM:SS)."

@tool
def update_event(event_id: str, new_summary: Optional[str] = None, new_start_time: Optional[str] = None, new_end_time: Optional[str] = None) -> str:
    """
    Cập nhật một sự kiện đã có bằng ID của nó.
    Bạn phải cung cấp 'event_id'.
    Bạn có thể cung cấp các giá trị mới cho 'new_summary', 'new_start_time', 'new_end_time'.
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
    system_prompt_content = """Bạn là một trợ lý quản lý Lịch Google thông minh và chính xác.
    
    QUY TẮC VÀNG:
    1.  **Xử lý Thời gian:** Khi người dùng cung cấp thời gian dạng tự nhiên (ví dụ: 'ngày mai lúc 3 giờ chiều'), bạn phải tự chuyển đổi nó sang định dạng chuỗi ISO 8601 ('YYYY-MM-DDTHH:MM:SS') trước khi gọi bất kỳ tool nào. Ví dụ, nếu hôm nay là 2025-08-05, 'ngày mai lúc 3 giờ chiều' sẽ là '2025-08-06T15:00:00'.
    2.  **Xác định ID:** Trước khi CẬP NHẬT hoặc XÓA một sự kiện, bạn BẮT BUỘC phải biết `event_id` của nó. Hãy dùng `list_events` để tìm ID nếu cần. Nếu tìm thấy nhiều sự kiện khớp với mô tả của người dùng, hãy dừng lại và hỏi lại để làm rõ.
    3.  **Chủ động:** Hãy chủ động dùng tool để hoàn thành yêu cầu. Nếu thiếu thông tin (ví dụ: không có thời gian kết thúc), hãy hỏi lại người dùng.
    """
    system_prompt = SystemMessage(content=system_prompt_content)
    conversation_history = []

    print("Chào bạn, tôi là trợ lý Lịch Google. (gõ 'exit' để thoát)")

    while True:
        user_input = input(">> Bạn: ")
        if user_input.lower() == "exit":
            print("Tạm biệt!")
            break

        conversation_history.append(HumanMessage(content=user_input))
        messages_for_graph = [system_prompt] + conversation_history
        inputs = {"messages": messages_for_graph}
        
        final_state = app.invoke(inputs)
        ai_response = final_state['messages'][-1]
        
        print(f">> Agent: {ai_response.content}")
        conversation_history.append(ai_response)

if __name__ == "__main__":
    main()