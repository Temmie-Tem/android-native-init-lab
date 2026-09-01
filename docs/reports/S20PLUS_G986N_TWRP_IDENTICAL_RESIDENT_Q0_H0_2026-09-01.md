# S20+ G986N TWRP identical-resident Q0 H0 report

Date: 2026-09-01

Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

Status: `H0_PASS_GO_NOT_ACTIVE`

## Outcome

This host-only unit implements a fixed-input static AArch64 backend and a
dormant render-only owner for a future resident-over-byte-identical-resident
`boot` write/readback qualification in the retained T2 recovery.

It does not activate the backend, stage a byte, open a live block node, read
partition content, write, fsync, reboot, invoke Odin, prepare a run, or emit an
approval. No device command was sent in this unit. The target contract records
the proposal as `DEFINED - H0 ONLY - NOT ACTIVE`.

## Exact S20+ inputs

The owner revalidates the exact 2,812-byte metadata-D0 receipt at SHA-256
`46ffd0388fdcf23b46608f1557d9523e9b338316537bc19c45015877eba5f6b7`.
That receipt proves only the current retained-T2 metadata mapping:

- direct boot node `/dev/block/sda23`;
- block inode and sysfs rdev `259:7`;
- `DEVNAME=sda23`, `DEVTYPE=partition`, and `PARTNAME=boot`;
- partition number 23, 131,072 sectors, and 67,108,864 bytes; and
- zero block opens, content bytes, writes, reboots, Odin calls, transfers, and
  commands to other targets.

The D0 receipt explicitly has `f1_authorized=false` and
`direct_block_write_authorized=false`. This H0 design does not change either
fact.

The proposed preimage, source, and readback are all the exact known-good
resident Magisk boot image, 67,108,864 bytes at SHA-256
`d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`.
The retained T2 terminal remains the exact 1,911-byte
`PROVED_T2_RECOVERY_RETAINED` receipt at SHA-256
`da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05`;
its candidate is consumed and supplies no new T2 transfer authority.

The proposed last-resort recovery artifact is the already demonstrated
boot-only Download/Odin AP, 25,835,561 bytes at SHA-256
`1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`.
Its sole regular `boot.img.lz4` member is 25,833,304 bytes at SHA-256
`2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5`.
Those bytes are recovery availability only; this unit grants no Odin use.

## Portable A90 lesson

The relevant early A90 sequence was progressive: read-only sysfs/rdev audit,
opened-fd guard, write-open feasibility, an identical 4-KiB zero-sector write,
then broader content rungs. Its portable safety structure was not the A90 path
or rdev. It was:

1. derive identity from each opened fd;
2. require `PARTNAME=boot`, exact geometry, and an exact preimage before effect;
3. use the already guarded write fd for the write;
4. call `fsync`;
5. re-open and independently guard a fresh O_DIRECT readback fd; and
6. treat interruption as consumed uncertainty, never as permission to replay.

The S20+ backend reimplements that structure using only the newly proved
S20+ `sda23/259:7/23/64-MiB` identity. It imports no A90 target, artifact,
approval, runtime path, or live authority. Whether S20+ should retain an
additional smaller live rung before the full identical image remains a review
question; H0 construction alone cannot decide or skip that gate.

## Fixed backend

The private reproducible executable has no caller argument. Its only accepted
stage is `/tmp/s20plus-g986n-identical-resident-q0`, an exact root-owned mode
`0700` directory containing exactly:

- mode-`0500` `s20plus_twrp_boot_write_q0`, which must be the running
  `/proc/self/exe` inode; and
- mode-`0400` `resident-boot.img`, a direct root-owned link-count-one regular
  64-MiB file.

The backend keeps that source fd open and binds its inode, owner, mode, link
count, size, mtime, and ctime. It hashes the complete source before any target
write fd exists and requires the resident SHA-256.

It then opens `/dev/block/sda23` O_DIRECT and read-only, derives identity from
that fd, requires block rdev `259:7`, `BLKGETSIZE64=67108864`, bounded power-of-
two logical/physical sector sizes, and the exact fixed sysfs uevent/dev/
partition/size fields. It hashes the complete preimage and requires the same
resident SHA-256 before closing that fd.

