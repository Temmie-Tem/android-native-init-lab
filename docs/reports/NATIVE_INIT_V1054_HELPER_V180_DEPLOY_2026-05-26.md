# V1054 Helper v180 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy-only | `tmp/wifi/v1054-execns-helper-v180-deploy/manifest.json` | `execns-helper-v180-deploy-pass` |

V1054 deployed helper `v180` to `/cache/bin/a90_android_execns_probe`. Remote
sha and usage contract match the V1053 artifact, with no daemon start or Wi-Fi
bring-up.

## Findings

- Local/remote helper sha256:
  `f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641`
- Marker: `a90_android_execns_probe v180`
- Deploy method: `serial appendfile + uudecode`
- Chunks written: `886`
- Postflight checks:
  - `native-health`: pass
  - `service-manager-processes-clean`: pass
  - `wifi-link-surface-clean`: pass
  - `remote-helper-v180`: pass
- Post-deploy selftest:
  - `selftest: pass=11 warn=1 fail=0`

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_helper_v180_deploy_v1054.py
python3 scripts/revalidation/native_wifi_helper_v180_deploy_v1054.py preflight
python3 scripts/revalidation/native_wifi_helper_v180_deploy_v1054.py \
  --approval-phrase "approve v1054 deploy execns helper v180 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/a90ctl.py --hide-on-busy selftest
```

## Guardrails

No service-manager, CNSS daemon, Wi-Fi HAL, `wificond`, scan/connect,
credentials, DHCP/routes, external ping, eSoC ioctl, subsystem open, GPIO write,
sysfs write, debugfs write, boot image write, partition write, or firmware
mutation occurred. Only `/cache/bin/a90_android_execns_probe` was replaced.

## Next

V1055 should rerun the bounded live gate with helper `v180` and inspect:

```text
modem_pre_holder_nonblock_errno
modem_pre_holder_plain_retry
modem_pre_holder_first_errno
modem_pre_holder_confirmed
pm_full_contract_seen
```
