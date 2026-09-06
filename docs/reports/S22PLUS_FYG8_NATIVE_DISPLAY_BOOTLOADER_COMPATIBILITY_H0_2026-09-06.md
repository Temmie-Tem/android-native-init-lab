# S22+ FYG8 display candidate: bootloader compatibility review

Date: 2026-09-06. Exact target: SM-S906N / g0q / S906NKSS7FYG8.
Scope: retained firmware, repository consumers and public source; H0 only.

## Finding

No display-specific bootloader rejection was identified for the proposed
source-matched Image plus generic-ramdisk module/renderer addition. This is not
acceptance of an unbuilt candidate. The useful remaining bootloader checks are
final boot-image layout and size, unchanged supporting firmware, and preservation
of the vendor DT/panel handoff. Module version/CFI failures and panel probe failures
occur after kernel entry and must not be labeled bootloader rejection.

The existing [P348 native session result](S22PLUS_FYG8_P348_RETAINED_SHELL_PREPARED_2026-09-06.md)
is stronger evidence against categorical rejection of custom PID1 than the older
ambiguous early-boot experiments. It does not qualify the new display module.
P349 remains paused and unchanged; no device command was issued in this review.

## Exact retained firmware inspected again

Re-extracted only ABL and UEFI from the already retained FYG8 firmware ZIP.
The BL archive is 114,319,472 bytes, SHA-256
`e5aeb59de4ed16c21111945900aeda4743b717361b0919084e9d284d08e4e0ba`.
ABL is 4,194,304 bytes, SHA-256
`b828dffa4ea63eeaeb5d374db96daee9e1f696487f724d18aecbbc61ed993a24`.
The standard UEFI parser opened its compressed firmware volumes; no encryption
or missing-source assumption was used to stop the inspection.

Extracted LinuxLoader is 1,671,168 bytes, SHA-256
`b1ee37a2be13a557fa05a6e603fa81c827b3d8be410df1a61145f050c67cde28`,
matching the [earlier exact-build RE](S22PLUS_FYG8_BOOTLOADER_REBOOT_REASON_AND_RETAINED_MEMORY_STATIC_RE_2026-07-11.md).
Odin is 1,208,320 bytes, SHA-256
`530562f08f06b5bb197f2a13aab47cce16923df032d67bb2708dc85221b15ea6`.
Publicly available Qualcomm-derived code is comparative source, not the exact
Samsung LinuxLoader source.

| Potential block | Evidence and implication |
| --- | --- |
| Odin authentication / revision checks | Exact Odin contains authentication, secure-check and fused-versus-binary revision diagnostics. These checks exist; their presence does not mean they reject this boot-only successor. Existing unlocked FYG8 native transfers are the relevant positive evidence. No firmware revision or security-state change is proposed. |
| AVB locked/unlocked policy | LinuxLoader has an unlocked continuation diagnostic at RVA `0xe4fbf`, referenced at `0x7d1c`, and separate device-state failure paths. Earlier retained traces and later native execution support the unlocked allowed path. This is not a blanket claim that every malformed image is accepted. |
| Boot/vendor-boot format | Exact LinuxLoader has invalid header/version/size and missing vendor-boot paths. Retain the existing version-4 packager, alignment, vendor boot, DTBO and AVB context; independently unpack the final artifact. |
| Image / ramdisk size | Exact LinuxLoader has overflow and ramdisk-layout checks. The retained P349 boot container is 100,663,296 bytes. The eventual expanded generic ramdisk must fit the actual packing layout; compressed AP size alone is not sufficient. |
| New `.ko` signature | The actual fixed Image was reopened: MODULE_SIG and MODULE_FORCE_LOAD are unset, MODVERSIONS and CFI_CLANG are enabled, CFI_PERMISSIVE is unset. The display module still needs matching imports, module metadata, CFI and runtime ABI. This is kernel loading, not ABL parsing a `.ko`. |
| Vendor DT and panel selection | ABL supplies/updates DT and boot parameters. Keep the stock vendor DTB/DTBO path. The retained selected-panel gamma tables were joined across all 11 matching overlay entries; their bytes agree. A stock splash or bootloader panel selection is not successful DRM scanout. |

The ramdisk diagnostic warrants a precise limit: at LinuxLoader RVA
`0x18ff8`, the inspected helper initializes its end-address local to zero
(`0x19014..0x19018`); `0x19104..0x19134` adds three 32-bit size fields and
compares the unsigned end-minus-load-address quantity against their sum.
This does **not** provide a simple positive RAM-size ceiling to copy into a
validator. Preserve the packager's actual range/overflow checks; do not invent a
threshold from the diagnostic string. Comparable
[BootLinux.c](https://github.com/SHIFTPHONES/android_bootable_bootloader_edk2/blob/sos-3.x/QcomModulePkg/Library/BootLib/BootLinux.c)
also initializes this end-address local to zero. Its field meanings are context
for the analysis, not independent proof of Samsung's complete structure layout.

## Public-source cross-check

AOSP distinguishes the version-4 GKI `boot_signature` VTS check from
device-specific verified boot. Removing or changing a generic ramdisk still
changes its containing boot image and requires the existing AVB/packaging
validation; these are separate mechanisms.
[Boot image header](https://source.android.com/docs/core/architecture/bootloader/boot-image-header).

The bootloader loads the generic ramdisk after the vendor ramdisk, and kernel
unpacking overlays the generic contents. Thus adding the reduced module to the
generic ramdisk is a supported structural route; it is not an instruction to
write vendor_boot. The final extraction must prove the intended file wins and
that no stock display copy is subsequently loaded.
[Vendor boot partitions](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions).

AOSP documents vendor-module compatibility as a kernel concern, including
configuration-dependent interfaces. Our exact Image's settings and the actual
loader consumer take precedence over a generic GKI signing description.
[Loadable kernel modules](https://source.android.com/docs/core/architecture/kernel/loadable-kernel-modules).

A related SM8450 tablet port reports that Samsung ABL's DT overlay merging can
break a mainline DTB and uses uniLoader to avoid it. That is a useful warning for
a future mainline migration, not an observed blocker for this stock-DT,
source-matched-kernel display experiment and not a reason to add another loader.
[Project's own account](https://github.com/aaronsb/sm-x800-linux#why-this-is-unusual).

## Evidence and remaining qualification

Private evidence: `workspace/private/outputs/s22-display-renderer-h0/` contains
`bl/receipt.json`, extracted PE images, `bl/string-census.json`, exact disassembly
windows and xref receipt, and `image-config-check.json`. All firmware stays
private. Strings establish diagnostics; only the stated disassembly windows
were decoded, not every Samsung verification branch.

Final packaging must check the changed generic ramdisk, sole boot archive member,
size/layout, unchanged supporting identities, and the exact loaded module plan.
An attended run must distinguish transfer rejection, pre-kernel failure,
module/probe failure, completed DRM events, visibly changing output, and rollback
health. No new F1 approval or activation is supplied by this report.
