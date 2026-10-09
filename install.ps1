# ask — Windows PowerShell one-line installer
# Usage:
#   irm https://raw.githubusercontent.com/sinhaKAN-ra/ask/main/install.ps1 | iex
#
# Requires: Python 3.8+ on PATH. Zero extra dependencies.

$ErrorActionPreference = "Stop"

$RepoRaw = "https://raw.githubusercontent.com/sinhaKAN-ra/ask/main"
$BaseDir = Join-Path $HOME ".ask-cli"
$BinDir  = Join-Path $BaseDir "bin"
$ScriptPath = Join-Path $BaseDir "ask.py"
$CmdPath    = Join-Path $BinDir "ask.cmd"
$Ps1Path    = Join-Path $BinDir "ask.ps1"
$ConfigPath = Join-Path $BaseDir "config.json"

Write-Host "==> Installing ask to $BaseDir" -ForegroundColor Cyan

# Check for python
$pythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonCmd = "py -3"
}

if (-not $pythonCmd) {
    Write-Host "error: Python 3.8+ is required. Please install Python from https://python.org or the Microsoft Store." -ForegroundColor Red
    exit 1
}

# Create directories
if (-not (Test-Path $BaseDir)) { New-Item -ItemType Directory -Path $BaseDir | Out-Null }
if (-not (Test-Path $BinDir))  { New-Item -ItemType Directory -Path $BinDir | Out-Null }

# Download ask.py
Write-Host "==> Downloading ask.py" -ForegroundColor Cyan
Invoke-WebRequest -Uri "$RepoRaw/src/aolbeam_ask/ask.py" -OutFile $ScriptPath -UseBasicParsing

# Create batch script wrapper for cmd.exe
$cmdContent = "@echo off`r`n$pythonCmd `"%USERPROFILE%\.ask-cli\ask.py`" %*"
Set-Content -Path $CmdPath -Value $cmdContent -Encoding ASCII

# Create PowerShell wrapper
$ps1Content = "& $pythonCmd `"`$HOME\.ask-cli\ask.py`" @args"
Set-Content -Path $Ps1Path -Value $ps1Content -Encoding ASCII

# Seed config if none exists
if (-not (Test-Path $ConfigPath)) {
    try {
        Invoke-WebRequest -Uri "$RepoRaw/config.json.example" -OutFile $ConfigPath -UseBasicParsing
    } catch {
        # ignore if offline or rate limited
    }
}

# Check / add PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    Write-Host "==> Adding $BinDir to User PATH" -ForegroundColor Green
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    $env:Path = "$env:Path;$BinDir"
    Write-Host "NOTE: You may need to restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==> Installation complete!" -ForegroundColor Green
Write-Host "Get a free Groq key at https://console.groq.com/keys then run:"
Write-Host "    `$env:GROQ_API_KEY = `"gsk_your_key`""
Write-Host "    ask `"hello, are you working?`""
