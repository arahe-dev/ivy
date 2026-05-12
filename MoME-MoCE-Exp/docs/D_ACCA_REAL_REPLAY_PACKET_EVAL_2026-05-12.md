# D-ACCA Real Replay Packet Eval

Date: 2026-05-12

## Purpose

This run moves beyond the previous synthetic black-box packet by deriving cases from local Codex session JSONL user turns. The harness still auto-labels against a curated ACCA concept catalog, so it is not a final human-labeled field test. It is a harder replay-style pressure test designed to answer:

```text
When the input comes from real Codex conversations, which ACCA variants still route useful context?
```

Raw private session logs are not committed. Generated/redacted cases and detailed query previews live under `out/`, which remains ignored.

## Built Artifacts

| artifact | role |
|---|---|
| `scripts/generate_real_replay_packet_cases.py` | reads Codex JSONL sessions, redacts text, maps real turns to ACCA concepts, and creates fixed organic query variations |
| `scripts/run_real_replay_packet_eval.py` | generates replay packet cases and runs selected ACCA variants through the black-box packet evaluator |
| `tests/test_librarian_advisor_harness.py` | adds a Codex-style JSONL smoke test for the replay harness |

## Non-Parameterized Variation Bank

The harness intentionally does not expose a big variation grid. It uses a fixed internal bank:

- raw replay turn;
- current-only rewrite;
- smallest-safe-agent-packet rewrite;
- stale/decoy guard rewrite;
- slang/messy rewrite;
- follow-up rewrite;
- typo rewrite.

This keeps the test reproducible without making the benchmark feel like a parameter-tuned synthetic packet.

## Source Mix

Full 1000-case run:

| metric | value |
|---|---:|
| session user turns seen | 305 |
| matched user turns | 166 |
| generated cases | 1000 |
| edge cases | 406 |
| edge ratio | 0.406 |

The generator filters orchestration noise such as subagent bootstrap prompts, subagent notifications, heartbeat messages, and AGENTS/environment context blocks.

Matched concept counts before case expansion:

| concept | matched source turns |
|---|---:|
| worktree_branch | 51 |
| deepseek_role | 23 |
| librarian_role | 18 |
| startup_saas | 15 |
| acca_identity | 12 |
| signal_integration | 10 |
| codex_opencode_logs | 9 |
| recall_board_integration | 8 |
| spec_dd_lazy | 6 |
| blackbox_results | 4 |
| bm25_role | 4 |
| distillation_loop | 3 |
| confidence_gate | 1 |
| helper_lazy | 1 |
| real_replay_testing | 1 |

## Selection Runs

Before the full run, two smaller passes were used as sanity checks.

### 64-case smoke

| variant | quality | forbidden | p95 latency |
|---|---:|---:|---:|
| helper-lazy | 0.5781 | 0 | 1.324 ms |
| dd-rule | 0.0312 | 0 | 3.429 ms |
| spec-dd-lazy | 0.0312 | 0 | 1.715 ms |

### 128-case cleaned candidate selection

| variant | quality | forbidden | p95 latency |
|---|---:|---:|---:|
| helper-lazy | 0.6172 | 0 | 1.494 ms |
| d-acca | 0.1328 | 7 | 1.478 ms |
| spec-dd | 0.1328 | 0 | 14.421 ms |
| dd-rule | 0.0938 | 0 | 4.152 ms |
| spec-dd-lazy | 0.0938 | 0 | 1.969 ms |
| rule | 0.0547 | 4 | 3.960 ms |

This changed the full-run top three. The assumed synthetic winners `dd-rule` and `spec-dd-lazy` were too narrow for replay. The full 1000 run used:

1. `helper-lazy`;
2. `d-acca`;
3. `spec-dd`.

## 1000-Case Top-3 Result

Command:

```powershell
cd C:\ivy-worktrees\d-acca-dd-acca-librarian-supercharge\MoME-MoCE-Exp
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe scripts\run_real_replay_packet_eval.py `
  --count 1000 `
  --seed 20260512 `
  --out out\real_replay_packet_eval\results_top3_1000 `
  --cases out\real_replay_packet_eval\real_replay_cases_1000.json `
  --dataset out\real_replay_packet_dataset `
  --variants helper-lazy d-acca spec-dd `
  --candidate-backend indexed
```

Results:

| variant | quality | edge quality | forbidden hits | precision | recall | mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| helper-lazy | 0.5980 | 0.6305 | 0 | 0.5980 | 0.5980 | 0.706 ms | 1.447 ms |
| d-acca | 0.1290 | 0.1601 | 35 | 0.1455 | 0.1640 | 0.657 ms | 1.496 ms |
| spec-dd | 0.1080 | 0.1182 | 0 | 0.1080 | 0.1080 | 3.491 ms | 14.508 ms |

## Interpretation

This is the first result in this branch that looks meaningfully less "internal benchmark-y." The old synthetic packet made helper-lazy look perfect. The real replay packet does not. Helper-lazy is still the clear winner, but it only passes 598/1000. That is a useful result because it shows the system is not merely rubber-stamping itself.

The direct D-ACCA baseline is very fast but brittle on real replay phrasing. It also hit forbidden/decoy evidence 35 times. That confirms the original concern: a deterministic router without enough learned alias/profile help can be both under-recalling and occasionally unsafe when replay turns contain broad or messy phrasing.

Spec-DD avoided forbidden hits but did not retrieve enough required evidence. Its p95 latency also rose to 14.508 ms because it internally verifies draft heads. This means the current Spec-DD logic is too narrow for broad real replay. The speculative architecture may still be good, but the draft heads need to be learned from replay/librarian failures rather than hand-coded around the earlier synthetic cases.

DD-rule and Spec-DD-lazy were not selected for the full run because the 128-case cleaned selection pass showed they were weaker than direct D-ACCA and Spec-DD on this replay corpus. That is an important finding: distilled rules from a tiny DeepSeek/librarian fixture do not generalize automatically.

## What We Learned

1. The helper/profile layer is real leverage.
   - It turned real, messy Codex phrasing into useful context far more often than direct D-ACCA.

2. Helper-lazy is not enough yet.
   - A 0.598 quality score means missing aliases, broad turn classification errors, and over-compressed intent are still common.

3. Replay breaks narrow synthetic winners.
   - DD-rule and Spec-DD-lazy looked strong on the focused librarian fixture but weak on broader replay.

4. Safety and precision matter separately.
   - Spec-DD had zero forbidden hits but low recall.
   - D-ACCA had better recall than Spec-DD but admitted forbidden/decoy evidence.

5. The next engine feature should be learned confidence plus distillation, not another static query template.
   - The failure mode is not only retrieval. It is deciding when a turn is too broad, when helper metadata is missing, and when to escalate.

## Caveats

- Labels are auto-derived from a curated ACCA concept catalog.
- This does not yet test final model answer quality.
- Some replay turns are still broad project-management turns rather than clean user questions.
- The packet is real-log-derived but not human-labeled.
- Generated case files may include redacted query previews and should stay under `out/`, not in committed docs.

## Next Build

1. Add a human-review packet for the hardest 50-100 replay cases.
2. Add metadata ablation against helper-lazy on the replay packet.
3. Add a distillation log: every helper miss becomes an alias/rule/test candidate.
4. Build Confidence Gate v1 around replay features:
   - helper alias score;
   - direct D-ACCA selected evidence;
   - stale/decoy risk;
   - query breadth;
   - category uncertainty;
   - no-context likelihood.
5. Rerun 1000 replay cases after adding gate/distillation and measure whether helper-lazy moves above 0.70 without increasing forbidden hits.
