# v204 Android/TWRP Wi-Fi Driver and Firmware Baseline

## Summary

v204 adds and validates a host-side Android/TWRP Wi-Fi baseline collector. The
first validated run used TWRP ADB in read-only mode. A second run temporarily
restored the Magisk Android boot image, confirmed Android ADB + Magisk root, and
captured Android Wi-Fi evidence in read-only collector mode.

The collector did not enable Wi-Fi, write rfkill state, bring up a WLAN
interface, load or unload modules, mutate firmware, or start Wi-Fi services.

Result: PASS.

Final decision: `ready-for-readonly-nl80211-probe-plan`.

Reason: Android exposes `wlan0`/`swlan0`/`p2p0`/`wifi-aware0`, an ICNSS-backed
Wi-Fi rfkill path, firmware/HAL/init service assets, and root-readable ICNSS/WLAN
kernel logs. Native init still lacks those gates, so the next step remains
read-only probing and mapping rather than active Wi-Fi bring-up.

## Changes

- Added `scripts/revalidation/android_twrp_wifi_baseline.py`.
- Added Android/TWRP ADB read-only collection modes:
  - `--android-adb`
  - `--twrp-adb`
  - `--serial`
  - `--v203-manifest`
  - `--out-dir`
- Added private evidence output with:
  - `manifest.json`
  - `summary.md`
  - `compare/v203-v204-matrix.json`
  - per-command transcripts under `<mode>/commands/`
- Added active Wi-Fi command guard.
- Added redaction for MAC-like values and boot serial fields in captured output.
- Tightened classifier logic so Bluetooth-only rfkill and generic Wi-Fi strings
  do not count as a Wi-Fi kernel gate.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/android_twrp_wifi_baseline.py \
  scripts/revalidation/wifi_baseline_refresh.py \
  scripts/revalidation/a90_kernel_tools.py \
  scripts/revalidation/a90harness/evidence.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts/revalidation")
import android_twrp_wifi_baseline
android_twrp_wifi_baseline.validate_no_active_wifi_commands()
print("android/twrp wifi baseline command guard PASS")
PY
```

Result: PASS.

TWRP transition and ADB state:

- native bridge `recovery` command succeeded
- TWRP ADB detected: `ro.twrp.version=3.7.0_12-0`
- TWRP kernel: `Linux localhost 4.14.190-Grass,SD855-Perf+ ... aarch64`

Collector run:

```bash
python3 scripts/revalidation/android_twrp_wifi_baseline.py \
  --twrp-adb \
  --v203-manifest tmp/wifi/v203-baseline/manifest.json \
  --out-dir tmp/wifi/v204-twrp-baseline
```

Result: PASS.

Evidence:

- `tmp/wifi/v204-twrp-baseline/summary.md`
- `tmp/wifi/v204-twrp-baseline/manifest.json`
- `tmp/wifi/v204-twrp-baseline/compare/v203-v204-matrix.json`
- `tmp/wifi/v204-twrp-baseline/twrp/commands/`

Hashes:

- `tmp/wifi/v204-twrp-baseline/manifest.json`: `1ff07fb5b17323f3c6e23fc5d9f3c708b84d60f574d75159c61d8b253b70cf30`
- `tmp/wifi/v204-twrp-baseline/summary.md`: `83439cbdd24835601ba9dbf06b6c204d30efe6228a82968fa08aa58dc9e8233e`
- `tmp/wifi/v204-twrp-baseline/compare/v203-v204-matrix.json`: `5cfd69c491171962d2ac80b168d8a5fa80b33319837cfe31d1aeb271e45a68a8`

## Live Result

### TWRP

- Mode: `twrp`
- Result: PASS
- Decision: `driver-candidate-found`
- Reason: Android/TWRP exposes Wi-Fi driver/firmware/HAL/init/log candidates but
  native gate remains missing
- v203 baseline: `no-go`
- v203 missing gates:
  - `native-wlan-interface`
  - `wifi-rfkill`
  - `wlan-cnss-qca-module-evidence`

Classification counts:

- `interface_evidence`: 0
- `rfkill_evidence`: 0
- `module_evidence`: 0
- `firmware_evidence`: 1
- `hal_evidence`: 0
- `init_service_evidence`: 0
- `kernel_log_evidence`: 19

### Android + Magisk root

Android boot transition:

- boot image flashed: `backups/baseline_a_20260423_030309/boot.img`
- local/remote boot image SHA256:
  `c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b`
- TWRP `adb reboot` and `reboot system` paths returned to recovery on this
  device; kernel `sysrq` reboot was used after the boot partition write.
- Android ADB detected:
  `product:r3qks model:SM_A908N device:r3q`
- Android build:
  `samsung/r3qks/r3q:12/SP1A.210812.016/A908NKSU5EWA3:user/release-keys`
- root check:
  `uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0`
- post-collection restore: `stage3/boot_linux_v159.img`
- native restore SHA256:
  `7e7e81a6af774b3b523c993851d64b86484be4c471dbee02edf062b3903c536f`
- native restore check:
  `A90 Linux init 0.9.59 (v159)` via `cmdv1 version`

Collector run:

```bash
python3 scripts/revalidation/android_twrp_wifi_baseline.py \
  --android-adb \
  --v203-manifest tmp/wifi/v203-baseline/manifest.json \
  --out-dir tmp/wifi/v204-android-baseline
