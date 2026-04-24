# COMBINED_POSITIVES_REPORT.md

## IVY Best-Known Stack Validation

### Stack Components Validated

1. **Frozen MoE-aware runtime baseline**
   ```powershell
   --n-gpu-layers 99
   --n-cpu-moe 16
   --flash-attn on
   --threads 14
   --threads-batch 14
   --ctx-size 8192
   ```

2. **Prompt Packing v3 ultra-minimal format** (adopted from autoresearch)

3. **Enhanced suite reporting** with pass/warn/fail classification

4. **Existing manifest/run/report pipeline**

### NOT Included in Stack
- prefix/cache reuse (no measurable TTFT win)
- output packing (quality failures)
- runtime flag tuning
- llama.cpp changes

---

## Before/After Table Per Task

| Task | Baseline prompt_n | Packed prompt_n | Baseline TTFT | Packed TTFT | Baseline wall | Packed wall |
|------|-----------------|---------------|---------------|--------------|-------------|-------------|------------|
| policy | 251 | 181 | 702ms | 617ms | 3699ms | 3628ms |
| troubleshoot | 291 | 200 | 659ms | 594ms | 3634ms | 3566ms |
| extraction | 496 | 279 | 818ms | 658ms | 3843ms | 3635ms |
| support | 253 | 150 | 663ms | 566ms | 3590ms | 3781ms |
| architecture | 291 | 169 | 654ms | 577ms | 3616ms | 3639ms |

---

## Aggregate Results

### Average Metrics

| Metric | Baseline (Ultra V1) | Best-Known Stack (V3) | Improvement |
|--------|------------------|---------------------|-------------|
| **prompt_n** | 316.4 | 195.8 | **-38.1%** |
| **TTFT** | 699.1ms | 602.2ms | **-13.9%** |
| **wall_ms** | 3676.4ms | 3649.8ms | -0.7% |
| decode_tps | ~53 | ~53 | stable |

### Key Findings
- **Prompt token reduction**: 38.1% (main gain)
- **TTFT improvement**: 13.9% (significant)
- **Wall improvement**: minimal (decode phase dominates)
- **Decode stability**: 53 tok/s maintained

---

## Quality Checklist

| Task | Output Length | Coherent | Required Format | Pass |
|------|--------------|----------|---------------|------|
| policy | 651 chars | ✓ | 5 bullets | ✓ |
| troubleshoot | 566 chars | ✓ | 6 bullets | ✓ |
| extraction | 385 chars | ✓ | 5 bullets | ✓ |
| support | 524 chars | ✓ | 4 bullets | ✓ |
| architecture | 553 chars | ✓ | 5 bullets | ✓ |

**Quality pass rate: 5/5 (100%)**

---

## Runtime Configuration

### Frozen Baseline Flags
```powershell
llama-server.exe \
  -m Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf \
  --host 127.0.0.1 --port 8121 \
  -np 1 --ctx-size 8192 \
  --no-webui \
  --threads 14 --threads-batch 14 \
  --n-gpu-layers 99 --n-cpu-moe 16 \
  --flash-attn on
```

### Generation Settings
```powershell
--seed 12345
--temperature 0.0
--top_k 1 --top_p 1.0
--repeat_penalty 1.0
--n_predict 160
--cache_prompt true
```

---

## Final Conclusion

### **ADOPT BEST-KNOWN STACK**

The Prompt Packing v3 + frozen MoE baseline combination is validated:
- **TTFT improved by 13.9%** (significant)
- **Prompt tokens reduced by 38.1%** (major gain)
- **Quality preserved** (5/5 pass)
- **Decode stable** (~53 tok/s)

---

## What Future Experiments Can Rely On

1. **Fixed runtime baseline** for all experiments
2. **Prompt Packing v3** as the standard prompt format
3. **Enhanced reporting** for pass/warn/fail classification
4. **Quality checklist** for validation
5. **TTFT as the key metric** (wall_ms dominated by decode)

---

## Files Part of Best-Known Stack

- `ivy/scripts/report_suite.ps1` - Enhanced reporting
- `ivy/docs/WORKLOAD_SUITE_SCHEMA.md` - Updated schema docs
- `ivy/validation_tasks/*_v3.txt` - Prompt Packing v3 prompts
- `AUTORESEARCH_*_REPORT.md` - Research logs
- `PROMPT_PACKING_VALIDATION.md` - Validation report
- `COMBINED_POSITIVES_REPORT.md` - This report

---

*Stack validation completed: 2026-04-25*
*Experiments used: 8 within 12 limit*
*Quality pass rate: 100%*