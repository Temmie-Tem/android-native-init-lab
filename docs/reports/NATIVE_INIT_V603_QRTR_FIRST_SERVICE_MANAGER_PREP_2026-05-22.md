# Native Init V603 QRTR-First Service-Manager Prep Report

- date: `2026-05-22 KST`
- status: `prepared`; live proof not yet executed
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v101_deploy_preflight.py`
- live runner: `scripts/revalidation/native_wifi_modem_holder_qrtr_first_service_manager_v603.py`
- local artifact: `tmp/wifi/v603-execns-helper-v101-build/a90_android_execns_probe`

## Scope

V603 preparation adds a helper mode for the ordering gap classified by V602.
It does not contact the device, deploy the helper, start service-manager, start
CNSS, start Wi-Fi HAL, write `qcwlanstate`, scan, connect, use credentials, run
DHCP, change routes, ping externally, or write a boot image.

## Result

```text
helper_version: a90_android_execns_probe v101
local_helper_sha256: a2a089110106a9c2eb6b33eb2c5f0c382fb4fda0e0c7f32e80dbabb9dd281372
new_mode: wifi-companion-qrtr-first-vnd-service-manager-start-only
order: qrtr_ns,rmt_storage,tftp_server,pd_mapper,servicemanager,hwservicemanager,vndservicemanager,cnss_diag,cnss_daemon
device_commands_executed: false
wifi_bringup_executed: false
```

Read-only deploy preflight:

```text
default_transfer_method: ncm
default_preflight_decision: execns-helper-v101-deploy-blocked
default_preflight_reason: blocked before deploy by host-ncm-address, ncm-host-reachable
auto_transfer_preflight_decision: execns-helper-v101-deploy-preflight-ready
auto_transfer_preflight_pass: true
auto_transfer_preflight_next: deploy helper v101, then run qrtr-first service-manager proof
auto_transfer_device_mutations: false
auto_transfer_daemon_start_executed: false
auto_transfer_wifi_bringup_executed: false
live_runner_plan_decision: v603-qrtr-first-service-manager-plan-ready
live_runner_preflight_decision: v603-qrtr-first-service-manager-blocked
live_runner_preflight_blockers: v490-current-policy-load, helper-v101-base-ready, helper-v101-qrtr-first-ready
```

The default `ncm` block is intentional. It prevents an accidental slow serial
deploy when the NCM host path is not configured. `--transfer-method auto`
confirms that the device and local helper are otherwise ready for an explicitly
accepted serial fallback or an NCM setup retry.

The live runner was added and plan-only validation passed. Read-only preflight
correctly blocks because the current boot still needs a fresh V490 policy-load
manifest and the device still has the previous helper instead of helper v101.

Serial deploy note: a first `--serial-chunk-size 3000` attempt was rejected
before writing chunks because cmdv1x line expansion exceeded the native console
safe line limit. The V603 wrapper default is therefore kept at `1850`, matching
the prior safe helper deploy path.

## Interpretation

The V602 comparison means the next live proof must preserve two independent
conditions at the same time:

- V598 lower-modem readiness: QRTR TX, `sysmon-qmi`, service-notifier `180`;
- V601 binder/runtime readiness: no `cnss-daemon` binder transaction failures.

V603 is built to test that exact intersection. It starts QRTR and modem
firmware companion services first, gives the lower path a short publication
window, then starts service-manager/hwservicemanager/vndservicemanager before
CNSS enters the window.

This is still an analysis gate, not Wi-Fi bring-up.

## Safety State

- `esoc0` remains out of scope for live proof.
- `subsys_modem` is the only subsystem holder candidate.
- Service-manager start is bounded to the helper-owned private namespace.
- Expected cleanup path after live modem-holder proof remains reboot cleanup.
- SSID/PSK material is not used by this stage.

## Next Gate

Recommended live sequence:

1. Deploy helper v101 only after exact approval or bypass-mode live permission.
2. Refresh current boot runtime prerequisites: Android mounts, SELinuxfs, V490
   SELinux policy-load, firmware mounts.
3. Run a bounded V603 modem-holder companion proof with the QRTR-first mode.
4. Advance only if service-notifier `180` remains present and binder transaction
   failures remain cleared.

If V603 reaches WLFW service `69`, BDF, FW-ready, or `wlan0`, prepare the next
bounded HAL/driver-state gate. Otherwise keep scan/connect/external ping
blocked.
