# S20+ G986N stock-artifact acquisition H0 record

Date: 2026-08-13
Target: Samsung Galaxy S20+ 5G `SM-G986N` / `y2q` / `y2qksx`
Exact build: `G986NKSS8IYC2`
Sales/OMC region used for firmware query: `KTC`
Tier: H0 host-only acquisition and validation
Result: **PASS_STOCK_FIRMWARE_AND_SOURCE_ACQUIRED**

## Scope and authority boundary

This record binds host-side stock artifacts to the already established public
S20+ identity. It grants no ADB, USB, Download-mode, Odin, reboot, root, D1,
F1, recovery, or partition-write authority. No device command was issued while
performing this work. S22+, A90, and every other attached target received zero
commands.

Firmware, extracted images, source archives, and tool binaries remain under
`workspace/private/` and are not tracked. This report records only public
artifact names, sizes, hashes, package membership, and validation results.

## Firmware provenance and exact version

The host queried Samsung FUS for model `SM-G986N` and region `KTC`. FUS returned
the exact four-part version:

`G986NKSS8IYC2/G986NOKT8IYC2/G986NKSS8IYC2/G986NKSS8IYC2`

The query and download used `samloader-rs` v2.0.0 from its published GitHub
release. The private tool bindings are:

- release metadata SHA-256:
  `0ee2e2c667313a776b0b9a6b53e16708df413ee41b571d83fccdecdd9820ef9f`;
- release archive SHA-256:
  `7c6514028f20d5ea0eb57d6f872eee41b3a52336eabac6379b15a01a06ed7a79`;
- extracted executable SHA-256:
  `8a12712a530aa404df50df4fef0b16b7e0081b5362a3a34c752472d79c61f288`.

Only the tool's host-side update query, firmware download, and `.tar.md5`
verification functions were used. Its detect, flash, PIT, reboot, and USB
functions were not invoked.

## Downloaded stock firmware

Downloaded private archive:

`SM-G986N_13_20250321153251_kw51x66nkx_fac.zip`

- size: `7,582,274,295` bytes;
- SHA-256:
  `1add7bd2e8b122b0668a44b084fd5e5cd62fb7b90472412d12348599d10d64d7`;
- ZIP64 integrity: `7z t` returned `Everything is Ok`;
- member count: exactly five.

The five members are:

1. `BL_G986NKSS8IYC2_G986NKSS8IYC2_MQB93855401_REV00_user_low_ship_MULTI_CERT.tar.md5`
2. `AP_G986NKSS8IYC2_G986NKSS8IYC2_MQB93855401_REV00_user_low_ship_MULTI_CERT_meta_OS13.tar.md5`
3. `CP_G986NKSS8IYC2_CP29396500_MQB93855401_REV00_user_low_ship_MULTI_CERT.tar.md5`
4. `HOME_CSC_OKT_G986NOKT8IYC2_QB93886324_REV00_user_low_ship_MULTI_CERT.tar.md5`
5. `CSC_OKT_G986NOKT8IYC2_QB93886324_REV00_user_low_ship_MULTI_CERT.tar.md5`

No unexpected ZIP member was observed. The complete package is retained only
as a stock-firmware provenance and possible future recovery input. This H0
record does not establish that Odin recovery is demonstrated, that a rollback
path is usable, or that any member is authorized to be flashed.

## AP and stock boot extraction

The AP member was extracted privately and validated independently:

- AP size: `8,799,989,882` bytes;
- AP SHA-256:
  `460a414ca8ba0d9fb64aa53de0fc1c1cc87ae75f0d79a1a1496e478bafa08753`;
- appended Samsung MD5: `samloader verify-md5 --verbose` returned
  `MD5 verification successful!`.

The AP archive contained these 13 top-level members or paths:
`boot.img.lz4`, `recovery.img.lz4`, `dtbo.img.lz4`, `super.img.lz4`,
`persist.img.lz4`, `vbmeta.img.lz4`, `vbmeta_samsung.img.lz4`,
`dqmdbg.img.lz4`, `carrier.img.lz4`, `userdata.img.lz4`, `misc.bin.lz4`,
`meta-data/`, and `meta-data/fota.zip`.

Only `boot.img.lz4` was extracted from AP:

