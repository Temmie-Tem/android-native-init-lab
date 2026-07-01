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
     `mknod 259:8` before open. **DONE (V3346, init 0.11.110, live 2026-07-02):** no-arg `boot-audit`
     now scans `/sys/class/block/*/uevent` for the single `PARTNAME=boot` partition, materializes
     `/dev/block/sda24`, audits it O_RDONLY, cross-checks the fd rdev against the sysfs major:minor,
     and unlinks the node — emitting `resolve=sysfs-partname materialized=1 open=ok read=ok
     authoritative=1 partname=boot size_bytes=67108864 cleaned=1`. The host wrapper consumed that
     live output and **proposed a confirmed `BootTargetPin`** (`canonical=/dev/block/sda24`,
     rdev 259:8, size 64 MiB, diskseq null, `forbidden_rdevs=[]`). A duplicate `PARTNAME=boot` is
     refused fail-closed (`resolve=ambiguous`); an rdev mismatch on a pre-existing node downgrades to
     `authoritative=0`. Rolled back to v2321 with `selftest fail=0` after each probe. **This closes
     the last read-only precondition** — the write-path design (§2–§6) can now start from a real
     auditor-confirmed pin. §0.2 (RKP write reaction) remains the only unproven gate.
2. **Will RKP/KDP treat a boot-partition WRITE from normal-boot/PID1 differently from a write in
   TWRP?** If it denies cleanly → fine (fall back to TWRP). If it **panics PID1 or the kernel
   mid-write**, the partial-write residual (§1) becomes much sharper — and on **UFS** a tear can
   corrupt the target LBA *and* neighbouring FTL metadata even for an identity write (see §11.1).
   Unknown until the gated RMW-identity write-probe experiment (**designed in §11**), which starts
   with an open-only (no-write) rung and tail-slack writes to bound the blast radius.
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
4. **First write experiment (only after 1–3): the §0.2 write-probe — see §11 for the full design.**
   Refined from the earlier "v2321-over-v2321" idea (chicken-egg — v2321 has no write command — plus
   mixed-corruption risk). The chosen form is **read-then-write-IDENTICAL**: read a bounded region of
   the *currently resident* boot partition and write the **exact same bytes** back. A COMPLETED
   identity write is a true no-op (idempotent, leaves the resident image untouched). **Important
   correction (Codex review):** the storage is **UFS**, and an *interrupted* write is NOT guaranteed
   identity-safe — UFS FTL programs/erases at a large internal granularity, so a tear mid-write can
   corrupt the target LBA and neighbouring FTL metadata even when the bytes are identical. So this is
   a **real destructive-class boot write** whose safety rests on (a) writing harmless **tail slack**
   first (never offset 0), (b) an **open-only** probe before any write, and (c) a **proven external
   recovery drill** — not on a "zero-change ⇒ safe on interrupt" guarantee. It still answers §0.2
   (clean refusal vs allowed vs oops/panic).
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
first (RMW-identity, §11) write experiment justified. The time win is modest (~15-25s/flash), so
self-write stays an **opt-in experiment for new-image-heavy workloads**, never a silent default;
resident-session already covers the REPL batching case, and `native_init_flash.py` remains the
sanctioned path.

## 11. §0.2 write-probe experiment — detailed design (RMW-identity, UFS-corrected)

**Status:** the read-only precondition is closed — the auditor produces an auditor-confirmed pin live
(§0.1, V3346). The ONLY unproven gate before a real write path is §0.2: *how does RKP react to a
`write()` to the boot block from normal-boot PID1?* — clean refusal (`EROFS`/`EPERM`), allowed, or an
oops/panic. This section designs the **lowest-risk** experiment to find out. It is a **real
destructive-class boot-partition write**, made low-risk by construction — not risk-free. **Storage is
UFS** (SM8150 `ufshc1`; `qcom,ufshc` + `CONFIG_SCSI_UFS_QCOM`), which shapes the safety model below.

