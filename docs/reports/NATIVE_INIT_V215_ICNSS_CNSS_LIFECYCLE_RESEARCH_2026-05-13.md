# v215 ICNSS/CNSS Lifecycle Research

## Summary

v215 adds a host-side read-only lifecycle collector for ICNSS/CNSS Wi-Fi
bring-up planning. It does not change the native init boot image and does not
start Wi-Fi services.

Result: PASS.

Final decision: `lifecycle-map-ready`.

Reason: Android lifecycle evidence plus the v214 ICNSS reprobe failure are
sufficient to design the v216 Android service replay model.

## Changes

- Added `scripts/revalidation/wifi_icnss_lifecycle_collect.py`.
- Added v215 plan:
  `docs/plans/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_PLAN_2026-05-13.md`.

## Scope

The collector combines:

- v204 Android/TWRP Wi-Fi baseline manifest
- v206 Android ICNSS/CNSS dependency map manifest
- v214 ICNSS reprobe safety-stop manifest
- optional native read-only bridge captures
- optional Android/TWRP read-only ADB captures

The default run can operate in manifest-only mode. Live modes are optional.

## Guardrails

- No ICNSS bind/unbind.
- No Wi-Fi enablement.
- No rfkill write.
- No WLAN link-up.
- No scan/connect.
- No module load/unload.
- No `firmware_class.path` write.
- No firmware mutation.
- No Android Wi-Fi service/supplicant/hostapd/cnss-daemon start.
- No `/data/misc/wifi` default collection.

## Static Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_icnss_lifecycle_collect.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_icnss_lifecycle_collect
wifi_icnss_lifecycle_collect.validate_no_active_commands()
print('v215 command guard PASS')
PY
```

Result:

```text
v215 command guard PASS
```

```bash
git diff --check
```

Result: PASS.

## Manifest-Only Validation

Command:

```bash
python3 scripts/revalidation/wifi_icnss_lifecycle_collect.py \
  --v204-android-manifest tmp/wifi/v204-android-baseline/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --v214-manifest tmp/wifi/v214-icnss-reprobe/manifest.json \
  --out-dir tmp/wifi/v215-icnss-cnss-lifecycle
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v215-icnss-cnss-lifecycle decision=lifecycle-map-ready reason=Android lifecycle evidence plus v214 failure are sufficient for v216 service replay modeling
```

Evidence:

- `tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json`
- `tmp/wifi/v215-icnss-cnss-lifecycle/summary.md`

Summary:

- live captures: `0/0`
- service evidence: `51`
- init evidence: `48`
- firmware evidence: `26`
- interface evidence: `130`
- ICNSS evidence: `120`
- QMI evidence: `17`
- log evidence: `120`

## Native Bridge Validation

Native bridge was available and responded to `cmdv1 version`:

```text
A90 Linux init 0.9.59 (v159)
```

Command:

```bash
python3 scripts/revalidation/wifi_icnss_lifecycle_collect.py \
  --native-bridge \
  --v204-android-manifest tmp/wifi/v204-android-baseline/manifest.json \
  --v206-manifest tmp/wifi/v206-android-icnss-cnss-map/manifest.json \
  --v214-manifest tmp/wifi/v214-icnss-reprobe/manifest.json \
  --out-dir tmp/wifi/v215-icnss-cnss-lifecycle-native
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v215-icnss-cnss-lifecycle-native decision=lifecycle-map-ready reason=Android lifecycle evidence plus v214 failure are sufficient for v216 service replay modeling
```

Evidence:

- `tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json`
- `tmp/wifi/v215-icnss-cnss-lifecycle-native/summary.md`

Summary:

- live captures: `16/16`
- service evidence: `51`
- init evidence: `48`
- firmware evidence: `28`
- interface evidence: `133`
- ICNSS evidence: `160`
- QMI evidence: `17`
- log evidence: `160`
- debug/recovery candidate lines: `16`

## Hashes

```text
e579abef104ac2ee80e6df1bb22fa5f357c143fa8becf38f9b40210f45ea39ba  scripts/revalidation/wifi_icnss_lifecycle_collect.py
812a0ef6206b6674e16fa1f644ba303ef4f3881eef8e523f25da28894df76b2d  docs/plans/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_PLAN_2026-05-13.md
9493d4a49bc765995b3c6457789d43d1e2a991f9942ff8d26256ab4eab45d23c  tmp/wifi/v215-icnss-cnss-lifecycle/manifest.json
7efbb8502f4fe807813d677eb786cc1d929475c4d853a7619c8d4dee76fbdfad  tmp/wifi/v215-icnss-cnss-lifecycle/summary.md
ccb0cf548f6598db1f5c9d16b758c01a100acc5894cc22b640b70eeadd1e60dc  tmp/wifi/v215-icnss-cnss-lifecycle-native/manifest.json
c2afb378eebd90fc8be46bda995d8287c69c0c442cd10b69a662ef2f5a9a7349  tmp/wifi/v215-icnss-cnss-lifecycle-native/summary.md
```

## Decision

v215 confirms the next step should not be another ICNSS reprobe or Wi-Fi scan.
The evidence is sufficient to move to v216, which should build an Android
service replay model from the known-good Android service chain and the native
gap.

The v216 model should treat the following as first-class dependencies:

- `cnss-daemon`
- `cnss_diag`
- Wi-Fi HAL services
- `wificond`
- `wpa_supplicant`
- vendor init rc service/class/property triggers
- required firmware paths
- ICNSS-backed `wlan0`/`ieee80211` state
- QMI/QRTR-adjacent readiness evidence

## Next

Plan v216 as Android service replay modeling. Keep active Wi-Fi bring-up,
rfkill writes, link-up, scan/connect, and generic ICNSS bind/unbind blocked.
