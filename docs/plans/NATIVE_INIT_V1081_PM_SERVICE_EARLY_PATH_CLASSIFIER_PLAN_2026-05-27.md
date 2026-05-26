# Native Init V1081 PM Service Early Path Classifier Plan

## Goal

Classify the early `pm-service` path that V1080 observed and extract concrete
instruction-level uprobe offsets for the next live proof.

## Background

V1080 showed that `pm-service` hits entry/main, `pipe`, `get_system_info`, one
Android log call, and two `close` calls, while Binder, QMI, property, open,
access, select, and write are not reached. This implies the failure path is
inside the early helper called from main before service registration begins.

## Gate

- Use only host-side files:
  - local extracted `pm-service`
  - V1080 manifest
- Disassemble:
  - main candidate region `0x7650..0x78f0`
  - helper region `0x6b6c..0x6bf0`
- Correlate observed tracefs counts with branch/call instructions.
- Produce V1082 candidate instruction offsets.

## Forbidden

- No device command.
- No tracefs write.
- No PM actor execution.
- No Wi-Fi HAL, scan/connect, credentials, DHCP, external ping, partition write,
  flash, or reboot.

## Success Criteria

- V1080 PASS evidence is present.
- The local `pm-service` binary is present.
- The classifier explains the V1080 hit/zero pattern with a coherent early
  branch path.
- Candidate instruction offsets are emitted for V1082.
