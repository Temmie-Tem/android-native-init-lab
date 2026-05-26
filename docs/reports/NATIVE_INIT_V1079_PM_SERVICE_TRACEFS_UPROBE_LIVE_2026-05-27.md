# Native Init V1079 PM Service Tracefs Uprobe Live Report

## Summary

V1079 passed. It replaced the V1078 BPF/perf path with tracefs-only dynamic
uprobes and captured real `pm-service` execution during the PM trigger observer
window.

The captured hits prove that the current native path starts `pm-service` and
reaches the classified offsets:

- `elf_entry`: `1`
- `libc_init_main_candidate`: `1`
- `mdmdetect_system_info`: `1`
- `android_log`: `1`

The PM observer contract still ends at the known runtime gap:
`per_mgr` exits with `255`, `per_proxy` exits with `1`,
`per_mgr_subsys_modem_seen=0`, and `pm_proxy_helper_subsys_modem_seen=0`.
This keeps the Wi-Fi chain blocked before `mdm3 ONLINE`, WLAN-PD, WLFW service
69, and `wlan0`.

## Change

- Added `scripts/revalidation/native_wifi_pm_service_tracefs_uprobe_live_v1079.py`.
- Added a tracefs-only collector script uploaded to the device for the bounded
  run.
- Registered all dynamic uprobes before enabling them to avoid tracefs `EBUSY`.
- Switched `uprobe_events` operations to append writes so registering multiple
  events does not remove previous events.
- Redirected verbose PM observer child output to a private device file and
  emitted only contract summary plus tracefs counts over TCP.
- Created and removed temporary `/dev/block/sda29` only when native devtmpfs did
  not provide it.

## Evidence

| item | path / value |
| --- | --- |
| runner | `scripts/revalidation/native_wifi_pm_service_tracefs_uprobe_live_v1079.py` |
| manifest | `tmp/wifi/v1079-pm-service-tracefs-uprobe-live/manifest.json` |
| summary | `tmp/wifi/v1079-pm-service-tracefs-uprobe-live/summary.md` |
| observer transcript | `tmp/wifi/v1079-pm-service-tracefs-uprobe-live/host/pm-service-tracefs-uprobe-observer.txt` |
| collector script | `tmp/wifi/v1079-pm-service-tracefs-uprobe-live/host/tracefs-uprobe-collector-script.txt` |
| child script | `tmp/wifi/v1079-pm-service-tracefs-uprobe-live/host/pm-observer-child-script.txt` |
| cleanup mounts | `tmp/wifi/v1079-pm-service-tracefs-uprobe-live/host/proc-mounts-after-cleanup.txt` |
| final selftest | `tmp/wifi/v1079-pm-service-tracefs-uprobe-live/host/post-selftest-final.txt` |

## Result

```text
decision: v1079-pm-service-tracefs-uprobe-boundary-captured
pass: True
reason: entry_hit=True main_hit=True hit_count=4
next: classify PM-service callsite hits and choose the next exit-255 root-cause probe
```

## Tracefs Hits

```text
pm-service: elf_entry
pm-service: libc_init_main_candidate
pm-service: mdmdetect_system_info
pm-service: android_log
```

Counts:

```json
{
  "android_log": 1,
  "binder_driver": 0,
  "elf_entry": 1,
  "libc_init_main_candidate": 1,
  "mdmdetect_system_info": 1,
  "property_set": 0,
  "qmi_csi_register": 0
}
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

V1079 proves the tracefs-only route is sufficient for low-frequency PM-service
userspace attribution on the stock v724 kernel. The next blocker is no longer
"can we observe `pm-service`?" It is now "which later `pm-service` or `per_mgr`
call path leads to exit 255 before `/dev/subsys_modem` is opened?"

The next cycle should use V1079's working tracefs path to add narrower offsets
or a compact actor-specific observer around `per_mgr` startup and exit.
