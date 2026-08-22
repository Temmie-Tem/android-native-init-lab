# A90 H34 RTIC MP / stale-DTB host causal analysis — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only analysis
Device contact: none
Authority: no D0, D1, F1, candidate, rollback, reboot, or live authority
Disposition: proved artifact defect; strongest H34 boot-loop cause candidate;
exact device causality remains unproved

## Result

H34 is not a configuration-zero reconstruction of the stock boot kernel. Its
rebuilt Image omits Qualcomm RTIC measurement parameters (`rtic_mp`), while its
copied stock DTB tail still contains the stock RTIC DTB. That 173-byte DTB
binds a virtual address, Image offset, byte count, and SHA-256 for the stock
measurement parameters. The bound stock hash matches the stock bytes exactly
and necessarily mismatches the H34 bytes at the same address.

This is a deterministic host-side inconsistency in the exact H34 kernel blob,
not an inference from the boot loop. Qualcomm's own kernel change describes
MPGen as embedding kernel measurement parameters for consumption by the RTIC
trusted application. The mismatch is therefore the strongest current causal
candidate and is sufficient to reject another candidate made by copying the
complete stock DTB tail onto an MPGen-free Image.

It does **not** prove that the RTIC trusted application caused the observed
H34 boot loop. The retained recovery log contains multiple boots and no
candidate-attributable H34 terminal record. Exact A90 RTIC enforcement and the
first failing boot stage remain unproved until either a candidate-specific
log closes attribution or a self-consistent MPGen rebuild changes the result.

## Live record being explained

The consumed H34 transaction is not replayable:

- exact H34 boot bytes were written and their boot-partition prefix read back;
- the sole candidate System-return request was confirmed;
- no H34 Native health was observed before recovery;
- exact V2321 rollback bytes were then written and read back;
- the sole rollback System-return request was uncertain and was not resent;
- terminal state is `RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`;
- H34 candidate replay is false.

The operator subsequently reported a boot loop and recovery return. The last
proved device health remains older V2321 evidence; present V2321 health is
unproved. This report sends no command and changes no live state.

## H24-to-H34 differential

The exact known-good H24 and failed H34 boot artifacts were unpacked directly.

| Surface | Result |
|---|---|
| boot header and mkbootimg semantics | identical |
| kernel wrapper size | identical: 49,827,613 bytes |
| raw Image size | identical: 48,830,480 bytes |
| appended DTB tail | byte-identical |
| ramdisk size and 31-entry path/metadata shape | identical |
| ramdisk content delta | only `/init` differs |
| init source closure | identical; version/build/state-path identity differs |

The known-good H24/V2321 carrier wrapper is
`d97eb6c7291477000299fae1c4272105e95fe77df09631ae13099303510b5263`.
The H34 rebuilt wrapper is
`59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac`.
Their DTB tails are identical, but their Images are not.

The known-good carrier Image SHA-256 is
`49e7d9040d2b8df90f74b56c19b4f15a535f7ff830b08bcf4c14f89d0651c88d`;
H34's is
`6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557`.
About half of their raw bytes differ. Equal size, banner, DTB, and IKCONFIG are
therefore format/configuration evidence, not semantic or production-transform
equivalence.

## The third appended blob is a valid RTIC DTB

The known-good carrier wrapper has three consecutive, size-valid FDTs:

| index | wrapper offset | size |
|---:|---:|---:|
| 0 | 48,830,500 | 497,331 |
| 1 | 49,327,831 | 499,609 |
| 2 | 49,827,440 | 173 |

The 173-byte third object consumes the exact remainder of the wrapper and
decompiles as a valid tree with `qcom,rtic-id = <1>` and one `MP_DATA`
property. It is not a stray magic match. This corrects the narrower statement
in `ESOC_DTB_PARITY_2026-06-02.md`; that report's comparison of the first
two hardware DTBs is unaffected.

The public MPGen source defines `MP_DATA` as this packed payload:

1. 64-bit RTIC MP virtual address;
2. 64-bit offset from `.head.text`;
3. 32-bit RTIC MP size; and
4. 32-byte SHA-256.

