# Fast Self-dd Boot-Flash Tool — Safety Design Spec

- Date: 2026-07-02 (rev.2 — incorporates Codex second-opinion review, session `019f1f35`)
- Motivation: flash is the **universal** per-iteration bottleneck for ALL device development
  (audio / GPU / USB / kernel .text-patch / any native-init change), not just the REPL call-proof
  track. The sanctioned TWRP flash path costs ~64s/flash because it **reboots through recovery**
  (reboot-into-recovery + adb push 60MB + remote SHA + dd + readback SHA + reboot-out). A self-dd
  path — native-init (already booted, root PID1) writes its own boot block directly, then reboots
  once — removes the recovery round-trip.
- **Realistic gain (revised down per review): ~15-25s/flash, NOT ~1.5x/~2x.** The
  reboot-to-new-kernel floor (~30s) dominates and is unavoidable; self-dd only removes the extra
  recovery round-trip. Worst case (staging a fresh 60 MiB image every iteration) the gain shrinks
  further. Still a compounding win applied to every future device iteration, but modest — which
  raises the bar on whether the added risk surface is justified (see §10 verdict).
- Non-negotiable requirement: **NO new permanent-brick path.** The catastrophic risk (write to a
  forbidden partition) must be removed *structurally in code*, leaving only the recoverable residual
  (interrupted write → download-mode reflash; the bootloader partition is never touched).
- Status: DESIGN ONLY, and per review the FIRST build increment is a **read-only auditor with no
  write path compiled in** (§7). Full write path is gated behind the auditor + fault-injection tests
  + an explicit policy update. `native_init_flash.py` (TWRP) remains the only sanctioned flash path
  until then.

## 0. Open feasibility questions (must be answered before any write)

These are UNPROVEN and could invalidate the whole approach; the §7 read-only auditor exists largely
to answer them cheaply, before any write path is built:

1. **Can native-init even open/read `sda24` at runtime under Samsung RKP/KDP?** — **ANSWERED YES
   (2026-07-02, live, V3345 `boot-audit`, init 0.11.109).** Findings:
   - The Android `/dev/block/by-name/boot` symlink does **not** exist under native-init (ueventd/vold
     populate it on Android; native-init does not). Auditing the default target returns
     `open=fail errno=2` — a real design finding, not a read failure.
   - native-init's `/dev/block` holds only the 5 nodes it created (`sda20/21/28/31`, `mmcblk0p1`);
     there is **no boot devnode**, because native-init never mounts boot (it *is* the boot ramdisk).
   - sysfs still knows the partition: `/sys/class/block/sda24/uevent` → `MAJOR=259 MINOR=8
     DEVNAME=sda24 PARTNAME=boot`. Materializing the node with the existing `mknodb /dev/block/sda24
     259 8` command, then `boot-audit /dev/block/sda24`, yields: `open=ok`, **`read=ok bytes=4096`**
     (the definitive answer — RKP permits native-init to read the boot block), `is_block=1`,
     `rdev=259:8`, `size_bytes=67108864` (exactly 64 MiB), `logical/physical_sector=4096`,
     `partname=boot`, `sysfs_sectors=131072`, `canonical=/dev/block/sda24`, `diskseq=absent`
     (kernel 4.14 does not expose diskseq — the pin enforces rdev+canonical, not diskseq).
   - **Design consequence for the write path:** the auditor/writer must resolve the authoritative boot
     node from **sysfs `PARTNAME=boot`** (not the absent by-name symlink) and materialize it via
     `mknodb 259:8` before open. The current auditor flags a manually-materialized `sda24` path as
     `authoritative=0`, so the host wrapper correctly refuses to propose a write pin from it; the next
     unit must add sysfs-`PARTNAME=boot` resolution so an `authoritative=1` confirmed pin can be
     produced. Rolled back to v2321 with `selftest fail=0` after the probe.
2. **Will RKP/KDP treat a boot-partition WRITE from normal-boot/PID1 differently from a write in
   TWRP?** If it denies cleanly → fine (fall back to TWRP). If it **panics PID1 or the kernel
   mid-write**, the partial-write residual (§1) becomes much sharper. Unknown until the gated
   v2321-over-v2321 experiment (§7.4).
