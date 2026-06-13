# NATIVE_INIT_V2317_USB_KERNEL_IDENTITY_RODATA_FEASIBILITY_2026-06-14

## Scope

- Goal: determine whether the host-visible USB `iManufacturer` / `iProduct` values can be changed after V2316 proved configfs/userspace strings are ignored by Samsung's gadget path.
- Method: host-only source inspection plus private-copy kernel string dry-run patch.
- Device flash: no.
- Device mutation: none.
- Public artifact policy: no boot image, kernel blob, ramdisk, raw log, serial, MAC/BSSID/IP, or credential committed.

## Baseline Input

- Baseline image inspected: `workspace/private/inputs/boot_images/boot_linux_v2316_usb_linux_identity.img`
- Baseline image SHA256: `cf54ff0ae3cca4af31263140e588920296abecdb0ffb690a807b3d8b393f452a`
- Extracted kernel SHA256: `9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a`
- Extracted ramdisk SHA256: `51a3434e48f2d010c4b16c1bd90c6308a733b03f92473f3ab2a399ce18211b11`
- Private run directory: `workspace/private/runs/usb-identity/v2317-kernel-string-feasibility-20260614-021903`

## Source Finding

The kernel source confirms the host-visible manufacturer/product strings are forced by Samsung's composite gadget path:

- `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/configs/r3q_kor_single_defconfig`: `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE=y`
- `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel/drivers/usb/gadget/configfs.c`: on UDC bind, the Samsung path copies literal `"SAMSUNG"` into `manufacturer_string` and `"SAMSUNG_Android"` into `product_string`.
- The same file then presents `manufacturer_string` and `product_string` for descriptor indices `USB_GADGET_MANUFACTURER_IDX` and `USB_GADGET_PRODUCT_IDX`.
- Serial remains `gs->serialnumber`, which matches V2316 live evidence: host-side serial changed to the redacted placeholder, while manufacturer/product stayed Samsung-branded.

Conclusion: changing configfs strings or native-init userspace code cannot change host-visible `iManufacturer` / `iProduct` on this kernel. A kernel-side change is required.

## Binary Literal Inventory

Private extracted-kernel scan:

| Literal | Count | Offset(s) | Interpretation |
| --- | ---: | --- | --- |
| `SAMSUNG_Android\0` | 1 | `0x233c11e` | Clean product literal candidate. |
| `SAMSUNG\0` | 1 | `0x2346d6c` | Manufacturer literal candidate, but merged with another string suffix. |
| `A90NATIVE001` | 0 | n/a | Serial is not in the kernel blob. |
| `A90 NativeInit` | 0 | n/a | Userspace/configfs-only string. |
| `A90 Linux (ARM)` | 0 | n/a | Userspace/configfs-only string. |

Private extracted-ramdisk scan:

| Literal | Count | Interpretation |
| --- | ---: | --- |
| `A90NATIVE001` | 2 | Present in ramdisk/userspace. |
| `A90 NativeInit` | 2 | Present in ramdisk/userspace. |
| `A90 Linux (ARM)` | 2 | Present in ramdisk/userspace. |
| `SAMSUNG_Android\0` | 0 | Not a ramdisk source. |

## Dry-Run Patch Result

A private copy of the extracted kernel was patched in-place with fixed-length replacements:

| Offset | Old bytes | New visible string | Length constraint |
| --- | --- | --- | --- |
| `0x233c11e` | `SAMSUNG_Android\0` | `A90 Linux ARM` | Product must fit within 15 visible chars. |
| `0x2346d6c` | `SAMSUNG\0` | `A90-LNX` | Manufacturer must fit within 7 visible chars. |

Dry-run patched kernel SHA256:

`b8c9181a134d419a35935cd7ec601769bd45416c284f5b2de5c4a293210793e2`

Post-patch private scan:

| Literal | Count |
| --- | ---: |
| `SAMSUNG_Android\0` | 0 |
| `SAMSUNG\0` | 0 |
| `A90 Linux ARM\0` | 1 |
| `A90-LNX\0` | 1 |

## Risk Assessment

- Product patch is clean: the `SAMSUNG_Android` literal is unique in the extracted kernel.
- Manufacturer patch is feasible but less clean: the compiler appears to have merged the standalone `"SAMSUNG"` literal with the suffix of another rodata string (`Gamepad for SAMSUNG`). Patching `SAMSUNG\0` to `A90-LNX\0` also changes that unrelated descriptor suffix to `Gamepad for A90-LNX`.
- The patch is rodata-only and fixed-length; it does not move code, change section sizes, alter command line, or write any partition in this feasibility unit.
- A full source rebuild would be cleaner architecturally, but has a larger risk surface: toolchain drift, Samsung/RKP post-link differences, config drift, and a much larger kernel binary delta.

## Recommendation

Kernel patching is possible. The lowest-risk path is not a full kernel rebuild; it is a bounded fixed-length rodata patch applied to the known V2316 kernel blob during a new V2317 boot-image build.

Recommended next options:

1. **Product-only V2317 test** — patch only `SAMSUNG_Android` to `A90 Linux ARM`; host would show `SAMSUNG` / `A90 Linux ARM` / `A90NATIVE001`. This avoids the collateral `Gamepad for ...` string change.
2. **Full identity V2317 test** — patch `SAMSUNG_Android` and `SAMSUNG`; host should show `A90-LNX` / `A90 Linux ARM` / `A90NATIVE001`, with the known collateral gamepad string suffix change.

If either option is promoted to a flashable test, it must be built as a new run/build identity with a native-init version bump, a private boot image SHA256, and the standard AGENTS.md flash gates:

- flash boot only via `workspace/public/src/scripts/revalidation/native_init_flash.py`;
- confirm V2237 rollback image and `boot_linux_v48.img` before flashing;
- run `a90ctl version`, `status`, and `selftest`;
- validate `usb status control.ok=1`;
- validate host descriptor strings with `lsusb` / host sysfs;
- rollback automatically on any health-check failure.