Decoding the stock property yields:

| Field | Stock RTIC binding |
|---|---|
| virtual address | `0xffffff8009f00000` |
| raw Image offset | `0x01e80000` |
| byte count | `0x658` (1,624) |
| expected SHA-256 | `26178df5bc4bff79726c4bea05fb8ee553899649a71902552a998f3db84ab90a` |

The stock `System.map` has `rtic_mp` at exactly
`0xffffff8009f00000`. The 1,624 stock bytes begin with
`--==!!!RTIC MP!!!==--`, name MPGen `2.7.ef86a6.30`, encode interface
`30.3`, and hash to the DTB value exactly.

H34 has no `rtic_mp` symbol or marker. Its unrelated 1,624 bytes at raw offset
`0x01e80000` hash to
`5943e1678d7d3e9255d7faefc52db7436a5958577cefbd75f500b0fe2b12d63b`.
The copied stock DTB still demands the stock hash. The mismatch is exact.

The host-only guard
`workspace/public/src/scripts/revalidation/a90_rtic_mp_consistency.py` now
parses this binding without `dtc`, a subprocess, or device contact. It requires
exactly one unambiguous RTIC DTB, validates the virtual-address/Image-offset
relation, confines the MP range to the raw Image, and binds the marker,
interface `30.3`, and SHA-256 to the measured bytes. Against the retained exact
artifacts it reports:

| Input class | Decision | RTIC byte result |
|---|---|---|
| known-good H24/V2321 carrier | `PASS` | expected hash equals actual hash |
| H34 rebuilt kernel wrapper | `FAIL` | hash, marker, and interface mismatch |

The guard has synthetic malformed/ambiguous-input coverage as well as the two
optional retained-artifact checks. It is a static H0 rejection gate only and
grants no candidate or live authority.

## Why the rebuild omitted it

The matching A908N source makes RTIC MP generation conditional on the
`RTIC_MPGEN` environment variable:

- `scripts/link-vmlinux.sh:239-255` invokes MPGen and compiles generated
  `rtic_mp.c` into an aligned object;
- `:363-366` adds that object before kallsyms/final link;
- `:425-437` regenerates it against the final symbol layout; and
- `:462-468` emits `rtic_mp.dts` for the appended RTIC DTB.

The selected build-C log records CFP instrumentation and FIPS HMAC insertion,
but records no MPGen invocation or RTIC MP generation. `RTIC_MPGEN` was not
effectively bound, and the selected System.map lacks `rtic_mp`. The build still
exits zero because the source deliberately treats absent MPGen as an optional
build environment, not because the resulting image is equivalent to a
production image that carries RTIC metadata.

The upstream Qualcomm commit that introduced this path states that MPGen
generates and embeds kernel measurement parameters and that the RTIC trusted
application consumes them:
<https://android.googlesource.com/kernel/msm/+/12e1b34f97ed136cd3161a7748f2bd54f39de0d8%5E%21/>.

