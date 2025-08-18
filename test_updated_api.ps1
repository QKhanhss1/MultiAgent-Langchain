# Test script for updated Multi-Agent API with userId support
# Usage: .\test_updated_api.ps1

Write-Host "🧪 Testing Updated Multi-Agent API with UserId Support" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Gray

# Configuration
$baseUrl = "http://localhost:9000"
$headers = @{
    'Content-Type' = 'application/json'
    'Accept' = 'application/json'
}

# Test token (replace with your actual token)
$testToken = " "
$testUserId = 5089

Write-Host "🔑 Test Token: $($testToken.Substring(0, 50))..." -ForegroundColor Yellow
Write-Host "👤 Test User ID: $testUserId" -ForegroundColor Yellow
Write-Host ""

# Test scenarios
$testScenarios = @(
    @{
        agent = "tasks"
        message = "List all my tasks"
        description = "Testing tasks agent"
    },
    @{
        agent = "calendar"
        message = "Show my events for today"
        description = "Testing calendar agent"
    },
    @{
        agent = "gmail"
        message = "Show my unread emails"
        description = "Testing gmail agent"
    }
)

foreach ($i in 1..$testScenarios.Count) {
    $scenario = $testScenarios[$i-1]
    
    Write-Host "🧪 Test $i`: $($scenario.description)" -ForegroundColor Cyan
    Write-Host "🤖 Agent: $($scenario.agent)"
    Write-Host "💬 Message: $($scenario.message)"
    
    # Prepare request body with new format
    $requestBody = @{
        message = $scenario.message
        agent_type = $scenario.agent
        access_token = $testToken
        user_id = $testUserId
        conversation_id = "test_session_$i"
    } | ConvertTo-Json
    
    try {
        Write-Host "📡 Sending request..." -ForegroundColor Gray
        $response = Invoke-RestMethod -Uri "$baseUrl/chat" -Method POST -Headers $headers -Body $requestBody -TimeoutSec 30
        
        Write-Host "✅ Success!" -ForegroundColor Green
        Write-Host "📥 Response: $($response.response.Substring(0, [Math]::Min(100, $response.response.Length)))..."
        Write-Host "👤 User ID: $($response.user_id)"
        Write-Host "🕒 Timestamp: $($response.timestamp)"
        
    } catch {
        Write-Host "❌ Test failed!" -ForegroundColor Red
        Write-Host "📥 Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host "-" * 60 -ForegroundColor Gray
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "🏁 API testing completed!" -ForegroundColor Green
Write-Host "💡 New Features:" -ForegroundColor Yellow
Write-Host "   ✅ User ID parameter support" -ForegroundColor Green
Write-Host "   ✅ Enhanced conversation isolation" -ForegroundColor Green
Write-Host "   ✅ InCard integration ready" -ForegroundColor Green
Write-Host "   ✅ Better error handling" -ForegroundColor Green
