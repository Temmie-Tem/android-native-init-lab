# Native Init V755 Tracefs Mount/Filter Proof Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_tracefs_mount_filter_proof_v755.py`
- plan evidence: `tmp/wifi/v755-tracefs-mount-filter-proof-plan/`
- preflight evidence: `tmp/wifi/v755-tracefs-mount-filter-proof-preflight-retry/`
- first live evidence: `tmp/wifi/v755-tracefs-mount-filter-proof/`
- final live evidence: `tmp/wifi/v755-tracefs-mount-filter-proof-retry/`
- decision: `v755-tracefs-mounted-no-target-filter-functions`
- status: `pass`

## Summary

V755 mounted tracefs, read the ftrace surfaces, then unmounted tracefs cleanly.
It did not write ftrace controls or run any Wi-Fi trigger.

Result:

```text
tracefs mounted during proof: yes
tracefs cleanup: yes
available_tracers readable: yes, only `nop`
current_tracer readable: yes, `nop`
tracing_on readable: yes
available_filter_functions readable: no
set_ftrace_filter readable: no
set_graph_function readable: no
target filter hits: 0
```

The ftrace/function-filter path is therefore not usable for the HDD/PLD target
on this kernel state.

## Checks

| check | result |
| --- | --- |
| V754 input | pass; `v754-tracefs-mount-gated-observer-needed` |
| live approval | pass; `--allow-tracefs-mount --assume-yes` |
| tracefs mounted during window | pass; `mount_rc=0`, mounted during proof |
| tracefs cleanup | pass; unmounted after proof |
| ftrace control readability | pass/finding; only basic `nop` tracer files readable |
| target filter functions | review; no target functions visible |

## Safety Result

V755 performed a temporary tracefs mount and cleanup only. It executed no ftrace
control writes, no `boot_wlan`/`qcwlanstate` writes, no service-manager, no
Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external
ping. Postflight `tracefs full` showed `mount_tracefs=no`.

## Interpretation

The ftrace path is effectively closed for this target on the current kernel:
tracefs can be mounted, but function tracing controls for target filtering are
not available. This matches V754's incomplete ftrace config surface.

The next gate should not be a ftrace dry-run. The next gate should plan
non-ftrace HDD/PLD observability. Practical candidates:

1. boot-image/kernel-command-line or PID1 dmesg-window improvements that do not
   require kernel source rebuild,
2. Android/native dmesg differential search for hidden lower-level markers,
3. source-backed boot image instrumentation only if a safe kernel/initramfs
   mechanism exists and rollback is ready.

## Evidence

- `tmp/wifi/v755-tracefs-mount-filter-proof-retry/manifest.json`
- `tmp/wifi/v755-tracefs-mount-filter-proof-retry/summary.md`
- `tmp/wifi/v755-tracefs-mount-filter-proof-retry/native/tracefs-mount-read-cleanup.txt`
- `tmp/wifi/v755-tracefs-mount-filter-proof-retry/native/tracefs-full-after.txt`

## Source Reference

- <https://docs.kernel.org/next/trace/ftrace.html>
