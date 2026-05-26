# V961 Post-Provider Trigger Gate Support Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source/build verifier | `tmp/wifi/v961-post-provider-trigger-gate-support/manifest.json` | `v961-post-provider-trigger-gate-support-pass` |

V961 adds helper `v160` support for an explicit subsystem trigger gate:
`--subsys-trigger-gate post-provider-no-wlfw`.

The default gate remains `wlfw-precondition`, so existing V959/V960 wrappers keep
their previous behavior unless the new option is explicitly selected.

## Implementation

- Updated `stage3/linux_init/helpers/a90_android_execns_probe.c` to
  `a90_android_execns_probe v160`.
- Added `--subsys-trigger-gate wlfw-precondition|post-provider-no-wlfw`.
- Restricted `post-provider-no-wlfw` to
  `wifi-companion-mdm-helper-cnss-service-manager-matrix` with
  `service_manager_order=after-mdm-helper-esoc-fd-with-pm-proxy`.
- Added a post-provider arm condition requiring:
  `mdm_helper_esoc0_fd_seen`, `pm_proxy_started`, service managers started,
  `cnss_diag_started`, `cnss_daemon_started`, at least one surface poll, and no
  WLFW precondition observed.
- Added result taxonomy:
  `post-provider-no-wlfw-trigger-clean`.
- Added verifier:
  `scripts/revalidation/native_wifi_post_provider_trigger_gate_support_v961.py`.

## Guardrails

- Source/build-only; no device command was executed by V961.
- Existing default `wlfw-precondition` gate remains unchanged.
- The new gate does not add `pm_proxy_helper`.
- The trigger child still only opens `/dev/subsys_esoc0`; it does not issue
  eSoC notify or boot-done.
- No GPIO write, sysfs write, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, or external ping is added.

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_post_provider_trigger_gate_support_v961.py
python3 scripts/revalidation/native_wifi_post_provider_trigger_gate_support_v961.py
```

Verifier result:

- decision: `v961-post-provider-trigger-gate-support-pass`
- build artifact:
  `tmp/wifi/v961-execns-helper-v160-build/a90_android_execns_probe`
- build sha256:
  `2b4d621b111fa8e0e24a3591dd233478ac1d94ca87fa8c0eb1541db4d6d11998`
- failed checks: none

## Next

V962 should deploy helper `v160` only. V963 should run a bounded live
`post-provider-no-wlfw` proof with `pm_proxy_helper`, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, and external ping still blocked.
