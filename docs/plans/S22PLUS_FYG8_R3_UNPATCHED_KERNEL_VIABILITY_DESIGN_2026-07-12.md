# S22+ FYG8 R3 Unpatched Kernel Viability Design

Date: 2026-07-12 KST  
Target: `SM-S906N/g0q/S906NKSS7FYG8`  
Scope: R3C0 control close plus host-only R3C1 artifact contract

Status: carrier design corrected after an actual MagiskBoot no-change repack;
corrected R1 v3/R2 v2, checker, exact-input audit, and independently reproduced
R3C0 synthetic control artifacts and its attended live control passed with
verified rollback on 2026-07-12. The R3C0 exception is retired. R3C1 host-only
artifacts now independently pass the exact kernel-only contract; R3C1 live
policy and transfer remain separate and unauthorized.

## Decision

R3 tests the **unpatched** R2-GO kernel with the exact FYG8 stock
ramdisk/userspace. It does not use Magisk kernel patches, Magisk ramdisk
semantics, a native PID1, a witness patch, or any security-config change.

Exact-stock analysis found a 528-byte Samsung `SignerVer02` record. An actual
pinned MagiskBoot v30.7 no-change repack writes only the 16-byte
`SEANDROIDENFORCE` marker, but it also recompresses the stock ramdisk and moves
the signature, signer, and vbmeta. R3C0 therefore does not use MagiskBoot as a
generator. It directly creates a synthetic minimal signer differential at the
stock geometry, splitting R3 into two independently rolled-back rungs:

1. R3C0 tests the synthetic minimal signer-normalized stock container with the
   exact stock kernel and ramdisk;
2. R3C1 starts from byte-identical R3C0 bytes and changes only the kernel region
   to the exact R2 Image.

The single proof question is:

> Can the static-stock-equivalent Full-LTO rebuild reach a bounded normal
> Android milestone on this hardware and then return through the pinned
> boot-only rollback path?

This is a kernel viability bit. It is not a complete runtime module-ABI proof,
root proof, native-PID1 proof, retained-witness proof, or Debian bring-up proof.

## Superseded Direction

`S22PLUS_FYG8_MAGISK_BOOT_SEMANTIC_AUDIT_2026-07-11.md` originally selected a
`magisk-equivalent-kernel` as the first live rebuild. The later parallel-lanes
review, R1/R2 close, current `GOAL.md`, and kernel roadmap supersede that order:

1. R3 unpatched stock-userspace viability first.
2. R3B Magisk-equivalent carrier only after R3 and only when rooted measurement
   is needed.

The semantic audit remains authoritative for the known Magisk delta and stale
vbmeta behavior; only its former rung ordering is superseded.

## Pinned Inputs

| Input | Size | SHA256 |
|---|---:|---|
| R1 v3 result JSON | 680,172 | `448f024b9c0d99fcac02cbc6a858a227ca5cb290a44f0616621542994b329c6f` |
| R2 v2 result JSON | 6,756 | `ee935a523270b45c93d2db3e1f21d32b2bf49f3a96965efe5d8df66515964392` |
| unpatched R2 `Image` | 41,490,944 | `9110a7722f28f075c5cb09789710341b44956147fa05867d05e5b3e7d024770d` |
| FYG8 stock `boot.img` carrier | 100,663,296 | `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae` |
| FYG8 stock Odin `boot.img.lz4` | 27,721,802 | `a75dd0285f31a5d18b0d19a0fa8f024f45a3682bb60dcdbfcbef3f654b848b38` |
| known Magisk rollback `boot.img` | 100,663,296 | `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e` |
| Magisk boot-only rollback AP | 23,367,721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |
| stock boot-only cleanup AP | 100,669,481 | `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94` |
| stock DTBO | 8,388,608 | `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c` |
| stock recovery | 104,857,600 | `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4` |
| pinned Magisk v30.7 `magiskboot` | 943,848 | `a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e` |

