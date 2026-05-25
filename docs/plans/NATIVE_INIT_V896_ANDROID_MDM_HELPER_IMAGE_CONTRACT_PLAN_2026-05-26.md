# V896 Android mdm_helper Image Contract Plan

## Goal

Classify, host-only, whether existing Android evidence already explains why
native V895 `ESOC_IMG_XFER_DONE` did not make GPIO 142 `mdm status` fire.

## Inputs

- Native negative control:
  `tmp/wifi/v895-mdm2ap-irq-snapshot-live/manifest.json`
- Android positive-control provider surface:
  `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/manifest.json`
- Android eSoC actor surface:
  `tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/manifest.json`
- ESOC source anchors:
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/include/uapi/linux/esoc_ctrl.h`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-pon.c`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-4x.c`

## Method

1. Parse V895 for `ESOC_IMG_XFER_DONE`, `GET_STATUS=0`, blocked
   `BOOT_DONE`, and GPIO 142 IRQ delta `0`.
2. Parse V852 for Android `mdm3=ONLINE`, WLFW/BDF/`wlan0` positive markers,
   GPIO debug/pinctrl surfaces, and `/proc/interrupts` GPIO 142 count.
3. Parse V853 for Android `mdm_helper`, `ks`, `pm-service`, `/dev/esoc-0`,
   `/dev/subsys_esoc0`, `/dev/subsys_modem`, SELinux, and init/ueventd
   surfaces.
4. Correlate source comments and ioctl constants showing that
   `ESOC_REQ_IMG` asks userspace to confirm link establishment before
   `ESOC_IMG_XFER_DONE`.

## Hard Gates

- No Android boot, ADB command, Magisk module, or new device contact.
- No live eSoC ioctl, `/dev/subsys_esoc0` open, `mdm_helper` start, `ks`
  start, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  external ping, boot image write, partition write, firmware mutation, GPIO
  write, sysfs write, or debugfs write.

## Success Criteria

- Host-only classifier produces private evidence.
- Android positive path proves GPIO 142 `mdm status` IRQ count `>0`.
- V895 negative path proves native immediate image-done keeps GPIO 142 IRQ
  delta `0`.
- Android actor evidence proves `mdm_helper` and `ks` hold `/dev/esoc-0`, and
  `ks` uses the MHI pipe/image path.
- Source markers support the image/link-establishment interpretation.

## Next

If classified, V897 should design a fail-closed native `mdm_helper`/`ks`
contract preflight. Do not retry blind image-done, blind `BOOT_DONE`, generic
command-engine expansion, or Wi-Fi HAL bring-up.
