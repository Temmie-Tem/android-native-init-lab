# S22+ — The Wall Is a PMIC/PON Abnormal Reset on a Non-Progressing Bare PID1, Not the Modules (Operator Reframe, 2026-07-09)

Operator (Claude) host-only reframe after the M30/M21A live result plus the
operator's RDX photo. Codex then host-verified the local module metadata,
kernel/watchdog source, current Android config, and current Android module
state. No flash, reboot, Odin action, partition write, or native-init live
action was run in this unit.

This supersedes the "fault in modules 1–24" and M31 short-dwell-download
primary direction. It also retracts the previous "regulator modules brown out
the rail" guess.

## The decisive evidence: M21A (zero modules) still resets

M30/M21A ran a **raw PID1 with NO modules** that only does
`nanosleep(90 s) -> reboot(..., "download")`. It did **not** reach Download; the
operator photographed an **RDX screen with `PMIC abnormal reset`** as the upload
cause. Compare to M26 `P00`:

```text
P00   (0 modules, reboots ~immediately)      HIT   -> reached Download
M21A  (0 modules, sleeps 90 s then reboots)  FAIL  -> PMIC abnormal reset (RDX)
```

Same raw PID1 harness (P00 proves the harness runs and can call
`reboot(download)`), differing only in **dwell**. So the reset fires **during the
dwell, at a timeout** — independent of any module. This directly kills three
prior beliefs:

- Not "the fault is in substrate modules 1–24": zero modules still resets.
- Not the **msm software watchdog** (`qcom_wdt_core`) we have been blocklisting:
  that module is absent in M21A yet the reset still happens.
- Not "regulator modules brown out a rail" (my prior-turn guess): M21A loads no
  regulator module. **Retracted.**

It also matches the older shapes now: M25 parked ~29 s then took a single reset
at ~30.3 s; M28/S24 park-then-reset — all the same **PMIC/PON timeout ceiling**,
not distinct module faults.

## What "PMIC abnormal reset" actually is

The string `PMIC abnormal reset` is **not** in the S22+ kernel source
(`s22plus_kernel_source/.../kernel_platform`, grep-confirmed absent). It is
drawn by the **bootloader (XBL/ABL) RDX/upload path**, which reads the PMIC
**PON** (power-on) reason register and classifies a non-clean previous reset as
"abnormal". So this is a **hardware/PON-level** reset classification — the
previous boot ended in a warm reset that was not a clean software shutdown.

The `store_lastkmsg=1` / `reset_reason=MPON` / `reset_rwc=25` post-run probe is
consistent with a PMIC-PON warm-reset path, and the RDX ramdump summary
(TrustZone/Hypervisor/TME/DCC) means MID upload mode engaged on the reset.

## Host Verification Added By Codex

The PMIC/RDX string is visual evidence from the operator photo, not a retained
`last_kmsg` marker. The retained log did preserve surrounding evidence:

```text
/proc/reset_reason = MPON
/proc/reset_rwc = 25
/proc/store_lastkmsg = 1
last_kmsg marker counts: S22_NATIVE=0, M21A=0
last_kmsg surrounding counts: RDX=16, abnormal=32, watchdog=72
```

Local source/string check:

```text
grep "PMIC abnormal reset" in FYG8 OSRC kernel tar: rc=1
grep "PMIC abnormal reset" in base OSRC Kernel.tar.gz: rc=1
```

That supports the conclusion that the exact LCD text is emitted by the
bootloader/RDX path, not by the Linux candidate.

Stock vendor-ramdisk module order from the extracted FYG8 metadata:

```text
modules.load #5   gh_virt_wdt.ko
modules.load #6   qcom_wdt_core.ko
modules.load #39  gh_virt_wdt.ko
modules.load #84  qcom_wdt_core.ko
```

Their `modules.dep` closure is small:

```text
/lib/modules/qcom_wdt_core.ko: /lib/modules/qcom-scm.ko /lib/modules/minidump.ko /lib/modules/smem.ko
/lib/modules/gh_virt_wdt.ko: /lib/modules/qcom_wdt_core.ko /lib/modules/qcom-scm.ko /lib/modules/minidump.ko /lib/modules/smem.ko
```

