# Native Init V1064 PM Service Trigger Observer Helper Plan

Date: `2026-05-27`

## Goal

Add source/build-only support for a bounded PM-service trigger observer in `a90_android_execns_probe`. V1063 showed native `pm-service` stays alive but sleeps with only binder-style readiness and never opens `/dev/subsys_modem`. V1064 prepares a narrower live gate that can observe the exact PM stack input surface without starting CNSS, Wi-Fi HAL, scan/connect, DHCP, external ping, or any eSoC trigger.

## Gate

- Cycle label: `v1064-pm-service-trigger-observer-helper`.
- Helper version: `a90_android_execns_probe v181`.
- New mode: `wifi-companion-pm-service-trigger-observer`.
- Required flag: `--allow-pm-service-trigger-observer`.
- Scope: source/build-only in this cycle; no deploy and no live daemon start.

## Guardrails

- Do not start `mdm_helper`, `cnss_diag`, `cnss-daemon`, Wi-Fi HAL, `wificond`, scan/connect, DHCP, route, or external ping.
- Do not open `/dev/subsys_esoc0`, `/dev/esoc-0`, or issue eSoC ioctls.
- Reject unrelated allow flags so the observer cannot be combined with CNSS/HAL/scan/connect/eSoC proof gates.
- Use bounded snapshots and cleanup semantics inherited from composite child helpers.

## Implementation

- Add mode/flag parsing and validation.
- Materialize private Android PM nodes needed for read-only status and fd matching.
- Start only `servicemanager`, `hwservicemanager`, `vndservicemanager`, `pm_proxy_helper`, `pm-service`, and `pm-proxy` inside the private Android namespace.
- Capture repeated snapshots of `pm-service` and `pm_proxy_helper` fd targets, binder/vndbinder readiness, PM process counts, and `pm-service` stall state.
- Emit clear result labels for `pm-service-subsys-modem-observed`, `pm-service-idle-input-gap-observed`, runtime gap, or cleanup risk.

## Success Criteria

- Static aarch64 helper build passes with no dynamic section.
- Helper strings contain version `v181`, mode, allow flag, and `pm_service_trigger_observer` result markers.
- `git diff --check` and changed-diff secret scan pass.
- Report documents artifact hash, size, guardrails, and next live gate.
