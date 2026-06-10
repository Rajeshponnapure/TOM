param(
    [switch]$Bootstrap,
    [string]$RepoRoot = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'

function Write-Section([string]$Text) {
    Write-Host ""
    Write-Host "=== $Text ===" -ForegroundColor Cyan
}

function Test-Command([string]$Name) {
    try {
        Get-Command $Name -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

Set-Location $RepoRoot

Write-Host "TOM Secondary Laptop Setup Checklist" -ForegroundColor Green
Write-Host "Repo root: $RepoRoot"

Write-Section "Prerequisites"
$checks = @(
    @{ Label = 'Python'; Name = 'python' },
    @{ Label = 'pip'; Name = 'pip' },
    @{ Label = 'Chrome'; Name = 'chrome' },
    @{ Label = 'Ollama'; Name = 'ollama' },
    @{ Label = 'ffmpeg'; Name = 'ffmpeg' },
    @{ Label = 'Tesseract'; Name = 'tesseract' }
)

foreach ($check in $checks) {
    $available = Test-Command $check.Name
    $status = if ($available) { 'OK' } else { 'MISSING' }
    $color = if ($available) { 'Green' } else { 'Yellow' }
    Write-Host ("{0,-10} {1}" -f $check.Label, $status) -ForegroundColor $color
}

if ($Bootstrap) {
    Write-Section "Bootstrap"
    if (-not (Test-Path '.\venv')) {
        Write-Host 'Creating virtual environment...'
        python -m venv venv
    }

    Write-Host 'Installing Python dependencies...'
    .\venv\Scripts\python.exe -m pip install --upgrade pip
    .\venv\Scripts\python.exe -m pip install -r requirements.txt

    Write-Host 'Running one Instagram validation pass...'
    .\venv\Scripts\python.exe agents\instagram_ai_news_agent\main.py --once
}

Write-Section "Manual Next Steps"
Write-Host '1. Fill in .env values for Gmail, Ollama, and the Chrome profile.'
Write-Host '2. Confirm Instagram login in the chosen Chrome profile.'
Write-Host '3. Run start_email_agent_daemon.bat and start_instagram_agent_daemon.bat after the one-off validation pass.'
Write-Host '4. Create KeepAlive and OnLogon scheduled tasks once the manual run succeeds.'
