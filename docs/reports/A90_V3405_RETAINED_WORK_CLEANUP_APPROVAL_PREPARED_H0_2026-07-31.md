# A90 V3405 Retained Work-Copy Cleanup Approval Prepared

Date: 2026-07-31

Status: `H0_CLEANUP_APPROVAL_PREPARED_AWAITING_EXACT_OPERATOR_ACK`

## Scope

This unit prepared the V3405 Debian rootfs and observer, created a dedicated
host NCM profile, and ran fresh connected D0 against the exact A90. It did not
stage a rootfs, unlink a device file, reboot, hand off PID1, transfer a boot
image, or authorize F1.

The separately connected S22+ received no command.

## Host preparation

The new run-local observer key was inserted into a new-inode clone of the
reviewed V3405 diagnostic rootfs. The source remained byte-identical. The
keyed 2 GiB ext4 image passed read-only `e2fsck`, retained label
`A90D3V3405`, and has SHA256:

```text
abde672d158e706727c0726ee9c212d466ab514e4b453e219c2eae9c291259c5
```

Its firstboot script, V3405 return supervisor, and stage contract hashes match
the reviewed H0 image. The private observer key and image remain mode `0600`.

The dedicated `a90-v3405-ncm` NetworkManager profile was cloned from the
working A90-only profile, given the same USB-local manual route with no
gateway, DNS, default route, IPv6, or autoconnect, and activated on the single
Samsung `cdc_ncm` interface. The prior V3404 profile was preserved. Direct
route, expected host CIDR, and device reachability passed.

## Fresh D0 result and blocker

Fresh bounded reads proved:

- one exact A90 target and no command to the other connected device;
- exact V2321 version/build;
- selftest `fail=0`;
- pstore `entries=0`;
- the new V3405 source path absent; and
- the new run-owned stage path absent.

The fixed `d3-handoff-work.img` path was still present. A bounded read proved
regular-file type, mode `0600`, size 2 GiB, and SHA256:

```text
ef45a234db2b3a28ecd8bfddef5932ba87298a266247f304f288712aa6e36d02
```

That size and digest exactly match the private V3404 postmortem image already
preserved on the host. Nothing was deleted.

One initial read-only status command was captured by the still-running V3404
bridge before it was rotated to a V3405 D0 capture. This appended only a
post-closure read to that private raw capture; no closed structured result,
journal, timeline, device state, or approval changed.

## Proportional cleanup contract

Deleting the retained SD file persists across reboot, so the risk-tier
contract does not permit treating it as ordinary transient D1. A separate
minimal one-shot helper was implemented instead of changing the F1 runner.

The helper requires:

- a private mode-`0600` manifest, connected D0 result, and host preservation;
- the exact target USB identity and one exact local bridge process;
- exact V2321 health, selftest, and empty pstore immediately before dispatch;
- the fixed work path, regular type, single link, mode, size, and SHA256;
- absence of both adjacent V3405 paths, including dangling symlinks;
- proof that the work image is not mounted or a loop backing file;
- approval-bound exact `15/180` second read/cleanup timeouts;
- fsynced intent and dispatch records before contact; and
- exactly one non-recursive `/bin/busybox rm --` dispatch with unsafe retry
  disabled.

A lost response permits read-only reconciliation only. The unlink command is
never retransmitted. Cleanup effect and post-health proof are separate; an
absent path with unproved health closes as a stop, not a pass.

## Validation and review

Final reviewed identities:

```text
helper  78f4cc9962331731e4db658987c9dbe61b70724f49c90a17b62606d8948489a7
tests   b7ee3cc1bb4983d120093af7e71bef56b9358062ae2ccf0f7435b4414cee5f71
```

Validation passed:

- focused host-only tests: `15/15`;
- Python `py_compile`;
- `git diff --check`; and
- independent safety review: `GO`, with no remaining Critical, High, or
  Medium finding.

The final private cleanup manifest SHA256 is:

```text
b882109ff487a87c28816a92e0db1d579326f8e81167247d559ce28d5023c24e
```

Host-only inspection reported approval-preparation readiness. One exclusive
mode-`0600` approval receipt was created with `device_contact=false`,
`device_write=false`, and `live_authorized=false`. Its exact token remains
private until operator acknowledgement.

## Next gate

The next action is one fresh exact acknowledgement of the prepared cleanup
token. It authorizes only the exact hash-gated retained-work unlink and bounded
post-health checks. It is not F1 authority.

After successful cleanup, fresh D0 must prove all three paths absent. Only then
may a separate final V3405 F1 manifest and fresh F1 approval be prepared.
