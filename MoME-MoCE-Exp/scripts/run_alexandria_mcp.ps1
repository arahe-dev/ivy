param(
    [ValidateSet("setup", "start", "stop", "status", "tunnel", "ngrok", "stop-tunnel", "print-chatgpt", "codex-config")]
    [string]$Command = "start",
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$DataRoot = "C:\ivy-data\alexandria",
    [int]$HookPort = 8767,
    [int]$McpPort = 8790,
    [string]$Python = "",
    [switch]$LogPayloads
)

$ErrorActionPreference = "Stop"

function New-UrlToken {
    param([int]$Bytes = 32)
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($buffer)
    }
    finally {
        $rng.Dispose()
    }
    return [Convert]::ToBase64String($buffer).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Resolve-Python {
    if ($Python) {
        return $Python
    }
    $candidates = @(
        "C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe",
        (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
        "python"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -eq "python") {
            return $candidate
        }
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return "python"
}

function Test-PortOpen {
    param([int]$Port)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne(250, $false)) {
            return $false
        }
        $client.EndConnect($iar)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Get-FreeLoopbackPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), 0)
    try {
        $listener.Start()
        return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    }
    finally {
        $listener.Stop()
    }
}

function Get-HookHealthRoot {
    param([int]$Port)
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -Method Get -TimeoutSec 2
        return [string]$health.root
    }
    catch {
        return ""
    }
}

function Stop-PidFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }
    $pidText = (Get-Content -Path $Path -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($pidText -match "^\d+$") {
        $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $proc.Id -Force
        }
    }
    Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}

function Ensure-Layout {
    $paths = @(
        $DataRoot,
        (Join-Path $DataRoot "bin"),
        (Join-Path $DataRoot "engine"),
        (Join-Path $DataRoot "logs"),
        (Join-Path $DataRoot "pids"),
        (Join-Path $DataRoot "secrets"),
        (Join-Path $DataRoot "exports")
    )
    foreach ($path in $paths) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
}

function Resolve-Cloudflared {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $local = Join-Path $DataRoot "bin\cloudflared.exe"
    if (Test-Path $local) {
        return $local
    }
    return ""
}

function Resolve-Ngrok {
    $cmd = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $winget = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
    if (Test-Path $winget) {
        return $winget
    }
    $local = Join-Path $DataRoot "bin\ngrok.exe"
    if (Test-Path $local) {
        return $local
    }
    return ""
}

function Resolve-NgrokDefaultConfig {
    $candidates = @()
    if ($env:NGROK_CONFIG) {
        $candidates += $env:NGROK_CONFIG
    }
    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA "ngrok\ngrok.yml")
    }
    if ($env:USERPROFILE) {
        $candidates += (Join-Path $env:USERPROFILE ".ngrok2\ngrok.yml")
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return ""
}

function Get-SecretsPath {
    return (Join-Path $DataRoot "secrets\alexandria.secrets.json")
}

function Ensure-Secrets {
    Ensure-Layout
    $secretsPath = Get-SecretsPath
    if (-not (Test-Path $secretsPath)) {
        $secrets = [ordered]@{
            created_at = (Get-Date).ToUniversalTime().ToString("o")
            mcp_bearer_token = (New-UrlToken -Bytes 32)
            mcp_path_secret = (New-UrlToken -Bytes 24)
            mcp_oauth_owner_pin = (New-UrlToken -Bytes 12)
        }
        $secrets | ConvertTo-Json | Set-Content -Path $secretsPath -Encoding UTF8
    }
    else {
        $secrets = Get-Content -Path $secretsPath -Raw | ConvertFrom-Json
        if (-not ($secrets.PSObject.Properties.Name -contains "mcp_oauth_owner_pin")) {
            $secrets | Add-Member -NotePropertyName "mcp_oauth_owner_pin" -NotePropertyValue (New-UrlToken -Bytes 12)
            $secrets | ConvertTo-Json | Set-Content -Path $secretsPath -Encoding UTF8
        }
    }
    try {
        $acl = Get-Acl -Path $secretsPath
        $acl.SetAccessRuleProtection($true, $true)
        Set-Acl -Path $secretsPath -AclObject $acl
    }
    catch {
        Write-Warning "Could not harden secrets ACL in this shell; keeping the local user-owned secret file."
    }
    return (Get-Content -Path $secretsPath -Raw | ConvertFrom-Json)
}

