# V904 mdm_helper Runtime Input Parity Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| classifier | `scripts/revalidation/native_wifi_mdm_helper_runtime_input_parity_v904.py` | host-only pass |
| manifest | `tmp/wifi/v904-mdm-helper-runtime-input-parity/manifest.json` | `v904-mdm-helper-runtime-input-parity-classified` |
| summary | `tmp/wifi/v904-mdm-helper-runtime-input-parity/summary.md` | pass |

V904 classified the V903 native failure boundary as a runtime-input parity gap,
not a reason to repeat `/dev/subsys_esoc0` open directly.

## Findings

- Android positive contract is present:
  - `mdm_helper` runs as `u:r:vendor_mdm_helper:s0`;
  - `mdm_helper` holds `/dev/esoc-0`;
  - `ks` runs as `u:r:vendor_mdm_helper:s0` with
    `/dev/mhi_0305_01.01.00_pipe_10`;
  - `pm-service` holds `/dev/subsys_esoc0` and `/dev/subsys_modem`;
  - `vendor.mdm_helper` is an init service;
  - init starts `vendor.mdm_helper` after
    `init.svc.vendor.per_mgr=running`.
- Native V903 negative contract is present:
  - native direct `mdm_helper` is observable;
  - `attr/current` remains `kernel`;
  - final wait state is `SyS_nanosleep`;
  - final fds are `/dev/ttyGS0`, two pipes, and one socket;
  - no `/dev/esoc-0`, `/dev/subsys_esoc0`, MHI pipe, or `ks` appears.
- Android/native deltas:
  - SELinux context mismatch:
    Android `u:r:vendor_mdm_helper:s0`, native `kernel`;
  - init service mismatch:
    Android has `vendor.mdm_helper` service and `vendor.per_mgr` trigger,
    native V903 starts `mdm_helper` directly;
  - peripheral-manager mismatch:
    Android `pm-service` owns subsystem nodes before image-link activity,
    native V903 does not start it;
  - device fd mismatch:
    Android reaches `/dev/esoc-0` and MHI, native reaches neither.

## Interpretation

The next blocker sits above the kernel `mdm_subsys_powerup` wait. Native direct
`mdm_helper` lacks the Android runtime contract that makes `mdm_helper` enter
its eSoC/MHI path.

The best next step is not another subsystem-open retry. V905 should design a
fail-closed repair around the missing runtime inputs, prioritizing:

1. SELinux/init service context parity for `vendor.mdm_helper`;
2. `vendor.per_mgr` / `pm-service` trigger and subsystem-node ownership;
3. property/socket/environment parity needed by `mdm_helper`;
4. only then a bounded live proof that observes `/dev/esoc-0`, `ks`, MHI, GPIO
   142, `mdm3`, WLFW/BDF, and `wlan0`.

## Guardrails

- V904 is host-only.
- No device contact, Android boot, ADB command, actor start, daemon start,
  live eSoC ioctl, subsystem open, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, module load/unload, reboot, or Wi-Fi
  link-up occurred.

## Next

V905 should be a source/design classifier for a fail-closed runtime-input repair
mode. It should decide whether to emulate init/SELinux/property context first,
start `pm-service`/peripheral-manager first, or require one focused Android
recapture for missing property/socket evidence.
