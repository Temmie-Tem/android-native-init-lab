# V885 ESOC_REQ_IMG Response Classifier Report

## Summary

V885 classified the V884 eSoC request path host-only. The important correction is
that V884 did not observe an ioctl failure: `ESOC_WAIT_FOR_REQ` returned a
nonnegative byte count for one `u32` request, and the copied value was
`ESOC_REQ_IMG`.

Decision:

- `v885-esoc-req-img-response-contract-classified`
- pass: `true`

Evidence:

- `tmp/wifi/v885-esoc-req-img-response-classifier/manifest.json`
- `tmp/wifi/v885-esoc-req-img-response-classifier/summary.md`
- classifier: `scripts/revalidation/native_wifi_esoc_req_img_response_classifier_v885.py`

## Inputs

- V884 live manifest:
  `tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json`
- local A90 eSoC UAPI:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h`
- staged Samsung OSRC eSoC source:
  `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/`

## Findings

- V884 `REG_REQ_ENG` returned rc `0`.
- V884 passive `ESOC_WAIT_FOR_REQ` returned rc `4`, errno `0`, value `1`.
- `esoc_dev.c` copies one `u32` from the request FIFO with
  `kfifo_out_spinlocked()`, writes it to userspace with `put_user()`, and
  returns the nonnegative byte count.
- `esoc_ctrl.h` maps value `1` to `ESOC_REQ_IMG`.
- `esoc-mdm-pon.c` can queue `ESOC_REQ_IMG` for the SDX50M path.
- `esoc-mdm-4x.c` exposes response handling for `ESOC_IMG_XFER_DONE` and
  `ESOC_BOOT_DONE`.

## Interpretation

The next blocker is no longer whether SDX50M emits an image request. It does.
The blocker is that native init has not implemented the Android-equivalent
response path after `ESOC_REQ_IMG`. Repeating a bare `/dev/subsys_esoc0` open
will re-enter the same D-state because the kernel is waiting for the request
consumer side.

## Guardrails

V885 was host-only:

- no bridge command
- no device contact
- no live eSoC ioctl
- no `/dev/subsys_esoc0` open
- no `ESOC_NOTIFY`
- no Android actor, service-manager, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, or external ping

## Next

V886 should be source/build-only helper `v140`:

- repair helper labelling so `WAIT_FOR_REQ rc=4 errno=0 value=1` is reported as
  `request-observed: ESOC_REQ_IMG`, not `ioctl-error`
- add a fail-closed response-mode scaffold for future `ESOC_REQ_IMG` handling
- keep live `ESOC_NOTIFY` blocked until a separate deploy gate and bounded live
  response proof exist
