# S22+ FYG8 R4W1-B Minimal Reusable Candidate Pipeline Design

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Status: final host-only architecture design. Implementation has not started.

Scope: reusable host-side construction and independent static qualification of
boot-only S22+ candidates, beginning with R4W1-B. This document authorizes no
device contact, USB enumeration, ADB, Odin transfer, Download transition,
flash, consumed state, timeline, policy activation, or live promotion.

## Decision

Proceed with a **minimal reusable slice**, not a broad candidate framework.

The repeated work in R3C1 and R4W1-A has identified three construction helpers
whose duplication has already drifted and should become canonical for new
candidates:

1. TOCTOU-stable pinned input reads;
2. fixed-interval replacement plus outside-interval equality checks;
3. deterministic single-member boot-only AP construction and marker
   classification.

The load-bearing construction claim and the independent checker must remain
separate. In particular, the builder and checker must not share the formula
that proves the candidate equals the selected carrier with only the intended
kernel interval changed. Sharing that formula would let one bug construct and
approve the same bad image.

Verdict: `GO_WITH_MUST_FIX`. Every MUST-FIX in this document is part of the
architecture, not deferred work.

## Why This Is The Right Amount Of Reuse

The current builders independently repeat pinned reads, ARM64 header parsing,
deterministic AP generation, and the invalid-device Odin gate. The current
checkers also repeat container and header parsing. This creates maintenance
cost without adding independent evidence.

The opposite extreme is also unsafe: one declarative manifest, one shared
geometry object, and one common implementation used by both builder and
checker would turn a shared error into a self-confirming PASS.

The selected boundary is therefore:

- reuse mechanics whose correctness is target-independent;
- duplicate load-bearing target pins in each evidence-producing program;
- independently re-express the construction relation in the checker;
- freeze all historical evidence programs and results;
- add no live capability to the construction package.

This architecture eliminates routine redesign. A new design is required only
when the evidence claim, carrier, partition envelope, boot-image format,
transition path, observer, or trust boundary changes.

## Frozen Evidence

The following remain byte-frozen and are not migrated by this unit:

- R3, R3C0, and R3C1 builders, checkers, tests, manifests, and reports;
- R4W1-A builders, checkers, tests, live helpers, results, and reports;
- R4W1-B kernel build, patch, audit, reproduction tools, results, and reports;
- consumed or retired policy text and state.

The new code uses new filenames, schemas, verdicts, and output directories.
Historical scripts may be used only as read-only fixtures or references.

## Durable R4W1-B Inputs

The builder and checker each carry their own inline copies of the load-bearing
pins. The generated manifest is not the source of these values.

| Input | Required identity |
|---|---|
| M4T2 raw boot carrier | size `100663296`, SHA256 `8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15` |
| qualified R4W1-B `Image` | size `41490944`, SHA256 `350bc71815a7dbf22caf5d42434e4f99ace846329fd11e599b3be2d9c5e080d3` |
| R4W1-B reproduction result | SHA256 `1b1124c828243772cb48cf8aa7f6667e88cd9ac5443164e2042243510d833eb1` |
| M4T2 `/init` | size `544`, mode `0750`, SHA256 `b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12` |
| stock FYG8 `vendor_boot` | SHA256 `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7` |
| `lz4` | size `218696`, SHA256 `91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8` |
| Odin4 | size `3746744`, SHA256 `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b` |
| marker ID | `36dc5462adedcf136176f2ddcfee08a8` |

The exact marker remains the 99-byte record defined in the binding R4W1-B
design. The family prefix is exactly `[[S22R4W1B|`; loose substring matching is
forbidden.

## Fixed Geometry

R4W1-B construction has exactly one replacement interval:

```text
carrier size       100663296
Android header     [0, 4096)
kernel interval    [4096, 41495040)
kernel size        41490944
alignment gap      [41495040, 41496576)  # 1536 bytes
preserved tail     [41495040, 100663296)
```

The builder replaces only `[4096,41495040)`. The independent checker reconstructs
the expected raw boot directly as:

```python
expected = carrier[:4096] + image + carrier[41495040:]
```

