# intelligent_agent_platform/app.py

import streamlit as st
import datetime
from langchain_core.messages import SystemMessage, HumanMessage

# Import các thành phần đã được tái cấu trúc
from agent import create_agent
from tools.google_tasks_tools import tasks_tools
from tools.google_calendar_tools import calendar_tools
from tools.google_gmail_tools import gmail_tools
# --- Caching: Tối ưu hiệu suất ---
# Streamlit sẽ chạy lại code từ đầu mỗi khi có tương tác.
# @st.cache_resource đảm bảo rằng "nhà máy" tạo agent và các tài nguyên đắt đỏ khác
# chỉ được tạo một lần duy nhất, giúp ứng dụng chạy nhanh hơn.
@st.cache_resource
def get_agent(agent_type: str):
    """Tải các tool phù hợp và tạo agent."""
    if agent_type == "Tasks":
        tools = tasks_tools
    elif agent_type == "Calendar":
        tools = calendar_tools
    elif agent_type == "Gmail": 
        tools = gmail_tools
    else:
        return None
    return create_agent(tools)

@st.cache_data
def load_prompt_template(prompt_file: str):
    """Tải prompt từ file (sử dụng cache để không phải đọc file liên tục)."""
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()

def get_formatted_prompt(prompt_file: str):
    """Điền các giá trị động vào prompt."""
    prompt_template = load_prompt_template(prompt_file)
    return prompt_template.format(
        current_time=datetime.datetime.now().isoformat(),
        start_of_day=datetime.datetime.now().replace(hour=0, minute=0, second=0).isoformat()
    )

# --- Thiết lập giao diện chính ---
st.set_page_config(page_title="Intelligent Agent Platform", page_icon="🤖")
st.title("🤖 Nền tảng Agent Thông minh")
st.caption("Trò chuyện với các Agent chuyên biệt cho Google Tasks và Calendar.")

# --- Sidebar để chọn Agent ---
with st.sidebar:
    st.header("Cấu hình Agent")
    agent_choice = st.selectbox(
        "Chọn Agent để tương tác:",
        ("--- Vui lòng chọn ---", "Tasks", "Calendar", "Gmail")
    )

# --- Logic chính của ứng dụng ---
if agent_choice != "--- Vui lòng chọn ---":
    # Khởi tạo hoặc lấy lại Agent và prompt từ session state
    if "agent" not in st.session_state or st.session_state.agent_name != agent_choice:
        st.session_state.agent_name = agent_choice
        st.session_state.agent = get_agent(agent_choice)
        prompt_file = f"prompts/{agent_choice.lower()}_agent_prompt.md"
        st.session_state.system_prompt = SystemMessage(content=get_formatted_prompt(prompt_file))
        st.session_state.messages = [st.session_state.system_prompt]
        st.success(f"Đã khởi tạo {agent_choice} Agent. Bạn có thể bắt đầu trò chuyện!")
    
    # Hiển thị lịch sử chat
    for message in st.session_state.messages:
        # Không hiển thị System Prompt trong giao diện chat
        if isinstance(message, SystemMessage):
            continue
        # Gán vai trò (role) phù hợp cho từng loại tin nhắn để hiển thị avatar
        role = "assistant" if not isinstance(message, HumanMessage) else "user"
        with st.chat_message(role):
            st.markdown(message.content)

    # Nhận input từ người dùng
    if user_input := st.chat_input(f"Hỏi {st.session_state.agent_name} Agent..."):
        # Thêm tin nhắn của người dùng vào lịch sử và hiển thị ngay lập tức
        st.session_state.messages.append(HumanMessage(content=user_input))
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Gọi Agent và hiển thị trạng thái "đang suy nghĩ"
        with st.chat_message("assistant"):
            with st.spinner("Agent đang suy nghĩ..."):
                try:
                    # Chuẩn bị input cho agent
                    inputs = {"messages": st.session_state.messages}
                    
                    # Gọi Agent
                    final_state = st.session_state.agent.invoke(inputs)
                    ai_response_message = final_state['messages'][-1]
                    
                    # Hiển thị câu trả lời của AI
                    st.markdown(ai_response_message.content)
                    
                    # Thêm câu trả lời của AI vào lịch sử
                    st.session_state.messages.append(ai_response_message)
                except Exception as e:
                    error_message = f"Đã có lỗi xảy ra: {e}"
                    st.error(error_message)
                    st.session_state.messages.append(SystemMessage(content=error_message)) # Lưu lỗi vào history để debug
else:
    st.info("Vui lòng chọn một Agent từ thanh bên để bắt đầu.")