3. Does AVB/vbmeta add any new next-boot refusal? Probably not (TWRP already flashes modified boot
   images that boot), but confirm the resident vbmeta policy is unchanged.

## 1. Threat model (what can go wrong writing a boot partition)

| Failure | Cause | Severity | This tool's defense |
| --- | --- | --- | --- |
| **Wrong-block write** | by-name mis-resolve, symlink swap between check and write (**TOCTOU**), wrong `of=` | **PERMANENT BRICK** if it hits efs/modem/RPMB/vbmeta/bootloader | **Single-fd target guard (§2)** — open once, verify the fd's identity, write through the *same fd*; no path is re-resolved at write time |
| Wrong/mixed image | wrong image handed in, corrupt source | boots bad kernel | **Anti-mixup SHA check (§3)** (honestly: an anti-mixup gate, not a true supply-chain allowlist) |
| Bad/partial write | flash media error, partial write | boots corrupt kernel | **Readback verify with cache bypass (§4)**; never reboot into an unverified boot |
| Interrupted write | power loss / panic / watchdog / killed PID1 mid-write | **RECOVERABLE** (corrupt boot, bootloader intact) → download-mode/TWRP reflash | minimize window; accept as the one irreducible residual; **sharper if RKP panics mid-write (§0.2)** |
| Rollback self-brick | self-write of v2321 fails, then reboots into bad boot | stranded until manual recovery | **Rollback-safety ordering (§5)** — verify before reboot; TWRP fallback |

The ONLY residual after this design is the **interrupted-write** case, **recoverable, not permanent**
(bootloader is a separate, never-touched partition; download mode + Odin/TWRP + a known-good image
always restore) — *provided* the target guard is airtight and RKP does not panic mid-write. This is
the same recovery net the project already depends on, so a correctly-guarded tool adds **no new
permanent-brick path** — but "structurally incapable" is too strong a claim; it is "no new
permanent-brick path if §2 holds and §0.2 resolves benignly."

## 2. Single-fd target guard (THE core — anti-wrong-block, TOCTOU-safe)

Per review, a resolve-then-`dd` (or resolve-then-shell) flow is a **TOCTOU hole**: the by-name
symlink could change between the check and the write. The guard MUST be tied to one open fd:

1. `open("/dev/block/by-name/boot", O_WRONLY | O_CLOEXEC)` **once**. All subsequent checks and the
   write use THIS fd — never re-resolve the path.
2. `fstat(fd)` and assert `S_ISBLK(st_mode)` and `st_rdev` == the **pinned expected major:minor**
   for the boot block (A90: `by-name/boot` → `sda24`, 64 MiB; pin the canonical target + major:minor,
   verified at first-run by the read-only auditor).
3. Cross-check the fd's identity via sysfs: resolve `st_rdev` → `/sys/dev/block/<maj>:<min>/` and
   assert `partition`/`uevent PARTNAME` == `boot` and the size matches the pinned partition size.
4. Assert `st_rdev` is **NOT** any forbidden partition's major:minor (efs, sec_efs, modem, RPMB,
   keymaster, vbmeta*, dsp, keydata, keyrefuge, bootloader, persist) — resolved to numbers, not names.
5. Any mismatch → **refuse, close fd, do not write, report.** Only after all asserts pass on the
   *same fd* is the write function reachable. No path string is used at write time.

## 3. Anti-mixup SHA check (honest naming — not a supply-chain allowlist)

- The image to write must present an **explicit expected SHA256** matched against the actual staged
  bytes; refuse on mismatch. For fixed images (v2321 `ca978551…`, deep fallback v2237 `b2ea2d26…`)
  this is a pinned check; for a fresh candidate image the SHA is **caller-asserted** — so this is an
  **anti-mixup gate** (did I stage the bytes I meant to?), *not* a trust/supply-chain allowlist.
  Name it that way in code and reports.
- Validate the image is a well-formed boot image of the expected size (header magic + size) before
  writing, echoing `native_init_flash.py`'s `inspect_local_image` discipline. Never scan-and-guess
  (the prior "unpinned boot-image autodiscovery" finding class).

## 4. Readback verify with cache bypass (anti-bad-write)

