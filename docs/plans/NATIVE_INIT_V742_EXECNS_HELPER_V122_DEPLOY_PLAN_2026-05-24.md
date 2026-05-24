# Native Init V742 Execns Helper v122 Deploy Plan

- date: `2026-05-24 KST`
- wrapper: `scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py`
- helper artifact: `tmp/wifi/v741-execns-helper-v122-build/a90_android_execns_probe`
- helper sha256: `032fe43041b908577bb1a2e4b3ff7a7dfea24958169723907df5d403f811e989`
- evidence target: `tmp/wifi/v742-execns-helper-v122-deploy-preflight-after-hide/`

## Goal

Deploy `/cache/bin/a90_android_execns_probe` v122 so the V741
service74-gated `mdm_helper` live proof can run on the device.

## Scope

Allowed:

- verify local helper v122 marker, hash, and gated `mdm_helper` mode;
- verify native status/selftest and clean process/link surface;
- deploy only `/cache/bin/a90_android_execns_probe` if the remote helper is
  missing or older;
- use NCM auto transfer when available, otherwise serial append/uudecode;
- rerun V741 plan after deployment.

Forbidden:

- daemon start, service-manager start, Wi-Fi HAL start, scan/connect, credential
  use, DHCP/routes, external ping, boot-image writes, or partition writes.

## Safety Fix

V742 adds a wrapper-local blocker for incomplete read-only preflight. Any
`busy` read-only step, or failure of `version`, `status`, `selftest`, `ps`, or
`proc-net-dev`, blocks deploy. This prevents a false deploy-ready result when
the native auto menu is still active.

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py

python3 scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py \
  --out-dir tmp/wifi/v742-execns-helper-v122-deploy-plan plan

python3 scripts/revalidation/a90ctl.py --timeout 10 hide

python3 scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py \
  --out-dir tmp/wifi/v742-execns-helper-v122-deploy-preflight-after-hide preflight
```

## Deploy Command

After committing this prep unit:

```bash
python3 scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py \
  --out-dir tmp/wifi/v742-execns-helper-v122-deploy-run \
  --transfer-method serial \
  --serial-chunk-size 1850 \
  --apply \
  --assume-yes \
  --approval-phrase 'approve v742 deploy execns helper v122 only; no daemon start and no Wi-Fi bring-up' \
  run
```
