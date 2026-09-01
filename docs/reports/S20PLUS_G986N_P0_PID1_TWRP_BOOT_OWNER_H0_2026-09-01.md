# S20+ G986N P0 PID1 and TWRP boot-owner H0 report

Date: 2026-09-01

Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

Tier: H0 only

Status: `H0_DESIGN_PASS_GO_EXPIRED_BY_TARGET_CONTRACT_DRIFT_NOT_ACTIVE`

Current note: the later P0 Odin owner amendment changed the binding S20+
target-contract bytes. The render-only TWRP owner intentionally retains its
older exact contract pin and therefore now fails closed. Its historical review
remains evidence for the old closure only; it is not a current qualification or
live authority. The 12,614-byte current regression test at SHA-256
`ef38626fdc5118e0d5eafb58049dd61a723f61391e55c8bfc9eb29e22d5c02a7`
preserves the ten old exact-closure cases as explicit historical skips and
passes two current checks: render fails on the changed repository- or target-
contract identity and
the report states the qualification expiry.

## Outcome

The host-only unit now builds one deterministic 64-MiB `boot` candidate whose
ramdisk replaces only `/init` with a 3,584-byte freestanding AArch64 program.
Its runtime entry executes raw `getpid` as its first syscall, accepts only
`pid == 1`, mounts only volatile kernel filesystems, creates one ACM USB
function, and emits one exact PID1 banner. It does not start Android or Magisk.

A separate observer attributes that banner to one exact USB identity and the
prepared physical topology without assuming `ttyACM0`. A third program binds
the exact candidate, resident rollback, retained T2 terminal, current common
and target contracts, risk tiers, Process-v2, and the build/observer closure.
That owner is deliberately render-only: it contains no ADB, Odin, shell,
partition-write, reboot, prepare, execute, or approval input surface.

This is not a live PID1 result and not boot-partition authority. No device was
contacted, no connected inventory was read, and no partition transfer occurred.

## What the early A90 history actually shows

The oldest A90 commit, `54cf98250b`, was not the later proof framework. It
contained a BusyBox initramfs and a short shell `/init` that mounted proc,
sysfs, and devtmpfs, printed a banner, and opened a shell. It was useful first
light scaffolding, but its console text alone did not prove a bound PID1
observation.

The process became progressively stricter:

- `88285ce5f9` added an explicit PID1 guard.
- `a1c78aa137` first built a read-only boot-target auditor; `4ae475ca3c`
  then resolved the authoritative `PARTNAME=boot` sysfs node and produced a
  confirmed path/rdev pin.
- `a5da0da7df` compared the design with TWRP's boot-image path and retained the
  stricter requirements: one opened-fd identity, exact major/minor, PARTNAME,
  size, source hash, fsync, independently guarded readback, and no reboot after
  a failed readback.
- `e568a5b93e` and `fcb93b140f` are later switch-root/Debian PID1 closures;
  they are downstream milestones, not evidence that a new device can skip
  first light or recovery qualification.

The portable lesson is therefore the ordering, not the A90 artifacts or live
authority: minimal observable PID1 first, exact recovery and target binding,
then a separately reviewed one-shot transfer owner. A90 target paths, rdevs,
TWRP hooks, approvals, and evidence do not transfer to S20+.

## P0 candidate construction

The offline base is the known resident-Magisk boot image, 67,108,864 bytes at
SHA-256
`d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`.
The builder proves a no-change Magiskboot repack is byte-identical, preserves
the exact kernel, DTB, boot header, command line, ramdisk membership, and entry
metadata, and replaces only the bytes of `init`.
The builder extracts and hashes every regular ramdisk entry before and after
the patch and after the final repack; all eight non-init entries are byte-exact.

The compiled runtime has no interpreter, dynamic dependencies, undefined
symbols, executable stack, caller input, exec, clone, reboot, module, network,
storage USB, persistent mount, persistent path, or block-device path.
Failure at any stage enters a quiet infinite park.

The exact success banner is:

`S20PLUS_P0_PID1_ACM_V1;pid=00000001;stage=ACM_READY\n`

Its SHA-256 is
`e9ed7e002f060e7ab46a554c2b7d76d5652127d4dbf9a43312277b28bac4522a`.
The hard-coded `pid=00000001` field is accepted only after the raw first
`getpid` syscall returned exactly 1; the observer therefore treats an exact
banner as PID1 evidence, not merely process liveness. It remains insufficient
for F1 PASS without transfer attribution, rollback, and terminal health.

## Exact private artifacts

The artifacts remain ignored under `workspace/private/` and are not committed.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| static P0 `/init` | 3,584 | `0243519e5d092d2b538b3c4e245935d2d149a3f0e8c38c491f413c827d91d4ee` |
| P0 `boot.img` | 67,108,864 | `de889ff6256950b98ad8898f4d646f2229cb41a3d1a42d22af608e72161cbf01` |
| `boot.img.lz4` | 25,722,068 | `09262d23d1b3925f946b7e249ef2f3a8d72745e00fb0ae98f23786a826afb57b` |
| one-member `AP.tar.md5` | 25,733,161 | `2c7b1563e7d340cbe0b1ef16dcc09fe828e1a24237a18c93382b5f61bf0c4cc6` |
| build manifest | 14,574 | `2b8dc91ac01ba374e18c80127b588255efb2eb97ce40d9f22a489ee8798caf0a` |

The AP archive contains exactly one regular `boot.img.lz4` member. It is an
offline derivative only and is not selected by the dormant TWRP owner, which
binds the raw `boot.img` candidate.

## Dormant TWRP boot-owner model

