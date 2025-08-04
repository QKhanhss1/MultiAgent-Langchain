from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv  
from langchain_core.messages import BaseMessage # The foundational class for all message types in LangGraph
from langchain_core.messages import ToolMessage # Passes data back to LLM after it calls a tool such as the content and the tool_call_id
from langchain_core.messages import SystemMessage # Message for providing instructions to the LLM
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import HumanMessage, AIMessage


load_dotenv()

memory = ConversationBufferWindowMemory(
    return_messages=True,
    k=5  # Optional: chỉ nhớ 5 lượt gần nhất
)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
@tool
def calculator(a: float, b: float, operator: str):
    """Basic calculator tool."""
    if operator == "+":
        return a + b
    elif operator == "-":
        return a - b
    elif operator == "*":
        return a * b
    elif operator == "/":
        return a / b
    return "Invalid operator"

@tool
def get_weather(city: str):
    """Get weather information for a city."""
    return f"The weather in {city} is sunny and 32°C."

@tool
def get_time(country: str):
    """Get the current time in a specific country."""
    from datetime import datetime
    return f"The current time in {country} is {datetime.now()}."


tools = [calculator, get_weather, get_time]

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash").bind_tools(tools)

def model_call(state: AgentState) -> AgentState:
    """Call the model with the current state."""
    system_prompt = SystemMessage(
        content="You are a helpful assistant. Please answer my query to the best of your ability.")
    history = memory.load_memory_variables({})["history"]
    response = model.invoke(
        [system_prompt] + history + state["messages"] )
    
    memory.chat_memory.add_user_message(state["messages"][-1].content)
    memory.chat_memory.add_ai_message(response.content)

    return {"messages": [response]}

def should_continue(state: AgentState):
    """Check if the conversation should continue."""
    messages=state["messages"]
    last_massage = messages[-1] 
    if not last_massage.tool_calls:
        return "end"
    else:
        return "continue"
    
graph = StateGraph(AgentState)
graph.add_node("our_agent", model_call)


tool_node = ToolNode(tools=tools)
graph.add_node("tools", tool_node)
graph.set_entry_point("our_agent")
graph.add_conditional_edges(
    "our_agent",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    }
)

graph.add_edge("tools", "our_agent")
app = graph.compile()

def print_stream(stream):
    for s in stream:
        message =s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()
            
            
user_input = input("Enter your message: ")
while user_input.lower() != "exit":
    inputs = {"messages": [("user", user_input)]}
    print_stream(app.stream(inputs,stream_mode="values"))
    user_input = input("Enter your message: ")


