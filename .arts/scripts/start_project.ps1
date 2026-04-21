$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$backendDir = Join-Path $root '服务端'
$frontendDir = Join-Path $root '网页\legal-ai-web'
$backendPort = 8111
$frontendPort = 5173

function Test-CommandAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Stop-PortProcess {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return
    }

    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
        }
    }
}

if (-not (Test-CommandAvailable 'python')) {
    Write-Host '[ERROR] 未找到 python，请先安装 Python 并加入 PATH。' -ForegroundColor Red
    exit 1
}

if (-not (Test-CommandAvailable 'npm')) {
    Write-Host '[ERROR] 未找到 npm，请先安装 Node.js 并加入 PATH。' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $backendDir 'app.py'))) {
    Write-Host "[ERROR] 未找到后端入口文件：$backendDir\app.py" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $frontendDir 'package.json'))) {
    Write-Host "[ERROR] 未找到前端入口文件：$frontendDir\package.json" -ForegroundColor Red
    exit 1
}

Write-Host '========================================'
Write-Host '   Smart Judicial System - Launcher'
Write-Host '========================================'
Write-Host ''

Write-Host "[1/3] Cleaning old processes on ports $backendPort and $frontendPort..."
Stop-PortProcess -Port $backendPort
Stop-PortProcess -Port $frontendPort
Start-Sleep -Seconds 1

$backendCommand = "cd /d `"$backendDir`" && set TRANSFORMERS_NO_IMAGE=1 && set FOR_DISABLE_CONSOLE_CTRL_HANDLER=1 && python -m uvicorn app:app --reload --host 127.0.0.1 --port $backendPort"
$frontendCommand = "cd /d `"$frontendDir`" && npm run dev -- --host 127.0.0.1 --port $frontendPort --strictPort"

Write-Host "[2/3] Starting backend on http://127.0.0.1:$backendPort ..."
Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $backendCommand | Out-Null

Write-Host "[3/3] Starting frontend on http://127.0.0.1:$frontendPort ..."
Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', $frontendCommand | Out-Null

Write-Host ''
Write-Host 'Waiting for services to warm up...'
Start-Sleep -Seconds 8

Start-Process "http://127.0.0.1:$frontendPort" | Out-Null

Write-Host ''
Write-Host '========================================'
Write-Host '   Startup Complete'
Write-Host '========================================'
Write-Host "Backend : http://127.0.0.1:$backendPort"
Write-Host "Frontend: http://127.0.0.1:$frontendPort"
Write-Host ''
