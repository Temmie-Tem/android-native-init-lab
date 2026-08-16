# A90 self-built kernel: first host build, four blockers, and one authorized deviation

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only build on the operator's LAN build host
Device or live effect: none
Disposition: a bootable-format kernel image now exists and is staged; whether
the device boots it is **unproved** and requires a separately authorized F1

Scope of the claim, stated once: this report proves that the A908N kernel
sources **build** and that the resulting artifact has the **format** of a
loadable kernel. It does not prove the device boots it, that the built kernel
is functionally equivalent to stock, or that any capability follows from it.
No boot has been attempted.

## Why this build was attempted

Two separate questions pointed at the same experiment.

`docs/reports/A90_WLAN_KERNEL_SIDE_COMPOSITION_H0_2026-08-15.md` established
that a same-tree rebuild removes **none** of the thirteen WLAN vendor roles,
and that conclusion is unchanged. A rebuild is not a WLAN ownership lever.

The rebuild matters for a different axis. The selected isolated-Debian design
requires a private Binder instance, and the staged A90 configuration has
`CONFIG_ANDROID_BINDER_IPC=y` with `# CONFIG_ANDROID_BINDERFS is not set` and
three global devices fixed at build time
(`CONFIG_ANDROID_BINDER_DEVICES="binder,hwbinder,vndbinder"`). The source tree
does contain `drivers/android/binderfs.c`, and its Kconfig text states the
filesystem "can be mounted per-ipc namespace allowing to run multiple
instances of Android". Flipping that one symbol therefore requires a working
rebuild-and-boot path that this target has never had.

The A90 has flashed many custom boot images, but all of them reused the **stock
kernel**: `base/kernel` and `v3404/kernel` under the staged
`a90-phase2a-kernel.tBOMsQ` output are byte-identical at 49,827,613 bytes. Only
the ramdisk changed. A self-compiled `Image` is new cargo for this target, and
the S22+ experience — where a host-toolchain mistake produced a silent boot
loop — is the reason the format checks below are recorded explicitly.

## Source identity

The OSRC package was acquired by the operator through the human-verification
step and staged privately as
`workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource_13272/`.

- `Kernel.tar.gz` SHA256
  `403fdc49f086d238c01a796c390083c3c47c1754c218e228f29b55cc7c35d554`,
  transferred to the build host and re-hashed there to the same value.
- Extracted tree reports `VERSION 4 / PATCHLEVEL 14 / SUBLEVEL 190`, matching
  the staged runtime configuration.
- Board defconfig `r3q_kor_single_defconfig` is present; `r3q` is the A908N
  codename named by `README_Kernel.txt`.

The generated `.config` was cross-checked against the device-derived
configuration and agrees on every symbol examined, including
`CONFIG_ICNSS=y`, `CONFIG_ICNSS_QMI=y`, `CONFIG_QCA_CLD_WLAN=y`,
`CONFIG_CNSS_UTILS=y`, `CONFIG_CNSS_GENL=y`, `CONFIG_QRTR=y`,
`CONFIG_MSM_PIL=y`, `CONFIG_LOG_BUF_SHIFT=17`, `CONFIG_NR_CPUS=8`, and
`# CONFIG_ANDROID_BINDERFS is not set`. That agreement is the strongest
available evidence that this source corresponds to the installed build.

## Four blockers and how each was cleared

The build host is a Debian 13 machine with no passwordless `sudo`. Every
resolution below stays inside operator-owned directories; **no system package
was installed and no system setting was changed**.

### 1. Missing `bc`, `bison`, `flex`

Modern Debian lacks them here, and `apt` requires a password that must not be
entered on the operator's behalf. The S22+ GKI build had never needed them
because that build ships hermetic tools in
`kernel_platform/prebuilts/build-tools/`; the A90 4.14 tree is pre-GKI and uses
system tools instead.

Those same AOSP hermetic binaries were copied from the retained S22+ tree and
placed on `PATH`: `bison 3.5`, `flex 2.6.4`, `m4`, and `gavinhoward-bc 4.0.1`
symlinked as `bc`. `bison` additionally required `BISON_PKGDATADIR` and an
explicit `M4` variable; without the latter it fails with
`m4 subprocess failed` even when `m4` is on `PATH`.

### 2. Missing `python`

`scripts/gcc-wrapper.py` carries a `#!/usr/bin/env python2` shebang and
`Makefile:393-398` wraps the compiler as `$(PYTHON) gcc-wrapper.py $(REAL_CC)`.
Python 2 reached end of life in 2020 and is unavailable through Debian 13.

