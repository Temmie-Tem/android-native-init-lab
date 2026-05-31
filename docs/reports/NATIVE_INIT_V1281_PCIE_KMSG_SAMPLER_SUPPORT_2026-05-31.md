# Native Init V1281 PCIe/GDSC/kmsg Sampler Support

- generated: 2026-05-31
- cycle: V1281
- command: source/build-only
- decision: `v1281-pcie-kmsg-sampler-build-pass`
- pass: true
- helper: `a90_android_execns_probe v268`
- stage3 binary: `stage3/linux_init/helpers/a90_android_execns_probe_v268`
- sha256: `e86db44aad14e54572d88d77c1ea2019ea28b1f91c01f7a9af9e6eabc690a3ba`
- size: `1319408`

## Scope

V1281 adds read-only `/dev/kmsg` marker counting to the existing bounded
PM-service response sampler. The next live gate can now observe PCIe/GDSC/MHI
and SDX50M/eSoC/WLFW-related kernel messages in the same response window as the
existing GPIO142, PCIe sysfs, MHI, and `wlan0` checks.

## Changes

- Bumped `stage3/linux_init/helpers/a90_android_execns_probe.c` to
  `a90_android_execns_probe v268`.
- Added `collect_response_kmsg_markers()` and filtered marker counts for:
  - PCIe / LTSSM / `msm_pcie`
  - GDSC
  - MHI
  - eSoC / ext-mdm
  - MDM / modem / SDX50M
  - ICNSS / WLFW
  - subsystem restart markers
- Extended `scripts/revalidation/native_wifi_late_per_proxy_response_sampler_live_v1242.py`
  to parse and summarize the new kmsg fields.
- Added `scripts/revalidation/native_wifi_response_sampler_pcie_support_v1281.py`
  as the source/build-only gate.

## Validation

| check | result |
| --- | --- |
| V1280 input manifest | pass |
| Python compile | pass |
| helper build | pass |
| static aarch64 | pass |
| no interpreter | pass |
| no dynamic section | pass |
| required binary strings | pass |
| device commands | not executed |
| Wi-Fi bring-up | not executed |

Evidence:

- `tmp/wifi/v1281-execns-helper-v268-build/manifest.json`
- `tmp/wifi/v1281-execns-helper-v268-build/summary.md`

## Safety

No device command, deploy, PM actor, GPIO line request, PMIC write, direct eSoC
ioctl, Wi-Fi HAL start, scan/connect, credential use, DHCP/route change,
external ping, flash, boot image write, or partition write was executed by
V1281.

## Next

V1282 should deploy helper v268 only. V1283 should run the bounded PCIe/GDSC/kmsg
sampler live and classify whether the kernel logs any PCIe RC1, GDSC, MHI,
ext-mdm, or WLFW response during the PM-service `/dev/subsys_esoc0` window.
