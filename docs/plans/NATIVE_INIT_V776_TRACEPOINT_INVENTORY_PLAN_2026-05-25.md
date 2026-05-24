# Native Init V776 Tracepoint Inventory Plan

## Goal

Use the recovered stock v724 kernel to classify whether static tracepoints can
replace the failed custom-kernel instrumentation route.

## Inputs

- V775 postmortem: `docs/reports/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md`
- V775 evidence: `tmp/wifi/v775-boot-incompat-postmortem/manifest.json`
- live native bridge on recovered `A90 Linux init 0.9.68 (v724)`

## Rules

- Stock v724 only; no custom kernel flash.
- Temporary tracefs mount/read/cleanup is allowed only with explicit gate flags.
- No ftrace control writes, BPF attach, `boot_wlan`, `qcwlanstate`, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, boot image write, or partition write.

## Work Items

1. Run plan-only classifier.
2. Run preflight: `version`, `status`, `tracefs full`, and `/proc/mounts`.
3. With `--allow-tracefs-mount --assume-yes`, mount tracefs if absent.
4. Read `available_events`, `available_tracers`, `current_tracer`, `tracing_on`, `trace_clock`, and event directory samples.
5. Count candidate event names for ICNSS/WLAN/Wi-Fi/QMI/QRTR/service-locator/subsystem/network/scheduler surfaces.
6. Unmount tracefs if V776 mounted it.
7. Confirm postflight cleanup and classify whether V777 should be BPF tracepoint feasibility or non-tracepoint observability.

## Success Criteria

- Evidence is written privately under `tmp/wifi/v776-tracepoint-inventory/`.
- Manifest proves no BPF attach, Wi-Fi action, credential use, network route change, external ping, reboot, flash, or partition write.
- If `available_events` is readable and focused candidates exist, V777 can inspect candidate semantics before any attach proof.
- If no focused candidates exist, keep custom-kernel flash paused and choose non-tracepoint stock-kernel observers.
