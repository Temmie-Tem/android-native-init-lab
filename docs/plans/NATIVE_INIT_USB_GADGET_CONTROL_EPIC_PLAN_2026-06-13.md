# USB Gadget Runtime-Control Epic — Native Init Plan (2026-06-13)

Design for a native-init **USB gadget control surface** (`usb` command): inventory
the live gadget, and reconfigure its personas/functions at runtime. This is
**layer ① of three** (see `docs/reports/TWRP_RECOVERY_TEARDOWN_DEVICE_REFERENCE_2026-06-13.md`
§1/§5): the foundation under ② a standard reconnecting control channel
(adb-over-ffs) and ③ phone-controls-host (HID/BadUSB). This plan covers ① only;
② and ③ are separate follow-on epics.

## Why ① is the foundation

Today native init brings up a **fixed gadget at boot** (NCM + the control ACM
serial). There is no runtime visibility or control of it. Every USB-side capability
(BadUSB, mass-storage, identity spoof, on-demand connect, adb persona) requires
**runtime gadget reconfiguration** — that is what this epic builds. The `usb`
command is the *control surface*; capabilities arrive when personas are added on
top.

## Grounding (already in repo)

- **Gadget recipe** (TWRP teardown §1): configfs root `/config/usb_gadget/g1`,
  Samsung `idVendor=0x04E8`, function dirs (`mass_storage.0`, `acm.0`, `ffs.adb`,
  `ffs.mtp`, `ffs.ptp`), config `configs/b.1`, activate by `symlink fn ->
  configs/b.1/fN` then write controller to `UDC` (unbind = write `"none"` first),
  enable via `setprop sys.usb.configfs 1` + `/sys/class/udc/<ctrl>/device/../mode
  peripheral`.
- **Compiled-in functions** (kernel capability inventory): `USB_F_HID`,
  `USB_F_MASS_STORAGE`, `USB_F_FS`, `USB_CONFIGFS_*` all `=y`.
- Native init already drives a configfs gadget (NCM) — this is incremental on that.

## THE critical safety constraint (read first)

**The control channel lives on the same UDC as everything else.** Native init is
reachable via the **USB ACM serial bridge** (TCP 54321) and **NCM** — both are
gadget functions bound to the one UDC. Linux **cannot modify a bound gadget's
configs**: adding/removing a function requires `UDC -> "none"` (unbind), reconfigure,
then rebind. **During unbind, every USB function drops — including the channel the
command arrived on.**

Therefore the absolute rules for this epic:

1. **Never saw off the branch you sit on.** A reconfigure that arrives over USB must
   be **atomic**: unbind → reconfigure → **rebind**, executed device-side as one
   bounded operation with an **auto-rebind watchdog** (if rebind does not complete
   within a short timeout, restore the known-good gadget).
2. **Control functions are sacred.** NCM + control ACM are **always** present in the
   rebuilt config. Only **auxiliary** functions (HID, mass_storage) are added/removed.
   Never produce a config without the control functions.
3. **Boot is the deterministic fallback.** The boot-time gadget setup must *always*
   bring up NCM + control ACM regardless of prior runtime state. A reboot is a
   guaranteed recovery to a controllable device. (Serial UART bridge, if independent
   of the USB ACM, is an additional backstop — U1 must determine this.)
4. If the device could be left with **no control channel**, do **not** ship that path.

## Staged units (one V-iteration each)

### U1 — `usb status` / inventory (read-only) — **do first**
Read `/config/usb_gadget/*` and `/sys/class/udc/*`; report: UDC name + bind state,
configs, the **function list (and which are the control functions)**, `idVendor`/
`idProduct`, strings. Pure read; **serial-self-validatable** (no host needed). This
is first **because we must know the exact current control-channel topology before
touching it** (rule 1–3 depend on it). Done-signal: `usb status` over the bridge
prints the live gadget, `selftest fail=0`.

### U2 — atomic auxiliary-function add/remove
Add or remove an **auxiliary** function (start with `mass_storage.0` — least likely
to wedge a host) via the atomic unbind→reconfigure→rebind with an auto-rebind
watchdog and the known-good restore. Keep NCM+ACM in every rebuilt config. Validate
that **the control channel returns** after the cycle (NCM/serial reachable again).
This is the risky unit — design it defensively; bound the unbound window.

### U3 — first real persona
Expose one persona end-to-end on top of U1/U2. Recommended `mass_storage` (host sees
a backing file as a USB disk) **or** HID if the multitool path is preferred. Host-side
validation required (plug into a PC). Keep it bounded.

## Validation

- **U1**: serial bridge `usb status` + `selftest` — fully on-device.
- **U2/U3**: require **host-side** validation (plug phone into a PC; confirm the new
  function enumerates AND that NCM/serial control returns after a reconfigure). This
  is a **new validation modality** vs the serial-only selftest used so far — the
  report must note operator host steps.
- Every device step: boot-only flash via the checked helper, pinned SHA, post-boot
  `version`/`status`/`selftest fail=0`, auto-rollback to `v2237` on failure.

## Safety gates (binding — mirror `AGENTS.md`)

- Boot partition only; `v2237` rollback target; never forbidden partitions.
- **Never leave the device without a control channel** (the §"critical constraint"
  rules are hard requirements, not guidance).
- No PMIC/regulator/GPIO writes; no kernel code/module changes; closed
  observation/security phases stay closed. Creds N/A (no Wi-Fi action).

## Build vs borrow

Gadget configfs glue + the atomic-reconfigure watchdog = **ours** (no off-the-shelf
PID1 equivalent; this is the research substance). If a later epic adds the **adb**
persona, `adbd` itself is **borrowed** (standard). `usb status`/switch is ours.

## Out of scope (separate follow-on epics)

- ② **adb-over-ffs reconnecting channel** (fast + stable + reboot auto-reconnect) —
  builds on U1/U2 but is its own epic.
- ③ **HID/BadUSB host control** — builds on U1/U2; offensive multitool persona.
- Both are deferred until ① (U1–U3) is solid.
