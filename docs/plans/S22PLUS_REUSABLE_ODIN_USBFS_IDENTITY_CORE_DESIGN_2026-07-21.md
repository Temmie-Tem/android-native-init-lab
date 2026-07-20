# S22+ reusable Odin usbfs identity core design (2026-07-21)

## Status

Host-only implementation and static validation complete. No device contact,
Download transition, Odin execution, transfer, flash, artifact construction, or
live-policy activation occurred in this unit.

This design converts the consumed R4W1-C zero-transfer observation into a reusable
mechanical component. It does not reuse the retired observer, its acknowledgement,
or its one-shot authority.

## Problem closed

The legacy Odin transition core encoded `st_ctime_ns` into the endpoint identity.
The R4W1-C observer proved that one successful `odin4 -l` changed only
`st_atime_ns`, `st_ctime_ns`, and `st_mtime_ns`; node replacement, topology change,
and inventory change were absent. Exact comparison of the legacy identity therefore
rejected a measured listing-time metadata transition as endpoint replacement.

Removing `st_ctime_ns` from a string would hide evidence and silently weaken every
caller. The replacement design instead makes the relaxed interpretation explicit,
records the complete transition, and keeps legacy behavior as the default.

## Components

### `s22plus_odin_usbfs_identity.py`

The new module owns only usbfs node observation and comparison:

- captures `stat -> birth-time -> stat` and rejects a change around the birth-time
  read;
- resolves and opens the host `stat` executable read-only, executes that pinned FD,
  and rejects executable metadata change during each birth-time read;
- requires a direct character device with one link, usbfs major 189, and the exact
  bus/device-to-minor relation;
- requires a present, parseable nanosecond birth time;
- inventories all direct `/dev/bus/usb/BBB/DDD` nodes before and after enumeration,
  records every node transition, and fails closed on membership change, any race,
  malformed entry, unrelated-node replacement, or observation error;
- creates a canonical `usbfs-immutable-v1:<sha256>` generation identity;
- emits and validates a complete before/after transition record; and
- performs a post-receipt immutable revalidation.

The only mutable fields are exactly:

1. `st_atime_ns`
2. `st_ctime_ns`
3. `st_mtime_ns`

The immutable identity contains exactly:

- path, `st_dev`, inode, `st_rdev`, and link count;
- character-device file type, permission mode, uid, and gid;
- birth time; and
- device major and minor.

Any immutable change is an error. The allowlist is fixed in source and repeated in
every evidence record; callers cannot pass a wider list.

### `s22plus_odin_transition_core.py`

The existing common core now accepts an optional `endpoint_observer_factory` in
`enumerate_odin`, both wait functions, and ticket revalidation. A future reviewed
gate opts in with:

```python
endpoint_observer_factory=odin_core.measured_usbfs_observer
```

Without that argument, the old exact-string identity path remains unchanged. Passing
legacy identity callbacks together with the measured observer is rejected before
enumeration.

Snapshot receipt schema v2 stores `endpoint_transition_evidence` in the sealed,
hash-bound receipt. The advisory index still binds the complete receipt SHA. The
reader remains compatible with historical v1 receipts, while rejecting evidence
smuggled into a v1 payload. Endpoint generations and tickets use only the canonical
immutable digest, so allowed timestamp changes do not manufacture a new generation.

## Fail-closed sequence

For each opt-in enumeration:

1. capture a complete usbfs inventory and immutable digest for every entry;
2. run the existing bounded `odin4 -l` command;
3. snapshot every reported path and compare it with the pre-command entry;
4. reject new, missing, replaced, malformed, or immutable-changed endpoints;
5. place the full before/after node record and timestamp diff in snapshot receipt v2;
6. publish and fsync the sealed receipt and append-only index; and
7. reobserve the complete usbfs inventory and reject any post-receipt membership or
   immutable change.

The existing generation ticket must still be revalidated immediately before any
future transfer. A failed post-receipt check leaves the already-published observation
receipt as durable failure evidence and returns no usable ticket.

## Deliberately outside this core

This component does not prove or authorize:

- Samsung model, device, firmware, or verified-boot state;
- Download sysfs topology, VID/PID, descriptors, serial absence, or ADB-to-Download
  continuity;
- strict target-specific `odin4 -l` stdout/stderr shape;
- Odin executable identity or version;
- the SHA256 identity of the host birth-time `stat` executable, which a future
  qualification gate must pin even though execution is FD-bound against replacement;
- AP member list, boot-image identity, candidate semantics, or rollback identity;
- an Odin transfer, partition write, flash, candidate run, or PASS verdict; or
- any live exception or reuse of a retired acknowledgement.

A target helper must continue to bind all of those independently. In particular,
the R4W1-C observer's stable sysfs/topology proof remains evidence for design, not a
general authorization exported by this module.

## Static validation

ResourceWarning-fatal tests pass `274/274` across:

- the legacy Odin transition core;
- the new measured usbfs identity module;
- R4W1-C connected and retired live gates;
- the retired enumeration observer and both binding generators; and
- the R4W1-C watchdog carrier builder and static checker.

Focused new tests cover all three allowed timestamps, every immutable field class,
birth-time parsing and command shape, inventory races, evidence tampering, legacy-v1
receipt compatibility, mixed-mode rejection, durable v2 evidence, stable generation,
and post-receipt replacement rejection. `py_compile` and `git diff --check` also pass.
`ruff` is not installed on this host, so no Ruff result is claimed.

## Promotion path

This is reusable source, not a live-ready transfer gate. Promotion requires separate
bounded units:

1. independent adversarial review of this implementation and tests;
2. host-only qualification with exact source and test hashes;
3. a new target-specific helper that uses the opt-in mode consistently for initial
   wait, disconnect wait, and immediate pre-transfer ticket revalidation;
4. exact sysfs/topology, Odin-output, artifact, rollback, and policy binding;
5. connected read-only dry-run; and
6. only then, a separately reviewed one-shot live exception and fresh approval.

No step above is authorized by this document.
