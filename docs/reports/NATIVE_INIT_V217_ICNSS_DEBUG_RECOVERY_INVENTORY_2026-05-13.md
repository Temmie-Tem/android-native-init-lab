# v217 ICNSS Debug / Recovery Inventory

## Summary

v217 adds a read-only ICNSS/CNSS debug and recovery inventory collector.

Result: PASS.

Final decision: `state-only-inventory`.

Reason: state evidence exists, but writable/recovery controls remain unsafe.

## Changes

- Added `scripts/revalidation/wifi_icnss_recovery_inventory.py`.
- Added v217 plan:
  `docs/plans/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_PLAN_2026-05-13.md`.

## Scope

The collector consumes v215/v216 manifests and optionally collects native bridge
read-only evidence. It writes:

- `tmp/wifi/v217-icnss-debug-recovery-inventory/manifest.json`
- `tmp/wifi/v217-icnss-debug-recovery-inventory/controls.json`
- `tmp/wifi/v217-icnss-debug-recovery-inventory/source-hints.json`
- `tmp/wifi/v217-icnss-debug-recovery-inventory/summary.md`

Native live validation writes the same files under:

- `tmp/wifi/v217-icnss-debug-recovery-inventory-native`

## Static Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_icnss_recovery_inventory.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_icnss_recovery_inventory
wifi_icnss_recovery_inventory.validate_no_active_commands()
print('v217 command guard PASS')
PY
```

Result:

```text
v217 command guard PASS
```

## Manifest-Only Run

Command:

```bash
python3 scripts/revalidation/wifi_icnss_recovery_inventory.py \
  --v215-manifest tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json \
  --v215-native-manifest tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json \
  --v216-manifest tmp/wifi/v216-service-replay-model/manifest.json \
  --out-dir tmp/wifi/v217-icnss-debug-recovery-inventory
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v217-icnss-debug-recovery-inventory decision=state-only-inventory reason=state evidence exists but writable/recovery controls remain unsafe
```

Risk summary:

```text
debug-state=1
ramdump-crash-evidence=11
read-only-state=144
writable-unknown=7
write-only-dangerous=3
```

## Native Read-Only Run

Command:

```bash
python3 scripts/revalidation/wifi_icnss_recovery_inventory.py \
  --native-bridge \
  --out-dir tmp/wifi/v217-icnss-debug-recovery-inventory-native
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v217-icnss-debug-recovery-inventory-native decision=state-only-inventory reason=state evidence exists but writable/recovery controls remain unsafe
```

Native capture result:

```text
captures=11
ok=11
controls=168
debug-state=1
ramdump-crash-evidence=11
read-only-state=146
writable-unknown=7
write-only-dangerous=3
```

## Important Controls

The collector classifies these as denied dangerous controls:

- `/sys/bus/platform/drivers/icnss/bind`
- `/sys/bus/platform/drivers/icnss/unbind`
- `/sys/devices/platform/soc/18800000.qcom,icnss/driver_override`

The collector classifies these as not safe for current recovery modeling:

- ICNSS `power/control` paths
- rfkill `soft` and `state` paths
- ramdump and crash-evidence paths
- debugfs-like state with unknown semantics

## Guardrails

- No ICNSS `bind`/`unbind`.
- No ICNSS sysfs/debugfs writes.
- No recovery/rejuvenate/shutdown/ramdump trigger writes.
- No service start.
- No Wi-Fi enablement.
- No rfkill write.
- No link-up.
- No scan/connect.

## Hashes

```text
25cf03d6b9ed89ae302040a0b4b90e90ecdad5d8335404cce87c950955953d31  scripts/revalidation/wifi_icnss_recovery_inventory.py
2a669a5f806572764ee492726f3fd7587651c687d74be54d3c0331405d47c115  docs/plans/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_PLAN_2026-05-13.md
8911f84b37274eabff6aa1dd385f7eab5cdf4bb60c74cb4f4011bfb0f0240473  tmp/wifi/v217-icnss-debug-recovery-inventory/manifest.json
cc7a9ba15ef8e0c7f47f7e9e7b076652cfdd0a2a1b73acd088f9345dfbe75c16  tmp/wifi/v217-icnss-debug-recovery-inventory/controls.json
a4a632d9733b139b9f2faac4e6876796dd4f5b95f9ede14bccc1ef5418fb3c8f  tmp/wifi/v217-icnss-debug-recovery-inventory/summary.md
3fc458b115251202ce83ecce2404b9f8e7a77acf19aa7eee8f20200aa89a72f1  tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json
8dcaea76b209bc40edc486d6d8a0a7215478407254d10bd92df1d8307b50d37d  tmp/wifi/v217-icnss-debug-recovery-inventory-native/controls.json
8edcd0234ef5565c40caadae61794967572ff9123e745583de8542140b430cf5  tmp/wifi/v217-icnss-debug-recovery-inventory-native/summary.md
```

## Decision

v217 does not identify a safe active recovery control. It does identify enough
read-only ICNSS state and ramdump/debug evidence to continue planning, but
future CNSS execution experiments must treat reboot as the only proven recovery
from broken ICNSS state unless a later explicit opt-in experiment proves
otherwise.

## Next

Plan v218 as CNSS daemon dry-run feasibility. It should inspect executable,
library, mount, property, socket, device-node, and capability requirements
without starting `cnss-daemon` or `cnss_diag`.