Only after the source metadata is unchanged does it open the same direct path
O_WRONLY. It repeats the complete opened-fd and sysfs guard and requires the
same alignment. Its sole `pwrite` call site copies exactly 64 MiB from the
already open source in 1-MiB chunks while independently recomputing the source
SHA-256. It then calls `fsync` even when a partial write needs failure
classification. A complete write still fails unless the in-flight source hash
and fsync are exact.

Finally it rechecks source identity, opens a fresh O_DIRECT readback fd,
independently repeats the complete guard, and hashes the complete partition.
Only exact resident SHA-256 produces
`PROVED_IDENTICAL_RESIDENT_WRITE_READBACK`. The backend blocks host-disconnect
signals before inspection/effect, emits no success before completion, never
reboots, and names no other block path.

## Interruption boundary

Identical bytes do not make a torn UFS write safe. Power loss, kernel failure,
or an unmaskable kill during the 64-MiB write can still corrupt `boot`; the
result is intended to be recoverable by the separately armed physical
Download/Odin path, not harmless. This is the principal live hazard.

Accordingly, any future durable write intent consumes the attempt before the
backend is invoked. Missing stdout, ADB loss, partial bytes, fsync uncertainty,
readback uncertainty, or host failure never permits another invocation. The
future owner must remain in Recovery, preserve the guard, and use only a
separately reviewed recovery branch. The current H0 owner implements none of
those live effects.

## Host-only evidence and journal-prefix model

The new evidence model accepts only two complete backend capture grammars:
the exact 15-line success with rc 0, or the exact ordered 10-line failure with
rc 70. Both require empty stderr, canonical ASCII/LF framing, bounded bytes,
fixed schema, zero reboot/other-partition counts, and exact numeric forms.
Success requires the fixed target/rdev/partition/size, resident source and
preimage hashes, 67,108,864 write bytes, successful fsync, and exact resident
readback hash.

Failure stages and counters are cross-constrained. A pre-write stage cannot
claim a write; `write` may report a partial effect; `write-fsync` requires a
complete write and fsync attempt; and post-fsync/readback failures require a
complete write plus successful fsync where applicable. No failure is promoted
to a proved effect, and every parsed backend invocation has replay false.

The model also validates only the canonical prefix
`prepared -> stage-intent -> stage-result -> write-intent -> backend-result`.
Each node has exact keys/types, one 19-digit run ID, monotonic ordinal, exact
predecessor hash, canonical bytes, and fixed payload closure. A backend-result
node is accepted only with the exact raw capture whose size/hash and fresh
strict parse match its payload using canonical-byte equality, so Python
bool/integer equality cannot substitute types. The write-intent source boot
must also equal the prepared recovery boot exactly.

The decisive cut rule is mechanical: a prefix ending at `write-intent`
classifies as `WRITE_OUTCOME_UNPROVED_ATTEMPT_CONSUMED_NO_REPLAY` even with no
capture or result. A later zero-write failure still remains consumed; a partial
write remains outcome-unproved; exact backend success remains pending physical
health and does not authorize System boot. This model publishes no file and
has no connected owner, so durable publication and full continuation remain
separate gates.

## Dormant owner and remaining blockers

The render-only owner binds the complete T2 predecessor, D0 result, target and
common policy, backend source/build/test closure, exact static artifact and
manifest, resident source, and boot-only fallback AP. Its binding SHA-256 is
`7d296f1666bfecd42044fa7dda49483cdcd418fbb7a478c3d98fc71c2be2b018`.
It exposes zero device commands, writes, or transfers and merely reserves the
future approval prefix.

Eight blockers remain explicit:

- the strict backend parser is H0-only and not integrated into a connected
  owner;
- the H0 journal-prefix validator has no durable no-replace publisher or full
  physical/recovery continuation;