Current normal Android, read-only through ADB/Magisk root, confirms the stock
runtime model:

```text
CONFIG_WATCHDOG_CORE=y
CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y
CONFIG_WATCHDOG_OPEN_TIMEOUT=0
# CONFIG_WATCHDOG_NOWAYOUT is not set
# CONFIG_WATCHDOG_SYSFS is not set

/proc/modules:
  gh_virt_wdt
  qcom_wdt_core
  qcom_soc_wdt
  sec_qc_qcom_wdt_core
```

Current root `dmesg` shows kernel-side watchdog feeding:

```text
msm_watchdog_data - pet: ... / last_pet: ... (delta: 9.47s)
```

The base OSRC `qcom-wdt.c` is not the exact Samsung vendor module source
(`CONFIG_QCOM_WDT` is not set in the live config while `qcom_wdt_core` is loaded
as a vendor module), but it is still useful reference: its default timeout is
30 seconds when no `timeout-sec` is specified, matching M25's about-30.3 second
reset return.

The kernel watchdog core is directly relevant and live config confirms it is
enabled. `watchdog_dev.c` sets:

```text
handle_boot_enabled = IS_ENABLED(CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED)
open_timeout = CONFIG_WATCHDOG_OPEN_TIMEOUT
```

and its worker pings a hardware-running watchdog before userspace opens
`/dev/watchdog` when `handle_boot_enabled` is true. With
`CONFIG_WATCHDOG_OPEN_TIMEOUT=0`, the open deadline is effectively infinite.
That is exactly the mechanism a bare native PID1 loses when the early watchdog
modules are excluded.

## Leading mechanism hypothesis (M31): the watchdog inversion

On this S22+ path the watchdog is effectively already a boot-critical platform
service. In a normal boot, stock vendor module order loads `gh_virt_wdt.ko` and
`qcom_wdt_core.ko` at positions **5** and **6**, and the live Android kernel
shows `msm_watchdog_data` petting about every 9.47 seconds. Every native-init
candidate since M13 has
**blocklisted** `qcom_wdt_core`/`gh_virt_wdt` on the theory "don't load the
watchdog so nothing needs petting."

That theory is likely **backwards**: the watchdog is armed in hardware
regardless of whether we load the module. The module's job is to *tame* it
(pet, or configure bark/bite). Blocklisting the module leaves the pre-armed
watchdog **un-managed**, so it bites at its timeout (~30 s, matching every
observed park duration) → warm reset → PON records "abnormal". A do-nothing
sleeping PID1 (M21A) is the purest demonstration.

If loading the stock watchdog modules registers the hardware-running watchdog
with the kernel watchdog core, `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y` and
`CONFIG_WATCHDOG_OPEN_TIMEOUT=0` should let the kernel keep it alive even while
PID1 parks. That would remove the ~30 second ceiling without userspace petting.

Caveat: the exact Samsung `qcom_wdt_core.ko` source is not present as source in
the OSRC tree. M31 must confirm behavior live. The fallback remains explicit
userspace keepalive (`/dev/watchdog` write/`WDIOC_KEEPALIVE`) or a narrowly
proved disable path, but those are secondary because stock Android already
demonstrates kernel-side petting.

## M31 = watchdog-managed park, not short-dwell download

Next host-only build target:

```text
M31B_WDT_MANAGED_PARK

setup minimal /dev/proc/sysfs enough for insmod
insmod smem.ko if needed and available as a module dependency
insmod minidump.ko
insmod qcom-scm.ko
insmod qcom_wdt_core.ko
insmod gh_virt_wdt.ko
park for observation; no Download beacon, no USB/configfs, no Android handoff
```

Notes:

- The exact dependency order must come from `modules.dep`, not hand guessing.
- If `qcom-scm` or `smem` are built-in/loaded by the kernel before PID1, the
  builder should still record their dependency status and only package needed
  `.ko` files.
- The first live candidate should prove survival, not USB. Do not mix in ACM,
  configfs, QMP, DTBO, or the 140-module substrate.