The full FYG8 stock evidence must also satisfy
`docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`.

The three R1/R2 pins above are locally retained and independently rehashed as
recorded in
`docs/reports/S22PLUS_FYG8_R1V3_R2V2_CLEAN_REPRODUCTION_2026-07-12.md`.

The rebuilt `Image` has the same 41,490,944-byte payload length as the stock
kernel. Equal size reduces layout churn but does not imply byte identity,
signature validity, or bootability.

## Corrected Carrier Finding

The exact 100,663,296-byte stock boot image has this relevant geometry:

- kernel `[4096, 41495040)`, 41,490,944 bytes;
- stock ramdisk `[41496576, 43475543)`, 1,978,967 bytes;
- GKI signature `[43479040, 43483136)`, 4,096 all-zero bytes;
- Samsung signer area `[43483136, 43483664)`, 528 bytes;
- vbmeta `[43487232, 43489344)`, 2,112 bytes;
- AVB footer `[100663232, 100663296)`, 64 bytes.

The signer area starts with `SEANDROIDENFORCE`, `SignerVer02`, FYG8 build
metadata, and signature-like bytes. MagiskBoot v30.7 source detects the first
16-byte marker, writes only those 16 bytes during repack, and updates the
footer's `original_image_size`. The actual pinned no-change repack additionally
changed ramdisk size from 1,978,967 to 1,653,775 bytes and moved the marker to
43,155,456 plus vbmeta to 43,159,552. Its output SHA256 was
`f173500c9c9f2dcbe1272e1e4557c6d5818cbc06ab6484a4d235a4ef0b9dc81f`.
It preserved the exact stock kernel and vbmeta bytes, but it is not the R3C0
two-field differential. The former stop-on-nonidentity and
MagiskBoot-as-R3C0-generator contracts are retired.

Full evidence and checker threat model:
`docs/reports/S22PLUS_FYG8_R3_CARRIER_AND_STATIC_CHECKER_AUDIT_2026-07-12.md`.

## R3C0 Artifact Construction Contract

The completed host-only R3C0 implementation follows this contract:

1. Start from the exact stock `boot.img`, never from a previous native-init or
   Magisk candidate.
2. Construct R3C0 directly from pinned stock bytes. MagiskBoot v30.7 is pinned
   as provenance for the 16-byte marker behavior but is not executed as the
   generator. R3C0 must retain the exact stock kernel and ramdisk.
3. Require R3C0 versus stock to differ only in the 528-byte Samsung signer area
   and AVB footer `original_image_size`. The first 16 signer bytes remain exact
   `SEANDROIDENFORCE`, the remaining 512 bytes become zero, and
   `original_image_size` becomes `43483152`. `vbmeta_offset` remains
   `43487232`.
4. A future R3C1 must start from the exact pinned R3C0 raw bytes and replace
   only kernel `[4096, 41495040)` with the exact R2 Image. Do not perform
   another semantic repack.
5. Require R3C1 versus R3C0 to differ only in that kernel range. Preserve the
   stock ramdisk byte-for-byte. No `/init`, cpio metadata, SELinux file,
   bootconfig, cmdline, vendor_boot, DTBO, or recovery change is allowed.
6. Require each raw image to remain exactly 100,663,296 bytes.
7. Re-parse both outputs and prove their exact rung-specific region contract,
   copied vbmeta blob, footer fields, and expected stale payload digest.
8. Produce one separately pinned Odin container per rung, each containing
   exactly one regular member named `boot.img.lz4`. Deterministic tar metadata,
   exact MD5 trailer, strict LZ4 round-trip, and no-trailing-data validation are
   mandatory.
9. Run offline Odin parse gates against an invalid device path. This checks
   container parsing only and must not contact USB.

R3C0 was independently reproduced twice. Exact pins are recorded in
`docs/reports/S22PLUS_FYG8_R3C0_ARTIFACT_REPRODUCTION_2026-07-12.md`.
This completion does not authorize R3C0 live use or any R3C1 construction.

