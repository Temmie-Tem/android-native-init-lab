# Native Init V604 CNSS-First Service-Manager Prep Report

- date: `2026-05-22 KST`
- status: `prepared`; live proof not yet executed
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v102_deploy_preflight.py`
- live runner: `scripts/revalidation/native_wifi_modem_holder_cnss_first_service_manager_v604.py`
- local artifact: `tmp/wifi/v604-execns-helper-v102-build/a90_android_execns_probe`

## Result

```text
helper_version: a90_android_execns_probe v102
local_helper_sha256: 8214098f750c77f982975f46a8b6af2a8461b6e4520962488b7daf9e013251d3
new_mode: wifi-companion-cnss-first-delayed-vnd-service-manager-start-only
order: qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,servicemanager,hwservicemanager,vndservicemanager
deploy_plan_decision: execns-helper-v102-deploy-plan-ready
deploy_auto_preflight_decision: execns-helper-v102-deploy-preflight-ready
live_runner_plan_decision: v604-cnss-first-service-manager-plan-ready
live_runner_readonly_preflight_decision: v604-cnss-first-service-manager-blocked
live_runner_readonly_preflight_blockers: v490-current-policy-load, helper-v102-base-ready, helper-v102-qrtr-first-ready, helper-v102-cnss-first-ready
device_commands_executed: false
wifi_bringup_executed: false
```

## Interpretation

V604 directly tests the V603 result:

- service-manager before CNSS keeps binder clean but suppresses
  service-notifier `180`;
- CNSS before service-manager should reproduce V598's lower service-notifier
  path, then test whether later service-manager availability is enough for
  binder recovery.

This remains an analysis gate. It is not a Wi-Fi connect attempt.

## Next Gate

1. Deploy helper v102.
2. Refresh current boot V401/V490 prerequisites after the V603 reboot cleanup.
3. Run V604 preflight.
4. Run V604 live proof only if preflight is clean.
5. Continue blocking Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials, DHCP,
   routing, and external ping until service-notifier `180` and binder-clean are
   observed together, or WLFW/BDF/FW-ready/`wlan0` appears.
