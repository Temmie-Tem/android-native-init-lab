# Native Init V856 pm-service Node Parity Start-Only Plan

## Goal

Run the smallest native equivalent of Android PeripheralManager startup after
V855 node parity: service managers plus `pm-service`/`pm-proxy`, with
Android-equivalent eSoC/subsys nodes present.

## Inputs

- V855 node parity evidence:
  `tmp/wifi/v855-esoc-node-parity-preflight/manifest.json`
- Android actor contract from V853:
  - `pm-service` holds `/dev/subsys_esoc0`
  - `pm-service` holds `/dev/subsys_modem`
  - `/dev/subsys_*` nodes are `0640 system:system`
- Current helper build:
  `tmp/wifi/v856-execns-helper-v131-build/a90_android_execns_probe`

## Method

1. Verify native health with `bootstatus` and `selftest`.
2. Prepare current-boot Android prerequisites:
   - `mountsystem ro`
   - V401 toybox-backed `selinuxfs` mount surface
3. Deploy helper v131 if `/cache/bin/a90_android_execns_probe` is stale.
4. Materialize V855-equivalent global nodes:
   - `/dev/esoc-0`
   - `/dev/subsys_esoc0`
   - `/dev/subsys_modem`
5. In the private exec namespace, materialize the same node parity and start
   only:
   - `/system/bin/servicemanager`
   - `/system/bin/hwservicemanager`
   - `/vendor/bin/vndservicemanager`
   - `/vendor/bin/pm-service`
   - `/vendor/bin/pm-proxy`
6. Capture child observability, fd summaries, property shim requests, result
   labels, cleanup status, and native postflight health.

## Guardrails

- No `mdm_helper` or `ks` start.
- No CNSS retry, Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect,
  credential use, DHCP/routes, or external ping.
- No raw eSoC ioctl, direct eSoC/subsys node open outside the actor process,
  GPIO/sysfs/debugfs write, subsystem state write, module load/unload, boot
  image write, or Android partition write.
- Node mutation is limited to V855-equivalent materialization and cleanup.
- SELinuxfs mutation is limited to the existing V401 toybox mount executor.

## Success Criteria

- Helper v131 is deployed or already current.
- `mountsystem ro` and V401 `selinuxfs` prerequisite pass.
- V855-equivalent nodes are created and then cleaned up.
- Helper reports mode
  `wifi-companion-peripheral-manager-node-parity-start-only`, allowed `1`, and
  order `servicemanager,hwservicemanager,vndservicemanager,per_mgr,per_proxy`.
- Private node parity exists inside the helper namespace.
- `pm-service` is observable and fd summary is captured.
- Postflight remains `BOOT OK` with selftest `fail=0`.

## Commands

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py \
  scripts/revalidation/wifi_execns_helper_v131_deploy_preflight.py

python3 scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py \
  --out-dir tmp/wifi/v856-pm-service-node-parity-plan-r4 \
  plan

python3 scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py \
  --out-dir tmp/wifi/v856-pm-service-node-parity-start-only-r5 \
  --allow-helper-deploy \
  --allow-netservice-start \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-node-materialization \
  --allow-node-cleanup \
  --allow-pm-service-start-only \
  --assume-yes \
  run
```
