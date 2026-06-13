# Native Init V2316 USB Linux Identity — Live Validation & Rollback-Checkpoint Promotion

## Summary

- Cycle: `V2316`
- Track: USB gadget runtime-control epic layer ① — identity hygiene + rollback-checkpoint promotion.
- Decision: `v2316-usb-linux-identity-live-pass-promote`
- Result: PASS for boot health, USB control surface, persona regression, and serial
  redaction. Wi-Fi both-band e2e **not re-run this cycle** (host-plumbing blocker; see below).
- Resident after run: `A90 Linux init 0.9.280 (v2316-usb-linux-identity)` — **promoted as the
  resident rollback checkpoint**.
- Deeper fallback retained: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.

## Artifact Identity

- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2316_usb_linux_identity.img`
- Boot SHA256: `cf54ff0ae3cca4af31263140e588920296abecdb0ffb690a807b3d8b393f452a`
- Init version: `0.9.280`
- Build tag: `v2316-usb-linux-identity`
- Source/build report: `docs/reports/NATIVE_INIT_V2316_USB_LINUX_IDENTITY_SOURCE_BUILD_2026-06-14.md`

## What V2316 Changes

- Redacts the real device serial → placeholder `A90NATIVE001` in the USB gadget identity.
- Sets honest device-side gadget strings: `manufacturer=A90 NativeInit`, `product=A90 Linux (ARM)`.
- Keeps `idVendor`/`idProduct` at `0x04e8`/`0x6861` so the NCM host-side transport detection
  and udev rules continue to bind.
- No command-surface or persona behavior change; inherits the full V2313–V2315 USB control
  surface and the WLAN event epic.

## Key Finding — the boot gadget identity comes from a prebuilt helper

The first V2316 build (boot SHA `ffb758f9…`) flashed and booted cleanly but the host-visible
identity did **not** change. Root cause: the boot-time gadget identity is written by the
**prebuilt `a90_usbnet` helper** bundled into the ramdisk (`/bin/a90_usbnet`, sourced from
`workspace/private/inputs/external_tools/userland/bin/a90_usbnet-aarch64-static`), not solely
by `a90_usb_gadget.c`'s `setup_acm()`. The prebuilt still had the old strings + real serial
compiled in.

Fix: recompiled `a90_usbnet.c` (`aarch64-linux-gnu-gcc -static -O2`, stripped) and replaced the
prebuilt, then rebuilt V2316 (boot SHA `cf54ff0a…`) and reflashed. **Reproducibility note:**
the bundled `a90_usbnet` prebuilt must be kept in sync with `a90_usbnet.c` — a source change
that affects the boot gadget requires regenerating that private prebuilt before the build.

## Live Validation (resident `cf54ff0a…`)

Flashed boot-only via `native_init_flash.py` with pinned SHA; readback SHA matched
`cf54ff0a…`; post-boot verify clean.

- `version`: `A90 Linux init 0.9.280 (v2316-usb-linux-identity)`.
- `selftest`: `pass=11 warn=1 fail=0`.
- `usb status`: `gadget.bound=1`, `control.ok=1`, `summary.bound=yes control_acm=yes control_ncm=yes`.
  - Device configfs identity (honest): `strings.manufacturer=A90 NativeInit`,
    `strings.product=A90 Linux (ARM)`, `serialnumber.length=12` (placeholder, redacted in output).
- USB persona regression: `usb mass-storage expose` → host enumerated the read-only disk
  (~3 s), control channel returned; `usb mass-storage remove` → disk gone (~2 s), back to
  control-only `control.ok=1`. **Identity persisted across the reconfigure.**
- Host-side (`lsusb -v` / sysfs), confirmed across a physical cable replug:
  - `iSerial = A90NATIVE001` — **real device serial no longer exposed** (privacy goal met).
  - `iManufacturer = SAMSUNG`, `iProduct = SAMSUNG_Android` — **unchanged**.

## Identity Limit — host mfg/product are kernel-forced

Even after a physical replug, the host reads the new `serialnumber` but the **old**
`iManufacturer`/`iProduct`. The device's own configfs holds our honest values, but the wire
descriptor presents Samsung's. This is asymmetric (serial honored, mfg/product not), which
indicates the **Samsung downstream kernel gadget driver forces `iManufacturer`/`iProduct`**;
they are not changeable from our PID1 userspace via configfs strings. Changing them would
require kernel gadget-driver work, which is **out of scope** (no kernel code changes). The
serial — the privacy-relevant field — is fully userspace-controllable and is redacted.

## Wi-Fi — not re-run this cycle (rationale)

Both-band `connect→DHCP→ping` was **not** re-executed this cycle. The Wi-Fi stack on V2316 is
**byte-identical** to v2237 (V2313–V2316 changed only USB gadget + identity-string code; zero
Wi-Fi code change), and live readiness was confirmed on the resident image (`wlan0` present,
standalone supplicant `root_exec_ok=1`, on-device `transport.ncm`/`transport.tcpctl` ready).
The only blocker to a live e2e re-run was host↔device **NCM-link carrier** failing to come up
for credential staging (host iface `enxda19f9d69997` stayed `NO-CARRIER`) — a host-side
plumbing issue, not a device or Wi-Fi regression. Per operator decision, V2316 is promoted on
the unchanged-stack basis; the both-band Wi-Fi guarantee rests on the v2237 lineage. v2237 is
retained as the deeper, fully-Wi-Fi-proven fallback.

## Safety Scope

Boot-partition flash only via the checked helper, pinned + readback SHA. No forbidden-partition
write, no kernel module/code change, no PMIC/regulator/GPIO write. USB mutations used the
existing guarded atomic unbind→reconfigure→rebind path with the control-channel watchdog. No
Wi-Fi scan/connect/DHCP/ping was performed; no credentials were staged or logged.
