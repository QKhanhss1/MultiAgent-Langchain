import requests
import json

# API Base URL
BASE_URL = "http://localhost:8000"

def test_api():
    """Test the Multi-Agent API endpoints."""
    
    print("🧪 Testing Multi-Agent Google Services API\n")
    
    # Test 1: Get available agents
    print("1. Getting available agents...")
    response = requests.get(f"{BASE_URL}/agents")
    if response.status_code == 200:
        agents = response.json()
        print(f"✅ Available agents: {len(agents['agents'])}")
        for agent in agents['agents']:
            print(f"   - {agent['name']} ({agent['type']})")
    else:
        print(f"❌ Failed to get agents: {response.status_code}")
    
    print("\n" + "="*50)
    
    # Test 2: Chat with Calendar Agent
    print("2. Testing Calendar Agent...")
    chat_data = {
        "message": "What events do I have this week?",
        "agent_type": "calendar",
        "conversation_id": "test_conversation",
        "token": "test_token_123"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=chat_data)
    if response.status_code == 200:
        result = response.json()
        print("✅ Calendar Agent Response:")
        print(f"   {result['response'][:100]}...")
    else:
        print(f"❌ Failed to chat with calendar agent: {response.status_code}")
        print(f"   Error: {response.text}")
    
    print("\n" + "="*50)
    
    # Test 3: Chat with Tasks Agent
    print("3. Testing Tasks Agent...")
    chat_data = {
        "message": "Show me my tasks",
        "agent_type": "tasks",
        "conversation_id": "test_conversation",
        "token": "test_token_456"
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=chat_data)
    if response.status_code == 200:
        result = response.json()
        print("✅ Tasks Agent Response:")
        print(f"   {result['response'][:100]}...")
    else:
        print(f"❌ Failed to chat with tasks agent: {response.status_code}")
        print(f"   Error: {response.text}")
    
    print("\n" + "="*50)
    
    # Test 4: Get conversation history
    print("4. Getting conversation history...")
    response = requests.get(f"{BASE_URL}/conversations/test_conversation/history?agent_type=calendar")
    if response.status_code == 200:
        history = response.json()
        print(f"✅ Calendar conversation has {history['total_messages']} messages")
    else:
        print(f"❌ Failed to get conversation history: {response.status_code}")
    
    print("\n" + "="*50)
    
    # Test 5: Clear conversation
    print("5. Clearing conversation...")
    response = requests.delete(f"{BASE_URL}/conversations/test_conversation?agent_type=all")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
    else:
        print(f"❌ Failed to clear conversation: {response.status_code}")

def interactive_test():
    """Interactive testing mode."""
    print("🎯 Interactive API Testing Mode")
    print("Available commands:")
    print("  - 'agents' - List available agents")
    print("  - 'chat <agent_type> <message>' - Chat with an agent")
    print("  - 'history <agent_type> <conv_id>' - Get conversation history")
    print("  - 'clear <conv_id>' - Clear conversation")
    print("  - 'exit' - Exit")
    
    while True:
        command = input("\n> ").strip()
        
        if command == "exit":
            print("Goodbye!")
            break
        elif command == "agents":
            response = requests.get(f"{BASE_URL}/agents")
            if response.status_code == 200:
                agents = response.json()['agents']
                for agent in agents:
                    print(f"  {agent['type']}: {agent['description']}")
            else:
                print(f"Error: {response.status_code}")
        
        elif command.startswith("chat "):
            parts = command.split(" ", 2)
            if len(parts) >= 3:
                agent_type = parts[1]
                message = parts[2]
                
                chat_data = {
                    "message": message,
                    "agent_type": agent_type,
                    "conversation_id": "interactive",
                    "token": "interactive_token"
                }
                
                response = requests.post(f"{BASE_URL}/chat", json=chat_data)
                if response.status_code == 200:
                    result = response.json()
                    print(f"\n{agent_type.title()} Agent: {result['response']}")
                else:
                    print(f"Error: {response.status_code} - {response.text}")
            else:
                print("Usage: chat <agent_type> <message>")
        
        elif command.startswith("history "):
            parts = command.split(" ")
            if len(parts) >= 3:
                agent_type = parts[1]
                conv_id = parts[2]
                
                response = requests.get(f"{BASE_URL}/conversations/{conv_id}/history?agent_type={agent_type}")
                if response.status_code == 200:
                    history = response.json()
                    print(f"\nConversation History ({history['total_messages']} messages):")
                    for msg in history['history']:
                        print(f"  {msg['type'].upper()}: {msg['content'][:80]}...")
                else:
                    print(f"Error: {response.status_code}")
            else:
                print("Usage: history <agent_type> <conversation_id>")
        
        elif command.startswith("clear "):
            conv_id = command.split(" ")[1]
            response = requests.delete(f"{BASE_URL}/conversations/{conv_id}?agent_type=all")
            if response.status_code == 200:
                print(f"Cleared conversation: {conv_id}")
            else:
                print(f"Error: {response.status_code}")
        
        else:
            print("Unknown command. Type 'exit' to quit.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_test()
    else:
        test_api()