function Start-Hooks {
    $engineRoot = Join-Path $DataRoot "engine"
    $pidPath = Join-Path $DataRoot "pids\hooks.pid"
    if (Test-PortOpen -Port $HookPort) {
        $liveRoot = Get-HookHealthRoot -Port $HookPort
        if ($liveRoot -and ((Resolve-Path -LiteralPath $liveRoot -ErrorAction SilentlyContinue).Path -eq (Resolve-Path -LiteralPath $engineRoot -ErrorAction SilentlyContinue).Path)) {
            Write-Host "D-ACCA hooks already listening on 127.0.0.1:$HookPort"
            return
        }
        throw "Port $HookPort is already in use by another service/root ($liveRoot). Choose -HookPort or stop that service."
        return
    }
    $pythonExe = Resolve-Python
    $stdout = Join-Path $DataRoot "logs\hooks.stdout.log"
    $stderr = Join-Path $DataRoot "logs\hooks.stderr.log"
    $args = @(
        "-m", "scripts.d_acca_dogfood_service",
        "serve",
        "--root", $engineRoot,
        "--host", "127.0.0.1",
        "--port", [string]$HookPort,
        "--candidate-backend", "indexed",
        "--top-k", "5"
    )
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $args -WorkingDirectory $RepoRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Set-Content -Path $pidPath -Value $proc.Id -Encoding ASCII
    Start-Sleep -Milliseconds 700
    if (-not (Test-PortOpen -Port $HookPort)) {
        throw "D-ACCA hooks did not start. Check $stderr"
    }
    Write-Host "Started D-ACCA hooks on 127.0.0.1:$HookPort"
}

function Start-Mcp {
    $secretsPath = Get-SecretsPath
    $pidPath = Join-Path $DataRoot "pids\mcp.pid"
    if (Test-PortOpen -Port $McpPort) {
        Write-Host "Alexandria MCP already listening on 127.0.0.1:$McpPort"
        return
    }
    $pythonExe = Resolve-Python
    $stdout = Join-Path $DataRoot "logs\mcp.stdout.log"
    $stderr = Join-Path $DataRoot "logs\mcp.stderr.log"
    $audit = Join-Path $DataRoot "logs\mcp_audit.jsonl"
    $args = @(
        "-m", "scripts.alexandria_mcp_server",
        "--host", "127.0.0.1",
        "--port", [string]$McpPort,
        "--engine-base-url", "http://127.0.0.1:$HookPort",
        "--secrets-file", $secretsPath,
        "--audit-log", $audit,
        "--oauth-enabled",
        "--require-oauth-for-tools"
    )
    if ($LogPayloads) {
        $args += "--log-payloads"
    }
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $args -WorkingDirectory $RepoRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Set-Content -Path $pidPath -Value $proc.Id -Encoding ASCII
    Start-Sleep -Milliseconds 700
    if (-not (Test-PortOpen -Port $McpPort)) {
        throw "Alexandria MCP did not start. Check $stderr"
    }
    Write-Host "Started Alexandria MCP on 127.0.0.1:$McpPort"
}

function Start-QuickTunnel {
    Ensure-Secrets | Out-Null
    $cloudflared = Resolve-Cloudflared
    if (-not $cloudflared) {
        throw "cloudflared is not on PATH or $DataRoot\bin. Install it with: winget install --id Cloudflare.cloudflared"
    }
    if (-not (Test-PortOpen -Port $McpPort)) {
        Start-Hooks
        Start-Mcp
    }
    $pidPath = Join-Path $DataRoot "pids\cloudflared.pid"
    $stdout = Join-Path $DataRoot "logs\cloudflared.stdout.log"
    $stderr = Join-Path $DataRoot "logs\cloudflared.stderr.log"
    Stop-PidFile -Path $pidPath
    $proc = Start-Process -FilePath $cloudflared -ArgumentList @("tunnel", "--protocol", "http2", "--edge-ip-version", "4", "--url", "http://127.0.0.1:$McpPort", "--no-autoupdate") -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Set-Content -Path $pidPath -Value $proc.Id -Encoding ASCII
    $url = ""
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        $combined = ""
        if (Test-Path $stdout) {
            $combined += Get-Content -Path $stdout -Raw -ErrorAction SilentlyContinue
        }
        if (Test-Path $stderr) {
            $combined += Get-Content -Path $stderr -Raw -ErrorAction SilentlyContinue
        }
        $match = [regex]::Match($combined, "https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        if ($match.Success) {
            $url = $match.Value
            break
        }
    }
    if (-not $url) {
        throw "Could not find Cloudflare quick tunnel URL. Check $stderr"
    }
    $secrets = Ensure-Secrets
    $chatgptUrl = "$url/mcp/$($secrets.mcp_path_secret)"
    Set-Content -Path (Join-Path $DataRoot "chatgpt_mcp_url.txt") -Value $chatgptUrl -Encoding UTF8
    Write-Host "ChatGPT MCP URL written to $DataRoot\chatgpt_mcp_url.txt"
}

