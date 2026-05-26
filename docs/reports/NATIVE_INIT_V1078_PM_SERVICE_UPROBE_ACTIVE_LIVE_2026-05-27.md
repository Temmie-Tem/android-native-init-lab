# Native Init V1078 PM Service Uprobe Active Live Report

## Summary

V1078 executed the first bounded active `pm-service` uprobe run. The device path
and tracefs path are now proven far enough for dynamic uprobe registration:
`sda29` was mounted read-only through a synthetic block node, `pm-service` was
visible under `/mnt/vendor/bin/pm-service`, tracefs accepted the dynamic uprobe
event, and the event id was readable.

The remaining blocker is the BPF/perf attach boundary. The helper loaded the
counter map, registered `event.elf_entry`, read tracepoint id `1269`, then
failed attach with `EINVAL`. No PM-service hit count was collected because the
observer child was not started after attach failure.

Cleanup and safety passed: vendor, tracefs, and SELinuxfs temporary mounts were
removed; `selftest` ended with `fail=0`; and no Wi-Fi HAL, scan/connect, DHCP,
route change, external ping, boot image write, partition write, flash, or reboot
was executed.

## Change

- Added `scripts/revalidation/native_wifi_pm_service_uprobe_active_live_v1078.py`.
- Added a child-script upload path for the PM observer to avoid TCP control
  argument-count truncation.
- Added synthetic `sda29` block-node handling for the current native device tree,
  where `/dev/block/sda29` is absent but `/sys/class/block/sda29/dev` exists.
- Added verbose helper execution so BPF/attach failure boundaries are visible in
  evidence.

## Evidence

| item | path / value |
| --- | --- |
| runner | `scripts/revalidation/native_wifi_pm_service_uprobe_active_live_v1078.py` |
| manifest | `tmp/wifi/v1078-pm-service-uprobe-active-live/manifest.json` |
| summary | `tmp/wifi/v1078-pm-service-uprobe-active-live/summary.md` |
| observer transcript | `tmp/wifi/v1078-pm-service-uprobe-active-live/host/pm-service-uprobe-observer.txt` |
| PM binary stat | `tmp/wifi/v1078-pm-service-uprobe-active-live/host/pm-binary-stat.txt` |
| cleanup mounts | `tmp/wifi/v1078-pm-service-uprobe-active-live/host/proc-mounts-after-cleanup.txt` |
| final selftest | `tmp/wifi/v1078-pm-service-uprobe-active-live/host/post-selftest-final.txt` |
| V1076 helper sha256 | `05a8b9786fdfe95de94ada2883e0ee9326df69cf8548018b05d65aef3b384d9d` |

## Result

```text
decision: v1078-uprobe-active-failed
pass: False
reason: uprobe result=uprobe-count-failed
next: inspect active helper transcript
```

## Active Uprobe Boundary

```text
a90_pm_service_uprobe_counter v1076
binary=/mnt/vendor/bin/pm-service
tracefs_root=/sys/kernel/tracing
group=a90pm1076
duration_sec=18
event_count=7
allow_tracefs_write=1
allow_attach=1
allow_child_command=1
map_fd=5
event.elf_entry.register=ok
event.elf_entry.id=1269
event.elf_entry.attach=failed
event.elf_entry.errno=22
event.elf_entry.cleanup=removed
result=uprobe-count-failed
```

Interpretation: dynamic uprobe registration and event-id discovery work. The
failure is after BPF program load and before a live enabled observation, inside
the current helper's generic tracepoint perf attach path
(`perf_event_open`, `PERF_EVENT_IOC_SET_BPF`, or `PERF_EVENT_IOC_ENABLE` are not
separated by V1076).

## Safety

- `pm-service` observer child did not start after attach failure.
- `wifi_hal_start_executed=False`.
- `scan_connect_executed=False`.
- `external_ping_executed=False`.
- Temporary `/mnt/vendor`, tracefs, and SELinuxfs mounts were cleaned up.
- Final native selftest: `pass=11 warn=1 fail=0`.

## Interpretation

V1078 closes the "can native register dynamic uprobes for vendor
`pm-service`?" question: yes. It does not close the PM-service exit-255 root
cause because BPF/perf attach failed before the observer child could execute.

The next practical step is V1079 as a tracefs-only dynamic uprobe collector:
register the same dynamic events, enable them through tracefs, run the PM
observer child, read `trace`/`trace_pipe`, count hits in userspace, then disable
and remove events. This avoids the current BPF/perf attach blocker while keeping
the same no-Wi-Fi safety contract.