```

Result: PASS.

Decision: `ready-for-readonly-nl80211-probe-plan`.

Reason: Android exposes WLAN interface/rfkill/module-adjacent evidence that is
sufficient to plan the next read-only `nl80211`/ICNSS probe.

Evidence:

- `tmp/wifi/v204-android-baseline/summary.md`
- `tmp/wifi/v204-android-baseline/manifest.json`
- `tmp/wifi/v204-android-baseline/compare/v203-v204-matrix.json`
- `tmp/wifi/v204-android-baseline/root-dmesg-wifi-tail.txt`
- `tmp/wifi/v204-android-baseline/root-icnss-sysfs-files.txt`

Hashes:

- `tmp/wifi/v204-android-baseline/manifest.json`: `bb2801dfd2ed1201639040ba255dde7ac6afd8d4b48ea1c98f9ad930aab9269b`
- `tmp/wifi/v204-android-baseline/summary.md`: `6a40ed9ab954542b2649de3480bb559cf9afa761b20c58d6c2d3bfc24eac9c5d`
- `tmp/wifi/v204-android-baseline/compare/v203-v204-matrix.json`: `4bed6a0488aded2b17f0c4a2ab3cc7c0a067d46f4924cab0fd9800360fd1ffb3`
- `tmp/wifi/v204-android-baseline/root-dmesg-wifi-tail.txt`: `ad6a3bae6d72319c4dcfe8db14d0741ba1c0fff340176fcd4506f7cf637ce518`
- `tmp/wifi/v204-android-baseline/root-icnss-sysfs-files.txt`: `129b1a555cb10d2022a58321d1005e2c22431a1c2293423a9ab46f17a8ccdb5f`

Classification counts:

- `interface_evidence`: 10
- `rfkill_evidence`: 1
- `module_evidence`: 0
- `firmware_evidence`: 12
- `hal_evidence`: 80
- `init_service_evidence`: 48
- `kernel_log_evidence`: 0

## Important Evidence

TWRP did not expose a WLAN interface, Wi-Fi rfkill node, or loaded wireless
module in this read-only run.

TWRP did expose kernel log hints for the Qualcomm WLAN platform path, including:

```text
OF: reserved mem: initialized node pil_wlan_fw_region
iommu: Adding device soc:ipa_smmu_wlan to group 4
icnss: Recursive recovery allowed for WLAN
iommu: Adding device 18800000.qcom,icnss to group 9
icnss: sec_create_wifi_sysfs done
icnss: Platform driver probed successfully
```

TWRP also exposed the firmware search path in the kernel command line:

```text
firmware_class.path=/vendor/firmware_mnt/image
```

The only rfkill node observed was Bluetooth-only:

```text
node=/sys/class/rfkill/rfkill0
name=bt_power
type=bluetooth
```

Therefore this is not enough for active Wi-Fi bring-up. It is enough to justify a
separate read-only investigation focused on ICNSS/WCNSS/QCA firmware and sysfs
state.

Android did expose the expected WLAN devices:

```text
wlan0
swlan0
p2p0
wifi-aware0
```

The Android sysfs paths map these devices to the Qualcomm ICNSS platform node:

```text
/sys/devices/platform/soc/18800000.qcom,icnss/net/wlan0
/sys/devices/platform/soc/18800000.qcom,icnss/net/swlan0
/sys/devices/platform/soc/18800000.qcom,icnss/net/p2p0
/sys/devices/platform/soc/18800000.qcom,icnss/net/wifi-aware0
```

Root-readable Android dmesg showed firmware and driver readiness evidence:

```text
icnss_qmi: QMI Server Connected
cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin
cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin
icnss: WLAN FW is ready
wlan: Firmware build version
HostSW: 5.2.022.3Q-HL210630A, FW: 3.2.0.3.910.8, HW: WCN39xx
```

## Guardrails

- No Wi-Fi enablement.
- No rfkill write.
- No WLAN link-up.
- No module load/unload.
- No firmware mutation.
- No supplicant/hostapd/vendor daemon start.
- No `/data/misc/wifi` default collection.
- Evidence output uses private/no-follow helper paths.
- Boot serial fields are redacted from output.

## Acceptance

- TWRP evidence was captured into a private bundle.
- Android/Magisk evidence was captured into a private bundle.
- Android ADB and Magisk root were confirmed.
- Native v159 boot was restored and verified after Android collection.
- v203 native missing gates were compared against TWRP evidence.
- Bluetooth-only rfkill was not counted as Wi-Fi rfkill.
- The result does not approve active Wi-Fi bring-up.
- The result narrows the next step to read-only ICNSS/WCNSS/QCA sysfs,
  firmware, and `nl80211` capability mapping.

## Next

Recommended v205 scope: ICNSS/WCNSS/QCA + `nl80211` read-only probe plan. It
should inspect available sysfs/debugfs/proc nodes, firmware file visibility, and
`nl80211` read-only capabilities without toggling rfkill, bringing interfaces
up, loading modules, starting Android Wi-Fi services, or using `iw` to mutate
state.
