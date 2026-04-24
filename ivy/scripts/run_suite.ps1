param(
  [string]$ManifestPath = "C:\ivy\ivy\manifests\suites\qwen35_context_envelope.yaml"
)

$ErrorActionPreference = "Stop"

function New-RunId {
  (Get-Date).ToString("yyyyMMdd_HHmmss")
}

function Parse-Scalar {
  param([string]$Text)

  $v = $Text.Trim()
  if ($v.StartsWith("'") -and $v.EndsWith("'")) { return $v.Substring(1, $v.Length - 2) }
  if ($v.StartsWith('"') -and $v.EndsWith('"')) { return $v.Substring(1, $v.Length - 2) }
  if ($v -eq "true") { return $true }
  if ($v -eq "false") { return $false }
  if ($v -match '^-?\d+$') { return [int]$v }
  if ($v -match '^-?\d+\.\d+$') { return [double]$v }
  return $v
}

function Read-SimpleYaml {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Suite manifest not found: $Path"
  }

  $root = @{}
  $section = $null
  foreach ($line in (Get-Content -LiteralPath $Path)) {
    if ($line -match '^\s*$') { continue }
    if ($line -match '^\s*#') { continue }

    if ($line -match '^([A-Za-z0-9_]+):\s*$') {
      $section = $Matches[1]
      if (-not $root.ContainsKey($section)) { $root[$section] = @{} }
      continue
    }

    if ($line -match '^  ([A-Za-z0-9_]+):\s*(.*)$') {
      if (-not $section) { continue }
      $root[$section][$Matches[1]] = Parse-Scalar $Matches[2]
      continue
    }

    if ($line -match '^([A-Za-z0-9_]+):\s*(.*)$') {
      $root[$Matches[1]] = Parse-Scalar $Matches[2]
    }
  }

  return $root
}

function Get-MapValueOrDefault {
  param(
    [hashtable]$Map,
    [string]$Key,
    $DefaultValue
  )
  if ($Map -and $Map.ContainsKey($Key)) { return $Map[$Key] }
  return $DefaultValue
}

function Get-SuiteCases {
  param([hashtable]$Manifest)

  $cases = @()
  foreach ($key in ($Manifest.Keys | Sort-Object)) {
    if ($key -notmatch '^case_') { continue }
    $case = [hashtable]$Manifest[$key]
    $id = $key.Substring(5)
    $cases += [PSCustomObject]@{
      Id = $id
      Order = [int](Get-MapValueOrDefault -Map $case -Key "order" -DefaultValue 999)
      Label = [string](Get-MapValueOrDefault -Map $case -Key "label" -DefaultValue $id)
      PromptFile = [string](Get-MapValueOrDefault -Map $case -Key "prompt_file" -DefaultValue "")
    }
  }
  return ($cases | Sort-Object Order, Id)
}

