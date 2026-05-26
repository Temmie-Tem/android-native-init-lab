# Native Init V1107 PM Server Mutex Owner Classifier Plan

## Goal

Classify the owner of the modem record mutex that blocked CNSS in V1106 using
host-only analysis of the existing V1106 live evidence.

V1106 proved the CNSS Binder TID waits in `futex_wait_queue_me` on the modem
record mutex. V1107 reconstructs raw lock/unlock ownership before that wait and
maps the owner return address back to the `pm-service` binary.

## Scope

- Require V1106 predecessor evidence.
- Do not run any device command.
- Parse V1106 raw `pthread_mutex_lock@plt`/`pthread_mutex_unlock@plt` events.
- Identify the CNSS pending mutex and timestamp.
- Reconstruct lock holders before the CNSS wait by pairing lock returns with
  unlock returns per `pm-service` thread.
- Attach V1106 `/proc/<tid>/wchan` samples to the reconstructed owner and
  waiter TIDs.
- Disassemble the owner return offset from the host-staged `pm-service` ELF.

## Guardrails

- No device command, tracefs write, BPF attach, PM actor, `cnss-daemon` start,
  Wi-Fi HAL, scan/connect, DHCP, route, credential use, or external ping.
- No eSoC open/ioctl, GPIO write, partition write, flash, or reboot.
- Use only existing evidence under `tmp/wifi/v1106-*` and host-staged vendor
  binaries.

## Success Criteria

- V1106 predecessor manifest is present and accepted.
- CNSS pending mutex and TID are found.
- A pre-existing unmatched holder of the same mutex is reconstructed before the
  CNSS wait timestamp.
- Owner TID samples show a concrete blocking state.
- Owner return offset is mapped into `pm-service` disassembly.

## Decision Rules

- `v1107-modem-mutex-owner-blocked-in-subsystem-get`: owner holds the modem
  record mutex and samples in `__subsystem_get` or `_request_firmware` while
  CNSS waits in futex on the same mutex.
- `v1107-modem-mutex-owner-classified`: owner is found with a different wait
  state.
- `v1107-modem-mutex-owner-not-found`: no unmatched holder can be reconstructed;
  extend live raw event capture before interpreting owner state.
