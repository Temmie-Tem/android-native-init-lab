# Native Init V1100 CNSS PM Register Return Tracefs Plan

## Goal

Replay the V1095 PM provider + `pm-proxy` + bounded `cnss-daemon` observer
window while arming tracefs-only entry and return uprobes on
`/mnt/vendor/lib64/libperipheral_client.so`.

V1099 proved that `cnss-daemon` reaches PM server transaction code `0x1` but
does not reach `0x3` connect. V1100 classifies whether that is because
`pm_client_register` fails, blocks, or returns successfully but `cnss-daemon`
does not call `pm_client_connect`.

## Scope

- Reuse deployed `a90_android_execns_probe v206`.
- Keep V1095 as the bounded PM provider predecessor gate.
- Mount tracefs and vendor read-only only for the observation window.
- Register dynamic uprobes for:
  - `pm_client_register_entry`
  - `pm_client_register_ret`
  - `pm_register_connect_entry`
  - `pm_client_connect_entry`
  - `pm_client_connect_ret`
  - `pm_client_ack_entry`
  - PM server `onTransact` code/flag fetchargs
- Capture PM register `client`/`peripheral` strings to distinguish
  `pm-proxy` from `cnss-daemon`.

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
- Tracefs supports entry, return, and string fetchargs.
- `pm-proxy` positive control shows register return and connect return.
- `cnss-daemon` register entry is observed and classified as one of:
  - non-zero register return before connect,
  - no register return before connect,
  - zero register return but no connect,
  - connect reached with success/failure.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- `cnss-daemon` register entry with no return means PM server code `0x1`
  blocks or waits inside the register path before CNSS can call connect.
- Non-zero `cnss-daemon` register return means code `0x1` rejects the CNSS
  register request.
- Zero register return with no connect means the gap is in `cnss-daemon`
  callsite state after registration.
- A connect call means the next gate moves below transaction `0x3` into PM
  server response or lower eSoC side effects.