- fixed stage/push verification and owned cleanup runner;
- physical no-hook System boot and direct-to-Recovery choreography owner;
- a boot-only Download/Odin fallback freshly bound to the Q0 run;
- target-contract activation;
- final independent `PASS_GO` over the execution-critical closure; and
- one fresh attended preparation and exact short-lived approval.

Even after a future exact backend result, qualification also requires a
physical no-hook System boot, fresh resident Android/Magisk health, physical
direct-to-Recovery return, fresh T2 recovery health, owned-stage cleanup, and
terminal publication before guard release. TWRP's System hook and `misc` write
remain forbidden.

## H0 identities and validation

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| C backend source | 25,151 | `ba79e36822487fdec23909c653bb05540bdced8678fea2a20dba972096378e06` |
| deterministic builder | 16,846 | `57edd59c660faef1a3c39b5fcf6e9eebb1f21d273bb39ac5e63edcf3f9b5949a` |
| backend test | 9,923 | `3e33f3bc0f91c12d2e1162ef1f9ef759dd730a7733da194fea6af8b4a2839086` |
| private static backend | 597,720 | `16271fee5c31ddb34e426b29ae5032e0fe366623eb3114862aac1ea1cc1022b5` |
| private build manifest | 7,517 | `e9b587c558c15cf1367e271f6b05561a40131a680bf5ee299d6e6c75a2ce9d86` |
| dormant H0 owner | 25,040 | `8ac859a91deee1b565896c6e6e16924a5698cbb89e80074de25556091e6054ae` |
| owner test | 13,587 | `824609f8dc4f679ddd06653fe693bbe103ec85c441efb0f2eebb383c264280b7` |
| H0 evidence model | 21,084 | `6ef0ba273c164e4bd4bb3d8aae3c8c2c98d0d72dbbf5279fee8fd00e47321a89` |
| evidence test | 18,326 | `06d724573c0b11697f4ba52d5dfcf0ce4b5c679a771fcda53f3098df0e0b4d06` |

Two independent builds produce the same stripped static AArch64 executable.
ELF audit finds no interpreter, dynamic dependency, undefined symbol, or RWE
LOAD segment. QEMU supplies a forbidden argument and receives the exact
bounded `stage=arguments`, `write_started=0` refusal.

Focused tests currently pass 40/40: 11 backend/builder tests, 15 evidence
tests, and 14 owner tests. They cover fixed target/source/geometry and operation ordering; one
`pwrite` site; forbidden partition/action strings; source, manifest, D0, type,
authority, count, target-contract, symlink, and hardlink mutations; exact
artifact modes and hashes; deterministic rebuild; interruption/no-replay
claims; private-identifier exclusion; and absence of any connected CLI.
`py_compile` and `git diff --check` pass.

Independent hostile safety review returned `PASS_GO` with HIGH/MEDIUM/LOW
`0/0/0`. A final delta review of the fail-closed `nm` audit correction returned
the same result. Both reviews qualify only these H0 bytes and explicitly found
no live authority. The evidence extension's initial hostile review found two
MEDIUM and two LOW issues; canonical typed comparison, prepared/write boot
continuity, and the stale owner description were corrected, while the claimed
`write-fsync` issue was withdrawn after the exact source-drift path was shown.
Final re-review returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`. Therefore the
strongest truthful claim is `H0_PASS_GO_NOT_ACTIVE`.

## Claim boundary

- `PROVED`: deterministic H0 construction, static-ELF properties, source-level
  fixed guard/effect ordering, strict owner binding, and hostile host fixtures.
- `OBSERVED`: the prior D0 metadata receipt and retained T2 recovery evidence,
  each only within its original claim boundary.
- `DESIGNED`: the future one-shot identical-resident qualification and physical
  health/recovery choreography.
- `UNPROVED`: live content read, write-fd feasibility, 64-MiB write, fsync,
  readback, post-write resident boot health, and qualification terminal.
- `NOT AUTHORIZED`: staging, backend execution, block open/content read, boot
  write, fsync/readback, reboot, Odin, P0 candidate attempt, or replay.
