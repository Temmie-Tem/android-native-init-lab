# Claude Usage And Review Ledger

Last updated: 2026-07-21 20:04 KST

## Purpose

This is the consolidated project ledger for substantive Claude reviews. It
tracks quota observations, conversation sessions, context pressure, and the
technical records produced from each review. It does not replace the linked
design or result reports, and it does not treat a Claude verdict as live
authorization.

Only values actually recorded by the Claude CLI or an existing repository
report are included. Missing historical values are marked `not recorded`; no
quota, token, time, or cost value is reconstructed from later observations.

## Interpretation Rules

- `current-session usage` is the rounded subscription usage for Claude's
  rolling session window. It is not the token count of one conversation or one
  CLI process.
- `weekly usage` is a separate quota window. Percentages from different reset
  windows must not be added together.
- A percentage delta is approximate because the account UI reports rounded
  values and may include other calls made in the same quota window.
- A conversation UUID identifies a resumable local Claude conversation. It is
  useful for continuity but is not evidence that every review in the same
  quota window used that conversation.
- Cost, output-token, and elapsed-time values are recorded only when the CLI
  reported them directly.
- Technical findings and GO/NO-GO decisions belong in the linked report. This
  ledger records their scope and outcome only.

## Chronological Ledger

| Date (KST) | Conversation | Model / effort | Review scope | Current-session usage | Weekly usage | Reset shown | Result and evidence |
|---|---|---|---|---:|---:|---|---|
| 2026-07-10 | `10a19d6c-d0ef-4659-af34-dfd6472c7eb6` | Claude Opus, high effort | V3426 observer architecture; V3428/V3428R transition controls; V3429 direct-PID1 implementation | not recorded | not recorded | V3429 later reported HTTP 429 with reset at `00:20 KST`; calendar date was not recorded | Architecture progressed from `GO-WITH-MUST-FIX` to host-only `GO`; V3428 pre-live defects were fixed; V3428R evidence was accepted; V3429 found one HIGH truncated-token issue, later closed locally, but final Opus delta review was quota-blocked. See [V3426 plan](../plans/NATIVE_INIT_V3426_S22PLUS_DIRECT_PID1_PHASE_OBSERVER_DESIGN_2026-07-10.md), [V3428 result](../reports/NATIVE_INIT_V3428_S22PLUS_STOCK_TRANSITION_POSITIVE_CONTROL_UNAVAILABLE_2026-07-10.md), [V3428R result](../reports/NATIVE_INIT_V3428R_S22PLUS_STOCK_TRANSITION_POSITIVE_CONTROL_LIVE_PASS_2026-07-10.md), and [V3429 report](../reports/NATIVE_INIT_V3429_S22PLUS_DIRECT_PID1_PHASE_OBSERVER_HOST_BUILD_PASS_2026-07-10.md). |
| 2026-07-11 | `c43595a1-fd84-4563-bf9a-e3831cc44331` | Claude Opus 4.8, high effort, no Claude tools | Native-PID1 parallel-lanes architecture review and adversarial correction | approximately `13% -> 28%` | approximately `38% -> 40%` | not recorded | Two-round review. The correction turn reported `7,468` output tokens, about `USD 0.99`, and about `119 s`. No code or repository file was changed by Claude. See [parallel-lanes review](../reports/S22PLUS_FYG8_NATIVE_PID1_PARALLEL_LANES_ARCHITECTURE_REVIEW_2026-07-11.md). |
| 2026-07-12 | not recorded | Claude Opus | R3C0 live-helper adversarial review and fix re-review | `23% -> 46% -> 58%` | not recorded | `2026-07-13 01:50 KST` | First review returned NO-GO; fixes closed the findings; re-review returned GO. Approximate observed delta across the recorded sequence: `+35` percentage points. See [R3C0 source-ready report](../reports/S22PLUS_FYG8_R3C0_LIVE_GATE_SOURCE_READY_2026-07-12.md). |
| 2026-07-12 | not recorded | Claude Opus | R3C1 artifact reproduction and builder audit | `60% -> 76%` | not recorded | `2026-07-13 01:50 KST` | GO with no high or critical finding. One LOW input-TOCTOU finding was fixed by reading and validating each artifact once. Approximate observed delta: `+16` points. See [R3C1 artifact report](../reports/S22PLUS_FYG8_R3C1_ARTIFACT_REPRODUCTION_2026-07-12.md). |
| 2026-07-12 | not recorded | Claude Opus | R3C1 one-shot live-gate source review | `76% -> 92%` | not recorded | `2026-07-13 01:50 KST` | GO with no blocking finding and four accepted LOW residuals. Approximate observed delta: `+16` points. See [R3C1 live-gate report](../reports/S22PLUS_FYG8_R3C1_LIVE_GATE_SOURCE_READY_2026-07-12.md). |
| 2026-07-13 18:30 | `290dc782-0f91-41bf-b876-b7aedb9e0903` | Claude Opus, high effort | Resumed R4W1/R4W1A review context; account usage and context inspection only for this entry | snapshot `75%` | all models `77%`; Fable `2%` | session `2026-07-13 22:30 KST`; weekly all models `2026-07-14 05:00 KST`; Fable `2026-07-14 04:59 KST` | `/usage` and `/context` were inspected without a new technical review. The conversation was cleanly exited and remains resumable by UUID. |
| 2026-07-13 20:02-20:19 | `290dc782-0f91-41bf-b876-b7aedb9e0903` | Claude Opus 4.8, high effort | Independent HOST-ONLY READ-ONLY adversarial review of R4W1A A5 commit `c889e14f` | `75% -> 85%` | all models `77% -> 79%` | session `2026-07-13 22:30 KST`; weekly all models `2026-07-14 05:00 KST` | `GO_TO_SEPARATE_POLICY_ACTIVATION_REVIEW`; no blocking finding, four LOW observations, 57 focused tests passed. Direct CLI metrics: `$4.76`, API `9m 15s`, wall `16m 55s`, `32.2k` output tokens. See [A5 adversarial review](../reports/S22PLUS_FYG8_R4W1A_A5_STREAM_CANDIDATE_ADVERSARIAL_REVIEW_2026-07-13.md). |
| 2026-07-13 20:30-20:41 | `290dc782-0f91-41bf-b876-b7aedb9e0903` | Claude Opus 4.8, high effort | Independent HOST-ONLY READ-ONLY activation review attempt for R4W1A A6 commit `f9e49404` | approximately `93% -> 101%` | all models `79% -> 80%` | session `2026-07-13 22:30 KST`; weekly all models `2026-07-14 05:00 KST` | No formal verdict: repeated CLI command-classifier denials preceded session-limit exhaustion. LOW-1 and A6 report consistency were confirmed, but this is not binding approval. Cumulative CLI-counter delta from the immediately preceding snapshot: approximately `$2.93`, API `99 s`, wall `664 s`, `6.2k` output, `1.9m` cache read, and `182.5k` cache write. Codex independently found and fixed one activation-cycle blocker; see [A7 checkpoint](../reports/S22PLUS_FYG8_R4W1A_A7_ACTIVATION_CYCLE_CLOSED_REVIEW_PENDING_2026-07-13.md). |
| 2026-07-14 00:09-00:19 | `89567438-0885-4f08-b462-f48d50eb8d2e` | Claude Opus 4.8, high effort, read-only tools | Independent adversarial review of the R4W1-B direct-PID1 exec-acceptance host design | `0% -> 32%` | all models `79% -> 83%` | session and weekly `2026-07-14 05:00 KST` | `GO_WITH_MUST_FIX`. It confirmed the exec-acceptance leg and fail-closed null, then found the unproved forced-from-park retention leg, 1,536-byte geometry conflict, unspecified Android header/kernel-size reconciliation, non-anchored marker-family risk, missing inside-Image equality, and missing exact DTBO restatement. All hard findings were incorporated into the revised [R4W1-B design](../plans/S22PLUS_FYG8_R4W1B_DIRECT_PID1_EXEC_ACCEPTANCE_DESIGN_2026-07-13.md). No device action or repository edit was performed by Claude. Direct token/cost/API-time metrics were not reported. Post-review context: `898.2k` free (`89.8%`), `53.4k` messages (`5.3%`), `32.4k` memory (`3.2%`). |
| 2026-07-19 04:18-04:29 | `c7d10391-7bb6-4274-9e49-076007945b03` | Claude Opus 4.8, high effort, plan mode, read-only repository tools | R4W1-B host-only candidate-pipeline architecture, reuse boundary, trust separation, and migration strategy | `16% -> 28%` on first completed render; UI then refreshed to approximately `30%` | all models `3% -> 4%` on first completed render; UI then refreshed to approximately `5%` | session `2026-07-19 05:20 KST`; weekly all models `2026-07-21 05:00 KST` | `GO_WITH_MUST_FIX`. Recommended a minimal reusable slice: canonical new-builder mechanics, checker-only verification primitives, and independently re-derived candidate equality. It rejected a manifest/registry trust root, shared builder/checker construction path, old FYG8 post-kernel geometry reuse, and any live-runner/timeline scope. All MUST-FIX items are incorporated in the [minimal reusable candidate pipeline design](../plans/S22PLUS_FYG8_R4W1B_MINIMAL_REUSABLE_CANDIDATE_PIPELINE_DESIGN_2026-07-19.md). Direct CLI metrics: `$2.99`, API `6m 31s`, wall `9m 32s`, Opus `8.8k` input and `26.7k` output, `982.7k` cache read and `178.5k` cache write; Haiku `2.6k` input and `46` output. No code, repository file, build, or device action was performed by Claude. Post-review context: `820.1k` free (`82.0%`), `108.5k` messages (`10.9%`), `38.4k` MCP tools, and `26.3k` memory files. |
| 2026-07-19 05:22-05:59 | `c7d10391-7bb6-4274-9e49-076007945b03` | Claude Opus 4.8, high effort, plan mode, read-only repository tools | R4W1-B reusable live-core and target-helper architecture/delta adversarial review | post-review snapshot `18%` | all models post-review `8%` | session `2026-07-19 10:20 KST`; weekly all models `2026-07-21 05:00 KST` | `GO_WITH_MUST_FIX` for host source-readiness; no HIGH finding. It found emergency rollback coupled to ACTIVE/current-helper identity and connected mode missing the live-equivalent double `last_kmsg` read. Both were fixed, with requested orchestration and marker-boundary tests added. Same-conversation cumulative CLI totals were `$11.18`, API `17m 29s`, wall `38m 54s`, Opus `8.9k` input and `71.9k` output, `3.9m` cache read and `740.9k` cache write; relative to the prior recorded conversation snapshot this round added about `$8.19`, API `10m 58s`, wall `29m 22s`, and `45.2k` Opus output. Post-review context: `663.2k` free (`66.3%`), `261.3k` messages (`26.1%`), `39.1k` MCP tools, and `26.3k` memory files. See [source-ready report](../reports/S22PLUS_FYG8_R4W1B_LIVE_GATE_SOURCE_READY_HOST_PASS_2026-07-19.md). No device action or repository edit was performed by Claude. |
| 2026-07-19 06:00-06:05 | `c7d10391-7bb6-4274-9e49-076007945b03` | Claude Opus 4.8, high effort, read-only repository tools | Exact committed `c744abb3` source-delta review | post-review snapshot `34%` | all models post-review `10%` | session `2026-07-19 10:20 KST`; weekly all models `2026-07-21 05:00 KST` | `GO_TO_SEPARATE_CONNECTED_POLICY_BINDING_REVIEW`; no finding. Same-conversation cumulative totals were `$15.91`, API `20m 29s`, wall `42m 44s`, Opus `8.9k` input and `84.0k` output, `6.1m` cache read and `1.1m` cache write. Context showed `106.7k` file-read tokens, `26.3k` memory, `2.5k` skills, and no loaded MCP tokens. No device action or repository edit was performed by Claude. |
| 2026-07-19 06:06-06:13 | `c7d10391-7bb6-4274-9e49-076007945b03` | Claude Opus 4.8, high effort, read-only repository tools | Exact R4W1-B connected-only binding clause review | approximately `34% -> 51%` | all models approximately `10% -> 11%` | session `2026-07-19 10:20 KST`; weekly all models `2026-07-21 05:00 KST` | `GO_TO_BIND_CONNECTED_ONLY_POLICY_COMMIT`; no HIGH, MEDIUM, or blocking LOW finding. It proved one connected sentinel, zero live sentinel lines/substrings, exact code/pin/observer agreement, and no transfer authorization. Same-conversation cumulative totals were `$20.31`, API `23m 30s`, wall `47m 47s`, Opus `8.9k` input and `97.3k` output, `7.2m` cache read and `1.4m` cache write. Relative to the prior snapshot this review added `$4.40`, API `3m 01s`, wall `5m 03s`, about `13.3k` Opus output, `1.1m` cache read, and `0.3m` cache write. Post-review context showed `108.4k` file-read tokens, `26.3k` memory, `2.5k` skills, and no loaded MCP tokens. See [connected binding report](../reports/S22PLUS_FYG8_R4W1B_CONNECTED_POLICY_BINDING_HOST_GO_2026-07-19.md). No device action or repository edit was performed by Claude. |
| 2026-07-19 06:25-06:29 | `c7d10391-7bb6-4274-9e49-076007945b03` | Claude Opus 4.8 requested, high effort, read-only repository tools | Proposed R4W1-B post-connected packet generator and live-clause template review | snapshot `52%` | all models `11%` | session `2026-07-19 10:20 KST`; weekly all models `2026-07-21 05:00 KST` | No verdict. The resumed interactive turn produced no review output, and the explicit print-mode retry returned `You've hit your session limit`. No technical conclusion is attributed to Claude. Codex then performed its own adversarial review and fixed render-field injection, evidence TOCTOU, connected-clause inheritance, and success-path test gaps. See [preconnected packet report](../reports/S22PLUS_FYG8_R4W1B_LIVE_BINDING_PACKET_PRECONNECTED_READY_HOST_PASS_2026-07-19.md). No device action occurred. |
| 2026-07-21 00:59-01:14 | `f89b5716-0573-42d1-9b8a-c7d7dcc58b3c` | Claude Opus 4.8, xhigh effort, plan mode, read-only repository tools | Exact committed `6861497d` R4W1-C2 measured-usbfs live helper and rendered one-shot policy adversarial review | `17% -> 81%` | all models `24% -> 27%` | session `2026-07-21 05:10 KST`; weekly all models `2026-07-21 05:00 KST` | `GO_TO_EXACT_POLICY_ACTIVATION`; no MUST-FIX. It approved rendered clause SHA256 `6f0f0471...5c478f8f` unchanged and confirmed all eight safety areas. Direct CLI metrics: `$6.1275`, API `886.095 s`, wall `893.689 s`, `59.9k` output, `5.58m` cache read, `183.9k` cache creation. Claude's Python test attempt was plan-sandbox denied; Codex had already passed `141/141` and actual offline/source gates. See [R4W1-C2 Opus review](../reports/S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_OPUS_ADVERSARIAL_GO_2026-07-21.md). No device action or repository edit was performed by Claude. |
| 2026-07-21 01:33-01:35 | `55c500cb-3c9e-4405-a167-b297bef5f0c1` | Claude Opus 4.8, xhigh effort, plan mode, read-only repository tools | Bounded R4W1-C2 pre-consumption USBFS repair delta review | `81% -> 100%` | all models `27% -> 28%` | session `2026-07-21 05:10 KST`; weekly all models `2026-07-21 05:00 KST` | No verdict. The review made 11 analysis turns but hit HTTP 429 before rendering a final decision, so it is not activation authority. Direct CLI metrics: `$1.188329`, API `109.785 s`, wall `111.043 s`, `7,954` output, `212,578` cache read, and `88,314` cache creation. A separate ephemeral `gpt-5.6-sol` xhigh read-only review later returned GO; see [repair adversarial GO](../reports/S22PLUS_FYG8_R4W1C2_USBFS_REPAIR_CODEX_ADVERSARIAL_GO_2026-07-21.md). No device action or repository edit was performed by Claude. |
| 2026-07-21 06:01-06:11 | ephemeral, persistence disabled | Claude Opus alias, high effort, plan mode, read-only tools | Process v2 H0 core adversarial review, remediation, and exact delta re-review | not recorded | not recorded | not recorded | Both rounds returned `GO_HOST_CORE_TO_D0_IMPLEMENTATION`. The first found journal-tail replay, fail-open ambiguous Odin classification, and run-path containment defects; all were fixed. Delta review found no new HIGH/MEDIUM issue. Combined direct metrics: `$1.897644`, API `464.217 s`, wall `464.759 s`, `32,549` output, `196,918` cache read, and `98,539` cache creation. See [Process v2 host-core report](../reports/DEVICE_ACTION_PROCESS_V2_HOST_CORE_PASS_2026-07-21.md). No device action, repository edit, test, build, or web action was performed by Claude. |
| 2026-07-21 06:24-06:28 | ephemeral, persistence disabled | Claude Opus alias, high effort, plan mode, read-only tools | Reusable Process v2 D0 adapter adversarial review before connected read-only qualification | not recorded | not recorded | not recorded | `GO_D0_CONNECTED_READ_ONLY`; no HIGH finding. One MEDIUM bootloader/incremental overconstraint and LOW USB-root, empty-inventory, and output-cap findings were fixed before the D0 run. Direct metrics: `$0.970639`, API `240.993 s`, wall `241.125 s`, `17,323` output, `25,468` cache read, and `52,481` cache creation. See [D0 qualification report](../reports/DEVICE_ACTION_PROCESS_V2_D0_QUALIFICATION_PASS_2026-07-21.md). Claude performed no device action, repository edit, test, build, or web action. |
| 2026-07-21 07:00-07:25 | ephemeral, persistence disabled (`2638e8a6...`, `7467fb54...`, third call no verdict) | Claude Opus 4.8 alias, high effort, plan mode, read-only repository tools, fast mode off | Reusable Process v2 F1 adapter execution-closure review and remediation delta review | `/usage` returned no percentage | not recorded | third call hit HTTP 429; reset displayed as `2026-07-21 10:30 KST` | The first two rounds returned `GO_HOST_SOURCE_TO_SEPARATE_MANIFEST_READINESS_AND_D0_PREPARE`; the third rendered no verdict and is not authority. Initial review found no HIGH, one MEDIUM test gap, and two LOW robustness/bound issues; the successful delta review confirmed M1/L1/L2 closed. Combined three-call direct metrics: `$5.857253`, API `979.484 s`, wall `982.338 s`, `69,907` output, `2,199,846` cache read, and `300,935` cache creation. See [F1 adapter host PASS](../reports/DEVICE_ACTION_PROCESS_V2_F1_ADAPTER_HOST_PASS_2026-07-21.md). Claude performed no device action, repository edit, build, test, or web action. |
| 2026-07-21 evening | `a0378e14-6b74-4987-8337-068602d5fe59` | Claude Opus 4.8, high effort, plan mode, read-only repository tools | Post-R4W1-D observable-runtime architecture and retained-carrier correction | `0% -> 28% -> 55%` | all models `8% -> 10% -> 12%` | session `2026-07-22 00:49 KST`; weekly `2026-07-28 04:59 KST` | Persistent two-round discussion. The first review agreed on local-runtime, bind/UDC, ACM, and fixed-exchange rungs but incorrectly recommended pmsg. After exact V3439 evidence, Claude explicitly withdrew pmsg/ramoops and moved to Samsung `sec_log_buf`. Codex then corrected the review's unsupported reserved-carve-out premise against the actual R4W1-D patch and FYG8 writer, and strengthened one mutable slot to A/B committed slots. Direct cost/token/time metrics were not reported. Context moved from `994.3k` free (`99.4%`) to `812.6k` free (`81.3%`); no compaction was needed. See [post-PID1 architecture](../plans/S22PLUS_FYG8_POST_PID1_OBSERVABLE_RUNTIME_ARCHITECTURE_2026-07-21.md). Claude performed no device action, repository edit, build, test, or web action. |