The compiler wrapper was bypassed by setting `CC=clang` on the command line,
which overrides the Makefile assignment. Separately,
`scripts/link-vmlinux.sh:477` invokes `python` directly for a post-link step;
that was satisfied with the AOSP `py2-cmd` binary — a genuine Python 2.7.15 —
symlinked as `python`.

### 3. Missing `ld.gold`

`Makefile:379-381,681` selects `LD := $(CROSS_COMPILE)ld.gold`. GNU gold was
removed from binutils by 2.44, so the host has no aarch64 gold at all.

Two substitutes were tried and both failed at `vmlinux`:

| linker | outcome |
|---|---|
| GNU bfd 2.44 | `dangerous relocation: unsupported relocation` |
| LLVM lld 12 | `relocation R_AARCH64_ABS32 cannot be used against symbol __crc_gsi_write_channel_scratch; recompile with -fPIC` |

The lld message identified the real mechanism. `genksyms` fails to produce a
CRC for exactly one exported symbol, `gsi_write_channel_scratch`, whose
parameter is a large by-value `union __packed gsi_channel_scratch`. Its
siblings succeed: `nm` shows `A __crc_gsi_write_channel_scratch2_reg` and
`A __crc_gsi_write_channel_scratch3_reg` against a bare
`w __crc_gsi_write_channel_scratch`. Because `CONFIG_RELOCATABLE=y` and
`CONFIG_RANDOMIZE_BASE=y` force a PIE link, both modern linkers reject an
`ABS32` relocation against that weak undefined symbol.

Gold 1.12 (binutils 2.27) tolerates the pattern, which is why the vendor
Makefile names it. It was obtained from the public AOSP prebuilt
`platform/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9`, branch
`android-msm-coral-4.14-android12-qpr3` — a 4.14/Android 12 branch matching
this kernel's generation. The archive is 28 MB. The repository default branch
holds only an `OWNERS` file; the toolchain lives on release branches.

With gold, `LD vmlinux`, `SYSMAP`, and `System.map` all succeeded.

### 4. `CONFIG_RKP_CFP` requires a compiler that is not published

After a successful link, `scripts/rkp_cfp/instrument.py` aborted with
`KeyError: 'jopp_springboard_blr_x16'`.

`Makefile:824-840` explains it. Under `CONFIG_RKP_CFP_JOPP` the build adds
`$(call cc-option, -mllvm -cfp-jopp)`, and `CFP_CC` defaults to
`$(srctree)/toolchain/llvm-arm-toolchain-ship/10.0/bin/clang`. Two facts close
the option:

1. the OSRC package contains **no `toolchain/` directory** — Samsung did not
   ship the compiler it references;
2. AOSP clang rejects the flag outright: `Unknown command line argument
   '-cfp-jopp'`.

Because the flag arrives through `cc-option`, an unsupporting compiler drops it
**silently**. The build then completes without emitting the JOPP springboards,
and the instrumentation pass fails only afterwards, when it cannot find them.

## The authorized deviation

Samsung's RKP CFP (JOPP/ROPP control-flow protection) cannot be reproduced
without Samsung's patched LLVM, which is not distributed. The operator was
presented with this and authorized disabling it.

The deviation from the device-derived configuration is **exactly three
symbols**, recorded by diffing against a retained `out/.config.stock`:

```
- CONFIG_RKP_CFP=y            → # CONFIG_RKP_CFP is not set
- CONFIG_RKP_CFP_JOPP=y       → # CONFIG_RKP_CFP_JOPP is not set
- CONFIG_RKP_CFP_ROPP=y       → # CONFIG_RKP_CFP_ROPP is not set
```

`System.map` confirms the intended scope and nothing wider: `rkp_cfp`,
`jopp_springboard`, and `ropp_` occur zero times, while `rkp_init` and
`uh_call` remain present. The RKP hypervisor layer and `CONFIG_UH_RKP`,
`CONFIG_RKP_KDP`, `CONFIG_RKP_NS_PROT`, `CONFIG_RKP_DMAP_PROT` are untouched.

**This lowers the device's security posture and should be recorded as such.**
JOPP/ROPP is kernel exploit mitigation. Three points bound the judgement, and
none of them is a claim that the loss is harmless:

- It is a hardening layer, not a functional one. No boot, driver, or WLAN path
  depends on it.
- The S22+ precedent does **not** transfer. That target did not disable the
  feature; the 5.10 GKI tree has no `scripts/rkp_cfp/`, no `RKP_CFP` Kconfig,
  and no such config entries at all. Samsung dropped CFP in the GKI transition,
  presumably because GKI must build with stock AOSP toolchains.
