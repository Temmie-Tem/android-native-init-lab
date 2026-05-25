# Native Init V851 ext-mdm Provider Surface Snapshot Plan

## Goal

Capture the live read-only provider surface around the V849
`mdm_subsys_powerup` blocker, using the V850 classification and the
`mdm3/ext-sdx50m/eSoC` research note as the route.

## Inputs

- V850 classifier:
  `tmp/wifi/v850-ext-mdm-powerup-surface-classifier/manifest.json`
- V849 wait-state evidence:
  `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/`
- Research overview:
  `docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md`

## Method

1. Confirm native v724 health before and after the snapshot.
2. Capture filtered `/proc/kallsyms` for subsystem/eSoC/MHI provider symbols.
3. Capture filtered `/proc/interrupts` for mdm/eSoC/GPIO/PMIC/MHI/PCIe lines.
4. Capture mdm3/eSoC/msm_subsys sysfs and live devicetree properties.
5. Capture readable GPIO/debug/pinctrl surfaces if already available.
6. Capture focused dmesg without triggering another `subsys_esoc0` open.

## Guardrails

- Live read-only only.
- No raw `/dev/esoc*` or `/dev/subsys*` open/ioctl.
- No GPIO/sysfs/debugfs write, GPIO export, subsystem state write, bind/unbind,
  driver override, module load/unload, daemon start, service-manager, Wi-Fi HAL,
  scan/connect, credential use, DHCP/routes, external ping, boot image write,
  partition write, or custom kernel flash.

## Success Criteria

- Runtime health remains `BOOT OK` with selftest `fail=0`.
- Provider-level symbol/IRQ/sysfs/devicetree/GPIO/pinctrl/dmesg surface is
  captured without mutation.
- The result selects whether to proceed to Android comparison, public-source
  cross-reference, or a more bounded provider action.

## Command

```bash
python3 scripts/revalidation/native_wifi_ext_mdm_provider_surface_snapshot_v851.py \
  --out-dir tmp/wifi/v851-ext-mdm-provider-surface-snapshot \
  --allow-live-readonly \
  --assume-yes \
  run
```
