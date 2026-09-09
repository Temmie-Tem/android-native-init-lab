# S22+ v0.1.2-rc.2 gauge diagnostics qualification

P379 adds the diagnostics missing from the consumed P378 run. The target is
SM-S906N/g0q/S906NKSS7FYG8. The subsequent attended run closed NO_PROOF with exact rollback and final
healthy state. Diagnostics localized rejection at the root-model allowlist.
The functional version remains v0.1.1; no gauge reading was established.
Preparation-stage evidence below is retained as historical context.
See [Gauge Diagnostics V1](../operations/S22PLUS_FYG8_GAUGE_DIAGNOSTICS_V1.md).

## Resulting behavior

The kernel keeps its original measurement interface and conversions. The new
pure status snapshot reports the last probe/check stage, binding state, read
stage, error and existing SMBus return, including the actual ID/revision byte
when an identity check rejects it. No additional bus transaction is performed.
Probe-not-called remains distinguishable from a failed probe, but by itself
does not distinguish a missing child from an already-owned child.

The collector preserves fixed-path open/read errno, a bounded raw sample and
snapshot, and a specific parser or age rejection reason. Successful sample
acceptance and the 96-byte HUD packet are unchanged. Diagnostics do not change
gauge validity or substitute for the existing three-fresh-sample qualification.

At most eight diagnostic lines fit within the existing log budget. Suppression
tracks reason/error/state changes, excluding raw measurement returns and attempt
counters, so normal changing current does not spend the diagnostic budget.
Pure snapshot reads may continue until that budget is spent. Each line is one
bounded nonblocking pipe write; failed writes are not retried. The separate
collector, CONTROL/return and rollback behavior remain unchanged.

## Host evidence

The final v5 diagnostic module is A/B identical, 304,648 bytes, SHA-256
`329e3ac99a1febff226d66ee3bd940f0b8629c537b6eb910ee182f78c6ff293a`.
All 21 imported symbol CRCs match the exact kernel Image exports. The builder
rechecks the module receipt and each source input. The measurement core is
byte-identical to P378. Earlier host drafts are retained, not overwritten.

Final2 candidate artifacts:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| AP | 31,139,881 | `795b6cc35b015d1b0247c9c273b20d4bc7c412905eba37e36e2310095351d922` |
| Image | 41,490,944 | `dea3a66b619be3ad1e649162bac576571d1e206dba2f84bc18c2c7f9d82a342e` |
| init | 149,448 | `7f5a1eea6a86865c527cab5a3086710198a723e9c1081378556296c04b17b204` |
| renderer/collector | 777,336 | `b3f88d8e17edb5a9266bfe131cdd2b4a3914e45bf71aaa88cf8c274b8d4d3e58` |

Host tests cover actual wrapper status without extra I2C calls; raw rejected
ID/revision returns and latched faults; ARM64 read errno, parser reasons, raw
retention and bounded/suppressed records; real wrapper output to ARM64 parser;
actual ARM64 collector and descriptor handling; generated PID1/collector/HUD
IPC, diagnostic capture, rendering and blocked/exited collectors; live receipt
invariants. These do not prove actual child binding or gauge availability.

Independent final review passed and binds final2: receipt SHA-256
`d082d44b14a7e3e5c9361e32aa4d1df1251be9290dcb27500eed43e67513c323`.
The reviewer checked all 279 source inputs, actual A/B artifacts, the exact
Image import CRCs, official static regeneration and real common bundle
verification. Six integration/receipt tests and three final diagnostic tests
passed independently. The official static is 38,246 bytes, SHA-256
`73477fc7a0bff075352d03d9b2a84b3d67845751b4b78a8eb1080d33deddf587`.
The review also covers the two changed foreground-goal source hashes; that
refresh opens or renews no grant. READY publication and connected read-only preparation completed as recorded
below. Fresh attended F1 approval is still required. Consumed P378 remains closed, and its
photo, raw logs and formal NO_PROOF result are unchanged. A90/S20+ are outside
this unit.

## READY and connected preparation

The READY manifest is 9,103 bytes, SHA-256
`873518efbb7ae7183acb60ef0decc8c5e7664bdff1a50478f94a3f90a954b519`.
The verified actual bundle is
`529a20963e806d150df5b816a749690b42db5e0b28751051235a69bb9fd24f45`.

