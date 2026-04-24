param(
  [string]$SuiteRunDir,
  [string]$SuiteResultPath
)

$ErrorActionPreference = "Stop"

if (-not $SuiteResultPath) {
  if (-not $SuiteRunDir) { throw "Provide -SuiteRunDir or -SuiteResultPath." }
  $SuiteResultPath = Join-Path $SuiteRunDir "suite_result.json"
}

if (-not (Test-Path -LiteralPath $SuiteResultPath)) {
  throw "suite_result.json not found: $SuiteResultPath"
}

$suite = Get-Content -LiteralPath $SuiteResultPath -Raw | ConvertFrom-Json
$suiteDir = if ($SuiteRunDir) { $SuiteRunDir } else { Split-Path -Parent $SuiteResultPath }

function Get-ValueOrBlank {
  param($Value)
  if ($null -eq $Value) { return "" }
  return [string]$Value
}

$lines = @()
$lines += "# Suite Report: $($suite.suite_name)"
$lines += ""
$lines += ("- ``suite_id``: {0}" -f $suite.suite_id)
$lines += ("- ``manifest``: {0}" -f $suite.manifest_path)
$lines += ("- ``model``: {0}" -f $suite.baseline.model)
$lines += ("- ``runtime``: {0}" -f $suite.baseline.runtime)
$lines += ""
$lines += "| case | prompt_n | predicted_n | ttft_est_ms | wall_ms | decode_tps | coherent | cpu_mapped_model_buffer | cuda_model_buffer | seq_rm_capability | kv_policy_status |"
$lines += "|---|---:|---:|---:|---:|---:|---|---|---|---|---|"

foreach ($case in $suite.cases) {
  if (-not (Test-Path -LiteralPath $case.result_json)) {
    throw "Missing result.json for case '$($case.id)': $($case.result_json)"
  }

  $result = Get-Content -LiteralPath $case.result_json -Raw | ConvertFrom-Json
  $m = $result.metrics
  $kv = $result.kv
  $lines += "| $($case.id) | $($m.prompt_n) | $($m.predicted_n) | $($m.ttft_est_ms) | $($m.wall_ms) | $($m.decode_tps) | $($m.coherent) | $(Get-ValueOrBlank $m.cpu_mapped_model_buffer) | $(Get-ValueOrBlank $m.cuda_model_buffer) | $(Get-ValueOrBlank $kv.seq_rm_capability) | $(Get-ValueOrBlank $kv.kv_policy_status) |"
}

$lines += ""
$lines += "## Child Runs"
$lines += ""
foreach ($case in $suite.cases) {
  $lines += ("- ``{0}``: ``{1}``" -f $case.id, $case.run_dir)
}

$reportPath = Join-Path $suiteDir "report.md"
$lines | Set-Content -Path $reportPath
Write-Output $reportPath
