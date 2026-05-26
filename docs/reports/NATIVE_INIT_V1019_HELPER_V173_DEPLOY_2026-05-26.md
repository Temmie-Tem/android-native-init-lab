# V1019 Helper v173 Deploy

- date: `2026-05-26`
- scope: deploy-only helper replacement
- decision: `execns-helper-v173-deploy-pass`
- pass: `True`
- evidence: `tmp/wifi/v1019-execns-helper-v173-deploy/manifest.json`

## Summary

V1019 deployed `a90_android_execns_probe v173` to:

```text
/cache/bin/a90_android_execns_probe
```

No daemon, service-manager, Wi-Fi HAL, `wificond`, CNSS, scan/connect, DHCP,
route, or external ping was executed.

## Deploy Evidence

| Item | Value |
| --- | --- |
| local artifact | `tmp/wifi/v1018-execns-helper-v173-build/a90_android_execns_probe` |
| expected sha256 | `63a2110d4b082ee6f1cd07d28c6d55e59335d0378089dac71824aff8f3903884` |
| transfer method | serial appendfile + uudecode |
| chunk size | `1850` |
| chunks written | `886` |
| line check | pass |
| remote sha | match |
| remote marker | `a90_android_execns_probe v173` |
| remote order token | `after-mdm-helper-esoc-fd-with-wifi-surface-subsys-window` |
| remote gate token | `post-upper-surface-no-wlfw` |

## Health

Postflight remained healthy:

- native health: pass
- service-manager process surface: clean
- Wi-Fi link surface: clean
- remote helper contract: pass

## Guardrails

- `daemon_start_executed=False`
- `wifi_bringup_executed=False`
- no service-manager/CNSS/Wi-Fi HAL/`wificond` live start
- no `/dev/esoc-0` or `/dev/subsys_esoc0` live open
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no eSoC ioctl, notify, BOOT_DONE, GPIO/sysfs/debugfs write
- no boot image, partition, or firmware write

## Validation

Commands:

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

Result:

```text
decision: execns-helper-v173-deploy-pass
pass: True
next: run V1020 bounded after-fd subsystem-window live gate
```

## Next

Proceed to V1020 bounded live scoped subsystem-window gate.
