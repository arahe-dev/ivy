param(
    [ValidateSet("start", "stop", "restart", "status", "logs", "foreground")]
    [string]$Command = "start",
    [int]$ApiPort = 8766,
    [int]$WebPort = 8788
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutDir = Join-Path $Root "out\alexandria_simple"
$LogDir = Join-Path $OutDir "logs"
$DogfoodRoot = Join-Path $OutDir "dogfood"
$Python = "C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$ApiOut = Join-Path $LogDir "d_acca_hooks.out.log"
$ApiErr = Join-Path $LogDir "d_acca_hooks.err.log"
$WebOut = Join-Path $LogDir "web.out.log"
$WebErr = Join-Path $LogDir "web.err.log"

function Get-Listener([int]$Port) {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Wait-Http([string]$Url, [string]$Name) {
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "Timed out waiting for $Name at $Url"
}

function Show-ProcessForPort([string]$Name, [int]$Port, [string]$Url) {
    $listener = Get-Listener $Port
    if ($null -eq $listener) {
        Write-Host "$Name stopped on port $Port"
        return
    }
    $proc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    Write-Host "$Name running"
    Write-Host "  url:  $Url"
    Write-Host "  pid:  $($listener.OwningProcess)"
    if ($null -ne $proc) {
        Write-Host "  proc: $($proc.ProcessName)"
    }
}

function Start-AlexandriaSimple {
    New-Item -ItemType Directory -Force -Path $LogDir, $DogfoodRoot | Out-Null

    if ($null -eq (Get-Listener $ApiPort)) {
        Write-Host "Starting D-ACCA hook service on http://127.0.0.1:$ApiPort"
        Start-Process `
            -FilePath $Python `
            -ArgumentList @(
                "scripts\d_acca_dogfood_service.py",
                "serve",
                "--root",
                $DogfoodRoot,
                "--host",
                "127.0.0.1",
                "--port",
                "$ApiPort",
                "--candidate-backend",
                "indexed"
            ) `
            -WorkingDirectory $Root `
            -WindowStyle Hidden `
            -RedirectStandardOutput $ApiOut `
            -RedirectStandardError $ApiErr | Out-Null
        Wait-Http "http://127.0.0.1:$ApiPort/health" "D-ACCA hook service"
    }

    if ($null -eq (Get-Listener $WebPort)) {
        Write-Host "Starting static Alexandria Simple server on http://127.0.0.1:$WebPort"
        Start-Process `
            -FilePath $Python `
            -ArgumentList @("-m", "http.server", "$WebPort", "--bind", "127.0.0.1", "--directory", $Root) `
            -WorkingDirectory $Root `
            -WindowStyle Hidden `
            -RedirectStandardOutput $WebOut `
            -RedirectStandardError $WebErr | Out-Null
        Wait-Http "http://127.0.0.1:$WebPort/alexandria_simple/index.html?api=http://127.0.0.1:$ApiPort" "Alexandria Simple"
    }

    $url = "http://127.0.0.1:$WebPort/alexandria_simple/index.html?api=http://127.0.0.1:$ApiPort"
    Write-Host ""
    Write-Host "Alexandria Simple is ready:"
    Write-Host "  $url"
    Start-Process $url | Out-Null
    Show-AlexandriaSimpleStatus
}

function Stop-Port([string]$Name, [int]$Port) {
    $listener = Get-Listener $Port
    if ($null -eq $listener) {
        Write-Host "$Name already stopped"
        return
    }
    Write-Host "Stopping $Name pid $($listener.OwningProcess)"
    Stop-Process -Id $listener.OwningProcess -Force
}

function Stop-AlexandriaSimple {
    Stop-Port "Alexandria Simple web server" $WebPort
    Stop-Port "D-ACCA hook service" $ApiPort
}

function Show-AlexandriaSimpleStatus {
    Show-ProcessForPort "D-ACCA hook service" $ApiPort "http://127.0.0.1:$ApiPort"
    Show-ProcessForPort "Alexandria Simple web server" $WebPort "http://127.0.0.1:$WebPort/alexandria_simple/index.html"
}

function Show-Logs {
    Write-Host "D-ACCA stdout: $ApiOut"
    if (Test-Path $ApiOut) { Get-Content $ApiOut -Tail 80 }
    Write-Host ""
    Write-Host "D-ACCA stderr: $ApiErr"
    if (Test-Path $ApiErr) { Get-Content $ApiErr -Tail 120 }
    Write-Host ""
    Write-Host "Web stdout: $WebOut"
    if (Test-Path $WebOut) { Get-Content $WebOut -Tail 80 }
    Write-Host ""
    Write-Host "Web stderr: $WebErr"
    if (Test-Path $WebErr) { Get-Content $WebErr -Tail 120 }
}

switch ($Command) {
    "start" { Start-AlexandriaSimple }
    "stop" { Stop-AlexandriaSimple }
    "restart" {
        Stop-AlexandriaSimple
        Start-Sleep -Milliseconds 500
        Start-AlexandriaSimple
    }
    "status" { Show-AlexandriaSimpleStatus }
    "logs" { Show-Logs }
    "foreground" {
        Write-Host "Serving Alexandria Simple from $Root on http://127.0.0.1:$WebPort"
        & $Python -m http.server $WebPort --bind 127.0.0.1 --directory $Root
    }
}
