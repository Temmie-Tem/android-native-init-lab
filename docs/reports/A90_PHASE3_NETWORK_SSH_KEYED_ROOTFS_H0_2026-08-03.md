# A90 Phase 3 Network/SSH Keyed Rootfs H0 Qualification

Date: 2026-08-03
Target: Samsung Galaxy A90 5G only
Tier: H0
Decision: `A90_PHASE3_NETWORK_SSH_KEYED_ROOTFS_HOST_PASS`

## Result

One absent-only host materialization created a new-inode private copy of the
exact reviewed Phase 3 network/SSH rootfs and inserted one fresh per-run
Ed25519 observer public key as root-owned mode-0600
`/root/.ssh/authorized_keys`.

The canonical qualification is
`a90-v3406-debian-display-f1-20260803-02`. Its private summary SHA256 is
`bc5956221a48deb89b3c7958fd56b5f9bb255ebebe480ae576e490b9c9f724f7`.
The keyed 2 GiB ext4 image SHA256 is
`168aff0345e1c6d829ece6959e637608917ca90217c1ec5fb9edfeb2f34699c4`.
The clean source remained
`8c4167f66bd339d49bd31625cf419e3551930fa331e2964d544eaba96799d5bd`.

The earlier Phase3-specific run-ID output and canonical sequence `-01` are
superseded private H0 evidence. They are excluded from qualification and will
not be reused.

## Exact closure and validation

- materializer SHA256:
  `44bb425533ccfd5b65b9be94056da302fa646d97b2b346ec15214cd7a5660396`;
- focused-test SHA256:
  `9026fc290d4c6a11fd0177f3737fd7ddbcc2e56cf249af0dad5934cc7137dced`;
- reviewed Phase 3 manifest SHA256:
  `0a0ced3d0720db7bedb4ebcc42f98162a687d2a4d5d785b8cc123cae777ef9c7`;
- reviewed Phase 3 builder SHA256:
  `3c15440d30e5cd14f320c6a1bc0d1639e89b0d878a8970284b5eb7bb58f87166`;
- transitive Phase 2 ext4 helper SHA256:
  `8b44e922aba9efdf8b6877c98d6d3395c4ec34a6d6d5e47247aa3c73d7b689a1`;
- combined Phase 3/keying tests: `17/17 PASS`;
- Python compilation and audit-only source contract: PASS;
- non-reflink copy requested, new inode proved, private mode 0600;
- exact service and return-arm hashes retained;
- runtime, host-key, service, and display marker paths absent;
- read-only `e2fsck` return code: `0`; and
- materializer size/SHA stable from opening through post-keying validation.

Credential bytes were not printed, copied into tracked evidence, or reviewed.
Only private metadata and hashes were reconciled.

## Independent capability review

The subagent receipt is
`docs/reports/A90_PHASE3_NETWORK_SSH_KEYED_ROOTFS_INDEPENDENT_REVIEW_2026-08-03.json`,
SHA256
`79ce2478276a8ca6fdb1283dae460940e9d3ae4894ba60ab37f2da7d9da98dc5`.
It records `PASS_GO`, zero unresolved findings, and unchanged permanent
boundaries.

The review closed canonical run-ID compatibility, exact key-generation and
zero-authority validator coverage, pre/post materializer source drift, the
transitive Phase 2 ext4 helper pin, dangling key-path symlinks, and exclusion
of stale sequence `-01` evidence.

This `PASS_GO` qualifies the reusable key-materialization capability. It is not
repeated per manifest, qualification, ordinal, or campaign unless the named
execution-critical closure or reviewed semantics change, or a new hazard or
incident occurs.

## Boundaries

This unit performed no device or network contact, staging, payload transfer,
partition write, flash, reboot, D1, or F1 action and grants none of those
authorities. The keyed rootfs has not yet run on A90. The separately attached
Samsung Android device and S22+ were untouched.
