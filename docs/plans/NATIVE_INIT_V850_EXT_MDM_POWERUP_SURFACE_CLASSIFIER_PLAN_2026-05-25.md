# Native Init V850 ext-mdm Powerup Surface Classifier Plan

## Goal

Classify the V849 `mdm_subsys_powerup` blocker without live mutation and select
the next safe provider-surface gate.

## Inputs

- V845 mdm3/ext-sdx50m read-only surface:
  `tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot/manifest.json`
- V849 wait-state sampler:
  `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/manifest.json`
- V849 evidence directory:
  `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/`
- Android reference:
  `docs/reports/NATIVE_INIT_V591_ANDROID_SUBSYS_STATE_HANDOFF_2026-05-22.md`
- Samsung OSRC source root:
  `kernel_build/SM-A908N_KOR_12_Opensource/Kernel`

## Method

1. Confirm V849 captured `mdm_subsys_powerup` D-state before
   `wait_for_err_ready`.
2. Confirm Android can bring the same mdm3/WLAN-PD surface online.
3. Map DTS/AP2MDM/MDM2AP GPIO and IRQ contract.
4. Confirm ESOC MDM configs are enabled while provider source is absent.
5. Reject blind longer holds, raw eSoC ioctls, GPIO/sysfs writes, MHI writes,
   and Wi-Fi HAL/scan/connect until provider-surface evidence improves.

## Guardrails

- Host-only classification.
- No device command, node creation, char open, raw eSoC open/ioctl,
  GPIO/sysfs/debugfs write, bind/unbind, module load/unload, daemon start,
  service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes,
  external ping, boot image write, partition write, or custom kernel flash.

## Success Criteria

- Current blocker is classified as ext-mdm provider `powerup()` level.
- DTS and Android reference explain why this path matters for WLFW publication.
- The next gate is read-only and does not widen into upper Wi-Fi.

## Command

```bash
python3 scripts/revalidation/native_wifi_ext_mdm_powerup_surface_classifier_v850.py \
  --out-dir tmp/wifi/v850-ext-mdm-powerup-surface-classifier \
  run
```
