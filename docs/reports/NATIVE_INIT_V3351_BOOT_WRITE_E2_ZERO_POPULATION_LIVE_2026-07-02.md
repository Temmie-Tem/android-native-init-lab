# Native Init V3351 §0.2 Write-Probe E2 Zero-Population Live

- Cycle: `V3351`
- Decision: `v3351-boot-write-e2-zero-population-live-pass`
- Candidate: `A90 Linux init 0.11.115 (v3351-boot-write-e2-zero-population)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3351_boot_write_e2_zero_population.img`
- Candidate SHA256: `84b035b494460c2d8976d0c09a1effb3a8f023858f3fa4b1e02120707ae7f89d`
- Rollback: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private run log: `workspace/private/runs/self-dd-v3351-e2-live-20260701T234432Z/`

## Preflight

- Source build prep was committed as `161bad93`.
- Rollback artifacts were present. `v2321` and `v2237` matched their pinned SHA256 values; `v48` was present.
- Recent GOAL gate records and this run confirmed the recovery/TWRP path.
- Serial bridge was healthy on the managed wrapper. Current resident before flash was `v2321-usb-clean-identity-rodata`.
- Pre-flash resident health: `version 0.9.285`, `status` BOOT OK, `selftest fail=0`.

## Candidate Flash

- Flashed only through `workspace/public/src/scripts/revalidation/native_init_flash.py --from-native`.
- Local candidate image passed Android boot magic, expected marker `0.11.115`, and expected SHA256.
- Recovery/TWRP path came up, ADB recovery was available, remote image SHA matched, boot dd write completed, and boot-prefix readback SHA matched.
- Candidate booted to native init and serial verify passed: `version 0.11.115`, `status` rc=0.
- Post-flash explicit selftest: `pass=12 warn=1 fail=0`.

## E2 Probe Result

Command:

```text
boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK
```

Observed E2 output:

```text
A90BWE2 begin
A90BWE2 rung=E2 mode=read-then-write-identical scope=tail-slack-4x4096-zero-population
A90BWE2 boot_header=ok version=1 page_size=4096 used_len=62644224
A90BWE2 slack_start=62644224 slack_end=66060288 footer_guard=1048576
A90BWE2 zero_candidates=26 zero_stored=26 target_count=4
A90BWE2 selected0_index=0 selected0_off=63631360
A90BWE2 selected1_index=8 selected1_off=63717376
A90BWE2 selected2_index=16 selected2_off=63750144
A90BWE2 selected3_index=25 selected3_off=66048000
A90BWE2 slack_scanned=834 have_zero_sector=1 target_count=4
A90BWE2 target0_off=63631360 len=4096 slack_zero=1
A90BWE2 target1_off=63717376 len=4096 slack_zero=1
A90BWE2 target2_off=63750144 len=4096 slack_zero=1
A90BWE2 target3_off=66048000 len=4096 slack_zero=1
A90BWE2 full_sha_before=f9295d311c9b07fc22ab8d0c8a04f76607cabdc21d297f86a422a23ade616d45
A90BWE2 pwrite0_rc=4096
A90BWE2 pwrite1_rc=4096
A90BWE2 pwrite2_rc=4096
A90BWE2 pwrite3_rc=4096
A90BWE2 pwrite_count=4 pwrite=ok fsync=ok
A90BWE2 readback0_rc=4096 region0_match=1
A90BWE2 readback1_rc=4096 region1_match=1
A90BWE2 readback2_rc=4096 region2_match=1
A90BWE2 readback3_rc=4096 region3_match=1
A90BWE2 region_match_all=1
A90BWE2 full_sha_after=f9295d311c9b07fc22ab8d0c8a04f76607cabdc21d297f86a422a23ade616d45
A90BWE2 full_match=1
A90BWE2 result=ok pwrite-permitted-identity-verified
A90BWE2 end rc=0
```

Interpretation:

- E2 passed: normal-boot PID1 performed four identity `pwrite` calls into confirmed-zero boot tail-slack sectors.
- All four O_DIRECT region readbacks matched and the O_DIRECT full-partition SHA before/after matched.
- This confirms multi-offset identity writes are permitted by the current runtime envelope.
- E3 can now target a larger identity write, still gated by confirmed-zero slack and full-partition before/after SHA.

Post-probe health:

- `status`: BOOT OK, `selftest fail=0`.
- `selftest`: `pass=12 warn=1 fail=0`.
- `pstore summary`: `entries=0`.

## Rollback

- Rolled back through `native_init_flash.py --from-native` to `v2321`.
- Rollback local image marker/SHA passed, recovery/TWRP path came up, remote SHA matched, boot dd write completed, and boot-prefix readback SHA matched.
- Rollback helper verify passed: `version 0.9.285`, `status` rc=0.
- Final explicit selftest passed: `pass=11 warn=1 fail=0`.

## Timeline

The private run timeline uses the standard single-events schema:

```json
{
  "events": [
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-01T23:44:32.863376Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-01T23:45:40.355118Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-01T23:45:46.855804Z"},
    {"name": "live_session_start", "timestamp_utc": "2026-07-01T23:45:56.223973Z"},
    {"name": "live_session_input_corrupt", "timestamp_utc": "2026-07-01T23:49:08.915548Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-01T23:49:08.915576Z"},
    {"name": "e2_retry_start", "timestamp_utc": "2026-07-01T23:50:24.031239Z"},
    {"name": "e2_retry_end", "timestamp_utc": "2026-07-01T23:50:28.068217Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-01T23:50:44.392619Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-01T23:51:48.755532Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-01T23:52:01.125744Z"}
  ]
}
```

## Notes

- First E2 attempt used `--input-mode slow` and the serial line dropped characters, yielding `[err] unknown command: te-e2`; no `A90BWE2 begin` occurred and no write path was entered. The live proof was rerun with `--input-mode normal`.
- A harmless `--input-mode double` check showed duplicate characters are not collapsed by the device shell, so double mode is not suitable on this bridge.
- A final explicit `version` retry after rollback lost the END marker to `ATAT` serial noise, but rollback helper `version/status` verification had already passed and the subsequent explicit `selftest` passed.
