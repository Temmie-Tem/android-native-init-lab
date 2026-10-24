# P458 physical baseline and candidate preparation

Status: **PASS_PHYSICAL_BASELINE_AND_H0_CANDIDATE**. The selected unit is the operator-requested
fixed S22+ baseline D0, a candidate built against that receipt, and a reviewed
unexecuted task with its exact attended finite approval. It does not include
opening the grant or starting the experiment. A90, S20+ and server work remain
untouched.

## Physical baseline and candidate

The fixed [baseline profile](../operations/S22PLUS_DEBIAN_REBOOT_V1.md#fixed-pre-build-baseline-d0)
returned **PASS_BASELINE_SUPERBLOCK_ONLY**, with clean native_data mount count
**M=18**. Exact original-A health passed before and after in the same Android
boot. The existing GPT and Android32 storage checks passed before the fixed
4096-byte native_data read. The source snapshot and raw evidence rederive;
there was no mount, filesystem write, transfer, reboot or F1 grant.
This is a superblock baseline, not complete current-root admission.

The new `p458` / `v0.19.0-rc.0` candidate seals that physical receipt and counts
18 through 22 at the four admitted writable boundaries. A/B construction is
identical. It uses the unchanged 168-source runtime closure and the reviewed
[production two-boot path](S22PLUS_DEBIAN_REBOOT_P458_INTEGRATION_H0_2026-10-25.md).
All **25 ARM64 production cases pass** for this build: one actual two-boot
lifecycle, two post-mount/pre-file error controls and twenty-two rejection
cases. The two SSH intervals are 120700 and 121850 ms; installed boot counts
advance from the boundary fixture's 99998 to 99999 and 100000. The final
superblock is clean at M+4=22, all four final files match, and allocated bytes
outside native_data remain unchanged. Consumed-count retry and a third startup
reject. The corpus retains its explicit Samsung platform, watchdog and USB
substitutions; this does not prove physical reboot success.

The actual 38,021,161-byte boot-only AP passes the original physical image and
archive consumers, including strict raw VM rederivation. It produces a physical
`image.json` with `ANDROID_FIXED_D0`, rather than the earlier synthetic H0
package. Original offline task preparation verifies artifact bytes, the exact
rollback/recovery evidence and the current 148-source host capability, then
saves the concrete task/proposal and frozen host/runtime snapshots. Both real
phase constructors and the eight-step operation sequence pass; their explicitly
nonexecutable H0 constructor input is rejected by the actual grant validator.
The unchanged production sources reuse their previous 121 focused tests and
independent capability review. The three private preparation/check/entry Python
files compile. Independent **PASS_READY_H0_AND_UNEXECUTED_ENTRY** has no findings.
The actual persistent bundle and status consumers pass with the final published
review, without source-verification overlays. Missing approval, five stale or
empty approval cases and a changed prepared-task pin reject. Negative approvals
existed only in memory; no operator approval file was created.

## Reviewed execution-tool compatibility

The existing approved-tool consumer requires top-level candidate, profile and
version fields in the independent capability receipt. The prior P458 core
contained the reviewed scope but omitted those three consumer fields. An
independent compatible successor adds exactly those fields, preserves every
original field and source map, and advances only the public review receipt.
Both original bundle predicates and twenty negative mutations were checked.
The completed D0 still rederives solely from its saved source/review snapshot;
its old receipt and original raw evidence are unchanged.

The persistent backend's immutable v1 review predated the P458 integration.
A separately reviewed v2 binds its current fourteen sources. The eight changed
members equal the already reviewed P458 closure; the stable worker and policy
are byte-identical. The selector now names v2, preserving v1. Actual capability,
selector and backend verification pass without virtualized source verification.
There is no execution-code, privilege, recovery, transport or authority change
in this preparation unit.

The baseline/build/VM records retain their original private directory. The
unexecuted task uses a separate direct preparation directory matching the
existing connector's naming contract, with exact references to those artifacts.
No symlink alias or directory-validation bypass is introduced.

## Execution boundary

The existing [two-boot finite effect](../operations/S22PLUS_DEBIAN_REBOOT_V1.md#selected-finite-effect-and-original-recovery)
requires one attended 3600-second, one-operation grant: one N transfer, two
Debian boots with one ordinary reboot, one final shutdown and one physical
original-A return. Each boot has two protected admissions and bounded writable
lifetimes; all four counts remain sealed. Uncertain effects never replay.

The approved terminal worker was unavailable at preparation time. It has not
been started. Its [ordinary-terminal deployment](../operations/S22PLUS_APPROVED_TERMINAL_PERSISTENT_V1.md#deployment)
retains uid/euid 1000 and NoNewPrivs=0. Live host-holder checks, fresh target and
Android health, runtime full-root admission and the actual attendance/recovery
conditions remain execution-time requirements. Successful H0 checks cannot
replace them or establish physical Debian reboot success.

Private immutable evidence is retained under
`workspace/private/outputs/s22plus-debian-reboot-p458-physical-prepare-20261025-1/`
and `workspace/private/outputs/s22plus-debian-reboot-p458-h0-20261025-1/`.
The exact task, proposal, source snapshot and prepared-entry review agree.
The independent reviewer also reopened all 125 normal-run command captures and
the complete 25-case corpus. The actual status is NOT_DISPATCHED, without an
approval record, grant, dispatch, attempt log or operation. The finite proposal
may now be presented; it is not a returned approval.

Qualification binds the exact current working-tree source bytes. All 46
pre-existing dirty files remain unchanged, including unrelated target work.
The repository boundary, local document links and whitespace checks pass.
