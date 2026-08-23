# A90 H35 Native recovery-command pre-write failure

Date: 2026-08-23
Target: operator-owned Samsung Galaxy A90 5G
Disposition: `RECOVERY_CLOSED_PREWRITE_ONLY_H35_UNPROVED`

## Result

The attended H35 run consumed candidate
`0.11.202 / phase3-minimal-h35-public-mpgen-rtic-canary`, 58,372,096 bytes at
SHA-256 `5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759`,
but did not write it. The candidate helper verified the exact local marker,
size, and SHA-256, revalidated the single A90 Native USB and managed-bridge
bindings, and sent its sole Native-to-Recovery request. After 5.344 seconds it
stopped with:

`bridge command outcome uncertain after one send for 'recovery': None`

The canonical candidate receipt is `PRE_WRITE_FAILURE` with
`writeStarted=false`, `bootWrittenReadbackExact=false`, and
`systemReturnAttempted=false`. H35 therefore received no boot opportunity. It
is unproved, not refuted, and cannot be replayed.

The durable records are:

| Record | Size | SHA-256 |
|---|---:|---|
| `22-candidate-result.json` | 332 | `89f203221385146f8fc43356e6fecb14c3a87e6c36203f439e8bfa8a5fe37bfc` |
| `32-rollback-result.json` | 365 | `19cc40642a5d24dd92723283b4b2f971bc2b1bbedb50f28ebaa218faa22eb4cf` |
| `40-terminal.json` | 498 | `bf7c30cd5bbeec393726f842cd2c720fbea8d9247bbed52fa1c4c4b419d37eda` |
| `41-recovery-closed.json` | 1,088 | `912d72e01c83f8792f1dcd289b009820a05b5792eebd8f3510365bac1dcd55c1` |

The owner followed its predeclared rollback branch. The rollback helper's
structured outcome is
`BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED`: exact V2321 boot bytes
were written and read back and the sole System return was confirmed. Its
process returned nonzero because final Native health was not proved inside the
helper, so record 40 correctly remained
`RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`.

After the rollback re-enumerated ACM from `/dev/ttyACM1` to `/dev/ttyACM0`, the
fixed managed bridge was rebound to the same by-id identity. The current
reviewed candidate-neutral postrollback finalizer then observed exact healthy
V2321 `0.9.285 / v2321-usb-clean-identity-rodata`, preserved both replay flags
as false, published record 41, and removed only the active-run guard. The H35
candidate guard remains as the consumed no-replay marker.

## Classification and next boundary

This run says nothing about H35 kernel, RTIC, Android, Debian, or Wi-Fi runtime
behavior because H35 never reached the boot partition. The failure is a
pre-write Native-to-Recovery command-response attribution failure. A visible
Recovery transition would not substitute for the missing exact command
outcome, and none is inferred here.

Before another candidate identity, H0 must diagnose and repair that exact
response path without loosening the one-send rule. The same preflight also
found that `a90_bridge.py repair-dirs` accepted owner-writable mode `0775`
while `serial_tcp_bridge.py` correctly requires an owner-private parent. The
host directories were narrowed to `0700`; the helper mismatch was the second
H0 repair requirement. Any execution-closure change requires current independent
review, and a future candidate requires a fresh identity, qualification,
manifest, connected D0, and attended approval. This incident grants none of
those authorities.

The host-only implementation follow-up is
`A90_PRE_CANDIDATE_RECOVERY_READY_OWNER_H0_2026-08-23.md`. It moves exact
Recovery readiness ahead of candidate-guard consumption and fixes the
directory helper, but remains non-authoritative pending independent review.
