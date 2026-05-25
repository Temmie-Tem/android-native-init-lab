# V894 MDM2AP Ready Surface Classifier Plan

## Goal

Find a safe observer surface for the MDM2AP status/ready transition identified
by V893.

## Inputs

- V893 classifier evidence:
  `tmp/wifi/v893-esoc-post-img-xfer-classifier/manifest.json`
- staged DTS/source:
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-4x.c`
- classifier:
  `scripts/revalidation/native_wifi_mdm2ap_ready_surface_v894.py`

## Method

1. Confirm DTS maps `mdm2ap-status-gpio` to GPIO `142`.
2. Confirm source sets readiness after `MDM2AP_STATUS` high.
3. Read current native sysfs/eSoC state.
4. Read `/proc/interrupts` and locate the `mdm status` IRQ line.
5. Classify whether a read-only observer exists for the next live proof.

## Hard Gates

- No device mutation.
- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No `ESOC_NOTIFY`.
- No GPIO export/write, debugfs write, sysfs write, actor start, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping.

## Success Criteria

- Decision is `v894-mdm2ap-ready-surface-classified`.
- DTS proves `mdm2ap-status-gpio = 142`.
- Current native `/proc/interrupts` exposes a read-only `mdm status` line for
  GPIO `142`.
- Next live gate is limited to sampling this observer around the existing
  guarded `IMG_XFER_DONE` flow.

## Next

V895 should add bounded `mdm status` IRQ snapshots before
`ESOC_IMG_XFER_DONE`, during `GET_STATUS` polling, and after cleanup. Blind
`BOOT_DONE`, actor/HAL start, scan/connect, credentials, DHCP/routes, and
external ping remain blocked.
