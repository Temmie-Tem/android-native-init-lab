# Native Init v402 Private SELinux Surface Proof Plan

## Goal

Prove the Android service-manager private execution namespace can see the SELinux runtime surface that V401 mounted.

V401 proved the native host namespace now has `selinuxfs` mounted at `/sys/fs/selinux`, with `/sys/fs/selinux/status` and `/sys/fs/selinux/enforce` visible. V402 does not start `servicemanager`. It only updates the static execution-namespace probe helper so a private namespace can bind the existing SELinuxfs surface and emit pre-exec visibility evidence.

V402 must not start `servicemanager`, `hwservicemanager`, Wi-Fi HAL, `wificond`, supplicant, hostapd, CNSS, or any Wi-Fi bring-up path.

## Starting Evidence

- V401 report: `docs/reports/NATIVE_INIT_V401_TOYBOX_SELINUXFS_MOUNT_SMOKE_2026-05-20.md`
- V401 approved live evidence: `tmp/wifi/v401-toybox-selinuxfs-mount-live-20260520-082325/`
- V401 post-mount proof: `tmp/wifi/v401-post-mount-selinux-proof-20260520-082352/`

Current blocker after V401:

```text
decision: service-manager-selinux-surface-native-ready-private-proof-needed
reason: native SELinux/status/context inputs are visible, but private namespace status visibility is unproven
```

## Implementation

Update `stage3/linux_init/helpers/a90_android_execns_probe.c` from v21 to v22:

- add `private-selinux-proof` mode.
- bind the already-mounted host `/sys/fs/selinux` into the private execution root.
- materialize binder devnodes and the V317 private property runtime tree without executing a daemon.
- print private namespace pre-exec context for:
  - `/sys/fs/selinux/status`
  - `/sys/fs/selinux/enforce`
  - `/sys/fs/selinux/policy`
  - service-manager SELinux class/perms paths
  - binder, hwbinder, vndbinder
  - `/dev/__properties__`
  - Android service and hwservice context files under system/system_ext/vendor
- emit `private_selinux_proof.result=pass` without calling `execve`.

Add two host tools:

- `scripts/revalidation/wifi_execns_helper_v22_deploy_preflight.py`
  - prepares deploy of helper v22 to `/cache/bin/a90_android_execns_probe`.
  - refuses mutation unless the exact V402 deploy approval phrase and `--apply --assume-yes` are supplied.
  - does not start daemons or Wi-Fi.

- `scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py`
  - runs read-only preflight checks.
  - refuses live proof unless the exact V402 private-proof approval phrase and `--apply --assume-yes` are supplied.
  - approved live proof runs only helper `private-selinux-proof`, with no daemon execution.

## Approval Boundaries

Helper deploy approval:

```text
approve v402 deploy execns helper v22 only; no daemon start and no Wi-Fi bring-up
```

Private SELinux namespace proof approval:

```text
approve v402 private selinux namespace proof only; no daemon start and no Wi-Fi bring-up
```

These approvals are intentionally separate. Deploying helper v22 does not approve the private proof. Passing the private proof does not approve service-manager start-only.

## Validation Plan

Static validation:

```text
python3 -m py_compile \
  scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py \
  scripts/revalidation/wifi_execns_helper_v22_deploy_preflight.py

bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v402-a90_android_execns_probe-v22/a90_android_execns_probe
```

Expected helper artifact:

```text
sha256: 55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6
marker: a90_android_execns_probe v22
mode: private-selinux-proof
```

Fail-closed validation:

```text
python3 scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py \
  --out-dir tmp/wifi/v402-private-proof-noapproval-run-fixed \
  run

python3 scripts/revalidation/wifi_execns_helper_v22_deploy_preflight.py \
  --out-dir tmp/wifi/v402-deploy-noapproval-run-fixed \
  run
```

Expected:

```text
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Read-only preflight:

```text
python3 scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py \
  --out-dir tmp/wifi/v402-private-proof-preflight-current \
  preflight

python3 scripts/revalidation/wifi_execns_helper_v22_deploy_preflight.py \
  --out-dir tmp/wifi/v402-deploy-preflight-current-fixed \
  preflight
```

Expected before deploy:

```text
private proof: blocked only by helper-v22
deploy: preflight-ready-needs-deploy
```

## Future Live Commands

Deploy helper v22 only after exact deploy approval:

```text
python3 scripts/revalidation/wifi_execns_helper_v22_deploy_preflight.py \
  --out-dir tmp/wifi/v402-execns-helper-v22-deploy-live-$(date +%Y%m%d-%H%M%S) \
  --approval-phrase "approve v402 deploy execns helper v22 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Run private SELinux namespace proof only after exact private-proof approval:

```text
python3 scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py \
  --out-dir tmp/wifi/v402-private-selinux-surface-live-$(date +%Y%m%d-%H%M%S) \
  --approval-phrase "approve v402 private selinux namespace proof only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

## Next Step

If V402 private proof passes, the next separate cycle is a bounded service-manager start-only retry using the same private runtime surface. Wi-Fi HAL/start/scan/connect remains blocked until service-manager is clean or explicitly classified as non-blocking.
