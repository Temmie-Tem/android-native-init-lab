# V1019 Helper v173 Deploy Plan

- date: `2026-05-26`
- type: deploy-only
- selected after: V1018 helper `v173` source/build pass
- local artifact: `tmp/wifi/v1018-execns-helper-v173-build/a90_android_execns_probe`
- remote target: `/cache/bin/a90_android_execns_probe`

## Objective

Deploy helper `a90_android_execns_probe v173` to the native init device without
starting service-manager, Wi-Fi HAL, `wificond`, CNSS, scan/connect, or Wi-Fi
bring-up.

## Inputs

- Build artifact sha256:
  `63a2110d4b082ee6f1cd07d28c6d55e59335d0378089dac71824aff8f3903884`
- Helper marker:
  `a90_android_execns_probe v173`
- Required order token:
  `after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window`
- Required gate token:
  `post-upper-surface-no-wlfw`

## Method

Use a deploy-only wrapper:

```text
scripts/revalidation/native_wifi_helper_v173_deploy_v1019.py
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
- no `/dev/esoc-0` or `/dev/subsys_esoc0` live open
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no eSoC ioctl, notify, BOOT_DONE, GPIO/sysfs/debugfs write
- no boot image, partition, or firmware write

## Serial Transfer

Use the console-safe chunk size:

```text
--serial-chunk-size 1850
```

## Success Criteria

- plan passes
- preflight passes
- deploy result `ok=True`
- postflight remote sha matches the local artifact
- remote usage exposes helper `v173`
- remote usage exposes the new subsystem-window order
- remote usage exposes the new `post-upper-surface-no-wlfw` gate
- `daemon_start_executed=False`
- `wifi_bringup_executed=False`

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v173_deploy_v1019.py
python3 scripts/revalidation/native_wifi_helper_v173_deploy_v1019.py plan
python3 scripts/revalidation/native_wifi_helper_v173_deploy_v1019.py preflight
python3 scripts/revalidation/native_wifi_helper_v173_deploy_v1019.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v1019 deploy execns helper v173 only; no daemon start and no Wi-Fi bring-up" \
  --serial-chunk-size 1850 \
  run
```
