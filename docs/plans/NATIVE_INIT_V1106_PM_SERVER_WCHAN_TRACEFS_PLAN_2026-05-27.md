# Native Init V1106 PM Server Wchan Tracefs Plan

## Goal

Replay the V1095 PM provider + `pm-proxy` + bounded `cnss-daemon` observer
window while keeping the V1105 raw mutex tracepoints and sampling
`pm-service` thread state through `/proc/<pid>/task/<tid>/wchan`.

V1105 proved that the CNSS Binder thread issues a raw
`pthread_mutex_lock@plt` call on the modem record mutex and does not receive a
matching return. V1106 classifies the live kernel wait state for that same TID.

## Scope

- Reuse deployed `a90_android_execns_probe v206`.
- Require V1105 predecessor evidence.
- Mount vendor read-only and tracefs only for the observation window.
- Keep `pm-proxy` as the positive control.
- Keep raw `pm-service` PLT checkpoints:
  - `pthread_mutex_lock@plt` at `0xa250` call/return
  - `pthread_mutex_unlock@plt` at `0xa270` call/return
- Start the child observer in the background and sample actual `pm-service`
  threads every `0.25s` while the child is running.

## Guardrails

- No BPF attach; this gate uses tracefs dynamic uprobes plus read-only `/proc`.
- No `mdm_helper`.
- No Wi-Fi HAL, supplicant, hostapd, scan, connect, DHCP, route, credential use,
  or external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl, GPIO write, partition write, flash,
  or reboot.
- Tracefs events must be disabled and removed during cleanup.

## Success Criteria

- V1105 predecessor manifest is present and accepted.
- Remote helper sha/usage match `a90_android_execns_probe v206`.
- `libperipheral_client.so` and `pm-service` are visible under the read-only
  vendor mount.
- CNSS still reaches raw `pthread_mutex_lock` on the modem record mutex.
- The matching CNSS pending TID is sampled from `/proc/<pid>/task/<tid>`.
- A `wchan`/syscall state is recorded for the pending TID.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- `v1106-cnss-raw-lock-pending-in-futex-wait`: CNSS pending TID is sampled with
  a futex wait state.
- `v1106-cnss-raw-lock-pending-wchan-captured`: CNSS pending TID is sampled, but
  the captured state is not futex-like.
- `v1106-cnss-raw-lock-pending-wchan-sample-missed`: raw pending is reproduced,
  but the matching TID was not sampled; increase sampling density or adjust
  timing before interpreting owner state.
- Any register/enable/cleanup failure, forbidden actor, Wi-Fi link, or helper
  mismatch is a failed gate requiring cleanup or predecessor repair.
