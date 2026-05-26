# Native Init V1083 mdmdetect System Info Classifier Plan

## Objective

Classify the `libmdmdetect.so::get_system_info()` requirements behind the
V1082-confirmed `pm-service` early exit. This is host-only and must produce the
next safe live trace offsets before another PM actor retry.

## Background

V1082 confirmed that `pm-service` reaches the helper call to
`get_system_info()`, takes the failure branch, logs the failure path, returns
nonzero to main, and exits before Binder/QMI setup. Therefore the next blocker
is not Binder, QMI CSI, or service-manager startup. It is the Android runtime
surface that lets `libmdmdetect` classify the modem/eSoC subsystem.

## Scope

- Parse the host-extracted `libmdmdetect.so`.
- Confirm exported symbol offsets for `get_system_info()` and related helpers.
- Extract focused sysfs/device strings.
- Disassemble only bounded function ranges.
- Produce V1084 candidate tracefs uprobe offsets.

## Inputs

| item | path |
| --- | --- |
| `libmdmdetect.so` | `tmp/wifi/v1073-host-only/vendor-extract/files/libmdmdetect.so` |
| V1082 manifest | `tmp/wifi/v1082-pm-service-instruction-trace-live/manifest.json` |

## Guardrails

- Host-only: no device command execution.
- No tracefs write, BPF attach, PM actor start, service-manager start, Wi-Fi HAL
  start, scan/connect, DHCP, route change, external ping, partition write,
  flash, or reboot.
- Keep evidence private through `a90harness.evidence`.
- Do not record Wi-Fi credentials.

## Success Criteria

- V1082 PASS evidence is present.
- Required `libmdmdetect` symbols are visible.
- Required ESOC/MSM SSR sysfs and `/dev/subsys_%s` strings are present.
- Candidate ARM64 offsets for the next live trace are 4-byte aligned.
- The report states which failure classes V1084 should separate.
