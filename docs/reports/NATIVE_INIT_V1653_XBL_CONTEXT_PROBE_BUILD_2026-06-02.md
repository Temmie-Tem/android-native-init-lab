# Native Init V1653 XBL Context Probe Build

## Summary

- Cycle: `V1653`
- Type: source/build-only XBL context probe helper
- Decision: `v1653-xbl-context-probe-build-pass`
- Result: PASS
- Source: `stage3/linux_init/helpers/a90_xbl_context_probe.c`
- Artifact: `tmp/wifi/v1653-xbl-context-probe-build/a90_xbl_context_probe_v1653`
- Artifact SHA256: `e7a143550d99e89aa5dfd3f25daa5c05118e4530cdafe4d1f615cc98daf32f53`
- Artifact size: `663456`
- Reason: build a static helper that reads only bounded XBL ranges and emits tracked-safe redacted records.

## Checks

- `source_exists`: `True`
- `source_contract_strings_present`: `True`
- `compile_ok`: `True`
- `strip_ok`: `True`
- `file_static`: `True`
- `static_no_interp`: `True`
- `static_no_dynamic`: `True`
- `binary_contract_strings_present`: `True`
- `artifact_private_tmp`: `True`
- `no_device_command`: `True`
- `no_live_write_gate`: `True`

## Contract

- Input: `--path PATH --artifact LABEL --range START:END`.
- Output: version, mode, range summaries, and `record` lines containing only artifact/range/offset/length/truncated/string_sha256/tokens/class.
- No raw string text is emitted in tracked output.
- Artifact is built under ignored private `tmp/` evidence, not committed as a binary.

## Next

V1654 may deploy/run this helper against temporary XBL devnodes and only the V1652 ranges. Tracked reports must include only redacted records. No partition write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
