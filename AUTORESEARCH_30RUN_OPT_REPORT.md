# AUTORESEARCH_30RUN_OPT_REPORT.md - FINAL (REVISED)

## CRITICAL FINDING: V7.1 OVERFIT

### Decision: KEEP V7 (V7.1 is over-compressed)

The V7.1 ultra-compact format fails held-out validation due to over-compression. Quality issues detected:
- Policy task: Output gibberish (repeated prompt content, no analysis)
- Reason task: Treated input as word puzzle rather than answering comparison question
- Abbreviation ambiguity: critical context lost

---

## Full Comparison Table

| Metric | Original | V7 | V7.1 | vs V7 | Notes |
|--------|----------|-----|------|-------|-------|
| **avg prompt_n** | ~316 | ~132 | **~54** | -59% vs V7 |
| **avg TTFT** | ~699ms | ~510ms | **~400ms** | -22% vs V7 |
| **avg wall_ms** | ~3676ms | ~3500ms | **~3350ms** | -4% vs V7 |
| **avg decode_tps** | ~53 | ~53 | ~54 | stable |
| **avg predicted_n** | 160 | 160 | 160 | stable |
| **quality pass rate** | 5/5 | 5/5 | **2/5** | FAIL |

### Metrics Analysis
- TTFT: V7.1 improves 22% over V7 (meets 8% threshold)
- wall_ms: V7.1 improves 4% over V7 (meets no regression)
- decode_tps: stable (meets 5% threshold)
- **BUT: quality fails** - Only 2/5 held-out tasks pass

---

## Held-Out Validation Results

### Task 1: Policy (Backup Change Request)

| Format | prompt_n | TTFT | wall | Output Quality |
|-------|----------|------|------|------------|
| V7 | 120 | 529ms | 3537ms | Coherent, answers question |
| V7.1 | 71 | 454ms | 3457ms | **FAIL** - Output repeats prompt |

**V7.1 Failure**: Output was gibberish showing repeated prompt content like `|20260426|compliant?3FIND+2RISK|20260426|compliant?3FIND+2RISK` - no analysis provided

### Task 2: Troubleshooting (API Outage)

| Format | prompt_n | TTFT | wall | Output Quality |
|-------|----------|------|------|------------|
| V7 | 147 | 535ms | 3575ms | Coherent RCA |
| V7.1 | 83 | 440ms | 3480ms | Coherent but simpler |

**V7.1 PASS**: Still produces usable output

### Task 3: Reasoning (Auth vs Payment Comparison)

| Format | prompt_n | TTFT | wall | Output Quality |
|-------|----------|------|------|------------|
| V7 | 80 | 475ms | 3527ms | Correctly answers comparison |
| V7.1 | 33 | 363ms | **FAIL** - Treats as word puzzle |

**V7.1 Failure**: Output starts with "Based on the structure of the input, this appears to be a **word puzzle**" - completely misunderstanding the task

---

## Quality Detailed Analysis

### Held-Out Task Quality Breakdown

| Task | Required Facts | V7 Preserves | V7.1 Preserves | V7.1 Issues |
|------|---------------|--------------|---------------|--------------|
| policy | 3 findings + 2 risks | ✓ 5/5 | X 0/5 | Output repeats prompt |
| troubleshoot | root cause analysis | ✓ 5/5 | ✓ 5/5 | OK but simpler |
| reason | comparison logic | ✓ 5/5 | X 1/5 | Misreads as puzzle |

### Abbreviation Ambiguity Issues in V7.1
- `CMPAUTHpaysvc` → Model sees as "company" + "auth" + "pay service" confusion
- `INST` vs `IN-PLACE` → Lost in compression
- `LOGINvsDATA` → Model treats as word puzzle clue

---

## Final Decision

### KEEP V7 FORMAT

V7.1 is **OVERFIT** - too compressed for general use.

**V7.1 rejected because:**
1. Quality failed on 2/3 held-out tasks
2. Output unusable on policy task (gibberish)
3. Reasoning task completely misinterpreted
4. Abbreviation compression loses critical context

**V7 remains the Adopted Stack** with:
- prompt_n: ~132 (acceptable)
- TTFT: ~510ms (21% improvement over original)
- wall_ms: ~3500ms (5% improvement over original)
- Quality: 100% (pass on all tasks)

---

## What Was Learned

1. **Compression ceiling exists**: Beyond ~50 chars, quality degrades
2. Delimiters matter: `|` provide parseability that model relies on
3. Task type sensitivity: Reasoning tasks most vulnerable to compression
4. Held-out validation essential: Search tasks were too similar

---

## Updated Metrics Table (Final)

| Metric | Original | V7 (ADOPTED) | vs Original |
|--------|----------|--------------|------------|
| prompt_n | 316 | **132** | **-58%** |
| TTFT | 699ms | **510ms** | **-27%** |
| wall_ms | 3676ms | **3500ms** | **-5%** |
| decode_tps | ~53 | ~53 | stable |
| quality pass | 100% | **100%** | ✓ |