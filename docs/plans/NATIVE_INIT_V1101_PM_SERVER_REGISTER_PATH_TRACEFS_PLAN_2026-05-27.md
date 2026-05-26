# Native Init V1101 PM Server Register Path Tracefs Plan

## Goal

Replay the V1095 PM provider + `pm-proxy` + bounded `cnss-daemon` observer
window while arming tracefs-only uprobes on both:

- `/mnt/vendor/lib64/libperipheral_client.so`
- `/mnt/vendor/bin/pm-service`

V1100 proved that `cnss-daemon` enters `pm_client_register` for
`peripheral="modem"` and `client="cnss-daemon"`, but the client-side register
call does not return. V1101 classifies where the server-side `pm-service`
register implementation stops.

## Scope

- Reuse deployed `a90_android_execns_probe v206`.
- Keep V1095 as the bounded PM provider predecessor gate.
- Mount vendor read-only and tracefs only for the observation window.
- Register dynamic uprobes for client-side PM register/connect entry and return.
- Register dynamic uprobes for `pm-service` register checkpoints:
  - function entry at `0x6048`
  - supported peripheral match at `0x60cc`
  - permission pass/deny at `0x60e8`/`0x6184`
  - client record construction at `0x6104`
  - state read at `0x6110`
  - add-client call/return at `0x611c`/`0x6124`
  - success/no-peripheral/return at `0x6140`/`0x6148`/`0x6048`
- Use `pm-proxy` as positive control for the same `pm-service` register path.

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
- `libperipheral_client.so` and `pm-service` are visible under the read-only
  vendor mount.
- `pm-proxy` positive control reaches server register match, permission-ok,
  add-client, register return, connect entry, and connect return.
- `cnss-daemon` client register entry is observed.
- `pm-service` server-side progress for the CNSS register request is classified
  as one of:
  - missing server register entry,
  - no supported peripheral,
  - permission denied,
  - no return at the last observed checkpoint,
  - server returned but client-side register still blocked,
  - server/client register returned but connect is missing.
- Wi-Fi HAL/start/connect/link-up/credential/DHCP/external ping remain false.

## Decision Rules

- A CNSS server register entry with no later match means the blocker is inside
  the earliest `pm-service` register argument/peripheral resolution path.
- A permission-denied checkpoint means the blocker is native PM actor UID/domain
  authorization.
- A no-peripheral checkpoint means the blocker is PM service peripheral table
  initialization.
- A server register return without client register return means Binder reply or
  client-side wait handling is the next target.
- A client register return without connect means `cnss-daemon` callsite state
  after PM registration is the next target.
