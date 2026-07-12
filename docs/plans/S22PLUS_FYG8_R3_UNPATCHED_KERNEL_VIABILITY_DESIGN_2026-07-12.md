# S22+ FYG8 R3 Unpatched Kernel Viability Design

Date: 2026-07-12 KST  
Target: `SM-S906N/g0q/S906NKSS7FYG8`  
Scope: host-only design; no candidate build, package, device contact, or flash

Status: design complete; corrected R1 v3/R2 v2 re-close and local artifact
retrieval passed on 2026-07-12. Artifact/static-checker implementation, policy
activation, and live work remain separate and unauthorized.

## Decision

R3 first tests the **unpatched** R2-GO kernel with the exact FYG8 stock
ramdisk/userspace carrier. It does not use Magisk kernel patches, Magisk
ramdisk semantics, a native PID1, a witness patch, or any security-config
change.

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

## Future Artifact Construction Contract

Artifact implementation is a separate unit. When authorized, it must:

1. Start from the exact stock `boot.img`, never from a previous native-init or
   Magisk candidate.
2. Use a temporary output directory and run a no-change stock
   `magiskboot unpack -h` plus `repack` parity probe first. If no-change repack
   is not byte-identical, stop and design a separately audited
   container-preserving writer; do not normalize the difference.
3. Unpack the stock carrier and pin the kernel, compressed ramdisk, header,
   4,096-byte boot-signature field, AVB vbmeta blob, footer, and padding.
4. Replace only the unpacked `kernel` payload with the exact R2 `Image`.
5. Preserve the stock ramdisk byte-for-byte. No `/init`, cpio metadata, SELinux
   file, bootconfig, cmdline, vendor_boot, DTBO, or recovery change is allowed.
6. Repack against the original stock image and require a 96 MiB padded boot
   container.
7. Re-unpack the result and prove exact R2 kernel hash, exact stock ramdisk
   hash, unchanged header fields, unchanged boot-signature field, unchanged
   copied vbmeta blob, and no other semantic delta.
8. Produce an Odin container containing exactly one member named
   `boot.img.lz4`. Deterministic tar metadata and LZ4 round-trip validation are
   mandatory.
9. Run an offline Odin parse gate against an invalid device path. This checks
   container parsing only and must not contact USB.

No output hash can be pinned until that future artifact unit is executed and
independently reproduced.

## AVB And Unlock Caveat

The stock signed vbmeta descriptor authenticates the stock boot payload. Once
the kernel is replaced, the copied descriptor is stale even if its signature
still verifies. The known-booting Magisk baseline demonstrates that this
unlocked device accepts one stale-descriptor boot path; it does not prove that
every rebuilt-kernel candidate will boot.

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
- stock no-change repack parity;
- candidate kernel equals R2 `Image` and differs from stock kernel;
- candidate ramdisk equals stock ramdisk, with no Magisk or native-init entry;
- no DEFEX, PROCA, RKP, legacy-SAR, config, cmdline, bootconfig, or witness
  transformation;
- candidate size within the 100,663,296-byte boot partition;
- AP member list exactly `boot.img.lz4`;
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

### Candidate Milestone

After one boot-only candidate transfer, observe for a bounded window. R3
candidate PASS evidence requires all of:

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

- `PASS_UNPATCHED_REBUILT_KERNEL_VIABLE_AND_ROLLED_BACK`
- `FAIL_PRELIVE_STATIC_GATE`
- `NO_PROOF_CANDIDATE_TRANSFER_FAILED`
- `NO_PROOF_NO_CANDIDATE_ANDROID_MILESTONE`
- `FAIL_CANDIDATE_IDENTITY_OR_VERSION_MISMATCH`
- `FAIL_ROLLBACK_NOT_VERIFIED`

No result promotes R3B, R4, native PID1, or Debian automatically.

## Timeline

The future helper must write only:

```json
{"events":[{"name":"candidate_flash_start","timestamp_utc":"..."}]}
```

It must include exactly one occurrence of each mandatory phase:

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
3. implement and independently review the artifact/static checker;
4. pin every resulting source and artifact hash;
5. add a fresh narrow boot-only `AGENTS.md` exception;
6. obtain fresh explicit operator approval while recovery is attended.

This document grants none of those later permissions.

Steps 1 and 2 above are complete for the corrected R1 v3/R2 v2 evidence.
Steps 3 through 6 remain mandatory and incomplete.
