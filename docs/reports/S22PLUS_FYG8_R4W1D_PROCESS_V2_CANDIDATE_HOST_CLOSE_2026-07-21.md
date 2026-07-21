# S22+ FYG8 R4W1-D Process v2 candidate host close

Date: 2026-07-21 KST
Scope: HOST-ONLY
Status: candidate packaging and offline D0 passed; connected D0 and F1 not authorized

## Decision

R4W1-D is packaged from the exact reproducible kernel Image and exact R4W1-C
watchdog carrier. The candidate path reuses the existing fixed-interval
packager, independent checker, and Process v2 data manifest. It adds no live
helper, policy exception, partition primitive, or transport behavior.

The R4W1-D kernel is intentionally not booted first with Android `/init`. Its
proof token has one meaning: successful execution of the intended native
`/init` as PID 1. An Android-init qualification boot with the same kernel would
contaminate the retained observer and make a later marker non-exclusive. The
already completed R3C1 result remains the evidence that a source-matched rebuilt
FYG8 kernel can boot Android normally.

## Pinned inputs

- watchdog carrier boot: 100,663,296 bytes, SHA256
  `fc10d94eb0e41a97b40d657e320f8f815870a41b7a6b6df0bc7a51b540a2fe57`;
- effective watchdog `/init`: 65,984 bytes, mode `0750`, SHA256
  `6bf7c60ca8f9b9561a9d38f0591028b23291595dd224853015807993ce97703d`;
- R4W1-D Image: 41,490,944 bytes, SHA256
  `bb768461a55a8ed4b36b4e5777e12e37953fa76fa3703b332b4273d653cbdcd9`;
- reproducibility result: 319,637 bytes, SHA256
  `6abde754a7411168bfd7bd42878efd9d743cd9cace86b113fbfb79294a6f5a60`;
- exact proof token: `[[S22P1D|0e13f28e8558dde01ce3345f16408673]]`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

## Construction and checks

The base R4W1-B builder and checker retain their original defaults. Candidate-
specific schemas, hashes, labels, marker families, and input keys are bound by
small context-managed adapters and restored in `finally` blocks. The candidate
formula remains:

`carrier[:4096] + Image + carrier[41495040:]`

This preserves the Android boot-v4 header, 1,536-byte alignment gap, ramdisk,
opaque tail, and stale AVB footer/vbmeta while replacing only the fixed kernel
interval. Packaging creates one deterministic LZ4 frame and one Odin AP with
exactly one regular member, `boot.img.lz4`.

The independent D checker does not import the builder. It reconstructs the raw
boot from fixed geometry and separately validates the exact carrier, Image,
reproducibility result, stock vendor_boot, and tools. It also proves one exact D
proof and no historical R4W1 family; one effective generic-ramdisk `/init` with
no override or `rdinit=`; exact watchdog init identity and static AArch64 ELF
shape; expected stale AVB behavior; AP consistency; distinct artifact inodes;
and three-way byte identity.

## Results

All three reproductions produced:

- raw boot: 100,663,296 bytes, SHA256
  `18db8c8d8f32b2d128131937865454af50ab255bc5c922a00ba29d0d0b0e6fa0`;
- LZ4 frame: 27,056,481 bytes, SHA256
  `e14e245123f049615e06167364e95fb1fa27e86a7b7a28f3a6dac9683a045c0b`;
- boot-only AP: 27,064,361 bytes, SHA256
  `e35cee4c81966f7b3955af60dfb4921edbb9a07f7a10336d6cc9fddfa915d649`;
- build manifest SHA256
  `9037d35ad2515dd0b0595cd71dd2f1e738301180aa5bec05e7b7c513cf6fdd12`.

The independent result is 29,939 bytes, SHA256
`df3e9d0898bed76cf63c1a7efdd21149fbeffe9bfd2f8f64ad44339e785830b9`,
with verdict `PASS_R4W1D_CANDIDATE_THREE_REPRO_STATIC_CONTRACT` and zero
blockers.

The Process v2 draft manifest SHA256 is
`6b70a505ff4acbba94504a1dcd0da378ecfd4e2f6c975eecc4be661cd0335fea`.
Offline D0 validation and plan rendering both bind bundle SHA256
`3a068ce78d045e943b878fa841593baad81c6e92c3153cf06e88bc15001aa498`.
The offline verdict is `PASS_DEVICE_ACTION_D0_V2_OFFLINE_READY`; every authority
flag remains false.

The B regression, D adapter, independent checker, draft-manifest, F1 core, and
D0 suites pass 59 tests. Targeted bytecode compilation and `git diff --check`
pass. `ruff` is not installed on this host.

An independent adversarial review found one medium compatibility regression:
the first parameterization reused the manifest reproduction-input key for the
unchanged B checker v1 result schema, changing its historical
`kernel_reproduction_result` field. Manifest and checker-result keys are now
separate contract values. B explicitly asserts the historical result key and D
asserts its new result key. A fresh full B checker run is byte-identical to its
pre-change result at SHA256
`969b4a5d94660fb07abba95fe2386cb9327c2a0e97167e153a895619c4385d47`.
The 59-test suite passes after remediation. Independent re-review found no
remaining critical, high, or medium issue and returned `GO` for this host-only
commit.

## Boundary and next gate

No ADB/USB enumeration, reboot, Download transition, Odin invocation, transfer,
partition write, or flash occurred. The manifest status is `draft-host-only`,
so Process v2 F1 `--prepare` must refuse it.

The next bounded unit is one freshly approved connected read-only D0 against
this exact bundle. Only after that result is validated may a data-only change
promote the manifest to `ready-for-f1-approval` and create a prepared F1
binding. Candidate transfer still requires a later fresh approval for that
exact binding and includes mandatory exact Magisk rollback.
