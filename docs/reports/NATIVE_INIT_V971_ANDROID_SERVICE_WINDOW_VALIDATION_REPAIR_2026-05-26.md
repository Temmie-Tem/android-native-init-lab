# V971 Android Service-Window Validation Repair

- generated: `2026-05-26`
- scope: source/build-only
- decision: `v971-android-service-window-validation-repair-pass`
- helper: `a90_android_execns_probe v162`
- evidence: `tmp/wifi/v971-android-service-window-validation-repair/manifest.json`
- build artifact: `tmp/wifi/v971-execns-helper-v162-build/a90_android_execns_probe`
- build sha256: `c51912bd4b723beddcd54ab2f958462dff4b291ace209bd0590bc45d108d0db7`

## Summary

V970 showed that helper `v161` rejected the Android service-window mode before actor execution because its own default `android_selinux_context_mode=service-defaults` was not allowed by the later validation allowlist.

V971 repairs that allowlist and bumps the helper to `v162`.

## Patch

The `service-defaults` validation now accepts:

```text
is_wifi_companion_android_wifi_service_window_start_only_mode(cfg->mode)
```

The Android service-window defaults are otherwise unchanged:

- private empty `/data/misc/wifi`
- `/dev/null` materialization
- VNDK APEX alias
- real linkerconfig copy
- Android service SELinux defaults
- full CNSS surface

## Guardrails

- source/build-only
- no device command
- no actor start
- no `qcwlanstate`
- no eSoC open/ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_service_window_validation_repair_v971.py
python3 scripts/revalidation/native_wifi_android_service_window_validation_repair_v971.py
```

Result:

```text
decision: v971-android-service-window-validation-repair-pass
pass: True
```

## Next

Deploy helper `v162`, then rerun the bounded Android service-window live proof.
