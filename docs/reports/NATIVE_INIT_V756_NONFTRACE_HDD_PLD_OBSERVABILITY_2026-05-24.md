# Native Init V756 Non-ftrace HDD/PLD Observability Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_nonftrace_hdd_pld_observability_v756.py`
- plan evidence: `tmp/wifi/v756-nonftrace-hdd-pld-observability-plan/`
- run evidence: `tmp/wifi/v756-nonftrace-hdd-pld-observability/`
- decision: `v756-nonftrace-live-observers-exhausted`
- status: `pass`

## Summary

V756 classified the remaining live, read-only observability routes after V755
closed the ftrace/function-filter path. The result is that the current native
kernel state does not expose a usable dynamic-debug or kprobe route for the
HDD/PLD/register-driver gap.

Result:

```text
dynamic debug config: no
dynamic debug control file: absent
kprobes config: no
kprobe_events config: no
event tracing config: yes
tracefs mounted: no
printk available: yes
existing dmesg resolution: insufficient
target kallsyms: still partially visible
wlan0/wiphy: absent
```

V757 should therefore stop treating live kernel tracing as available and move to
one of two routes: expanded Android/native dmesg differential evidence, or a
rollback-safe boot-image/kernel-log instrumentation plan.

## Checks

| check | result |
| --- | --- |
| V753 input | pass; `v753-hdd-pld-register-driver-gap-needs-instrumentation` |
| V755 input | pass; `v755-tracefs-mounted-no-target-filter-functions` |
| current native health | pass; `version`, `status`, and `selftest` passed |
| dynamic-debug route | rejected; config/control/catalog are absent |
| kprobe route | rejected; `CONFIG_KPROBES` and `CONFIG_KPROBE_EVENTS` are absent |
| printk/dmesg route | review; printk exists, but existing dmesg does not resolve PLD/HDD/register-driver |
| containment | pass; no wiphy or `wlan0` appeared |

## Safety Result

V756 was read-only. It performed no tracefs/debugfs mount, no ftrace write, no
dynamic-debug write, no kprobe write, no `boot_wlan`/`qcwlanstate` write, no
service-manager or Wi-Fi HAL start, no scan/connect, no credential use, no
DHCP/routes, and no external ping.

## Interpretation

The kernel still exposes enough kallsyms names to know where the missing path
should be, but it does not expose a live tracing mechanism that can safely hook
those names from native init:

- dynamic debug is not compiled in and no control catalog is present,
- kprobe event support is not compiled in and no event file is present,
- ftrace was already rejected by V755 because function-filter controls and
  target functions are unavailable,
- existing printk/dmesg output only shows the coarse failure boundary and does
  not identify whether the stall is in `pld_init`, `hdd_init`, or
  `wlan_hdd_register_driver`.

The next useful unit is not another `boot_wlan` retry and not a live ftrace,
dyndbg, or kprobe proof. The next useful unit should either compare richer
Android/native boot logs around the HDD/PLD window, or prepare a minimal
rollback-safe instrumentation boot image that adds the missing log boundaries.

## Evidence

- `tmp/wifi/v756-nonftrace-hdd-pld-observability/manifest.json`
- `tmp/wifi/v756-nonftrace-hdd-pld-observability/summary.md`
- `tmp/wifi/v756-nonftrace-hdd-pld-observability/native/dynamic-debug-surface.txt`
- `tmp/wifi/v756-nonftrace-hdd-pld-observability/native/probe-event-surface.txt`
- `tmp/wifi/v756-nonftrace-hdd-pld-observability/native/config-observability.txt`
- `tmp/wifi/v756-nonftrace-hdd-pld-observability/native/focused-dmesg.txt`
- `tmp/wifi/v756-nonftrace-hdd-pld-observability/native/wlan-sysfs-surface.txt`
- `tmp/wifi/v756-nonftrace-hdd-pld-observability/native/target-kallsyms-confirm.txt`

## Source References

- Linux dynamic debug documentation:
  <https://docs.kernel.org/admin-guide/dynamic-debug-howto.html>
- Linux kprobe event tracing documentation:
  <https://docs.kernel.org/trace/kprobetrace.html>
- Linux printk documentation:
  <https://docs.kernel.org/core-api/printk-basics.html>
