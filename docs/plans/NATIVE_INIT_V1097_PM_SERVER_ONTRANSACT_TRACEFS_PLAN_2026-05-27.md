# Native Init V1097 PM Server onTransact Tracefs Plan

## Goal

Replay the V1095 PM provider + `pm-proxy` + bounded `cnss-daemon` observer
window while arming tracefs-only dynamic uprobes on
`libperipheral_client.so` server-side Binder symbols. The purpose is to
classify whether the `vendor.qcom.PeripheralManager` server receives Binder
transactions after the V1096-proven client requests.

## Scope

- Reuse deployed `a90_android_execns_probe v206`.
- Keep V1095 as the predecessor gate.
- Mount tracefs and vendor read-only only for the bounded observation window.
- Register dynamic uprobes on:
  - `pm_client_register`
  - `pm_register_connect`
  - `pm_client_connect`
  - `pm_client_event_acknowledge`
  - `BnPeripheralManager::onTransact`
  - the non-virtual `BnPeripheralManager::onTransact` thunk
- Map server hits back to `pm-service` by matching Binder thread comm names
  such as `Binder:<pm-service-pid>_*`.

## Guardrails

- No BPF attach; this gate uses tracefs dynamic uprobes only.
- No `mdm_helper`.
- No Wi-Fi HAL, supplicant, hostapd, scan, connect, DHCP, route, credential use,
  or external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl, GPIO write, partition write, flash,
  or reboot.
- Tracefs events must be disabled and removed during cleanup.

## Success Criteria

- V1095 predecessor manifest is present and accepted.
- Remote helper sha/usage match `a90_android_execns_probe v206`.
- `libperipheral_client.so` is visible from the read-only vendor mount.
- Tracefs registers/enables/removes all events cleanly.
- The child reaches the V1095 CNSS phase.
- PM server `onTransact` hits are counted separately from client-side hits.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- `Binder:<pm-service-pid>_*` `onTransact` hits after client requests mean the
  PM Binder server receives the request; the next blocker is PM service
  vote/QMI decision or lower eSoC trigger.
- Client hits with no PM server `onTransact` mean Binder delivery or proxy
  transaction framing is still broken.
- No tracefs hits mean file/offset/inode mapping must be repaired before
  interpreting PM behavior.
