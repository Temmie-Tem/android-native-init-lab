# V893 eSoC Post Image-done Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| classifier | `tmp/wifi/v893-esoc-post-img-xfer-classifier/manifest.json` | `v893-post-img-xfer-status-line-classified` |

V893 is host-only. It used V891 evidence plus staged ESOC source to classify why
`ESOC_GET_STATUS` stayed `0` after `ESOC_IMG_XFER_DONE`.

## Findings

V891 evidence:

- `ESOC_REQ_IMG` was observed.
- `ESOC_IMG_XFER_DONE` was sent with rc `0`, errno `0`.
- `ESOC_GET_STATUS` was polled `87` times and stayed value `0`.
- `ESOC_BOOT_DONE` was not sent.
- cleanup reboot restored healthy native state.

Source-backed classification:

- `ESOC_IMG_XFER_DONE` is not a readiness setter.
- In `esoc-mdm-4x.c`, `ESOC_IMG_XFER_DONE` schedules delayed
  `mdm2ap_status_check_work` when `MDM2AP_STATUS` is still low.
- Readiness is reached when `MDM2AP_STATUS` transitions high, setting
  `mdm->ready = true`.
- `ESOC_BOOT_DONE` only sends `ESOC_RUN_STATE`; blind `BOOT_DONE` would
  synthesize state without proving modem readiness.

## Interpretation

The blocker moved again:

1. `REG_REQ_ENG` works.
2. `/dev/subsys_esoc0` triggers `ESOC_REQ_IMG`.
3. `ESOC_NOTIFY(ESOC_IMG_XFER_DONE)` works.
4. The missing transition is MDM2AP status/ready after image-done.

This means the next useful test is not another blind notify retry. The next
gate must observe or reproduce the condition that makes `MDM2AP_STATUS` go high
after image-done.

## Guardrails

- no device command
- no live eSoC ioctl
- no `/dev/subsys_esoc0` open
- no `ESOC_NOTIFY`
- no Android actor start
- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping

## Next

V894 should plan a bounded MDM2AP status/ready observer. If no read-only status
surface exists, the next host-only step should compare Android `mdm_helper`
behavior around the image-done to ready transition before any new live action.
