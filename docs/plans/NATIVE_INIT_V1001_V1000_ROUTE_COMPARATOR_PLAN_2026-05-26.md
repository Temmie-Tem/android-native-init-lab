# V1001 V1000 Route Comparator Plan

## Goal

Compare the V1000 Android read-only recapture against the current native
service-window evidence and decide the next native gate.

The specific question is whether the older V923 fail-closed gate waited for the
wrong precondition: V923 required `wlfw_start` before opening
`/dev/subsys_esoc0`, while V1000 shows the current Android boot reaches
`/dev/subsys_esoc0` get before `wlfw_start`.

## Inputs

- V1000 Android handoff live:
  `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/manifest.json`
- V1000 Android dmesg/process/GPIO evidence:
  `tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/v913-android-esoc-gpio-timeline-run/android/commands/`
- V998 post-SELinux native service-window:
  `docs/reports/NATIVE_INIT_V998_ANDROID_SERVICE_WINDOW_POST_SELINUX_2026-05-26.md`
- V923 fail-closed CNSS-before-eSoC gate:
  `docs/reports/NATIVE_INIT_V923_CNSS_BEFORE_ESOC_LIVE_2026-05-26.md`
- V964 post-provider trigger stall:
  `docs/reports/NATIVE_INIT_V964_V963_POST_PROVIDER_TRIGGER_CLASSIFIER_2026-05-26.md`
- V965 stale route classifier:
  `docs/reports/NATIVE_INIT_V965_V964_ROUTE_CLASSIFIER_2026-05-26.md`

## Method

1. Parse V1000 Android dmesg for:
   - `vendor.wifi_hal_legacy`;
   - `vendor.wifi_hal_ext`;
   - `wificond`;
   - `vendor.mdm_helper`;
   - `cnss-daemon`;
   - `/dev/subsys_esoc0` `__subsystem_get`;
   - `cnss-daemon wlfw_start`;
   - WLAN-PD indication;
   - ICNSS QMI connection.
2. Check V1000 process/fd evidence for Android actor contexts and
   `mdm_helper` holding `/dev/esoc-0`.
3. Check V1000 GPIO evidence for readable GPIO135/GPIO142 surfaces.
4. Confirm V998 had the repaired actor window but did not try
   `/dev/subsys_esoc0`.
5. Confirm V923 kept `/dev/subsys_esoc0` closed because `wlfw_start` was absent.
6. Keep V964/V965 guardrails:
   - no blind `/dev/subsys_esoc0` retry;
   - no stale `qcwlanstate` or `IWifi.start` retry.

## Decision Criteria

Select source/build support for a service-window-scoped subsystem trigger only
if:

- V1000 rollback completed and Android evidence is usable.
- V1000 reaches `/dev/subsys_esoc0` get, `wlfw_start`, WLAN-PD, and ICNSS QMI.
- V1000 orders `/dev/subsys_esoc0` get before `wlfw_start`.
- V1000 proves `mdm_helper` holds `/dev/esoc-0` and the relevant actors run
  under Android SELinux domains.
- V998 proves the repaired native actor window but no lower trigger.
- V923 proves the previous `wlfw_start` precondition gate was fail-closed.
- V964/V965 still block blind lower retries and stale Wi-Fi API retries.

## Guardrails

- Host-only comparator.
- No device command.
- No actor start.
- No eSoC ioctl or `/dev/subsys_esoc0` open.
- No Wi-Fi scan/connect/link-up.
- No credential use.
- No DHCP, route mutation, or external ping.
- No boot image or partition write.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1000_route_comparator_v1001.py
python3 scripts/revalidation/native_wifi_v1000_route_comparator_v1001.py
```
