# Native Init V599 Service-Notifier Instance Gap Plan

- date: `2026-05-22 KST`
- status: `executed`; host-only classifier
- scope: Android reference versus V598 native service-registration coverage

## Objective

Classify why V598 advanced from `sysmon-qmi` to service-notifier instance `180`
but still did not publish WLAN-PD, WLFW service `69`, BDF, or `wlan0`.

## Inputs

- Android Wi-Fi/CNSS dmesg reference:
  `tmp/wifi/v515-android-native-sequence-delta/inputs/android-dmesg-wifi-cnss-tail.txt`
- V597 post-sysmon timing classifier:
  `tmp/wifi/v597-post-sysmon-gap/manifest.json`
- V598 modem-holder WLFW readback:
  `tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json`
- V598 native dmesg delta:
  `tmp/wifi/v598-modem-holder-wlfw-readback/native/dmesg-delta.txt`

## Method

1. Parse Android reference markers for:
   - `sysmon-qmi` modem/slpi/cdsp/adsp/esoc0 SSCTL services
   - service-notifier instances `180` and `74`
   - WLAN-PD indication and ACK
   - `icnss_qmi` server connection, BDF, FW-ready, and `wlan0`
2. Parse V598 native markers for the same timeline.
3. Preserve V598 WLFW QRTR readback values for service `69` instances `0` and
   `1`.
4. Classify whether the remaining blocker is:
   - service-notifier instance coverage,
   - WLAN-PD indication after service-notifier,
   - WLFW service publication,
   - or an input/regression review.

## Guardrails

- Host-only; no device command.
- No QRTR or QMI packet.
- No daemon start.
- No service-manager, Wi-Fi HAL, or `qcwlanstate`.
- No scan/connect/link-up.
- No credential, DHCP, route, or external ping.
- No boot image or persistent partition writes.

## Source Notes

- Qualcomm `sysmon-qmi` registers a QMI new-server callback for SSCTL service
  discovery and logs when a subsystem SSCTL service is connected.
- Qualcomm `service-notifier` creates QMI clients per service instance and logs
  when a QMI handle connects to that instance.
- Qualcomm `icnss_qmi` registers WLFW service lookup and posts a server-arrive
  event when the WLFW server is visible.
- Primary references:
  - `https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/service-notifier.c`
  - `https://android.googlesource.com/kernel/msm.git/+/330705db41eb77d77476c5fccf3527f5db1d1525/drivers/soc/qcom/sysmon-qmi.c`
  - `https://android.googlesource.com/kernel/msm.git/+/03c2d42aa4bc362578b3824a81583638e2e23151/drivers/soc/qcom/icnss_qmi.c`

## Success Criteria

- The classifier writes private evidence under
  `tmp/wifi/v599-service-notifier-instance-gap/`.
- `device_commands_executed=False`.
- `wifi_bringup_executed=False`.
- The decision identifies whether native V598 is missing only the second
  service-notifier instance or a broader sysmon/service-registry matrix.

## Expected Next Gate

If V599 confirms `180`-only native coverage, the next live gate should be a
bounded service-registry/sysmon instance matrix. It should not retry
`qcwlanstate`, Wi-Fi HAL, scan, connect, or external ping until WLAN-PD/WLFW/BDF
or `wlan0` readiness appears.
