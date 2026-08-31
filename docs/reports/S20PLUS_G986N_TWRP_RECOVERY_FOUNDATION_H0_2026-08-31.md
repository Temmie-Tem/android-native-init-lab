# S20+ G986N TWRP and recovery-foundation H0 record

Date: 2026-08-31
Target: Samsung Galaxy S20+ 5G `SM-G986N` / `y2q` / `y2qksx`
Exact build: `G986NKSS8IYC2`
Tier: H0 host-only provenance, extraction, and static inspection
Result: **STOCK_RECOVERY_BOUND; PUBLIC_TWRP_NO_GO; MINIMAL_CANARY_SELECTED**

## Scope and authority boundary

The operator selected recovery/TWRP preparation as the next research direction.
This record performs only host-side acquisition and static inspection. No ADB,
USB, `su`, reboot, Download-mode, Odin, or device command was issued. No image
was transferred and no partition, Android data, Magisk state, or device setting
was changed. S22+, A90, and every other target received zero commands.

The common contract currently permits ordinary partition payloads only to
`boot` and explicitly rejects `recovery` and VBMeta payloads. The S20+ target
contract also grants no TWRP or recovery-write authority. Therefore neither the
operator's direction nor this H0 result activates a live installation. A future
recovery experiment requires a deliberate common-boundary amendment, matching
S20+ contract/process changes, exact reviewed artifacts and runner closure, an
independent review, mechanical activation, and fresh attended run binding.

Firmware and unpacked images remain private and untracked. This report records
only public provenance, hashes, structure, and conclusions.

## Exact stock recovery input

The exact `G986NKSS8IYC2` AP previously acquired from Samsung firmware contains
`recovery.img.lz4`. It was streamed out host-side, copied to the private exact-
target input tree, decoded, hashed, and structurally inspected:

| Form | Size | SHA-256 |
|---|---:|---|
| AP member `recovery.img.lz4` | 36,600,544 bytes | `6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923` |
| decoded `recovery.img` | 82,694,144 bytes | `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e` |

The decoded image is Android boot-image header version 2 with:

- board name `SRPSK18B008`;
- kernel size 51,959,820 bytes;
- ramdisk size 11,346,441 compressed bytes;
- recovery DTBO size 1,034,509 bytes;
- DTB size 1,580,275 bytes;
- OS version 11.0 and patch level 2025-03;
- kernel banner `Linux version 4.19.113-27166950`, built 2025-03-17.

Its unpacked component SHA-256 values are:

- kernel: `127d0f43de5e5e5ce5eee9e496b9593cf6ce7f0ce97581ad483e8f76feeb31ca`;
- ramdisk CPIO: `9dc6cc9efa7889f339c4e8a98d87b58a3e6ff201d519aadc3a4394ec235482a3`;
- DTB: `09ce85eab63208c985486bba8b450d17fd5907839361b53bf1971e0eeaceb883`;
- recovery DTBO:
  `11e0da1564c1e2bbbccfa13f41ceaa105135586a443646980baa421b00137455`.

The stock image's embedded AVB hash descriptor verifies the exact stock bytes.
Its public-key SHA-1 is
`034de7d0a233d802b43f46c92cbde4bc3420c918`, matching the recovery chain
descriptor in the exact top-level stock `vbmeta.img`.

This closes the exact stock recovery **input** identity. It does not yet prove a
usable or demonstrated recovery-partition rollback path; that requires a
reviewed transfer process and attended evidence.

## Public candidate landscape

