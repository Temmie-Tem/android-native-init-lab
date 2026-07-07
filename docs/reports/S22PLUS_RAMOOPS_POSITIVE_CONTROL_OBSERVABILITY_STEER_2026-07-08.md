# S22+ — Get the Kernel Console Before More Bring-Up (Ramoops Positive-Control Steer, 2026-07-08)

Operator (Claude) host-only steer, operator-user approved. No device action here.
This redirects the S22+ USB epic from **blind park-vs-loop bisection** to **buying
observability first**, the way the A90 serial bridge was the early unlock that made
every later A90 iteration cheap.

## Why progress stalled (name it plainly)

The fault is already localized: **M13** (no-module freestanding init) **parks**;
**M15** (insmod `phy-msm-ssusb-qmp.ko`) **bootloops**. The wall is the QMP PHY /
dwc3 runtime power/clock/GDSC/RPMh-vote sequence that Android userspace normally
orchestrates and a bare init does not.

But we cannot **read** the fault. All three console channels are down:
1. `reboot("download")` beacon — proven unreliable by disassembly (M10/M11); the
   M19 C000 / M20A "floor" runs are debugging *this beacon's noise*, not USB.
2. pstore/ramoops — DT `reserved-memory/ramoops_region status = "disabled"`, so
   `/sys/fs/pstore` is empty.
3. UART — needs a physical jig (not purchased).

So M14→M21 is blind bisection over ~441 modules + complex power sequencing with a
**1-bit park/loop signal**. That does not converge; it is the entire slowdown.
A90 was cheap because the console was effectively free from early on. On S22+ we
went straight to bring-up and are now paying the observability debt.

## The ramoops attempt was mis-executed, not refuted

The prior ramoops capture (`0116dd61`, run `...ramoops_dtbo_m18_capture...`):
- enabled ramoops via a **DTBO overlay**, not the vendor_boot DTB direct patch the
  earlier steer specified — `status` override via DTBO is fragile;
- ran **no positive control** — it never confirmed the region was actually enabled
  in the native boot;
- pointed straight at the faulting **M18** boot, got an **empty pstore**, which is
  ambiguous (channel-broken vs enable-didn't-take vs fault-silent). The report
  itself asks *"did the DTBO ramoops node not create a retained pstore path?"*

Conclusion: **the cheapest no-UART channel is still open.** It was done wrong.

## The decisive experiment: enable ramoops RIGHT + positive control

### Step 1 — enable via direct vendor_boot DTB patch (not DTBO)
Host-only: unpack stock vendor_boot, `fdtput` the DTB
`/reserved-memory/ramoops_region` `status` from `"disabled"` → `"okay"` (use a
DT-aware round-trip; the property length changes, so no raw byte poke), repack,
readback-verify only that property changed. Region address/size and
console/pmsg sizes already exist — no memory conflict.

### Step 2 — POSITIVE CONTROL before pointing at the fault
Flash the ramoops-enabled vendor_boot alongside **M13** (the *known-good, parking,
no-module* init). On-device in that boot, confirm
`/proc/device-tree/reserved-memory/ramoops_region/status == okay` and console-size
> 0; then roll back and read `/sys/fs/pstore/console-ramoops`.
- **M13's clean boot console is present** ⇒ channel is alive. Proceed to Step 3.
- **Even M13's clean console does not persist** ⇒ ramoops is genuinely dead here
  (region not written / wiped by the reset path). Stop; go to EUD, then UART.

This single control removes the "channel-broken vs fault-silent" ambiguity that
made the M18 capture useless.

### Step 3 — point the proven channel at the fault
Flash ramoops-enabled vendor_boot + **M15** (or the M18 substrate) that loads the
QMP PHY. It faults, the kernel logs the abort (unhandled fault / regulator /
GDSC / clk / PLL-lock name, or at minimum the last successful line before the
register touch), roll back, read `console-ramoops` = **the exact fault, no UART.**

## Parallel, near-free: read the Samsung reset/PON reason precisely
M19/M20A `last_kmsg` shows `panic=absent, Oops=absent, not syncing=absent` yet it
bootloops — consistent with a **watchdog / async-SError reset** (PHY touches an
unpowered/unclocked register → bus hang → watchdog), not a clean panic. Read the
reset/PON reason register precisely (it is retained; `reboot_reason` is present in
`last_kmsg`) to confirm **watchdog-bark vs panic vs SError**. That is one coarse
bit we can get with zero new flashes and it directly tests the hang hypothesis
(and warns whether ramoops will even have a printed smoking gun vs only the
last-line-before-hang).

## What to stop
Do **not** make M20B/M20C or further M21x floor-discriminators the primary path.
They characterize the unreliable `reboot("download")` beacon — noise — not the USB
fault. M21A may still run if already gated, but it is not the high-value unit; the
observability investment is.

## Fallback order if ramoops proves dead
1. **EUD** — SM8450's in-SoC Embedded USB Debugger exposes the kernel console over
   the *same USB-C cable* (no jig). `eud.ko` is present. Qualcomm's intended debug
   path. Bring-up cost, but zero hardware purchase.
2. **UART jig** — definitive; buy it only after ramoops (Step 2 control) and EUD
   are both shown dead.

## Safety framing (needs a fresh exception; vendor_boot is not forbidden)
`vendor_boot` is odin-flashable and stock-recoverable (stock vendor_boot is in the
FYG8 firmware we hold); it is **not** on the forbidden list
(efs/sec_efs/modem/vbmeta/vbmeta_system/bootloader/dsp/keydata/persist/RPMB/
vm-bootsys). The change enables an already-reserved debug-log region — minimal and
safe. Requires a **new SHA-pinned `vendor_boot`-only `AGENTS.md` exception**
(patched vendor_boot AP hash + stock vendor_boot rollback hash) + attended ack +
stock vendor_boot staged for rollback. Native boot candidates keep their existing
boot-only gates. Restore stock vendor_boot when done. No other partition, no
PMIC/GPIO/power writes, no secrets committed. Device stays on the Magisk baseline.

## Bottom line
Stop bisecting blind. Enable ramoops the right way, prove the channel with a
positive control on the parking M13, then read the QMP PHY fault in one boot. This
is the highest-value step short of UART and likely ends the blind phase without it.
