# Native Init V653 Service74-Gated Service-Manager Prep Report

- date: `2026-05-23 KST`
- status: `prep-pass`; live proof not yet executed
- helper: `a90_android_execns_probe v105`
- helper artifact:
  `tmp/wifi/v653-execns-helper-v105-build/a90_android_execns_probe`
- helper sha256:
  `8e712fab67de9e4e330e2c9ac2ab2f3328fe4b08fbad02b7279977ba6db76117`
- runner:
  `scripts/revalidation/native_wifi_service74_gated_service_manager_v653.py`
- deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v105_deploy_preflight.py`

## Result

V653 adds a new helper mode that starts lower companion/CNSS children first and
gates the service-manager trio on a fresh kernel-log service-notifier `74`
publication:

```text
wifi-companion-service74-gated-vnd-service-manager-start-only
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,
service74_gate,servicemanager,hwservicemanager,vndservicemanager
```

The gate records baseline/final service `74` counts, wait attempts, elapsed
time, and whether the service-manager trio actually started. If no fresh service
`74` publication appears, service-manager is withheld and the live proof should
classify `v653-service74-gate-timeout`.

## Validation

```text
scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v653-execns-helper-v105-build/a90_android_execns_probe
sha256: 8e712fab67de9e4e330e2c9ac2ab2f3328fe4b08fbad02b7279977ba6db76117
static: no dynamic section
```

```text
python3 -m py_compile \
  scripts/revalidation/native_wifi_service74_gated_service_manager_v653.py \
  scripts/revalidation/wifi_execns_helper_v105_deploy_preflight.py
```

```text
python3 scripts/revalidation/native_wifi_service74_gated_service_manager_v653.py \
  --out-dir tmp/wifi/v653-plan-smoke plan
decision: v653-service74-gated-service-manager-plan-ready
pass: True
```

```text
python3 scripts/revalidation/wifi_execns_helper_v105_deploy_preflight.py \
  --out-dir tmp/wifi/v653-helper-v105-deploy-plan-smoke plan
decision: execns-helper-v105-deploy-plan-ready
pass: True
```

Current live deploy preflight was run without mutation and correctly stopped on
host NCM prerequisites:

```text
evidence: tmp/wifi/v653-helper-v105-deploy-preflight-current/
decision: execns-helper-v105-deploy-blocked
reason: blocked before deploy by host-ncm-address, ncm-host-reachable
device_mutations: False
wifi_bringup_executed: False
```

## Next Gate

1. Re-enable host NCM or use the approved serial deploy fallback.
2. Deploy helper v105 only.
3. Re-arm V641 clean-DSP one-shot and refresh V401/V490 current-boot
   prerequisites.
4. Run V653 live proof with Wi-Fi HAL, scan/connect, credentials, DHCP, route
   changes, and external ping still blocked.
