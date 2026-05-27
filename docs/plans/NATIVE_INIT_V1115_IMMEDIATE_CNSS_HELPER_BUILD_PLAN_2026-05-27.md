# V1115 Immediate CNSS Helper Build Plan

Date: `2026-05-27`

## Goal

Implement the V1114-selected helper support for an immediate
CNSS-after-`per_mgr` observer path.

V1114 showed that the current PM observer waits 1000 ms after starting
`pm-service`; by that time `pm-service` has already exited cleanly and CNSS PM
client uprobes have zero hits. V1115 therefore changes only the helper
observability/order support, not Wi-Fi behavior.

## Scope

- Bump `a90_android_execns_probe` to `v210`.
- Add `--pm-observer-start-cnss-immediate-after-per-mgr`.
- In PM observer mode, when the new flag is present:
  - sample `per_mgr` after a 20 ms wait instead of the existing 1000 ms wait;
  - skip the pre-CNSS `vndservice` query after `per_mgr`;
  - skip `per_proxy`;
  - start `cnss-daemon` immediately after `per_mgr`.

## Guardrails

- Source/build-only.
- No helper deploy.
- No device command.
- No PM actor or CNSS actor execution.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
- No reboot, partition write, boot image write, or flash.

## Success Criteria

V1115 passes if:

- source contains the v210 marker and immediate-CNSS flag/order strings;
- static AArch64 helper builds successfully;
- built helper has no dynamic interpreter;
- built helper contains:
  - `a90_android_execns_probe v210`;
  - `--pm-observer-start-cnss-immediate-after-per-mgr`;
  - `cnss_daemon_immediate`;
  - `immediate-cnss-after-per_mgr`;
  - `post_start_probe_wait_ms=20`.

## Expected Next

V1116 should deploy helper `v210`, then run a bounded combined live gate:

```text
global firmware mounts
  -> global /dev/subsys_modem holder
  -> PM observer v210 immediate CNSS after per_mgr
```

Wi-Fi HAL and scan/connect remain forbidden until the PM client path and lower
WLFW/service69 boundary are explained.
