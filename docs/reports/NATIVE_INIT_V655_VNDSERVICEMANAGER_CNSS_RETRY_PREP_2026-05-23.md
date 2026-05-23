# Native Init V655 vndservicemanager CNSS Retry Prep Report

- date: `2026-05-23 KST`
- status: `prep/preflight-ready`; Wi-Fi external ping is **not** complete
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- runner:
  `scripts/revalidation/native_wifi_vndservicemanager_cnss_retry_v655.py`
- deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v106_deploy_preflight.py`
- build evidence: `tmp/wifi/v655-execns-helper-v106-build/`
- runner plan evidence:
  `tmp/wifi/v655-vndservicemanager-cnss-retry-plan-check/`
- deploy plan evidence:
  `tmp/wifi/v655-execns-helper-v106-deploy-plan-check/`
- deploy preflight evidence:
  `tmp/wifi/v655-execns-helper-v106-deploy-preflight-serial-check2/`

## Scope

V655 adds a bounded helper mode that preserves the V653 service `74` gate, then
proves `vndservicemanager` readiness before retrying `cnss-daemon`. Prep and
preflight did not deploy the helper, start daemons, start service-manager, start
Wi-Fi HAL, scan/connect/link-up, use credentials, run DHCP, change routes, or
ping externally.

## Result

```text
helper: a90_android_execns_probe v106
sha256: 5492f3cc32087e4f589b816c8b0757edb5caa2e9b87f8c0fa7f4486f05fb63cb
runner plan: v655-vndservicemanager-cnss-retry-plan-ready
deploy plan: execns-helper-v106-deploy-plan-ready
serial deploy preflight: execns-helper-v106-deploy-preflight-ready
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

The current live state still needs helper deployment:

| check | status | interpretation |
| --- | --- | --- |
| `remote-helper-v106` | `needs-deploy` | `/cache/bin` helper is not v106 yet |
| `approval-gate` | `needs-operator` | live `/cache/bin` write is intentionally gated |
| `host-ncm-address` | `warn` | NCM is not currently configured for fast deploy |
| `ncm-host-reachable` | `warn` | serial transfer is the current ready fallback |

## Implementation Notes

- Helper v106 adds:
  `wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only`.
- The mode records:
  `wifi_companion_start.vndservicemanager_readiness.*` and
  `wifi_companion_start.cnss_retry.*`.
- The runner requires V641 clean-DSP current boot state, V490 policy-load
  freshness, real linkerconfig/APEX config files, and helper v106.
- The deploy wrapper defaults to the v641 native version and keeps NCM as the
  default fast path; current preflight passes with explicit serial transfer.

## Next Gate

Deploy helper v106, refresh V641/V401/V490 prerequisites if needed, then run the
V655 bounded live proof. The live proof should stop at one of these labels:

- `v655-service74-gate-timeout`
- `v655-vndservicemanager-readiness-blocked`
- `v655-cnss-retry-not-executed`
- `v655-cnss-retry-wlfw-advanced`
- `v655-cnss-retry-binder-loop-persists`

Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP, routes, or
external ping until V655 proves native CNSS advances beyond the binder blocker.
