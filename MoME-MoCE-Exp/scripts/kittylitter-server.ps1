param(
    [ValidateSet("start", "stop", "restart", "status", "logs", "foreground")]
    [string]$Command = "start",
    [int]$Port = 8390
)

$ErrorActionPreference = "Stop"

$listenUrl = "ws://127.0.0.1:$Port"
$stdoutLog = Join-Path $env:TEMP "codex-mobile-server-$Port-manual.log"
$stderrLog = Join-Path $env:TEMP "codex-mobile-server-$Port-manual-err.log"
$litterCodex = Join-Path $env:USERPROFILE ".litter\bin\codex.cmd"
$npmCodex = Join-Path $env:APPDATA "npm\codex.cmd"
$codexCmd = if (Test-Path $litterCodex) { $litterCodex } else { $npmCodex }

function Get-KittyListener {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Show-KittyStatus {
    $listener = Get-KittyListener
    if ($null -eq $listener) {
        Write-Host "kittylitter: stopped (no listener on 127.0.0.1:$Port)"
        return
    }
    $proc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    Write-Host "kittylitter: running"
    Write-Host "  listen: $listenUrl"
    Write-Host "  pid:    $($listener.OwningProcess)"
    if ($null -ne $proc) {
        Write-Host "  proc:   $($proc.ProcessName)"
        Write-Host "  path:   $($proc.Path)"
    }
    try {
        Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/healthz" -TimeoutSec 3 | Out-Null
        Write-Host "  health: ok"
    } catch {
        Write-Host "  health: not ready ($($_.Exception.Message))"
    }
}

function Start-KittyServer {
    if (-not (Test-Path $codexCmd)) {
        throw "Codex CLI wrapper not found at $codexCmd"
    }
    $listener = Get-KittyListener
    if ($null -ne $listener) {
        Show-KittyStatus
        return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stdoutLog) | Out-Null
    Write-Host "kittylitter: starting Codex app-server on $listenUrl"
    $proc = Start-Process `
        -FilePath $codexCmd `
        -ArgumentList @("--enable", "goals", "app-server", "--listen", $listenUrl) `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog
    Write-Host "kittylitter: started pid $($proc.Id)"
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        if (Get-KittyListener) {
            break
        }
    }
    Show-KittyStatus
}

function Stop-KittyServer {
    $listener = Get-KittyListener
    if ($null -eq $listener) {
        Write-Host "kittylitter: already stopped"
        return
    }
    Write-Host "kittylitter: stopping pid $($listener.OwningProcess)"
    Stop-Process -Id $listener.OwningProcess -Force
    Start-Sleep -Milliseconds 500
    Show-KittyStatus
}

function Show-KittyLogs {
    Write-Host "stdout: $stdoutLog"
    if (Test-Path $stdoutLog) {
        Get-Content $stdoutLog -Tail 80
    }
    Write-Host ""
    Write-Host "stderr: $stderrLog"
    if (Test-Path $stderrLog) {
        Get-Content $stderrLog -Tail 120
    }
}

switch ($Command) {
    "start" { Start-KittyServer }
    "stop" { Stop-KittyServer }
    "restart" {
        Stop-KittyServer
        Start-KittyServer
    }
    "status" { Show-KittyStatus }
    "logs" { Show-KittyLogs }
    "foreground" {
        if (-not (Test-Path $codexCmd)) {
            throw "Codex CLI wrapper not found at $codexCmd"
        }
        & $codexCmd --enable goals app-server --listen $listenUrl
    }
}