## AVB And Unlock Caveat

The stock signed vbmeta descriptor authenticates the stock boot payload. R3C0
already makes that descriptor stale by changing the signer/footer shape; R3C1
would additionally replace the kernel. The known-booting Magisk baseline proves
only that this unlocked device accepts one different stale-descriptor image
whose ramdisk and internal layout differ from R3C0. It does not prove that the
synthetic R3C0 shape or any rebuilt-kernel candidate will boot. That unresolved
acceptance question is precisely why a separate R3C0 live control is required.

R3 must therefore report all three facts explicitly:

- copied vbmeta signature blob unchanged;
- boot payload digest mismatch expected;
- candidate acceptance relies on the already-unlocked orange-state path.

It must not claim a newly valid Samsung- or AVB-signed image.

## Future Static Gate

Before any policy activation or device contact, an independent checker must
require:

- exact R1 and R2 result hashes and PASS fields;
- exact retrieved R2 `Image` bytes, release, compiler, Full-LTO config, and
  41,490,944-byte size;
- exact stock carrier, Magisk rollback AP, stock cleanup AP, DTBO, recovery,
  and full-firmware evidence;
- exact 11-region stock geometry including the 528-byte Samsung signer record;
- R3C0 normalization differs from stock only in the declared signer and footer
  fields, while retaining the exact stock kernel and ramdisk;
- R3C1 differs from R3C0 only in the kernel region, whose bytes equal the exact
  R2 Image and differ from stock;
- both rung ramdisks equal stock, with no Magisk or native-init entry;
- no DEFEX, PROCA, RKP, legacy-SAR, config, cmdline, bootconfig, or witness
  transformation;
- candidate size within the 100,663,296-byte boot partition;
- each AP contains exactly one regular `boot.img.lz4` member, a valid exact MD5
  trailer, canonical tar termination, and one strict LZ4 frame with no trailing
  data;
- no active live authorization implied by an offline PASS.

Any zero/multiple input identity, unexpected delta, missing rollback artifact,
oversize image, or parser ambiguity is fail-closed.

## Future Live Gate Contract

This section is a design requirement, not authorization.

### Baseline

Require exactly one normal Android ADB target with:

- model/device/bootloader `SM-S906N` / `g0q` / `S906NKSS7FYG8`;
- `sys.boot_completed=1` and stopped boot animation;
- current boot equal to the pinned known-booting Magisk boot;
- Magisk root healthy for baseline and rollback verification only;
- exact stock DTBO and recovery hashes;
- exactly one Odin endpoint only after an attended Download transition.

### R3C0 Control Milestone

R3C0 uses the stock kernel and stock ramdisk in the synthetic minimal
signer-normalized container. Its PASS requirements are the same bounded Android
identity and stability checks below plus mandatory rollback. It proves only
acceptance of this exact synthetic carrier shape.

R3C0 must run in its own one-shot session and roll back before R3C1 is eligible.

### R3C1 Candidate Milestone

After R3C0 PASS and rollback, a separately authorized R3C1 session may perform
one boot-only candidate transfer and observe for a bounded window. R3C1 PASS
evidence requires all of:

