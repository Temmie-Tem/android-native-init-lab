# Native Init V907 Helper v148 Deploy Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| helper `v148` deploy-only wrapper | `tmp/wifi/v907-execns-helper-v148-deploy-preflight/manifest.json` | `execns-helper-v148-deploy-pass` |

V907 deployed the V906-built `a90_android_execns_probe v148` helper to
`/cache/bin/a90_android_execns_probe` and verified remote checksum/mode parity.
No runtime-contract actor was started in this unit.

## Deploy

| Field | Value |
| --- | --- |
| transfer | `serial` |
| chunks_written | `837` |
| encoded_bytes | `1546991` |
| line_check_ok | `True` |
| remote_sha256 | `12633b3c21292cf547393abce972bc7b1e855144dcdaea3975a45e943228cae6` |

The wrapper manifest keeps the `remote-helper-v148` check from the pre-deploy
snapshot, where the old helper was still installed. The post-deploy evidence
and direct readback prove that the target helper is now `v148`.

## Post-Deploy Evidence

- `tmp/wifi/v907-execns-helper-v148-deploy-preflight/post-deploy-steps.json`
- `tmp/wifi/v907-execns-helper-v148-deploy-preflight/native/sha-helper.txt`
- `tmp/wifi/v907-execns-helper-v148-deploy-preflight/native/helper-usage.txt`
- `tmp/wifi/v907-execns-helper-v148-deploy-preflight/host/serial-install-helper.txt`

Readback confirmed:

```text
12633b3c21292cf547393abce972bc7b1e855144dcdaea3975a45e943228cae6  /cache/bin/a90_android_execns_probe
a90_android_execns_probe v148
wifi-companion-mdm-helper-runtime-contract-capture
```

## Guardrails

- `daemon_start_executed=False`
- `wifi_bringup_executed=False`
- service-manager process surface clean
- Wi-Fi link surface clean
- no `mdm_helper`, `ks`, `pm-service`, or `pm_proxy_helper` actor start
- no live eSoC ioctl or controller `/dev/subsys_esoc0` open
- no Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, reboot,
  boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write,
  module load/unload, or Wi-Fi bring-up

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v148_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_v148_deploy_preflight.py plan
python3 scripts/revalidation/wifi_execns_helper_v148_deploy_preflight.py preflight
python3 scripts/revalidation/wifi_execns_helper_v148_deploy_preflight.py \
  --apply \
  --assume-yes \
  --approval-phrase "approve v907 deploy execns helper v148 only; no actor start, no daemon start and no Wi-Fi bring-up" \
  run
```

## Next

V908 should run the bounded `wifi-companion-mdm-helper-runtime-contract-capture`
mode. That next unit should remain diagnostic-only: property shim plus
`per_mgr_light`/`mdm_helper` runtime-contract capture, no service-manager, no
CNSS daemon, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and
no external ping.
