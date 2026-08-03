# A90 Phase 3 Debian Network and SSH Ownership H0 Qualification

Date: 2026-08-03
Target: Samsung Galaxy A90 5G only
Tier: H0
Decision: `HOST_PASS_CAPABILITY_PASS_GO`

## Bounded capability

This unit replaces the Phase 2 monolithic firstboot service setup with an
explicit Debian sysvinit sequence while retaining the exact proved Phase 2
display image and V3405 automatic-return supervisor:

1. `/etc/a90-d3-firstboot` arms the exact 120-second V3405 return supervisor
   before any service work, verifies `/usr/sbin/init` as PID1, and publishes an
   atomic return marker.
2. sysvinit runs `/usr/local/sbin/a90-debian-network-ssh-v1` as a runlevel-2
   `wait` action before the existing display launcher.
3. The service checks the exact key files and metadata before a network effect,
   configures and verifies one `ncm0` address and peer route with bounded host
   tools, starts Dropbear with public-key-only authentication and forwarding
   disabled, then verifies its PID, executable, and exact listener.
4. Success and failure are distinct atomic `/run/a90-services` markers. A
   post-start validation failure stops only the exact newly started Dropbear
   child with bounded TERM/KILL verification, removes a newly generated host
   key, and restores only NCM link/address/route state introduced by this
   action. Cleanup observer errors are recorded as failure, never as absence.
   The already armed return supervisor remains the terminal recovery path.

This is a host qualification of the immutable rootfs closure. It is not a live
proof that the new profile has run on A90.

## Exact source closure

| Input | SHA256 |
|---|---|
| `a90_debian_return_arm_v1.sh` | `e83ede7fb430de98881ff7b9d18e8127bfc8bc19e4707d9ccf78410ac555faf3` |
| `a90_debian_network_ssh_v1.sh` | `b52b7306d928d0a7275af70f16ff44d578a8440260828343eefa2a204bdc8859` |
| Phase 3 `inittab` | `b5cf75145bf87bd7a96fd8d953413e0e9fb3ebaf62c2ac76e7c7050e2083a9ec` |
| Phase 3 stage record | `ee008742dbe031119b9d41cae40d47291c0c75577417354cbe93a992d6e28512` |
| Phase 3 rootfs builder | `3c15440d30e5cd14f320c6a1bc0d1639e89b0d878a8970284b5eb7bb58f87166` |
| retained Phase 2 builder | `8b44e922aba9efdf8b6877c98d6d3395c4ec34a6d6d5e47247aa3c73d7b689a1` |
| retained V3405 return builder | `fec5e2582eae5942b209c7517ebe952127e83257fe2e98e34690dc4154880d31` |
| retained V3405 supervisor source | `dc4fae13984d458f512d9b5f88239c7e9b68cfcff29ec64d8857474a1a49e8bb` |

Manifest SHA256:
`0a0ced3d0720db7bedb4ebcc42f98162a687d2a4d5d785b8cc123cae777ef9c7`.

## Immutable A/B evidence

The absent-only private build is
`workspace/private/outputs/server-distro/a90-phase3-network-ssh-v1-ab-05-20260803/`.

- receipt SHA256:
  `93b644eaad41181bda40ad3e0a93a1c21e82447fe006ccffcbfd06bbf628a6bf`;
- A and B image SHA256:
  `8c4167f66bd339d49bd31625cf419e3551930fa331e2964d544eaba96799d5bd`;
- both images are exactly 2 GiB with label `PHASE3NETSSHV1`;
- both read-only `e2fsck` results are zero;
- the Phase 2 base, return-supervisor binary, display presenter, and display
  launcher remained exact;
- runtime host key, `authorized_keys`, and success/failure markers remain
  absent from the clean image; and
- the receipt records `candidate_authority=false`, `device_action=false`, and
  `flash=false`.

The earlier private `ab-01` through `ab-04` outputs predate the final exact
child/listener binding and verified failure-restore semantics. They are
superseded and are not part of this qualification or review closure.

## Focused validation

The following passed against the final closure:

```text
python3 -m py_compile prepare_phase3_network_ssh_v1_rootfs.py test_a90_phase3_network_ssh_v1.py
/bin/sh -n a90_debian_return_arm_v1.sh
/bin/sh -n a90_debian_network_ssh_v1.sh
python3 -m unittest tests.test_a90_phase3_network_ssh_v1
.........
Ran 9 tests
OK
git diff --check
```

Fault tests reject changed return timing, service work in the return-arm script,
unbounded PID polling, non-replacing address or route operations, weakened
Dropbear flags, a missing foreground-child or PID/listener binding, missing
TERM/KILL or NCM cleanup, cleanup readback observer failures disguised as
absence, missing PID1 proof, changed ready schema, and changed sysvinit
serialization.

The retained Phase 2 display/keying tests and V3405 return-supervisor tests were
also replayed after qualification: 25 Phase2/Phase3 tests and 17 V3405 tests
passed. This replay exposed and repaired one stale host-only flat-builder
closure pin left by the already reviewed Phase3-E source removal. The
`phase2-display-v1/manifest.toml` closure is now
`a348fe428484a6feec9780ce09c4f38382149d2990e3e4a818f32a76462ab9e3`,
equal to the current expanded source closure; no native source, build flag,
candidate authority, or device state changed.

Read-only inspection of the exact Dropbear binary carried by the qualified
image also found its own usage strings for `-F` (foreground/no fork), `-P`
(PID file), `-s` (disable password logins), `-j` (disable local forwarding),
and `-k` (disable remote forwarding). This is host evidence for the selected
flags, not a live service proof.

## Independent capability review

The independent subagent review closed three pre-decision findings: separate
process/listener observations did not initially prove common ownership;
failure cleanup did not initially restore and verify introduced NCM state; and
cleanup readback errors were initially indistinguishable from confirmed
absence. The final ab-05 closure binds the foreground child, PID file, process
executable, and exact listener owner; performs bounded TERM/KILL and reverse
NCM/host-key cleanup; and records every cleanup observer error as failure.

The final receipt is
`docs/reports/A90_PHASE3_DEBIAN_NETWORK_SSH_OWNERSHIP_INDEPENDENT_REVIEW_2026-08-03.json`,
SHA256
`ad5e54d9f16971f7666a9828724abbe684d3a6bd603f77a0c87bb44d0fb5a00f`.
It records `PASS_GO`, no unresolved findings, unchanged permanent boundaries,
and zero device, network, payload, partition, reboot, or flash action.

This independent `PASS_GO` is a reusable capability qualification. It is not
repeated per manifest, qualification, ordinal, or campaign unless a named
execution-critical hash or reviewed semantic changes, or a new hazard or
incident occurs. Fresh artifact, credential/keyed-image, manifest, runner, and
live tier inputs remain independently required.

## Boundaries and remaining proof

- No rootfs key was materialized for this profile.
- No candidate manifest, staging packet, approval, transfer, flash, reboot,
  handoff, service change, or live execution occurred.
- The fresh D0 performed earlier in this work unit remained read-only and used
  only the exact pinned A90 bridge. S22+ received no command.
- A live Phase 3 proof would require a separately closed keyed-image and
  execution path under the then-current contract. This H0 result grants no such
  authority.
- The reusable capability review does not qualify a keyed Phase 3 image or a
  live runner and grants no device authority.
