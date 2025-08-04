import os
import operator
from typing import TypedDict, Annotated, List

# --- Các thư viện LangChain & LangGraph ---
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import dotenv
dotenv.load_dotenv()

# --- Import các tools chúng ta đã tạo ---
from google_tasks_tools import (
    create_task, 
    search_tasks, 
    find_near_due_date_tasks
)

# --- BƯỚC 1: THIẾT LẬP TOOLS VÀ MODEL ---

# Tạo một danh sách các tool mà Agent có thể sử dụng
tools = [create_task, search_tasks, find_near_due_date_tasks]

# ToolExecutor là một lớp trợ giúp giúp thực thi các tool một cách an toàn
tool_executor = ToolNode(tools)

# Chọn model LLM. Các model "turbo" hoặc "o" mới nhất của OpenAI 
# hoạt động rất tốt với việc gọi tool.
# model = ChatOpenAI(model="gpt-4-turbo", temperature=0)
model = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)


# --- BƯỚC 2: ĐỊNH NGHĨA AGENT RUNNABLE ---
# Agent Runnable là sự kết hợp của (Model + Prompt + Tool).
# Nó chịu trách nhiệm nhận input và quyết định xem nên gọi tool nào.

# Đây là prompt template, nơi chúng ta chỉ dẫn cho Agent
# MessagesPlaceholder là nơi lịch sử chat sẽ được chèn vào.
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Bạn là một trợ lý AI hữu ích, chuyên quản lý công việc trên Google Tasks. Bạn phải sử dụng các tool được cung cấp để đáp ứng yêu cầu của người dùng. Hãy trả lời bằng tiếng Việt."),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad"), # Nơi agent ghi lại các bước gọi tool và kết quả
    ]
)

# Tạo Agent Runnable
agent_runnable = create_openai_tools_agent(model, tools, prompt)


# --- BƯỚC 3: ĐỊNH NGHĨA TRẠNG THÁI (STATE) CỦA GRAPH ---
# State là một đối tượng chứa toàn bộ thông tin được truyền giữa các node trong graph.

class AgentState(TypedDict):
    # Lịch sử tin nhắn. `operator.add` đảm bảo các tin nhắn mới sẽ được nối vào list cũ.
    messages: Annotated[List[BaseMessage], operator.add]
    # Trường này sẽ chứa các bước trung gian (tool calls, tool outputs)
    # create_openai_tools_agent expects 'intermediate_steps' not 'agent_scratchpad'
    intermediate_steps: Annotated[List, operator.add]


# --- BƯỚC 4: ĐỊNH NGHĨA CÁC NODE CỦA GRAPH ---
# Mỗi node là một hàm Python nhận vào State và trả về một phần của State.

def call_model(state: AgentState):
    """Node 1: Gọi Agent Runnable để quyết định bước tiếp theo."""
    print("---GỌI MODEL---")
    
    # Call the agent
    response = agent_runnable.invoke(state)
    
    # The agent returns either an AgentAction or AgentFinish
    return {"messages": [response]}


def call_tool(state: AgentState):
    """Node 2: Thực thi tool mà model đã quyết định."""
    print("---GỌI TOOL---")
    
    # Get the last message which should be an AgentAction
    last_message = state["messages"][-1]
    
    # Execute the tool
    if hasattr(last_message, 'tool') and hasattr(last_message, 'tool_input'):
        # This is an AgentAction, execute the tool
        tool_name = last_message.tool
        tool_input = last_message.tool_input
        
        # Find and execute the tool
        for tool in tools:
            if tool.name == tool_name:
                try:
                    result = tool.invoke(tool_input)
                    break
                except Exception as e:
                    result = f"Error executing {tool_name}: {str(e)}"
        else:
            result = f"Tool {tool_name} not found"
        
        # Create a ToolMessage with the result
        tool_message = ToolMessage(
            content=str(result), 
            tool_call_id=getattr(last_message, 'tool_call_id', 'unknown')
        )
        
        return {
            "messages": [tool_message],
            "intermediate_steps": [(last_message, result)]
        }
    else:
        return {"messages": []}


# --- BƯỚC 5: ĐỊNH NGHĨA LOGIC ĐIỀU HƯỚNG (ROUTER) ---
# Hàm này sẽ quyết định Graph sẽ đi đến node nào tiếp theo.

def should_continue(state: AgentState):
    """Hàm quyết định: Tiếp tục gọi tool hay kết thúc và trả lời."""
    print("---KIỂM TRA ĐIỀU KIỆN---")
    last_message = state["messages"][-1]
    print(f"Type of last message: {type(last_message)}")
    print(f"Has tool attribute: {hasattr(last_message, 'tool')}")
    
    # Check if it's an AgentAction (has tool attribute) 
    if hasattr(last_message, 'tool'):
        print("---TIẾP TỤC GỌI TOOL---")
        return "continue"
    else:
        print("---KẾT THÚC---")
        return "end"


# --- BƯỚC 6: XÂY DỰNG VÀ BIÊN DỊCH GRAPH ---

# 1. Khởi tạo graph
workflow = StateGraph(AgentState)

# 2. Thêm các node vào graph
workflow.add_node("agent", call_model) # Tên node "agent" sẽ thực thi hàm `call_model`
workflow.add_node("action", call_tool) # Tên node "action" sẽ thực thi hàm `call_tool`

# 3. Đặt điểm bắt đầu cho graph
workflow.set_entry_point("agent")

# 4. Thêm các cạnh (edges) để kết nối các node
# Ở đây chúng ta dùng một cạnh có điều kiện (conditional edge)
workflow.add_conditional_edges(
    "agent", # Bắt đầu từ node "agent"
    should_continue, # Dùng hàm này để quyết định
    {
        "continue": "action", # Nếu hàm trả về "continue", đi tới node "action"
        "end": END,          # Nếu hàm trả về "end", kết thúc graph
    },
)

# Thêm cạnh thông thường: sau khi thực thi "action", luôn quay lại "agent" để xử lý tiếp
workflow.add_edge("action", "agent")

# 5. Biên dịch graph thành một đối tượng có thể chạy được
app = workflow.compile()


# --- BƯỚC 7: CHẠY THỬ AGENT ---
if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    
    print("Chào bạn, tôi là trợ lý Google Tasks. Bạn cần giúp gì?")
    
    while True:
        user_input = input("Bạn: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        # Chuẩn bị input cho graph
        inputs = {"messages": [HumanMessage(content=user_input)], "intermediate_steps": []}
        
        # `stream` cho phép chúng ta thấy các bước mà agent thực hiện
        final_state = None
        for output in app.stream(inputs):
            # `output` là một dictionary chứa tên node và kết quả của nó
            for key, value in output.items():
                print(f"Kết quả từ node '{key}':")
                final_state = value
                # print(value, end="\n---\n") # In ra đầy đủ để debug
        
        # Lấy câu trả lời cuối cùng của AI để hiển thị cho người dùng
        if final_state and 'messages' in final_state:
            final_response = final_state['messages'][-1]
            # Check the type of the final response
            if hasattr(final_response, 'return_values'):
                # It's an AgentFinish
                print("AI:", final_response.return_values.get('output', str(final_response)))
            elif hasattr(final_response, 'content'):
                # It's a regular message
                print("AI:", final_response.content)
            elif hasattr(final_response, 'tool'):
                # It's an AgentAction - this shouldn't happen at the end
                print("AI: Đã thực hiện công việc:", final_response.tool)
            else:
                print("AI:", str(final_response))