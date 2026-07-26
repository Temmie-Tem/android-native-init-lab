# S22+ FYG8 P2.70 generic E3 QEMU runtime correction

Date: 2026-07-26 KST

Scope: H0 host-only. No device connection, D0, approval, Odin session,
transfer, reboot, partition write, or live authority occurred.

## Result

Exact generic-arm64 execution invalidated the frozen P2.69 candidate before
D0, localized two configfs symlink contract defects, and verified the
source-bound correction end to end through a virtual ACM host endpoint.

The corrected P2.60 runtime now passes:

- configfs mount and exact `statfs` magic;
- ACM gadget/function/config construction;
- canonical configfs function-link verification;
- `ttyGS0` publication and raw-mode setup;
- pre-UDC-bind queuing of the exact banner;
- dummy-hcd UDC bind and configured/high-speed state; and
- exact 49-byte receipt through guest `/dev/ttyACM0`.

Verdict: `PASS_P260_E3_GENERIC_QEMU_HOST_ONLY`.

This is a new host capability and a candidate correction. It is not S22+
device proof.

## Why this unit ran

P2.67 showed that the previous candidate reached E3 stage `0x88` but failed
configfs validation. P2.68 corrected the sysfs/configfs magic mismatch, and
P2.69 completed static, Full-LTO, package, and offline promotion checks.
Those checks still did not execute the generic configfs/ACM userspace path.

The long unattended interval made an H0 execution harness cheaper than
spending another F1 on a dynamic userspace defect. A complete SM8450 emulator
was explicitly rejected; only the vendor-independent E3 sequence was in
scope.

## Investigation trail

| Step | Hypothesis or action | Result | Disposition |
|---|---|---|---|
| 1 | Boot an official generic arm64 kernel with real configfs, libcomposite, dummy-hcd, gadget serial, and ACM modules | All required modules loaded and configfs stage `0x88` passed | Harness substrate valid |
| 2 | Execute the unchanged P2.69 gadget helper | `symlinkat` returned `ENOENT` at stage `0x89` | Deterministic candidate defect |
| 3 | Trace only the failing syscall | Target was `../../functions/acm.usb0`, destination was the config directory link | Creation-target assumption isolated |
| 4 | Compare with Linux configfs documentation and implementation | Configfs resolves the supplied target with `kern_path()` and documents creation from the gadget root | Relative target was resolved from PID1's `/`, not from the link directory |
| 5 | Use a temporary absolute creation target for diagnosis | Link creation succeeded; readback was `../../../../usb_gadget/g1/functions/acm.usb0` | Second deterministic mismatch found |
| 6 | Temporarily adapt both values | All generic E3 stages and exact ACM banner receipt passed | No further generic dynamic blocker found |
| 7 | Correct the real runtime and remove the diagnostic overlay | Exact, overlay-free QEMU execution passed | Source-bound correction verified |

The temporary overlays were private forensic tools. They are not present in
the final harness and never produce a promotable verdict.

## Root cause

The candidate used one string for two different configfs contracts:

```text
../../functions/acm.usb0
```

For creation, configfs resolves the supplied target through `kern_path()`.
With bare PID1 running from `/`, that string does not name the gadget function
and creation fails with `ENOENT`.

For verification, configfs exposes its own canonical relative representation:

```text
../../../../usb_gadget/g1/functions/acm.usb0
```

Even if creation were forced to succeed, the old verifier would reject this
canonical readback.

The runtime now uses separate authoritative values:

```text
creation: /config/usb_gadget/g1/functions/acm.usb0
readback: ../../../../usb_gadget/g1/functions/acm.usb0
```

Both values are parsed and checked by the versioned source contract. Mutating
either value fails before generic source-identity validation.

## Harness boundary

The checked harness:

- includes the exact P2.60 E3 runtime source;
- builds a static arm64 PID1;
- boots QEMU `virt` with an official Debian arm64 kernel;
- loads the exact generic USB module closure;
- replaces only Qualcomm role/UDC selection with `dummy_udc.0`;
- enforces a bounded process timeout; and
- stores generated initramfs, console output, and result JSON only in private
  storage.

It validates generic Linux runtime semantics. It does not validate:

- Qualcomm DWC3-MSM probe or peripheral-role behavior;
- S22+ SS/HS/eUSB2 PHY and repeater behavior;
- VBUS, Type-C, or Samsung notifier interaction; or
- physical USB enumeration on the target.

Those facts remain F1-only.

## Host validation

- runtime source SHA256:
  `767bd359de56cb24be84c4479cd01d4f710a676490c23f966617b996fe5cc612`;
- exact source-contract and QEMU tests: 18 passed;
- focused plus historical host regression suite: 119 passed;
- Python compilation: passed;
- static arm64 PID1 type check: passed;
- deterministic exact harness build: passed; and
- overlay-free QEMU execution: passed in under three seconds.

A fresh source-bound intent and exact userspace two-link closure also pass.
No Full-LTO build has run for this corrected source. The local host has only
15 GiB RAM and is below the qualification gate; the qualified build host was
not accessible during this H0 unit.

## Candidate disposition

P2.69's immutable AP and ready bundle remain unchanged but are live-ineligible.
Do not run D0 or F1 with them.

The next step is clean Full-LTO A/B from the P2.70 intent on the qualified
build host, followed by linked audit, deterministic packaging, independent
closure, and offline promotion. Connected D0 comes only after that line
passes.

## Primary references

- Linux USB gadget configfs:
  https://docs.kernel.org/usb/gadget_configfs.html
- Linux configfs:
  https://www.kernel.org/doc/html/latest/filesystems/configfs.html
- Linux configfs symlink implementation:
  https://github.com/torvalds/linux/blob/master/fs/configfs/symlink.c
