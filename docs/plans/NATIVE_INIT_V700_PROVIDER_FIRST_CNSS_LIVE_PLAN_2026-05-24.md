# Native Init V700 Provider-first CNSS Live Plan

- date: `2026-05-24 KST`
- cycle: `v700`
- type: bounded live proof

## Goal

V699 built helper `a90_android_execns_probe v119` with a provider-first
initial-suppressed CNSS mode. V700 deploys that helper and answers the next
narrow live question:

- can native init suppress the initial pre-provider `cnss-daemon`;
- can it still reach service-notifier `180/74`;
- can it confirm `vendor.qcom.PeripheralManager` through `vndservicemanager`;
- can it then start one fresh post-provider `cnss-daemon` retry;
- and does WLFW/BDF/`wlan0` advance afterward.

## Scope

V700 is still below Wi-Fi bring-up. It may run only the current-boot prep and
the bounded companion/CNSS proof:

1. V641 clean-DSP reboot gate;
2. V401 SELinuxfs mount surface;
3. V490 native SELinux policy-load proof;
4. helper v119 provider-first companion mode;
5. read-only marker capture and reboot cleanup.

## Guardrails

V700 must not:

- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan, connect, link up, use credentials, run DHCP, change routes, or external
  ping;
- write sysfs/debugfs subsystem state;
- open or hold `esoc0`;
- write boot images or partitions.

## Expected Contract

Helper marker:

```text
a90_android_execns_probe v119
```

Mode:

```text
wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only
```

Expected order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,service74_gate,
servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,
per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry
```

Required runtime fields:

- `wifi_companion_start.initial_cnss_daemon.suppressed=1`
- exact `vendor.qcom.PeripheralManager` match in `/vendor/bin/vndservice list`
- exactly one post-provider `cnss-daemon` retry tail
- cleanup reboot returns to healthy native init

## Implementation

Add:

- `scripts/revalidation/native_wifi_provider_first_cnss_v700.py`
- `scripts/revalidation/wifi_execns_helper_v119_deploy_preflight.py`
- `scripts/revalidation/native_wifi_provider_first_cnss_orchestrator_v700.py`

The runner reuses the proven V695/V673 current-boot orchestration pattern, but
changes the live arm to helper v119 and the provider-first mode. The deploy
wrapper installs only `/cache/bin/a90_android_execns_probe` and does not start
daemons or Wi-Fi bring-up.

## Validation Plan

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_provider_first_cnss_v700.py \
  scripts/revalidation/wifi_execns_helper_v119_deploy_preflight.py \
  scripts/revalidation/native_wifi_provider_first_cnss_orchestrator_v700.py

python3 scripts/revalidation/native_wifi_provider_first_cnss_v700.py \
  --out-dir tmp/wifi/v700-provider-first-cnss-plan-check plan

python3 scripts/revalidation/wifi_execns_helper_v119_deploy_preflight.py \
  --out-dir tmp/wifi/v700-execns-helper-v119-deploy-preflight-check preflight

python3 scripts/revalidation/wifi_execns_helper_v119_deploy_preflight.py \
  --out-dir tmp/wifi/v700-execns-helper-v119-deploy-run-safe \
  --apply --assume-yes \
  --approval-phrase "approve v700 deploy execns helper v119 only; no daemon start and no Wi-Fi bring-up" \
  run

python3 scripts/revalidation/native_wifi_provider_first_cnss_orchestrator_v700.py \
  --out-dir tmp/wifi/v700-provider-first-cnss-orchestrated-run \
  --apply --assume-yes run
```

## Decision Labels

- `v700-provider-first-cnss-plan-ready`
- `execns-helper-v119-deploy-preflight-ready`
- `execns-helper-v119-deploy-pass`
- `v700-provider-first-cnss-preflight-ready`
- `v700-provider-first-cnss-gap-persists`
- `v700-provider-first-cnss-wifi-surface-advanced`
- `v700-cleanup-review`
