# Native Init V755 Tracefs Mount/Filter Proof Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_tracefs_mount_filter_proof_v755.py`
- scope: bounded tracefs mount/read/cleanup proof; no ftrace writes and no Wi-Fi trigger

## Goal

V754 found tracefs support and partial target symbols in `/proc/kallsyms`, but
tracefs was not mounted. V755 performs the narrow proof needed before any active
tracing: mount tracefs, read ftrace control/readability surfaces, inspect
`available_filter_functions` for HDD/PLD targets, then unmount if this runner
mounted it.

## Basis Evidence

- `docs/reports/NATIVE_INIT_V754_HDD_PLD_TRACEABILITY_SELECTOR_2026-05-24.md`
- `tmp/wifi/v754-hdd-pld-traceability-selector/manifest.json`
- Linux ftrace documentation:
  <https://docs.kernel.org/next/trace/ftrace.html>

## Work Items

1. Run plan and no-mount preflight.
2. Require `--allow-tracefs-mount --assume-yes` for live proof.
3. Detect whether tracefs was already mounted.
4. Mount tracefs at `/sys/kernel/tracing` if needed.
5. Read `available_tracers`, `current_tracer`, `available_filter_functions`,
   `set_ftrace_filter`, `set_graph_function`, `tracing_on`, and `trace`.
6. Search `available_filter_functions` for the HDD/PLD target names.
7. Unmount tracefs if V755 mounted it.
8. Confirm postflight `tracefs full` reports no tracefs mount.

## Forbidden

- no ftrace control writes
- no `boot_wlan`, `qcwlanstate`, bind/unbind, module, or subsystem writes
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping
- no boot image or partition writes

## Success Criteria

- Produce `manifest.json` and `summary.md`.
- Prove tracefs mount and cleanup behavior.
- Prove whether ftrace filter function targets are visible.
- Prove no ftrace write or Wi-Fi trigger occurred.
- Route the next gate to ftrace dry-run only if target filters exist; otherwise
  route to non-ftrace instrumentation planning.
