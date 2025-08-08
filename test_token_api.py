import requests
import json

# Test the API with a sample request
def test_api():
    base_url = "http://localhost:8000"
    
    # Test 1: Get available agents
    print("=== Testing Available Agents ===")
    response = requests.get(f"{base_url}/agents")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    # Test 2: Test chat endpoint with token
    print("=== Testing Chat Endpoint ===")
    chat_request = {
        "message": "List my upcoming calendar events",
        "agent_type": "calendar",
        "conversation_id": "test-123",
        "token": "sample_token_replace_with_real_token"
    }
    
    response = requests.post(f"{base_url}/chat", json=chat_request)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.text}")
    print()
    
    # Test 3: Test without token (should fail)
    print("=== Testing Without Token (should fail) ===")
    chat_request_no_token = {
        "message": "List my tasks",
        "agent_type": "tasks",
        "conversation_id": "test-456"
        # No token provided
    }
    
    response = requests.post(f"{base_url}/chat", json=chat_request_no_token)
    print(f"Status: {response.status_code}")
    print(f"Error: {response.text}")

if __name__ == "__main__":
    test_api()
