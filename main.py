
import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from agent_graph import create_agent, create_agent_with_token
from tools.google_tasks_tools import tasks_tools
from tools.google_calendar_tools import calendar_tools
from tools.google_gmail_tools import gmail_tools
# API Models
class ChatRequest(BaseModel):
    message: str
    agent_type: str  # "tasks", "calendar", or "gmail"
    conversation_id: str = "default"
    token: str  # Authentication or session token

class ChatResponse(BaseModel):
    response: str
    agent_type: str
    conversation_id: str
    timestamp: str
    token: str  # Echo back the token for reference

class AgentListResponse(BaseModel):
    agents: List[Dict[str, str]]

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent Google Services API",
    description="API for interacting with Google Tasks, Calendar, and Gmail agents",
    version="1.0.0"
)

# Store conversation histories
conversation_histories: Dict[str, List[Any]] = {}

def get_agent_tools_and_prompt(agent_type: str):
    """Get tools and prompt file for specified agent type."""
    agent_map = {
        "tasks": (tasks_tools, "prompts/tasks_agent_prompt.md"),
        "calendar": (calendar_tools, "prompts/calendar_agent_prompt.md"),
        "gmail": (gmail_tools, "prompts/gmail_agent_prompt.md")
    }
    
    if agent_type not in agent_map:
        raise HTTPException(status_code=400, detail=f"Invalid agent type. Must be one of: {list(agent_map.keys())}")
    
    return agent_map[agent_type]

def load_and_format_prompt(prompt_file: str, access_token: str = None):
    """Tải prompt từ file và điền các giá trị động."""
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    
    # Add token instruction to the prompt
    token_instruction = ""
    if access_token:
        token_instruction = f"\n\n**QUAN TRỌNG: Bạn có access token sau để gọi Google APIs: {access_token}**"
    
    formatted_prompt = prompt_template.format(
        current_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))), 
        start_of_day=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    ) + token_instruction
    
    return formatted_prompt

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Multi-Agent Google Services API",
        "version": "1.0.0",
        "endpoints": "/docs for documentation"
    }

@app.get("/agents", response_model=AgentListResponse)
async def get_available_agents():
    """Get list of available agents."""
    agents = [
        {"type": "tasks", "name": "Google Tasks Agent", "description": "Manage Google Tasks"},
        {"type": "calendar", "name": "Google Calendar Agent", "description": "Manage Google Calendar events"},
        {"type": "gmail", "name": "Gmail Agent", "description": "Read and manage Gmail"}
    ]
    return AgentListResponse(agents=agents)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """Chat with specified agent."""
    try:
        # Validate token (you can add your own validation logic here)
        if not request.token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        # Get tools and prompt for the specified agent
        tools, prompt_file = get_agent_tools_and_prompt(request.agent_type)
        
        # Create agent
        agent_app = create_agent_with_token(tools, request.token)
        
        # Load and format prompt with token
        formatted_prompt = load_and_format_prompt(prompt_file, request.token)
        system_prompt = SystemMessage(content=formatted_prompt)
        
        # Get or create conversation history
        conv_key = f"{request.agent_type}_{request.conversation_id}"
        if conv_key not in conversation_histories:
            conversation_histories[conv_key] = []
        
        conversation_history = conversation_histories[conv_key]
        
        # Add user message to history
        user_message = HumanMessage(content=request.message)
        conversation_history.append(user_message)
        
        # Prepare messages for agent
        messages_for_graph = [system_prompt] + conversation_history
        
        # Get response from agent
        final_state = agent_app.invoke({"messages": messages_for_graph})
        ai_response = final_state['messages'][-1]
        
        # Add AI response to history
        conversation_history.append(ai_response)
        
        # Update conversation history
        conversation_histories[conv_key] = conversation_history
        
        return ChatResponse(
            response=ai_response.content,
            agent_type=request.agent_type,
            conversation_id=request.conversation_id,
            timestamp=datetime.datetime.now().isoformat(),
            token=request.token
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str, agent_type: str = "all"):
    """Clear conversation history for specified conversation ID."""
    try:
        if agent_type == "all":
            # Clear all conversations for this ID across all agents
            keys_to_delete = [key for key in conversation_histories.keys() if key.endswith(f"_{conversation_id}")]
        else:
            # Clear specific agent conversation
            keys_to_delete = [f"{agent_type}_{conversation_id}"]
        
        for key in keys_to_delete:
            if key in conversation_histories:
                del conversation_histories[key]
        
        return {"message": f"Cleared {len(keys_to_delete)} conversation(s)", "conversation_id": conversation_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")

@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, agent_type: str):
    """Get conversation history for specified conversation ID and agent type."""
    try:
        conv_key = f"{agent_type}_{conversation_id}"
        history = conversation_histories.get(conv_key, [])
        
        formatted_history = []
        for message in history:
            if hasattr(message, 'content'):
                message_type = "human" if isinstance(message, HumanMessage) else "ai"
                formatted_history.append({
                    "type": message_type,
                    "content": message.content,
                    "timestamp": getattr(message, 'timestamp', None)
                })
        
        return {
            "conversation_id": conversation_id,
            "agent_type": agent_type,
            "history": formatted_history,
            "total_messages": len(formatted_history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation history: {str(e)}")

def cli_mode():
    """CLI mode for direct interaction (backup)."""
    load_dotenv()
    
    print("=== CLI Mode ===")
    print("Available agents: tasks, calendar, gmail")
    
    while True:
        agent_type = input("Choose agent (tasks/calendar/gmail) or 'exit': ").lower()
        if agent_type == 'exit':
            print("Goodbye!")
            break
            
        if agent_type not in ['tasks', 'calendar', 'gmail']:
            print("Invalid agent type. Please choose tasks, calendar, or gmail.")
            continue
            
        try:
            # For CLI mode, we need to get a token from user
            token = input("Enter your Google access token: ").strip()
            if not token:
                print("Error: Access token is required for API access.")
                continue
                
            tools, prompt_file = get_agent_tools_and_prompt(agent_type)
            agent_app = create_agent_with_token(tools, token)
            formatted_prompt = load_and_format_prompt(prompt_file)
            system_prompt = SystemMessage(content=formatted_prompt)
            
            conversation_history = []
            print(f"\n{agent_type.title()} Agent ready. (type 'back' to choose another agent)")
            
            while True:
                user_input = input(">> You: ")
                if user_input.lower() in ['back', 'exit']:
                    break
                    
                conversation_history.append(HumanMessage(content=user_input))
                messages_for_graph = [system_prompt] + conversation_history
                
                try:
                    final_state = agent_app.invoke({"messages": messages_for_graph})
                    ai_response = final_state['messages'][-1]
                    print(f">> Agent: {ai_response.content}")
                    conversation_history.append(ai_response)
                except Exception as e:
                    print(f"Error: {e}")
                    
        except Exception as e:
            print(f"Error initializing agent: {e}")

def main():
    """API server main function."""
    import sys
    
    # Check if CLI mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        cli_mode()
        return
    
    load_dotenv()
    
    print("🚀 Starting Multi-Agent Google Services API...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔧 Interactive API: http://localhost:8000/redoc")
    print("💬 Chat endpoint: POST http://localhost:8000/chat")
    print("📋 Available agents: GET http://localhost:8000/agents")
    print("\n💡 Tip: Use --cli flag to run in CLI mode")
    
    # Run the FastAPI server
    uvicorn.run(
        "main:app",  # Use import string instead of app object
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()