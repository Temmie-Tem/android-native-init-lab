# A90 V3406-04 resident promotion host-framing abort and rollback

## Result

Run `a90-v3406-debian-display-f1-20260801-03` is closed as:

`ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK`

The durable journal records one boot-only candidate transfer and one exact
V2321 rollback transfer. There was no candidate replay. Final V2321 health is
restored with exact version/build, `selftest fail=0`, and pstore `entries=0`.
No command was sent to the separately connected S22+.

The conservative structured result leaves `candidate_transfer_count=null` and
sets `candidate_transfer_uncertain=true` because no `candidate-boot-ready`
record was reached. The earlier durable `candidate-flashed` record separately
records one completed candidate transfer. These two facts describe different
proof boundaries and must not be collapsed.

## Observed failure

The candidate completed its checked transfer, rebooted, re-enumerated its A90
ACM interface, and exposed a native prompt. The first strict candidate-health
exchange was then interleaved with host AT probe bytes and lacked a valid
`A90P1 END` frame. This is evidence of a host serial-owner/framing failure, not
proof that the candidate image failed to boot.

The initial rollback recovery completed the exact V2321 transfer once. Its
first final-health capture also lost one side of the strict frame. Recovery was
resumed from the durable `ROLLBACK_FLASHED` record; it did not retransmit the
rollback. The resumed version, status, and selftest frames were exact and the
transaction closed healthy.

The operator-observed PC disconnect notification followed by ACM
re-enumeration is consistent with the expected reboot boundary. It is not the
failure in this run.

## Root cause boundary

The existing transient A90-only ModemManager guard does not cover the first
candidate boot-health exchange. The base F1 runner performs
`settle_observation_channel()` and `verify_candidate_health()` before it calls
the resident `promotion_tail`. The resident tail arms the guard only after that
health exchange, immediately before the later resident reboot.

Consequently, the later resident reboot corridor was designed to be guarded,
but this run stopped in the earlier unguarded candidate boot corridor. No
Debian handoff, resident reboot, or display attempt was reached.

The next candidate line must remain stopped. The next H0 change unit is to
extend the already reviewed exact A90 guard lifetime across the first
candidate reboot and health exchange, without adding a second flash owner or
replaying this candidate. Because this changes the F1 runner execution
closure, it requires focused regression and one independent safety review
before a new manifest and approval.

## Evidence identities

- Manifest SHA256: `62921192572a5b9005e963ce760b726e0d6556b9ab0396342b639342d747c92c`.
- Structured result SHA256: `10628c95f425490108c2563f25bb29f13d1b754473ec7fac64bec4a1563234ab`.
- Timeline SHA256: `2426ef1a76ad4e0f7f1a84a90dbbf6d0b27cbcce8200cd746cd91d7a40f0a571`.
- Candidate-flashed journal SHA256: `644917a7bd2af9b16ca94340cbd5a0bba0373fcfb2c011a1c18a99fc8ca1446e`.
- Rollback-flashed journal SHA256: `d729194de2c92c12aec61432c1f89a890e3a539678294a95490f013c682e59e1`.
- Final-health journal SHA256: `42e05f39b4737c89bb7323778b83cbb3f32e55ebad08d2b26fdf25dd55a315a3`.
- Closed journal SHA256: `74c64f1dbebcce73f7b6509a4dd6a1aa2f4bdb23db450b999f03170dce308acf`.

Raw flash and serial evidence remains under the private run directory. No raw
device log, target serial, recovery identifier, or payload is committed.
