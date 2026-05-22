# Native Init V653 Service74-Gated Service-Manager Prep Report

- date: `2026-05-23 KST`
- status: `prep-pass/deployed`; live proof not yet executed
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

Initial live deploy preflight was run without mutation and correctly stopped on
host NCM prerequisites:

```text
evidence: tmp/wifi/v653-helper-v105-deploy-preflight-current/
decision: execns-helper-v105-deploy-blocked
reason: blocked before deploy by host-ncm-address, ncm-host-reachable
device_mutations: False
wifi_bringup_executed: False
```

Because non-interactive sudo is unavailable on the host, V653 deployment used
the explicit serial transfer fallback. A `3000` byte chunk retry was rejected
before writes because it exceeded the native console line limit; the safe
`1850` byte default completed:

```text
evidence: tmp/wifi/v653-helper-v105-serial-deploy-run-1850/
method: serial appendfile + uudecode
chunk_size: 1850
chunks_written: 739
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Remote helper verification after deployment:

```text
remote: /cache/bin/a90_android_execns_probe
sha256: 8e712fab67de9e4e330e2c9ac2ab2f3328fe4b08fbad02b7279977ba6db76117
marker: a90_android_execns_probe v105
mode: wifi-companion-service74-gated-vnd-service-manager-start-only
```

Post-deploy V653 preflight now reaches the intended next blockers:

```text
evidence: tmp/wifi/v653-service74-gated-preflight-after-deploy/
decision: v653-service74-gated-service-manager-blocked
reason: blocked by v490-current-policy-load, v641-clean-dsp-state
device_mutations: False
wifi_bringup_executed: False
```

## Next Gate

This prep report is superseded by
`docs/reports/NATIVE_INIT_V653_SERVICE74_GATED_SERVICE_MANAGER_LIVE_2026-05-23.md`.
The live proof has been executed; follow the live report's V654 binder/runtime
mismatch classifier gate.
