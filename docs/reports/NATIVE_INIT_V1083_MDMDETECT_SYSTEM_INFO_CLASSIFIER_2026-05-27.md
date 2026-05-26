# Native Init V1083 mdmdetect System Info Classifier Report

## Summary

V1083 passed. Host-only analysis of `libmdmdetect.so` confirms that the
V1082 `pm-service` exit path depends on ESOC/MSM SSR sysfs enumeration and
`/dev/subsys_%s` path synthesis inside `get_system_info()`.

This narrows the next live gate: V1084 should trace `libmdmdetect.so`
instruction offsets directly while running the same bounded PM observer. It
should identify the exact failing branch without starting Wi-Fi HAL or bringing
up Wi-Fi.

## Change

- Added `scripts/revalidation/native_wifi_mdmdetect_system_info_classifier_v1083.py`.
- Parsed V1082 evidence as the required predecessor.
- Captured `readelf`, focused strings, dynamic section, and bounded disassembly
  for `get_system_info`, `get_subsystem_info`, `esoc_supported`, and
  `get_esoc_details`.
- Wrote private evidence under
  `tmp/wifi/v1083-mdmdetect-system-info-classifier/`.

## Evidence

| item | path / value |
| --- | --- |
| classifier | `scripts/revalidation/native_wifi_mdmdetect_system_info_classifier_v1083.py` |
| plan | `docs/plans/NATIVE_INIT_V1083_MDMDETECT_SYSTEM_INFO_CLASSIFIER_PLAN_2026-05-27.md` |
| manifest | `tmp/wifi/v1083-mdmdetect-system-info-classifier/manifest.json` |
| summary | `tmp/wifi/v1083-mdmdetect-system-info-classifier/summary.md` |
| V1082 input | `tmp/wifi/v1082-pm-service-instruction-trace-live/manifest.json` |
| binary input | `tmp/wifi/v1073-host-only/vendor-extract/files/libmdmdetect.so` |

## Result

```text
decision: v1083-mdmdetect-system-info-requirements-classified
pass: True
reason: libmdmdetect get_system_info requires ESOC/MSM SSR sysfs enumeration and /dev/subsys_%s path synthesis; V1084 should trace the library branch actually failing
next: run V1084 tracefs-only libmdmdetect instruction trace under the same PM observer, with no Wi-Fi HAL or bring-up
```

## Model

`get_system_info()` follows this host-classified sequence:

1. Check the caller output pointer.
2. `stat()` `/sys/bus/esoc/devices`.
3. If the ESOC root exists, `opendir()` it and enumerate entries.
4. For supported ESOC entries, read `esoc_name`, `esoc_link`, and
   `esoc_link_info` through `get_esoc_details()`.
5. Fall back to `opendir()` `/sys/bus/msm_subsys/devices`.
6. Enumerate subsystem entries and classify `slpi`, `modem`, and `spss` through
   `get_subsystem_info()`.
7. Format `/dev/subsys_%s` device paths for recognized subsystem entries.

## Required Surface

| surface | status |
| --- | --- |
| `/sys/bus/esoc/devices` | present in binary strings |
| `/sys/bus/msm_subsys/devices` | present in binary strings |
| `/dev/subsys_%s` | present in binary strings |
| `esoc_name` | present in binary strings |
| `esoc_link` | present in binary strings |
| `esoc_link_info` | present in binary strings |
| `modem`, `slpi`, `spss` | present in binary strings |

## V1084 Trace Targets

Primary candidate offsets:

| label | offset |
| --- | --- |
| `mdm_get_system_info_entry` | `0x2c94` |
| `mdm_stat_esoc_call` | `0x2d18` |
| `mdm_esoc_stat_fail_branch` | `0x2d1c` |
| `mdm_esoc_opendir_call` | `0x2d28` |
| `mdm_esoc_supported_call` | `0x2d74` |
| `mdm_get_esoc_details_call` | `0x2d94` |
| `mdm_msm_opendir_call` | `0x2de8` |
| `mdm_get_subsystem_info_nonmodem_call` | `0x2ee8` |
| `mdm_get_subsystem_info_modem_call` | `0x2f1c` |
| `mdm_success_return` | `0x2f3c` |
| `mdm_failure_return_after_info` | `0x2fec` |

All emitted offsets are 4-byte aligned for ARM64 tracefs uprobes.

## Safety

- `device_command_executed=False`.
- `tracefs_write_executed=False`.
- `pm_actor_executed=False`.
- `bpf_attach_executed=False`.
- `wifi_hal_start_executed=False`.
- `wifi_bringup_executed=False`.
- `scan_connect_executed=False`.
- `credential_use_executed=False`.
- `dhcp_route_executed=False`.
- `external_ping_executed=False`.
- `partition_write_executed=False`.
- `flash_executed=False`.
- `reboot_executed=False`.

## Interpretation

The original V1071 BPF-uprobe direction was useful as a starting point, but
V1079-V1082 already narrowed the failure below the PM-service process boundary:
`pm-service` reaches `libmdmdetect::get_system_info()` and exits because that
call fails. V1083 shows what that library expects from Android state. The next
live experiment should not retry the whole Wi-Fi stack; it should trace the
specific `libmdmdetect.so` branches and record whether the failure is ESOC
enumeration, MSM subsystem enumeration, or subsystem path synthesis.