- compressed size: `25,667,811` bytes;
- compressed SHA-256:
  `c2bb08fcbaf492bb0e9bd5dc119633e17b97539f7cd954d88c20c80d046ca29e`;
- decoded size: `67,108,864` bytes;
- decoded SHA-256:
  `29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab`;
- decoded type: Android boot image with `ANDROID!` magic, kernel load address
  `0x8000`, ramdisk load address `0x2000000`, and page size `4096`.

Decoding used Ubuntu archive package `lz4` version `1.10.0-8` without installing
it system-wide. Its private package SHA-256 is
`33135f6ca21d87ddf90162650b660183e579a041b3e48b372bfcc96b50724828`
and extracted executable SHA-256 is
`4be960d6f6b0d7ef69e01a9e1a056591c17b8687e9851db128018b2ac5f01da0`.

The decoded stock boot image is only an exact offline candidate for later
analysis. It is not yet a reviewed rollback artifact, and it grants no patch,
transfer, boot, or flash authority.

## Samsung-published source acquisition

Samsung Open Source Release Center has exactly one search result for
`G986NKSS8IYC2`, identified as upload `13148`. It lists model `SM-G986N`,
version `G986NKSS8IYC2`, and source file
`SM-G986N_KOR_13_Opensource.zip` with displayed size `242.06 MB`.

After the agent-side Chrome download event failed, the operator completed the
official download. The downloaded outer bundle is `SM-G986N.zip`:

- size: `254,275,697` bytes;
- SHA-256:
  `3ae8f4606ce54e931535b72c5e339494655fd5b01a8b0abc45088033410fa1a5`;
- ZIP integrity: `7z t` returned `Everything is Ok`;
- member count: exactly two.

The outer bundle contains the expected target archive
`SM-G986N_KOR_13_Opensource.zip` and the separately named small companion
`SM-G988N_KOR_13_Opensource_G988NKSS8IYC2.zip`. The bundle is retained intact,
but only the `SM-G986N` member was extracted for target analysis. No G988N
source content was extracted or treated as S20+ target evidence.

The exact target source archive is:

- size: `253,820,334` bytes;
- SHA-256:
  `f21189586ed4739b4810a81346cee0fdd6b82aa8fd7854b6ca337e7cac13d31e`;
- ZIP integrity: `7z t` returned `Everything is Ok`;
- members: `Kernel.tar.gz`, `Platform.tar.gz`, `README_Kernel.txt`, and
  `README_Platform.txt`, with no additional member.

`Kernel.tar.gz` was extracted privately and passed `gzip -t`:

- size: `214,726,875` bytes;
- SHA-256:
  `4ed0aa2f390d9d847eee313693fe8b9b726f4decefc40b3ba8fde1b64272ae6d`;
- archive member count: `76,056`;
- kernel Makefile version: `4.19.113`;
- exact Samsung defconfig:
  `arch/arm64/configs/vendor/y2q_kor_singlex_defconfig`;
- defconfig SHA-256:
  `d9c701269d2a17fea691da1a9e824cfd8920e331fc0877b5a4a9b3e936ebba48`;
- defconfig length: `6,986` lines.

The source README and `build_kernel.sh` both select
`vendor/y2q_kor_singlex_defconfig`, `ARCH=arm64`, external DTC, ARM64 DT
overlay building, an Android GCC 4.9 cross-prefix, and Qualcomm's shipped
Clang 10 as `REAL_CC`. The source archive has no top-level `toolchain/`
directory even though `build_kernel.sh` refers to one. Therefore the source
tree is exact public source evidence, but a complete toolchain, generated final
`.config`, reproducible build, and byte identity with the stock kernel remain
unproven. The defconfig's `CONFIG_IKCONFIG=y` is not by itself proof of the
stock image's final runtime configuration.

## Verdict

The exact `KTC` stock firmware and its stock `boot.img` are now present and
cryptographically bound under private storage. Package shape, ZIP integrity,
AP appended MD5, and decoded boot-image type passed. Samsung's exact source
bundle, target source archive, and kernel archive are also present and
cryptographically bound; their container integrity and public kernel version
and defconfig path passed host-only inspection.

No root, recovery, flash readiness, usable rollback path, partition identity,
D1, F1, reproducible-build, or stock-kernel byte-identity conclusion follows
from this H0 result.