The owner treats the 1,911-byte T2 terminal at SHA-256
`da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05`
as exact retained-recovery evidence. It re-parses the terminal and requires the
proved T2 version, marker, root UID, security values, running adbd, and
`mtp,adb`. It also preserves the fact that the T2 candidate is consumed. The
terminal grants no new T2 transfer, TWRP UI, mount, format, install, backup,
restore, terminal, or block-write authority.

The planned future transaction is intentionally bounded to:

1. Revalidate the same exact S20+ and retained T2 recovery under a new lane.
2. Read-only resolve and bind S20+'s exact boot direct path, major/minor,
   PARTNAME, and size.
3. In a separate reviewed qualification, write the resident image over the
   identical resident image once, prove exact readback, use a physical
   no-hook System boot, return directly to Recovery, and retain the already
   demonstrated Download/Odin recovery path.
4. Stage the exact candidate in recovery tmpfs, no-clobber, and re-hash it.
5. Publish durable intent before one fixed candidate boot write and readback.
6. Use attended physical System boot without the TWRP System hook or `misc`.
7. Observe the exact P0 ACM banner once; uncertainty never replays candidate.
8. Use attended physical direct-to-Recovery return.
9. Publish rollback intent before one exact resident boot write and readback.
10. Re-prove a fresh T2 recovery boot and publish terminal before guard release.

The resident rollback raw boot is 67,108,864 bytes at SHA-256
`d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`.
The already demonstrated Download/Odin fallback remains the boot-only AP at
SHA-256
`1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`.
Neither artifact authorizes a transfer in this unit.

## Activation blockers

The owner cannot become live until all of these are closed together:

- S20+'s direct boot path, rdev, PARTNAME, and exact size are not yet bound.
- The fixed no-input, opened-fd-guarded TWRP stage/write/fsync/readback backend
  does not exist.
- A separate resident-over-identical-resident write/readback qualification has
  not proved that backend on S20+.
- The durable intent, cut recovery, no-replay journal does not exist.
- The S20+ target contract activates no P0 TWRP boot lane.
- The execution-critical backend, journal, boundary, and hostile tests have no
  independent `PASS_GO`.
- No fresh attended preparation or exact short-lived approval exists.

Closing these blockers is a separate contract/review/activation unit. The
existing T0/T1/T2 recovery exceptions explicitly permit no `dd` or direct
block write and cannot be reused for P0.

The owner records each blocker as a named hazard and scope plus objective
retirement evidence and a drift/expiry review trigger. A blocker disappears
only when its named evidence exists; prose or this H0 result cannot retire it.

## Validation

Focused validation passes 28/28:

- P0 builder and artifact closure: 8/8.
- bounded USB observer: 10/10.
- dormant TWRP owner model: 10/10.

The builder performs two independent complete builds and obtains byte-identical
init, raw boot, LZ4, and AP bytes. QEMU self-tests the pure parsing/state
helpers. The final init is identified as stripped static AArch64, and readelf
shows no dynamic section. `py_compile` and `git diff --check` pass.

The independently reviewed public identities are:

| File | Size | SHA-256 |
| --- | ---: | --- |
| P0 C init | 15,549 | `33fd27b2216a870947ccb88da18d0d6aada76f1de9e5f9f4aab7a17a02d2bdd9` |
| deterministic builder | 23,173 | `464878e79347fb82de019ff3297c41c048f75b090f393ca16762beab7d3e46b3` |
| bounded observer | 16,366 | `7343a97da5b54fa30922210e1afb00f0c4699985b6636fe5dd9c553f3fcee8fc` |
| builder test | 13,633 | `34f577a071a9e6a78ddd131fe4d4b2c397ca56b24462e143b42ca2479ed56674` |
| observer test | 12,197 | `524e13a601c0be00fd93935f0c3ea3cccac75559c75e47c11e9cd0dbed9ea2e8` |
| dormant owner | 24,295 | `da063130a6a71f841e2863f5b23d5da35bb5238acb0a2ce1337db4570371c95e` |
| owner test | 11,616 | `37941c605b470deeea33f09bed16981645597ff30188e40a05cd79546c74addd` |

The owner binding SHA-256 is
`695cd96cd2d5b4caeb5ae48b4963172e885839ff6239935f29b937f07fde00a1`.

Independent hostile review historically returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0` for the then-exact closure.
It confirmed the direct-PID1 structure, byte-exact non-init ramdisk closure,
observer attribution, retained-T2 boundary, structured activation blockers,
and absence of a connected command surface. A final delta review of the
physical no-hook System/direct-Recovery qualification also returned `PASS_GO`
with `0/0/0` and exact supplied identities.

After the later target-contract drift, the strongest truthful current status is:

`H0_DESIGN_PASS_GO_EXPIRED_BY_TARGET_CONTRACT_DRIFT_NOT_ACTIVE`

The old result documents a host design but no longer qualifies current bytes.
It does not retire any activation blocker, prepare a run, create an approval,
or authorize a connected action.

## Claim boundary

- `PROVED`: deterministic host construction, exact closure, byte preservation,
  first-syscall PID gate in the compiled binary, observer behavior under host
  fixtures, and retained T2 terminal revalidation.
- `DESIGNED`: future TWRP boot-only state machine and recovery sequence.
- `UNPROVED`: S20+ direct boot-block identity, TWRP write/readback backend,
  candidate boot, runtime ACM arrival, and live PID1.
- `NOT AUTHORIZED`: connected preparation, root read, staging, reboot, direct
  block access, boot write, Odin, or any partition transfer.

No command was sent to S20+, A90, S22+, or any other attached device.
