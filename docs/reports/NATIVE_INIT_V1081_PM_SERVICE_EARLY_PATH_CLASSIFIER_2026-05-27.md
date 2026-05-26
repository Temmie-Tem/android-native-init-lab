# Native Init V1081 PM Service Early Path Classifier Report

## Summary

V1081 passed host-only. It correlates the V1080 tracefs counts with the stripped
`pm-service` disassembly and classifies the early `per_mgr` exit-255 path.

The inferred path is:

1. main candidate `0x7650` enters.
2. main creates a pipe at `0x7748`.
3. main calls helper `0x6b6c` from `0x77c8`.
4. helper calls `get_system_info` at `0x6bc0`.
5. `get_system_info` returns nonzero, so the `cbz w0, 0x6be8` success branch at
   `0x6bc4` is not taken.
6. helper logs failure at `0x6bdc`, sets return `-2` at `0x6be0`, and returns.
7. main observes nonzero at `0x77cc`, skips Binder/QMI setup, closes pipe fds at
   `0x77d4` and `0x77dc`, then exits with error.

This explains why V1080 saw `pipe`, `get_system_info`, `android_log`, and
`close`, but did not see Binder, QMI, property, open, access, select, or write.

## Change

- Added `scripts/revalidation/native_wifi_pm_service_early_path_classifier_v1081.py`.
- Wrote host-only evidence to
  `tmp/wifi/v1081-pm-service-early-path-classifier/manifest.json`.

## Evidence

| item | path |
| --- | --- |
| runner | `scripts/revalidation/native_wifi_pm_service_early_path_classifier_v1081.py` |
| manifest | `tmp/wifi/v1081-pm-service-early-path-classifier/manifest.json` |
| summary | `tmp/wifi/v1081-pm-service-early-path-classifier/summary.md` |
| main disassembly | `tmp/wifi/v1081-pm-service-early-path-classifier/analysis/pm-service-main-early-disasm.txt` |
| helper disassembly | `tmp/wifi/v1081-pm-service-early-path-classifier/analysis/pm-service-helper-get-system-info-disasm.txt` |

## Result

```text
decision: v1081-pm-service-early-exit-path-classified
pass: True
reason: per_mgr exits after get_system_info failure path and before Binder/QMI/open server setup
next: use instruction-level tracefs uprobes at helper branch/return offsets in V1082
```

## V1082 Candidate Offsets

| label | offset |
| --- | --- |
| `main_entry` | `0x7650` |
| `main_pipe_call` | `0x7748` |
| `main_helper_call` | `0x77c8` |
| `main_helper_return_branch` | `0x77cc` |
| `main_error_close0` | `0x77d4` |
| `main_error_close1` | `0x77dc` |
| `main_binder_driver_call` | `0x78e0` |
| `helper_entry` | `0x6b6c` |
| `helper_get_system_info_call` | `0x6bc0` |
| `helper_get_system_info_branch` | `0x6bc4` |
| `helper_get_system_info_failure_log` | `0x6bdc` |
| `helper_get_system_info_failure_return` | `0x6be0` |
| `helper_get_system_info_success_path` | `0x6be8` |

## Safety

V1081 was host-only. It executed no device command, no tracefs write, no PM
actor, no Wi-Fi action, no partition write, no flash, and no reboot.

## Interpretation

The immediate blocker is likely not Binder, QMI, or missing `/dev/subsys_modem`
fd creation itself. The current path fails earlier because `get_system_info`
does not provide usable peripheral information in the native namespace. V1082
should confirm this branch with instruction-level tracefs uprobes and then
classify what `get_system_info` expects from Android state.
