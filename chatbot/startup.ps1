# AlumCraft AI Customer Service System
# Quick Startup Script for Windows PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AlumCraft AI Chatbot - Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Ollama
Write-Host "[1/3] Checking Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  [OK] Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Ollama is not running" -ForegroundColor Red
    Write-Host "  Please run: ollama serve" -ForegroundColor Yellow
    Write-Host "  Then restart this script." -ForegroundColor Yellow
    exit 1
}

# Check Model
Write-Host ""
Write-Host "[2/3] Checking model 'qwen3.5'..." -ForegroundColor Yellow
$models = ollama list 2>$null
if ($models -match "qwen3.5") {
    Write-Host "  [OK] Model qwen3.5 is available" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Model qwen3.5 not found" -ForegroundColor Red
    Write-Host "  Please run: ollama pull qwen3.5" -ForegroundColor Yellow
}

# Test API
Write-Host ""
Write-Host "[3/3] Testing Ollama API..." -ForegroundColor Yellow
$test = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
if ($test) {
    Write-Host "  [OK] Ollama API is responding" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Start Ngrok: ngrok http 11434" -ForegroundColor White
Write-Host "  2. Copy the HTTPS URL from Ngrok" -ForegroundColor White
Write-Host "  3. Update API_BASE_URL in chat.js" -ForegroundColor White
Write-Host "  4. Open chatbot/index.html in browser" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