### 11.1 Core principle — read-then-write-IDENTICAL, and its LIMIT

The probe reads a bounded region of the **currently resident** boot partition and writes the **exact
same bytes** back to the same offsets. A **completed** identity write is a true no-op — idempotent,
leaves the resident image untouched, so a successful probe perturbs nothing and can be repeated.

**Correction (Codex review, MUST-FIX):** identity content does **NOT** make an *interrupted* write
safe. On UFS the FTL programs/erases at a large internal granularity (typ. 512 KiB–4 MiB) and updates
mapping metadata; a tear mid-write (panic/watchdog/power) can leave the **target LBA** old/new/corrupt
**and** damage **neighbouring FTL metadata** — even though the bytes we intended were identical.
`fsync` only reaches `blkdev_issue_flush` after writeback; it does not make the in-flight write
atomic, and the Samsung drop ships no device-supported atomic/reliable-write path. So:
- **Drop** any "zero net change ⇒ safe on interrupt / still bootable after a mid-write panic" claim.
- Treat every rung as a **real boot-partition write** whose recovery is **external** (Odin/TWRP),
  bounded to **boot-only corruption** (we never touch vbmeta/PIT/bootloader/forbidden partitions).
- Minimise what a tear can damage: **write harmless tail slack first** (§11.2) and **prove recovery
  before writing** (§11.4). The value of identity content is only that a *completed* write changes
  nothing — not that an interrupted one is safe.

### 11.2 Bounded, escalating region — tail-slack first, offset 0 LATE

The 64 MiB `sda24` holds a ~60 MiB boot image; the tail is padding/unused **slack**. Confirm the
slack extent first by reading the resident image length (Android boot header `kernel_size`,
`ramdisk_size`, page-rounded) and the auditor's `size_bytes`. Each rung is **separately
operator-gated**; do not advance past any anomaly:
- **E-open (first, NO write):** `open(node, O_WRONLY|O_CLOEXEC)` then `close` — no `write` at all.
  Answers "does RKP/kernel even permit opening the boot block writable" with **zero write**. If this
  fails `EROFS`/`EPERM`, §0.2 is answered "blocked" without a single byte written.
- **E1 — tail-slack 4 KiB identity:** one physical sector (4096 B) inside **confirmed slack** (near
  the partition tail, well past the image), RMW-identity. A tear here can only touch padding, never
  the boot header or image body.
- **E2 — multi-offset 4 KiB identity:** a few sectors at different slack offsets, to catch
  offset-dependent behaviour.
