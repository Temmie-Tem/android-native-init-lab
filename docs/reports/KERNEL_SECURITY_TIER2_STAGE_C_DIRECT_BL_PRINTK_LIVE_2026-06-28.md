# Kernel Security Tier-2 Stage C Direct-BL Printk Live Result

- Cycle: `TIER2_STAGE_C`
- Decision: `tier2-stage-c-direct-bl-printk-live-pass`
- Base / rollback boot: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Base / rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Passing candidate boot: `workspace/private/inputs/boot_images/boot_linux_tier2_stage_c_direct_bl_printk.img`
- Passing candidate SHA256: `21c567f0d3ebaa9d6caaa7c6310463fe7aa1710e5ca6a077305c36e489f16b8a`

## Result

PASS. A newly injected direct `bl` from patched kernel `.text` into the plain
`printk(fmt, ...)` variadic wrapper executed under RKP_CFP.

Live marker evidence:

```text
[   68.455135] [3:           init:    1] A90TIER2C
```

The marker appeared after reading the reachable benign sysfs node:

```text
cat /sys/class/kgsl/kgsl-3d0/num_pwrlevels
```

The sysfs read returned successfully (`rc=0`, duration `1ms`). It printed five NUL
bytes because the injected show stub returns `5` intentionally and does not format
the sysfs output buffer; the observable proof is the kernel log marker.

## Candidate Details

- Patched target function: `kgsl_pwrctrl_num_pwrlevels_show`
- Patched entry: `0xffffff80089262dc` at kernel offset `0x8a62f0`
- Marker address: `0xffffff8008926300`
- Direct `bl` target: `0xffffff800813d8cc` at kernel offset `0xbd8e0`
- Target locator: plain `printk(fmt, ...)` variadic-wrapper signature with `x1..x7`
  and `q0..q7` vararg spills, va_list setup, direct call to helper
  `0xffffff800813d77c`, and emit core `0xffffff800813bd4c`
- Diff contract: kernel `.text` patch body plus boot header id only; changed byte
  count `111`

## Live Sequence

1. Confirmed rollback/fallback artifacts before flashing:
   - v2321 rollback SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
   - v2237 fallback SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
   - v48 fallback SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
   - TWRP recovery image SHA256 `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
2. Flashed the passing candidate with `native_init_flash.py --from-native`.
3. Flash helper verified local SHA, recovery push SHA, boot-block readback SHA, and
   post-flash `version/status`.
4. Confirmed post-flash `selftest: pass=11 warn=1 fail=0`.
5. Set `panic_on_oops=0` and verified the value read back as `0`.
6. Read `/sys/class/kgsl/kgsl-3d0/num_pwrlevels`.
7. Grepped dmesg for `A90TIER2C`; marker was present.
8. Restored `panic_on_oops=1` and verified the value read back as `1`.
9. Confirmed post-trigger `selftest: pass=11 warn=1 fail=0`.
10. Rolled back to clean v2321 with `native_init_flash.py --from-native`.
11. Rollback helper verified local SHA, recovery push SHA, boot-block readback SHA,
    and post-rollback `version/status`.
12. Confirmed final rollback health: `version=0.9.285`, `selftest: pass=11 warn=1 fail=0`.

## First Attempt Note

The first source-build candidate, SHA256
`eec5651cd49a28f2f074aba02a4189386d1c824cc6ceb4cab7359b15d8307fd3`, booted and passed
selftest but selected the `printk_emit(..., fmt, ...)` variadic wrapper at
`0xffffff800813c814` instead of plain `printk(fmt, ...)`. The injected stub only
provided `x0=marker`, so that target interpreted the call frame incorrectly. The
sysfs read lost serial until reboot and produced no marker or pstore entry. The device
recovered to native init, selftest stayed `fail=0`, and it was rolled back to clean
v2321 before the corrected candidate was built.

## Safety

- RECON only.
- No UAF, grooming, EL1 exploit attempt, `ret` patch, `blr` patch, CFP-site patch,
  forbidden partition write, PMIC/GPIO/power write, or raw flash path.
- `x17` is preserved by the injected ROPP prologue/epilogue.
- All boot writes used only `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Final device state was restored to clean v2321 and `selftest fail=0`.
