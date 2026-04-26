param(
    [string]$ManifestPath = "C:\ivy\ivy\manifests\q4km_hot_agent.yaml",
    [string]$RunsRoot = "C:\ivy\runs\phase1_agent_demo_ui",
    [string]$SandboxRoot = "C:\ivy\ivy_agent_demo\sandbox_workspace",
    [int]$Port = 8787,
    [int]$SlotId = 0,
    [int]$RequestTimeoutSec = 180
)

$ErrorActionPreference = "Stop"

python -m ivy_agent_demo.ui_server `
  --manifest $ManifestPath `
  --runs-root $RunsRoot `
  --sandbox-root $SandboxRoot `
  --host 127.0.0.1 `
  --port $Port `
  --slot-id $SlotId `
  --request-timeout-sec $RequestTimeoutSec
