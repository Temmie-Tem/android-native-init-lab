# v203 Wi-Fi Read-Only Baseline Refresh

## Summary

v203 adds and validates a host-side Wi-Fi baseline collector. The run was
read-only and did not change Wi-Fi, rfkill, module, firmware, service, firewall,
storage, debug, PID1, or boot-image state.

Result: PASS.

Final decision: `no-go` for active Wi-Fi bring-up.

Reason: mounted Android-side candidates exist, but native kernel-facing Wi-Fi
gates remain absent.

## Changes

- Added `scripts/revalidation/wifi_baseline_refresh.py`.
- Added private evidence output under `tmp/wifi/v203-baseline`.
- Added bridge option aliases `--bridge-host` and `--bridge-port`.
- Added `--mount-system-ro` / `--no-mount-system-ro` control.
- Added automatic kernel capability summary refresh fallback when default source
  JSON inputs are missing.
- Added static guard for active Wi-Fi mutation command strings.
- Fixed candidate path parsing so report candidates come from real `match path=`
  or `exists=yes path=` evidence, not malformed status text.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_baseline_refresh.py \
  scripts/revalidation/wifi_inventory_collect.py \
  scripts/revalidation/kernel_capability_summary.py \
  scripts/revalidation/a90_kernel_tools.py \
  scripts/revalidation/a90harness/evidence.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts/revalidation")
import wifi_baseline_refresh
wifi_baseline_refresh.validate_no_active_wifi_commands()
print("wifi baseline command guard PASS")
PY
```

Result: PASS.

```bash
python3 scripts/revalidation/wifi_baseline_refresh.py \
  --out-dir tmp/wifi/v203-baseline
```

Result: PASS.

Evidence:

- `tmp/wifi/v203-baseline/summary.md`
- `tmp/wifi/v203-baseline/manifest.json`
- `tmp/wifi/v203-baseline/kernel-capability/summary.md`
- `tmp/wifi/v203-baseline/kernel-capability/summary.json`
- `tmp/wifi/v203-baseline/commands/`

Hashes:

- `tmp/wifi/v203-baseline/manifest.json`: `a7f56606697f40515c6875f655a5c2041975d38a616acd82a90e1d9b3fd011df`
- `tmp/wifi/v203-baseline/summary.md`: `659e29d3225f44607f60e7266b97216f68cbda6bd21821bc8fd3f16b97b7e6ae`
- `tmp/wifi/v203-baseline/kernel-capability/summary.json`: `2e26aadbb5811660a1b09ca4f0937394bb55b326852276a355bbda93c35079c3`

## Live Result

- Expected version: `A90 Linux init 0.9.59 (v159)`
- Version match: PASS
- `wififeas gate`: `baseline-required`, `rc=0`, `status=ok`
- Kernel capability summary: PASS
- Kernel Wi-Fi gate: `baseline-required`
- Mounted system phase: captured with `mountsystem ro`
- Device captures: 16
- Host captures: 1
- Manual ADB captures: 0

## Wi-Fi Gate Evidence

Native pre-mount gate:

```text
wififeas: decision=baseline-required
wififeas: reason=native default sees no wlan/rfkill/module and no Android/vendor candidates
wififeas: next=collect mountsystem-ro or Android/TWRP read-only baseline before bring-up
```

Mounted-system feasibility:

```text
decision=no-go
reason=Android-side candidates exist but kernel-facing wlan/rfkill/module gates are missing
gates wlan=no rfkill=no module=no candidates=yes proc_modules=yes
inventory net=9 wlan=0 rfkill=1 wifi_rfkill=0 modules=0 paths=7/26 files=8
```

Missing gates:

- `native-wlan-interface`
- `wifi-rfkill`
- `wlan-cnss-qca-module-evidence`

## Captured Android-Side Candidates

Real mounted-system matches observed in the evidence:

- `/mnt/system/system/etc/sysconfig/carrierwifi-sysconfig.xml`
- `/mnt/system/system/etc/init/wifi.rc`
- `/mnt/system/system/etc/init/wificond.rc`
- `/mnt/system/system/etc/permissions/carrierwifi.xml`
- `/mnt/system/system/etc/permissions/privapp-permissions-com.samsung.android.server.wifi.mobilewips.xml`

These are Android-side framework/init/permission candidates. They do not prove a
native kernel-facing WLAN device, Wi-Fi rfkill node, or WLAN/CNSS/QCA module is
available in the current native-init environment.

## Acceptance

- The collector captured live `wififeas gate` with `rc=0/status=ok`.
- The evidence bundle records commands, output files, version match, decision,
  missing gates, and candidate files.
- No active Wi-Fi bring-up was attempted.
- The result blocks Wi-Fi enablement and points the next step to read-only
  Android/TWRP driver/firmware baseline or controlled read-only kernel probe
  planning.

## Next

Do not start active Wi-Fi bring-up from native init yet. Recommended v204 scope:
read-only Android/TWRP Wi-Fi driver and firmware baseline, focused on locating
actual vendor driver, firmware, module, rfkill, and `nl80211` evidence before any
write-side Wi-Fi operation is designed.
