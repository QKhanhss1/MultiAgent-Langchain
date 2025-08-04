# =================================================================
# AGENT QUẢN LÝ GOOGLE TASKS
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

from langchain_core.messages import BaseMessage, ToolMessage, AIMessage, HumanMessage,SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI

# Tải biến môi trường (ví dụ GOOGLE_API_KEY cho LangChain)
load_dotenv()

# --- PHẦN XÁC THỰC GOOGLE API ---
# Nếu thay đổi các scope này, hãy xóa file token.json.
SCOPES = ["https://www.googleapis.com/auth/tasks"]
# ID của danh sách công việc. '@default' là danh sách mặc định.
TASK_LIST_ID = '@default'

def get_google_tasks_service():
    """Xác thực với Google và trả về một đối tượng service để tương tác với API."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # Nếu không có credentials hợp lệ, cho người dùng đăng nhập.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "Lỗi: Không tìm thấy file credentials.json. "
                    "Vui lòng tải nó từ Google Cloud Console và đặt vào cùng thư mục."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Lưu credentials cho lần chạy tiếp theo
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
    try:
        service = build("tasks", "v1", credentials=creds)
        return service
    except Exception as e:
        print(f"Lỗi khi xây dựng service Google Tasks: {e}")
        return None

# --- CÁC TOOLS CHO GOOGLE TASKS ---

def _format_due_date(date_str: str) -> Optional[str]:
    """Chuyển đổi ngày YYYY-MM-DD thành định dạng RFC3339 mà Google API yêu cầu."""
    try:
        # Giả sử người dùng nhập ngày, chúng ta đặt giờ là nửa đêm UTC
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.isoformat() + "Z"
    except (ValueError, TypeError):
        # Nếu định dạng sai hoặc date_str là None
        return None

def get_task_agent_instructions():
    current_time = datetime.datetime.now().isoformat()

    role = "## VAI TRÒ & MỤC TIÊU\n"
    role += "**BẠN LÀ MỘT TASK AGENT THỰC THI HIỆU SUẤT CAO.**\n"
    role += "**MỤC TIÊU SỐ 1: CHÍNH XÁC.** Luôn xác thực đầy đủ thông tin trước khi hành động.\n"
    role += "**MỤC TIÊU SỐ 2: TỐC ĐỘ.** Hoàn thành yêu cầu với ít bước nhất có thể sau khi đã xác thực.\n"

    tools = "## CÁC CÔNG CỤ\n`create_task`, `update_task`, `list_tasks`, `delete_task`\n"

    process_tree = """## QUY TRÌNH THỰC THI (Decision Tree)

### 1. Ý ĐỊNH: TẠO MỚI (Create)
#### A. Tạo Task
**BƯỚC 1: KIỂM TRA ĐIỀU KIỆN ĐẦU VÀO**
1. **Kiểm tra Hạn chót:** Yêu cầu có cung cấp hạn chót không?
   - **Nếu KHÔNG:** DỪNG LẠI. Hỏi người dùng để xác nhận, nếu không đồng ý thì mặc định là hôm nay.

**BƯỚC 2: THỰC THI (Sau khi đã có đủ thông tin)**
1. **Kiểm tra trùng lặp Task:** Dùng `list_tasks`.
2. **Hành động:**
   - Nếu trùng, báo cho người dùng.
   - Nếu không trùng, gọi `create_task`.

### 2. Ý ĐỊNH: CẬP NHẬT hoặc XÓA (Update/Delete)
1. **Tìm kiếm:** Dùng `list_tasks` để tìm task.
2. **Xử lý kết quả:**
   - **Nếu tìm thấy 1:** Thực thi `update_task` hoặc `delete_task`.
   - **Nếu tìm thấy NHIỀU:** DỪNG LẠI. Liệt kê các kết quả và hỏi người dùng.
   - **Nếu KHÔNG tìm thấy:** DỪNG LẠI. Báo không tìm thấy cho người dùng.

### 3. Ý ĐỊNH: TÁC VỤ HÀNG LOẠT (Batch)
#### A. Xóa các task đã hoàn thành
1. Gọi `list_tasks` để lấy danh sách công việc.
2. **Tự lọc** các task có `status: 'completed'`.
3. Gọi `delete_task` lặp lại cho mỗi ID đã lọc.

#### B. Liệt kê các task sắp hết hạn
- **Điều kiện lọc:** `due >= {current_time}` và `due <= {current_time.plus(1,days)}`.
- **Hành động:** Gọi `get_tasks`, tự lọc theo điều kiện, và trình bày kết quả theo markdown.
"""

    rules = """## QUY TẮC PHỤ
- **Thời gian:** Luôn tuân thủ ISO 8601 (UTC). Bỏ qua giờ nếu người dùng cung cấp.
- **Quyết đoán:** Sau khi đã xác thực, hãy thực thi một cách hiệu quả.
"""

    notes = f"""## LƯU Ý
- **Không cần hỏi lại:** Nếu đã có đủ thông tin, hãy thực thi ngay.
- **Không cần xác nhận:** Trừ khi có nghi ngờ về thông tin.
- **Không cần giải thích:** Chỉ cần thực hiện hành động.
- ** Thời gian hiện tại là: `{current_time}` **
"""

    return role + tools + process_tree + rules + notes


@tool
def list_tasks() -> str:
    """
    Liệt kê các công việc trong danh sách mặc định.
    """
    try:
        service = get_google_tasks_service()
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
        service = get_google_tasks_service()
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
        service = get_google_tasks_service()
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
        service = get_google_tasks_service()
        service.tasks().delete(tasklist=TASK_LIST_ID, task=task_id).execute()
        return f"Đã xóa thành công công việc với ID: {task_id}."
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy công việc với ID '{task_id}' để xóa."
        return f"Lỗi HTTP khi xóa công việc: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi xóa công việc: {e}"

# --- PHẦN XÂY DỰNG AGENT VỚI LANGGRAPH ---

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Danh sách các tool mà Agent có thể sử dụng
tools = [list_tasks, create_task, update_task, delete_task]
# Trang bị tools cho model
tool_node = ToolNode(tools)
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3).bind_tools(tools)

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return "end"
    return "continue"

def call_model(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# Xây dựng Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "tools", "end": END}
)
workflow.add_edge("tools", "agent")

# Biên dịch thành ứng dụng
app = workflow.compile()

# --- VÒNG LẶP CHÍNH ĐỂ TƯƠNG TÁC ---
def main():
    system_message = get_task_agent_instructions(),
    conversation_history = [
        # Bạn có thể thêm một SystemMessage ở đây để định hình 'tính cách' của Agent
        SystemMessage(content=system_message)
    ]
    print("Chào bạn, tôi là trợ lý Google Tasks. (gõ 'exit' để thoát)")

    while True:
        user_input = input(">> Bạn: ")
        if user_input.lower() == "exit":
            print("Tạm biệt!")
            break

        conversation_history.append(HumanMessage(content=user_input))

        inputs = {"messages": conversation_history}
        
        final_state = app.invoke(inputs)
        ai_response = final_state['messages'][-1]
        
        print(f">> Agent: {ai_response.content}")
        
        conversation_history.append(ai_response)

if __name__ == "__main__":
    main()