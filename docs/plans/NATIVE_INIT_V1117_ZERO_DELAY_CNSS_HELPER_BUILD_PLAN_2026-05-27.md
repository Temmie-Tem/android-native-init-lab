# V1117 Zero-delay CNSS Helper Build Plan

Date: `2026-05-27`

## Goal

Remove the remaining `20 ms` pre-CNSS sample delay from the V1116 order by
adding helper `v211` support for zero-delay CNSS after `per_mgr`.

## Scope

- Bump `a90_android_execns_probe` to `v211`.
- Add `--pm-observer-start-cnss-zero-delay-after-per-mgr`.
- Make the new flag mutually exclusive with the V1115 `20 ms` immediate flag.
- In PM observer mode, when zero-delay is selected:
  - fork `per_mgr`;
  - skip the post-`per_mgr` vndservice query;
  - skip `per_proxy`;
  - fork `cnss-daemon` without the `20 ms` sleep/drain/sample.

## Guardrails

- Source/build-only.
- No helper deploy.
- No device command.
- No PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credential, DHCP/route,
  external ping, reboot, partition write, boot image write, or flash.

## Success Criteria

V1117 passes if:

- source contains the `v211` marker and zero-delay flag/contract strings;
- static AArch64 helper builds successfully;
- built helper has no dynamic interpreter;
- built helper contains:
  - `a90_android_execns_probe v211`;
  - `--pm-observer-start-cnss-zero-delay-after-per-mgr`;
  - `cnss_daemon_zero_delay`;
  - `zero-delay-cnss-after-per_mgr`;
  - `post_start_probe_wait_ms=0`.

## Expected Next

V1118 should deploy helper `v211` and run the bounded global-holder zero-delay
CNSS live gate.
