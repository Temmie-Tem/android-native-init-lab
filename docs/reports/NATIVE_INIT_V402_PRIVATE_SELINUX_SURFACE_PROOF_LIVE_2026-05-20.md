# Native Init v402 Private SELinux Surface Proof Live Result

## Summary

V402 live execution completed successfully.

Two exact-approved live steps were run in sequence:

1. deploy `a90_android_execns_probe v22` to `/cache/bin/a90_android_execns_probe`.
2. run the helper in `private-selinux-proof` mode.

The private proof passed. The service-manager private execution namespace can now see the SELinux status/enforce surface, Binder devnodes, private property runtime tree, and Android service context inputs together.

This was not service-manager start-only and not Wi-Fi bring-up. `servicemanager`, `hwservicemanager`, Wi-Fi HAL, scan, connect, supplicant, hostapd, DHCP, routing, and Wi-Fi credentials were not executed.

## Approvals Used

Helper deploy:

```text
approve v402 deploy execns helper v22 only; no daemon start and no Wi-Fi bring-up
```

Private proof:

```text
approve v402 private selinux namespace proof only; no daemon start and no Wi-Fi bring-up
```

## Evidence

Primary evidence:

- helper deploy: `tmp/wifi/v402-execns-helper-v22-deploy-live-20260520-084231/`
- helper deploy manifest: `tmp/wifi/v402-execns-helper-v22-deploy-live-20260520-084231/manifest.json`
- private proof: `tmp/wifi/v402-private-selinux-surface-live-20260520-084832/`
- private proof manifest: `tmp/wifi/v402-private-selinux-surface-live-20260520-084832/manifest.json`
- private proof transcript: `tmp/wifi/v402-private-selinux-surface-live-20260520-084832/steps/private-selinux-proof.txt`
- postflight preflight: `tmp/wifi/v402-private-proof-postflight-20260520-084853/`

Deploy result:

```text
decision: execns-helper-v22-deploy-pass
pass: True
reason: helper v22 deployed or already current; V402 private proof preflight is ready
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Private proof result:

```text
decision: private-selinux-surface-proof-pass
pass: True
reason: private namespace SELinux/status/context inputs are visible
device_commands_executed: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Postflight result:

```text
decision: private-selinux-surface-proof-preflight-ready
pass: True
reason: read-only preflight is ready; live proof still needs approval
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Key Private Namespace Evidence

Selected lines from the approved private proof transcript:

```text
A90_EXECNS_BEGIN version="a90_android_execns_probe v22"
mode=private-selinux-proof
helper_status=namespace-ready

context.dev_binder.exists=1
context.dev_hwbinder.exists=1
context.dev_vndbinder.exists=1
context.dev_properties.exists=1

context.selinux_status.exists=1
context.selinux_status.mode=444
context.selinux_status.access_r=1
context.selinux_enforce.exists=1
context.selinux_enforce.mode=644
context.selinux_enforce.access_r=1
context.selinux_policy.exists=1

context.plat_service_contexts.exists=1
context.plat_hwservice_contexts.exists=1
context.vendor_service_contexts.exists=1
context.vendor_hwservice_contexts.exists=1

private_selinux_proof.result=pass
private_selinux_proof.exec_attempted=0
private_selinux_proof.daemon_start_executed=0
private_selinux_proof.wifi_bringup_executed=0
A90_EXECNS_END rc=0
```

The helper intentionally did not call `execve` for `servicemanager`; it only built the private namespace and reported visibility.

## Interpretation

V402 removes the private namespace SELinux surface blocker identified after V401.

Confirmed now:

- native `/sys/fs/selinux/status` and `/sys/fs/selinux/enforce` are mounted and readable.
- helper v22 is deployed on the device.
- the private service-manager namespace sees SELinuxfs status/enforce/policy.
- Binder devnodes are visible in the same namespace.
- the V317 private property runtime tree is visible as `/dev/__properties__`.
- system/vendor service context inputs are visible.
- no service-manager or Wi-Fi process was started by this proof.

Still not proven:

- `servicemanager` clean start.
- `servicemanager` interaction with Binder/service_contexts after actual execution.
- Wi-Fi HAL start-only.
- Wi-Fi scan/connect/link-up.

## Next Target

Proceed to V403: bounded service-manager start-only retry using helper v22 and the proven private SELinux/property/Binder namespace.

V403 must remain a separate approval packet. It should still exclude Wi-Fi HAL start, scan, connect, credentials, DHCP, routing, supplicant, and hostapd. If `servicemanager` starts cleanly or reaches a narrower runtime gap, only then should the next Wi-Fi HAL readiness packet be considered.
