# S22+ — EUD Feasibility Probe (Operator Steer, 2026-07-08)

Operator (Claude) host-only steer, operator-user "go." No device action in this
doc. Runs in parallel with the sec_debug/MID card; EUD has the higher ceiling —
a **live** serial console **and** JTAG over the existing USB-C, the true
A90-serial-bridge equivalent for S22+.

## Why EUD is worth a dedicated probe
Qualcomm's Embedded USB Debugger is an on-chip mini USB hub exposing COM (a
bidirectional UART serial console), SWD (JTAG halt/step), and a trace peripheral
over the same USB-C port — no jig, no soldering. Present on ~all Qualcomm SoCs
since 2018; SM8450 is supported; `eud.ko` is in our vendor ramdisk. If EUD's COM
comes up, the blind phase ends: we get a live kernel console (and, via SWD, full
halt/step) instead of post-mortem `last_kmsg` guessing. The one real unknown is
whether EUD is fused/secured off on this retail unit — that is exactly what the
probe resolves, cheaply, before any native-init integration.

## The probe — phased, reversible, no flash

### Phase A — read-only inventory (zero risk, do first, over adb on rooted Android)
- `eud.ko` state: is it loaded / bound? `lsmod | grep eud`, `dmesg | grep -i eud`.
- EUD sysfs/platform device: locate it, e.g.
  `ls -l /sys/bus/platform/devices/ | grep -i eud`, and look for an `enable`
  attribute and mode/secure/attach state; read (do not write) current values.
- EUD DT node + address: confirm the `qcom,msm-eud`/EUD reg in the live
  `/proc/device-tree` (it was not in the dtbo string scan → likely in the main
  dtb; confirm it exists and its `status`).
- Any `eud`/`secure`/`fuse` gating hints in dmesg or the node.
All read-only; commit the inventory as evidence. This alone tells us if EUD is
present + not obviously fused off.

### Phase B — attended reversible enable + host enumeration (needs operator ack)
Only if Phase A shows EUD present and an `enable` control:
1. Operator watches the host. On the device (rooted Android):
   `echo 1 > /sys/.../eud/enable` (reversible; `echo 0` restores).
2. **Expect adb/USB to reconfigure** — enabling EUD reroutes the USB-C port to
   the EUD hub, so adb may drop. That is normal, not a failure.
3. On the host: `lsusb` / `dmesg` for the EUD enumeration — a ~7-port hub with an
   "EUD control interface" device is the success signal.
4. If the hub appears, probe the COM (UART) interface: does a serial endpoint
   appear, and does it carry any kernel console text? (console is currently
   `console=null`; a follow-up may need `console=` routed to the EUD COM.)
5. Restore: `echo 0 > /sys/.../eud/enable`, confirm normal adb/USB returns.

### Decision gate
- **Host enumerates the EUD hub** ⇒ EUD is live. Pursue: route the kernel console
  to EUD COM (cmdline/bootconfig) and read the native-init boot live; SWD/JTAG is
  a bonus. This becomes the primary S22+ observation channel.
- **`enable` write has no host effect / EUD fused off / node absent** ⇒ EUD is not
  available on this retail unit. Fall back to the sec_debug/**debug_level=MID**
  retained-log card (already in flight), then UART only if both fail.

## Safety framing
- Phase A is read-only over adb — zero risk, no gate needed beyond normal rooted
  access.
- Phase B is a **runtime sysfs write on rooted Android**, reversible (`echo 0`),
  **not** a flash, **not** a partition write, **not** PMIC/GPIO/power. It only
  reconfigures the USB-C port for debug. It is attended (operator watches host
  enumeration and can `echo 0` to restore). No forbidden partition, no secrets
  committed. Do not confuse EUD-enable with any boot/vendor_boot flash — no flash
  is involved.
- If the loop implements a helper, keep it host/adb-side, make the enable an
  explicit ack-gated step separate from the read-only inventory, and record only
  redacted metadata (no device serial in committed logs — strip `adb devices`
  output per the commit-hygiene rule).

## Sequencing
Do Phase A now (host-only/adb, zero risk) alongside the sec_debug/MID work. Only
schedule Phase B (attended enable) after Phase A confirms EUD is present with an
enable control. Two no-jig cards run in parallel: MID (retained log, cheapest) and
EUD (live console/JTAG, highest ceiling).

## Sources
- EUD COM/SWD/trace over USB-C, sysfs enable: https://lwn.net/Articles/984085/ ,
  https://www.linaro.org/blog/hidden-jtag-qualcomm-snapdragon-usb/ ,
  https://hackaday.com/2025/07/10/embedded-usb-debug-for-snapdragon/
