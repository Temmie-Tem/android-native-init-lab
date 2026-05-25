# V893 eSoC Post Image-done Classifier Plan

## Goal

Classify why `ESOC_GET_STATUS` stayed not-ready after V891 successfully sent
`ESOC_IMG_XFER_DONE`.

## Inputs

- V891 live evidence:
  `tmp/wifi/v891-esoc-conditional-response-live-v142/manifest.json`
- staged ESOC source:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/`
- classifier:
  `scripts/revalidation/native_wifi_esoc_post_img_xfer_classifier_v893.py`

## Method

Host-only classification:

1. Read V891 conditional response evidence.
2. Confirm `ESOC_IMG_XFER_DONE` was sent and `ESOC_GET_STATUS` stayed `0`.
3. Inspect ESOC source markers for:
   - `ESOC_REQ_IMG`
   - `ESOC_IMG_XFER_DONE`
   - `ESOC_GET_STATUS`
   - `ESOC_BOOT_DONE`
   - `MDM2AP_STATUS` readiness handling
4. Produce a source-backed next gate.

## Hard Gates

- No device command.
- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No `ESOC_NOTIFY`.
- No actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping.

## Success Criteria

- Decision is `v893-post-img-xfer-status-line-classified`.
- The classifier proves `ESOC_IMG_XFER_DONE` does not directly set ready.
- The classifier identifies the next blocker as the MDM2AP status/ready
  transition after image-done.

## Next

Plan a bounded observer for the MDM2AP status/ready transition. Do not use
blind `BOOT_DONE`, actor/HAL start, scan/connect, credentials, DHCP/routes, or
external ping for that gate.
