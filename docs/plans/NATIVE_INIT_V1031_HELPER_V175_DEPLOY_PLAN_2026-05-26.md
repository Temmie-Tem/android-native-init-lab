# V1031 Helper v175 Deploy Plan

- date: `2026-05-26`
- type: deploy-only
- input: `docs/reports/NATIVE_INIT_V1030_PM_RUNTIME_DOMAIN_GUARD_SUPPORT_2026-05-26.md`
- local artifact: `tmp/wifi/v1030-execns-helper-v175-build/a90_android_execns_probe`
- expected sha256: `9036bb15ced9fb1098c4375c15c2c729502c841574ae14798fb331fc29c89e42`

## Objective

Deploy helper `a90_android_execns_probe v175` to
`/cache/bin/a90_android_execns_probe` and verify remote sha/usage parity without
starting PM actors, daemons, Wi-Fi HAL, or Wi-Fi bring-up.

## Guardrails

- deploy-only replacement of `/cache/bin/a90_android_execns_probe`
- no service-manager/CNSS/Wi-Fi HAL live start
- no `wificond`, scan/connect/link-up, credentials, DHCP, route, or external ping
- no eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write
- no boot image or partition write

## Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py
python3 scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py plan
python3 scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py preflight
python3 scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v1031 deploy execns helper v175 only; no daemon start and no Wi-Fi bring-up" \
  run
```

## Success Criteria

- Local helper exists, is static, and matches expected sha.
- Remote helper sha matches expected sha after deploy.
- Remote usage includes `a90_android_execns_probe v175`,
  `wifi-companion-mdm-helper-cnss-service-manager-matrix`,
  `--require-android-selinux-exec-match`, and the PM full-contract order enum.
- Native postflight health remains `BOOT OK`, selftest `fail=0`.
- No daemon start or Wi-Fi bring-up occurred.

## Next

If V1031 passes, V1032 should run a bounded domain-guarded PM full-contract
proof. It must pass `--require-android-selinux-exec-match` and stop before
unsafe PM actor execution if `attr/exec` is still not the requested Android
context.
