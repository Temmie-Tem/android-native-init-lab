# A90 Phase 2D V3406 Execution Closure H0

Date: 2026-07-31
Decision: `A90_PHASE2D_V3406_EXECUTION_CLOSURE_H0_PASS`

Independent verdict: GO
Unresolved HIGH: 0
Unresolved MEDIUM: 0
Device actions: none

## Result

The host closure now supports one fresh V3406 Debian display transaction
without granting live authority. It adds:

- a new-inode per-run Ed25519-keyed copy of the exact clean Phase 2B 2 GiB
  ext4 image;
- split native-release, Debian-ready, and bounded-failure marker validators;
- an attended visible-confirmation receipt that is bound to the mechanical
  display proof and a finite deadline;
- a connected D0 helper that records exact A90 baseline health and read-only
  final/work/stage absence;
- a host-only finalizer that binds the current execution sources, private
  evidence, exact Phase 2 candidate, and canonical V2321 rollback;
- V3406 support in the absent-only stager and F1 orchestrator.

The recovery path treats any display-evidence parser failure as `NO_PROOF`.
Such a failure cannot preempt the already-authorized exact rollback. A fault
test using the display observer's distinct exception type proves one rollback
invocation and `observation_proven=false`.

## Exact host closure

- key materializer:
  `5bcd3a91a70ef6e21192be1bc09173158762543ced8cc41a451904636dfca542`
- display observer:
  `4e920bd61029ce5631f3de44d3ae89f10231e35489d46e98d05e8658a60954fb`
- connected D0 preflight:
  `ca8314e57a11b3f9407205178743802cb46b1e0ef0be4d681fe45574714be10a`
- F1 finalizer:
  `04141c1aa4737d26c77125c781165fa82abd114e36de8d2fc120230a51dd1042`
- absent-only staging adapter:
  `0262d480360ad55e74273c77005af62e9670d63ef10f635b45fd006cce21199f`
- F1 orchestrator:
  `8465eb450637cd0dec0084d68c91ad43a48f13b6d2b3f96d5ccf63cac48c3703`

The finalizer hard-pins the canonical V2321 rollback to size `60882944`,
SHA256
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`,
the exact V2321 version/build, and the boot partition. A V3405 template cannot
substitute another rollback artifact.

Connected evidence self-binds its helper path, size, and SHA256. Both the
finalizer and V3406 staging loader compare those values to the current helper,
and the staging execution closure retains the helper as a bound file through
live verification.

## Validation

- integrated focused regression: `185/185 PASS`
- Phase 2C closure regression: `6/6 PASS`
- touched Python: `py_compile PASS`
- tracked diff whitespace: `git diff --check PASS`
- keyer, connected-preflight, and finalizer host audits: ready with device,
  staging, flash, reboot, F1, and live authority all false

The independent review specifically rechecked recovery exception containment,
canonical rollback identity, connected-helper self-binding, and current
Phase 2C machinery hashes.

## Authority

No device was accessed, no rootfs was staged, no boot image was transferred,
and no approval receipt was created. This report permits the reviewed host
closure to be committed and used for subsequent H0 materialization and one
bounded D0 preflight. It does not authorize F1.
