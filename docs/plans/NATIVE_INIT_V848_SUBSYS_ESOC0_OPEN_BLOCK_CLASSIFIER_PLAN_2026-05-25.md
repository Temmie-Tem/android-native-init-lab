# Native Init V848 subsys_esoc0 Open-Block Classifier Plan

## Goal

Classify the V847 `/dev/subsys_esoc0` open-block boundary using only host-side
evidence and Samsung OSRC source before any further live retry.

## Inputs

- V846 contract: `tmp/wifi/v846-mdm3-esoc-state-control-contract/manifest.json`
- V847 live smoke: `tmp/wifi/v847-subsys-esoc0-char-open-smoke/manifest.json`
- V847 evidence directory: `tmp/wifi/v847-subsys-esoc0-char-open-smoke/`
- Samsung OSRC source root: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel`

## Method

1. Verify V846 selected the source-backed `subsys_esoc0` char-device path.
2. Verify V847 reached `__subsystem_get(esoc0)` and changed `fw_name`.
3. Verify V847 did not complete open or show MHI/PCIe/WLFW/BDF/`wlan0`.
4. Map the remaining boundary through `subsys_start()`, provider `powerup()`,
   and `wait_for_err_ready()` source anchors.
5. Confirm the ESOC MDM configs are enabled while the actual eSoC MDM provider
   source is absent from the staged OSRC tree.
6. Reject blind longer retries, raw eSoC ioctls, GPIO/sysfs writes, MHI writes,
   and upper Wi-Fi layers until lower wait-state evidence exists.

## Guardrails

- Host-only classification.
- No device command, `mknod`, char-device open, raw `/dev/esoc*` open/ioctl,
  sysfs/GPIO/debugfs write, bind/unbind, module load/unload, daemon start,
  service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes,
  external ping, boot image write, partition write, or custom kernel flash.

## Success Criteria

- V847 entry and block signals are classified.
- Source anchors identify the remaining boundary below `__subsystem_get()` and
  inside/under `subsys_start()`.
- The two remaining block candidates are explicit: provider `powerup()` GPIO
  handshake vs `wait_for_err_ready()` completion wait.
- The missing OSRC eSoC provider source is recorded as a blocker to source-only
  branch attribution.
- The next live gate is limited to bounded wait-state sampling with cleanup.

## Command

```bash
python3 scripts/revalidation/native_wifi_subsys_esoc0_open_block_classifier_v848.py \
  --out-dir tmp/wifi/v848-subsys-esoc0-open-block-classifier \
  run
```
