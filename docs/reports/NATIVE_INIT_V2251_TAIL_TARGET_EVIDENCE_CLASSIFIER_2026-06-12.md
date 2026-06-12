# Native Init V2251 Tail Target Evidence Classifier

## Summary

- Cycle: `V2251`
- Type: host-only classifier over the existing V2250 live helper result and V2247 scorer output.
- Decision: `v2251-tail-target-evidence-generic-sampler-miss-confirmed`
- Result: PASS
- Private run: `workspace/private/runs/kernel/v2251-tail-target-evidence-classifier-20260612-125858`
- Input run: `workspace/private/runs/kernel/v2250-tail-perf-sampler-full-print-live-20260612-124426`

## Why This Unit Exists

V2250 proved the helper-started full-print perf regs/codeword sampler captured all occupied samples, but the generic CPU-clock scorer had `0/835` hits against the V2246 post-FWREADY firmware_class/qcacld-HDD whitelist. That zero-hit result needed one more discriminator before being interpreted: did the target path not execute, or did random CPU-clock sampling miss a narrow path that did execute?

V2251 answers that using deterministic helper-owned evidence already present in the same V2250 boot. No new device action was needed.

## Evidence

- Post-FWREADY `boot_wlan` trigger executed: `true`.
- QCACLD firmware_class feeder confirmed: `true`.
- Feeder request count: `3`.
- Feeder seen count: `1`.
- Feeder fed count: `1`.
- Fed firmware: `wlan/qca_cld/WCNSS_qcom_cfg.ini`.
- Fed bytes: `13343`.
- Data write rc: `0`.
- Loading completion rc: `0`.
- Target stack sample count: `1`.
- Full target stack sample count: `1`.
- Generic CPU-clock scorer hits: `0/835`.
- Per-boot symbolization slide usable: `true`, reason `lr_exact_single_pc_mismatch`.

## Target Stack

The helper's read-only `/proc/*/stack` sampler caught one target sample:

- `comm`: `kworker/u16:1`
- `wchan`: `_request_firmware`
- target symbol count: `7/7`
- symbols present: `_request_firmware`, `request_firmware`, `qdf_file_read`, `qdf_ini_parse`, `cfg_parse`, `hdd_context_create`, `wlan_hdd_pld_probe`

This exactly matches the V2246 source-backed whitelist.

## Interpretation

The V2246 firmware_class/qcacld-HDD tail did execute in the V2250 boot. Therefore the V2250 generic CPU-clock `0/835` target-hit result is a sampler miss, not evidence that the function path was absent.

The T1 next step should not be another generic CPU-clock duration or print-limit tweak. If finer timing is still needed, use a deterministic observable at the already-confirmed boundary: for example, helper-owned phase markers around `boot_wlan`, firmware_class feeder writes, and focused `/proc/*/stack` snapshots immediately before and after each firmware_class fallback operation.

## Track Decision

- Track stayed on T1 kernel observation.
- No downgrade to T2/T3 occurred.
- Trigger: V2250 made generic CPU-clock retries low-value, but V2251 found a host-only target-specific discriminator, so T1 remained meaningful and safely actionable.

## Safety

- Host-only analysis.
- No device I/O.
- No flash/reboot.
- No BPF attach.
- No tracefs control write.
- No `probe_write_user`.
- No Wi-Fi scan/connect/DHCP/ping.
- No network route change.
- No partition, firmware, eSoC/PCIe/GDSC/PMIC/GPIO action.
- Raw helper output stayed under `workspace/private/**`; this report contains only public-safe derived metadata.
