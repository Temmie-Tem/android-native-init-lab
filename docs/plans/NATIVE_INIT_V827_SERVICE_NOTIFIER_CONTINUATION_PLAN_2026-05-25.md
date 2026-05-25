# Native Init V827 Service-Notifier Continuation Classifier Plan

## Goal

Map V826's visible QRTR service-locator and service-notifier endpoints onto the
Samsung OSRC ICNSS continuation path, then decide the next gate before any QMI
payload or Android Wi-Fi component.

## Scope

- Target runner:
  - `scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py`
- Inputs:
  - `tmp/wifi/v826-qrtr-event-detail-classifier/manifest.json`
  - Samsung OSRC source under `kernel_build/SM-A908N_KOR_12_Opensource/Kernel`
- Source anchors:
  - `icnss.c`
  - `icnss_qmi.c`
  - `service-locator.c`
  - `service-notifier.c`
  - `sysmon-qmi.c`
  - `wlan_firmware_service_v01.h`

## Hard Gates

- Host-only analysis.
- No bridge command, device command, reboot, bootloader handoff, boot image
  write, partition write, or custom kernel flash.
- No QRTR socket open or QRTR/QMI packet transmission.
- No service-manager, Wi-Fi HAL, scan/connect/link-up, credential use, DHCP,
  route change, or external ping.

## Success Criteria

- V826 manifest exists and passed with decision
  `v826-qrtr-event-details-classified`.
- Visible control endpoints include service-locator `64/257` and
  service-notifier `66/46081`.
- SSCTL `43/4098`, service-notifier `66/18945`, and WLFW `69/1` remain absent
  in V826 evidence.
- Source anchors prove the ICNSS continuation path:
  - `get_service_location("ICNSS-WLAN", "wlan/fw")`
  - service-locator `GET_DOMAIN_LIST`
  - `service_notif_register_notifier()` for returned domains
  - service-notifier `REGISTER_LISTENER`
  - WLFW `69/1` lookup
- Guardrails remain false for device commands, QMI payloads, Wi-Fi HAL,
  scan/connect, external ping, custom kernel flash, boot image write, and
  partition write.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py

python3 scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py \
  --out-dir tmp/wifi/v827-service-notifier-continuation-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_service_notifier_continuation_classifier_v827.py \
  run
```

## Next

V828 should derive the bounded service-locator `GET_DOMAIN_LIST` request for
`wlan/fw` before any live QMI payload is attempted. A later live probe should be
strictly bounded and still avoid service-manager, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, boot image writes, partition writes,
and custom kernel flashes.
