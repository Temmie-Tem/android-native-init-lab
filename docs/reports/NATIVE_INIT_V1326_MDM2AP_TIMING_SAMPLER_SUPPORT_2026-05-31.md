# Native Init V1326 MDM2AP Timing Sampler Support

## Summary

- Cycle: `V1326`
- Type: source/build-only helper support gate
- Decision: `v1326-mdm2ap-timing-sampler-build-pass`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1326-mdm2ap-timing-sampler-support/manifest.json`
  - `tmp/wifi/v1326-mdm2ap-timing-sampler-support/summary.md`
- Script: `scripts/revalidation/native_wifi_mdm2ap_timing_sampler_support_v1326.py`
- Helper: `stage3/linux_init/helpers/a90_android_execns_probe_v276`
- Helper SHA256: `dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f`

V1326 implements the V1325 plan as a source/build-only helper update. The
helper marker is now `a90_android_execns_probe v276` and the new opt-in flag is
`--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`.

## Added Helper Surface

- Response mode: `late-per-proxy-mdm2ap-errfatal-pcie-timing`
- Intended live cadence: `120` samples at `50ms` after late `per_proxy` start
- Output contract: compact aggregate `mdm2ap_timing.*` keys
- Primary fields:
  - `gpio142_irq_initial`, `gpio142_irq_max`, `gpio142_irq_delta`
  - `errfatal_irq_initial`, `errfatal_irq_max`, `errfatal_irq_delta`
  - `pcie_rc1_transition_seen`, `pcie_rc1_first_transition_sample`
  - `mhi_bus_max`, `mhi_pipe_seen`, `ks_process_max`
  - `wlfw_kmsg_max`, `wlan0_seen`
- Safety fields remain explicit:
  - `safety_wifi_hal_start=0`
  - `safety_scan_connect=0`
  - `safety_credentials=0`
  - `safety_dhcp_route=0`
  - `safety_external_ping=0`
  - `safety_pmic_write=0`
  - `safety_gpio_request=0`
  - `safety_direct_esoc_ioctl=0`

## Validation

- Source string checks passed for the helper marker, new flag, timing sampler
  structure, GPIO142/errfatal delta fields, PCIe transition field, MHI/WLFW
  fields, and safety zeros.
- Static aarch64 build passed.
- `readelf` confirmed no interpreter and no dynamic section.
- Binary string checks passed for the helper marker, new flag, response mode,
  timing fields, and safety zeros.

## Decision

V1326 is ready for the next gated step. V1327 should deploy helper `v276` only.
V1328 should run the bounded MDM2AP timing sampler live and classify whether the
late `per_proxy` / `pm-service` path produces any GPIO142, MDM errfatal, PCIe
RC1, MHI/ks, WLFW, or `wlan0` transition inside the compact timing window.

## Safety

Source/build-only. No device command, helper deploy, PM actor start, Wi-Fi HAL
start, scan/connect, credential use, DHCP/routes, external ping, PMIC write,
GPIO request/hold, direct eSoC ioctl, flash, boot image write, or partition
write occurred.