- **E3 — 1 MiB identity** in slack (TWRP's chunk size).
- **E4 — header sector (offset 0) 4 KiB identity:** only *after* E-open..E3 are clean; offset 0 is
  the Android boot header, the highest-consequence single sector, so it is a LATE rung.
- **E5 — full 64 MiB identity:** proves a whole-partition write is permitted and measures self-dd
  timing.
- Only after E-open..E5 pass cleanly and repeatably does a **real new-image self-write** (content
  changes) become the actual tool — a *different* risk class needing its own gate plus §5 rollback
  ordering. Any short write, error, oops, hang, or SHA mismatch on any rung **halts the ladder**.

### 11.3 Guarded, TOCTOU-safe write path (separate fds)

1. Run the auditor (§7.1) → obtain the **auditor-confirmed pin** (rdev 259:8, canonical
   `/dev/block/sda24`, size 64 MiB). Resolve + materialize the node from sysfs `PARTNAME=boot`.
2. **Write fd is the safety-critical one:** `open(node, O_WRONLY|O_CLOEXEC)` (representative of the
   real write path, per review — not `O_RDWR`). Build `BlockIdentity` from the **fd** (`fstat`
   st_rdev, `BLKGETSIZE64`, sysfs `PARTNAME`/size by the fd's rdev — never re-stat the path) and run
   `authorize_write(open_id, open_id, confirmed_pin)`; it **must** pass. Refuse/abort otherwise,
   before any write. (E-open stops here: `close`, report.)
3. Read the source bytes through a **separate** guarded `open(node, O_RDONLY|O_CLOEXEC)` fd:
   `pread(rfd, buf, N, off)`; `sha_pre = SHA256(buf)`. Also snapshot a **full-partition SHA** before.
4. `pwrite(wfd, buf, N, off)` → identical bytes. Record `write_rc`/`write_errno`. Require the return
   to equal `N`; a **short write** is an anomaly → STOP (§11.6), not "unchanged".
5. `fsync(wfd)`; require it to succeed (an `fsync` error is an anomaly → STOP).
6. **Independent** `O_DIRECT` readback: `open(node, O_RDONLY|O_DIRECT)`, re-guard that third fd's
   rdev, read `N` at `off` aligned to `max(logical,physical,4096)=4096`; `sha_post`. Also re-snapshot
   the **full-partition SHA** after.
7. Assert `sha_pre == sha_post == SHA256(written buf)` **and** full-partition-SHA-before ==
   full-partition-SHA-after (catches FTL metadata / cross-LBA change). Report all fields + the guard
   decision. The write buffer is **only** bytes just read from the device (assert `wbuf is rbuf`);
   never a host-supplied buffer for E-open..E5.

### 11.4 Recovery drill (mandatory pre-write gate) & observability

- **Mandatory before E1 (first actual write):** a **recovery drill** confirming the escape hatch is
  live — TWRP boots and can flash boot, and download/Odin mode is reachable — plus v2321
  (`ca978551…`)/v2237/v48 present with known SHAs and the auditor still yielding a confirmed pin.
  Frame recovery honestly: **"boot-only corruption is expected recoverable"**, not "any bad state is
  recoverable" (Odin recovery is conditional on anti-rollback/RPMB/vbmeta, §4a).
- `panic_on_oops`: keep the containment-safe default (`1`) unless a specific rung needs the log; if a
  rung sets `0` for oops capture, do it **only** for the minimal write window, arm a hard watchdog,
  and **halt the whole ladder on any oops/hang even if readback matches** — do not advance to the
  next rung. (Review WARN: `panic_on_oops=0` can let an unhealthy kernel keep issuing I/O.)
- Capture bounded `dmesg | tail` (serial `cmdv1x`) after each write attempt; pstore/last_kmsg on the
  next boot if a reboot occurred. After the probe, **roll back to v2321 via `native_init_flash.py`**
  and confirm `selftest fail=0`.

### 11.5 Gating & guardrails

- **Exact operator approval phrase per rung** (one-shot, non-retried, `hide`/menu-settle before
  dispatch), e.g. `BOOT-WRITE-PROBE-E1 go: read-then-write-identical single 4096B sector in confirmed
  tail slack of the resident boot partition, external recovery drilled, rollback to v2321`.
- The command compiles a write primitive for the **boot block only**; it reuses the §2 guard (numeric
  forbidden-rdev denylist + positive `PARTNAME==boot` + size + confirmed-pin) so it can never target a
  forbidden partition. It writes **only** bytes it just read from the device at the same offset.
- No vbmeta/AVB/PIT/bootloader/forbidden-partition access. A completed identity write does not change
  boot's bytes, so its AVB hash is unchanged — *provided the write completes* (an interrupted write
  could change boot's hash; that is the boot-only-corruption case the recovery drill covers).
- This is the first build to carry a partition-write primitive; the §3/§7 policy ("flash only via
  `native_init_flash.py`") must be amended **deliberately** to permit this gated experiment.

### 11.6 Decision matrix (any anomaly ⇒ UNKNOWN/STOP)

| Observed | Meaning | Next |
| --- | --- | --- |
| E-open `open(O_WRONLY)` → `EROFS`/`EPERM` | kernel/RKP makes boot block unwritable to PID1 | §0.2 = **blocked**; keep TWRP; no byte written; done |
| `pwrite` → `EROFS`/`EPERM`, full-partition SHA unchanged | write refused at the block layer | §0.2 = blocked; keep TWRP |
| `pwrite` returns `N` + region SHA matches + full-partition SHA unchanged | RKP permits PID1 boot writes | §0.2 = **allowed**; advance one rung |
| **short `pwrite`** (< `N`) | partial write — content may have changed | **UNKNOWN/STOP**; verify via full-partition SHA; recover if changed |
| `fsync` error | durability unknown | **UNKNOWN/STOP** |
| `pwrite` `ENOSPC` / `EINVAL` (O_DIRECT align) / other errno | misuse or boundary hit | **STOP**; fix probe; do not advance |
| readback open/read fails, or region SHA mismatch, or **full-partition SHA changed** | cross-LBA / FTL-metadata change | **UNKNOWN/STOP**; recover; do not advance |
| oops in dmesg (no reboot) | RKP traps the write | **STOP the ladder**; analyze; keep TWRP; do not advance even if readback matched |
| panic / hang / reboot | fatal reaction; boot bytes possibly torn | **STOP**; verify next-boot `selftest`, recover via TWRP/Odin if needed; §0.2 = hostile |

### 11.7 Live results

- **E-open (V3347, init 0.11.111, live 2026-07-02): `open_wronly=ok`.** The token-gated
  `boot-write-open-probe BOOT-WRITE-OPEN-PROBE-E-OPEN` resolved the boot partition from sysfs
  `PARTNAME=boot`, materialized `/dev/block/sda24`, and **`open(O_WRONLY)` SUCCEEDED** — `is_block=1`,
  `partname=boot`, `size_bytes=67108864`, `identity_confirmed=1`, `no_write_performed=1`, `cleaned=1`,
  `rc=0`. No `write()`/`pwrite()` was compiled in or called. **This refutes the "RKP forces the boot
  block read-only at open" outcome**: a writable open from normal-boot PID1 is *permitted*. The
  remaining half of §0.2 — whether an actual `pwrite` is permitted vs refused vs faults — is E1
  (tail-slack identity write), still gated and unbuilt. Rolled back to v2321 with `selftest fail=0`.
- **rdev is NOT stable across boots (design correction).** The V3346 auditor saw `sda24` as rdev
  `259:8`; the V3347 E-open probe saw the same `sda24`/`PARTNAME=boot`/64 MiB as rdev **`259:24`**.
  Major 259 is the extended-block major, whose **minor is dynamically allocated per boot**. The
  stable cross-boot anchors are **`PARTNAME=boot` + size (+ canonical name `sda24`)**; the rdev minor
  is a **within-session** value only. Consequence: the auditor-confirmed pin's `rdev` is valid for
  the *current boot session* (open↔write TOCTOU consistency, §2) and **must be re-derived each boot** —
  never persisted/cached across a reboot. The host wrapper's `proposed_pin` is therefore a
  per-session artifact; the write path must run the auditor in the same boot it writes.
- **E1 (V3349, init 0.11.113, live 2026-07-02): `§0.2 = ALLOWED` — the first-ever boot-partition
  write SUCCEEDED and was RKP-permitted.** V3348 first fired the safety net (the fixed tail offset
  held stale non-zero data → `slack_zero=0 stop=slack-not-zero`, **no write**), confirming the
  all-zero gate refuses non-padding. V3349 added a tail-slack zero-sector scan: it parsed the boot
  header (`version=1 page_size=4096 used_len=62644224`, exactly the image size), scanned the slack
  window `[62644224, 66060288)`, found a zero sector at `63631360` after 242 sectors, and performed
  the read-then-write-identical probe: **`pwrite_rc=4096`**, `fsync=ok`, O_DIRECT `region_match=1`,
  and the **full-partition SHA was identical before and after** (`full_match=1`,
  `fc908de2…c732e4`) — a true no-op with zero cross-LBA change. No `EROFS`/`EPERM`/oops/panic. Rolled
  back to v2321 with `selftest fail=0`. **Conclusion: a normal-boot PID1 `pwrite` to the boot
  partition is permitted by RKP; the self-dd write path is feasible.** Next rungs (E2 multi-offset,
  E3 1 MiB, E4 header sector, E5 full-partition identity, then real new-image self-write) remain
  separately gated; each still carries the irreducible UFS-tear residual (§11.1) and needs the
  recovery-drill gate.

### 11.8 E1 implementation (built, Codex-reviewed 2026-07-02 — pre-live)

`a90_boot_write_e1.c` (`boot-write-e1 <token>`), the only self-dd file with a `pwrite` (exactly one).
Built + adversarially reviewed **before** any build/flash/run; Codex returned NO-GO with 5 MUST-FIX +
2 WARN, all folded in:
- **UFS FTL residual (MUST-FIX 1):** removed the over-claim that a torn identity write "can only
  disturb padding". The source/comments now state plainly that on UFS a tear can corrupt the target
  LBA *and* neighbouring FTL mapping metadata (other LBAs), so the rung is only low-risk-by-
  construction with an **externally-recoverable (boot-only)** failure class — the operator must have
  drilled Odin/TWRP recovery first.
- **Header fail-closed + v1/v2 (MUST-FIX 2):** the Android boot-header parse now **fails closed** if
  the `ANDROID!` magic is absent, `page_size` is out of range, or `header_version > 2`; `used_len`
  now includes v1 `recovery_dtbo_size` and v2 `dtb_size` (offsets 1632/1648) so the slack floor is a
  true content upper-bound. The all-zero gate remains the independent safety net.
- **O_DIRECT full-partition SHA (MUST-FIX 3):** the before/after full-partition hash is now a
  cache-bypassed **O_DIRECT streaming** SHA-256 (`a90_helper_sha256_{init,update,final}` exposed for
  this) through a freshly-opened, re-confirmed fd — not `BLKFLSBUF` + buffered read — so a cross-LBA
  change cannot be masked by cache. The region readback stays O_DIRECT + `memcmp`.
- **All fds re-guarded + O_NOFOLLOW (MUST-FIX 4):** every open of the boot node (`rfd`, `wfd`, the
  O_DIRECT readback fd, and both O_DIRECT full-SHA fds) is `O_NOFOLLOW` and runs `e1_confirm`
  (block + rdev==sysfs + PARTNAME=boot + size==64 MiB) before use.
- **Menu-danger gate (MUST-FIX 7):** `boot-write-e1` is now `CMD_DANGEROUS` and is **removed** from
  `command_allowed_during_menu_ex`, so it returns `BUSY_DANGEROUS` while the auto-menu is up — it
  cannot run without an explicit `hide`/menu-settle, as §11.5 requires.
- **fsync log (WARN 5):** an `fsync` failure now prints `fsync=fail` and stops, instead of the
  previous misleading `pwrite=ok fsync=ok`.
- **Recovery drill (WARN 6):** the recovery drill + `panic_on_oops` + dmesg/pstore capture remain
  operator-side; a live E1 run is valid **only** if the operator drills Odin/TWRP recovery before
  dispatch. The C token alone is not proof of recovery readiness.

Control flow (verified): the single `pwrite` is reachable only after token, single-match sysfs boot
resolution, `rfd` identity, header parse (fail-closed), target-in-tail-slack bound, `slack_zero==1`,
before-SHA, and `wfd` identity; it writes exactly the bytes it read; `result=ok` is emitted only when
no `stop` was set. **Not yet built into an image or run** — the next step is a v3348 build, an
operator recovery drill, `hide`, and the token-gated live E1, then rollback to v2321.
