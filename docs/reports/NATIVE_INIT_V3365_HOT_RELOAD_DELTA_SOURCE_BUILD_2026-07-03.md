# Native Init V3365 Hot-Reload Delta Source Build

- Cycle: `V3365`
- Decision: `v3365-hot-reload-delta-source-build`
- Init: `A90 Linux init 0.11.126 (v3365-hot-reload-delta)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3365_hot_reload_delta.img`
- Boot SHA256: `e040ddb6fa02c2043844636a138e79235e42178fbf484162e519f7e7bcc5a13b`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- H2 delta candidate: preserve V3364's `reload INIT-RELOAD-EXECVE` command and `A90_RELOADED` fast path, but bump the init identity to `0.11.126` / `v3365-hot-reload-delta`.
- Live H2 will flash V3364 as the resident once, stage this V3365 init ELF under the approved SD staging root, then reload it to prove a genuinely changed native-init binary takes effect without rebooting or re-enumerating USB.
- This candidate does not add a new boot-write primitive and does not require flashing V3365 for the proof; only the V3365 init ELF is staged as reload input.
- Existing self-dd F0/F1/F2/F3 commands and the V3364 fast-path guards are preserved.

## Validation Contract

- Static PASS requires the V3365 version strings plus the reload markers (`A90RELOAD`, `INIT-RELOAD-EXECVE`, usage) and the fast-path marker to be present.
- Live H2 PASS, separately gated, requires: V3364 resident boot health clean; staged V3365 init SHA matches the caller-pinned SHA; `reload` returns through the new init shell; `version` reports `0.11.126` / `v3365-hot-reload-delta`; `selftest fail=0`; then rollback to v2321 and health-check clean.
- No live H2 reload result is claimed by this source-build report.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `hot-reload-delta`.
