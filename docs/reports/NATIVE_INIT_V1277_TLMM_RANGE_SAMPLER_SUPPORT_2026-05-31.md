# Native Init V1277 TLMM Range Sampler Support

- generated: 2026-05-31
- cycle: V1277
- command: source/build-only
- decision: `v1277-tlmm-range-sampler-build-pass`
- pass: true
- helper: `a90_android_execns_probe v267`
- stage3 binary: `stage3/linux_init/helpers/a90_android_execns_probe_v267`
- sha256: `eccd9ca475927c2a37551304fedcc6740d19aeb048ebd137f966a18c269f0337`
- size: `1319408`

## Scope

V1277 extends the existing PM-service response sampler with read-only TLMM
debugfs GPIO range capture. The purpose is to distinguish "GPIO135/GPIO142 line
name absent" from "TLMM gpiochip/range absent" during the bounded
`/dev/subsys_esoc0` response window.

## Changes

- Bumped `stage3/linux_init/helpers/a90_android_execns_probe.c` to
  `a90_android_execns_probe v267`.
- Added bounded `/sys/kernel/debug/gpio` range-header parsing for the gpiochip
  range that contains TLMM GPIO135 and GPIO142.
- Added sampler output fields for:
  - `tlmm_gpio135_debugfs_range_block_seen`
  - `tlmm_gpio135_debugfs_range_start`
  - `tlmm_gpio135_debugfs_range_end`
  - `tlmm_gpio135_debugfs_range_block`
  - `tlmm_gpio142_debugfs_range_block_seen`
  - `tlmm_gpio142_debugfs_range_start`
  - `tlmm_gpio142_debugfs_range_end`
  - `tlmm_gpio142_debugfs_range_block`
- Extended the V1242 parser to preserve and summarize the new v267 fields.
- Added `scripts/revalidation/native_wifi_response_sampler_tlmm_support_v1277.py`
  as the source/build-only gate.

## Validation

| check | result |
| --- | --- |
| V1276 input manifest | pass |
| Python compile | pass |
| helper build | pass |
| static aarch64 | pass |
| no interpreter | pass |
| no dynamic section | pass |
| required binary strings | pass |
| device commands | not executed |
| Wi-Fi bring-up | not executed |

Build evidence:

- `tmp/wifi/v1277-execns-helper-v267-build/manifest.json`
- `tmp/wifi/v1277-execns-helper-v267-build/summary.md`

## Safety

No device command, deploy, live PM actor, GPIO line request, PMIC write, direct
eSoC ioctl, Wi-Fi HAL start, scan/connect, credential use, DHCP/route change,
external ping, flash, boot image write, or partition write was executed by
V1277.

## Next

V1278 should deploy helper v267 only. V1279 should run the same bounded
PM-service response sampler live gate and check whether TLMM GPIO135/GPIO142
range blocks are visible while GPIO142 IRQ, PCIe RC1, MHI pipe, and `wlan0`
remain observed read-only.
