# Multi-Agent API with Token-Based Authentication

## Overview

This API now uses **token-based authentication** where Google OAuth access tokens are passed in the request body instead of using local credential files. This approach is more secure and flexible for production deployments.

## Key Changes

### ✅ Authentication Architecture
- **Before**: Local `credentials.json` and `token.json` files
- **After**: Access tokens passed in API request bodies
- **Benefit**: No credential files needed, more secure, easier deployment

### ✅ API Endpoints
All endpoints now require an `access_token` parameter:

```json
{
  "message": "List my calendar events",
  "agent_type": "calendar", 
  "conversation_id": "unique-id",
  "token": "your_google_oauth_access_token"
}
```

### ✅ Google Service Tools
All Google service integrations now use token-based authentication:
- **Calendar Tools**: `tools/google_calendar_tools.py`
- **Tasks Tools**: `tools/google_tasks_tools.py`  
- **Gmail Tools**: `tools/google_gmail_tools.py`

## Usage

### 1. Start the API Server
```bash
cd "d:\Program Files\LearnLangchain\MultiAgent-basic"
.\venv\Scripts\Activate.ps1
python main.py
```

### 2. API Documentation
- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Example Request
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What events do I have today?",
    "agent_type": "calendar",
    "conversation_id": "session-123",
    "token": "your_real_google_access_token"
  }'
```

### 4. Available Agents
- `tasks`: Google Tasks management
- `calendar`: Google Calendar management  
- `gmail`: Gmail reading and management

## Getting Google Access Tokens

To use this API, you need a valid Google OAuth2 access token with appropriate scopes:

### Required Scopes
```
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/tasks
https://www.googleapis.com/auth/gmail.readonly
```

### Methods to Get Tokens
1. **Google OAuth2 Playground**: https://developers.google.com/oauthplayground/
2. **Your own OAuth2 flow** in your frontend application
3. **Google Cloud Console** for testing

## API Endpoints

### GET /agents
List available agents
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

### POST /chat
Chat with a specific agent
```json
{
  "message": "string",
  "agent_type": "tasks|calendar|gmail",
  "conversation_id": "string", 
  "token": "string"
}
```

### DELETE /conversations/{conversation_id}
Clear conversation history
```bash
DELETE /conversations/session-123?agent_type=calendar
```

### GET /conversations/{conversation_id}/history
Get conversation history
```bash
GET /conversations/session-123/history?agent_type=calendar
```

## Docker Deployment

The Docker setup has been simplified to remove credential file dependencies:

```bash
docker build -t multiagent-api .
docker run -p 8000:8000 multiagent-api
```

No volume mounts or credential files needed!

## Error Handling

### Invalid/Expired Token
```json
{
  "response": "Lỗi khi liệt kê sự kiện: <error details>. Hãy chắc chắn access token còn hiệu lực.",
  "agent_type": "calendar",
  "conversation_id": "test-123", 
  "timestamp": "2025-08-08T09:47:04.258519",
  "token": "invalid_token"
}
```

### Missing Token
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "token"],
      "msg": "Field required"
    }
  ]
}
```

## Testing

Use the provided test script:
```bash
python test_token_api.py
```

## Security Notes

1. **Access tokens expire**: Implement token refresh logic in your client
2. **HTTPS only**: Use HTTPS in production to protect tokens in transit
3. **Token validation**: Add additional token validation if needed
4. **Rate limiting**: Consider implementing rate limiting for production use

## Migration from Local Auth

If migrating from the previous local authentication setup:
1. Remove `credentials.json` and `token.json` dependencies
2. Update your client applications to pass tokens in request bodies
3. Implement OAuth2 flow in your frontend to obtain access tokens
4. Update Docker deployments to remove credential volume mounts

## Technical Architecture

```
Client Request → FastAPI → Agent Graph → Google Tools → Google APIs
     ↑                                        ↑
   Token                            Token passed through
```

The access token flows through the entire system:
1. Client provides token in request body
2. FastAPI validates token presence
3. Agent creation includes token binding
4. Tools receive token as first parameter
5. Google APIs called with token-based credentials
