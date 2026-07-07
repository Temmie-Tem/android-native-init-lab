# S22+ — Enable ramoops to Get the Kernel Console Without UART (Operator Steer, 2026-07-08)

Operator (Claude) host-only steer, operator-user approved. No device action here.
This unlocks on-device kernel-console retention so the QMP PHY/dwc3 fault reason
becomes readable after rollback — the "UART without hardware" path.

## Why every pstore capture was empty (root cause found)
The device HAS the pstore infrastructure built in — `CONFIG_PSTORE=y`,
`CONFIG_PSTORE_RAM=y`, `CONFIG_PSTORE_CONSOLE=y`, `CONFIG_PSTORE_PMSG=y` — and the
DT reserves a fully-configured ramoops region (live DT:
`/reserved-memory/ramoops_region` with `pmsg-size=0x200000`, console-size, and a
`reg` address). The ONLY reason `/sys/fs/pstore` was always empty is:

```
/proc/device-tree/reserved-memory/ramoops_region/status = "disabled"
```

The region is reserved and sized; the node is just switched off (set by DTS
`fragment@116`, `status = "disabled"`). The prior "empty pstore" results were NOT
DDR loss — they were this disabled switch. ramoops persists across warm reboots
(a watchdog reset is warm; download-mode entry and odin are warm), so once
enabled it should reliably retain the last native-init boot's console.

## The patch (host-only)
In the **vendor_boot DTB**, set the `ramoops_region` node
`status = "disabled"` → `status = "okay"`. One property. The region address/size
and console/pmsg sizes already exist, so there is no memory conflict and nothing
else changes. Use a DT-aware tool (`fdtput`/`dtc` round-trip), not a raw
same-length byte poke, because the fdt property length changes.

## Capture flow
1. Host-only: unpack stock vendor_boot, patch the DTB ramoops status to "okay",
   repack (preserve everything else), readback-verify only that property changed.
2. Attended live: flash the patched vendor_boot (one-time) alongside a native USB
   candidate boot (e.g. M18 or the QMP subset). Both are needed because the fault
   is in the native boot; the patched vendor_boot only enables the recorder.
3. Native init runs, the QMP PHY/dwc3 probe faults, the kernel logs the exact
   abort (GDSC/clk/regulator/PLL-lock/SError/PC) to the ramoops console region.
4. Recover: manual download → roll back to the pinned Magisk boot. Keep the
   patched vendor_boot for the read, or restore stock vendor_boot after.
5. Boot Android and read `/sys/fs/pstore/console-ramoops` (and `dmesg-ramoops`) =
   **the native-init kernel console, including the fault reason — no UART.**
6. When done, restore stock vendor_boot for a clean state.

## Safety framing (this expands scope beyond boot-only — needs a new exception)
- `vendor_boot` is **not** a forbidden partition (not efs/sec_efs/modem/vbmeta/
  vbmeta_system/bootloader/dsp/keydata/persist/RPMB/vm-bootsys). It is
  odin-flashable and stock-recoverable (stock vendor_boot is in the FYG8
  firmware we hold).
- The change is minimal and safe: enabling an already-reserved debug-log region.
- Requires a **new SHA-pinned `vendor_boot`-only `AGENTS.md` exception** (patched
  vendor_boot AP hash + stock vendor_boot rollback hash) + attended operator ack
  + the stock vendor_boot staged for rollback. Do not touch any other partition.

## Why this is the right next move if M18 loops
It is the highest-value step short of buying UART: it converts the entire blind
bisect into a single readable fault. Instead of permuting module subsets and
guessing, we read exactly which rail/GDSC/clock the QMP PHY/dwc3 probe needs, fix
that specific dependency, and proceed. It also permanently unlocks console
observability for all later native-init S22+ work (a general win, like the A90
serial bridge).

Precedent note: SM8450 USB gadget from a minimal (non-Android) init is solved in
mainline Linux / postmarketOS (Linaro day-1 support), so the goal is feasible;
the wall is the vendor `dwc3-msm` Android coupling, which the ramoops console
will let us see precisely.

## Sequence recommendation
1. M18 (in flight) — if it parks, proceed to ACM host-only; ramoops not needed yet.
2. If M18 loops → build the ramoops-enabled vendor_boot (host-only) + new
   SHA-pinned vendor_boot exception → attended capture run → read pstore console
   → fix the exact dependency. This likely ends the blind phase without UART.
3. UART only if, against expectation, the enabled ramoops still retains nothing.

## Discipline
Host-only build + dry-run; attended live only; new SHA-pinned vendor_boot-only
exception + boot rollback + stock vendor_boot restore; no forbidden partitions;
no secrets committed. Device is on the known-good Magisk baseline.
