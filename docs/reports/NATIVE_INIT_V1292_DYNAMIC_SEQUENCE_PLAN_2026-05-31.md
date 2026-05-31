# V1292 Dynamic PCIe/GDSC/eSoC Sequence Plan

- date: 2026-05-31
- scope: host/source evidence classifier
- script: `scripts/revalidation/native_wifi_dynamic_sequence_plan_v1292.py`
- evidence: `tmp/wifi/v1292-dynamic-sequence-plan/manifest.json`
- result: `v1292-dense-dynamic-response-sampler-selected`
- pass: `true`

## Purpose

V1291 closed static TLMM GPIO135/GPIO142 and PMIC9 shape as the shortest
blocker. V1292 decides the next movement toward native Wi-Fi bring-up without
starting Wi-Fi HAL or changing PMIC/GPIO/eSoC state.

## Result

V1292 selects a dense no-write response sampler build as the next gate.

The existing V1290 sampler is structurally correct, but it samples the response
window at `1000 ms`. Android-positive evidence reaches PCIe RC1 at `8.820s`
after `subsys_esoc0_get` at `8.301226s`, a `519 ms` delta. That sub-second
window is narrower than the current native sampling cadence, so the next
lowest-risk step is denser observation before any mutation gate.

## Checks

| check | result |
|---|---|
| V1291 static shape closed | pass |
| V1290 dynamic gap still active | pass |
| Android sub-second PCIe reference present | pass |
| helper dense sampler reuse possible | pass |
| MHI/eSoC/PCIe source model present | pass |
| tracepoint fallback sources and tracefs feasibility present | pass |
| safety clean | pass |

## Source Model

| source point | finding |
|---|---|
| helper source | `stage3/linux_init/helpers/a90_android_execns_probe.c` |
| current helper version | `a90_android_execns_probe v270` |
| existing sample function | `append_pm_esoc_response_sample()` |
| current response interval | `late_per_proxy_poll_interval_ms = 1000` |
| current sample count | `late_per_proxy_poll_max = 12` |
| MHI eSoC hook | `mhi_arch_esoc_ops_power_on()` |
| PCIe resume path | `msm_pcie_pm_control(MSM_PCIE_RESUME, ...)` |
| MHI probe path | `mhi_pci_probe()` |
| eSoC hook registration | `esoc_register_client_hook()` |

## Next Gate

V1293 should be source/build-only:

- bump `a90_android_execns_probe` to helper `v271`
- add an opt-in dense late-`per_proxy` response sampler flag
- reuse existing `append_pm_esoc_response_sample()` without adding writes
- sample at `50 ms` cadence for `40` samples, covering the first `2s`
- emit dense mode metadata and summary keys
- keep PMIC writes, GPIO requests/holds, direct eSoC ioctls, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, flash, boot image
  writes, and partition writes blocked

## Safety

- host/source classifier only
- no device command or mutation executed by V1292
- no PMIC write
- no userspace GPIO line request or hold
- no direct eSoC ioctl
- no new daemon/HAL expansion
- no scan/connect, credentials, DHCP/routes, or external ping
- no flash, boot image write, or partition write

## Verification

```bash
python3 -m py_compile scripts/revalidation/native_wifi_dynamic_sequence_plan_v1292.py
python3 scripts/revalidation/native_wifi_dynamic_sequence_plan_v1292.py run
```