## Current Context Snapshot

The same conversation was measured before and after the 2026-07-13 A5 review:

| Category | Before | After |
|---|---:|---:|
| Free space | `937.6k` (`93.8%`) | `823.5k` (`82.3%`) |
| Memory files | `32.4k` (`3.2%`) | `32.4k` (`3.2%`) |
| Messages | `14.6k` (`1.5%`) | `128.9k` (`12.9%`) |
| Skills | `2.3k` (`0.2%`) | `2.3k` (`0.2%`) |
| MCP tools | `0` loaded tokens | `0` loaded tokens |
| Custom agents | `83` tokens | `83` tokens |

The resumed conversation had already been compacted once. After the long A5
review it still retained `823.5k` free tokens, so context pressure alone does
not justify another immediate compaction.

## Observed Consumption

The repository has several paired measurements for bounded reviews, but not
enough for a model-wide cost forecast:

| Review unit | Observed current-session delta | Other direct measurement |
|---|---:|---|
| 2026-07-11 two-round architecture discussion | approximately `+15` points | correction: `7,468` output tokens, about `USD 0.99`, about `119 s` |
| R3C0 initial review | approximately `+23` points | no token/cost/time record |
| R3C0 fix re-review | approximately `+12` points | no token/cost/time record |
| R3C1 artifact review | approximately `+16` points | no token/cost/time record |
| R3C1 live-gate review | approximately `+16` points | no token/cost/time record |
| R4W1A A5 adversarial review | approximately `+10` session points; `+2` weekly points | `$4.76`; API `555 s`; wall `1,015 s`; `32.2k` output, `4.6m` cache read, `163.6k` cache write |
| R4W1A A6 activation-review attempt | approximately `+8` session points; `+1` weekly point | no verdict; approximate direct counter delta: `$2.93`; API `99 s`; wall `664 s`; `6.2k` output, `1.9m` cache read, `182.5k` cache write |
| R4W1-B host-design adversarial review | approximately `+32` session points; `+4` weekly points | `GO_WITH_MUST_FIX`; direct token/cost/API-time metrics not reported; post-review context `898.2k` free (`89.8%`) |
| R4W1-B candidate-pipeline architecture review | first completed render approximately `+12` session points and `+1` weekly point; final UI refresh approximately `+14` and `+2` | `$2.99`; API `391 s`; wall `572 s`; Opus `26.7k` output, `982.7k` cache read, `178.5k` cache write; `GO_WITH_MUST_FIX` |
| R4W1-B exact source-delta review | approximately `+16` session points; `+2` weekly points | cumulative `$15.91`; API `20m 29s`; wall `42m 44s`; `GO_TO_SEPARATE_CONNECTED_POLICY_BINDING_REVIEW` |
| R4W1-B connected binding review | approximately `+17` session points; `+1` weekly point | delta `$4.40`; API `181 s`; wall `303 s`; about `13.3k` Opus output; `GO_TO_BIND_CONNECTED_ONLY_POLICY_COMMIT` |
| R4W1-C2 measured live activation review | approximately `+64` session points; `+3` weekly points | `$6.13`; API `886 s`; wall `894 s`; `59.9k` output, `5.58m` cache read, `183.9k` cache creation; `GO_TO_EXACT_POLICY_ACTIVATION` |
| Process v2 H0 core review plus remediation re-review | not recorded | `$1.90`; API `464 s`; wall `465 s`; `32.5k` output, `196.9k` cache read, `98.5k` cache creation; `GO_HOST_CORE_TO_D0_IMPLEMENTATION` |
| Process v2 D0 adapter review | not recorded | `$0.97`; API `241 s`; wall `241 s`; `17.3k` output, `25.5k` cache read, `52.5k` cache creation; `GO_D0_CONNECTED_READ_ONLY` |

