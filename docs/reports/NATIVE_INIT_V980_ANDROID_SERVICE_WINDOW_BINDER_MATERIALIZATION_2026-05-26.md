# V980 Android Service-Window Binder Materialization

- generated: `2026-05-26`
- scope: source/build-only
- decision: `v980-android-service-window-binder-materialization-pass`
- helper: `a90_android_execns_probe v165`
- evidence: `tmp/wifi/v980-android-service-window-binder-materialization/manifest.json`
- build artifact: `tmp/wifi/v980-execns-helper-v165-build/a90_android_execns_probe`
- build sha256: `5d4bda053547e0f67ee39356dc5c156927860551bb94456a8421c16f531f1981`

## Summary

V979 reached the Android service-window actor sequence but service-manager/HAL-class actors aborted immediately because `/dev/binder` was absent in the private namespace:

```text
Binder driver '/dev/binder' could not be opened. Terminating.
```

The native global `/dev` also has no binder device nodes, so the private namespace must materialize binder nodes explicitly.

V980 repairs that coverage for the dedicated Android service-window mode.

## Patch

Helper `v165` now includes the Android service-window mode in the binder device materialization gate when:

```text
is_wifi_companion_android_wifi_service_window_start_only_mode(cfg->mode)
cfg->allow_android_wifi_service_window
```

The existing materialized nodes remain:

- `/dev/binder` major `10`, minor `81`
- `/dev/hwbinder` major `10`, minor `80`
- `/dev/vndbinder` major `10`, minor `79`

## Guardrails

- source/build-only
- no device command from verifier
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
python3 -m py_compile scripts/revalidation/native_wifi_android_service_window_binder_materialization_v980.py
python3 scripts/revalidation/native_wifi_android_service_window_binder_materialization_v980.py
```

Result:

```text
decision: v980-android-service-window-binder-materialization-pass
pass: True
```

Verified checks:

- helper version string is `v165`
- binder materialization gate includes Android service-window mode and allow flag
- binder/hwbinder/vndbinder node materialization remains intact
- dedicated service-window allow model remains single-flag
- static helper artifact was produced and version/mode strings are present

## Next

Deploy helper `v165`, then rerun the bounded Android service-window live proof.