Refined per web research (kernel writeback-cache docs + dm-devel): `ioctl(BLKFLSBUF)` alone is
**insufficient** for a durable-commit check — it only drops the block device's page-cache dirty
pages; it does NOT send a flush bio, so data may still sit in the device's volatile cache. Do both
of the following instead:
- **Write durability:** after the write, `fsync(fd)` on the block device — on Linux 4.14 an fsync of
  a block fd issues a FLUSH CACHE to the storage controller via the block layer (this is the
  userspace primitive; `blkdev_issue_flush` / `REQ_PREFLUSH` are the *kernel-internal* mechanism it
  triggers, **not** a userspace ioctl). `dd … conv=fsync` fsyncs per block; an explicit final
  `fsync(fd)` is the belt. `fdatasync` is not meaningfully better on a raw block fd.
- **Readback correctness:** **re-open the block `O_RDONLY | O_DIRECT`** and read the written prefix
  from the device (bypassing the page cache), then SHA-compare to the source. Do NOT rely on
  `BLKFLSBUF` + a plain buffered read — `BLKFLSBUF` only drops page-cache dirty pages, it is not a
  durability primitive and a buffered read can be served stale.
  - **O_DIRECT alignment:** do NOT assume 512 bytes. Query `BLKSSZGET` (logical) and `BLKPBSZGET`
    (physical) and align the read offset, length, and buffer (`posix_memalign`) to
    `max(logical, physical, 4096)`. A 64 MiB partition + boot-image-sized reads are alignment-
    friendly *if* chunking is enforced.
  - The `O_DIRECT` readback fd is a **second fd** → it must be **independently re-guarded** (§2)
    against its own `fstat` rdev before reading, not trusted from the write fd.
  - If `O_DIRECT` open fails `EINVAL` on this platform, the write path **stays disabled** (do not
    silently fall back to a cache-served read).
- **On mismatch, do NOT reboot.** Stay in native-init (retry or TWRP fallback possible). Never reboot
  into an unverified boot partition.

Prior art (mechanism is established, not novel): Magisk's on-device boot patching and the
`fastbootx` Magisk module both manage the boot partition from a running rooted system via `dd`
(+`bootctl` on A/B); Magisk backs up stock boot before patching (our v2321 is that known-good
backup). This corroborates the review's "normally feasible, Magisk-class" assessment — the residual
risk is the platform-specific RKP reaction (§0.2), not the dd mechanism itself.

### 4a. TWRP reference — proven-in-the-wild flash sequence (host-RE 2026-07-02)

We cross-checked our design against how TWRP actually flashes `boot` on **this** device (local
teardown `tmp/twrp-unpack/`; source: TeamWin `android_bootable_recovery` `partition.cpp`
`Raw_Read_Write`). Odin is **not** an imitation target — it hands the image to the *bootloader* over
the download-mode protocol (pre-kernel, no RKP), which PID1 cannot drive; Odin's only role for us is
the recovery net of last resort. The working assumption is that a corrupt `boot` stays recoverable
by an Odin/download-mode reflash of a `boot`-only `.tar` (bootloader intact) — but that is the
*standard* Samsung-flashing assumption, **not independently verified in this repo**: it holds only
if anti-rollback fuses, RPMB state, and the vbmeta/AVB chain do not refuse the reflashed `boot`.
Treat it as "conditionally recoverable," and confirm with a Samsung/Odin primary source before
relying on it as a hard guarantee (TODO). This is the §1/§5 residual assumption, now explicitly
conditional.

TWRP *is* the right reference — it does a userspace block-write of `boot`, the same layer as us:
- **Partition resolution (A90 `twrp.flags`):** `/boot  emmc  /dev/block/bootdevice/by-name/boot
  flags=backup=1;flashimg=1`. `bootdevice` is symlinked from `ro.boot.bootdevice` (kernel cmdline)
  and TWRP's own ueventd builds `by-name/*` **from the GPT partition labels** (uevent `PARTNAME`).
  → This *confirms* our live finding: the authoritative source is the GPT `PARTNAME=boot`, and our
  sysfs `PARTNAME=boot` resolution (§0.1) reads the **same ground truth** TWRP's ueventd does, minus
  the convenience symlink native-init never creates. **Equivalence caveat:** the by-name symlink and
  our sysfs read are only equivalent once both resolve to the *identical* `st_rdev` + sysfs
  `PARTNAME` + size — ueventd derives the link name purely from `PARTNAME`, so a **duplicate label**
  could leave a `by-name/boot` symlink pointing at the wrong node. Our guard therefore must not trust
  the name alone: it pins the exact `rdev` (259:8) + `PARTNAME=boot` + `size==64MiB` together (§2),
  which is precisely what defends against a duplicate-label alias. `flashimg=1`/fstype `emmc` = raw
  image write path.
