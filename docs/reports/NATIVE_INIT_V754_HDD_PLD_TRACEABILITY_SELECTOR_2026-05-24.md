# Native Init V754 HDD/PLD Traceability Selector Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_hdd_pld_traceability_selector_v754.py`
- plan evidence: `tmp/wifi/v754-hdd-pld-traceability-selector-plan/`
- run evidence: `tmp/wifi/v754-hdd-pld-traceability-selector/`
- decision: `v754-tracefs-mount-gated-observer-needed`
- status: `pass`

## Summary

V754 checked whether the V753 HDD/PLD/register-driver gap can be instrumented
without kernel rebuild first. It found:

```text
tracefs filesystem support: yes
debugfs filesystem support: yes
tracefs mounted: no
debugfs mounted: no
available_filter_functions readable: no
target symbols in /proc/kallsyms: partial yes
ftrace function config from /proc/config.gz: not confirmed
```

This means the next step is not another Wi-Fi trigger. The next step is a
bounded tracefs mount/filter proof that mounts tracefs, checks whether target
functions appear in `available_filter_functions`, then cleans up without running
`boot_wlan`.

## Checks

| check | result |
| --- | --- |
| V753 input | pass; `v753-hdd-pld-register-driver-gap-needs-instrumentation` |
| current native healthy | pass |
| tracefs support present | pass; tracefs/debugfs supported, not mounted |
| target symbols visible | pass; partial target symbols found in `/proc/kallsyms` |
| tracefs not active yet | pass; no readable active ftrace controls |
| ftrace config surface | review; `CONFIG_KALLSYMS=y`, `CONFIG_DEBUG_FS=y`, function tracer config not confirmed |

## Target Symbol Hits

| function | hits |
| --- | --- |
| `__hdd_module_init` | `0` |
| `wlan_boot_cb` | `1` |
| `wlan_hdd_state_ctrl_param_create` | `1` |
| `pld_init` | `1` |
| `hdd_init` | `12` |
| `wlan_hdd_register_driver` | `1` |
| `cds_is_driver_loaded` | `0` |
| `icnss_register_driver` | `3` |
| `icnss_wlan_enable` | `3` |
| `icnss_qmi` | `0` |

## Safety Result

V754 was read-only. It executed no tracefs/debugfs mount, no ftrace control
write, no `boot_wlan`/`qcwlanstate` write, no service-manager, no Wi-Fi HAL, no
scan/connect, no credentials, no DHCP/routes, and no external ping.

## Interpretation

`/proc/kallsyms` exposes enough related target names to justify a controlled
tracefs mount/filter proof, but ftrace readiness is not proven yet because
tracefs is not mounted and `available_filter_functions` is not readable. The
right next gate is V755:

1. mount tracefs in a bounded proof window,
2. read `available_tracers`, `current_tracer`, and `available_filter_functions`,
3. check target functions,
4. unmount/cleanup,
5. stop before `boot_wlan` or any Wi-Fi daemon/HAL/connect behavior.

If V755 shows no function tracer/filter support, route to non-ftrace
instrumentation or boot-image/kernel-log instrumentation planning.

## Evidence

- `tmp/wifi/v754-hdd-pld-traceability-selector/manifest.json`
- `tmp/wifi/v754-hdd-pld-traceability-selector/summary.md`
- `tmp/wifi/v754-hdd-pld-traceability-selector/native/tracefs-kernel-surface.txt`
- `tmp/wifi/v754-hdd-pld-traceability-selector/native/target-kallsyms.txt`
- `tmp/wifi/v754-hdd-pld-traceability-selector/native/target-filter-functions-if-mounted.txt`

## Source References

- <https://docs.kernel.org/next/trace/ftrace.html>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c>