The [official TWRP Samsung device list](https://twrp.me/Devices/Samsung/)
contains the Exynos S20+ `y2s`, but no Snapdragon S20+ `y2q`. There is therefore
no official TWRP image or official-device maintenance claim for this target.
That absence is a provenance and maintenance limitation, **not** a standalone
rejection criterion. The A90 recovery used by this repository is also an
unofficial TWRP. Its operational value was established instead through an exact
version/banner, exact helper bytes, one bound recovery-ADB identity and arrival,
physical availability, boot readback, and observed rollback/return behavior.
The S20+ candidate must be judged by the same evidence-first standard.

The original [unofficial Snapdragon S20-series thread](https://xdaforums.com/t/recovery-unofficial-twrp-for-galaxy-s20-series-snapdragon.4157901/page-14)
names `G986N`/`y2q`, but its documented installation sequence flashes a VBMeta-
disable payload before TWRP and uses `multidisabler` plus a data format. The
associated AndroidFileHost directory no longer exposes the old binary without
restricted access. A public source mirror preserves an Android 12.1 tree at
commit `3b7644b9203dfa0ab1120a3b83553520e9a99b8e`, last dated 2022-10-17, with a
prebuilt US `G986USQU2FVC5` kernel. It is proxy evidence, not an exact IYC2 build.

TWRP 3.7.0 was the project's major
[Android 12 release](https://twrp.me/site/update/2022/10/10/3.7.0-released.html),
while Android 13 work was only beginning. The old tree also sets
`TW_INCLUDE_CRYPTO=false`. Its `multidisabler` remounts vendor read-write, may
resize its filesystem, alters encryption flags, and removes or renames stock-
recovery restoration files. Thus its advertised `/data` usability depends on
additional persistent mutation, not TWRP alone.

A newer public image was quarantined from the
[AstroForge V2 GitHub release](https://github.com/AstroByteX-Code/android_device_samsung_y2q/releases/tag/AstroForge-V2):

- asset: `Twrp_3.7.1_12-AstroForge-V2_y2q.img`;
- size: 82,694,144 bytes;
- SHA-256:
  `41d922d2c812256703981c3ce24ea467888d567a7e6c708670632af535787b0d`;
- release date: 2026-08-03;
- public download count observed during this audit: one.

The downloaded bytes match the digest published by GitHub. That proves the
download identity only; it does not prove authorship, build provenance,
runtime behavior, exact-target compatibility, or safety.

## AstroForge V2 static audit

The candidate is header version 2, OS version 12.0, patch level 2022-04, and
contains kernel `4.19.325-AstroForge-g8b317761d52d` built 2026-08-02. Its AVB
public-key SHA-1 is `2597c218aae470a130f61162feaae70afd97f011`, which differs
from the stock recovery chain key. It therefore cannot inherit the verified
stock recovery signature, and host inspection cannot establish that the
currently installed top-level VBMeta will accept it.

The release asset is not reproducible from its tagged device tree. The tagged
tree contains a different 2021 `4.19.113/EUFC-Recovery` prebuilt kernel and
different DTB/recovery-DTBO bytes. Its proprietary FBE, keymaster, and
gatekeeper blobs also lack pinned origin and byte provenance in the release.
The referenced AstroForge kernel commit exists publicly, but that fact does not
bind the complete released recovery image.

The ramdisk CPIO has 3,685 entries. Static path inspection found no duplicate
members, parent traversal, absolute paths, or special-device nodes. It did find
reachable high-risk behavior:

- `system/bin/postrecoveryboot.sh` remounts vendor read-write and deletes the
  stock recovery-restore script and service files;
- `system/bin/rebootsystem.sh` performs a raw 256-byte zero write to the `misc`
  block device;
- the recovery executable contains references to both hook scripts;
- `twrp.flags` exposes boot, recovery, modem, system, vendor, product, ODM,
  DTBO, Samsung VBMeta, persistent/FRP, and EFS surfaces to recovery UI actions;
- `init.recovery.qcom.rc` mounts persist and EFS read-write.

The 89-byte `rebootsystem.sh` has SHA-256
`3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07`:
it is byte-identical to the exact hook currently bound for A90 TWRP
`3.7.0_12-0`. This is useful transfer experience, not S20+ authority. A90 has a
narrowly reviewed target-only exception for that one hook after an exact boot
write/readback; S20+ currently has no matching exception. The hook must either
be removed or receive its own separately reviewed S20+-specific treatment.

The automatic vendor deletion hook, unconstrained mutation surfaces, missing
complete build reproduction, and absent S20+-specific reviewed exception still
conflict with the current bounded process. The candidate is **NO_GO_AS_IS**,
independent of the operator's willingness to discard Android or `/data`.

## AVB and modification consequence

An isolated no-content-change unpack/repack test of the exact stock recovery
produced the same partition size but different ramdisk compression bytes and a
different whole-image SHA-256. The original image passes isolated AVB
verification; the repack retains a parseable embedded signature but fails the
`recovery` hash descriptor against its changed bytes.

Therefore any ramdisk-modified stock-derived canary is necessarily a custom
recovery candidate. It cannot be represented as stock-signed, and whether the
current unlocked/orange-state boot chain accepts it is a live unknown. That
unknown must be tested through a one-shot recovery-only process with exact
stock recovery rollback; it must not be inferred from root, unlocked state,
artifact shape, or a host-side AVB parse.

## Selected next experiment: T0 recovery ADB canary

Even with the A90 unofficial-TWRP precedent, full TWRP installation is not the
first S20+ live rung: acceptance of any changed IYC2 recovery under the current
boot chain is still unproved. The selected T0 experiment is an exact-stock-
derived `G986NKSS8IYC2` recovery ADB canary:

1. retain the exact stock kernel, DTB, recovery DTBO, header geometry, and
   partition size;
2. change only the ramdisk closure needed to request recovery ADB and expose
   one fixed, read-only canary marker;
3. add no formatter, mount mutation, vendor mutation, `misc` write, root-data
   installer, shell-selected path, or arbitrary partition UI;
4. build candidate and exact-stock rollback archives with one recovery member
   each, deterministic membership, fixed hashes, and no VBMeta payload;
5. statically prove the component delta and reject every unexpected member;
6. separately review the common-boundary amendment, target contract, runner,
   journal, recovery choreography, and hostile tests before activation;
7. in a future attended run, observe bounded recovery ADB plus the marker, then
   return to and prove exact healthy rooted Android; on uncertainty, never
   replay the candidate and retain only the prebound stock rollback path.

If T0 is host-qualified and later passes live, a T1 TWRP candidate may be built
from a pinned source closure with the automatic vendor and `misc` hooks removed,
all persistent/critical surfaces excluded or guarded, exact target components
bound, and proprietary blob provenance resolved. The current public binaries
will not be promoted directly.

## T0 host build result

The fixed host-only builder is now implemented at
`workspace/public/src/scripts/revalidation/build_s20plus_g986n_recovery_adb_canary_h0.py`.
It pins the exact stock recovery, stock LZ4 frame, Magisk v30.7 `magiskboot`,
local `lz4`, and AOSP `avbtool` bytes. It has no ADB, USB, Odin, reboot, `su`,
or other device transport.

The private output is
`workspace/private/outputs/s20plus_g986n/recovery_adb_canary_t0_v1/`.
Its important identities are:

| Artifact | Size | SHA-256 |
|---|---:|---|
| candidate `recovery.img` | 82,694,144 | `e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b` |
| candidate `recovery.img.lz4` | 36,547,618 | `7f0e6b53a1036904fd02c5e8c2c014d3112ffb58fc33f9aa9a26c0962af45928` |
| candidate recovery-only `AP.tar.md5` | 36,556,841 | `30227458889f1fa99eca192c9b7f8747f168d9e33cc1f407b52ae2b4d298559a` |
| rollback exact stock `recovery.img` | 82,694,144 | `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e` |
| rollback exact stock `recovery.img.lz4` | 36,600,544 | `6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923` |
| rollback recovery-only `AP.tar.md5` | 36,608,041 | `ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157` |
| build manifest | 5,459 | `7c693b4e2e13efa912b5de00a95bbd41bb1651913427461e756225243381e1e3` |

The candidate retains the exact header, kernel, DTB, recovery DTBO, and total
partition size. Of 427 stock ramdisk entries, it removes none, changes only
`prop.default` and `init.recovery.samsung.rc`, and adds one mode-`0444` marker.
All other entry content and modes are identical. The changes set recovery-only
ADB properties, request ADB at the recovery boot trigger, and expose the fixed
marker `/init.s20plus_g986n_recovery_adb_canary`.

Each candidate/rollback AP has exactly one regular member,
`recovery.img.lz4`, and a verified appended MD5. Two complete builds are byte-
identical. The focused hostile/reproducibility corpus passes 9/9. Isolated AVB
verification passes the exact stock image and rejects the candidate only at
the changed recovery hash descriptor while verifying its retained embedded
VBMeta signature. Runtime acceptance remains `UNKNOWN`.

## Verdict

The exact IYC2 stock recovery bytes are now durably retained and cryptographically
bound as rollback-building input. Official versus unofficial status is not the
decision boundary. The historical candidate depends on VBMeta/encryption/vendor
mutation, while the recent public candidate contains an automatic vendor
mutation path, lacks a reproducible complete build closure, and has not received
the S20+-specific treatment that made the exact A90 hook acceptable. Neither
public candidate is presently eligible for device transfer as-is.

T0 host construction and hostile static validation are complete. The next
bounded unit is a separate policy/process and execution-closure review. There
is no current live recovery-write authority, no installation approval consumed,
and no claim that recovery rollback has been demonstrated.
