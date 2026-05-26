# Native Init V1099 PM Server Transaction Code Tracefs Plan

## Goal

Replay the V1095 PM provider + `pm-proxy` + bounded `cnss-daemon` observer
window while arming tracefs-only dynamic uprobes on
`/mnt/vendor/lib64/libperipheral_client.so` with ARM64 register fetchargs.

V1096 proved that `cnss-daemon` enters the PM client path. V1097 proved that the
request reaches the `pm-service` Binder server. V1098 proved that the
`pm-service` QMI loop registers/selects/unregisters but does not send or handle
QMI messages during the CNSS request window. V1099 classifies which Binder
transaction codes are actually delivered to the PM server.

## Scope

- Reuse deployed `a90_android_execns_probe v206`.
- Keep V1095 as the predecessor gate.
- Mount tracefs and vendor read-only only for the bounded observation window.
- Register dynamic uprobes for PM client calls and PM server `onTransact`
  dispatch:
  - `pm_client_register`
  - `pm_register_connect`
  - `pm_client_connect`
  - `pm_client_ack`
  - `pm_server_ontransact`
  - `pm_server_ontransact_thunk`
- Capture `code=%x1` and `flags=%x4` on the PM server transaction probes.

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
- `/mnt/vendor/lib64/libperipheral_client.so` is visible from the read-only
  vendor mount.
- Tracefs register/enable/disable/remove operations complete without failures.
- The bounded child reaches the CNSS phase.
- `pm-service` Binder server transaction codes are captured.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- If `cnss-daemon` produces the same transaction codes as `pm-proxy`, the next
  gate should classify why `pm-service` does not convert those transactions into
  lower QMI/eSoC action.
- If `cnss-daemon` only produces register/listener transactions while `pm-proxy`
  produces connect/ack transactions, the next gate should classify why the CNSS
  path does not issue the actionable PM connect/vote request.
- If transaction codes are missing despite `onTransact` hits, the next gate
  should repair tracefs fetcharg capture or fall back to callsite-level
  classification.
