# V1040 Helper v177 Deploy Plan

- date: `2026-05-26`
- type: deploy-only live gate
- selected after: V1039 PM proxy context parity support

## Objective

Deploy the verified helper `v177` artifact to `/cache/bin/a90_android_execns_probe`
without starting PM actors, service-manager, CNSS, Wi-Fi HAL, scan/connect, or
network bring-up.

## Inputs

- local artifact:
  `tmp/wifi/v1039-execns-helper-v177-build/a90_android_execns_probe`
- expected sha256:
  `d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795`
- deploy wrapper:
  `scripts/revalidation/native_wifi_helper_v177_deploy_v1040.py`

## Method

1. Run deploy preflight against the current native device.
2. Confirm native health, no active service-manager experiment, no Wi-Fi link
   surface, and local helper marker/sha/usage contract.
3. Install helper `v177` to `/cache/bin/a90_android_execns_probe`.
4. Read back remote sha and usage contract.
5. Capture post-deploy native health.

## Hard Gates

- Deploy-only.
- No actor start, daemon start, service-manager start, Wi-Fi HAL, `wificond`,
  scan/connect/link-up, credentials, DHCP/routes, external ping, boot image
  write, partition write, firmware mutation, GPIO/sysfs/debugfs write, eSoC
  ioctl, or live `/dev/subsys_esoc0` open.

## Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v177_deploy_v1040.py
python3 scripts/revalidation/native_wifi_helper_v177_deploy_v1040.py preflight
python3 scripts/revalidation/native_wifi_helper_v177_deploy_v1040.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v1040 deploy execns helper v177 only; no daemon start and no Wi-Fi bring-up" \
  run
```

## Success Criteria

- Preflight passes.
- Remote helper sha matches the V1039 artifact sha.
- Remote usage confirms `a90_android_execns_probe v177` and PM full-contract
  order support.
- Post-deploy health remains clean.

## Next

If V1040 passes, V1041 should rerun the bounded PM full-contract live proof with
helper `v177`, still without scan/connect/link-up or external ping.
