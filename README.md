# Multi-Agent Google Services API

A containerized API for managing Google Calendar, Tasks, and Gmail using AI agents with token-based authentication.

## 🚀 Quick Start

```bash
# Start the API
docker-compose up -d

# Test the API  
curl http://localhost:8000/agents

# Stop the API
docker-compose down
```

## 📡 API Usage

All endpoints require a Google OAuth access token:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "List my calendar events",
    "agent_type": "calendar",
    "conversation_id": "session-123",
    "token": "your_google_oauth_access_token"
  }'
```

## 🤖 Available Agents

- **`calendar`** - Google Calendar management
- **`tasks`** - Google Tasks management  
- **`gmail`** - Gmail reading and management

## 🔐 Authentication

Get Google OAuth tokens from: https://developers.google.com/oauthplayground/

Required scopes:
```
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/tasks
https://www.googleapis.com/auth/gmail.readonly
```

## 📚 Documentation

- **API Docs**: http://localhost:8000/docs
- **Interactive**: http://localhost:8000/redoc

## 🛠 Development

```bash
# Run locally (optional)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

That's it! 🎉