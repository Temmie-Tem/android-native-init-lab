# V976 Android Service-Window Live v163

- generated: `2026-05-26`
- scope: bounded live proof retry with helper `v163`
- decision: `v970-step-failed`
- pass: `False`
- evidence: `tmp/wifi/v976-android-service-window-live-v163/manifest.json`

## Summary

V976 reran the Android service-window live proof with deployed helper `v163`.

The V974 predicate repair worked: remote helper sha/mode parity passed and the previous `--property-root` validation blocker did not recur.

The helper then rejected the service-window command at the generic Wi-Fi companion allow-gate before any actors started:

```text
Wi-Fi companion modes require --allow-wifi-companion-start-only and --allow-cnss-start-only
```

This is a validation layering issue, not a runtime Wi-Fi failure. The Android service-window mode needs generic predicate coverage for shared allowlists, but it intentionally uses only `--allow-android-wifi-service-window` and rejects the generic actor flags.

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

V974 added the Android service-window mode to:

```text
is_wifi_companion_any_start_only_mode()
```

That fixed shared allowlists, but also made the mode enter the generic Wi-Fi companion validation gate that requires:

```text
--allow-wifi-companion-start-only
--allow-cnss-start-only
```

Those flags are explicitly disallowed for this dedicated mode.

## Next

V977 should keep the mode in the generic predicate, but exempt it from the generic companion allow-flag requirement so the dedicated `--allow-android-wifi-service-window` gate remains authoritative.
