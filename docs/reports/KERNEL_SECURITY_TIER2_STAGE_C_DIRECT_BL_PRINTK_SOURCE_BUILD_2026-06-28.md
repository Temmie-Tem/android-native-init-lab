# Kernel Security Tier-2 Stage C Direct-BL Printk Source Build

- Cycle: `TIER2_STAGE_C`
- Decision: `tier2-stage-c-direct-bl-printk-source-build-pass`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Base SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Candidate boot: `workspace/private/inputs/boot_images/boot_linux_tier2_stage_c_direct_bl_printk.img`
- Candidate SHA256: `21c567f0d3ebaa9d6caaa7c6310463fe7aa1710e5ca6a077305c36e489f16b8a`

## What Changed

- Direct-patched clean V2321 kernel `.text` only; no ramdisk/native-init changes.
- Replaced the reachable `kgsl_pwrctrl_num_pwrlevels_show` body with a ROPP-correct stub.
- The stub preserves `x17`, loads an in-function `A90TIER2C` marker, executes one new direct `bl` to the printk variadic-wrapper signature target, restores the ROPP return address, returns `5`, and leaves the following RKP magic word intact.
- Recomputed only the Android boot header v1 `id` after the kernel patch.

## Signature Evidence

- KGSL entry: `0xffffff80089262dc` at kernel offset `0x8a62f0`.
- KGSL patch room: `108` bytes; payload length `108` bytes.
- Marker: `A90TIER2C\n\0` at `0xffffff8008926300`.
- Printk target: `0xffffff800813d8cc` at kernel offset `0xbd8e0`.
- Printk target was located by the plain `printk(fmt, ...)` variadic-wrapper signature: RKP marker, stack frame, `x1..x7` and `q0..q7` vararg spills, va_list setup, and a direct call into the printk va_list helper at `0xffffff800813d77c` / emit core at `0xffffff800813bd4c`.

## Diff Contract

- Changed byte count: `111`.
- Changed ranges: `[['0x240', '0x254'], ['0x8a72fc', '0x8a7317'], ['0x8a7318', '0x8a7358']]`.
- Allowed ranges are the injected KGSL function body and the 32-byte boot header `id`; the builder fails if any other byte changes.

## Live Gate

- Not run by this source-build step.
- Required next: flash only via `native_init_flash.py`, confirm boot/selftest, set `panic_on_oops=0`, read `/sys/class/kgsl/kgsl-3d0/num_pwrlevels`, grep dmesg for `A90TIER2C`, restore `panic_on_oops=1`, roll back to clean V2321, and confirm `selftest fail=0`.

## Safety

- RECON only: no UAF, grooming, EL1 exploit attempt, forbidden partition write, raw flash path, power write, or `blr`/indirect-branch patch.
