
import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from agent import create_agent
from tools.google_tasks_tools import tasks_tools
from tools.google_calendar_tools import calendar_tools

def select_agent():
    """Cho phép người dùng chọn agent để tương tác."""
    while True:
        choice = input("Bạn muốn sử dụng Agent nào? (1: Tasks, 2: Calendar): ")
        if choice == '1':
            print("\nĐang khởi tạo Task Agent...")
            return tasks_tools, "prompts/tasks_agent_prompt.md"
        elif choice == '2':
            print("\nĐang khởi tạo Calendar Agent...")
            return calendar_tools, "prompts/calendar_agent_prompt.md"
        else:
            print("Lựa chọn không hợp lệ. Vui lòng nhập 1 hoặc 2.")

def load_and_format_prompt(prompt_file: str):
    """Tải prompt từ file và điền các giá trị động."""
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    return prompt_template.format(current_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))), start_of_day=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).replace(hour=0, minute=0, second=0, microsecond=0).isoformat())

def main():
    """Hàm chính để chọn và chạy Agent."""
    load_dotenv()
    
    tools, prompt_file = select_agent()
    
    app = create_agent(tools)
    
    formatted_prompt = load_and_format_prompt(prompt_file)
    system_prompt = SystemMessage(content=formatted_prompt)
    
    conversation_history = []
    print("Agent đã sẵn sàng. (gõ 'exit' để thoát)")

    while True:
        user_input = input(">> Bạn: ")
        if user_input.lower() == "exit":
            print("Tạm biệt!")
            break

        conversation_history.append(HumanMessage(content=user_input))
        messages_for_graph = [system_prompt] + conversation_history
        
        try:
            final_state = app.invoke({"messages": messages_for_graph})
            ai_response = final_state['messages'][-1]
            print(f">> Agent: {ai_response.content}")
            conversation_history.append(ai_response)
        except Exception as e:
            print(f"Đã có lỗi nghiêm trọng xảy ra: {e}")

if __name__ == "__main__":
    main()