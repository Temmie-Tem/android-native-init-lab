# V1108 PM Ordering No Pre-CNSS `per_proxy` Plan

Date: 2026-05-27

## Goal

Verify whether `cnss-daemon` can complete PeripheralManager register/connect when the PM observer does **not** run the `pm-proxy` connect path before CNSS.

## Background

- V1107 classified the V1106 mutex owner: pre-CNSS `per_proxy` caused a Binder thread in `pm-service` to hold the modem record mutex while blocked in `__subsystem_get` / `_request_firmware`.
- The next narrow question is whether CNSS itself can progress if the PM provider is present but pre-CNSS `per_proxy` is skipped.
- This is still a bounded diagnostic gate, not Wi-Fi bring-up.

## Implementation

- Bump `a90_android_execns_probe` from `v206` to `v207`.
- Add `--pm-observer-start-cnss-before-per-proxy`.
- In `wifi-companion-pm-service-trigger-observer` mode:
  - start service managers, `pm_proxy_helper`, and `pm-service`;
  - confirm PM provider registration by `vndservice_query`;
  - mark `per_proxy` as skipped without spawning `/vendor/bin/pm-proxy`;
  - start `cnss-daemon`;
  - keep the existing no-HAL/no-scan/no-connect safety contract.
- Reuse the V1106 tracefs PM client/server uprobes and thread sampler.

## Success Criteria

- helper usage exposes `a90_android_execns_probe v207` and the new ordering flag.
- `per_proxy_start_executed=0`.
- `child.per_proxy.start_skipped=1`.
- `start_cnss_before_per_proxy=1`.
- `cnss_daemon_start_executed=1`.
- PM client/server tracefs events classify whether CNSS reaches register/connect.

## Hard Gates

- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No DHCP, route change, credential use, or external ping.
- No `/dev/subsys_esoc0` open attempt.
- No partition write, flash, or reboot.
- Cleanup must prove all spawned Android-side actors stopped.