- one authorized ADB target returns;
- `sys.boot_completed=1` and boot animation is stopped;
- model, device, bootloader, and incremental remain FYG8-exact;
- `uname -r` is
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`;
- `/proc/version` reports the expected `build-user@build-host` and Clang
  `12.0.5` identity;
- verified-boot state is recorded, with orange expected but not normalized;
- three bounded stability samples preserve the same identity and boot-complete
  state.

Root, Magisk, direct-PID1 USB, display rendering, audio, Wi-Fi, and a complete
loaded-module census are not candidate PASS requirements. Their absence must
not be confused with the narrow kernel-viability result.

### Mandatory Rollback

Rollback to the exact Magisk boot-only AP is mandatory after candidate PASS or
FAIL. If candidate Android does not expose ADB, the operator physically enters
Download mode. The stock boot-only AP is cleanup-only if the Magisk transfer
fails while one unambiguous Odin endpoint remains.

Final PASS requires normal Android, Magisk root, exact Magisk boot hash, exact
stock DTBO/recovery hashes, and no Odin endpoint. A successful candidate boot
without verified rollback is not an R3 PASS.

## Result Classes

- `PASS_R3C0_NORMALIZED_STOCK_CARRIER_AND_ROLLED_BACK`
- `PASS_R3C1_UNPATCHED_REBUILT_KERNEL_VIABLE_AND_ROLLED_BACK`
- `BLOCKED_R3C1_REQUIRES_R3C0_PASS`
- `FAIL_PRELIVE_STATIC_GATE`
- `NO_PROOF_CANDIDATE_TRANSFER_FAILED`
- `NO_PROOF_NO_CANDIDATE_ANDROID_MILESTONE`
- `FAIL_CANDIDATE_IDENTITY_OR_VERSION_MISMATCH`
- `FAIL_ROLLBACK_NOT_VERIFIED`

No result promotes R3B, R4, native PID1, or Debian automatically.

## Timeline

Each rung's future helper must write only:

```json
{"events":[{"name":"candidate_flash_start","timestamp_utc":"..."}]}
```

Each separate R3C0 or R3C1 session must include exactly one occurrence of each
mandatory phase:

1. `live_session_start`
2. `candidate_flash_start`
3. `candidate_flash_done`
4. `candidate_boot_ready`
5. `rollback_flash_start`
6. `rollback_flash_done`
7. `rollback_boot_ready`
8. `live_session_end`

If the candidate milestone is not reached, `candidate_boot_ready` records the
bounded observation close with explicit no-proof semantics; it must not falsely
claim Android readiness. No `phases_elapsed_sec`, nested phase object, or other
timeline schema is allowed.

## Policy Boundary

Before artifact implementation or live work:

1. retrieve and independently hash the R2 artifact bytes;
2. complete a clean one-shot R1/R2 reproduction or explicitly accept the
   current incremental-close evidence;
3. implement and independently review the checker before artifact generation;
4. construct and independently reproduce R3C0, then pin every source and
   artifact hash;
5. add a fresh narrow R3C0 boot-only `AGENTS.md` exception and obtain explicit
   attended approval;
6. only after R3C0 PASS and rollback, construct/review/pin R3C1 and add a
   separate narrow exception and approval.

This document grants none of those later permissions.

Steps 1 and 2 above are complete for the corrected R1 v3/R2 v2 evidence.
Step 3 is complete. Checker source and input-audit evidence:
`docs/reports/S22PLUS_FYG8_R3_STATIC_CHECKER_SOURCE_READY_2026-07-12.md`.
Step 4 is complete for R3C0 only: two clean private reproductions are
byte-identical and both passed the independent checker. The step-5 helper,
tests, pending exception text, offline gate, connected read-only dry-run, and
two-round adversarial review are source-closed in
`docs/reports/S22PLUS_FYG8_R3C0_LIVE_GATE_SOURCE_READY_2026-07-12.md`.
Step 5 subsequently completed once with durable verdict
`PASS_R3C0_NORMALIZED_STOCK_CARRIER_AND_ROLLED_BACK`; exact result and the
read-only host continuation are recorded in
`docs/reports/S22PLUS_FYG8_R3C0_LIVE_RESULT_2026-07-12.md`. The R3C0 policy and
one-shot state are retired. Step 6 host construction and independent review are
complete: three byte-identical reproductions return
`PASS_R3C1_STATIC_CONTRACT`, recorded in
`docs/reports/S22PLUS_FYG8_R3C1_ARTIFACT_REPRODUCTION_2026-07-12.md`. No R3C1
live helper, exception, approval, or transfer exists; those require a separate
pre-live unit.
