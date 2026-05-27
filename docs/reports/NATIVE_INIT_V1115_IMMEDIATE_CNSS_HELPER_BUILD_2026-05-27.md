# V1115 Immediate CNSS Helper Build Report

Date: `2026-05-27`

## Result

- Decision: `v1115-immediate-cnss-helper-build-pass`
- Pass: `true`
- Evidence: `tmp/wifi/v1115-execns-helper-v210-build/manifest.json`
- Collector: `scripts/revalidation/native_wifi_immediate_cnss_helper_build_v1115.py`
- Helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`

## Summary

V1115 adds helper support for the V1114-selected immediate CNSS gate.

Changes:

- Bumped helper marker to `a90_android_execns_probe v210`.
- Added flag `--pm-observer-start-cnss-immediate-after-per-mgr`.
- Added validation so the new flag is only valid in
  `wifi-companion-pm-service-trigger-observer` mode and requires
  `--pm-observer-start-cnss-before-per-proxy`.
- Added PM observer branch that:
  - samples `per_mgr` after `20 ms`;
  - skips the old pre-CNSS `vndservice` query;
  - skips `per_proxy`;
  - allows `cnss-daemon` to start immediately after `per_mgr`.

Build output:

```text
artifact=tmp/wifi/v1115-execns-helper-v210-build/a90_android_execns_probe
sha256=05cf75f9410ec14b07fca0f21de10cf4c08ab618b33770632190099f360497ed
size=1188336
static_no_interp=true
```

Required strings all passed:

```text
a90_android_execns_probe v210
--pm-observer-start-cnss-immediate-after-per-mgr
cnss_daemon_immediate
immediate-cnss-after-per_mgr
post_start_probe_wait_ms=20
```

## Safety

- `device_commands_executed=false`
- `deploy_executed=false`
- `tracefs_write_executed=false`
- `pm_actor_executed=false`
- `cnss_daemon_start_executed=false`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `reboot_executed=false`

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_immediate_cnss_helper_build_v1115.py
python3 scripts/revalidation/native_wifi_immediate_cnss_helper_build_v1115.py plan
python3 scripts/revalidation/native_wifi_immediate_cnss_helper_build_v1115.py run
```

Run result:

```text
decision: v1115-immediate-cnss-helper-build-pass
pass: True
```

## Next

V1116 should deploy helper `v210` and run the combined global-holder
immediate-CNSS live gate. The live gate should still forbid `/dev/subsys_esoc0`,
Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.