A [public Qualcomm BootLib implementation](https://github.com/tadiphone-caf/bootable_bootloader_edk2/blob/e63da7af4ea0a9f6b0ff24e6a193210b14894ffe/QcomModulePkg/Library/BootLib/Rtic.c)
also parses this exact root `qcom,rtic-id`/`MP_DATA` ABI, joins it with the
kernel load address, and sends it to QHEE through
`HYP_NOTIFY_RTIC_DTB_LOCATION`. That source proves the property is active
boot metadata in the Qualcomm design, not an unused trailer. It is not proof
that the exact Samsung A90 ABL binary implements identical code or that QHEE's
response caused H34's observed return; those remain target-specific unknowns.

## Available MPGen and the remaining provenance gap

The same public Qualcomm vendor dump family used to locate Snapdragon LLVM
also contains `qrsp/mpgen`. Two host-inspected public variants matter:

- a [public 2.7 variant](https://github.com/tadiphone-caf/vendor_qcom_proprietary/tree/9a79e3c6b709ced2c53befa46628395989d8892b/qrsp/mpgen)
  reports interface `30.3` and local content version `2.7.48ef28.30`;
- the [already selected public 2.8 variant](https://github.com/comprehensive9/vendor_qcom_proprietary/tree/36fc163a534963a5b3af52186af5efcc63401ad2/qrsp/mpgen)
  reports interface `30.3` and local content version `2.8.4b5c1b.30`.

The stock MP uses the same `30.3` structure interface but names tool content
`2.7.ef86a6.30`. Exact stock MPGen source bytes have not been located. The
public 2.7 implementation is therefore a credible next H0 build input, not an
exact-stock-tool proof. Its generated object, catalog warnings, interface,
address, size, hash, and DTB must be measured rather than assumed.

## Other build warnings

Two visible warnings are secondary to the proved RTIC inconsistency:

- `kperfmon` did not collapse to its dummy implementation. The released tree
  already contains `include/linux/perflog.h` and `olog.pb.h`; the rebuilt
  System.map and Image contain `kperfmon_init`, read/write, `_perflog`, and
  `perflog_evt`. Failed attempts to copy a workspace header were noisy but not
  evidence that kperfmon was omitted.
- `secgetspf` is absent from the standalone workspace. Its three product
  queries affect SEP-version flags, a fingerprint conditional, and one WLAN
  MIMO define. Those remain reproducibility gaps and must be bound for a full
  production rebuild. They do not explain the already proved stale RTIC hash;
  the WLAN MIMO branch is not an earlier boot-acceptance path.

The new module-signing certificate also remains a known non-stock difference,
but the narrow Native ramdisk loads no external module. The next section
separates that later compatibility risk from early boot acceptance. None of
these findings retires the need to inspect the secondary inputs if an
RTIC-consistent kernel still fails.

## Module-signing certificate hypothesis

The available code does not support the hypothesis that the bootloader rejected
H34 merely because Kbuild generated a new module-signing certificate.

Host extraction of the compiled-in certificate list from the known-good stock
Image and direct inspection of the build-C output produced this comparison:

The extracted stock kallsyms map places `system_certificate_list` at
`0xffffff800a701d00`, raw Image offset `0x02681d00`; the adjacent size symbol
reports 1,357 DER bytes. OpenSSL parses that exact bounded byte range as the
stock certificate below.

| Field | Stock kernel | H34 rebuilt kernel |
|---|---|---|
| subject | `CN=Build time autogenerated kernel key` | same generic subject |
| key type | RSA 4096-bit | RSA 4096-bit |
| SHA-256 fingerprint | `8fe91927138761f729152cf6271c42523e7c098b616b3c098d0a804e5c7462e3` | `c773e5d46d151f8e10e966c1fbeba21dd49213dc80d057ecc9a7e200a8bc26db` |
| provenance | Samsung's 2023 stock build | locally autogenerated in build C |

The identical common name is a Kbuild default, not key identity. The stock
Image contains only the public X.509 certificate; its corresponding private
module-signing key is not present in the image or released OSRC. Build C lacked
that private key, so the source's default `certs/Makefile` generated a new
keypair. `certs/system_certificates.S` then embedded the new public certificate
in H34's `system_certificate_list`.

The executable Linux path is narrower than a boot-image signature check:

1. `certs/system_keyring.c:138-189` imports the compiled-in X.509 list at a
   `late_initcall`. Even malformed-list and key-import errors are logged and
   the function returns zero; this path does not reject the kernel image.
2. `kernel/module.c:312` enables strict module policy from
   `CONFIG_MODULE_SIG_FORCE`.
3. `kernel/module.c:2836-2863` verifies a signature on a candidate module.
4. The only relevant call in `load_module()` is at `:3752`, reached from the
   `init_module()` or `finit_module()` system calls at `:3929-3973`.
5. The exact H34 ramdisk contains zero `.ko` files, and the compiled H34 init
   closure contains no direct `init_module`/`finit_module` syscall path. There
   is no retained evidence of any external-module load before recovery.

The [Linux module-signing documentation](https://www.kernel.org/doc/html/next/admin-guide/module-signing.html)
agrees with that code: the public key is built into the kernel and signature
enforcement occurs when an external module is loaded. Therefore the direct
`NEW_MODULE_KEY_REJECTED_BY_BOOTLOADER` explanation is **not supported by the
available path**. The new key remains a real later hazard: with
`CONFIG_MODULE_SIG_FORCE=y`, a stock external module signed only by the stock
private key will not validate against H34's new built-in public key.

Android Verified Boot is a separate bootloader trust layer. The
[AOSP boot-flow documentation](https://source.android.com/docs/security/features/verifiedboot/boot-flow)
describes unlocked devices as the `orange` path; it does not make the Linux
module key an AVB root of trust. Exact Samsung A90 ABL/TZ/HYP code is not in the
available source, so a proprietary whole-Image measurement that includes the
certificate bytes remains unproved. Such a path would be measuring changed
kernel bytes, not invoking Linux's module-signature verifier.

RTIC is the named source-backed example of that distinct measurement class.
Qualcomm's [MPGen change](https://android.googlesource.com/kernel/msm/+/12e1b34f97ed136cd3161a7748f2bd54f39de0d8%5E%21/)
says the generated measurement parameters are consumed by the RTIC trusted
application, and a public [Qualcomm BootLib implementation](https://github.com/tadiphone-caf/bootable_bootloader_edk2/blob/e63da7af4ea0a9f6b0ff24e6a193210b14894ffe/QcomModulePkg/Library/BootLib/Rtic.c)
passes their DTB location to QHEE. H34's proved stale RTIC binding is therefore
a materially stronger early-boot cause candidate than its different module
certificate. Exact device causality remains unproved.

## Historical recurrence

V773/V774 in May followed the same broad construction: an OSRC-built Image
received the complete stock DTB tail, transfer/readback succeeded, Native was
not reached, and recovery remained available. V775 recorded that the custom
kernel had one fewer coarse `RTIC` marker than stock and named production
transforms/RTIC metadata as an unresolved suspect. Its classifier counted FDT
magic but did not parse the 173-byte RTIC DTB or validate `MP_DATA` against the
new Image.

H34 reproduces the missing-marker shape with exact stock/rebuilt bytes now
available, and closes the formerly coarse signal into a concrete stale-hash
defect. Historical V774 causality remains unproved because its diagnostic
kernel bytes are no longer in the current evidence set.

## Exact next sequence

1. Keep H34 consumed; do not replay it and do not create another candidate
   from the current MPGen-free kernel blob.
2. On the build host, rebuild from the same pinned source/config/compiler/gold
   inputs with the public 2.7 MPGen path bound. Preserve the complete vmlinux,
   generated `rtic_mp.c`, `rtic_mp.dts`, RTIC DTB, System.map, Image, config,
   and build log.
3. Retain the first two stock hardware DTBs, but append the newly generated
   RTIC DTB. Do **not** copy the complete three-DTB stock tail, reuse the
   stock 1,624-byte MP, or strip RTIC as a shortcut; the MP describes the
   exact rebuilt kernel and remains a security input.
4. Before any candidate identity, mechanically require one valid RTIC DTB and
   prove that its address/offset/size select an in-Image RTIC marker whose
   SHA-256 equals `MP_DATA`. Also require interface `30.3` and zero fatal MPGen
   catalog warnings.
5. Compare the resulting symbol/layout deltas and use the unchanged functional
   Native ramdisk lineage for one fresh, non-replayed boot canary only after
   ordinary qualification and attended F1 preparation.
6. If that self-consistent kernel still fails, then acquire the exact matching
   ABL plus TZ/HYP artifacts and perform the enforcement-path analysis. BL-only
   extraction is not the next discriminator because the boot image already
   contains a proved RTIC producer/consumer mismatch.

The next unit is therefore **H0 MPGen reconstruction and RTIC self-consistency
validation**, not another F1 and not BL-first reverse engineering.

## Boundary

This report used existing private host artifacts, matching OSRC source, and
public source repositories. It contacted no device, `/dev`, USB endpoint,
ADB server, recovery, serial path, or A90 network service. It grants no device
or candidate authority. S22+ and S20+ were not contacted and supply no A90
evidence.
