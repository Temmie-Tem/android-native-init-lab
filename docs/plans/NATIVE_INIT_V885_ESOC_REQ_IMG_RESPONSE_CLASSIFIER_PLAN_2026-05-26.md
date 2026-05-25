# V885 ESOC_REQ_IMG Response Classifier Plan

## Goal

Classify the response contract for the `ESOC_REQ_IMG` request observed in V884.
This is host-only and must not contact the device or execute live eSoC ioctls.

## Inputs

- V884 live manifest:
  `tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json`
- local A90 UAPI:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h`
- staged OSRC eSoC sources:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/`
- classifier:
  `scripts/revalidation/native_wifi_esoc_req_img_response_classifier_v885.py`

## Method

1. Parse V884 observer fields.
2. Confirm that `rc=4`, `errno=0`, `value=1` maps to `ESOC_REQ_IMG`.
3. Confirm source anchors for request FIFO return semantics.
4. Confirm kernel response hooks for `ESOC_IMG_XFER_DONE` and
   `ESOC_BOOT_DONE`.
5. Select the next source/build-only helper change before any new live
   `ESOC_NOTIFY` attempt.

## Hard Gates

- Host-only.
- No bridge/device command.
- No live `REG_REQ_ENG`, `WAIT_FOR_REQ`, `ESOC_NOTIFY`, `CMD_EXE`, or
  `/dev/subsys_esoc0` open.
- No Android actor, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping.

## Success Criteria

- Decision is `v885-esoc-req-img-response-contract-classified`.
- V884 `ESOC_REQ_IMG` observation is confirmed from current evidence.
- Local source anchors explain why `WAIT_FOR_REQ` returned rc `4`.
- Local source anchors expose both `ESOC_IMG_XFER_DONE` and `ESOC_BOOT_DONE`
  response hooks.

## Next

If V885 passes, V886 should be source/build-only helper `v140`: repair
`WAIT_FOR_REQ` semantic labelling and add a guarded response-mode scaffold.
Live `ESOC_NOTIFY` must remain blocked until the new helper path is built,
deployed, and separately approved as a bounded live gate.
