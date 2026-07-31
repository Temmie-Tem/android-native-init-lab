# A90 V3405 Retained Work-Copy Cleanup Closure and F1 Approval Prepared

Date: 2026-07-31

Status: `CLEANUP_PASS_F1_APPROVAL_CONSUMED_BY_CLOSED_SUCCESSOR`

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

## Pre-dispatch host rejection and correction

The first acknowledged cleanup token did not reach a device command or create
the live transaction directory. The helper stopped in its host target
continuity gate because the prepared manifest had hashed the tty realpath with
one trailing newline, while the reviewed helper correctly hashes the exact
string without a newline.

The first run closed as a host pre-dispatch rejection with:

- cleanup dispatch count `0`;
- device contact and device write both false;
- no transaction directory;
- no unlink, staging, reboot, or payload action; and
- its approval permanently superseded rather than rebound.

Fresh D0 then reconfirmed exact V2321 health, selftest `fail=0`, empty pstore,
the same exact retained-work size/hash, both adjacent paths absent, the
dedicated NCM profile active, and no command to the other connected device.

A successor manifest binds the exact realpath string without a trailing
newline. Its SHA256 is:

```text
217280b8234f3b46a18d45c9c4d6f545d9bec598a31bbbe4d8d572534d747d85
```

Host-only inspection reported approval-preparation readiness. One exclusive
mode-`0600` approval receipt was created with `device_contact=false`,
`device_write=false`, and `live_authorized=false`. Its exact token remains
private until operator acknowledgement. The earlier token is not reusable.

## Approved cleanup result

The corrected cleanup approval was acknowledged. Before dispatch, the helper
reopened the exact target, revalidated V2321 health, rehashed the exact 2 GiB
work image and host preservation, rechecked both adjacent paths, and proved
that the image was neither mounted nor used as a loop backing file.

The result is:

```text
outcome=PASS_EXACT_RETAINED_WORK_COPY_UNLINKED
dispatch_count=1
cleanup_retransmitted=false
response_proven=true
effect_proven=true
post_health_proven=true
```

No payload, flash, reboot, rootfs staging, or command to the other connected
device occurred in the cleanup transaction. The exact host postmortem copy
remains preserved.

## Fresh F1 closure

After cleanup, a separate fresh D0 proved:

- exact V2321 version/build and selftest `fail=0`;
- pstore `entries=0`;
- the dedicated NCM profile active and reachable; and
- the V3405 final source, fixed work image, and run-owned stage path all
  absent, including symlink absence.

The final manifest binds the exact V3404 boot candidate, V2321 rollback,
V3405 keyed rootfs, current staging adapter and orchestrator, run-local
observer key, same-current-ACM NCM rebind, retained-pmsg capture/cleanup,
connected D0, path preflight, and recovery evidence.

Both host-only inspectors returned zero contract issues. The final V3405 F1
manifest SHA256 is:

```text
9db8e9870cbce47d98ac2efbdf363eb42efc1db48874bca58231b632506eff97
```

One exclusive F1 approval receipt was prepared with `device_contact=false`,
`device_write=false`, `f1_authorized=false`, and `live_authorized=false`.

## Successor disposition

The prepared F1 token was acknowledged exactly once and consumed by run
`a90-v3405-debian-f1-20260731-01`. The candidate, attended handoff, mandatory
rollback, and final health closure are recorded separately in
`A90_V3405_DEBIAN_PID1_F1_CLOSED_2026-07-31.md`.

No cleanup, F1, or attended-continuation approval is reusable.
