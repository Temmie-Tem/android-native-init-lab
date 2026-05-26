# V1051 Helper v179 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| deploy-only | `tmp/wifi/v1051-execns-helper-v179-deploy/manifest.json` | `execns-helper-v179-deploy-pass` |

V1051 deployed helper `v179` to `/cache/bin/a90_android_execns_probe`. Remote
sha and usage contract now match the V1050 artifact, with no Android daemon or
Wi-Fi bring-up executed.

## Findings

- Local helper:
  - sha256: `9cb6d49849af181a87a5619e7b3ed7f0f513223ef97ce8b0599ce43694453a7b`
  - marker: `a90_android_execns_probe v179`
  - usage contains `--allow-pm-full-contract-with-modem-holder`
  - usage contains `after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder`
- Deploy result:
  - method: `serial appendfile + uudecode`
  - chunks written: `886`
  - encoded bytes: `1637328`
  - line check: `ok`
- Postflight checks:
  - `native-health`: pass
  - `service-manager-processes-clean`: pass
  - `wifi-link-surface-clean`: pass
  - `remote-helper-v179`: pass
- Post-deploy selftest:
  - `selftest: pass=11 warn=1 fail=0`

## Tooling Note

The shared deploy wrapper now performs `hide` and retries a read-only capture
when the auto menu returns `busy`. This prevents a long `status` page from
activating the HUD and causing false deploy preflight failures.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_helper_v154_deploy_v930.py \
  scripts/revalidation/native_wifi_helper_v179_deploy_v1051.py
python3 scripts/revalidation/native_wifi_helper_v179_deploy_v1051.py preflight
python3 scripts/revalidation/native_wifi_helper_v179_deploy_v1051.py \
  --approval-phrase "approve v1051 deploy execns helper v179 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/a90ctl.py --hide-on-busy selftest
```

## Guardrails

No service-manager, CNSS daemon, Wi-Fi HAL, `wificond`, scan/connect,
credentials, DHCP/routes, external ping, eSoC ioctl, subsystem open, GPIO write,
sysfs write, debugfs write, boot image write, partition write, or firmware
mutation occurred. Only `/cache/bin/a90_android_execns_probe` was replaced.

## Next

V1052 should rerun the bounded live gate and require:

```text
modem_pre_holder_child_chroot=1
modem_pre_holder_open_reported=1
modem_pre_holder_confirmed=1
pm_full_contract_seen=1
```
