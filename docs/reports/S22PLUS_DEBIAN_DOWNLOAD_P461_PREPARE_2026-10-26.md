# S22+ P461 Debian Download return preparation

State: **PASS_READY_H0_AND_UNEXECUTED_ENTRY**, with independent capability
**PASS_GO**. This report covers the new capability and its
concrete preparation, not device execution authority. The selected target
is S22+ FYG8 only. A90, S20+ and their existing changes remain untouched.

This was the pre-execution boundary. The separately approved
[P461 physical run](S22PLUS_DEBIAN_DOWNLOAD_P461_RUN_2026-10-26.md) subsequently
completed automatic Download/A return and healthy closure; this task is consumed.

## Result and implementation

P461 retains P460's two Debian boots, four admitted writable lifetimes and
persistent cron configuration creation, second-boot consumption and retirement.
The first reboot remains ordinary. After the second boot, the new fixed
`download` control enters packaged SysV runlevel 6. A RAM dispatcher preserves
K01–K05 cleanup and invokes the final RAM hook at K06.

The hook verifies authenticated intent, actual native_data root identity and
ext4 superblock read-only state. A read-only bind flag alone is insufficient.
One exclusive RAM claim and the original deadline protect each module/control
operation. Five exact retained stock modules prepare the Samsung route, then
one literal Download restart is attempted. Failure or a returned syscall parks
without an alternate control, repeat insertion or persistent cleanup.

The host uses the existing measured Download and boot-only original-A transfer
machinery. Departure, exact Download arrival and A dispatch share the original
90-second final-control window, clipped to the grant. A normal automatic return
must join that arrival to the actual A transfer. Health-only continuation after
raw-proved A preserves those facts; physical recovery cannot create them.

The [specialization](../operations/S22PLUS_DEBIAN_DOWNLOAD_RETURN_V1.md) records
the stock initialization effects, including the temporary FULLDUMP selection,
SEC_DEBUG_MODE write and existing stock read-error hazard. No dump acquisition,
unattended operation or automatic failure recovery is introduced. Blocking
kernel calls still depend on attended physical recovery.

## Qualification evidence

- The reviewed fixed D0 measured clean native_data M=30 with matching Android
  health before and after. An earlier invocation rejected a relative closed-task
  path before the Android/superblock read; its diagnostic remains preserved.
- The actual-baseline A/B build is identical. The real producer, exact payload
  consumer and retained-template consumer accept the six declared RAM additions:
  one dispatcher and five modules, with unchanged existing member ordering and
  metadata. Physical helpers cross-compile as ARM64.
- Sixty-four focused tests pass. The physical ARM64 helper fixture exercises
  thirty cases, including incorrect intent/root state, repeated claim, deadline,
  provider/registry binding, five insertion failures, expiry after each insertion
  and returned reboot calls without another control. Actual target UAPI flags
  are used; host syscall delivery is substituted explicitly.
- The actual two-boot packaged SysV VM passes, including the ordinary first
  reboot, cron configuration settlement and clean M=30 to M=34. Samsung firmware
  Download is explicitly substituted by VM power-off; this is not device proof.
- All 49 ARM64 cases pass. The original package consumer rederives the complete
  corpus and accepts the 38,082,601-byte boot-only AP, actual CPIO and template.
  Independent final PASS_GO has no findings and binds 157 host and 178 runtime
  sources. Its bounded raw rederivation confirms both positive boot chains and
  all 48 negative cases; it does not rerun the full VM corpus.
- Cold original image admission passes from an unrelated directory in a fresh
  Python process, with file writes, process/network effects and raw acquisition
  denied. The concrete task also passes both phase constructors, its exact finite
  step sequence and rejection of nonexecutable constructor data as a grant.
- The separate bridge review passes for 20 sources and two unchanged resident
  inputs. Published v7 is accepted by the original consumer and connected worker.
- Independent prepared-entry review passes the actual persisted
  `Controller.bundle(current=True, approval=False)` and nine missing/altered
  approval negatives using memory-only invalid fixtures. The connected worker
  reports no approval, grant or dispatch; all three continuation paths are also
  `NOT_DISPATCHED`.

The private evidence root is
`workspace/private/outputs/s22plus-debian-download-p461-h0-20261026-1/`.
It preserves failed and superseded host builds, partial VM work, original raw
outputs, source snapshots and independent review records. Old P460 artifacts,
approval, consumption and closure retain their original identities.

## Execution boundary

The intended operation is one attended P461 `debian-autoboot` owner with a
3600-second budget: one N transfer, two Debian boots, one ordinary reboot,
one final Download request and one original-A return with Android health.
The concrete task is `216b357bf1e38a991f394c07657ae13e5b567e9d56979e2a9b9c4082719ea0d6`.
At preparation, its source snapshot, capability bindings and independent entry
review passed while returned approval and current attendance were still pending.
No grant, entry attempt or image transfer had occurred at that boundary. The
separate run report above records the later human approval, actual Download/A
proof and closed consumption. Final post-return filesystem consistency remains
unproved.
