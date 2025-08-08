from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from config import MODEL_NAME, MODEL_TEMPERATURE
import dotenv
dotenv.load_dotenv()
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def create_agent_with_token(tools: list, access_token: str):
    """
    Tạo và biên dịch một LangGraph Agent với một bộ công cụ được cung cấp và access token.
    """
    # Create wrapped tools that include the access token
    wrapped_tools = []
    for tool in tools:
        # Create a wrapper function that injects the access token
        def create_wrapper(original_tool, token):
            from functools import wraps
            from langchain_core.tools import tool as tool_decorator
            
            # Get the original function
            original_func = original_tool.func
            
            # Create a new function with the token injected
            @wraps(original_func)
            def wrapper_func(*args, **kwargs):
                return original_func(token, *args, **kwargs)
            
            # Create the tool with the same name and description
            wrapper_func.__name__ = original_tool.name
            wrapper_func.__doc__ = original_tool.description
            
            wrapped_tool = tool_decorator(wrapper_func)
            
            return wrapped_tool
        
        wrapped_tools.append(create_wrapper(tool, access_token))
    
    tool_node = ToolNode(wrapped_tools)
    model = ChatGoogleGenerativeAI(
        model=MODEL_NAME, 
        temperature=MODEL_TEMPERATURE,
    ).bind_tools(wrapped_tools)

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

def create_agent(tools: list):
    """
    Tạo và biên dịch một LangGraph Agent với một bộ công cụ được cung cấp.
    """
    tool_node = ToolNode(tools)
    model = ChatGoogleGenerativeAI(
        model=MODEL_NAME, 
        temperature=MODEL_TEMPERATURE,

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