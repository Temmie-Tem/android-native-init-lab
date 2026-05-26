# V973 Android Service-Window Live v162

- generated: `2026-05-26`
- scope: bounded live proof retry with helper `v162`
- decision: `v970-step-failed`
- pass: `False`
- evidence: `tmp/wifi/v973-android-service-window-live-v162/manifest.json`

## Summary

V973 reran the Android service-window live proof with deployed helper `v162`.

The V971 `android_selinux_context_mode=service-defaults` repair worked, but the helper then rejected `--property-root` before actor execution:

```text
--property-root is only valid with property-lookup, private-selinux-proof, service-manager-start-only, rmt-storage-start-only, Wi-Fi companion, companion HAL order, or wifi-hal-composite modes; --property-key is only valid with property-lookup mode
```

This is the same class of validation bug: the new Android service-window mode was not included in every generic Wi-Fi companion allowlist.

## Guardrails

- remote helper sha/mode verified before execution
- no service-window actors started
- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no cleanup reboot needed

## Root Cause

The helper has a generic predicate:

```text
is_wifi_companion_any_start_only_mode()
```

Several validation gates use that predicate to decide whether Wi-Fi companion modes may use Android-like runtime inputs such as private property roots.

The new mode was dispatched separately before the generic mode handler, but it was not included in this predicate. That forced repeated one-off allowlist patches.

## Next

V974 should include `wifi-companion-android-wifi-service-window-start-only` in `is_wifi_companion_any_start_only_mode()`, build helper `v163`, and verify the generic allowlists cover the new service-window mode.
