# V1031 Helper v175 Deploy

- date: `2026-05-26`
- scope: deploy-only
- helper: `a90_android_execns_probe v175`
- decision: `execns-helper-v175-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v1031-execns-helper-v175-deploy/manifest.json`

## Summary

Helper `v175` was deployed to `/cache/bin/a90_android_execns_probe` and verified
by remote sha and usage/contract parity. No daemon, PM actor proof, Wi-Fi HAL,
scan/connect, credential use, DHCP/route, external ping, boot image write, or
partition write occurred.

## Result

| Item | Value |
| --- | --- |
| decision | `execns-helper-v175-deploy-pass` |
| remote sha | `9036bb15ced9fb1098c4375c15c2c729502c841574ae14798fb331fc29c89e42` |
| transfer | `serial appendfile + uudecode` |
| chunks written | `886` |
| encoded bytes | `1637328` |
| daemon start | `False` |
| Wi-Fi bring-up | `False` |
| device mutation | `/cache/bin/a90_android_execns_probe` replacement only |

Postflight checks passed:

- native health: `BOOT OK`, selftest `fail=0`
- service-manager experiment process count: `0`
- Wi-Fi link surface count: `0`
- remote helper sha: matched
- remote helper contract: `v175`, service-manager matrix mode,
  `--require-android-selinux-exec-match`, PM full-contract order

## Guardrails

- no service-manager/CNSS/Wi-Fi HAL live start
- no `wificond`, scan/connect/link-up
- no credentials
- no DHCP/route/external ping
- no eSoC ioctl/subsystem open
- no GPIO/sysfs/debugfs write
- no boot image or partition write

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py
python3 scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py plan
python3 scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py preflight
python3 scripts/revalidation/native_wifi_helper_v175_deploy_v1031.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v1031 deploy execns helper v175 only; no daemon start and no Wi-Fi bring-up" \
  run
python3 scripts/revalidation/a90ctl.py --timeout 5 bootstatus
python3 scripts/revalidation/a90ctl.py --timeout 5 selftest
```

Result:

```text
decision: execns-helper-v175-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Post-deploy health:

```text
boot: BOOT OK shell
selftest: pass=11 warn=1 fail=0
```

## Next

V1032 should run a bounded domain-guarded PM full-contract proof using helper
`v175`. It must use `--require-android-selinux-exec-match` and treat an
`attr/exec` mismatch as a safe runtime-domain blocker before executing PM
actors.
