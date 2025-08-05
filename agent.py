from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from tools.google_calendar_tools import calendar_tools
from config import MODEL_NAME, MODEL_TEMPERATURE
import dotenv
dotenv.load_dotenv()
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def create_agent(tools: list):
    """
    Tạo và biên dịch một LangGraph Agent với một bộ công cụ được cung cấp.
    """
    tool_node = ToolNode(tools)
    model = ChatGoogleGenerativeAI(
        model=MODEL_NAME, 
        temperature=MODEL_TEMPERATURE,
        convert_system_message_to_human=True
    ).bind_tools(tools)

    def should_continue(state: AgentState):
        if not isinstance(state["messages"][-1], AIMessage) or not state["messages"][-1].tool_calls:
            return "end"
        return "continue"

    def call_model(state: AgentState):
        return {"messages": [model.invoke(state["messages"])]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()