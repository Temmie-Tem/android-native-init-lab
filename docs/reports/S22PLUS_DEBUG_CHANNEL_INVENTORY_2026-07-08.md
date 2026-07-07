# S22+ (SM8450) Debug-Channel Inventory — Official + Unofficial (Host Survey, 2026-07-08)

Operator (Claude) host-only survey (shipped `/proc/config.gz`, live cmdline +
bootconfig, dtbo decode, vendor module list) + websearch. No device action.
Answers "what debug tools/features exist to open a control/observation channel."

## Ground truth from our own captures

Live kernel cmdline (retail unit): `console=null`, `nohyp_uart`, `loglevel=10`,
`sec_debug.debug_level=0x4f4c` (**LOW**), **`sec_debug.enable=0`**,
`sec_debug.force_upload=0x0`, `sec_debug.dump_sink=0x0`. Bootconfig:
`androidboot.debug_level="0x4f4c"`, `androidboot.cp_debug_level="0x55FF"`.
Shipped config: `MAGIC_SYSRQ=y`, `DEBUG_FS=y`, `PSTORE*=y`, `IKCONFIG=y`,
`BOOT_CONFIG=y`, `MODVERSIONS=y`, **`MODULE_SIG` not set**,
`SECURITY_DMESG_RESTRICT` not set; **off:** `CORESIGHT`, `STM`, `KGDB`,
`FUNCTION_TRACER`, `DYNAMIC_DEBUG`. `eud.ko` present in the vendor ramdisk.

Two consequences: (1) nothing prints because `console=null` + sec_debug is
`enable=0`/LOW; (2) the levers below are what turn a channel on.

## Tier 1 — official, no jig, highest value

1. **Samsung `debug_level=MID` (sec_debug) — the retained kernel console.**
   `*#9900#` SysDump → "Debug Level ... → MID" (Knox-documented; reversible).
   At MID a panic enters **Upload Mode / ramdump** and the full kernel log is
   retained to `samsung,kernel_log_buf` (→ `/proc/last_kmsg`, 2 MiB zstd),
   captured independent of `console=null` (sec_debug hooks the log ring, not the
   console device). **Caveat from our cmdline:** LOW *and* `sec_debug.enable=0`
   ship together, so MID must also flip `enable=1`; verify the menu does both, or
   patch vendor_boot bootconfig `androidboot.debug_level="0x494d"` (+ enable).
   SysDump also bundles: **Copy Kernel Log to SD**, Run dumpstate/logcat, Run
   CP/modem log, Forced CP crash dump, Silent Log, Wakelock Monitor.

2. **EUD — Qualcomm Embedded USB Debugger (in-SoC, over the same USB-C).**
   A mini on-chip USB hub exposing **COM (bidirectional UART serial console)** +
   **SWD (JTAG halt/step)** + trace — no jig, no soldering. Present on ~all
   Qualcomm SoCs since 2018; SM8450 supported; `eud.ko` in-hand. Enable pattern:
   `echo 1 > /sys/bus/platform/.../enable` + bring up the USB HS phy; host then
   enumerates an "EUD control interface" hub. This is a **live** console (beats
   post-mortem last_kmsg) and, via SWD, full JTAG. **Strongest card if it comes
   up** — it is the A90-serial-bridge equivalent for S22+.

## Tier 2 — host-side levers we control

3. **`console=` routing.** Currently `null`; patch boot/vendor_boot cmdline or
   bootconfig to route console (to the EUD COM tty, or `ttyMSM0` if a UART pad is
   used). Not required for sec_debug capture, but needed for a *live* text console
   without EUD.
4. **Custom debug kernel module.** `MODULE_SIG` is OFF → our own `.ko`
   (marker/printk-dumper/KASAN-lite, the A90 Tier-2 analog) is loadable — **but**
   `MODVERSIONS=y` means it must match the kernel vermagic/symversions (need
   `Module.symvers`/headers from the FYG8 kernel source we hold). A built-in
   observability primitive once vermagic is matched.
5. **debugfs + sysrq + ftrace-core + unrestricted dmesg** (all `=y`/on) — rich
   runtime introspection the moment we have *any* shell or console (e.g., over
   EUD COM or a future ACM).

## Tier 3 — unofficial / heavier

6. **EDL / Sahara DDR dump (9008).** Full memory image incl. the kernel log ring,
   but retail is auth-gated (needs a signed firehose programmer) → usually closed.
7. **Physical JTAG** (RiffBox/Medusa on pads) — EUD's SWD makes this unnecessary.
8. **Console-enabled custom kernel rebuild** — out of current S22+ scope (we do
   not rebuild the S22+ kernel yet); the FYG8 kernel source is on-hand if ever
   chartered.

## Not available here (confirmed off in shipped config)
CORESIGHT/STM (SoC trace), KGDB (kernel gdb stub), FUNCTION_TRACER,
DYNAMIC_DEBUG. Don't plan around these.

## Recommendation
Two cards dominate, both no-jig:
- **debug_level=MID** — cheapest first proof (menu/bootconfig; zero-flash Android
  sysrq-panic positive control), gives a *retained* post-mortem kernel log.
- **EUD** — higher ceiling: a *live* serial console **and** JTAG over USB-C. Worth
  a dedicated host-only feasibility probe (does `eud.ko` enable, does the host
  enumerate the EUD hub, does COM carry the console). If EUD's COM comes up, the
  S22+ has a first-class interactive channel and the blind phase is over.
Order: debug_level=MID (validate the retained log now) → EUD (aim for the live
console/JTAG) → UART jig only if both somehow fail.

## Sources
- Qualcomm EUD (COM/SWD/trace over USB-C, enable via sysfs): https://lwn.net/Articles/984085/ , https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/ , https://hackaday.com/2025/07/10/embedded-usb-debug-for-snapdragon/
- Samsung `*#9900#` SysDump options incl. Debug Level→MID, Copy Kernel Log, dumpstate/CP ramdump: https://docs.samsungknox.com/admin/knox-platform-for-enterprise/troubleshoot/get-device-logs/ , https://xdaforums.com/t/ref-servicemode-how-to-make-your-samsung-perform-dog-tricks.2734094/
- Kernel panic Upload Mode / ramdump: https://itechify.com/2024/02/18/fix-kernel-panic-upload-mode-error-samsung/