These deltas are not directly comparable: prompt size, attached evidence,
output length, compaction state, and concurrent account activity were not held
constant. They support operational budgeting only, not per-token billing or a
claim that one review class always consumes a fixed percentage.

## Known Gaps

- Reviews before 2026-07-11 generally recorded technical verdicts but not
  quota snapshots.
- The persistent 2026-07-10 conversation has no before/after usage values.
- The 2026-07-12 reports do not record conversation UUIDs, weekly usage,
  context occupancy, elapsed time, output tokens, or cost.
- The post-review Fable percentage was not captured; only the all-model weekly
  before/after pair is attributable to the A5 review window.
- UI percentages are rounded and account-wide; they are not an auditable token
  meter.

## Recording Protocol

For every future substantive Claude review:

1. Run `/usage` and `/context` before the first prompt.
2. Record KST timestamp, conversation UUID, exact model, effort level, review
   scope, and linked source/report paths.
3. Keep related fix and delta reviews in the same conversation when practical.
4. Run `/usage` after each load-bearing round and `/context` after a long round
   or before deciding to compact.
5. Record exact verdict, finding counts/severity, output tokens, elapsed time,
   and cost only when directly displayed.
6. Compact based on context pressure and topic continuity, not mechanically
   after every turn.
7. Put full technical reasoning in the work report and add only one summarized
   row here.

Use this row template:

```text
date_kst:
conversation_id:
model:
effort:
scope:
usage_before: {session_pct, weekly_pct, reset_kst}
context_before: {free_tokens, free_pct, compacted}
usage_after: {session_pct, weekly_pct, reset_kst}
context_after: {free_tokens, free_pct, compacted}
direct_metrics: {output_tokens, elapsed_sec, cost_usd}
verdict:
findings:
report:
commit:
```

## Operational Guidance

- Reserve Opus/high-effort calls for architecture, safety policy, artifact
  identity, live-gate, and post-live evidence reviews where an independent
  adversarial pass can change the decision.
- Use the existing conversation for bounded delta reviews so the model retains
  the exact finding and fix context.
- When the current-session quota is near exhaustion, freeze the exact review
  packet and wait for reset rather than replacing a missing verdict with an
  assumption.
- Weekly quota and the rolling session quota must both be checked. The A6
  activation-review attempt exhausted the rolling session quota at `101%`
  while weekly all-model usage reached `80%`; no further Opus call should run
  before the recorded session reset.
- Claude review never relaxes `AGENTS.md`, creates live authorization, or
  substitutes for static checks, connected preflight, explicit operator
  approval, rollback gates, or real-device evidence.
