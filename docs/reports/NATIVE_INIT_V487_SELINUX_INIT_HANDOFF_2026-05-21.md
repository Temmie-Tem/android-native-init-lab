# Native Init V487 SELinux Init Handoff Proof

- Date: 2026-05-21 KST
- Scope: bounded native-init SELinux kernel-to-init/domain handoff proof
- Result: `v487-selinux-init-handoff-kernel-stuck`
- Pass meaning: the next Wi-Fi blocker was narrowed; native-init Wi-Fi connect and external ping are still not achieved

## What Changed

- Added `a90_android_execns_probe v45`.
- Extended `selinux-domain-proof` to allow `u:r:init:s0` as a target context.
- Bound the live `/sys/fs/selinux` surface into the private proof namespace for this mode.
- Added `native_selinux_init_handoff_v487.py` to test `current`, `exec`, and `both` attr modes across init/HAL/manager domains.
- Added `wifi_execns_helper_v45_deploy_preflight.py` for bounded helper deployment.

## Evidence

- Build artifact: `tmp/wifi/v487-a90_android_execns_probe-v45/a90_android_execns_probe`
- Build SHA-256: `387b4f10a3f6e11805b1680cdf18f25f3be8b939826739e06edc7ea6b3c07770`
- Deploy preflight: `tmp/wifi/v487-helper-preflight-20260521-053009/manifest.json`
- Deploy evidence: `tmp/wifi/v487-helper-deploy-20260521-053024/manifest.json`
- Live evidence: `tmp/wifi/v487-selinux-init-handoff-20260521-053648/manifest.json`
- Live summary: `tmp/wifi/v487-selinux-init-handoff-20260521-053648/summary.md`
- SELinux surface probe: `tmp/wifi/v487-selinux-surface-probe-20260521-052558/`
- SELinux policy read-only probe: `tmp/wifi/v487-selinux-policy-size-20260521-053817/`

## Matrix Result

| context | current write | current match | exec write | exec match | postexec current | postexec match |
|---|---:|---:|---:|---:|---|---:|
| `u:r:init:s0` | `1` | `0` | `1` | `0` | `kernel` | `false` |
| `u:r:hal_wifi_default:s0` | `1` | `0` | `1` | `0` | `kernel` | `false` |
| `u:r:servicemanager:s0` | `1` | `0` | `1` | `0` | `kernel` | `false` |
| `u:r:hwservicemanager:s0` | `1` | `0` | `1` | `0` | `kernel` | `false` |

Representative facts:

```text
context.selinux_status.exists=1
context.selinux_enforce.exists=1
selinux_domain_proof.target_context=u:r:init:s0
selinux_domain_proof.write_current.ok=1
selinux_domain_proof.verify_current.match=0
selinux_domain_proof.verify_current.value=kernel
selinux_domain_proof.write_exec.ok=1
selinux_domain_proof.verify_exec.match=0
selinux_domain_proof.verify_exec.value=kernel
selinux_domain_proof.postexec.current=kernel
selinux_domain_proof.postexec.match=0
```

## Native SELinux Surface

Read-only probes show:

```text
/proc/filesystems: nodev selinuxfs
/proc/mounts: selinuxfs /sys/fs/selinux selinuxfs rw,relatime 0 0
/sys/fs/selinux/enforce: 0
/sys/fs/selinux/policyvers: 31
/proc/self/attr/current: kernel
/sys/fs/selinux/policy: Invalid argument
/mnt/system/system/etc/selinux/plat_sepolicy.cil: 1807055 bytes
```

The device has SELinuxfs mounted and platform policy files available on the mounted system partition, but native PID1 and children remain in the `kernel` context.

## AOSP Reference

AOSP init documents the expected Android path in `init/selinux.cpp`: early init starts in the kernel domain, loads SEPolicy, restores `/system/bin/init`, then execs `/system/bin/init second_stage` so init runs in the proper domain.

Relevant upstream reference:

- `https://chromium.googlesource.com/aosp/platform/system/core/+/upstream/init/selinux.cpp`
- `https://source.android.com/docs/security/features/selinux/vendor-init`

## Interpretation

- V486 proved HAL/manager target domains stayed `kernel` after static post-exec.
- V487 adds the missing init-domain case and proves even `u:r:init:s0` does not take effect in the current native runtime.
- Binding `/sys/fs/selinux` into the private namespace does not change the result.
- The current native init v319 code does not implement the AOSP SELinux setup path: no Android split-policy load, no restorecon of `/system/bin/init`, and no second-stage reexec into `u:r:init:s0`.
- Therefore, retrying Samsung Wi-Fi HAL registration without addressing native SELinux setup is unlikely to advance scan/connect/ping.

## Safety

- No service-manager, hwservicemanager, Wi-Fi HAL, CNSS, wpa_supplicant, wificond, scan, connect, DHCP, route change, credential read, or external ping was executed.
- All proof mutations were child-local procattr writes or helper deployment to `/cache/bin/a90_android_execns_probe`.
- Final postflight was clean.

## Next Work

1. Plan V488 as a read-only Android SELinux policy assembly inventory:
   - system/vendor/odm/product/system_ext policy file presence
   - precompiled policy hash compatibility
   - secilc availability
   - required mounts for AOSP `OpenSplitPolicy` equivalent
2. Decide whether to implement a native mini `LoadSelinuxPolicyAndroid` path or a narrower experimental policy-load helper.
3. Only after a child can enter `u:r:init:s0` or `u:r:hal_wifi_default:s0`, retry Samsung HAL registration.
4. Continue toward final Wi-Fi proof in this order: HAL registration, readiness calls, scan/connect/link-up, DHCP/routing, external ping.
