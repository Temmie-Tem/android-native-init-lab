# A90 H17 post-root-mount native fallback incident

Date: 2026-08-10
Target: operator-owned Samsung Galaxy A90 5G only
Incident: `H17_POST_ROOT_MOUNT_NATIVE_FALLBACK`

## Result

H17 D1 run01 consumed exactly one arm-plus-reboot action and must never be
replayed. The persistent-server observer returned no proof, but later bounded
read-only native evidence established that the automatic handoff did run and
then cleanly returned to native-init.

The same boot's retained sequence is:

1. durable H17 latch and same-intent on-device evidence publication;
2. `handoff_begin`;
3. initial userdata identity verification;
4. `display_release_done`;
5. post-display userdata identity verification;
6. read-only `root_mounted`;
7. no `writable_set_ready` and no `switch_root_exec`;
8. `cleanup_clean=1 root_mounted=0 recovery_required=0
   userdata_unchanged=1 userdata_write=0`;
9. `handoff_failed_native`, `auto_handoff_returned_native`, and
   `native_fallback_ready`.

The operator-visible screen transition matches this sequence: native-init,
black during strict display release, then native-init again with `E1`. `E1`
is the outer `errno=1`; it is not a durable discriminator for the failing
inner helper.

## Safety disposition

The private diagnosis proves exact H17 `0.11.185`, self-test `11/1/0`, PID 1
guard `12/0/0`, native HUD and USB-local NCM/tcpctl restored, retained exact
`binding=1 enable=1 latch=1`, zero candidate replay, and no new payload,
partition, or userdata write. Cleanup reported the UFS root unmounted and the
same userdata identity unchanged. The device is operationally native again,
but the durable D1 journal remains `HEALTH_PENDING_PERSISTENT_DEBIAN` until an
incident-specific finalizer appends exact final health and close records.

## Finalizer boundary

The finalizer is read-only on the device and append-only on the host journal.
It must bind the exact five-record prefix and the exact private diagnosis, then
freshly prove:

- exact A90/H17 health and unique target;
- `binding=1 enable=1 latch=1`;
- enable, latch, and on-device evidence all carry the consumed intent;
- one exact failed-handoff benchmark segment ending in native fallback;
- exact clean-restoration markers with `root_mounted=0`,
  `recovery_required=0`, and `userdata_write=0`; and
- the sole runtime-resolved userdata partition is currently unmounted.

It may not claim persistent Debian, a successful `switch_root`, automatic
success return, or operator physical return. It may not arm, reboot, mount,
handoff, start or stop services, clear state, transfer a payload, flash, or
write userdata. Missing or contradictory evidence leaves the journal open and
does not replay the action.

The exact terminal is
`REFUTED_H17_PERSISTENT_SERVER_NATIVE_FALLBACK_HEALTHY`. `REFUTED` applies to
the attempted persistent-server transition, not to device health: the same
terminal separately establishes exact native `RESIDENT_HEALTHY`. The finalizer
is an incident-specific adapter whose execution closure excludes the consumed
H17 D1 runner. It validates the five predecessor records and private diagnosis
by exact SHA256, requires a fresh attended read-only approval, and permits only
an identical host-only `closed` append after a durable `final-health` crash.

## Successor diagnostic boundary

The current raw log cannot identify which helper failed after `root_mounted`
and before `writable_set_ready`, because the helper-specific stop strings were
console-only while the persistent log retained only the aggregate cleanup
result. A later boot candidate must persist a bounded stage identifier and
return code for each post-root-mount step before another D1 is considered:
root content verification, writable-set mount/verify, observer-auth overlay,
firstboot overlay, persistent-HUD start/validation, evidence bind, and Wi-Fi
handoff bind. The roughly eight-second interval makes persistent-HUD startup
the leading source hypothesis, not proof.

S22+ evidence, commands, approvals, artifacts, and recovery are outside this
incident and must remain untouched.
