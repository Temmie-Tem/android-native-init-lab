# S22+ v0.1.2-rc.1 gauge HUD qualification

The bounded unit adds gauge SOC, voltage and signed current to the native HUD.
Target: SM-S906N/g0q/S906NKSS7FYG8. The subsequent attended run closed
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; exact rollback and final health passed.
The functional version remains v0.1.1. The sections before the live close below
retain the preparation-stage evidence and authority separation.
The prospective design is [Gauge HUD V1](../operations/S22PLUS_FYG8_GAUGE_HUD_V1.md).

## Evidence and correction

The prior battery research's 17-module inventory described AP additions, not
the full inherited runtime: vendor_boot already loads all 73 USB-plan modules.
Disassembly of the actual init and MAX77705 parent module establishes the
existing MFD/PDIC load and fuel-gauge child/client construction. The new reader
reuses that child and its existing 0x36 client without rerunning the parent.
Stock fuel-gauge initialization is excluded because it performs writes.

The wrapper checks the reviewed parent structure offsets, actual OF-node
identities and resistor setting before exposing any read. Independent review
found an initial path check using `device_node.full_name` incorrectly: this
kernel stores unit names there. Exact `of_find_node_by_path` identity checks
replaced it before qualification. No device probe consumed that host draft.

A later consumer review found a timestamp relation that rejected fresh reads
starting after the collector's loop-start time. System and gauge ages are now
checked independently; a fixture with the later gauge start produces valid
frames. Cached samples retain their original timestamp and values.

The common bundle rehearsal caught an incomplete packaged-module allowlist:
the builder contained 18 additions but the inherited artifact list named 17.
Only the new candidate's packaged list and builder snapshot were corrected;
the sealed 12-module display dependency graph is unchanged. A fresh final2
build retained the earlier host drafts and produced identical AP bytes.

## Host qualification

The final component module A/B builds are byte-identical, 294,480 bytes,
SHA-256 `a0a78e0831fed6cf11a64bdf8583851ed8bad4b29cb33e3a84c1161ab8043eda`.
Every imported symbol CRC matches the exact FYG8 candidate Image exports.
The build receipt and all its source inputs are revalidated by the candidate
builder. The final2 candidate AP is 31,129,641 bytes, SHA-256
`f2c4cb1dd8509298dc9a076ea663220e8e007f00225dcf1eefa6eb77bd15815b`.
The final renderer is 711,304 bytes, SHA-256
`404cbf9d458f73b4bcfa7b700814a91e6772905af804ff620996577215e45fc0`.
The new Image identity transform is
`45ca04ed855b767085f2ea813216e2a9f0b593d79fd065469f0c1a6e5831dcbd`.

Core/wrapper tests exercise fixed read order, identity negatives, signed
conversion extremes, SOC clamping, finite budget, cache/lock behavior and
first-error latching. Actual wrapper output is consumed by the ARM64 parser.
The generated renderer tests cover bounds, immutable lifecycle, packet order,
cache contradictions, invalid ranges and age at paint and matched event.
The generated PID1, collector and renderer use real IPC with a deterministic
DRM fixture; absent and blocked collectors retain console control.
The raw-frame observer requires three distinct fresh gauge and memory/CPU
samples, including a BUSY frame, and rejects stale or malformed evidence.
These fixtures establish host behavior, not live bus readings or visible text.

Independent component review and the changed candidate capability review passed.
The reviewer ran 45 independent tests; the inventory correction was separately
reviewed against the actual 18 packaged modules, 13 renderer rows and unchanged
five return modules. The final independent receipt is SHA-256
`74a90e12a8a609d1a631064fffbc4e1ce151a43dadb9b4b6d7a8c10d427fad40`.
It independently rehashed 259 build inputs, 40 static sources, final A/B artifacts,
the exact official static regeneration and the actual common bundle rehearsal.
The two changed foreground-goal review source hashes were separately covered;
that refresh opens or renews no grant.

## Boundaries and retained evidence

The provider performs fixed identity and three measurement reads only. A bus
operation may still block despite trylock; separate collector ownership keeps
userspace control independent but does not prove recovery from a kernel stall.
The original ten-minute limit, one-shot CONTROL/return, exact rollback and final
health remain binding. A90 and S20+ are outside this unit.
Private build drafts, module A/B files, compiler logs and receipts remain under
`workspace/private/outputs/`; no binaries or raw device logs are committed.
Temperature and charge state are not inferred from current direction. Gauge
SOC is not promoted to Android battery-policy percentage.

## READY and connected preparation

The official static result is 37,857 bytes, SHA-256
`160692f2d5555ca33abc8a0f6850e0f2b53e8daf4716c170b6f8587cb85f365d`.
The READY manifest is 9,103 bytes, SHA-256
`e1228139869d91b92649e04877502b12f12b9f965cdb8c45f018f890b6201583`;
the verified bundle is
`0cb2e7cab00a956bff5c3adfa37895fcdcd9dee05c5785581c2b655e0188cc44`.

