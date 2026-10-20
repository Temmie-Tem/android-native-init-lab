# S22+ P440 fixed P437-pair reader after journal replay

Preparation status: **PASS_GO / READY_CONNECTED_FIXED_D0**.
Target: `SM-S906N/g0q/S906NKSS7FYG8`. Preparation opened no grant, transfer or
native_data access. The subsequent [P440 physical read](S22PLUS_AUTOBOOT_EVIDENCE_P440_RUN_2026-10-20.md)
is now consumed and closed healthy, with both P437 files authenticated.

The [P439 run](S22PLUS_JOURNAL_RECOVERY_P439_RUN_2026-10-20.md) completed strict
replay and its read-only checker, restored partition RO and closed Android
healthy. Its exact comparison still leaves three unaccounted tree entries.
P438's earlier dirty home-block view authenticated the P437 early file but
reported the runtime file absent.

Prepare a fresh instance of the existing
[fixed mountless pair reader](../operations/S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md)
for those same exact P437 early/runtime paths. This is a new observation after
a closed recovery, not reuse of P438's consumed candidate or grant. Preserve
both original file verdicts and P439's negative complete-root result.

The helper, two-file table, metadata and size limits remain unchanged.
Partition RO and bounded mountless libext2fs reads permit no mount, replay,
repair, file write or installed execution. Fresh reader identity is declarative
data; the prospective capability pointer and policy selection receive current
source-bound review without repinning a historical receipt.

Completion requires actual A/B image qualification, current producer/consumer
and retained failure-evidence checks, independent review and a concrete
one-operation, 1800-second attended proposal. Fixed Android preparation reads
do not grant execution. Any actual acquisition will preserve raw files before
authenticating their writer/run/source and boot/nonce relationship. Missing,
partial or conflicting records keep their distinct meanings.

A successful capture alone cannot admit a new writable boot. Any historical
root-table addition must use exact authenticated bytes and metadata, with
fresh complete protected admission in the later watchdog candidate.

Private inputs and evidence:
`workspace/private/outputs/s22plus-autoboot-evidence-p440-h0-20261020-1/`.
A90 and S20+ are outside this work.

## Qualification and readiness

Actual fresh `p440` / `v0.11.0-rc.1` A/B packages are byte-identical. Full
AP/Image/CPIO audits and the live image consumer passed. Physical and virtual
reader ELFs differ from P438 only in the fresh reader run identity and GNU
build ID; writer paths, selected table, libraries and compiler are unchanged.

Two fresh ARM64 VMs exercise complete pair acquisition and missing runtime.
Their actual raw projections and full disk-before/after identities passed.
Fixtures rejoin the retained P437 VM producer, not physical P437 data. The
17-case retained corpus and P438's two representative cases remain reusable
with their original provenance. Thirty-three focused tests and Python
compilation passed. Actual incorrect identities and scope mutations reject.

Independent review returned **PASS_GO**, no findings, covering 139 current
host sources and 165 unchanged reader runtime sources. It independently
rederived P438's dirty-view absence and P439's consumed healthy closure and
negative complete-root comparison. No historical result or review was repinned.

Fresh fixed D0 preparation passed both original-A health brackets, exact
partition hashes, Android32 GPT/capacity and current target binding. The
prepared task and raw-derived projection validate; the exact original-A
rollback/recovery basis is preserved. The concrete proposal is one attended
`root-evidence` operation, 1800 original BOOTTIME seconds, one N and at most
one original A. No grant or F1 owner exists.

All 46 preexisting changed paths remain intact; removing the new P440 catalog
row reproduces the previous catalog bytes. Qualification and Android health
do not authorize native_data acquisition or admit a later writable boot.
