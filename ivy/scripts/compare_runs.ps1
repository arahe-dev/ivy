param(
  [Parameter(Mandatory = $true)]
  [string]$BaselineRunDir,

  [Parameter(Mandatory = $true)]
  [string]$ExperimentRunDir
)

$ErrorActionPreference = "Stop"

function Read-Result {
  param([string]$RunDir)

  $path = Join-Path $RunDir "result.json"
  if (-not (Test-Path -LiteralPath $path)) {
    throw "result.json not found in run dir: $RunDir"
  }

  return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
}

$baseline = Read-Result -RunDir $BaselineRunDir
$experiment = Read-Result -RunDir $ExperimentRunDir

$bw = [double]$baseline.metrics.wall_ms
$ew = [double]$experiment.metrics.wall_ms
$bt = [double]$baseline.metrics.ttft_est_ms
$et = [double]$experiment.metrics.ttft_est_ms
$bd = [double]$baseline.metrics.decode_tps
$ed = [double]$experiment.metrics.decode_tps

$wallDelta = [math]::Round($ew - $bw, 3)
$ttftDelta = [math]::Round($et - $bt, 3)
$decodeDelta = [math]::Round($ed - $bd, 3)

$baselineCoherent = [bool]$baseline.metrics.coherent
$experimentCoherent = [bool]$experiment.metrics.coherent

$recommendation = if ($experimentCoherent -and $wallDelta -lt 0) {
  "Experiment run is preferred (lower wall_ms, coherent output)."
} else {
  "Keep baseline run as preferred reference."
}

$summary = [ordered]@{
  baseline_run_id = [string]$baseline.run_id
  experiment_run_id = [string]$experiment.run_id
  baseline_wall_ms = [math]::Round($bw, 3)
  experiment_wall_ms = [math]::Round($ew, 3)
  wall_ms_delta = $wallDelta
  baseline_ttft_est_ms = [math]::Round($bt, 3)
  experiment_ttft_est_ms = [math]::Round($et, 3)
  ttft_est_ms_delta = $ttftDelta
  baseline_decode_tps = [math]::Round($bd, 3)
  experiment_decode_tps = [math]::Round($ed, 3)
  decode_tps_delta = $decodeDelta
  baseline_coherent = $baselineCoherent
  experiment_coherent = $experimentCoherent
  baseline_cpu_mapped_model_buffer = $baseline.metrics.cpu_mapped_model_buffer
  experiment_cpu_mapped_model_buffer = $experiment.metrics.cpu_mapped_model_buffer
  baseline_cuda_model_buffer = $baseline.metrics.cuda_model_buffer
  experiment_cuda_model_buffer = $experiment.metrics.cuda_model_buffer
  recommendation = $recommendation
}

$summary | ConvertTo-Json -Depth 5

