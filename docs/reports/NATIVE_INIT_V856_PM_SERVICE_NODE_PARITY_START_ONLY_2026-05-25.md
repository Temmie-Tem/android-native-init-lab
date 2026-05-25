# Native Init V856 pm-service Node Parity Start-Only Report

## Result

- decision: `v856-pm-service-observable-without-subsys-hold`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py`
- helper wrapper: `scripts/revalidation/wifi_execns_helper_v131_deploy_preflight.py`
- helper version: `a90_android_execns_probe v131`
- evidence: `tmp/wifi/v856-pm-service-node-parity-start-only-r5/`
- next: V857 should classify the `pm-service` property-service contract before
  any `mdm_helper`/`ks` replay.

## Scope

V856 performed a bounded native live mutation. It prepared `mountsystem ro`,
mounted the V401 SELinuxfs runtime surface, deployed helper v131, materialized
V855-equivalent eSoC/subsys nodes, started only service-manager processes plus
`pm-service` and `pm-proxy`, captured fd/runtime evidence, cleaned up created
nodes, and verified native health.

V856 did not start `mdm_helper`, `ks`, CNSS retry, Wi-Fi HAL, wificond,
supplicant, or hostapd. It did not scan/connect, use credentials, run DHCP,
change routes, ping externally, write GPIO/sysfs/debugfs, write subsystem state,
load/unload modules, write boot images, write Android partitions, or use raw
eSoC ioctl.

## Prerequisites

| Prerequisite | Result |
| --- | --- |
| V855 manifest | `v855-esoc-node-parity-clean` |
| `mountsystem ro` | pass |
| V401 SELinuxfs mount | `toybox-selinuxfs-mount-live-executor-run-pass` |
| helper deploy | `execns-helper-v131-deploy-pass` |
| helper sha256 | `3ff904b3b0e662b4f3a155d0ef84db7587a4fd0b69986d71015640c8f293f766` |

The helper was already current during the final run. NCM was unavailable because
native `netservice start` still lacks `a90_tcpctl`, so deploy verification used
serial/cmdv1 paths. This is a tooling speed issue, not a V856 Wi-Fi result.

## Live Result

The helper reached the intended mode and order:

```text
mode=wifi-companion-peripheral-manager-node-parity-start-only
wifi_companion_start.allowed=1
wifi_companion_start.order=servicemanager,hwservicemanager,vndservicemanager,per_mgr,per_proxy
wifi_companion_start.peripheral_manager.enabled=1
wifi_companion_start.service_manager_started=1
wifi_companion_start.child_started=5
```

Private node parity was present inside the execution namespace:

```text
wifi_companion_start.private_node.subsys_modem.exists=1
wifi_companion_start.private_node.subsys_esoc0.exists=1
wifi_companion_start.private_node.esoc_0.exists=1
```

`pm-service` and `pm-proxy` were observable:

```text
wifi_companion_start.peripheral_manager.per_mgr.observable=1
wifi_companion_start.peripheral_manager.per_mgr.fd_summary_captured=1
wifi_companion_start.peripheral_manager.per_mgr.ready=1
wifi_companion_start.peripheral_manager.per_proxy.observable=1
wifi_companion_start.peripheral_manager.per_proxy.fd_summary_captured=1
wifi_companion_start.peripheral_manager.per_proxy.ready=1
```

The observed runtime result was:

```text
wifi_companion_start.result=start-only-runtime-gap
wifi_companion_start.reason=child-exited-before-observe-window
wifi_companion_start.all_postflight_safe=1
```

## Subsystem FD Finding

V856 did not prove that native `pm-service` holds the target subsystem nodes:

| Actor | fd evidence |
| --- | --- |
| `pm-service` | fd summary captured, but no fd targets remained by capture time |
| `pm-proxy` | `/dev/ttyGS0`, pipes, socket, and private `/dev/vndbinder`; no `subsys_*` fd |

This differs from Android V853, where `pm-service` holds both
`/dev/subsys_esoc0` and `/dev/subsys_modem`.

## Property-Service Gap

The strongest newly observed gap is the property-service contract. The shim
allowed the known offline-state properties, but rejected
`vendor.peripheral.shutdown_critical_list` updates:

```text
wifi_hal_composite_start.property_service_shim.request.2.name=vendor.peripheral.SDX50M.state
wifi_hal_composite_start.property_service_shim.request.2.value=OFFLINE
wifi_hal_composite_start.property_service_shim.request.2.allowed=1
wifi_hal_composite_start.property_service_shim.request.3.name=vendor.peripheral.shutdown_critical_list
wifi_hal_composite_start.property_service_shim.request.3.value=SDX50M 
wifi_hal_composite_start.property_service_shim.request.3.allowed=0
wifi_hal_composite_start.property_service_shim.request.6.name=vendor.peripheral.modem.state
wifi_hal_composite_start.property_service_shim.request.6.value=OFFLINE
wifi_hal_composite_start.property_service_shim.request.6.allowed=1
wifi_hal_composite_start.property_service_shim.request.7.name=vendor.peripheral.shutdown_critical_list
wifi_hal_composite_start.property_service_shim.request.7.value=SDX50M modem 
wifi_hal_composite_start.property_service_shim.request.7.allowed=0
```

Interpretation: V856 shows that service managers, SELinuxfs, linker namespace,
private properties, and node parity are enough to start and observe
PeripheralManager. The missing Android-equivalent behavior is not yet
`mdm_helper`; it is the lower `pm-service` property contract and resulting
subsystem-node hold behavior.

## Cleanup and Health

V856 removed every node it created:

```text
REMOVE /dev/esoc-0
REMOVE /dev/subsys_esoc0
REMOVE /dev/subsys_modem
```

Postflight stayed healthy:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
```

## Validation

Executed:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py \
  scripts/revalidation/wifi_execns_helper_v131_deploy_preflight.py
python3 scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py \
  --out-dir tmp/wifi/v856-pm-service-node-parity-plan-r4 plan
python3 scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py \
  --out-dir tmp/wifi/v856-pm-service-node-parity-start-only-r5 \
  --allow-helper-deploy \
  --allow-netservice-start \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-node-materialization \
  --allow-node-cleanup \
  --allow-pm-service-start-only \
  --assume-yes run
```

Result:

```text
decision: v856-pm-service-observable-without-subsys-hold
pass: True
pm_service_start_only_executed: True
mdm_helper_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next Gate

V857 should replay the narrow `pm-service` property contract only. It should add
a bounded helper mode or option that permits exactly the observed
`vendor.peripheral.shutdown_critical_list` values while keeping the same hard
gates: no `mdm_helper`, no `ks`, no CNSS retry, no Wi-Fi HAL, no scan/connect,
no credentials, no DHCP/routes, no external ping, no raw eSoC ioctl, and no
GPIO/sysfs/debugfs/subsystem writes.

V857 success should be one of:

- `pm-service` stays observable longer and holds `/dev/subsys_esoc0` plus
  `/dev/subsys_modem`; then V858 can plan `mdm_helper`/`ks` contract replay.
- `pm-service` still does not hold subsystem nodes; then classify missing init
  property/context/service input before any `mdm_helper` replay.
