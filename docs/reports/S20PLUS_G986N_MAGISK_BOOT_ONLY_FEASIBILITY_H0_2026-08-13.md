# S20+ G986N Magisk boot-only feasibility H0 record

Date: 2026-08-13
Target: Samsung Galaxy S20+ 5G `SM-G986N` / `y2q` / `y2qksx`
Exact build: `G986NKSS8IYC2`
Tier: H0 host-only stock-image and upstream-source analysis
Result: **FORMAT_COMPATIBLE_AVB_AND_TRANSPORT_UNQUALIFIED_NO_GO**

## Scope and authority boundary

This record answers only whether the exact stock `boot.img` has a shape that
Magisk understands and whether the currently known evidence is sufficient to
design a boot-only first install. It creates no patched image or Odin archive
and grants no ADB, USB, Download-mode, reboot, root, recovery, payload,
partition read/write, D1, or F1 authority. No device command was issued. S22+,
A90, and every other attached target received zero commands.

The firmware, boot components, Magisk package and source, AVB tooling, and raw
analysis outputs remain under `workspace/private/`. Only public artifact
properties and cryptographic bindings are recorded here.

## Pinned Magisk release

The host pinned official Magisk v30.7 release metadata, APK, and tag source:

- official APK size: `11,613,864` bytes;
- APK SHA-256:
  `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`;
- the SHA-256 equals the digest published for the GitHub release asset;
- APK archive integrity: `7z t` returned `Everything is Ok` for 690 files;
- embedded release metadata: version `30.7`, version code `30700`, stub version
  `40`;
- release metadata SHA-256:
  `53088eba0bc2162711aebe32ddb33f4e4ceeb567dcfdf0f24ba2dc9b1bb992bb`;
- tag-source archive SHA-256:
  `9a908fc13a60bbb95c848c9e8cfbb5bd4e49fda98ee6932907c4a517fbc95437`.

The x86-64 `magiskboot` extracted from that APK is a static ELF executable
bound by SHA-256
`a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e`.
The APK's `boot_patch.sh` is byte-identical to the script in the v30.7 tag
source and is bound by SHA-256
`20de7208d610a267aaafafe09846c4458a240ba51656d05252fc1c9c7e7ada8f`.

Upstream references:

- Magisk installation documentation:
  <https://topjohnwu.github.io/Magisk/install.html>;
- official Magisk repository: <https://github.com/topjohnwu/Magisk>;
- official release page: <https://github.com/topjohnwu/Magisk/releases>.

## Exact stock boot structure

The analyzed input is the previously bound 64 MiB stock boot image with
SHA-256
`29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab`.
Official Magisk v30.7 `magiskboot unpack -h` accepted it and reported:

- Android boot header version `2` and page size `4096`;
- kernel size `51,959,820` bytes, raw ARM64 Linux `Image`;
- ramdisk size `724,388` bytes in gzip form;
- decoded ramdisk cpio size `1,565,952` bytes;
- DTB size `1,580,275` bytes;
- OS version `11.0.0` and patch level `2025-03` as encoded in the header;
- Samsung `SEANDROIDENFORCE` marker; and
- an AVB 2 footer/VBMeta block.

The extracted components are bound as follows:

- header SHA-256:
  `1f948cfa15174ab850d66c2600654aacece5f7c2a5cd871f1b30db153d3baff3`;
- kernel SHA-256:
  `127d0f43de5e5e5ce5eee9e496b9593cf6ce7f0ce97581ad483e8f76feeb31ca`;
- decoded ramdisk cpio SHA-256:
  `42432b5d43303497e2953df21661b69ba132b8b748e30f255568d626bcc06990`;
- DTB SHA-256:
  `09ce85eab63208c985486bba8b450d17fd5907839361b53bf1971e0eeaceb883`.

`magiskboot cpio ... test` returned stock status `0`, and read-only DTB testing
also returned `0`. The ramdisk has an ordinary first-stage shape containing
`init`, `fstab.qcom`, `dpolicy`, and the minimal device/mount directories.
These results establish that the exact stock image is structurally accepted
by the v30.7 patch engine and has a boot ramdisk. They do not establish that a
patched image will pass Samsung Download-mode and AVB policy or boot.

## Direct stock-kernel evidence

The kernel reports:

`Linux version 4.19.113-27166950 (dpi@SWDM8415) (clang version 10.0.6 for Android NDK) #1 SMP PREEMPT Mon Mar 17 23:08:14 KST 2025`

Samsung's source `extract-ikconfig` recovered the embedded final configuration
from the stock kernel; the recovered text is bound by SHA-256
`5e4e4a986f7aae396dc3ebb03818a4c0b9bea5f6948c5e17eb6abaf8d988f760`.
Selected final values are:

