# Native Init V694 PeripheralManager vndservice Query Plan

- date: `2026-05-24 KST`
- cycle: `v694`
- target helper: `a90_android_execns_probe v117`
- target mode: `wifi-companion-service74-gated-peripheral-manager-vndservice-query-start-only`

## Goal

V692/V693 showed that `pm-service` and `pm-proxy` can be started in the
service `74` positive private namespace, but registry snapshots alone did not
prove whether `vendor.qcom.PeripheralManager` was registered through
`vndservicemanager`.

V694 adds one bounded proof: after `pm-service` and `pm-proxy` start below the
Wi-Fi bring-up line, run `/vendor/bin/vndservice list` from the same private
Android namespace and classify whether `vendor.qcom.PeripheralManager` appears.

## Gate

Expected order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,
service74_gate,servicemanager,hwservicemanager,vndservicemanager,
vndservicemanager_ready,cnss_daemon_initial_cleanup,
per_mgr,vndservice_query,per_proxy,vndservice_query
```

Success labels:

- `v694-peripheral-vndservice-registration-confirmed`: query exits zero and sees `vendor.qcom.PeripheralManager`.
- `v694-peripheral-vndservice-registration-absent`: query exits zero but does not show the provider.
- `v694-vndservice-query-runtime-gap`: query runs but does not exit zero.

## Guardrails

V694 must not:

- start Wi-Fi HAL, `wificond`, supplicant, or hostapd;
- scan, connect, link up, use credentials, run DHCP, change routes, or external ping;
- write subsystem sysfs nodes or open/hold `esoc0`;
- write boot images or partitions.

## Implementation

- Add helper v117 mode with `wifi_vndservice_query.<phase>.*` key output.
- Query phases: `after_per_mgr_probe` and `after_per_proxy_probe`.
- Keep query timeout bounded to 3000 ms per phase.
- Keep provider processes in the existing start-only cleanup contract.
- Add deploy wrapper, direct proof runner, and current-boot orchestrator.

## Validation Plan

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v694-execns-helper-v117-build/a90_android_execns_probe
python3 -m py_compile \
  scripts/revalidation/native_wifi_peripheral_vndservice_query_v694.py \
  scripts/revalidation/native_wifi_peripheral_vndservice_query_orchestrator_v694.py \
  scripts/revalidation/wifi_execns_helper_v117_deploy_preflight.py
python3 scripts/revalidation/wifi_execns_helper_v117_deploy_preflight.py --out-dir tmp/wifi/v694-execns-helper-v117-deploy-preflight-current preflight
python3 scripts/revalidation/wifi_execns_helper_v117_deploy_preflight.py --out-dir tmp/wifi/v694-execns-helper-v117-deploy-live-serial1850 --transfer-method serial --serial-chunk-size 1850 --approval-phrase "approve v694 deploy execns helper v117 only; no daemon start and no Wi-Fi bring-up" --apply --assume-yes run
python3 scripts/revalidation/native_wifi_peripheral_vndservice_query_orchestrator_v694.py --out-dir tmp/wifi/v694-peripheral-vndservice-query-orchestrated-live-rerun --apply --assume-yes run
```
