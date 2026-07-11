# Native-init V3443 S22+ HIGH Panic Comparison Policy Activation

Date: 2026-07-11 KST

## State

`S22PLUS_V3443_HIGH_PANIC_COMPARE_POLICY_STATE=ACTIVE`

The operator explicitly approved the V3443 live comparison after source-ready
commit `ac539683`. `AGENTS.md` now pins helper SHA256
`9e5e561bc39019b7ec5ebe1a79c3a24fa89803bca568c7aec6d5308a1a35f6a9`
and the three independent HIGH-panic, preamble-only, and MID-recovery
acknowledgements.

The active scope is one HIGH dispatch, one SysRq panic, exactly one
`PrEaMbLe\0` command, one bounded response packet, HIGH retained-log collection,
and immediate MID restoration. `PrObE`, `DaTaXfEr`, memory ranges, RAM transfer,
and dump retrieval remain forbidden even after a positive acknowledgement.

No device action occurred during policy activation. Next is connected read-only
dry-run. Live HIGH or panic is allowed only if that dry-run proves the exact
MID Android/Magisk baseline, pinned control evidence, setter/recovery artifacts,
and host PyUSB runtime.
