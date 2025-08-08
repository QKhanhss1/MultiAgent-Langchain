# Multi-Agent Google Services API

A FastAPI-based REST API for interacting with Google Tasks, Calendar, and Gmail through intelligent agents powered by LangChain and Google's Gemini AI.

## 🚀 Features

- **Multi-Agent Support**: Choose between Tasks, Calendar, and Gmail agents
- **Persistent Conversations**: Maintain conversation history across multiple requests
- **RESTful API**: Clean HTTP endpoints for easy integration
- **Interactive Documentation**: Automatic OpenAPI documentation
- **CLI Mode**: Fallback command-line interface

## 📋 Available Agents

1. **Tasks Agent** (`tasks`)
   - Create, read, update, and delete Google Tasks
   - Manage task lists and due dates
   - Mark tasks as complete/incomplete

2. **Calendar Agent** (`calendar`)
   - Create, update, and delete calendar events
   - Search events by date range
   - Manage event attendees and reminders

3. **Gmail Agent** (`gmail`)
   - Read and search emails
   - Get email summaries
   - Access inbox, sent, and other folders

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MultiAgent-basic
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google API credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Calendar, Tasks, and Gmail APIs
   - Create OAuth 2.0 credentials
   - Download the credentials file as `credentials.json`
   - Place it in the project root directory

4. **Set up environment variables**
   ```bash
   # Create .env file
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```

## 🚀 Running the API

### API Server Mode (Default)
```bash
python main.py
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

### CLI Mode
```bash
python main.py --cli
```

## 📡 API Endpoints

### 1. Get Available Agents
```http
GET /agents
```

**Response:**
```json
{
  "agents": [
    {
      "type": "tasks",
      "name": "Google Tasks Agent",
      "description": "Manage Google Tasks"
    },
    {
      "type": "calendar", 
      "name": "Google Calendar Agent",
      "description": "Manage Google Calendar events"
    },
    {
      "type": "gmail",
      "name": "Gmail Agent", 
      "description": "Read and manage Gmail"
    }
  ]
}
```

### 2. Chat with Agent
```http
POST /chat
```

**Request Body:**
```json
{
  "message": "What events do I have this week?",
  "agent_type": "calendar",
  "conversation_id": "user123_session1",
  "token": "auth_token_here"
}
```

**Response:**
```json
{
  "response": "Here are your events for this week...",
  "agent_type": "calendar",
  "conversation_id": "user123_session1", 
  "timestamp": "2025-08-07T10:30:00",
  "token": "auth_token_here"
}
```

### 3. Get Conversation History
```http
GET /conversations/{conversation_id}/history?agent_type=calendar
```

**Response:**
```json
{
  "conversation_id": "user123_session1",
  "agent_type": "calendar",
  "history": [
    {
      "type": "human",
      "content": "What events do I have this week?",
      "timestamp": null
    },
    {
      "type": "ai", 
      "content": "Here are your events for this week...",
      "timestamp": null
    }
  ],
  "total_messages": 2
}
```

### 4. Clear Conversation
```http
DELETE /conversations/{conversation_id}?agent_type=all
```

**Response:**
```json
{
  "message": "Cleared 3 conversation(s)",
  "conversation_id": "user123_session1"
}
```

## 🧪 Testing the API

### Automated Tests
```bash
python test_api.py
```

### Interactive Testing
```bash
python test_api.py --interactive
```

### Example cURL Commands

1. **List agents:**
   ```bash
   curl -X GET "http://localhost:8000/agents"
   ```

2. **Chat with calendar agent:**
   ```bash
   curl -X POST "http://localhost:8000/chat" \
        -H "Content-Type: application/json" \
        -d '{
          "message": "Create a meeting tomorrow at 2pm",
          "agent_type": "calendar",
          "conversation_id": "test123",
          "token": "your_auth_token"
        }'
   ```

3. **Get conversation history:**
   ```bash
   curl -X GET "http://localhost:8000/conversations/test123/history?agent_type=calendar"
   ```

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `PORT`: API server port (default: 8000)
- `HOST`: API server host (default: 0.0.0.0)

### Agent Configuration
Agent prompts are stored in the `prompts/` directory:
- `prompts/tasks_agent_prompt.md`
- `prompts/calendar_agent_prompt.md`  
- `prompts/gmail_agent_prompt.md`

## 🎯 Use Cases

### 1. Personal Assistant Integration
```python
import requests

def schedule_meeting(title, datetime, attendees, token):
    response = requests.post("http://localhost:8000/chat", json={
        "message": f"Create a meeting '{title}' on {datetime} with {attendees}",
        "agent_type": "calendar",
        "conversation_id": "assistant_session",
        "token": token
    })
    return response.json()["response"]
```

### 2. Task Management Dashboard
```python
def get_daily_tasks():
    response = requests.post("http://localhost:8000/chat", json={
        "message": "Show me all tasks due today",
        "agent_type": "tasks", 
        "conversation_id": "dashboard"
    })
    return response.json()["response"]
```

### 3. Email Summarization
```python
def get_email_summary():
    response = requests.post("http://localhost:8000/chat", json={
        "message": "Summarize my unread emails from today",
        "agent_type": "gmail",
        "conversation_id": "email_summary"
    })
    return response.json()["response"]
```

## 🐛 Troubleshooting

### Common Issues

1. **401 Unauthorized Error**
   - Ensure `credentials.json` is in the project root
   - Run the app once to complete OAuth flow
   - Check if `token.json` was created

2. **Module Not Found Errors**
   - Install all dependencies: `pip install -r requirements.txt`
   - Use virtual environment: `python -m venv venv && source venv/bin/activate`

3. **API Key Errors**
   - Set `GOOGLE_API_KEY` in `.env` file
   - Ensure Gemini API is enabled in Google Cloud Console

4. **Port Already in Use**
   - Change port: `uvicorn main:app --port 8001`
   - Or kill existing process: `lsof -ti:8000 | xargs kill`

## 📝 Development

### Adding New Agents
1. Create new tool functions in `tools/`
2. Add agent prompt in `prompts/`
3. Update `get_agent_tools_and_prompt()` function
4. Add agent info to `/agents` endpoint

### Extending API
- Add new endpoints in `main.py`
- Update Pydantic models for request/response schemas
- Add tests in `test_api.py`

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

**Happy coding! 🎉**
