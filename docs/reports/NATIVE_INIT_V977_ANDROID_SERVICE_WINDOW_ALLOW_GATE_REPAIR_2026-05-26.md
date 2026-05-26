# V977 Android Service-Window Allow-Gate Repair

- generated: `2026-05-26`
- scope: source/build-only
- decision: `v977-android-service-window-allow-gate-repair-pass`
- helper: `a90_android_execns_probe v164`
- evidence: `tmp/wifi/v977-android-service-window-allow-gate-repair/manifest.json`
- build artifact: `tmp/wifi/v977-execns-helper-v164-build/a90_android_execns_probe`
- build sha256: `891f8363c09dbb8263a7e85fe30b47c0e8f0142ee99e04bbe94a34c10b46966e`

## Summary

V977 repairs the V976 validation layering issue.

Helper `v164` keeps the Android service-window mode inside the generic Wi-Fi companion predicate so shared validation allowlists still apply, but excludes that dedicated mode from the generic companion allow-flag requirement.

The dedicated mode still accepts only:

```text
--allow-android-wifi-service-window
```

and still rejects generic CNSS/companion/service-manager/HAL actor flags.

## Patch

- bumped helper version to `a90_android_execns_probe v164`
- added an `android_service_window` boolean in the generic companion validation block
- skipped the generic `--allow-wifi-companion-start-only` and `--allow-cnss-start-only` requirement only for the Android service-window mode
- preserved dedicated-mode guardrails and dispatch ordering

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
python3 -m py_compile scripts/revalidation/native_wifi_android_service_window_allow_gate_repair_v977.py
python3 scripts/revalidation/native_wifi_android_service_window_allow_gate_repair_v977.py
```

Result:

```text
decision: v977-android-service-window-allow-gate-repair-pass
pass: True
```

Verified checks:

- helper version string is `v164`
- new mode remains covered by the generic Wi-Fi companion predicate
- generic validation has an Android service-window carveout
- dedicated mode still rejects generic actor flags
- dedicated dispatch still precedes generic companion dispatch
- static helper artifact was produced and version/mode strings are present

## Next

Deploy helper `v164`, then rerun the bounded Android service-window live proof.
