# Native Init V1103 PM Server Name Helper Tracefs Plan

## Goal

Replay the V1095 PM provider + `pm-proxy` + bounded `cnss-daemon` observer
window while arming tracefs-only instruction uprobes inside `pm-service` helper
`0x9538`.

V1102 proved that the CNSS register path reaches the second/modem supported
peripheral entry and then stops at the helper call. V1103 classifies whether
that helper blocks inside `pthread_mutex_lock(entry + 0x18)`.

## Scope

- Reuse deployed `a90_android_execns_probe v206`.
- Require V1102 predecessor evidence.
- Mount vendor read-only and tracefs only for the observation window.
- Keep `pm-proxy` as positive control for the same helper and mutex.
- Trace client PM register/connect entry/return in `libperipheral_client.so`.
- Trace `pm-service` register list iteration around `0x6094`..`0x60cc`.
- Trace helper `0x9538`:
  - entry pointer at `0x9538`
  - mutex address derivation at `0x9544`
  - `pthread_mutex_lock` call at `0x9550`
  - lock return at `0x9554`
  - unlock and helper return path at `0x9558`..`0x9560`

## Guardrails

- No BPF attach; this gate uses tracefs dynamic uprobes only.
- No `mdm_helper`.
- No Wi-Fi HAL, supplicant, hostapd, scan, connect, DHCP, route, credential use,
  or external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl, GPIO write, partition write, flash,
  or reboot.
- Tracefs events must be disabled and removed during cleanup.

## Success Criteria

- V1102 predecessor manifest is present and accepted.
- Remote helper sha/usage match `a90_android_execns_probe v206`.
- `libperipheral_client.so` and `pm-service` are visible under the read-only
  vendor mount.
- `pm-proxy` positive control locks and unlocks both `SDX50M` and `modem`
  peripheral record mutexes, then completes register/connect.
- `cnss-daemon` second/modem helper progress is classified by the last
  chronological checkpoint before bounded cleanup.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- Stop before `pm_server_name_helper_lock_call` means helper setup or mutex
  address derivation is the blocker.
- Stop at `pm_server_name_helper_lock_call` means the blocker is the
  `pthread_mutex_lock(entry + 0x18)` wait.
- Reaching `pm_server_name_helper_lock_after` but not helper return means the
  blocker is inside unlock/return handling.
- Reaching `pm_server_register_match` moves the target below supported
  peripheral matching.
