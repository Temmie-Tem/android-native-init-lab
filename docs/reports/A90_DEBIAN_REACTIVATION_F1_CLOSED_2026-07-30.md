# A90 Debian Reactivation F1 Closed

Date: 2026-07-30 KST

Status:
`NO_PROOF_DEBIAN_HANDOFF_CANDIDATE_ROLLED_BACK; TRANSACTION_CLOSED`

## Scope

This report records one authorized A90 V3402 checked boot-only candidate
transfer, its bounded SD-backed Debian handoff observation, the mandatory exact
V2321 rollback, and final health.

Raw device and host evidence remains under `workspace/private/`. This report
contains no device serial, USB identity, filesystem UUID, network address,
credential, or raw log.

## Exact transaction

- run ID: `a90-debian-reactivation-f1-20260730-01`;
- prepared-manifest SHA256:
  `ba4f0f285fc7ac813caa9249e9534432f675c72008e7fb3efcc20d633de44a99`;
- checked transfer helper SHA256:
  `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53`;
- V3402 candidate SHA256:
  `57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1`;
- exact V2321 rollback SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`;
- initial SD-backed Debian image SHA256:
  `648d7a6bc4b47106b81595c016ebad896067cd0dd3558e75adea24bc3cced8c1`.

The connected read-only preflight reopened the exact manifest, candidate,
rollback, helper, target selection, current V2321 health, empty pstore, and
SD-rootfs identity before approval. Generic serial discovery was ambiguous
because another device was connected, so every recovery transition required
one endpoint on the already selected A90 physical topology.

## Candidate transfer

The checked helper transferred V3402 to `boot` exactly once:

- local image SHA matched;
- recovery-side staged image SHA matched;
- boot prefix readback SHA matched;
- exact version
  `0.11.158 build=v3402-dpublic-hud-presenter-restart-policy` appeared; and
- candidate selftest reported `pass=12 warn=1 fail=0`.

The candidate was not replayed.

## First Debian handoff

Immediately before handoff, the candidate recomputed the complete 2 GiB
SD-rootfs SHA and matched the manifest.

The exact `switch-root-to-distro` path then proved:

1. the manifest-bound rootfs SHA matched;
2. the loop node was created and attached;
3. the ext4 rootfs mounted read-write;
4. `/sbin/init` was present and executable; and
5. the first display owner was terminated.

The remaining display owner did not release within the bounded cleanup. The
command returned `-EBUSY` before moving core mounts or executing
`switch_root`. The failure path unmounted the rootfs, detached the loop, and
removed the transient loop node. V3402 remained healthy.

There was no `exec_switch_root_now` marker. This attempt does not prove Debian
PID1.

## Immutable-rootfs stop

The failure exposed an ordering hazard in the current D3 implementation:

```text
rootfs SHA check
-> loop attach
-> ext4 rw mount
-> init validation
-> display-owner cleanup
-> switch_root
```

Although the first attempt stopped before `switch_root`, the ext4
mount/unmount updated filesystem bytes. The next exact read reported SHA256:

`7eb159c13e9112761d807e423e71fb970c265559022861d7dc6aac782551826a`

The one bounded corrected handoff retained the original manifest-bound SHA. It
therefore failed closed at `expected_sha_match=0` before loop attachment or
mount. The changed image was not accepted, no new SHA was substituted, and no
further handoff was attempted.

This is the load-bearing result: display cleanup occurs too late to preserve an
immutable retry input. A pre-`switch_root` display failure can consume the
rootfs identity even though Debian never becomes PID1.

## Rollback and final health

Rollback recovery reidentified exactly one endpoint on the same A90 physical
topology. The checked helper transferred the exact V2321 image once:

- local and recovery-side image SHA matched;
- boot prefix readback SHA matched;
- exact version `0.9.285 build=v2321-usb-clean-identity-rodata` appeared; and
- selftest reported `pass=11 warn=1 fail=0`.

Final bounded checks passed for:

- `BOOT OK`;
- empty pstore;
- serial and NCM readiness;
- the exact selected A90 bridge; and
- absence of a recovery endpoint.

Internal userdata was not mounted, written, formatted, or flashed. The only
partition payloads were the approved candidate and mandatory rollback writes
to `boot`.

## Evidence closure

Private evidence is under:

`workspace/private/runs/server-distro/a90-debian-reactivation-f1-20260730-01/`

The append-only journal has 17 records, sequence `0..16`, and ends in
`CLOSED`. The candidate and rollback transfer counts are `1/1`; candidate
replay is false.

The structured result SHA256 is:

`dd0ab182fb8bd00c7a6dd5b534d1ff7d5dafb144641525dea2ba2af2bc2b0cd0`

The canonical timeline SHA256 is:

`c90f53299f417e0a1bdd70b33604e565fb6d50cab738d8a4581742cbeec613d1`

The timeline contains only the canonical eight events:

```json
{
  "events": [
    {"name": "live_session_start", "timestamp_utc": "2026-07-30T10:25:35Z"},
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-30T10:28:02Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-30T10:28:03Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-30T10:28:37Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-30T10:36:14Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-30T10:36:15Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-30T10:36:49Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-30T10:38:17Z"}
  ]
}
```

## Disposition

The approval is consumed and the transaction is closed. Do not replay V3402,
reuse the manifest, or accept the changed SD-rootfs SHA for a later live run.

The selected successor is host-only:

1. move bounded display-owner cleanup before loop attachment and rw mount;
2. prove every pre-`switch_root` failure leaves the immutable rootfs input
   byte-identical;
3. use a fresh versioned candidate and a fresh rootfs input;
4. rerun focused static/fault validation; and
5. require a new exact target binding, rollback check, manifest, and approval
   before any later device action.
