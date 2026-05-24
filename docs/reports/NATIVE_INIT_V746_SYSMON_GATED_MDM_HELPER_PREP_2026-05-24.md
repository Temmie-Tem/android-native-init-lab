# Native Init V746 Sysmon-gated MDM Helper Prep Report

- date: `2026-05-24 KST`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper version: `a90_android_execns_probe v124`
- helper sha256: `d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6`
- runner: `scripts/revalidation/native_wifi_mdm_helper_sysmon_live_v746.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v124_deploy_preflight.py`
- plan evidence: `tmp/wifi/v746-mdm-helper-sysmon-live-plan-final/`
- deploy preflight evidence: `tmp/wifi/v746-execns-helper-v124-deploy-preflight-final/`

## Summary

V746 adds helper v124 and a new sysmon-gated `mdm_helper` mode. It is the
minimal follow-up to V745: V745 proved the service `180` gate can stay closed
even when QRTR TX and `sysmon-qmi` are present, so V746 uses `sysmon-qmi` as the
gate and starts only `/vendor/bin/mdm_helper` after that marker.

The committed prep unit is static/read-only validated. Remote `/cache/bin` still
contains helper v123 until the v124 deploy run is executed.

## Key Results

| check | result |
| --- | --- |
| helper static build | pass |
| helper marker | `a90_android_execns_probe v124` |
| helper sha256 | `d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6` |
| new mode marker | `wifi-companion-sysmon-gated-mdm-helper-start-only` |
| new order marker | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,sysmon_gate,mdm_helper` |
| V746 runner plan | `v746-mdm-helper-gated-live-plan-ready` |
| v124 deploy preflight | `execns-helper-v124-deploy-preflight-ready` |
| remote helper | needs deploy |
| daemon / Wi-Fi bring-up | not executed by prep |

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v746-execns-helper-v124-build/a90_android_execns_probe

python3 -m py_compile \
  scripts/revalidation/native_wifi_mdm_helper_sysmon_live_v746.py \
  scripts/revalidation/wifi_execns_helper_v124_deploy_preflight.py

python3 scripts/revalidation/native_wifi_mdm_helper_sysmon_live_v746.py \
  --out-dir tmp/wifi/v746-mdm-helper-sysmon-live-plan-final \
  plan

python3 scripts/revalidation/wifi_execns_helper_v124_deploy_preflight.py \
  --out-dir tmp/wifi/v746-execns-helper-v124-deploy-preflight-final \
  --transfer-method serial \
  --serial-chunk-size 1850 \
  preflight
```

Observed:

```text
decision: v746-mdm-helper-gated-live-plan-ready
pass: True

decision: execns-helper-v124-deploy-preflight-ready
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next Gate

Deploy helper v124, refresh current-boot SELinuxfs/policy-load prep, then run
V746 live. The live proof may start `mdm_helper` only after `sysmon-qmi` appears
inside the bounded lower/CNSS-only window.
