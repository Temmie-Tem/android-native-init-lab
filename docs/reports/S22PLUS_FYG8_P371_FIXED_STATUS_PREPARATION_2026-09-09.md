# S22+ FYG8 P371 fixed STATUS preparation

P371 adds two usable fixed status observations after P370's planned host
handoff and resumed authentication. The target remains exact S22+ FYG8;
P370 is consumed and CLOSED. This is H0 preparation, not a device effect or
permission to replay a prior candidate.

## Behavior and proof boundary

One child, one planned host reopening and the original sixty-second budget
remain. STATUS sequences 8 and 9 carry only the fixed authenticated request.
Each reply has eight signed data bytes: version, ordinal, submitted-swap
count, wait/child flags and native elapsed milliseconds since the first sample.
The first elapsed value is zero. The host waits two seconds before its second
request; qualification requires the independently signed native interval.

A shared sampling helper observes the exact child's wait4(WNOHANG) state,
retains a reap if one occurs, and reads the existing monotonic clock. STATUS
consumes its ordinal before writing a response. It neither consumes CONTROL
nor emits the final CONTROL checkpoint. No target ABI flags were added.

CONTROL 10 remains valid at a complete-frame boundary before either STATUS,
between them or after both. The normal host requires both samples only when
qualifying the completed result: negative wait facts and an early second
sample do not prevent sending CONTROL. Authentication, syscall, clock and
transport failures stop without retry. No arbitrary shell, path, PID selection,
child restart, additional handoff or budget renewal was introduced.

A successful candidate must show both expected fixed-wait samples and at least
two seconds of native spacing, the existing signed final checkpoint, accepted
CONTROL, exact Download arrival, one exact rollback and final health. These are
two observations, not continuous liveness, pixel evidence or arbitrary
connection/kernel/PID1-failure recovery. Attendance and physical Download
recovery remain required for a separately approved F1.

## Implementation and H0 evidence

P370 sources remain sealed. The fresh namespace adds one native sampling/status
include and reuses the host handoff owner under a fresh bound identity. Common
receipt routing preserves P370's field values while selecting each variant's
handoff records and command count. Both positive and negative P371 receipts
rederive STATUS samples from retained raw bytes; two legs still mean one host
reopening and one session per descriptor, with six counted commands.

The design received independent review before implementation. Actual generated
native C and the actual host descriptor/record consumer are exercised with PTY
and platform fixtures. Early CONTROL and malformed request cases deliberately
exercise the native protocol outside the normal two-query host qualification;
they do not claim a valid production raw transcript. Build/static qualification and final source-bound review passed as recorded
below; connected preparation is recorded separately.

Thirteen focused tests passed and were independently repeated. Coverage includes
normal two-query use, native CONTROL before/between/after queries, early second
sampling, child exit, duplicate/reordered STATUS and a consumed partial-response
write failure. Actual common owner tests cover positive and negative raw receipt
reopening, STATUS-field tampering and exact rollback after response failure.
The combined P371/P370/P369/P368/P367, common live and goal-research suite passed
135/135; seventeen changed/new Python files compiled. Namespace projection
seams were corrected before native qualification, with their exact occurrence
checks retained. Fresh P371 metadata now reports the actual reconnect count
and two qualification legs; consumed P370 metadata is unchanged.

The 188 build inputs were frozen and rechecked unchanged. Both compiled outputs
are static AArch64; the A/B boot-only packages are identical and contain only
`boot.img.lz4`. The Image transform uses the existing verified identity-only
construction and preserves its original length.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| A/B-identical boot-only AP | 31,006,761 | `72d3322531c8adc8aab28d67048b40e274807f8d135d45f2270685ec368e8f8f` |
| Native init | 151,648 | `76f232b1893d566efb12c4ee32d3f05c6aaec285e40b17eeafff568b108950dc` |
| Fixed-wait renderer | 710,040 | `50031047521746a7556e41f7cc6c73fba29b91000dac7c083551c6036f32a96a` |
| Candidate-static receipt | 79,906 | `3a89223771726a726177f8d65a6c39dc31623ae690e4fcc0c8861277cd2173d8` |

Private source freezes, build outputs, raw H0 test evidence and review receipts
remain in `workspace/private/outputs/s22plus_fyg8_p371/`. No P371 F1 closure row
is written before a device effect.

## Final review and publication

Final source/artifact review returned PASS_GO with no blocking findings. It
verified 188 build inputs, 238 static closure entries, A/B equality, 135
regression passes and an independent thirteen-test run. The private review
receipt SHA-256 is `bce54397d64e59d597c713b0b6e8b010f40036f0320f98680afa2049054aceb0`.

Actual common offline verification and publication passed. The ready manifest
is `workspace/public/src/device-action/manifests/s22plus_fyg8_p371_process_v2_ready_1.json`,
5666 bytes, SHA-256 `f6c26b93b0e70b744bef1d995714f77ea55dc5c3845b9fa5fcdc36f7ab90699c`.
The published bundle SHA-256 is `7fdcb623cf809248675d719f438b9c10b5262bfbb9aeeffdbc7b4aefe858cad5`.
Publication made no device contact.

The prospective goal-research review was refreshed for the changed live owner
and target clause; its previous exact receipt is retained privately. Current
review SHA-256: `b3984cace1a173c2d16eb41ab04f2527bef81f7370529ffeb12e14222ed9f740`.
The review verified P370 CLOSED/19, rollback/final health, absent pending D1,
F1 owner and research grants, and the current runtime review gate. It rewrote
no historical grant or consumed binding and opened no new research grant.

## Fresh connected preparation

One fixed read-only `--prepare` completed in
`p371-ready1-prepared-20260909-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Exact rooted S22+ FYG8,
original boot/supporting partition hashes, completed Android/stopped boot
animation and Download absence passed. It requested no reboot, mode change or
partition transfer; other targets received no commands. A separately returned
fresh attended F1 approval and available physical Download recovery remain
required before any P371 candidate effect.

The actual `load_prepared` consumer reopened the published/prepared paths
successfully. The prepared record is 35,571 bytes, SHA-256
`28070356385965ce5977e2e43bcad5f56a24b5908e3251d081c32b7f87895460`.
Implementation, qualification and connected preparation are complete. Only the
separately returned attended F1 approval remains; no live STATUS claim follows
from these H0/D0 results.
