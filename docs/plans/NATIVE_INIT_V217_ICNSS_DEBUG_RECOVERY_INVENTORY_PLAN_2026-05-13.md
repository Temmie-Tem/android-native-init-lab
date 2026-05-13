# v217 Plan: ICNSS Debug / Recovery Inventory

## Summary

v217 follows v216 `replay-model-ready`. The goal is to map the ICNSS/CNSS
debug, recovery, ramdump, PDR/SSR, and firmware-service surface before any
Android Wi-Fi/CNSS service is executed.

This version is read-only. It must not write ICNSS sysfs/debugfs controls,
repeat generic platform-driver `unbind`/`bind`, start `cnss-daemon`, or bring up
Wi-Fi.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v216 PASS, `replay-model-ready`
- planned collector: `scripts/revalidation/wifi_icnss_recovery_inventory.py`
- evidence input:
  - `tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json`
  - `tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json`
  - `tmp/wifi/v216-service-replay-model/manifest.json`
- evidence output: `tmp/wifi/v217-icnss-debug-recovery-inventory`
- report after execution:
  `docs/reports/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_2026-05-13.md`

## Reference Notes

- Qualcomm ICNSS sources create debugfs and sysfs surfaces and register
  recovery, ramdump, PDR/SSR, and firmware-service paths. These names must be
  inventoried before selecting any control path:
  <https://android.googlesource.com/kernel/msm/+/289f176f9259d8f663478a246542cf6be4ed3d24/drivers/soc/qcom/icnss.c>
- Other ICNSS variants expose debugfs files such as `stats`, `fw_debug`,
  `reg_read`, and `reg_write`, and may create sysfs shutdown/recovery nodes.
  Writable nodes must be classified, not exercised:
  <https://android.googlesource.com/kernel/msm.git/+/03c2d42aa4bc362578b3824a81583638e2e23151/drivers/soc/qcom/icnss.c>
- v214 showed that generic Linux driver-model reprobe is unsafe for this
  device state. v217 must not treat platform `bind`/`unbind` as recovery:
  <https://docs.kernel.org/6.7/driver-api/driver-model/driver.html>
- ICNSS device tree bindings describe the Q6 integrated WLAN control model,
  QMI communication, and PD restart relationship. This supports the assumption
  that userspace service ordering matters:
  <https://android.googlesource.com/kernel/msm/+/157ab4a1b7d2bf3275a20ee90d855bec184d742e/Documentation/devicetree/bindings/cnss/icnss.txt>

## Current Evidence Chain

- v214 proves generic ICNSS platform-driver `unbind`/`bind` can leave the driver
  broken until reboot.
- v215 proves native ICNSS state is visible, but WLAN netdev/wiphy/rfkill state
  still does not appear in native init.
- v216 models Android's first-class Wi-Fi/CNSS service chain and keeps
  `cnss-daemon`/`cnss_diag` blocked until ICNSS recovery/debug inventory exists.

## Scope

Allowed:

- parse v215/v216 manifests and summaries
- collect read-only native bridge evidence
- collect optional Android/TWRP read-only evidence if the operator already has
  the device in that mode
- list ICNSS sysfs/debugfs paths
- read regular read-only files with bounded size
- stat writable files without writing them
- classify path risk by name, permissions, file type, and source-reference hints
- write host-only private evidence bundles

Forbidden:

- ICNSS platform `unbind` or `bind`
- writing any `/sys/devices/platform/soc/18800000.qcom,icnss/*` path
- writing any `/sys/kernel/debug/*icnss*` path
- recovery, rejuvenate, shutdown, ramdump trigger, firmware assert, `reg_write`,
  or test-mode writes
- Wi-Fi scan/connect
- rfkill writes
- `ip link set wlan* up`
- module load/unload
- firmware path writes
- Android service start or `ctl.start`
- boot image or PID1 change

## Collector Design

Add `scripts/revalidation/wifi_icnss_recovery_inventory.py`.

Default mode:

- manifest-only when no live mode is selected
- no live device command by default
- validate that command lists contain no active mutation pattern

Optional native mode:

```sh
python3 scripts/revalidation/wifi_icnss_recovery_inventory.py \
  --native-bridge \
  --out-dir tmp/wifi/v217-icnss-debug-recovery-inventory-native
```

Native read-only captures:

