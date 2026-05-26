# V970 Android Service-Window Live

- generated: `2026-05-26`
- scope: bounded live proof
- decision: `v970-step-failed`
- pass: `False`
- evidence: `tmp/wifi/v970-android-service-window-live/manifest.json`

## Summary

V970 attempted the helper `v161` Android service-window live proof:

```text
wifi-companion-android-wifi-service-window-start-only
```

The device did not reach service-window actor execution. The helper rejected the mode during argument validation:

```text
--android-selinux-context-mode is only valid with service-manager, Wi-Fi HAL composite, CNSS userspace readiness, or Wi-Fi companion modes
```

This is a helper source validation gap, not a device runtime blocker.

## Evidence

Remote helper was correct before execution:

- sha matched `1d936d9117e68b97c1449d9ed357560ec7ae1901eeb179da474f1dacbc837643`
- marker matched `a90_android_execns_probe v161`
- mode string was present in usage

The live command failed before `android_wifi_service_window.begin=1`, so no service-manager, Wi-Fi HAL, `wificond`, `mdm_helper`, or `cnss-daemon` start happened.

## Guardrails

- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no cleanup reboot needed

## Root Cause

Helper `v161` sets `android_selinux_context_mode=service-defaults` by default for the new Android service-window mode, but the later `service-defaults` validation allowlist did not include:

```text
is_wifi_companion_android_wifi_service_window_start_only_mode(cfg->mode)
```

## Next

V971 should patch the helper allowlist, build helper `v162`, and verify the new mode no longer rejects its own default namespace policy.