- Samsung therefore ships current flagships without it, so it is not required
  for a Samsung device to operate. That is context, not equivalence: the A908N
  shipped **with** it, and removing it is a real reduction on this unit.

The deliberate reading is that Option C's containment boundary and this
mitigation address different layers — CFP constrains an attacker already
executing in the kernel, while the isolation boundary is intended to deny
reach. A future design may argue the trade explicitly; this report does not
make that argument, and no such compensation is proved.

## Artifacts and format verification

The build completed with `BUILD_EXIT=0`, 4015 compiled objects, and no errors.

```
Image        48,826,384  sha256 6cab67938d2d235ad5ad965abaefe7e3ebda6d13b57251705c91f5f333ab1b6d
kernel blob  49,823,517  = "UNCOMPRESSED_IMG" + u32 image size + Image + stock DTB region
```

The `Image` is the durable product of this report. The boot image first packed
around it — pairing this kernel with the resident's own ramdisk, sha256
`7c293af9...` — was **later deleted**; see the superseding note below. The
surviving packaging of this kernel is
`boot_a90_base_selfbuilt_kernel_20260816.img`, size 66,375,680, sha256
`2d0be40158d56b6b053bc1aff6c6e149beb904da43a303b812e8ca6c4d583a9e`, which pairs
it with the v3403 base ramdisk and serves as the flat builder's `base_boot`.

`file` reports `Linux kernel ARM64 boot executable Image, little-endian, 4K
pages`, and the ARM64 magic is present at offset 56. This is the check the S22+
silent boot loop taught, and it is recorded rather than assumed.

The version banner reads `Linux version 4.14.190 ... clang version 12.0.5 ...
GNU ld (binutils-2.27-bd24d23f) 2.27.0.20170315`.

WLAN symbols analysed elsewhere in this campaign are present in `System.map`,
including `icnss_probe`, `hdd_init`, `cnss_utils_set_wlan_mac_address`, and
`qrtr_endpoint_register`.

### Device tree was reused, not rebuilt

The stock kernel blob decomposes as a 20-byte `UNCOMPRESSED_IMG` header, a
48,830,480-byte `Image`, and a 997,113-byte trailing region containing three
concatenated DTBs (497,331 / 499,609 / 173 bytes, each opening with
`d00dfeed`).

Our build produced **no** DTBs: `CONFIG_BUILD_ARM64_DT_OVERLAY` is not set in
`.config` — passing it as a make variable does not set the symbol — and every
`r3q` device tree in the tree is an overlay
(`arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r00..r03.dts`)
belonging to the separate `dtbo` path.

The stock 997,113-byte DTB region was therefore carried over unmodified. No
device tree source was changed, so reusing the stock device tree is correct and
also keeps the experiment to one variable: kernel code.

### Boot image parity against the actual resident

The reference must be the installed resident, not a convenient staged image.
`GOAL_A90.md` names H24 `0.11.192` as the exact installed resident, and its
deterministic A/B build output
(`workspace/private/outputs/a90-h24-minimal-debian-dev-ab-20260812-01/`)
carries byte-identical `A/boot.img` and `B/boot.img` at SHA256
`d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782`.

A first attempt at this candidate was packed against the retained
`boot_linux_v3404_d3_resolved_owner_timeout.img` instead. That was wrong. The
resident's ramdisk is 8,537,600 bytes and v3404's is 16,545,280, so that image
would have changed **two** things at once — the kernel and the userspace
lineage — and a boot failure could not have been attributed. It was discarded
and is not staged.

The kernel inside both images is the same stock 49,827,613-byte blob, so the
reused DTB region is the resident's own device tree.

The candidate was repacked with the in-tree AOSP `mkbootimg` using the
resident's ramdisk. Re-unpacking and diffing the two headers yields exactly one
differing field:

```
kernel_size: 49827613   →   49823517
```

Load addresses, tags offset, page size, header version, OS version, patch level
`2023-01`, product name, and the full command line are identical, and the
ramdisk is **byte-identical to the resident**. The `Image` itself is 4,096
bytes — one page — smaller than stock.

A one-page delta is **not** evidence of equivalence. Compiler, linker, and the
three disabled symbols all differ from Samsung's build; the small size
difference is an observation, not a similarity proof.

### The packed image was superseded and deleted

