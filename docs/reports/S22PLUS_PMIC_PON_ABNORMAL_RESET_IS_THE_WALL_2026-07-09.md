# S22+ — The Wall Is a PMIC/PON Abnormal Reset on a Non-Progressing Bare PID1, Not the Modules (Operator Reframe, 2026-07-09)

Operator (Claude) host-only reframe after the M30/M21A live result plus the
operator's RDX photo. No device action here. This supersedes the "fault in
modules 1–24" and "msm software watchdog" framing and retracts the previous
"regulator modules brown out the rail" guess.

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

## Leading mechanism hypothesis (to confirm in M31): the watchdog inversion

On Qualcomm the **APSS hardware watchdog is armed by XBL before the kernel
runs**. In a normal boot, the kernel's Qualcomm watchdog driver
(`qcom_wdt_core.ko`, stock `modules.load` position **6**, right after
`gh_virt_wdt.ko` at **5**) takes over and keeps it alive (Qualcomm
`msm_watchdog_v2` pets from a kernel timer/delayed-work, i.e. kernel-side, not
requiring userspace). Every native-init candidate since M13 has
**blocklisted** `qcom_wdt_core`/`gh_virt_wdt` on the theory "don't load the
watchdog so nothing needs petting."

That theory is likely **backwards**: the watchdog is armed in hardware
regardless of whether we load the module. The module's job is to *tame* it
(pet, or configure bark/bite). Blocklisting the module leaves the pre-armed
watchdog **un-managed**, so it bites at its timeout (~30 s, matching every
observed park duration) → warm reset → PON records "abnormal". A do-nothing
sleeping PID1 (M21A) is the purest demonstration.

If the Qualcomm driver's pet is a **kernel timer** (as in mainline
`msm_watchdog_v2`), then simply **loading** `qcom_wdt_core` would keep the
watchdog alive even while PID1 sleeps — removing the ~30 s ceiling entirely,
with no userspace petting needed. This is the opposite of what we have been
doing.

Caveat (honest): the Samsung OSRC tree here is a base GKI drop and does not
contain the Qualcomm watchdog driver source, so the "kernel-timer auto-pet" is
inferred from mainline `msm_watchdog_v2`, not confirmed against this exact
build. M31 must confirm it, and there is a real alternative: if this build's
watchdog needs **userspace** keepalive (`/dev/watchdog` write, or a magic-close
disable), the bare init must pet or disable it explicitly.

## M31 = host-only research + one decisive load-the-watchdog test

1. **Host-only:** confirm the S22+ watchdog pet model — is `qcom_wdt_core`'s pet
   a kernel timer (survives a sleeping PID1) or does it need userspace
   `/dev/watchdog` keepalive? Use the mainline `msm_watchdog_v2` / `qcom-wdt`
   reference and any bark/bite/`pet_time`/`bark_time` DT properties in the FYG8
   DTB. Also check for a cmdline/sysfs to disable the APSS/PON watchdog
   (`qcom_wdt`, `nodl`, `pet`, `s2_reset`, PON `warm_reset`), and whether a
   bare init can write `/dev/watchdog`/`WDIOC_*` inside the ~30 s budget.
2. **Decisive live test (fresh SHA-pinned boot-only exception):** a minimal
   candidate that **LOADS `gh_virt_wdt` + `qcom_wdt_core`** (plus only their own
   `modules.dep` deps) and then **parks** (no reboot beacon). If it survives past
   ~60–120 s with no PMIC abnormal reset, the watchdog inversion is confirmed and
   the dwell ceiling is gone — every prior park/ACM attempt was dying to the
   un-managed watchdog, and USB-ACM bring-up (which needs the device to stay
   alive) becomes reachable. If it still resets, fall back to explicit
   `/dev/watchdog` petting from the init, or a cmdline/PON disable.
3. Only after the ceiling is removed do the earlier threads resume: HS-only ACM
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

Host-only research + one attended live test under a fresh SHA-pinned boot-only
`AGENTS.md` exception. No forbidden partitions, no PMIC/regulator/GDSC/GPIO
power *writes* (loading the stock watchdog driver is not a power write). Redact
serials from committed reports. Device stays recoverable to the Magisk baseline;
it is currently clean (M30 rollback verified boot/dtbo/vendor_boot baseline,
`uid=0`).
