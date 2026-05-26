# Native Init V1080 PM Service Tracefs Expanded Live Report

## Summary

V1080 passed. The expanded tracefs-only PLT probe shows that `pm-service` starts
and exits through a very early path: entry/main, `pipe`, `get_system_info`,
Android log, and `close` fire, but Binder, QMI server registration/event loop,
property set, access/open/select/write do not fire.

This narrows `per_mgr exit 255` substantially. The failure occurs before
`pm-service` enters Binder/QMI server setup or opens additional files through
the traced `__open_2` PLT slot.

## Change

- Added `scripts/revalidation/native_wifi_pm_service_tracefs_expanded_live_v1080.py`.
- Reused the V1079 tracefs-only collector path.
- Expanded dynamic uprobe coverage from 7 events to 15 events using the V1075
  host-classified PLT candidates.

## Evidence

| item | path / value |
| --- | --- |
| runner | `scripts/revalidation/native_wifi_pm_service_tracefs_expanded_live_v1080.py` |
| manifest | `tmp/wifi/v1080-pm-service-tracefs-expanded-live/manifest.json` |
| summary | `tmp/wifi/v1080-pm-service-tracefs-expanded-live/summary.md` |
| observer transcript | `tmp/wifi/v1080-pm-service-tracefs-expanded-live/host/pm-service-tracefs-uprobe-observer.txt` |
| cleanup mounts | `tmp/wifi/v1080-pm-service-tracefs-expanded-live/host/proc-mounts-after-cleanup.txt` |
| final selftest | `tmp/wifi/v1080-pm-service-tracefs-expanded-live/host/post-selftest-final.txt` |

## Result

```text
decision: v1080-pm-service-tracefs-uprobe-boundary-captured
pass: True
reason: entry_hit=True main_hit=True hit_count=6
next: classify PM-service callsite hits and choose the next exit-255 root-cause probe
```

## Expanded Tracefs Counts

```json
{
  "access": 0,
  "android_log": 1,
  "binder_driver": 0,
  "binder_service_manager": 0,
  "close": 2,
  "elf_entry": 1,
  "libc_init_main_candidate": 1,
  "mdmdetect_system_info": 1,
  "open": 0,
  "pipe": 1,
  "property_set": 0,
  "qmi_csi_event_loop": 0,
  "qmi_csi_register": 0,
  "select": 0,
  "write": 0
}
```

Observed order:

```text
elf_entry
libc_init_main_candidate
pipe
mdmdetect_system_info
android_log
close
close
```

## PM Contract

```text
pm_service_trigger_observer.result=observer-runtime-gap
pm_service_trigger_observer.reason=child-exited-before-observe-window
pm_service_trigger_observer.child.per_mgr.exit_code=255
pm_service_trigger_observer.child.per_proxy.exit_code=1
pm_service_trigger_observer.per_mgr_subsys_modem_seen=0
pm_service_trigger_observer.pm_proxy_helper_subsys_modem_seen=0
pm_service_trigger_observer.all_postflight_safe=1
```

## Safety

- `bpf_attach_executed=False`.
- `wifi_hal_start_executed=False`.
- `scan_connect_executed=False`.
- `credential_use_executed=False`.
- `dhcp_route_executed=False`.
- `external_ping_executed=False`.
- `partition_write_executed=False`.
- `flash_executed=False`.
- `reboot_executed=False`.
- Postflight actor list was clean.
- Postflight Wi-Fi link list was clean.
- Final selftest: `pass=11 warn=1 fail=0`.

## Interpretation

`pm-service` is not failing after a QMI/Binder server setup attempt. It exits
before those PLT calls are reached. The next cycle should classify the stripped
binary's early main/basic-block region around:

- entry `0x6000`
- main candidate `0x7650`
- `pipe` PLT call `0xa040`
- `get_system_info` PLT call `0x9f40`
- Android log PLT call `0x9e60`
- `close` PLT call `0xa080`

That should identify branch offsets suitable for a narrower V1081 tracefs probe
or a small local emulation/argument classifier.
