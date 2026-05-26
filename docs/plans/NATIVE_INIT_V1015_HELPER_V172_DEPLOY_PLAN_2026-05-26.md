# V1015 Helper v172 Deploy Plan

- date: `2026-05-26`
- type: deploy-only
- selected after: V1014 helper `v172` source/build pass
- local artifact: `tmp/wifi/v1014-execns-helper-v172-build/a90_android_execns_probe`
- remote target: `/cache/bin/a90_android_execns_probe`

## Objective

Deploy helper `a90_android_execns_probe v172` to the native init device without
starting service-manager, CNSS, Wi-Fi HAL, `wificond`, scan/connect, or Wi-Fi
bring-up.

## Inputs

- Build artifact sha256:
  `0c9b6d34be91211255a1359198329405806092fb9b4eeb4f24d3089e878df54d`
- Helper marker:
  `a90_android_execns_probe v172`
- Required order token:
  `after-mdm-helper-esoc-fd-with-wifi-surface`

## Method

Use a deploy-only wrapper:

```text
scripts/revalidation/native_wifi_helper_v172_deploy_v1015.py
```

Sequence:

1. run plan mode
2. run preflight mode
3. verify native health and no active Wi-Fi/service-manager surface
4. serial install the helper to `/cache/bin/a90_android_execns_probe`
5. run postflight sha/usage/health checks

## Hard Gates

- no service-manager start
- no CNSS daemon start
- no Wi-Fi HAL or `wificond` start
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no eSoC ioctl, subsystem open, notify, BOOT_DONE, GPIO/sysfs/debugfs write
- no boot image, partition, or firmware write

## Serial Transfer

The helper uses the native console safe line limit. The attempted
`--serial-chunk-size 3000` is unsafe for the current console limit, so the live
deploy must use the safe `1850` chunk size unless NCM transfer is available.

## Success Criteria

- preflight passes
- deploy result `ok=True`
- postflight remote sha matches the local artifact
- remote helper usage exposes `a90_android_execns_probe v172`
- remote helper usage exposes
  `after-mdm-helper-esoc-fd-with-wifi-surface`
- `daemon_start_executed=False`
- `wifi_bringup_executed=False`

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v172_deploy_v1015.py
python3 scripts/revalidation/native_wifi_helper_v172_deploy_v1015.py plan
python3 scripts/revalidation/native_wifi_helper_v172_deploy_v1015.py preflight
python3 scripts/revalidation/native_wifi_helper_v172_deploy_v1015.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v1015 deploy execns helper v172 only; no daemon start and no Wi-Fi bring-up" \
  --serial-chunk-size 1850 \
  run
```