- `version`
- `status`
- `bootstatus`
- `cat /sys/devices/platform/soc/18800000.qcom,icnss/uevent`
- `find /sys/devices/platform/soc/18800000.qcom,icnss -maxdepth 8`
- `find /sys/bus/platform/drivers/icnss -maxdepth 3`
- `find /sys/kernel/debug -maxdepth 6`
- `stat` for every ICNSS/CNSS-looking sysfs/debugfs path
- bounded `cat` only for paths classified as regular read-only safe
- filtered `dmesg`

Optional Android/TWRP read-only captures:

- ICNSS/CNSS sysfs/debugfs tree
- `getprop` service states for `cnss`, `icnss`, `wlan`, `wifi`
- filtered `dmesg` and `logcat` where available
- `ps -A` filtered for CNSS/Wi-Fi services

## Risk Classifier

Every discovered candidate path should be classified as one of:

- `read-only-state`
  - safe to read; examples: `uevent`, `modalias`, `driver`, selected `stats`
- `write-only-dangerous`
  - must not be written; examples: `bind`, `unbind`, `reg_write`,
    `force_fw_assert`, recovery/shutdown triggers
- `writable-unknown`
  - writable but semantics not confirmed
- `debug-state`
  - debugfs state that may be readable but should be bounded and redacted
- `ramdump-crash-evidence`
  - existing crash/ramdump evidence only
- `source-hint-only`
  - present in source/reference, absent on current device

Risk keywords:

- dangerous: `bind`, `unbind`, `shutdown`, `recovery`, `rejuvenate`, `assert`,
  `crash`, `ramdump`, `reg_write`, `testmode`, `fw_debug`
- state: `uevent`, `modalias`, `state`, `stats`, `version`, `status`,
  `firmware`, `pdr`, `ssr`, `service`

## Output Model

The collector should write:

- `manifest.json`
- `summary.md`
- `controls.json`
- `source-hints.json`

Each control entry should include:

- path
- origin: `native`, `android`, `twrp`, `source-hint`
- file type
- mode/permissions
- owner/group if available
- read attempted: true/false
- read rc/status if attempted
- risk class
- reason
- related source hint if any

## Decision Model

- `safe-control-candidate`
  - at least one documented or clearly read-only recovery/status path exists
    that can guide a future bounded experiment without generic reprobe.
- `state-only-inventory`
  - useful state evidence exists, but no control path is safe enough to use.
- `no-safe-control`
  - no safer control is visible; reboot remains the only known recovery from
    broken ICNSS state.
- `insufficient-evidence`
  - current manifests are not enough; optional Android/TWRP/native live evidence
    is required.
- `manual-review-required`
  - controls are visible but semantics are ambiguous or risky.

## Validation

Static:

```sh
python3 -m py_compile scripts/revalidation/wifi_icnss_recovery_inventory.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_icnss_recovery_inventory
wifi_icnss_recovery_inventory.validate_no_active_commands()
print('v217 command guard PASS')
PY
```

Manifest-only:

```sh
python3 scripts/revalidation/wifi_icnss_recovery_inventory.py \
  --v215-manifest tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json \
  --v215-native-manifest tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json \
  --v216-manifest tmp/wifi/v216-service-replay-model/manifest.json \
  --out-dir tmp/wifi/v217-icnss-debug-recovery-inventory
```

Native read-only:

```sh
python3 scripts/revalidation/wifi_icnss_recovery_inventory.py \
  --native-bridge \
  --out-dir tmp/wifi/v217-icnss-debug-recovery-inventory-native
```

## Acceptance

- No active Wi-Fi, service-start, sysfs-write, or ICNSS reprobe command exists
  in the collector's default or live command sets.
- Manifest-only mode works from existing v215/v216 evidence.
- Native mode works through bridge with only read-only commands.
- Every discovered ICNSS/CNSS candidate path is classified by risk.
- The summary explicitly states whether v218 can proceed to CNSS daemon dry-run
  feasibility or whether reboot remains the only accepted recovery path.

## Next Step

If v217 returns `safe-control-candidate` or `state-only-inventory`, v218 should
continue to CNSS daemon dry-run feasibility without executing the daemon. If it
returns `no-safe-control`, v218 must treat reboot as the only recovery path and
raise the opt-in threshold for any future CNSS execution experiment.