No R3/R4W1-A `FYG8_GEOMETRY` post-kernel offset may be reused. M4T2 has a
different ramdisk and therefore different signer, vbmeta, and footer layout.
Everything after the kernel is treated as opaque carrier bytes, with the
1,536-byte gap also checked explicitly.

## File Architecture

All new source files live under
`workspace/public/src/scripts/revalidation/`; tests live under `tests/`.

### Builder-side primitives

`s22plus_boot_slice.py`

This is a side-effect-minimized builder-side module. It contains no target
geometry, artifact path, expected hash, verdict, device command, or live
policy. All bounds and pins are supplied by the caller.

Allowed responsibilities:

- `sha256_bytes` and `sha256_path`;
- `read_pinned_stable`, using one open descriptor and pre-read, post-read, and
  current-path identity checks;
- `parse_arm64_header`;
- `replace_fixed_interval` with exact length and bounds checks;
- `diff_outside_interval`;
- `write_deterministic_boot_ap` for exactly one `boot.img.lz4` member;
- `classify_marker_family`, separating exact, foreign, partial, and duplicate
  records;
- the invalid-device Odin structural gate, fixed to
  `/dev/bus/usb/999/999` and forbidden from enumerating USB.

Only candidate builders import this module. Static checkers do not.

### Checker-side primitives

`s22plus_boot_verify.py`

This is a checker-only module with no construction function and no target
geometry. It may contain carrier-independent parsers needed to inspect already
constructed bytes:

- a checker-local TOCTOU-stable pinned read;
- AVB footer parsing and sealed-memfd `avbtool` execution;
- strict single-member boot tar parsing;
- strict LZ4 frame parsing and round-trip verification;
- generic CPIO entry normalization and duplicate/alias detection;
- ARM64 entrypoint disassembly helpers.

It must not import `s22plus_boot_slice.py`, a candidate builder, or a generated
manifest. Duplication with the frozen R3 checker is intentional evidence
isolation and may be removed only in a later separately qualified migration.

### R4W1-B builder

`build_s22plus_fyg8_r4w1b_candidate.py`

Responsibilities:

- carry exact R4W1-B pins and geometry inline;
- reopen and validate the qualified kernel reproduction result;
- read the exact M4T2 carrier, Image, LZ4, and Odin binaries through stable
  pinned reads;
- require `PATCHVBMETAFLAG` to be absent or exactly false;
- require the Image ARM64 header to match the bytes inserted into the final
  kernel interval;
- replace exactly one fixed interval;
- require the gap and all outside bytes to remain carrier-equal;
- require the final kernel interval SHA to equal the qualified Image;
- require exactly one exact marker and no foreign or partial family record;
- write outputs exclusively into an empty reproduction directory;
- create a deterministic boot-only AP and verify its invalid-device Odin
  structural behavior;
- emit deterministic schema `s22plus_fyg8_r4w1b_candidate_build_v1`.

The builder has no ADB, real Odin-device, USB enumeration, reboot, Download,
flash, timeline, consumed-state, or live-policy code path.

### R4W1-B independent checker

`s22plus_fyg8_r4w1b_candidate_static_checker.py`

Responsibilities:

- carry the same durable pins and fixed geometry as independent inline data;
- never import the builder or builder-side primitives;
- accept three distinct reproduction directories;
- require byte identity for each raw boot, LZ4 member, AP, and deterministic
  manifest across all three reproductions;
- independently reconstruct the expected raw boot with direct slicing;
- require candidate bytes to equal that reconstruction exactly;
- unpack and validate the final AP, LZ4 frame, and raw boot;
- require Android boot header v4, unchanged `kernel_size`, raw kernel format,
  and final kernel header equality to the qualified Image;
- require the kernel interval SHA and exact marker cardinality;
- explicitly require the 1,536-byte gap and opaque tail to equal M4T2;
- require byte-exact preservation of the stale M4T2 signature/vbmeta/footer
  state and the expected failing/stale AVB verification outcome;
- enumerate the generic ramdisk and every exact stock `vendor_boot` fragment
  in boot-v4 composition order;
- prove exactly one effective regular `/init`, UID/GID `0/0`, mode `0750`,
  size `544`, and exact M4T2 SHA;
