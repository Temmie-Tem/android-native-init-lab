# A90 public MPGen 2.7 self-consistent RTIC rebuild and public-source follow-up — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only acquisition, build, and artifact analysis
Device contact: none
Authority: no candidate, D0, D1, F1, rollback, reboot, or live authority
Disposition: RTIC byte consistency reproduced; stock production-catalog
equivalence and device acceptance remain unproved

## Result

The missing H34 build input is now reproduced far enough to separate two
claims that must not be collapsed:

1. **RTIC structural consistency is proved.** Public MPGen 2.7 generated an
   `rtic_mp` object and a 173-byte RTIC DTB for an otherwise H34-equivalent
   rebuild. A comparison wrapper made from that Image, the unchanged first two
   stock hardware DTBs, and the new RTIC DTB passes
   `a90_rtic_mp_consistency.py`: the virtual address, raw-Image offset, byte
   count, interface `30.3`, marker, and SHA-256 all agree.
2. **Stock security equivalence is not proved.** The public package identifies
   its catalog as a test catalog and tells users to contact Qualcomm for the
   production catalog. It emits one extra write-once-unknown SELinux asset,
   embeds a warning that its declared writer was not found, uses a different
   MPGen content version, and incorporates wall-clock time into the measured
   bytes.

The private output is therefore an H0 comparison artifact named
`PUBLIC_MPGEN27_SELF_CONSISTENT_CONTROL`. It is not a boot image, candidate,
qualification input, approval target, or reason to replay consumed H34.

## Frozen public and retained inputs

The build reused the already selected A908N Android 12 OSRC source and the
exact H34 configuration and module-signing key. It changed only the presence
of MPGen in the kernel link environment; host compatibility tools do not alter
kernel source semantics.

| Input | Exact identity |
|---|---|
| A908N OSRC `Kernel.tar.gz` | `403fdc49f086d238c01a796c390083c3c47c1754c218e228f29b55cc7c35d554` |
| selected `.config` | 188,380 / `e4b7fa2f4fd6055eecfc7fd7b7546ab3e77ffdaf8ee77da27c9f341646f77f8b` |
| Snapdragon LLVM 10.0.7 `clang` | 96,189,952 / `453971166fa1b628df189e602f355cb2c58c12cd289515400ee6260c9a83459d` |
| GNU 4.9/gold repository | `606f80986096476912e04e5c2913685a8f2c3b65` |
| retained H34 build X.509 | 1,324 / `c773e5d46d151f8e10e966c1fbeba21dd49213dc80d057ecc9a7e200a8bc26db` |
| public MPGen repository | `tadiphone-caf/vendor_qcom_proprietary@9a79e3c6b709ced2c53befa46628395989d8892b` |
| public `qrsp/mpgen` Git tree | `da751d7cc2cca10f1f4af50f48abfe26c534d652` |
| public `mpgen.py` | `7c21589480f95e5901d4cbcdc4d9c5a8d819cb9857014a3e27cd952a8082af88` |
| public `const.py` | `35ca852f5f115123c7d589d1ad969cd04a5a0bf675c269d114f31330e4c954f0` |
| CPython 2.7.18 source archive | `b62c0e7937551d0cc02b8fd5cb0f544f9405bafc9a54d3808ed4594812edef43` |

Primary public source links:

