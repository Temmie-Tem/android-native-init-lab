# Native Init V745 Service180-gated MDM Helper Prep Report

- date: `2026-05-24 KST`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper version: `a90_android_execns_probe v123`
- helper sha256: `1456974a114240380dce30a855d3571985ae4587ab61366fb3426862ccd59240`
- runner: `scripts/revalidation/native_wifi_mdm_helper_service180_live_v745.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v123_deploy_preflight.py`
- plan evidence: `tmp/wifi/v745-mdm-helper-service180-live-plan2/`
- deploy preflight evidence: `tmp/wifi/v745-execns-helper-v123-deploy-preflight-after-hide/`

## Summary

V745 adds helper v123 and a new service `180` gated `mdm_helper` mode. This is
the direct repair for V743: V743 waited on service `74`, but V744 proved the
reproducible current native marker is service-notifier `180`.

The prep unit was followed by live execution. Helper v123 was deployed in
`tmp/wifi/v745-execns-helper-v123-deploy-run-serial1850/`, and the live result
is recorded in
`docs/reports/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_LIVE_2026-05-24.md`.

## Key Results

| check | result |
| --- | --- |
| helper static build | pass |
| helper marker | `a90_android_execns_probe v123` |
| helper sha256 | `1456974a114240380dce30a855d3571985ae4587ab61366fb3426862ccd59240` |
| new mode marker | `wifi-companion-service180-gated-mdm-helper-start-only` |
| new order marker | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service180_gate,mdm_helper` |
| V745 runner plan | `v745-mdm-helper-gated-live-plan-ready` |
| v123 deploy preflight | `execns-helper-v123-deploy-preflight-ready` |
| remote helper | needs deploy |
| daemon / Wi-Fi bring-up | not executed |

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v745-execns-helper-v123-build/a90_android_execns_probe

python3 -m py_compile \
  scripts/revalidation/native_wifi_mdm_helper_service180_live_v745.py \
  scripts/revalidation/wifi_execns_helper_v123_deploy_preflight.py

python3 scripts/revalidation/native_wifi_mdm_helper_service180_live_v745.py \
  --out-dir tmp/wifi/v745-mdm-helper-service180-live-plan2 plan

python3 scripts/revalidation/wifi_execns_helper_v123_deploy_preflight.py \
  --out-dir tmp/wifi/v745-execns-helper-v123-deploy-preflight-after-hide \
  preflight
```

Plan/preflight output:

```text
decision: v745-mdm-helper-gated-live-plan-ready
pass: True
next: deploy helper v123, then run V745 bounded live proof

decision: execns-helper-v123-deploy-preflight-ready
pass: True
next: deploy helper v123, then run V745 service180-gated mdm_helper proof
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Next Gate

V745 live showed service-notifier `180` is not stable enough as the gate.
Continue with V746 sysmon-gated `mdm_helper` proof.