- Success is external behavior: no PMIC/RDX abnormal reset past 60-120 seconds.
  Manual Download rollback is expected because a park candidate has no self
  Download beacon.
- Failure means the module-only watchdog management path is insufficient, and
  the next branch is explicit `/dev/watchdog` keepalive or a proven disable
  path.

Only after the ceiling is removed do the earlier threads resume: HS-only ACM
gadget bring-up (dependency-complete substrate + watchdog now managed), then
the DTBO ssphy-phandle question.

## Why this reframes the whole saga

Every "park then single reset ~30 s", every empty `last_kmsg` (PMIC hard reset +
RDX inserts an extra boot that clears it), and every "no ACM before Download"
was the **same PON/watchdog timeout**, not a module-specific bug. The observable
truth was on the RDX screen the whole time (`PMIC abnormal reset`), not in
`last_kmsg`. The fix is not more markers or finer prefix bisection — it is to
**stop starving the pre-armed watchdog** (load/pet/disable it), so a bare PID1
can stay alive long enough to do anything.

## Discipline

Host-only build/design + one attended live test under a fresh SHA-pinned boot-only
`AGENTS.md` exception. No forbidden partitions, no PMIC/regulator/GDSC/GPIO
power *writes* (loading the stock watchdog driver is not a PMIC/regulator/GDSC/
GPIO write). Redact serials from committed reports. Device stays recoverable to
the Magisk baseline; it is currently clean (M30 rollback verified
boot/dtbo/vendor_boot baseline, `uid=0`). No live flash is authorized by this
report.

## Fallback observability: RDX / S-Boot Upload Mode RAM dump (web-researched, low-ROI)

The operator's RDX photo shows `[To PC] Connect a USB cable` — i.e. the crashed
device can offer a RAM dump over USB. Researched for completeness; kept as a
**documented fallback only**, not the next step.

**The path/tools exist.** The screen is Samsung **S-Boot Upload Mode** (RDX).
Open-source pullers:
- `bkerler/sboot_dump` (SUC, Python, reverse-engineered S-Boot): dumps RAM over
  USB — `samupload.py` (partition table) / `all` / `range 0x0 0xffffffff` /
  `partition N`.
- `linux-msm/qdl` `qramdump` (Qualcomm **Sahara**, EDL PID `900e`) — lower-level,
  but that is EDL mode, distinct from S-Boot Upload Mode; not simpler here.

**Two gates make it low-ROI for this project:**
1. **Protocol generation gap.** `sboot_dump`'s newest *Samsung-QC* test target is
   the **S7 (2016)**; the S22/SM8450 S-Boot upload protocol is untested and
   likely needs porting.
2. **`RDX (without Token)` = the real wall.** Modern Samsung ramdump is gated by
   a **signed token**; retail units only get the "without Token" path. With
   `debug_level=MID` (not HIGH) and no token, the dump is expected to be
   **limited / scrubbed / whitebox-AES-encrypted** (Samsung WAES + CC flags),
   i.e. not freely decodable. A full decodable kernel RAM dump needs
   `debug_level=HIGH` **and** a Samsung-signed token = not available on retail.
   This is the **same token/TZ gating pattern that closed the EUD path.**

**And we do not need it.** The datum we wanted — the reset *cause* — is already
on the RDX screen (`PMIC abnormal reset`). Per-instruction localization would be
the only extra value, but the M31B watchdog-managed-park test discriminates the
leading hypothesis far more cheaply than porting an S-Boot dumper and fighting a
token gate; a watchdog-bite RAM dump would most likely just show a CPU idle in
`nanosleep` when the un-managed watchdog bit — which the park test proves
directly.

**Verdict:** pursue M31B first. Only if M31B is inconclusive *and* per-instruction
localization becomes necessary, attempt `sboot_dump` as a read-only experiment
(RAM read, no partition write — within safety bounds), accepting probable
protocol-port work and token-gated/limited output. Sources: `bkerler/sboot_dump`,
`linux-msm/qdl`, Qualcomm "collect and parse RAM dumps", SSTIC 2017 "Attacking
Samsung Secure Boot" (whitebox AES), Samsung Community "ss rdx without token".
