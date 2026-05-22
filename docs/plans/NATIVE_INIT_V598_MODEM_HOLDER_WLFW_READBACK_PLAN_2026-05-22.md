# Native Init V598 Modem Holder WLFW Readback Plan

- date: `2026-05-22 KST`
- status: `executed`; bounded live proof
- scope: V596 lower precondition plus WLFW QRTR nameservice readback

## Objective

After V597 showed the post-sysmon gap, prove whether WLFW service registration
is visible from native while the V596 modem-holder companion window is active.

## Inputs

- V596 modem-holder companion proof:
  `tmp/wifi/v596-modem-holder-companion-proof/manifest.json`
- V597 post-sysmon classifier:
  `tmp/wifi/v597-post-sysmon-gap/manifest.json`
- Current-boot V490 SELinux policy-load proof:
  `tmp/wifi/v598-v490-current-run/manifest.json`

## Method

1. Mount Android system read-only and load Android SELinux policy through V490.
2. Reuse V596 lower precondition:
   - global read-only `/vendor/firmware_mnt`
   - global read-only `/vendor/firmware-modem`
   - temporary `subsys_modem` holder
   - QRTR RX gate before companion start
3. Start the bounded companion stack only:
   `qrtr-ns`, `rmt_storage`, `tftp_server`, `pd-mapper`, `cnss_diag`,
   `cnss-daemon`.
4. Send only QRTR nameservice `NEW_LOOKUP` / `DEL_LOOKUP` for WLFW service `69`
   instances `0` and `1`.
5. Reboot as cleanup boundary.

## Guardrails

- No `esoc0` open.
- No QMI payload.
- No service-manager, Wi-Fi HAL, `IWifi.start()`, or `qcwlanstate`.
- No scan/connect/link-up.
- No credentials, DHCP, routing, or external ping.
- No boot image or persistent partition writes.

## Source Notes

- Qualcomm `sysmon-qmi` logs the SSCTL new-server callback when QMI service
  registration is seen.
- Qualcomm `service-notifier` connects to service instances and registers
  listener callbacks for service state indications.
- Primary references:
  - `https://android.googlesource.com/kernel/msm.git/+/330705db41eb77d77476c5fccf3527f5db1d1525/drivers/soc/qcom/sysmon-qmi.c`
  - `https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/service-notifier.c`

## Success Criteria

- Cleanup returns native init healthy.
- `qmi_attempted=0`.
- QRTR readback sends and returns either:
  - WLFW service events, allowing a next bounded CNSS/HAL gate; or
  - clean end-of-list/timeout, proving WLFW service registration is still
    absent in the current native window.
