# Native Init V742 Execns Helper v122 Deploy Prep Report

- date: `2026-05-24 KST`
- wrapper: `scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py`
- helper artifact: `tmp/wifi/v741-execns-helper-v122-build/a90_android_execns_probe`
- helper sha256: `032fe43041b908577bb1a2e4b3ff7a7dfea24958169723907df5d403f811e989`
- preflight evidence: `tmp/wifi/v742-execns-helper-v122-deploy-preflight-after-hide/`
- decision: `execns-helper-v122-deploy-preflight-ready`
- pass: `true`

## Summary

V742 adds the deployment wrapper for helper v122 and validates that the device
is ready for a helper-only deploy. No helper install was executed in this prep
commit.

The first preflight attempt exposed a safety gap: after `version/status/selftest`
passed, the later read-only commands returned native `busy` because the auto
menu was active. V742 now blocks deploy when any read-only preflight step is
busy or when required status/process/network-surface checks fail.

After `hide`, preflight passed.

## Key Results

| check | result |
| --- | --- |
| wrapper compile | pass |
| local helper v122 | pass; marker, hash, and gated `mdm_helper` mode present |
| registration/token guard | pass; v122 token set present |
| native version | pass; `A90 Linux init 0.9.68 (v724)` |
| native clean | pass; status/selftest `fail=0` |
| read-only preflight completeness | pass after `hide` |
| remote helper v122 | needs deploy |
| host NCM | warning; NCM address/reachability absent |
| device mutations | false |
| daemon / Wi-Fi bring-up | false |

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py

python3 scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py \
  --out-dir tmp/wifi/v742-execns-helper-v122-deploy-plan plan

python3 scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py \
  --out-dir tmp/wifi/v742-execns-helper-v122-deploy-preflight preflight

python3 scripts/revalidation/a90ctl.py --timeout 10 hide

python3 scripts/revalidation/wifi_execns_helper_v122_deploy_preflight.py \
  --out-dir tmp/wifi/v742-execns-helper-v122-deploy-preflight-after-hide preflight
```

Final preflight output:

```text
decision: execns-helper-v122-deploy-preflight-ready
pass: True
reason: preflight complete; helper v122 deploy still requires exact approval
next: deploy helper v122, then run V741 gated mdm_helper proof
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next Gate

Deploy helper v122 using the V742 wrapper. Because host NCM is not currently
configured, the immediate no-sudo path is serial transfer with safe chunk size
`1850`. After deploy, run the V741 gated `mdm_helper` live proof.