One exact connected preparation completed in
`p378-ready1-prepared-20260909-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. The retained D0 result is
3,260 bytes, SHA-256
`c547c0f73c386e66528b66f287b5cc4c8e75ac3075b13f87f47ac1b1041a736d`.
The prepared record is 36,988 bytes, SHA-256
`27328c6559ac92e1e400998c654417aa4e584919b5c1f21db8cb0576fd10a86b`.
Device writes, reboot requests, Odin and partition transfers are all false.
A90 and S20+ received no command. No F1 ledger row is created before an effect.
Fresh exact approval and current physical attendance remain required for the
one candidate, fixed qualifications/three-command console plan, exact rollback
and final health. No native gauge-reading or physical-screen proof is claimed.

The actual prepared-record consumer reopened the published bundle and run.
The exact console-plan consumer reopened the sealed three-command plan:
877 bytes, SHA-256
`43ce00417966304b328579b9be638a1c68d5fb667f203df59c3ff93a01fa6907`.
A host summary initially treated the D0 receipt as an embedded result; it was
corrected by dereferencing the retained file after load/seal had succeeded.
No connected read, preparation or device transition was repeated.

## Attended live close — 2026-09-10 KST

The operator supplied the exact prepared approval in response to the attendance
condition. The original execute ran once and completed without a recover call.
One candidate and one exact rollback completed. The journal validates as
CLOSED/19; `recovery_required=false`, final rooted FYG8/original hashes/Android
health and Download absence passed. A90 and S20+ received no command.

The result is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p378_root_console_unproved_rollback_verified`. All six fixed requests were
accepted and reached terminal responses, but the gauge HUD proof is false.
The aggregate `qualified_command_count` is 0; none of the three planned console
commands was executed. CONTROL acceptance remained observable. Preserve the
observer's `authenticated-session-error`, `framed_session_closed=false` and
`P378 root console stopped; no replay`; do not relabel it as full console PASS.
ACK-only `software_download_arrival=UNPROVED` is also preserved separately from
the subsequent exact Download/rollback/final-health evidence.

The bounded HUD capture contains 15 matched-frame records, sequences 1–15,
uptime 3896–18022 ms, including 14 BUSY frames. The last record has valid=3,
so memory/CPU are valid but gauge fields are not; gauge sequence is 0.
The new module's load index 12 has a retained LOAD_DONE marker, which establishes
insertion return only, not a successful child probe or register read. The capture
does not retain the fixed module sample or a probe/read error reason. Therefore
it cannot distinguish rejected child binding, failed sampling and consumer
rejection. No specific cause is promoted from the N/A display.

The operator photograph separately shows unclipped version/status text, uptime
10 seconds, BUSY console, memory 1052/7024 MiB, available 5972 MiB and CPU 0.3%.
Gauge SOC, voltage, current and gauge age are all N/A, as are temperature and
charge state. This is OBSERVED physical output; one photograph does not prove
continuous updates, an exact machine frame or a gauge measurement. The original
photo and separate observation record are retained privately; machine records
and journal are unchanged. v0.1.2 is not confirmed and this consumed candidate
cannot be replayed. Further gauge diagnosis needs its own bounded H0 preparation
and any new device execution must satisfy the existing authority rules.

Canonical timeline (UTC):

| Event | Timestamp |
| --- | --- |
| `live_session_start` | 2026-09-09T20:15:02.879217Z |
| `candidate_flash_start` | 2026-09-09T20:15:24.740906Z |
| `candidate_flash_done` | 2026-09-09T20:15:26.472801Z |
| `candidate_boot_ready` | 2026-09-09T20:15:55.237095Z |
| `rollback_flash_start` | 2026-09-09T20:16:03.752761Z |
| `rollback_flash_done` | 2026-09-09T20:16:05.540899Z |
| `rollback_boot_ready` | 2026-09-09T20:16:52.174202Z |
| `live_session_end` | 2026-09-09T20:16:52.194630Z |

Retained private evidence:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `live-result.json` | 47,141 | `57591f638914c50d49f0d9514446a638da883fb9206b3a256f23b95adf0e0538` |
| `candidate-observer.json` | 38,064 | `03881c733a2f6976eeeecbf60ee318342319e9fe3a3850b1ff1f98441d38aafb` |
| `operator-gauge-hud-photo.jpg` | 77,239 | `35765b9a74882c886bfc0850757ed45f61dbdab82eabf2d929979f9a5b2adc65` |
| `operator-gauge-hud-observation.json` | 1,021 | `63f352f20516048f00926aea2fb3d0d4152a42122c3ebfa2abaa1a4f92d4e99f` |

Close validation: the read-only journal validator accepted the complete chain;
new closure fields, unique append-only row, document links, goal size and diff
checks passed. The full legacy ledger auditor stops at its existing row 547
unknown-evidence-outcome error; the unchanged HEAD ledger reproduces the same
error. That historical row and the auditor were not changed for this close.
