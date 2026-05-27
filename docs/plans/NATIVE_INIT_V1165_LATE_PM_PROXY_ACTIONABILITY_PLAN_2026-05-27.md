# Native Init V1165 Late pm-proxy Actionability Plan

Date: `2026-05-27`

## Goal

Instrument the V1164 actionability gap after late `pm-proxy` start.  V1164
proved that native reaches PM client/server connect success, but `pm-service`
still does not open `/dev/subsys_esoc0` as Android does.  V1165 extends the
bounded live window and records whether the late `pm-proxy` process remains
alive, exits, or produces output while the PM server connect path runs.

## Scope

- Build static execns helper `a90_android_execns_probe v217`.
- Deploy only `/cache/bin/a90_android_execns_probe`.
- Re-establish current-boot prerequisites:
  - V401 SELinuxfs runtime surface mount.
  - V490 Android split SELinux policy load proof.
- Run the bounded PM/CNSS/mdm_helper observer with late `pm-proxy` enabled.
- Collect:
  - `per_proxy` alive/exit/stdout/stderr state per poll.
  - twelve 1 second late polls.
  - PM server connect state/start-vote/action tracefs lines.
  - `pm-service` `/dev/subsys_modem`, `/dev/subsys_esoc0`, and `/dev/vndbinder` fd state.

## Safety

- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route, or external ping.
- No boot image write, partition write, or flash.
- Tracefs/vendor/SELinuxfs mounts must be bounded and cleaned up.
- Helper deployment may replace only `/cache/bin/a90_android_execns_probe`.

## Success Criteria

- Helper `v217` builds as static AArch64 and exposes the late `pm-proxy` flag.
- Deploy preflight verifies remote SHA and usage output.
- Live gate records 12 late polls with `per_proxy` lifecycle state.
- PM server connect trace reaches `pm_server_connect_impl_start_vote` with
  return `0x0` or records a concrete failure.
- The result classifies one of:
  - `v1165-late-per-proxy-esoc-trigger-observed`
  - `v1165-late-per-proxy-lower-artifact-observed`
  - `v1165-late-per-proxy-actionability-gap`
  - a fail-closed helper/deploy/precondition blocker.

## Expected Decision Use

If `pm-proxy` remains alive and PM server connect/start-vote returns success but
`pm-service` still never opens `/dev/subsys_esoc0`, the next gate must stop
retrying late `pm-proxy` and inspect the missing Binder/PM action contract
between Android-good `vendor.per_proxy` and native `pm-proxy`.
