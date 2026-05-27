# V1112 Subsys Modem Precondition Classifier Plan

Date: `2026-05-27`

## Goal

Classify the remaining V1111 blocker before any Wi-Fi HAL or scan/connect work:
why `pm-service` blocks in `openat("/dev/subsys_modem")` after a successful CNSS
PM connect.

## Inputs

- V1111 live evidence: `tmp/wifi/v1111-pm-connect-path-capture-live/manifest.json`
- V1061 live evidence: `tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json`
- V1045 first-opener model report:
  `docs/reports/NATIVE_INIT_V1045_PM_PIL_PREREQUISITE_DELTA_2026-05-26.md`
- V1061 global firmware holder report:
  `docs/reports/NATIVE_INIT_V1061_GLOBAL_FIRMWARE_PM_FULL_CONTRACT_2026-05-27.md`

## Method

1. Parse V1111 and confirm:
   - CNSS `pm_client_register`/`pm_client_connect` returned `0x0`.
   - The blocked owner thread target is `/dev/subsys_modem`.
   - No pre-existing `/dev/subsys_modem` fd was present in the PM actor window.
2. Parse V1061 and confirm:
   - Global firmware mounts were executed.
   - Global `/dev/subsys_modem` holder opened.
   - `mss` reached `ONLINE`.
   - PM full contract still lacked the CNSS-triggered `pm-service` open.
3. Live read-only capture:
   - `firmware_class.path`
   - `/proc/mounts`
   - `/sys/class/subsys/*/dev`
   - `/sys/bus/msm_subsys/devices/*/{name,state,restart_level,firmware_name}`
   - focused dmesg tail

## Guardrails

- Do not open `/dev/subsys_modem`.
- Do not open `/dev/subsys_esoc0`.
- Do not start Wi-Fi HAL, `wificond`, `IWifi.start`, or `qcwlanstate`.
- Do not scan/connect, use credentials, run DHCP/routes, or external ping.
- Do not write firmware, partitions, boot images, sysfs, debugfs, or GPIO.

## Success Criteria

V1112 passes if it can select the next route from current evidence without
mutating device state:

```text
V1061 global firmware + modem holder prerequisite
  +
V1111 CNSS PM connect trigger
  ->
V1113 combined bounded gate before Wi-Fi HAL
```

## Expected Next

If the classifier passes, V1113 should be source/build-only first: add a
PM-service observer order that installs global firmware mounts and a bounded
`/dev/subsys_modem` holder before service-manager/PM/CNSS PM-connect probing,
while still forbidding eSoC, Wi-Fi HAL, scan/connect, DHCP, credentials, and
external ping.
