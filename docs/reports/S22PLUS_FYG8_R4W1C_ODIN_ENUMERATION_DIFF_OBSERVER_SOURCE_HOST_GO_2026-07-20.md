# S22+ FYG8 R4W1-C Odin Enumeration-Diff Observer Source Host GO

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `SOURCE_GO_TO_SEPARATE_BINDING_POLICY_REVIEW`

Scope: host-only implementation, tests, static validation, and independent
read-only review of a zero-transfer observer for one bounded `odin4 -l`
enumeration. No device was enumerated or contacted. No ADB action, reboot,
Download transition, Odin execution, transfer, flash, partition write,
candidate consumption, policy activation, or acceptance decision occurred.

## Purpose And Boundary

The retired no-serial R4W1-C live gate stopped before consumption and transfer
because the exact Download usbfs endpoint changed during enumeration. Later
host evidence strongly suggested late node metadata or ACL settling, but that
run did not retain enough before/after evidence to identify the changed field.

This source packet only prepares a future observer that can record:

- a complete Android baseline and physical USB binding;
- three identical stabilized Download sysfs and usbfs-node samples;
- complete bounded inventories immediately before and after one exact
  `/usr/bin/odin4 -l`;
- raw stdout, raw stderr, command outcome, process-cleanup outcome, and every
  evidence-persistence error; and
- exact Android return after attended physical Download exit.

Every possible classification is non-accepting. The source owns no AP or
transfer command and grants no candidate, flash, partition-write, or device
acceptance authority. Download has no intrinsic handset serial, so same-handset
continuity remains an explicit attending-operator trust boundary.

## Exact Source Snapshot

```text
observer helper
  size    104055
  SHA256  90707b79c67080533c9c32f9d787f254d83c11ce98471b9a7bfb1c7d15871913

focused test
  size    87409
  SHA256  510bf46191f05096d716409f29a754c928c1f332b8ada767819495235998a545

inactive exception draft
  size    10848
  SHA256  ddcf158a40d4cf56853340c8219535038afb99e99f21b81a9b5f42f902b02c4a
```

The draft is deliberately inactive. Current `AGENTS.md` contains no matching
observer clause, and the helper requires one singular byte-exact rendered
clause before any future live path could open.

## Review History

Four fresh `gpt-5.6-sol` xhigh read-only sessions reviewed successive exact
source snapshots. They did not execute tests, import the helper, build, contact
a device, invoke ADB/USB/Odin, or edit files.

Reviewer `019f7ec7-bec2-76b2-92f9-ecf93a7f0fc0` returned `SOURCE_NO_GO` and
identified four HIGH issues:

1. an interrupt gap between a stabilization read and durable sample evidence;
2. process-cleanup failure could discard already captured partial output;
3. authority was not rechecked after durable result creation; and
4. recovery did not recheck authority around every poll and final result.

Reviewer `019f7ed5-98ea-7473-b679-003f40a9aa05` returned `SOURCE_NO_GO` and
identified three HIGH issues:

1. recovery relabeled canonical timeline placeholders as reached;
2. initial Android baseline and reboot were not fully authority-bracketed; and
3. post-result authority failure could leave a durable PASS result.

Reviewer `019f7ee4-77fc-7ac0-9682-b7930a8a7c5c` returned `SOURCE_NO_GO` with
three HIGH issues and one MEDIUM issue:

1. the live consumed state was not held through a no-follow FD and continuously
   revalidated;
2. recovery still relabeled prior rollback placeholders;
3. failure to persist `enumeration-after.json` skipped remaining command and
   raw-stream evidence; and
4. the two policy-digest preimages were not sufficiently distinguished.

Each blocker was corrected and covered with focused tests. Final reviewer
`019f7ef3-6856-7ae1-af0c-6eb26d2dab7c` reopened the exact three identities
above, the current contract, source, tests, and inactive draft. It found no
HIGH or MEDIUM issue and returned `SOURCE_GO`.

The final review retained two LOW test-coverage limits, neither a source
defect:

- signal-atomic stabilization directly injects SIGINT, while the identical
  source path also masks SIGTERM and SIGHUP; and
- source ordering is fail-closed after durable pending preclosure, but no test
  injects a failure at the exact preclosure-to-final-result boundary.

## Closed Failure Windows

The final source now provides all of the following:

- stabilization sampling and exclusive durable sample persistence under one
  SIGINT/SIGTERM/SIGHUP-masked unit;
- partial stdout/stderr and original interruption preservation even when
  process-group cleanup fails;
- authority checks bracketing baseline, reboot, every stabilization write,
  physical confirmation, observation, every return poll, preclosure, and final
  result;
- a durable non-PASS `PENDING_FINAL_AUTHORITY_VALIDATION` preclosure before the
  final authority gate;
- exclusive consumption before reboot, immediate no-follow reopen, and
  path/inode/SHA continuity through final closure;
- recovery activity separated from canonical timeline milestone status;
- independent attempts to persist post-capture inventory, command outcome,
  stdout, and stderr, with any failure remaining non-PASS; and
- separate normalized-template and final-rendered-clause digest preimages.

The source has one generic bounded `subprocess.Popen` implementation and one
exact Odin-listing callsite. It verifies `/usr/bin/odin4` by held no-follow FD,
executes through that FD, and checks same-path identity before and after. Static
inspection found no AP, transfer, flash, partition-write, USB claim/accept, or
alternate execution surface.

## Validation

```text
py_compile                                      PASS
focused observer tests                         80 passed
adjacent R4W1-C regression tests                84 passed
offline source verdict                         PASS_R4W1C_ENUM_DIFF_OBSERVER_SOURCE_OFFLINE_CHECK
policy active                                  false
device contact/write/reboot/download/Odin      false/false/false/false/false
transfer surface/flash                         false/false
trailing whitespace                            none
tracked real-device serial in packet           none
ruff                                            unavailable
```

The focused suite includes direct observation-level rejection of nonzero
return, truncation, empty stdout, and post-execution Odin pathname mutation. It
also proves that failure writing one post-capture artifact still attempts the
other command and raw-stream artifacts, and that replacing the consumed-state
path during the live path blocks preclosure and final result creation.

## Decision

Commit this host-only source checkpoint. The only next step is a separate,
deterministic binding/policy review of an exact rendered exception. This source
GO does not install or activate a clause, authorize device contact, permit the
observer to run, accept an Odin endpoint, or authorize any transfer or flash.
