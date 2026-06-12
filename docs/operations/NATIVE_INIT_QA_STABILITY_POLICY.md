# Native Init QA And Stability Policy

Updated: `2026-06-12`

This document defines what must be proven before a native-init behavior is
treated as baseline quality. It separates required baseline checks from optional
polish so that revalidation work does not drift into unrelated live tests.

## Required For Baseline Promotion

- Boot identity is explicit:
  - run/build identity;
  - native init version;
  - helper marker;
  - boot image path;
  - boot SHA256;
  - host commit.
- Rollback is explicit:
  - rollback image path;
  - rollback SHA256;
  - final `selftest fail=0`.
- Runner evidence is structured:
  - `selector_contract=1` for transport-aware runners;
  - `phase_timer_contract=1` when the runner spans flash, boot, Wi-Fi,
    artifact upload, rollback, or a bounded stability window;
  - `residual_state_contract=1` when the runner can leave device, host, network,
    or filesystem state behind.
- Secret hygiene is proven:
  - Wi-Fi SSID/PSK values remain under ignored private roots;
  - public reports contain only redacted summaries;
  - runners fail closed when secret leakage is detected.

## Required Before Repeated Live QA

- Start from the current promoted baseline unless the test explicitly validates a
  candidate boot image.
- Use `a90_transport.select_transport()` for active runners that talk to the
  device through the bridge/NCM path.
- Capture residual state that can affect the next run:
  - bridge process/listener state;
  - NCM interface/link-local readiness;
  - `tcpctl` readiness;
  - supplicant/config/profile state for Wi-Fi tests;
  - generated device files or test roots;
  - final `selftest` result when the runner changes boot/network/runtime state.
- Treat cleanup failures as real risks unless the report explicitly proves the
  leftover state is harmless for the next run.

## Optional Polish

- Physical button/OCR validation for menus that already have command-level
  framebuffer evidence.
- Repeated large-file or multi-hour Wi-Fi/data-path soak after a single-run SHA
  proof already passed.
- Archive-wide dedupe of historical scripts. Archive scripts are provenance,
  not active entrypoints.

## Current Baseline Notes

- Current promoted baseline: `v2237-supplicant-terminate-poll`.
- Current source-root revalidation inventory:
  `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md`.
- Current inventory state:
  - `43 active`;
  - `6 module`;
  - `0 archive`;
  - `0 delete-review`.
- Current active live metadata gaps:
  - phase timer markers: `0`;
  - residual-state metadata: `0`.
- Phase-timer-exempt live utilities:
  - `ncm_host_setup.py`;
  - `netservice_reconnect_soak.py`.