- **Write sequence (`Raw_Read_Write`, verbatim, `partition.cpp` android-12.1 L2800-2882 /
  android-9.0 L2735-2814):** dest `open(O_WRONLY | O_CREAT | O_TRUNC | O_LARGEFILE)` (on a block node
  `O_CREAT`/`O_TRUNC` are no-ops), **1 MiB chunks** read/write loop, a single **`fsync(dest_fd)` at
  the end**, then close. We adopt exactly this (§4: O_WRONLY, 1 MiB chunks, final fsync).
- **Size preflight — clarified (per review):** `Raw_Read_Write` itself has **no internal size
  bound** (it copies until the source EOF). But the *entry point* for a direct flash,
  `TWPartition::Flash_Image`, **does** reject `image_size > Size` before dispatching to the raw write
  (android-12.1 L3299-3333) — so TWRP is not size-blind at the flash level. The "erase first 2 KB"
  trick is **`Flash_Image_FI` / `BM_FLASH_UTILS` (MTD/BML) only**, *not* the `emmc` / `BM_DD` path,
  so it does **not** apply to A90 `/boot`. Our pin is *stricter still*: exact `size == 64 MiB`
  equality, not TWRP's `image <= partition` inequality.
- **Where we deliberately EXCEED TWRP (keep these):** TWRP's `BM_DD` path has **no read-back
  verification** and **no target-identity guard** (it trusts the fstab/by-name mapping). Our design
  adds both — the O_DIRECT cache-bypassed readback SHA (§4) and the single-fd rdev/PARTNAME/size
  guard (§2) — plus the anti-mixup SHA (§3) and exact-size pin above. Imitating TWRP validates the
  *mechanism*; our extra checks are the safety margin TWRP lacks. (`Flash_Image` for `BM_DD` also
  does no AVB/vbmeta handling — vbmeta is a separate flashable entry — so there is no boot-side AVB
  step for us to inherit or drop.)
- **Caveat imitation cannot remove:** TWRP runs its **own recovery kernel**, so its successful
  `boot` write does **not** prove RKP-under-normal-boot allows a PID1 partition write (§0.2). That
  remains the one unproven risk, answerable only by the gated v2321-over-v2321 experiment (§7.4) — a
  different kernel's success is not evidence here.

