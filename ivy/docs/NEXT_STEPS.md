# IVY Next Steps

## Ready for Experimentation

### What Can Be Done Now

1. **Hot-Server Runner** (enables prefix/cache reuse testing)
   - Need: Sustained server connection across requests
   - Why: Current runner spawns fresh server each time

2. **Output Packing with Budget** (if llama.cpp adds support)
   - Current: No per-task token budget in server API
   - Need: Budget-aware output limits

## Not Allowed

- Do NOT modify llama.cpp
- Do NOT change frozen runtime flags
- Do NOT implement KV behavior in this repo

## Possible Future Work

### When Hot-Server Runner Exists

1. Test prefix/cache reuse with persistent connections
2. Measure cross-request cache effects
3. Validate cache benefits for similar prompts

### If llama.cpp Adds Budget Support

1. Re-visit output packing experiments
2. Test per-task budget enforcement

## Documentation Improvements Needed

- [ ] Consolidate all validation_task files
- [ ] Add integration tests for V7 format
- [ ] Document Circular KV Lite simulation
- [ ] Add trace schema validator

## Recommended Next Build

Priority | Item
---------|------
P0 | Hot-server runner (run_suite_hot.ps1)
P1 | V7 format integration tests
P2 | Circular KV Lite documentation