```text
CONFIG_IKCONFIG=y
CONFIG_IKCONFIG_PROC=y
CONFIG_INITRAMFS_SOURCE=""
CONFIG_KALLSYMS=y
CONFIG_RANDOMIZE_BASE=y
CONFIG_MODULES=y
CONFIG_MODULE_SIG=y
CONFIG_MODULE_SIG_FORCE=y
```

This is final embedded kernel configuration evidence, not an inference from
the published defconfig. It is useful for a later kernel-build unit but does
not prove reproducibility or Magisk boot success.

## Exact AVB relationship

AOSP `avbtool` from branch `android13-release`, commit
`8261ecd67956f6e9647ff5fd4aeb829f75fb3f66`, was pinned for read-only
inspection. Its SHA-256 is
`69783733ce5e198317b02a5567cc356e898c891de872f58a963e9d5c082973c6`.
The upstream AVB implementation and documentation are at
<https://android.googlesource.com/platform/external/avb/>.

The stock boot footer is valid AVB 2 metadata using `SHA256_RSA4096`; it covers
the first `54,272,528` bytes of partition `boot` with digest
`731feb7bd909bf3eb7820a628fa78d0bcefb489c6dd941c164a442189b68f2d6`.
`avbtool verify_image` verified the embedded key and boot hash. A
`magiskboot verify` return of `1` is not an integrity failure here because that
subcommand checks AVB 1 signatures, whereas this image uses an AVB 2 footer.

The AP also contains distinct `vbmeta.img` and `vbmeta_samsung.img` members.
The decoded top-level `vbmeta.img` is `9,408` bytes, has SHA-256
`8bf58077aa649d24e3e749bedce8f57355081fb765d81194ac11a0f84e2d9258`,
uses the same public-key digest as the boot footer, and has flags `0`. Its
descriptors repeat the exact stock boot image size, salt, and digest. Therefore
changing the boot payload necessarily invalidates both the stock boot hash and
the stock top-level VBMeta boot descriptor unless the verified-boot policy is
changed or an equivalent accepted signing relationship is provided.

## Why the official Samsung path is not boot-only

Magisk v30.7's Samsung AP-tar path confirms the AVB coupling in executable
source:

1. it extracts the AP's `boot.img` for ramdisk patching;
2. when it encounters a `vbmeta.img` member, it sets VBMeta flags to `3`, the
   combination of hashtree-disabled and verification-disabled;
3. it emits that modified `vbmeta.img` together with the patched boot and the
   copied AP members; and
4. it disables the embedded-boot VBMeta-flag patch when a separate VBMeta
   member is present.

The official Samsung instructions accordingly require selecting the complete
AP tar in Magisk and flashing the resulting patched AP together with `BL`,
`CP`, and `CSC` for first installation, including another data wipe. They also
warn that installing Magisk irreversibly trips the Knox warranty bit.

That documented process exceeds this repository's permanent boot-only payload
boundary: `vbmeta`, BL, CP, CSC, recovery, and every non-boot partition are
forbidden. Bootloader state `OFF (U)` and Android verified-boot state `orange`
show that unofficial images may be accepted, but they do not prove that this
exact Samsung firmware accepts a modified boot while retaining stock top-level
VBMeta, nor do they authorize testing that proposition.

## Verdict and next gate

The exact stock boot image is **format-compatible** with Magisk v30.7: it is a
valid boot v2 image, contains a stock ramdisk, passes read-only ramdisk and DTB
classification, and is accepted by the official unpacker. No TWRP or recovery
image is needed to perform the patch operation itself.

Live boot-only rooting is nevertheless **not qualified**. The unresolved
blocking facts are:

1. a patched boot would conflict with the exact stock boot and top-level
   VBMeta descriptors;
2. the official Samsung AP path deliberately modifies separate VBMeta and
   requires a multi-slot Odin operation outside the permanent boundary;
3. no exact boot-only Odin archive and archive-membership validator exists;
4. the exact Download-mode boot partition mapping, accepted transfer behavior,
   size limit, and post-transfer observation have not been qualified;
5. the stock boot file is a provenance-bound candidate but not yet a
   demonstrated rollback through a reviewed recovery path; and
6. the S20+ target contract defines no D1/F1/root/flash/recovery process.

The next safe unit is a separate H0 design proving whether an exact
`boot.img`-only Odin transaction can be accepted under the device's current
unlocked/orange state without modifying any VBMeta or other forbidden
partition. It must define exact target selection, a stock-boot rollback,
physical recovery, one-shot/no-replay journaling, archive membership,
observation, and final health, then receive independent review before any live
action. Until that proof exists, do not create a Magisk-patched candidate, do
not install TWRP, and do not flash.
