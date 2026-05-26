# V979 Android Service-Window Live v164

- generated: `2026-05-26`
- scope: bounded live proof retry with helper `v164`
- decision: `v970-android-service-window-runtime-gap`
- pass: `True`
- evidence: `tmp/wifi/v979-android-service-window-live-v164/manifest.json`

## Summary

V979 reran the Android service-window live proof with deployed helper `v164`.

The previous validation blockers are resolved:

- remote helper sha/mode matched `v164`
- `service-defaults` validation accepted the mode
- `property-root` validation accepted the mode
- generic companion allow-gate no longer rejected the dedicated service-window mode

The helper reached the live start-only window and started all 14 planned actors. It still did not reach Wi-Fi readiness:

```text
result=start-only-runtime-gap
reason=child-exited-before-observe-window
wlfw_precondition_observed=0
```

## Actor Outcome

Actors that were started and remained observable until cleanup:

- `qrtr_ns`
- `rmt_storage`
- `tftp_server`
- `pd_mapper`
- `cnss_diag`
- `mdm_helper`

Actors that exited before the observe window with `SIGABRT`:

- `servicemanager`
- `hwservicemanager`
- `vndservicemanager`
- `wifi_hal_legacy`
- `wifi_hal_ext`
- `per_mgr`
- `wificond`
- `cnss_daemon`

## Runtime Signals

- `child_started=14`
- `timed_out=1`
- `all_observable_at_timeout=0`
- `all_postflight_safe=1`
- `wlfw_precondition_observed=0`
- `/sys/class/net/wlan0` absent
- `mdm3` remained `OFFLINING`
- no Wi-Fi link surface remained after cleanup

Only relevant new kernel/user signal observed in the post surface:

```text
rmt_storage:INFO:check_support_using_libmdm: Modem subsystem found on target!
```

## Guardrails

- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no cleanup reboot needed

## Interpretation

V979 proves that the service-window runner can now execute the intended bounded actor sequence.

The remaining blocker is no longer argument validation. It is a runtime context gap: Android service-manager/HAL-class actors abort early in the private native namespace, while QRTR/storage companion actors stay observable until cleanup.

## Next

Classify the early `SIGABRT` actors by adding bounded stderr/tombstone/logcat-equivalent capture for the service-manager and Wi-Fi HAL group, without scan/connect, `qcwlanstate`, eSoC open, or Wi-Fi bring-up.
