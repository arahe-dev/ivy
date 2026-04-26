param(
    [string]$ManifestPath = "C:\ivy\ivy\manifests\q4km_hot_agent.yaml",
    [string]$ScenariosPath = "C:\ivy\ivy_agent_demo\scenarios\scenarios.json",
    [string]$RunsRoot = "C:\ivy\runs\phase1_agent_demo",
    [string]$SandboxRoot = "C:\ivy\ivy_agent_demo\sandbox_workspace",
    [int]$SlotId = 0,
    [int]$RequestTimeoutSec = 180,
    [switch]$StopServerAfter
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "Manifest not found: $ManifestPath"
}
if (-not (Test-Path -LiteralPath $ScenariosPath)) {
    throw "Scenarios file not found: $ScenariosPath"
}
if (-not (Test-Path -LiteralPath $SandboxRoot)) {
    throw "Sandbox root not found: $SandboxRoot"
}

New-Item -ItemType Directory -Force -Path $RunsRoot | Out-Null

$argsList = @(
    "-m",
    "ivy_agent_demo.agent_loop",
    "--manifest", $ManifestPath,
    "--scenarios", $ScenariosPath,
    "--runs-root", $RunsRoot,
    "--sandbox-root", $SandboxRoot,
    "--slot-id", "$SlotId",
    "--request-timeout-sec", "$RequestTimeoutSec"
)

if ($StopServerAfter) {
    $argsList += "--stop-server-after"
}

Write-Host "Running IVY Phase 1 agent demo..."
Write-Host "Manifest: $ManifestPath"
Write-Host "Scenarios: $ScenariosPath"
Write-Host "Runs root: $RunsRoot"

python @argsList
