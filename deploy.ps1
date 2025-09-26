#!/usr/bin/env powershell
# Simple deployment script

Write-Host "🚀 Starting Multi-Agent API..." -ForegroundColor Green

# Start with Docker Compose
docker-compose up -d

# Quick health check
Start-Sleep -Seconds 5
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/" -TimeoutSec 5
    Write-Host "✅ API is running at http://localhost:9090" -ForegroundColor Green
    Write-Host "📚 Documentation: http://localhost:9090/docs" -ForegroundColor Cyan
}
catch {
    Write-Host "❌ API failed to start. Check logs: docker-compose logs" -ForegroundColor Red
}