function Start-NgrokTunnel {
    Ensure-Secrets | Out-Null
    $ngrok = Resolve-Ngrok
    if (-not $ngrok) {
        throw "ngrok is not on PATH or in the expected winget/data-root locations. Install it with: winget install --id Ngrok.Ngrok"
    }
    if (-not (Test-PortOpen -Port $McpPort)) {
        Start-Hooks
        Start-Mcp
    }
    Stop-PidFile -Path (Join-Path $DataRoot "pids\cloudflared.pid")
    $pidPath = Join-Path $DataRoot "pids\ngrok.pid"
    $stdout = Join-Path $DataRoot "logs\ngrok.stdout.log"
    $stderr = Join-Path $DataRoot "logs\ngrok.stderr.log"
    Stop-PidFile -Path $pidPath
    Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue
    $apiPort = Get-FreeLoopbackPort
    Set-Content -Path (Join-Path $DataRoot "pids\ngrok_api_port.txt") -Value $apiPort -Encoding ASCII
    $target = "http://127.0.0.1:$McpPort"
    $ngrokConfig = Join-Path $DataRoot "pids\ngrok_alexandria.yml"
    @"
version: 3
agent:
  web_addr: 127.0.0.1:$apiPort
"@ | Set-Content -Path $ngrokConfig -Encoding ASCII
    $ngrokArgs = @()
    $defaultConfig = Resolve-NgrokDefaultConfig
    if ($defaultConfig) {
        $ngrokArgs += @("--config", $defaultConfig)
    }
    $ngrokArgs += @("--config", $ngrokConfig, "http", $target, "--log", "stdout", "--log-format", "json")
    $proc = Start-Process -FilePath $ngrok -ArgumentList $ngrokArgs -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Set-Content -Path $pidPath -Value $proc.Id -Encoding ASCII
    $url = ""
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        if ($proc.HasExited) {
            break
        }
        try {
            $api = Invoke-RestMethod -Uri "http://127.0.0.1:$apiPort/api/tunnels" -Method Get -TimeoutSec 2
            $https = @($api.tunnels | Where-Object { $_.public_url -like "https://*" -and [string]$_.config.addr -eq $target } | Select-Object -First 1)
            if ($https) {
                $url = [string]$https.public_url
                break
            }
        }
        catch {
        }
    }
    if (-not $url) {
        throw "Could not find ngrok HTTPS URL. Check $stderr"
    }
    $secrets = Ensure-Secrets
    $chatgptUrl = "$url/mcp/$($secrets.mcp_path_secret)"
    Set-Content -Path (Join-Path $DataRoot "chatgpt_mcp_url.txt") -Value $chatgptUrl -Encoding UTF8
    [Environment]::SetEnvironmentVariable("ALEXANDRIA_CHATGPT_MCP_URL", $chatgptUrl, "User")
    $env:ALEXANDRIA_CHATGPT_MCP_URL = $chatgptUrl
    Write-Host "ChatGPT MCP URL written to $DataRoot\chatgpt_mcp_url.txt"
}

function Configure-Codex {
    $secrets = Ensure-Secrets
    [Environment]::SetEnvironmentVariable("ALEXANDRIA_MCP_TOKEN", [string]$secrets.mcp_bearer_token, "User")
    [Environment]::SetEnvironmentVariable("ALEXANDRIA_MCP_OAUTH_PIN", [string]$secrets.mcp_oauth_owner_pin, "User")
    $env:ALEXANDRIA_MCP_TOKEN = [string]$secrets.mcp_bearer_token
    $env:ALEXANDRIA_MCP_OAUTH_PIN = [string]$secrets.mcp_oauth_owner_pin
    Write-Host "Set user env vars ALEXANDRIA_MCP_TOKEN and ALEXANDRIA_MCP_OAUTH_PIN. Restart Codex to inherit them."
}

function Print-Status {
    $hooks = Test-PortOpen -Port $HookPort
    $mcp = Test-PortOpen -Port $McpPort
    Write-Host "Data root: $DataRoot"
    Write-Host "Hooks 127.0.0.1:$HookPort running: $hooks"
    Write-Host "MCP   127.0.0.1:$McpPort running: $mcp"
    $chatgptPath = Join-Path $DataRoot "chatgpt_mcp_url.txt"
    if (Test-Path $chatgptPath) {
        Write-Host "ChatGPT MCP URL file: $chatgptPath"
    }
}

Ensure-Layout

switch ($Command) {
    "setup" {
        Ensure-Secrets | Out-Null
        Configure-Codex
        Write-Host "Alexandria layout ready under $DataRoot"
    }
    "start" {
        Ensure-Secrets | Out-Null
        Start-Hooks
        Start-Mcp
        Print-Status
    }
    "stop" {
        Stop-PidFile -Path (Join-Path $DataRoot "pids\mcp.pid")
        Stop-PidFile -Path (Join-Path $DataRoot "pids\hooks.pid")
        Print-Status
    }
    "status" {
        Print-Status
    }
    "tunnel" {
        Start-QuickTunnel
        Print-Status
    }
    "ngrok" {
        Start-NgrokTunnel
        Print-Status
    }
    "stop-tunnel" {
        Stop-PidFile -Path (Join-Path $DataRoot "pids\cloudflared.pid")
        Stop-PidFile -Path (Join-Path $DataRoot "pids\ngrok.pid")
        Remove-Item -LiteralPath (Join-Path $DataRoot "pids\ngrok_api_port.txt") -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $DataRoot "pids\ngrok_alexandria.yml") -Force -ErrorAction SilentlyContinue
        Print-Status
    }
    "print-chatgpt" {
        $path = Join-Path $DataRoot "chatgpt_mcp_url.txt"
        if (-not (Test-Path $path)) {
            throw "No ChatGPT MCP URL yet. Run: .\alexandria-mcp.cmd tunnel"
        }
        Get-Content -Path $path
    }
    "codex-config" {
        Configure-Codex
    }
}