- [public MPGen 2.7 tree](https://github.com/tadiphone-caf/vendor_qcom_proprietary/tree/9a79e3c6b709ced2c53befa46628395989d8892b/qrsp/mpgen)
- [published Snapdragon LLVM source dump](https://github.com/comprehensive9/vendor_qcom_proprietary/tree/36fc163a534963a5b3af52186af5efcc63401ad2/llvm-arm-toolchain-ship/10.0)
- [AOSP GNU 4.9/gold commit](https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9/+/606f80986096476912e04e5c2913685a8f2c3b65)
- [official CPython 2.7.18 release](https://www.python.org/downloads/release/python-2718/)

The local host-preparation receipt is
`9ee833f36233ea71abb46882f7e6e98bbbff0f7ec708481897b4a2aef3ddc506`.
It records the same three line-ending normalizations, 26 exact-byte mappings,
63 preserved includes, two workspace links, and
`semanticSourceChanges: 0` as the earlier selected rebuild.

## Build result

The exact H34 banner was retained:

```
Linux version 4.14.190-25818860-abA908NKSU5EWA3 (dpi@SWDK6110) (clang version 10.0.7 for Android NDK, GNU ld (binutils-2.27-bd24d23f) 2.27.0.20170315) #2 SMP PREEMPT Thu Jan 12 18:53:40 KST 2023
```

The build log records three successful MPGen executions: placeholder object,
post-kallsyms object, and final DTS payload. CFP instrumentation and the FIPS
HMAC update then complete, followed by raw Image generation. The retained H34
PEM and DER bytes were restored after a discovery build showed that an older
mtime causes Kbuild to generate a new key. Direct Image extraction confirms
the final compiled-in certificate is again exactly the retained H34 DER hash.

| Final host artifact | Bytes | SHA-256 |
|---|---:|---|
| raw `Image` | 48,830,480 | `94767a8233173ea3a5f1875822373f92084a90483b9ec5d0cf84a6135207b962` |
| `System.map` | 6,363,557 | `01df7d8ad1915ef64a48916dd3fee19aadf57005777fb73ad6ebad8e15ff31db` |
| generated `rtic_mp.dtb` | 173 | `3434b434da95108252a74133c4cc39c7ffef48bf04fb781d52a1d23f8f66c874` |
| H0 comparison wrapper | 49,827,613 | `36ef56c07a9b8a8d8e8fffb56609e617846a5705cbf0e86adeb71f446112430e` |

The wrapper is format-comparable to the retained kernel carrier: 20-byte
`UNCOMPRESSED_IMG` header, 48,830,480-byte Image, the exact two stock hardware
DTBs (497,331 and 499,609 bytes), and one freshly generated 173-byte RTIC DTB.
No boot ramdisk or boot image was made.

## Exact RTIC comparison

| Surface | Stock carrier | Failed H34 hybrid | Public-MPGen control |
|---|---|---|---|
| wrapper decision | `PASS` | `FAIL` | `PASS` |
| `rtic_mp` VA | `0xffffff8009f00000` | absent | `0xffffff8009f00000` |
| raw Image offset | `0x01e80000` | unrelated bytes | `0x01e80000` |
| interface | `30.3` | unrelated values | `30.3` |
| MPGen content version | `2.7.ef86a6.30` | absent | `2.7.48ef28.30` |
| measured byte count | 1,624 | stale DTB asks for 1,624 | 1,728 |
| expected/actual SHA-256 | `26178df5…` / equal | `26178df5…` / `5943e167…` | `8bb97ebc…` / equal |
| RTIC feature cardinality | RO 3 / WK 1 / WU 2 / AW 0 | no MP | RO 3 / WK 1 / WU 3 / AW 0 |

The current validator proves byte binding only. Its `PASS` does not validate
whether a catalog is the Samsung/Qualcomm production policy, whether QHEE will
accept the different content version and feature cardinality, or whether the
device will boot it.

## The catalog difference is load-bearing

The public source itself says:

```
# TEST CATALOG
# For production catalog contact Qualcomm Technologies, Inc.
```

Its catalog unconditionally adds `selinux_state` with the adjacent comment
`after kernel 4.19`. The A90 kernel reports 4.14.190 but contains a backported
two-byte `selinux_state` symbol. The public tool therefore emits that third WU
record. It searches for `selinux_init` as the writer in the pre-final object,
does not find it, embeds `` `selinux_state`(no selinux_init) `` in the MP
warning field, and still emits the asset with an empty writer list.

The stock MP contains:

- RO: `linux_banner`, `linux_proc_banner`, `selinux_hooks`;
- WK: `ss_initialized`;
- WU: `.head.text`, `selinux_enforcing`; and
- AW: none.

The public control contains the same named set plus WU `selinux_state`.
Whether that is stricter, harmless, or rejected is **unproved**. The public
tool's own `is_checkable_kernel = 1` is self-description, not independent
production-policy evidence.

The public tool also computes `created_tmstmp` from the current host clock and
does not consume `SOURCE_DATE_EPOCH`. The final control embeds
`2026-08-22T09:43:54Z`; the stock MP embeds `2023-01-12T09:54:31Z`. A second
build at a later time produces different MP bytes and a different RTIC DTB
hash even when all named source inputs are unchanged. Exact built bytes can be
pinned, but build reproducibility is not yet closed.

## Layout repair relative to H34

The public tool does restore the fixed RTIC layout that H34 omitted. The new
`System.map` adds exactly one symbol relative to H34, `rtic_mp`, at the exact
stock address. Because the linker reserves that fixed region, 29,240 common
symbols change address relative to the MPGen-free H34 build.

An independently extracted stock kallsyms map gives a useful bounded
comparison:

| Candidate map | Names common with stock | Exact-address common names |
|---|---:|---:|
| H34 MPGen-free rebuild | 142,719 | 54,709 |
| public-MPGen rebuild | 142,720 | 80,997 |

The H34 map has a 26,286-symbol mode shifted by `-0xd4000`; that mode disappears
after MPGen is linked. This is strong host evidence that the missing fixed RTIC
region caused a large H34 layout divergence. It is not a boot result.

## Public 4.14.190 source reconstruction result

The parallel attempt to bind the 2023 Evolution X artifact to exact public
source did not close. Two closest release-era snapshots were acquired directly:

| Snapshot | Source archive SHA-256 | IKCONFIG symbols after `olddefconfig` | Value changes from artifact IKCONFIG |
|---|---|---:|---:|
| [`d6ddde5205b0`](https://github.com/Roynas-Android-Playground/kernel_samsung_r3q/commit/d6ddde5205b05dd0d2b0a43f797e944124881a2b) | `e35e4ab76f41d22160400f46c223176a835e5892f4513627bb14b3635776f1e0` | 5,402 | 115 |
| [`e1d271581eff`](https://github.com/Roynas-Android-Playground/kernel_samsung_r3q/commit/e1d271581eff) | `19c94ebc15055cc1571b47a60e2ba37ce109bf436af36229b443d0b28f7c4b76` | 5,405 | 120 |

Both trees report Linux 4.14.190. Their exact KernelSU submodule
`0617c4440bfe80b386b068cfbc7091630e67d4a7` was also acquired; its source
archive is `7bb1a2954845c98714043fa0086ba47bcbde30f5d583d3bf2d5a5e3eda7ba4a5`.
The released boot's embedded IKCONFIG has 5,512 represented symbols and SHA-256
`d938920195a3ef85b033c65f9c06d4d3c97cd84ac4da8b222dab623fa92e4a28`.

The public device tree selects only `r3q_defconfig`; it does not explain the
missing definitions or the 115/120 normalization changes. The released Image,
config, banner, and two-DTB shape remain exact artifact evidence, but the exact
source commit and build closure are **unproved**. No unpublished working tree
or manual config-data substitution is inferred.

Relevant primary records are the
[r3q BoardConfig](https://raw.githubusercontent.com/Roynas-Android-Playground/device_samsung_r3q/thirteen/BoardConfig.mk)
and the
[public r3q defconfig history](https://github.com/Roynas-Android-Playground/kernel_samsung_r3q/commits/master/arch/arm64/configs/r3q_defconfig).

## Consequence and next host unit

This unit closes the claim that MPGen is unavailable or cannot generate an
A90-shaped RTIC object. It does not close the production-policy claim.

The next bounded H0 discriminator is catalog closure, in this order:

1. search for the exact stock content version `2.7.ef86a6.30` or another
   directly attributable production catalog;
2. if absent, derive the stock 3/1/2/0 feature set and compare every field,
   attribute, address, size, and writer against the public generator before
   considering a catalog override; and
3. define deterministic time injection without modifying MPGen source bytes,
   then reproduce two independent identical Images and RTIC DTBs.

Only after those H0 closures and an independent review could a fresh candidate
question be posed. Nothing in this report grants F1 or selects the public-ROM
hardening-disabled architecture.

## Boundary

This unit contacted public web and source hosts and used local private build
inputs. It did not enumerate or contact `/dev`, USB, ADB, recovery, serial,
Download mode, an A90 network endpoint, S22+, or S20+. It made no boot image,
approval, manifest, journal, transfer, reboot, rollback, or device claim.
H34 remains consumed and non-replayable.