- reject duplicate entries, symlink/hardlink aliases, path aliases,
  vendor-fragment overrides, and every `rdinit=` override;
- disassemble the complete `/init` entrypoint and require exactly `wfe; b`, no
  interpreter, and no syscall instruction;
- emit schema `s22plus_fyg8_r4w1b_candidate_static_checker_v1` and PASS only as
  `PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT` with `blockers: []`.

The checker may parse the generated manifest for consistency reporting, but no
load-bearing conclusion may be derived only from it.

### Historical fixture checker

`s22plus_fyg8_r4w1b_historical_fixture_check.py`

This host-only checker imports only `s22plus_boot_slice.py`, applies those
builder-side mechanics to exact frozen R4W1-A private reproduction inputs, and
requires the historical raw-boot and AP identities. It emits schema
`s22plus_fyg8_r4w1b_historical_fixture_check_v1` and PASS only as
`PASS_R4W1B_BUILD_PRIMITIVES_R4W1A_FIXTURE`. It neither imports nor edits any
R4W1-A program. Missing private fixture inputs are a qualification blocker.

### Exact test files

- `tests/test_s22plus_boot_slice.py`;
- `tests/test_s22plus_boot_verify.py`;
- `tests/test_build_s22plus_fyg8_r4w1b_candidate.py`;
- `tests/test_s22plus_fyg8_r4w1b_candidate_static_checker.py`;
- `tests/test_s22plus_fyg8_r4w1b_historical_fixture_check.py`.

## Manifest Contract

Each reproduction emits one deterministic `manifest.json`. It is a receipt,
not an input specification and not a trust root.

Required properties:

- no timestamp, hostname, absolute path, inode, output-directory name, or
  nondeterministic field;
- exact schema, target, rung, input size/SHA pairs, geometry, output size/SHA
  pairs, marker classification, and named invariant results;
- `host_only=true`, `device_contact=false`, `device_write=false`,
  `flash=false`, and `live_authorized=false`;
- byte-identical across `reproduction-a`, `reproduction-b`, and
  `reproduction-c`.

The checker must not read the manifest to discover carrier SHA, Image SHA,
marker ID, interval bounds, or PASS criteria. Those values come from its own
inline pins and are compared against the manifest only after independent
verification.

An artifact registry is not introduced in this unit. If added later, it may be
read-only or append-only and may only duplicate `{schema,size,sha256,provenance}`
records. It must never replace inline pins or independent checking.

## Data Flow

```text
durably pinned evidence
  M4T2 raw boot + qualified R4W1-B Image + kernel repro result
  + stock vendor_boot + pinned lz4/Odin
        |
        v
build_s22plus_fyg8_r4w1b_candidate.py  (three fresh processes)
        |
        +-- reproduction-a/{boot.img,boot.img.lz4,odin4/AP.tar.md5,manifest.json}
        +-- reproduction-b/{boot.img,boot.img.lz4,odin4/AP.tar.md5,manifest.json}
        +-- reproduction-c/{boot.img,boot.img.lz4,odin4/AP.tar.md5,manifest.json}
        |
        v
s22plus_fyg8_r4w1b_candidate_static_checker.py
  independent reconstruction + container inspection + final-rootfs proof
        |
        v
result.json
  PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT or blockers[]
```

Each builder run starts with a new exclusive output directory and reopens all
inputs. Reusing a previous output, hardlinking outputs between reproductions,
or overwriting an existing artifact fails closed.

## Test Matrix

### Primitive tests

- valid fixed-interval replacement;
- input-size, replacement-size, bounds, and overlap rejection;
- outside-byte and explicit-gap mutation rejection;
- valid and malformed ARM64 header cases;
- inode, size, mtime, device, and path-target changes during pinned reads;
- deterministic AP identity and exactly one safe member;
- marker exact count `0/1/2`, foreign ID, partial prefix/suffix, and family
  namespace separation;
- invalid-device Odin gate cannot target a real path.

### Builder tests

