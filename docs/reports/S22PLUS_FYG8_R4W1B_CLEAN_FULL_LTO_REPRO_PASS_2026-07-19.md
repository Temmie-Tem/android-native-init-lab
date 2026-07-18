# S22+ FYG8 R4W1-B Clean Full-LTO Reproducibility Pass

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: host-only recovery, validation, two clean Full-LTO builds, two static
audits, and one final reproducibility audit. No device was contacted,
enumerated, rebooted, or flashed. No boot artifact was promoted as a candidate,
and no live helper or policy exception was created.

## Source Recovery

The Debian build host retained later R4W1-B provenance hardening that was not in
the restored Git history. Four exact scripts were recovered, reviewed, brought
back into the repository, and covered by focused tests:

```text
build.py       6d35f8e2940e4ff1530297f31bbe525b5240b34f079d39b3a9790755336693e1
elf_audit.py   8bc5a0ad86b5ba3f9cb3d77d0f18d9f8a8d8897622fdf8c6c4c9c6c57e21f3b1
static_audit.py
               200749f9ba0dfe873d5b41839376e446b73f9b9ce79969fef7413128b72cb468
repro_check.py 6b8b128f9f798ba58cecd43dfe31bee29d0e2edf9b57566ef5e3660603e43b8a
patch_check.py 5521e1b232c1615922701bc5f3276476c80db15df9d5c03fd6cda8c8da6ca8e8
patch          cacfdcb5b81d1dede4b41cfe65998038b0e3935cacb16ce43d61db3eb2b5c6a0
commit         e2599c06b0c84d501b6b31b70d2beb852bd37d77
```

The hardening binds a private unprivileged user/mount namespace, zero
capabilities, `no_new_privs`, exact source-overlay identity, an exclusively
created clean output tree, restored source deltas, pinned host tools, FIPS
regeneration inputs, final ELF control flow, and cross-run static manifests.

Focused unit validation passed on both hosts:

```text
current host: 46 tests, OK, 3 source/toolchain-dependent skips
build host:   46 tests, OK, 4 source/toolchain-path-dependent skips
build-host final-a patch integration:
  PASS_R4W1B_HOST_PATCH_CONTRACT
  DT revisions=11, marker bytes=99
```

The build-host integration check used the real `source-r4w1b-final-a` tree;
the skips only keep the same unit suite runnable where the full private Samsung
tree or local AArch64 clang fixture is absent.

## Preflight

An initial v5 preflight intentionally failed closed before creating `out`
because the default restored-workspace toolchain copy was not the required Git
toolchain. It reported `build_allowed=false`, missing effective LLVM tools, and
`clang_verified=false`.

The corrected v6 invocation explicitly selected the previously qualified build
host toolchain:

```text
--clang-repo toolchains/aosp-clang-android12-release
```

v6 then proved:

```text
build_allowed=true
private_namespace_verified=true
cap_eff=0 cap_prm=0 cap_bnd=0
no_new_privs=1
clean_output_verified=true, exists=false
effective_tools_verified=true
clang_verified=true
source_overlay_verified=true
missing_paths=[]
missing_host_tools=[]
```

## Clean Builds

The two builds were sequential, not concurrent, on separate reconstructed
source trees and distinct output/result directories:

```text
A work tree       source-r4w1b-final-a
A elapsed         35:36.51
A max RSS         24,243,364 KiB
A build result    a62458f2503314d085ae162676fcdd196d7c8f72bfea296a882e9fc6000249da

B work tree       source-r4w1b-final-b
B elapsed         37:06.67
B max RSS         24,243,552 KiB
B build result    138cf8cb0ab4454411cd5fbeedda297031e14ec17fa8d0ec354fafb635388cbd
```

Both build results had `returncode=0`, `r4w1b_build_pass=true`, and verified
witness, output, module, source-restoration, clean-output, and exclusive-output
gates. Full builds also emitted normal host packaging outputs under each build
tree; those outputs remain explicitly non-promoted and are not R4W1-B
candidates.

## Reproduced Artifacts

Every load-bearing artifact below matched byte-for-byte across A and B:

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| `Image` | 41,490,944 | `350bc71815a7dbf22caf5d42434e4f99ace846329fd11e599b3be2d9c5e080d3` |
| `vmlinux` | 476,909,328 | `025e1885451133a885afaa8ce0b59014781de0e64c4fb663dcd1f6343e4f637b` |
| `System.map` | 5,072,350 | `53b3f04959d5fb5d1e2770774f5d7c22f390a394f860e2d2a41956dd0a63aef4` |
| `vmlinux.symvers` | 439,646 | `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19` |
| `abi.xml` | 12,787,205 | `3660c592e1884ab323816c09a3abd197744c8b2f78aed890b02c3e69dbc1c55c` |
| `.config` | 185,335 | `9c54c862ac5b6a7f1c29a89041eb027458bc0c1189243bce99cd9ed0eba39efc` |

The reproduced `vmlinux.symvers` and `abi.xml` hashes are the exact pinned R4W1
KMI/ABI baselines.

## Static Audits

```text
A verdict       PASS_R4W1B_STATIC_COMPATIBILITY
A result SHA256 f8f302732ef29adfcc37e425b19acdfe0146276cd7944c829ddf64e325046a0c
A blockers      []

B verdict       PASS_R4W1B_STATIC_COMPATIBILITY
B result SHA256 f881e438bfd5cf858b78a9c3f1c0edb26cec698363c91e5add695d69f765355f
B blockers      []
```

Both audits proved:

- exact ARM64 Image header and whole-Image PT_LOAD derivation from `vmlinux`;
- one exact R4W1-B marker in Image and ELF, with no historical family marker;
- one exact `kernel_execve("/init")==0` success edge and no unsupported control
  transfer in the audited region;
- exact System.map symbol binding;
- exact FIPS range/HMAC projection and independent generator reproduction;
- exact full symbol CRC and ABI definitions;
- `sec_log_buf` remains a loadable module, preserving single-writer timing;
- exact 41,492,480-byte aligned slot, 41,490,944-byte Image, and 1,536-byte
  remaining gap before the fixed ramdisk start.

## Final Reproducibility Gate

```text
schema          s22plus_fyg8_r4w1b_repro_check_v1
verdict         PASS_R4W1B_CLEAN_REPRODUCIBILITY
result SHA256   1b1124c828243772cb48cf8aa7f6667e88cd9ac5443164e2042243510d833eb1
blockers        []
reproducible    true
```

The checker additionally proved distinct build-result paths, distinct static
result paths, distinct work-tree identities, distinct inode/path bindings for
all six compared artifacts, equal effective tool fingerprints, equal FIPS
HMAC, and byte identity for Image, config, symbol CRCs, ABI, vmlinux, and
System.map.

## Interpretation

This closes the R4W1-B source/build/static/reproducibility prerequisite. It does
not prove device boot, retained-ring survival, direct PID1 execution, EL0 entry,
USB, Debian, or rollback. It also does not authorize candidate construction or
live work by itself.

The next bounded unit is host-only: construct and statically audit a raw
R4W1-B boot candidate by replacing only the selected M4T2 kernel interval with
the exact reproduced Image while preserving the 1,536-byte gap and every byte
outside that interval. AP packaging and any live policy remain separate later
gates.

Verdict:

`PASS_R4W1B_CLEAN_REPRODUCIBILITY; CANDIDATE_CONSTRUCTION_NEXT; NO_LIVE_AUTHORIZATION`
