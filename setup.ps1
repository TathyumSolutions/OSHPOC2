# setup.ps1 - Insurance Eligibility Agent (Windows PowerShell)
# Run from the project root:   powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
}

function Ensure-Venv {
    param([string]$Dir, [string]$Label)
    $venv = Join-Path $Dir "venv"
    if (-not (Test-Path $venv)) {
        Write-Host "  Creating virtual environment for $Label ..." -ForegroundColor Yellow
        & python -m venv $venv
    }
    return $venv
}

function Install-Deps {
    param([string]$Dir, [string]$Label)
    $venv = Ensure-Venv -Dir $Dir -Label $Label
    $pip  = Join-Path $venv "Scripts" "pip.exe"
    $reqs = Join-Path $Dir "requirements.txt"
    Write-Host "  Installing dependencies for $Label ..." -ForegroundColor Yellow
    & $pip install -r $reqs --quiet
}

Write-Header "Insurance Eligibility Agent - Windows Setup"

$envFile    = Join-Path $BackendDir ".env"
$envExample = Join-Path $BackendDir ".env.example"

if (-not (Test-Path $envFile)) {
    Write-Host "  .env not found - copying from .env.example" -ForegroundColor Yellow
    Copy-Item $envExample $envFile
}

$envContent = Get-Content $envFile -Raw
if ($envContent -match "your-openai-api-key-here") {
    Write-Host ""
    Write-Host "  [!] IMPORTANT: Open backend\.env and replace" -ForegroundColor Red
    Write-Host "      'your-openai-api-key-here' with your actual OpenAI API key" -ForegroundColor Red
    Write-Host "      before running the backend." -ForegroundColor Red
}

Write-Host ""
Write-Host "  1) Install dependencies only" -ForegroundColor White
Write-Host "  2) Run Backend  (port 5000)" -ForegroundColor White
Write-Host "  3) Run Frontend (port 8501)" -ForegroundColor White
Write-Host "  4) Install + Run Backend  (then open a 2nd window and pick 3)" -ForegroundColor White
Write-Host "  5) Exit" -ForegroundColor White
Write-Host ""

$choice = Read-Host "  Enter choice [1-5]"

if ($choice -eq "1") {
    Write-Header "Installing Dependencies"
    Install-Deps -Dir $BackendDir  -Label "Backend"
    Install-Deps -Dir $FrontendDir -Label "Frontend"
    Write-Host "  [OK] Done. Run this script again and choose 4, or 2 and 3 separately." -ForegroundColor Green
}
elseif ($choice -eq "2") {
    Write-Header "Starting Backend"
    Install-Deps -Dir $BackendDir -Label "Backend"
    $python = Join-Path $BackendDir "venv" "Scripts" "python.exe"
    Set-Location $BackendDir
    & $python app.py
}
elseif ($choice -eq "3") {
    Write-Header "Starting Frontend"
    Install-Deps -Dir $FrontendDir -Label "Frontend"
    $streamlit = Join-Path $FrontendDir "venv" "Scripts" "streamlit.exe"
    Set-Location $FrontendDir
    & $streamlit run streamlit_app.py
}
elseif ($choice -eq "4") {
    Write-Header "Install + Run Backend"
    Install-Deps -Dir $BackendDir  -Label "Backend"
    Install-Deps -Dir $FrontendDir -Label "Frontend"
    Write-Host ""
    Write-Host "  [OK] Dependencies installed." -ForegroundColor Green
    Write-Host "  Starting Backend now ..." -ForegroundColor Green
    Write-Host "  Open a NEW PowerShell window and run:" -ForegroundColor Green
    Write-Host "      powershell -ExecutionPolicy Bypass -File setup.ps1  -> choose 3" -ForegroundColor Green
    Write-Host ""
    $python = Join-Path $BackendDir "venv" "Scripts" "python.exe"
    Set-Location $BackendDir
    & $python app.py
}
elseif ($choice -eq "5") {
    Write-Host "  Goodbye." -ForegroundColor Cyan
}
else {
    Write-Host "  Invalid choice." -ForegroundColor Red
}