- synthetic small geometry success;
- wrong carrier, Image, repro-result, LZ4, or Odin pin rejection;
- marker absent, duplicated, foreign, or boundary-partial rejection;
- ARM64 header mismatch rejection;
- `PATCHVBMETAFLAG=true` rejection;
- output-directory preexistence and partial-output rejection;
- source scan proving no `adb`, `fastboot`, real Odin target, USB enumeration,
  timeline, consumed state, or live helper import.

### Independent checker tests

- exact reconstruction success and every one-byte mutation class;
- wrong Image SHA, carrier SHA, gap byte, opaque-tail byte, or header field;
- extra AP member, unsafe member name, bad MD5 trailer, malformed/trailing LZ4;
- stale-AVB expectation changed in either direction;
- duplicate `/init`, aliases, symlinks, vendor override, wrong metadata,
  wrong bytes, `rdinit=`, interpreter, syscall, or extra entrypoint instruction;
- two equal plus one different reproduction;
- source assertion that the checker does not import the builder or
  `s22plus_boot_slice.py`.

### Historical fixture

One host qualification test applies the new builder-side primitives to the
already frozen R4W1-A reproduction bytes and offsets and requires the historical
interval result and deterministic AP identity. It does not import or edit an
R4W1-A script. Private fixture absence is an explicit qualification blocker,
not a silently skipped PASS.

## Implementation Sequence

1. Add `s22plus_boot_slice.py` and focused primitive tests.
2. Add `s22plus_boot_verify.py` and checker-primitive tests.
3. Run the frozen R4W1-A historical fixture qualification.
4. Add the R4W1-B builder with independent inline pins and focused tests.
5. Produce `reproduction-a`, `-b`, and `-c` in fresh private directories.
6. Add the independent R4W1-B checker and adversarial mutation tests.
7. Run the checker over all three real reproductions and emit `result.json`.
8. Run focused tests, relevant frozen regression tests, `py_compile`, and
   `git diff --check`; write a host-only qualification report.
9. Update `GOAL.md` only after the exact PASS result exists.

No live helper, policy clause, consumed state, timeline, candidate transfer,
or promotion is part of this sequence.

## Change Qualification Rules

These rules prevent routine work from triggering another architecture cycle:

| Change class | Required work |
|---|---|
| Documentation or report wording only | document checks and `git diff --check` |
| Builder-side primitive or packaging change | primitive tests, R4W1-A historical fixture, three fresh candidate reproductions, independent checker |
| Checker/parser change only | checker mutation suite and recheck of all three frozen candidate reproductions |
| Candidate inline pin or geometry change | new target-specific rung/design amendment, three fresh reproductions, full independent checker |
| Kernel source, patch, config, toolchain, FIPS, KMI, ABI, or Image change | repeat the complete two-clean Full-LTO kernel qualification before candidate work |
| Carrier, partition, AVB policy, final-rootfs composition, observer, or transition change | new bounded design and adversarial review |
| Any live behavior | separate helper, policy, review, one-shot state, attended approval, and rollback gate under `AGENTS.md` |

R3C1 or R4W1-A migration onto the new primitives is optional and separate. It
requires byte-identical historical reproduction, all frozen evidence gates,
and source-scan test updates. It is not needed to qualify R4W1-B.

## MUST-FIX Closure Checklist

Implementation cannot claim architecture completion until all are true:

1. Manifest and any future registry remain convenience records, never trust
   roots.
2. Builder and checker share no construction formula or interval-equality
   assertion; the checker imports neither builder nor builder primitives.
3. M4T2 post-kernel bytes are opaque and carrier-equal; no old geometry is
   reused, and the 1,536-byte gap is explicit.
4. The unit contains no timeline, consumed-state, live-runner, device-contact,
   or flash capability.
5. Historical evidence programs and results remain unchanged.
6. Stable pinned reads, deterministic AP creation, and marker classification
   are canonical for new builders and covered by adversarial tests.
7. Three fresh reproductions and the independent checker PASS before any later
   live design discussion.

## Final Boundary

This design standardizes the recurring host-side mechanics while preserving
the independent evidence needed for a safety-critical boot candidate. It is
the default structure for the next S22+ fixed-slice candidate. It does not
generalize across devices, partition types, boot formats, or live transitions
without a new bounded design.