Sources: [TeamWin android_bootable_recovery partition.cpp](https://github.com/TeamWin/android_bootable_recovery/blob/android-12.1/partition.cpp),
device `twrp.flags` (`tmp/twrp-unpack/rd/system/etc/twrp.flags`),
[TWRP teardown reference](../reports/TWRP_RECOVERY_TEARDOWN_DEVICE_REFERENCE_2026-06-13.md).

## 5. Rollback-safety ordering (the most safety-critical path)

Rollback to v2321 is where a self-brick would strand the device (no native-init to retry after a bad
reboot). Therefore:
- Verify (cache-bypassed readback SHA of v2321) **before** issuing the reboot.
- If self-write rollback verify fails → **fall back to the sanctioned TWRP `native_init_flash.py`
  path** rather than rebooting into an unverified boot.
- Keep TWRP + a known-good image available at all times (unchanged project invariant).
- Prefer keeping **v2321 staged resident on device** so rollback is a local write (no push).

## 6. Implementation shape (device is the authority)

- **One native-init command does guard→verify→write→readback in a single fd-scoped operation** — NOT
  "guard, then `system("dd …")`". Guard/anti-mixup/write/cache-bypassed-readback are all enforced
  **device-side**, tied to the opened fd, so a host bug cannot bypass them. The command does NOT
  reboot; it returns a machine-parseable result and the host decides.
- **Identity MUST be built from the opened fd, never re-derived from the path** (Codex Q3): after
  `open(path, O_WRONLY|O_CLOEXEC)`, take `st_rdev` from `fstat(fd)`; size from `BLKGETSIZE64` on the
  fd; PARTNAME and `diskseq` re-read from `/sys/dev/block/<maj>:<min>/{uevent,diskseq}` using the
  **fd's rdev**, not the original path string. Never `stat()` the path after open. The `O_DIRECT`
  readback fd repeats this independently.
- **The host-side guard logic is already implemented and adversarially tested**:
  `workspace/public/src/scripts/revalidation/a90_boot_target_guard.py` (+ `tests/…`, 27 tests). The
  device C command PORTS `evaluate_boot_target` / `authorize_write`. Critical rule ported from that
  module: **a write is refused unless the pin is auditor-confirmed** (`pin_is_confirmed`: rdev +
  canonical path set) — a default/unconfirmed pin may be used ONLY by the read-only auditor, never to
  authorize a write. Numeric forbidden-rdev denylist + `diskseq` pin are enforced when the auditor
  populates them.
- **Host orchestrates only**: staging (push if not resident), candidate-SHA selection, reboot,
  post-flash health/selftest, rollback policy, reporting. It is NOT the authority for target identity
  or write refusal — the device is.
- **`native_init_flash.py` (TWRP path) stays the sanctioned default and the recovery-grade path.**
  Self-write is an experiment/opt-in fast path until proven, not a replacement.

## 7. Build order (revised per review — read-only auditor FIRST)

1. **`boot-target-audit` — device-side, READ-ONLY, NO write path compiled in.** Opens the resolved
   target, reports canonical path, `st_rdev` major:minor, sysfs `PARTNAME`, size, denylist result,
   and the current boot-prefix SHA. This alone answers §0.1 (can native-init read `sda24` under RKP)
   and validates the guard's identity checks — with zero write risk.
2. **Host-only guard fault-injection tests (safety-critical):** every one must fail *before any write
   function is reachable* — boot resolving to a forbidden alias / wrong major:minor / wrong
   `PARTNAME` / wrong size / **symlink swapped between check and write (TOCTOU)** / concurrent
   invocation. This is the sharpest test set; it gates everything downstream.
3. **Policy update** (explicit): the repo currently mandates flash only via `native_init_flash.py`.
   Building/using a write path requires updating that policy deliberately — not silently.
4. **First write experiment (only after 1–3):** self-write the **already-resident v2321 over itself**
   (no new-image variable), TWRP/download recovery armed, then reboot + `version/status/selftest
   fail=0`. This tests the runtime write path and answers §0.2 (RKP reaction) with the safest
   possible payload.
5. Only after 4 passes cleanly and repeatably: allow self-write as an **opt-in** fast path (not
   default), TWRP as fallback. Re-measure the real per-flash saving; if it is at the low end
   (~15s) reassess whether it is worth carrying.

## 8. Scope / relationship to the batching levers

Independent and complementary to the REPL resident-session levers:
- Resident-session (① don't rollback between batches, ② skip batch-1 warm reboot) reduces the *count*
  of flashes for the call-proof workload — and per review is **enough on its own for REPL batching**.
- This tool reduces the *cost of each flash* — relevant to **new-image-per-iteration** workloads
  (kernel .text-patch, native-init feature dev) where flash count can't be reduced. Per review this
  is worth **one bounded experiment, not default adoption**.

## 9. Bright lines (unchanged)

Never write forbidden partitions (enforced by §2's fd-scoped numeric checks, not just convention).
Boot-partition-only. Keep TWRP + known-good images. The interrupted-write residual is accepted as
recoverable-only; nothing in this tool may create a permanent-brick path.

## 10. Verdict (Codex-reviewed)

Do **not** build the full fast-flash write path up front. Build the **read-only `boot-target-audit`
first** — it is zero-risk, answers the RKP read-feasibility unknown, and exercises the guard identity
logic. Then the guard fault-injection tests. Only after those + an explicit policy update is the
first (v2321-over-v2321) write experiment justified. The time win is modest (~15-25s/flash), so
self-write stays an **opt-in experiment for new-image-heavy workloads**, never a silent default;
resident-session already covers the REPL batching case, and `native_init_flash.py` remains the
sanctioned path.
