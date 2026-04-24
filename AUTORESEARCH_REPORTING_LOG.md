# IVY Reporting Autoresearch Log

## Iteration 1: Inspect Current Reports

### Current State
- Basic table with metrics only
- No pass/warn/fail classification
- No recommendations
- No context scaling insight

## Iteration 2: Propose Improvements

### Proposed Features
1. **Status column**: PASS/WARN/FAIL per case based on thresholds
2. **TTFT thresholds**: short (1500/3000), medium (5000/8000), long (12000/20000)
3. **Decode stability**: min > 48 stable, min > 45 acceptable
4. **Context scaling**: short vs medium/long ratios
5. **Recommendation line**: BASELINE STABLE, PREFILL BOTTLENECK, DECODE REGRESSION, etc.

## Iteration 3: Implement Enhanced Report

### Script Changes
- Added `Get-Status()` function with PASS/WARN/FAIL logic
- Added `Get-Recommendation()` function for actionable advice
- Added Summary section with context scaling
- Added Recommendation section

## Iteration 4: Validate Against Suite Results

### Test Runs
```powershell
# Run 1: 20260425_023951
.\report_suite.ps1 -SuiteResultPath suite_result.json -AddRecommendations

# Run 2: 20260425_021725  
.\report_suite.ps1 -SuiteResultPath suite_result.json -AddRecommendations
```

### Results Validation
- Both suites correctly classified as PASS
- Context scaling shows 3.0x medium, 7.7x long
- Decode stability correctly identified as stable
- Recommendations properly generated

## Summary

| Feature | Before | After |
|---------|--------|-------|
| Status per case | none | PASS/WARN/FAIL |
| Context scaling | none | 3.0x / 7.7x |
| Decode stability | none | stable/degraded |
| Recommendation | none | BASELINE STABLE |
| TTFT average | none | 5095ms |