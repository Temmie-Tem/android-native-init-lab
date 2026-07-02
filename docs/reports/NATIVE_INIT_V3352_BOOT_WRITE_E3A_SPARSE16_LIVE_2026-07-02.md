# Native Init V3352 §0.2 Write-Probe E3a Sparse16 Live

- Cycle: `V3352`
- Decision: `v3352-boot-write-e3a-sparse16-live-pass`
- Candidate: `A90 Linux init 0.11.116 (v3352-boot-write-e3a-sparse16)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3352_boot_write_e3a_sparse16.img`
- Candidate SHA256: `7eea6580236dff3fcd38e5e19689873da2e140d001edf6f5f53fca9d0b579cd8`
- Rollback: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private run log: `workspace/private/runs/self-dd-v3352-e3a-live-20260702T001020Z/`

## Preflight

- Source build prep was committed as `d4f6ad07`.
- Rollback artifacts were present. `v2321` and `v2237` matched their pinned SHA256 values; `v48` was present.
- Serial bridge was healthy on the managed wrapper. Current resident before flash was `v2321-usb-clean-identity-rodata`.
- Pre-flash resident health: `version 0.9.285`, `status` BOOT OK, `selftest fail=0`.

## Candidate Flash

- Flashed only through `workspace/public/src/scripts/revalidation/native_init_flash.py --from-native`.
- Local candidate image passed Android boot magic, expected marker `0.11.116`, and expected SHA256.
- Recovery/TWRP path came up, ADB recovery was available, remote image SHA matched, boot dd write completed, and boot-prefix readback SHA matched.
- Candidate booted to native init and serial verify passed: `version 0.11.116`, `status` rc=0.
- Post-flash explicit selftest passed: `pass=12 warn=1 fail=0`.

## E3a Probe Result

Command:

```text
boot-write-e3a BOOT-WRITE-PROBE-E3A-SPARSE-TAILSLACK
```

Observed E3a output:

```text
A90BWE3A begin
A90BWE3A rung=E3A mode=read-then-write-identical scope=tail-slack-16x4096-zero-population-sparse
A90BWE3A boot_header=ok version=1 page_size=4096 used_len=62644224
A90BWE3A slack_start=62644224 slack_end=66060288 footer_guard=1048576
A90BWE3A zero_candidates=26 zero_stored=26 target_count=16
A90BWE3A selected0_index=0 selected0_off=63631360
A90BWE3A selected1_index=1 selected1_off=63635456
A90BWE3A selected2_index=3 selected2_off=63643648
A90BWE3A selected3_index=5 selected3_off=63705088
A90BWE3A selected4_index=6 selected4_off=63709184
A90BWE3A selected5_index=8 selected5_off=63717376
A90BWE3A selected6_index=10 selected6_off=63725568
A90BWE3A selected7_index=11 selected7_off=63729664
A90BWE3A selected8_index=13 selected8_off=63737856
A90BWE3A selected9_index=15 selected9_off=63746048
A90BWE3A selected10_index=16 selected10_off=63750144
A90BWE3A selected11_index=18 selected11_off=63758336
A90BWE3A selected12_index=20 selected12_off=66027520
A90BWE3A selected13_index=21 selected13_off=66031616
A90BWE3A selected14_index=23 selected14_off=66039808
A90BWE3A selected15_index=25 selected15_off=66048000
A90BWE3A pwrite_count=16 pwrite=ok fsync=ok
A90BWE3A region_match_all=1
A90BWE3A full_sha_before=ae9cbe455c575c7f8d86b3567103cc77482d0d63dc5faf759f818b8c75eace0c
A90BWE3A full_sha_after=ae9cbe455c575c7f8d86b3567103cc77482d0d63dc5faf759f818b8c75eace0c
A90BWE3A full_match=1
A90BWE3A result=ok pwrite-permitted-identity-verified
A90BWE3A end rc=0
```

Interpretation:

- E3a passed: normal-boot PID1 performed sixteen identity `pwrite` calls into confirmed-zero boot tail-slack sectors.
- All sixteen O_DIRECT region readbacks matched and the O_DIRECT full-partition SHA before/after matched.
- This scales the proven E2 path from 4 sectors to 16 sectors while staying within confirmed-zero slack.
- The original contiguous 1MiB E3 remains a separate higher-risk question because this run again observed only 26 zero sectors in the scanned slack population.

Post-probe health:

- `status`: BOOT OK, `selftest fail=0`.
- `selftest`: `pass=12 warn=1 fail=0`.
- `pstore summary`: `entries=0`.

## Rollback

- Rolled back through `native_init_flash.py --from-native` to `v2321`.
- Rollback local image marker/SHA passed, recovery/TWRP path came up, remote SHA matched, boot dd write completed, and boot-prefix readback SHA matched.
- Rollback helper verify passed: `version 0.9.285`, `status` rc=0.
- Final explicit selftest passed: `pass=11 warn=1 fail=0`.
- Final pstore summary passed: `entries=0`.

## Timeline

The private run timeline uses the standard single-events schema:

```json
{
  "events": [
    {"name": "candidate_flash_start", "timestamp_utc": "2026-07-02T00:10:20.233729Z"},
    {"name": "candidate_flash_done", "timestamp_utc": "2026-07-02T00:11:29.974453Z"},
    {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-02T00:11:37.333400Z"},
    {"name": "live_session_start", "timestamp_utc": "2026-07-02T00:11:50.505379Z"},
    {"name": "live_session_end", "timestamp_utc": "2026-07-02T00:11:54.534975Z"},
    {"name": "rollback_flash_start", "timestamp_utc": "2026-07-02T00:12:09.953762Z"},
    {"name": "rollback_flash_done", "timestamp_utc": "2026-07-02T00:13:15.361290Z"},
    {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-02T00:13:22.417842Z"}
  ]
}
```

## Notes

- `boot-write-e3a` initially returned `BUSY_DANGEROUS` while the auto-menu was up; `a90ctl --hide-on-busy` sent `hide` and retried once, then the token command ran.
- Final pstore's first retry path hit serial echo corruption after a busy/hide exchange; the host-side wait was stopped and pstore was retried as a fresh normal command. The successful pstore result is the recorded gate.