Pairing this kernel with the resident's ramdisk produced an image that is
byte-parity-correct but **contract-invalid as a candidate**:
`A90_TARGET_CONTRACT.md:320-324` requires every replacement candidate to carry a
new build identity with fresh versioned enable/latch paths, and that image
reused H24's. It also could not serve as the flat builder's `base_boot`, because
the builder overlays onto a base ramdisk and rejects an already-built one.

Having no remaining role, it was deleted rather than left staged where it could
be mistaken for a candidate. The kernel it carried is unchanged and is preserved
in the base image named above. The actual candidate is the flat-builder output
`phase3-minimal-h24k`, recorded in
`docs/plans/A90_SELF_BUILT_KERNEL_F1_DESIGN_2026-08-16.md`.

### Bound rollback

`GOAL_A90.md` states that "V2321 remains the exact bound rollback for a future,
freshly qualified successor". The staged
`boot_linux_v2321_usb_clean_identity_rodata.img` is byte-identical to the
`rollback-boot-v2321.img` consumed by prior A90 F1 runs, SHA256
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`. No other
staged image is the bound rollback, and none of the `v33xx`/`v34xx` images
substitutes for it.

## What this does not settle

- **It does not prove the device boots.** No flash has occurred and no F1
  authority exists. A format-valid image can still boot-loop.
- **It does not prove functional equivalence to stock.** A different compiler
  and linker produce a different kernel even where configuration matches.
- **It does not enable `CONFIG_ANDROID_BINDERFS`.** That symbol remains off.
  Flipping it is a separate change on top of a build path that must first be
  proved by booting the unmodified-configuration build.
- **It does not retire any WLAN gate.** `H0D01` through `H0D10` are unchanged,
  and the thirteen roles are unaffected.
- **It does not make the CFP removal reversible by rebuilding.** Restoring CFP
  requires Samsung's compiler, which remains unavailable.

## Related finding recorded elsewhere

Reading the reference boot image header for this work also closed an open item
in `docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md`: the
kernel command line contains `service_locator.enable=1`, so the protection
domain service locator is enabled at boot rather than left at its source
default. That report was updated and its pinned digests regenerated.

## This is not an F1-ready candidate

The artifact is format-valid and now differs from the resident in one field.
That is necessary and nowhere near sufficient. The following preconditions are
**unmet**, and each is independent of the others:

- **No successor candidate is authorized.** `GOAL_A90.md` states plainly: "No
  successor candidate, approval, transfer, reboot, or D1 effect is authorized
  by this goal."
- **No fresh connected D0.** The goal requires "fresh connected D0 and exact
  attended F1 approval before one" candidate. Neither exists.
- **No candidate qualification.** This image has no identity, no approval, no
  transfer plan, and no execution review. It is a build product, not a
  qualified candidate.
- **Attended-only.** The A90 v1 runner is attended-only, and
  `--operator-attended` must never be asserted while the operator is absent.

A separate, reviewed F1 design is required, and it must treat the disabled
RKP CFP as part of what is being accepted, not as a build detail.

## Next bounded units

Host-only work that remains available without new authority:

1. compare the built `System.map` against the device-derived symbol evidence
   already staged for this campaign;
2. decide whether a resident-configuration build (CFP disabled only) or a
   `BINDERFS` build is the first flash candidate — the disciplined order is the
   former, so a boot failure has one fewer explanation;
3. draft the F1 design and its predeclared recovery for separate review,
   including the exact V2321 rollback transfer and the CFP acceptance.

The first flash is an attended F1 with an exact predeclared rollback. It is not
authorized by this report.

## Sources

- private: `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource_13272/`
- private: `workspace/private/inputs/boot_images/boot_a90_base_selfbuilt_kernel_20260816.img`
- private: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- private: `workspace/private/outputs/a90-h24-minimal-debian-dev-ab-20260812-01/`
- `GOAL_A90.md`
- private: `workspace/private/outputs/a90-phase2a-kernel.tBOMsQ/v3404.config`
- `docs/reports/A90_WLAN_KERNEL_SIDE_COMPOSITION_H0_2026-08-15.md`
- `docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md`
- `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`

## Boundary

Produced by host-only compilation on an operator-owned build host reached over
the local network, plus reads of already-staged private artifacts. Device,
`/dev`, USB, S22+, and S20+ contacts are zero. Network use was limited to one
public AOSP prebuilt download; no human-verification bypass occurred. The built
boot image is staged under `workspace/private/` and is excluded from commit by
`workspace/.gitignore`, per the permanent repository and evidence boundaries.
No ordinal, candidate, qualification, approval, or command is created, and no
D0, D1, or F1 authority is granted or implied.
