# IVY Reporting Autoresearch Report

## Best Mutation Found
**Enhanced report_suite.ps1** with pass/warn/fail classification and automatic recommendations.

## Before/After Comparison

### Before
```
| case | prompt_n | predicted_n | ttft_est_ms | wall_ms | decode_tps | coherent |
|---|---:|---:|---:|---:|---:|---|
| short | 734 | 160 | 1313 | 4407 | 51.7 | True |
```

### After
```
| case | status | prompt_n | predicted_n | ttft_est_ms | wall_ms | decode_tps | coherent |
|---|:------:|---:|---:|---:|---:|---:|:------:|
| short | ✓ PASS | 734 | 160 | 1313 | 4407 | 51.7 | True |

## Context scaling (short vs): medium 3.0x, long 7.7x
## Decode stability: stable (avg: 51.4, min: 50.1)
## TTFT: 5095ms average
## Overall: **PASS**
## Recommendation
## BASELINE STABLE
```

## Fields Added
- **status**: PASS/WARN/FAIL per case (✓PASS, ⚠WARN, ✗FAIL)
- **Context scaling**: short vs medium/long multiplier
- **Decode stability**: stable/degraded classification
- **TTFT average**: across all cases
- **Overall**: PASS/WARN/FAIL aggregate
- **Recommendation**: Actionable next step

## Example Recommendations
- `BASELINE STABLE` - Ready for experiments
- `BASELINE UNSTABLE` - Monitor decode performance  
- `PREFILL BOTTLENECK` - Consider prompt packing
- `DECODE REGRESSION` - Retry or rollback
- `INVALID ARTIFACTS` - Check case outputs
- `NEEDS RERUN` - Check artifacts

## Thresholds Used
| Case | TTFT WARN | TTFT FAIL | Decode WARN | Decode FAIL |
|------|----------|----------|------------|-------------|
| short | 1500ms | 3000ms | 48 tok/s | 45 tok/s |
| medium | 5000ms | 8000ms | 48 tok/s | 45 tok/s |
| long | 12000ms | 20000ms | 48 tok/s | 45 tok/s |

## Files Changed
- `ivy/scripts/report_suite.ps1` - Enhanced with status classification

## Usage
```powershell
# Generate report with recommendations
.\report_suite.ps1 -SuiteRunDir "runs\suites\qwen35_context_envelope"

# Or specify result path
.\report_suite.ps1 -SuiteResultPath "suite_result.json" -AddRecommendations
```

## What Future Experiments Can Now Rely On
1. Automatic PASS/WARN/FAIL classification without manual review
2. Context scaling insight shows bottleneck location
3. Actionable recommendation for next step
4. Decode stability check before running experiments
5. Easy comparison across suite runs via consistent format

## Validation
- Tested on 2 existing suite results: PASS
- Context scaling: 3.0x (medium), 7.7x (long) - matches expectations
- Recommendation: BASELINE STABLE - matches manual review