function Invoke-ExperimentCase {
  param(
    [string]$ExperimentRunner,
    [string]$ExperimentName,
    [string]$CaseRunRoot,
    [string]$ModelPath,
    [string]$RuntimePath,
    [string]$PromptFile,
    [hashtable]$Server,
    [hashtable]$Generation,
    [int]$Port
  )

  $output = & $ExperimentRunner `
    -ExperimentName $ExperimentName `
    -RunRoot $CaseRunRoot `
    -ModelPath $ModelPath `
    -RuntimePath $RuntimePath `
    -PromptFile $PromptFile `
    -HostAddr ([string](Get-MapValueOrDefault -Map $Server -Key "host" -DefaultValue "127.0.0.1")) `
    -Port $Port `
    -NParallel ([int](Get-MapValueOrDefault -Map $Server -Key "n_parallel" -DefaultValue 1)) `
    -CtxSize ([int](Get-MapValueOrDefault -Map $Server -Key "ctx_size" -DefaultValue 8192)) `
    -Threads ([int](Get-MapValueOrDefault -Map $Server -Key "threads" -DefaultValue 14)) `
    -ThreadsBatch ([int](Get-MapValueOrDefault -Map $Server -Key "threads_batch" -DefaultValue 14)) `
    -FlashAttn ([string](Get-MapValueOrDefault -Map $Server -Key "flash_attn" -DefaultValue "on")) `
    -NGpuLayers ([int](Get-MapValueOrDefault -Map $Server -Key "n_gpu_layers" -DefaultValue 99)) `
    -NCpuMoe ([int](Get-MapValueOrDefault -Map $Server -Key "n_cpu_moe" -DefaultValue 16)) `
    -NoWebui ([bool](Get-MapValueOrDefault -Map $Server -Key "no_webui" -DefaultValue $true)) `
    -Seed ([int](Get-MapValueOrDefault -Map $Generation -Key "seed" -DefaultValue 12345)) `
    -Temperature ([double](Get-MapValueOrDefault -Map $Generation -Key "temperature" -DefaultValue 0.0)) `
    -TopK ([int](Get-MapValueOrDefault -Map $Generation -Key "top_k" -DefaultValue 1)) `
    -TopP ([double](Get-MapValueOrDefault -Map $Generation -Key "top_p" -DefaultValue 1.0)) `
    -MinP ([double](Get-MapValueOrDefault -Map $Generation -Key "min_p" -DefaultValue 0.0)) `
    -RepeatPenalty ([double](Get-MapValueOrDefault -Map $Generation -Key "repeat_penalty" -DefaultValue 1.0)) `
    -NPredict ([int](Get-MapValueOrDefault -Map $Generation -Key "n_predict" -DefaultValue 160)) `
    -CachePrompt ([bool](Get-MapValueOrDefault -Map $Generation -Key "cache_prompt" -DefaultValue $true))

  return [string]($output | Select-Object -Last 1)
}

$manifest = Read-SimpleYaml -Path $ManifestPath
$paths = [hashtable](Get-MapValueOrDefault -Map $manifest -Key "paths" -DefaultValue @{})
$server = [hashtable](Get-MapValueOrDefault -Map $manifest -Key "server" -DefaultValue @{})
$generation = [hashtable](Get-MapValueOrDefault -Map $manifest -Key "generation" -DefaultValue @{})
$output = [hashtable](Get-MapValueOrDefault -Map $manifest -Key "output" -DefaultValue @{})

$suiteName = [string](Get-MapValueOrDefault -Map $manifest -Key "name" -DefaultValue "suite")
$suiteId = New-RunId
$suiteRoot = [string](Get-MapValueOrDefault -Map $output -Key "suite_root" -DefaultValue "C:\ivy\ivy\runs\suites")
$suiteDir = Join-Path $suiteRoot ("{0}\{1}" -f $suiteName, $suiteId)
$caseRunRoot = Join-Path $suiteDir "runs"
New-Item -ItemType Directory -Force -Path $caseRunRoot | Out-Null

$modelPath = [string](Get-MapValueOrDefault -Map $paths -Key "model" -DefaultValue "")
$runtimePath = [string](Get-MapValueOrDefault -Map $paths -Key "runtime" -DefaultValue "")
$experimentRunner = [string](Get-MapValueOrDefault -Map $paths -Key "experiment_runner" -DefaultValue "C:\ivy\ivy\scripts\run_experiment.ps1")

foreach ($required in @($modelPath, $runtimePath, $experimentRunner)) {
  if (-not (Test-Path -LiteralPath $required)) { throw "Required path does not exist: $required" }
}

$cases = Get-SuiteCases -Manifest $manifest
if ($cases.Count -eq 0) { throw "No case_* sections found in suite manifest: $ManifestPath" }

$basePort = [int](Get-MapValueOrDefault -Map $server -Key "port" -DefaultValue 8121)
$caseResults = @()
$caseIndex = 0

foreach ($case in $cases) {
  if (-not (Test-Path -LiteralPath $case.PromptFile)) {
    throw "Prompt file not found for case '$($case.Id)': $($case.PromptFile)"
  }

  $port = $basePort + $caseIndex
  Write-Host ("[{0}] running suite case {1} on port {2}" -f (Get-Date).ToString("s"), $case.Id, $port)

  $childRunDir = Invoke-ExperimentCase `
    -ExperimentRunner $experimentRunner `
    -ExperimentName $case.Id `
    -CaseRunRoot $caseRunRoot `
    -ModelPath $modelPath `
    -RuntimePath $runtimePath `
    -PromptFile $case.PromptFile `
    -Server $server `
    -Generation $generation `
    -Port $port

  $caseResults += [ordered]@{
    id = $case.Id
    order = $case.Order
    label = $case.Label
    prompt_file = $case.PromptFile
    port = $port
    run_dir = $childRunDir
    result_json = (Join-Path $childRunDir "result.json")
  }
  $caseIndex++
}

$suiteResult = [ordered]@{
  suite_id = $suiteId
  suite_name = $suiteName
  timestamp_local = (Get-Date).ToString("s")
  manifest_path = (Resolve-Path -LiteralPath $ManifestPath).Path
  suite_dir = $suiteDir
  baseline = [ordered]@{
    model = $modelPath
    runtime = $runtimePath
    flags = [ordered]@{
      n_gpu_layers = [int](Get-MapValueOrDefault -Map $server -Key "n_gpu_layers" -DefaultValue 99)
      n_cpu_moe = [int](Get-MapValueOrDefault -Map $server -Key "n_cpu_moe" -DefaultValue 16)
      flash_attn = [string](Get-MapValueOrDefault -Map $server -Key "flash_attn" -DefaultValue "on")
      threads = [int](Get-MapValueOrDefault -Map $server -Key "threads" -DefaultValue 14)
      threads_batch = [int](Get-MapValueOrDefault -Map $server -Key "threads_batch" -DefaultValue 14)
      ctx_size = [int](Get-MapValueOrDefault -Map $server -Key "ctx_size" -DefaultValue 8192)
    }
    generation = $generation
  }
  cases = $caseResults
}

$suiteResultPath = Join-Path $suiteDir "suite_result.json"
$suiteResult | ConvertTo-Json -Depth 10 | Set-Content -Path $suiteResultPath
Write-Output $suiteDir
