# Native Init v402 Private SELinux Surface Proof Packet

## Summary

V402 prepares the next bounded Wi-Fi-readiness step after V401.

V401 mounted `selinuxfs` successfully in the native host namespace. V402 adds a helper v22 proof mode and guarded host runners so the next approved live step can prove the service-manager private execution namespace sees SELinuxfs, binder, private properties, and Android service context inputs together.

This packet did not deploy helper v22, start `servicemanager`, start Wi-Fi HAL, scan, connect, write SELinux policy, change SELinux enforcement, or bring up Wi-Fi.

## Scope

Included:

- helper v22 static build support in `stage3/linux_init/helpers/a90_android_execns_probe.c`.
- deploy preflight wrapper: `scripts/revalidation/wifi_execns_helper_v22_deploy_preflight.py`.
- private proof runner: `scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py`.
- exact approval phrases for deploy and private proof.

Excluded:

- service-manager execution.
- ptrace/crash capture.
- Wi-Fi HAL, scan, connect, credentials, DHCP, routing, supplicant, hostapd.
- SELinux policy writes or enforcement changes.
- Android partition writes.

## Validation

Static validation passed:

```text
python3 -m py_compile scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py scripts/revalidation/wifi_execns_helper_v22_deploy_preflight.py
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v402-a90_android_execns_probe-v22/a90_android_execns_probe
git diff --check
```

Helper artifact:

```text
tmp/wifi/v402-a90_android_execns_probe-v22/a90_android_execns_probe
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
sha256: 55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6
marker: a90_android_execns_probe v22
mode token: private-selinux-proof
```

Private proof no-approval refusal:

```text
evidence: tmp/wifi/v402-private-proof-noapproval-run-fixed/
decision: private-selinux-surface-proof-approval-required
pass: True
reason: exact approval phrase required; no device command executed
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Deploy no-approval refusal:

```text
evidence: tmp/wifi/v402-deploy-noapproval-run-fixed/
decision: execns-helper-v22-deploy-approval-required
pass: True
reason: exact approval phrase required; no mutation executed
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Private proof read-only preflight:

```text
evidence: tmp/wifi/v402-private-proof-preflight-current/
decision: private-selinux-surface-proof-blocked
pass: False
reason: blocked by helper-v22
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Key preflight checks:

| check | status | detail |
| --- | --- | --- |
| `native-health` | `pass` | `status/selftest fail=0 expected` |
| `helper-v22` | `blocked` | `remote helper must be v22 with private-selinux-proof mode` |
| `native-selinux-status-visible` | `pass` | `global /sys/fs/selinux/status and enforce must be visible` |
| `private-property-root-visible` | `pass` | `/mnt/sdext/a90/private-property-v317/dev/__properties__` |
| `linkerconfig-inputs-visible` | `pass` | `real linkerconfig/apex library config expected` |
| `service-manager-processes-clean` | `pass` | `process_count=0` |
| `wifi-link-surface-clean` | `pass` | `wifi_link_count=0` |

Deploy read-only preflight:

```text
evidence: tmp/wifi/v402-deploy-preflight-current-fixed/
decision: execns-helper-v22-deploy-preflight-ready-needs-deploy
pass: True
reason: preflight complete; helper v22 deploy still requires exact approval
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Approval Phrases

Deploy helper v22:

```text
approve v402 deploy execns helper v22 only; no daemon start and no Wi-Fi bring-up
```

Run private SELinux namespace proof:

```text
approve v402 private selinux namespace proof only; no daemon start and no Wi-Fi bring-up
```

## Interpretation

V402 is ready for the next approved live step, but it has not performed that step.

The current device-side blocker is intentionally narrow: `/cache/bin/a90_android_execns_probe` is still older than v22. Once v22 is deployed under the exact deploy approval, the private proof runner can verify the namespace surface without daemon execution.

If the private proof passes, the next separate target is a bounded service-manager start-only retry. Wi-Fi HAL/start/scan/connect remains blocked.
