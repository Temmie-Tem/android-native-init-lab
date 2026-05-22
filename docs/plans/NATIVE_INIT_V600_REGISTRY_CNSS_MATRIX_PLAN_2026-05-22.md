# Native Init V600 Registry/CNSS Matrix Plan

- date: `2026-05-22 KST`
- status: `executed`; host-only classifier
- scope: V598/V599 evidence matrix for service-registry and CNSS runtime gaps

## Objective

Turn the V599 `service-notifier 180`-only finding into a concrete next live
gate by comparing Android and native coverage across:

- QRTR/sysmon/service-notifier registrations,
- CNSS userspace startup,
- WLFW thread entry,
- WLAN-PD, QMI, BDF, FW-ready, and `wlan0`.

## Inputs

- Android Wi-Fi/CNSS dmesg reference:
  `tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt`
- V598 modem-holder WLFW readback:
  `tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json`
- V598 native dmesg delta:
  `tmp/wifi/v598-modem-holder-wlfw-readback/native/dmesg-delta.txt`
- V598 companion transcript:
  `tmp/wifi/v598-modem-holder-wlfw-readback/native/companion-start-only-with-holder.txt`
- V599 service-notifier classifier:
  `tmp/wifi/v599-service-notifier-instance-gap/manifest.json`

## Method

1. Parse Android and native marker coverage for QRTR, `sysmon-qmi`,
   service-notifier, CNSS, WLFW, BDF, FW-ready, and `wlan0`.
2. Count native-only failure markers, especially `cnss-daemon` binder failures.
3. Preserve V598 WLFW QRTR readback state for service `69`.
4. Classify whether the next live gate should target:
   - service-registry/sysmon instance publication,
   - CNSS daemon runtime/binder dependency,
   - or a broader WLFW/QMI path.

## Guardrails

- Host-only; no device command.
- No QRTR or QMI packet.
- No daemon start.
- No service-manager, Wi-Fi HAL, or `qcwlanstate`.
- No scan/connect/link-up.
- No credential, DHCP, route, or external ping.
- No boot image or persistent partition writes.

## Source Notes

- Qualcomm `sysmon-qmi` logs SSCTL service new-server callbacks.
- Qualcomm `service-notifier` logs QMI service instance connections and service
  state indications such as WLAN-PD.
- Qualcomm `icnss_qmi` registers WLFW service lookup and posts server-arrive
  work when WLFW becomes visible.
- Primary references:
  - `https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/service-notifier.c`
  - `https://android.googlesource.com/kernel/msm.git/+/330705db41eb77d77476c5fccf3527f5db1d1525/drivers/soc/qcom/sysmon-qmi.c`
  - `https://android.googlesource.com/kernel/msm.git/+/03c2d42aa4bc362578b3824a81583638e2e23151/drivers/soc/qcom/icnss_qmi.c`

## Success Criteria

- The classifier writes private evidence under
  `tmp/wifi/v600-registry-cnss-matrix/`.
- `device_commands_executed=False`.
- `wifi_bringup_executed=False`.
- The decision identifies the highest-value next live blocker without
  broadening into Wi-Fi HAL, scan, connect, credentials, DHCP, routing, or
  external ping.

## Expected Next Gate

If V600 shows `cnss-daemon` starts but never reaches `wlfw_start`, the next live
gate should be a bounded service-manager/binder dependency proof around CNSS
daemon. It should preserve the V598 lower-readiness path and still block
`qcwlanstate`, Wi-Fi HAL, scan/connect, and external ping.
