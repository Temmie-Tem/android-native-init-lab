# A90 H24 persistent-HUD bootstrap EINVAL incident

Date: 2026-08-12
Target: operator-owned Samsung Galaxy A90 5G only
Tier: prior attended D1; successor work H0
Status: `REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY`

## Incident

The exact H24 boot-only resident install completed once and established
`RESIDENT_HEALTHY`. Its separately approved D1 run then consumed exactly one
arm and one reboot. The armed boot mounted and verified the read-only UFS root
and mounted the four-file writable set, but stopped at the outer
`persistent-hud` stage with `rc=-22 errno=22` before evidence or Wi-Fi handoff
binds and before `switch_root`.

The same-intent native log proves clean restoration: the UFS root was
unmounted, userdata remained unchanged with zero writes, no payload or
partition transfer occurred, and the run closed
`REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY` with exact
native `RESIDENT_HEALTHY`. The H24 arm, reboot, and handoff attempt are consumed
and are never replayed.

H24 recorded only the outer HUD return code, so the live evidence does not
identify which private-root syscall returned `EINVAL`. `pivot_root` against
the initramfs rootfs topology is the leading source-derived hypothesis, not a
proved root cause. Treating it as proved would exceed the captured evidence.

## Disposition

The first host-only successor proposal, H25 `0.11.193`, attempted to diagnose
and replace the failing HUD bootstrap with a `chroot` path and a boot self-test.
Independent review found new execution-critical hazards before qualification:
the old mount graph remained available as a namespace capability, the self-test
could leave parent mount state or alter an unowned fixed directory, its result
could be rerun and overwritten, and several cleanup and receipt paths were not
fail closed. H25 is therefore `NO_GO_RETIRED`. It never gained a runner,
connected D0, approval, transfer, reboot, or handoff authority.

The next design direction removes persistent native HUD from the headless
server's critical handoff path instead of patching H25. A fresh successor may
prove headless Debian PID 1, authenticated SSH, minimal Debian `/dev`, final
Wi-Fi, and persistent service health while remaining
`HEALTH_PENDING_PERSISTENT_DEBIAN`; it makes no display claim. Only an attended
return or recovery and exact native checks can close `RESIDENT_HEALTHY`.
Display can return later as a separately qualified optional capability,
preferably owned by Debian. The H24 attempt remains consumed and H25 identity,
paths, artifacts, and evidence remain retired.

## Evidence boundary

The incident facts come from the immutable H24 F1/D1 journals and captured
same-intent native log under `workspace/private/`. This report contains no raw
device identifiers, credentials, network identifiers, or private log bytes.
H25 implementation and build validation used no device, `/dev`, USB, network,
flash, reboot, handoff, S22+, or S20+ contact. Its separate host-design incident
is recorded in
`A90_H25_HUD_CHROOT_AND_SELFTEST_REPLAY_HOST_INCIDENT_2026-08-12.md`.
