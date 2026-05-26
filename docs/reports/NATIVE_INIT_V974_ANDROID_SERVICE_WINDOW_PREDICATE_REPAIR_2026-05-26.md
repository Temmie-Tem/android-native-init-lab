# V974 Android Service-Window Predicate Repair

- generated: `2026-05-26`
- scope: source/build-only
- decision: `v974-android-service-window-predicate-repair-pass`
- helper: `a90_android_execns_probe v163`
- evidence: `tmp/wifi/v974-android-service-window-predicate-repair/manifest.json`
- build artifact: `tmp/wifi/v974-execns-helper-v163-build/a90_android_execns_probe`
- build sha256: `63ea88bbb3fbe074bf38e69873957ffa1082b061cf61b03e80061d83bc94b7f1`

## Summary

V973 showed that helper `v162` still rejected the Android service-window mode before actor execution, this time at the `--property-root` validation gate.

V974 repairs the root predicate coverage by including:

```text
wifi-companion-android-wifi-service-window-start-only
```

in:

```text
is_wifi_companion_any_start_only_mode()
```

This makes the Android service-window mode visible to the generic Wi-Fi companion allowlists instead of adding another one-off validation exception.

## Patch

- bumped helper version to `a90_android_execns_probe v163`
- added the Android service-window start-only mode to the generic Wi-Fi companion predicate
- kept the dedicated Android service-window dispatch before the generic Wi-Fi companion dispatch
- kept the existing no-bring-up guardrails unchanged

## Guardrails

- source/build-only
- no device command
- no actor start
- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_service_window_predicate_repair_v974.py
python3 scripts/revalidation/native_wifi_android_service_window_predicate_repair_v974.py
```

Result:

```text
decision: v974-android-service-window-predicate-repair-pass
pass: True
```

Verified checks:

- helper version string is `v163`
- new mode is covered by the generic Wi-Fi companion predicate
- dedicated service-window dispatch still precedes generic companion dispatch
- `service-defaults` and `property-root` allowlists use the generic predicate
- service-window guardrail strings remain present
- static helper artifact was produced and version/mode strings are present

## Next

Deploy helper `v163`, then rerun the bounded Android service-window live proof.
