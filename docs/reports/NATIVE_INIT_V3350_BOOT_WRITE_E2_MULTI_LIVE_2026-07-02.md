# Native Init V3350 §0.2 Write-Probe E2 Multi-Offset Live

- Cycle: `V3350`
- Decision: `v3350-boot-write-e2-multi-live-clean-refusal`
- Candidate: `A90 Linux init 0.11.114 (v3350-boot-write-e2-multi)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3350_boot_write_e2_multi.img`
- Candidate SHA256: `1238a1e4b701e5d9038aefa85dd0dac3968d0d5291af39b80db9540167c4427c`
- Rollback: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private run log: `workspace/private/runs/self-dd-v3350-e2-live-20260701T232956Z/`

## Preflight

- Worktree was clean at start; latest source commit was `58752ff6`.
- Rollback artifacts were present. `v2321` and `v2237` matched their pinned SHA256 values; `v48` was present.
- Serial bridge was healthy on the managed wrapper. Current resident was `v2321-usb-clean-identity-rodata`.
- Pre-flash resident health: `version 0.9.285`, `status` BOOT OK, `selftest fail=0`.

## Candidate Flash

- Flashed only through `workspace/public/src/scripts/revalidation/native_init_flash.py --from-native`.
- Local candidate image passed Android boot magic, expected marker `0.11.114`, and expected SHA256.
- Recovery/TWRP path came up, ADB recovery was available, remote image SHA matched, boot dd write completed, and boot-prefix readback SHA matched.
- Candidate booted to native init and serial verify passed: `version 0.11.114`, `status` rc=0.
- Post-flash selftest: `pass=12 warn=1 fail=0`.

## E2 Probe Result

Command:

```text
boot-write-e2 BOOT-WRITE-PROBE-E2-MULTI-TAILSLACK
```

Observed E2 output:

```text
A90BWE2 begin
A90BWE2 rung=E2 mode=read-then-write-identical scope=tail-slack-4x4096-spread
A90BWE2 target_node=/dev/block/sda24 resolve=sysfs-partname
A90BWE2 rdev=259:8
A90BWE2 boot_header=ok version=1 page_size=4096 used_len=62644224
A90BWE2 slack_start=62644224 slack_end=66060288 footer_guard=1048576
A90BWE2 scan0_start=62644224 scan0_end=63496192
A90BWE2 no_zero_in_band=0
A90BWE2 slack_scanned=208 have_zero_sector=0 target_count=4
A90BWE2 stop=no-zero-slack
A90BWE2 cleaned=1
A90BWE2 stop=no-zero-slack
A90BWE2 end rc=-28
```

Interpretation:

- E2 stopped before opening the write fd and before any `pwrite`.
- The first quarter-band of the tail-slack window had no all-zero 4096B sector.
- This is a clean refusal by the all-zero gate, not an E2 write proof.
- Do not advance to E3 on this result.

Post-probe health:

- `status`: BOOT OK, `selftest fail=0`.
- `selftest`: `pass=12 warn=1 fail=0`.
- `pstore summary`: `entries=0`.

## Rollback

- Rolled back through `native_init_flash.py --from-native` to `v2321`.
- Rollback local image marker/SHA passed, recovery/TWRP path came up, remote SHA matched, boot dd write completed, and boot-prefix readback SHA matched.
- Final resident verify passed: `version 0.9.285 build=v2321-usb-clean-identity-rodata`.
- Final selftest passed: `pass=11 warn=1 fail=0`.

## Notes

- One final health-check attempt was accidentally issued in parallel and hit the serial transaction lock / garbled input path; the check was repeated sequentially and passed. No device action was taken by the failed parallel check.
- Next E2 revision should keep the confirmed-zero gate but select multiple all-zero sectors from the available zero population across the tail slack, rather than requiring every fixed quarter-band to contain one.
