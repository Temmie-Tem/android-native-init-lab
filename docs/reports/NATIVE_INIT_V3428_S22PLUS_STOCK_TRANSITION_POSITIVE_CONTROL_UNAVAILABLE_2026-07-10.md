# V3428 S22+ Stock Transition Positive Control Live Result

## Verdict

`UNAVAILABLE_STOP_MANUAL_DOWNLOAD_TIMEOUT; CURRENT-RING PAIR PASS; FLASH 0`.

The stock/Magisk-origin positive control did not reach the selected transition.
The helper proved its exact run-bound PRECHECK+FINAL pair in the current
`/proc/ap_klog` ring, then observed no Odin device during the attended manual
RDX/Download window and stopped before any flash. This run neither proves nor
disproves cross-session retention.

## Pins And Review

- Target: `SM-S906N/g0q/S906NKSS7FYG8`
- Helper SHA256: `1b2c3395334efd8d51388676799c832042a82df20dad49817e0ab403ce78be52`
- Observer contract: `cba82ce1bae23f56bcad57876f5d647e31a37a36d7bc9b477de57b1f85b3babf`
- Transition contract: `426aa2bb50f6e73e153f5f5dc9cde59ddf37ab315f46860c1dc0bd0b3e810734`
- Focused validation: `49 tests PASS`, `py_compile PASS`
- Connected read-only dry-run: PASS before and after exception pinning
- Persistent Claude Opus session: `10a19d6c-d0ef-4659-af34-dfd6472c7eb6`
- Independent pre-live verdict after fixes: GO

Opus first rejected the helper because post-rollback health was non-gating, the
hard deadline was not rechecked immediately before flash, timeline semantics
were unclear, and imported Odin logging was not guaranteed to redact serials.
The final helper gates exact target/root/boot identity before classification,
rechecks the 180-second deadline after AP verification, uses JSON-safe observer
shutdown, adds no-candidate semantic events to the canonical event stream, and
uses local redacting Odin wrappers.

## Live Evidence

Private run:
`workspace/private/runs/s22plus_v3428_stock_transition_20260710T094423Z/`.

- Run ID: `40903bee21e68437fc063090fb46014b`
- Live start: `2026-07-10T09:44:23.650120Z`
- Quiet-transition start: `2026-07-10T09:44:24.880427Z`
- Live end: `2026-07-10T09:47:24.069336Z`
- Baseline `/proc/ap_klog`: 2,097,136 bytes, current-run markers 0, PASS
- PRECHECK snapshot: exact PRECHECK only, no issue, PASS
- FINAL snapshot: exact PRECHECK then FINAL, no issue, PASS
- Baseline SHA256: `42368321afe06b3243ab4ea51ceafd65a1bad11d7300a4243224accefd034a1f`
- PRECHECK SHA256: `235ab3f9906234dc037c379d7b8d99d5649cd018bba086af1aea1c317019d753`
- FINAL SHA256: `18c0166e033a844586bf8d4542c0e3ca8911857973da32b9205e6ab9d9e6fbee`
- Odin observations during the manual window: no device
- Candidate flash: 0
- Magisk identity rollback flash: 0
- Stock fallback flash: 0
- Reboot: 0
- First-boot `/proc/last_kmsg` reads: not reached

`timeline_complete=false` is intentional and honest: the required
`rollback_flash_start`, `rollback_flash_done`, and `rollback_boot_ready` phases
never happened. The event stream explicitly records that the compatibility
`candidate_*` phases were marker-arm events and that no candidate flash existed.

## Final Device State

Read-only post-run checks found normal Android/Magisk:

- model/device: `SM-S906N` / `g0q`
- bootloader: `S906NKSS7FYG8`
- `sys.boot_completed=1`
- `ro.boot.verifiedbootstate=orange`
- root: `uid=0`, Magisk context
- boot SHA256: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

## Development Note

Before the final helper was frozen, one baseline inspection reused the legacy
M3 root wrapper. That wrapper writes `/dev/null` to
`/proc/sys/kernel/core_pattern`; the write was unintended and volatile, and no
partition was written. The V3428 helper was changed to a local root wrapper that
does not perform this write. The final post-run read still showed
`core_pattern=/dev/null`. It was not restored because the original value was not
pinned and the V3428 exception authorized no additional sysctl write.

## Next Gate

The one-shot V3428 exception is consumed and retired. A rerun needs a new exact
exception and explicit approval. The operator must be ready to enter Samsung
RDX/Download only after the helper prints `MANUAL_ACTION_REQUIRED`; absence of a
transition remains `UNAVAILABLE/STOP`, and no direct-PID1 candidate may proceed
until the stock-origin same-transition positive control actually reaches the
first rollback boot and produces a valid double-read classification.