One `--prepare` completed in `p379-ready1-prepared-20260910-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. The D0 result is 3,261 bytes,
SHA-256 `665c2a5d2a775912ac042c590682fb8a19789259e6329075285d514f6afc55ca`.
The prepared record is 37,546 bytes, SHA-256
`f37d071fe261e1ff834ffc3fca280e7e0d5ba66a35fc89001ba3b21b406ce4da`.
Writes, reboot requests, Odin and partition transfers are false. The actual
prepared-record consumer reopened it and sealed the three-command plan, 877
bytes, SHA-256
`180c146cf332f150f0cc393885679c89d5c4769d6c383e9123b10a9ee4eae41d`.

A90 and S20+ received no command. No F1 ledger row or native lease is created.
Fresh exact approval and current physical attendance are required for the new
candidate and its exact rollback/final-health transaction. H0 and ordinary
Android preparation do not prove diagnostic output or gauge reads in native
boot. The functional version remains v0.1.1.

## P379 live close and localized cause — 2026-09-10 KST

The exact approval was consumed once. Original execute completed with
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p379_root_console_unproved_rollback_verified`. One candidate and one exact
rollback completed; the read-only journal validator accepted CLOSED/19.
`recovery_required=false`, final rooted FYG8/original hashes/Android health and
Download absence passed. No recover invocation or replay occurred.

All six fixed requests reached terminal responses, but the gauge HUD proof
was false and all three planned commands remained unexecuted. The capture
contains 15 matched frames, sequences 1–15, uptime 3612–17711 ms, with 14 BUSY
frames. Memory/CPU were available; gauge data remained unavailable. The formal
observer/session failure classification is not promoted to full console PASS.

An authenticated offline replay used the complete received session and retained
handshake-plus-command TX. It reconstructed the 6,927-byte sixth-command stdout
and matched its original receipt exactly. Two diagnostic records were recovered:
startup open ENOENT, then sample-read ENODEV with a successful diagnostic read.
The second snapshot establishes:

| Derived field | Value | Meaning |
| --- | ---: | --- |
| probe stage | 7 | Root model check rejected |
| probe error | -19 | ENODEV from the explicit allowlist branch |
| bound | 0 | Reader never bound |
| read stage / attempts | 0 / 0 | No identity or measurement bus read began |
| raw read return | -61 | Initial ENODATA sentinel |
| latched stop | 0 | No bus-fault latch occurred |

The exact target kernel's `of_property_read_string` returns EINVAL, ENODATA
or EILSEQ on failure, not ENODEV. Thus the model string was read successfully
and matched neither permitted Waipio string. Parent/name/address/compatible and
parent/adapter OF checks before stage 7 passed. The later resistor, private
parent/FG-client relationship and adapter-capability checks were not reached.
This is a driver identity-guard rejection before I2C or unit conversion, not
proof of a chip failure. The actual model string was not included in this
snapshot; do not invent it. P378's earlier unlocalized record remains unchanged.

The operator photograph shows unclipped rc.2/footer text, BUSY at uptime10,
memory1053/7024 MiB, available5971 MiB, CPU0.1%, sample age0.0s, and all gauge,
temperature and charge fields N/A. It is a separate OBSERVED physical record,
not an exact frame/time or continuous-update proof. The original photo remains
private; machine result and journal are unchanged. Diagnostic localization
succeeded, but v0.1.2 remains unconfirmed. HUD image publication is deferred
until actual gauge display is observed in rc.3, as requested by the operator.

Canonical timeline (UTC):

| Event | Timestamp |
| --- | --- |
| `live_session_start` | 2026-09-09T21:09:21.581077Z |
| `candidate_flash_start` | 2026-09-09T21:09:40.357140Z |
| `candidate_flash_done` | 2026-09-09T21:09:42.101982Z |
| `candidate_boot_ready` | 2026-09-09T21:10:22.343923Z |
| `rollback_flash_start` | 2026-09-09T21:10:30.440107Z |
| `rollback_flash_done` | 2026-09-09T21:10:32.128388Z |
| `rollback_boot_ready` | 2026-09-09T21:11:18.194487Z |
| `live_session_end` | 2026-09-09T21:11:18.214999Z |

Private retained evidence:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `live-result.json` | 47,142 | `bd4da81d45e8c81fd519f862519bb8d5df3505919057262f73909da3423d3450` |
| `candidate-observer.json` | 38,066 | `349fe706bad3ddb7b3584a6cee48e481459a8eb16a739b685b6306082cfd1085` |
| `authenticated-hud-log.bin` | 6,927 | `df120b4f3b8b3b7f4f3c0075655c3dc2a6526388ef02a72aff7e2d448f28cd92` |
| `operator-gauge-diagnostic-photo.jpg` | 88,468 | `db577585060e5414bb665722a6800429e5702f491846e0e544b986958fe4f92b` |
| `operator-gauge-diagnostic-observation.json` | 1,008 | `815a536f4d2a5cb89c9fff4db524c502ce7a9ba7181e8a5e761648c08826e979` |
