# S22+ FYG8 P2.59 E3 ACM-banner focused analysis

Date: 2026-07-25 KST
Tier: H0
Status: `ANALYSIS_COMPLETE`
Device contacted: no
Build or image produced: no

## Question

P2.58A proved the exact 60-module E2 sequence, publication of
`a600000.dwc3`, and the terminal userspace path. This unit asks what is still
required to prove E3: one exact byte stream from native PID1 to the host over a
generic ACM gadget.

The analysis is deliberately narrower than a new USB bring-up investigation.
It examines:

1. whether the qualified P2.58A kernel and module plan already contain the
   generic ACM closure;
2. the smallest race-resistant device-side ordering;
3. the missing Process v2 host observation and PASS semantics; and
4. whether older M34/O3F results are evidence against that path.

No candidate, kernel, manifest, or device state changed.

## Inputs

- `docs/reports/S22PLUS_FYG8_P258A_F1_LIVE_TERMINAL_UDC_PASS_2026-07-25.md`
- `docs/plans/S22PLUS_FYG8_POST_PID1_OBSERVABLE_RUNTIME_ARCHITECTURE_2026-07-21.md`
- exact P2.58A `.config`, `vmlinux`, materialized runtime, and plan under
  `workspace/private/outputs/s22plus_fyg8_p258a_v2/`
- `workspace/public/src/native-init/s22plus_init_o3f_freestanding_acm.c`
- `workspace/public/src/scripts/revalidation/device_action_f1_v2.py`
- `workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py`
- `docs/reports/NATIVE_INIT_V3417_S22PLUS_O3F_FREESTANDING_ACM_LIVE_MISS_2026-07-10.md`
- `docs/reports/S22PLUS_NATIVE_INIT_M34_S3_LIVE_RESULT_2026-07-09.md`
- `docs/reports/S22PLUS_NATIVE_INIT_M35_STOCK_GADGET_GAP_ANALYSIS_2026-07-09.md`
- `docs/reports/S22PLUS_S3_ENUMERATION_ROLE_LEVER_STOCK_2026-07-09.md`
- Linux configfs gadget and gadget-serial documentation and source.

The FYG8 vendor source checkout on the remote build host was not reopened in
this unit. The exact qualified binary and config were available locally. The
load-bearing generic ACM lifecycle below is verified against that binary, so
source access is not a blocker for E3 design.

## Confirmed E2 boundary

The P2.58A live record contains:

```text
generation 80: stage=0x87 item=11 outcome=progress detail=0
generation 81: stage=0x8f item=0  outcome=terminal-success detail=0
```

This proves the 60 module operations, provider/bind chain, exact real UDC
membership, and the userspace terminal path. It does not prove configfs gadget
construction, peripheral mode, UDC binding to a gadget, host enumeration, or
ACM bytes.

Those omissions are the E3 work. Reopening module-provider analysis without a
new contradictory coordinate would discard rather than use the P2.58A result.

## Generic ACM is already in the qualified kernel

The exact P2.58A `.config` contains:

```text
CONFIG_CONFIGFS_FS=y
CONFIG_USB_DWC3=y
CONFIG_USB_DWC3_DUAL_ROLE=y
CONFIG_USB_GADGET=y
CONFIG_USB_LIBCOMPOSITE=y
CONFIG_USB_F_ACM=y
CONFIG_USB_U_SERIAL=y
CONFIG_USB_CONFIGFS=y
CONFIG_USB_CONFIGFS_ACM=y
```

The exact `vmlinux` contains the expected executable closure, including:

```text
acm_alloc_instance
acm_alloc_func
configfs_composite_bind
gserial_alloc_line_no_console
gserial_connect
gs_open
gs_write
gs_start_io
gs_start_tx
usb_add_gadget_udc
dwc3_gadget_init
```

The exact 60-entry module plan contains the qualified platform, PHY, Type-C,
and DWC3 modules but no `usb_f_ss_acm.ko`. That is not a missing dependency:
E3 uses the built-in generic configfs function `acm.usb0`, not Samsung's
separate `ss_acm.0` function.

Therefore the default E3 hypothesis is:

- keep the exact 60-module plan and its proven order;
- do not add `usb_f_ss_acm.ko`, another provider, or a kernel config;
- add only a versioned post-E2 userspace sequence and host observer.

Any module-plan growth now requires positive contrary evidence.

## A race-resistant one-banner ordering

The exact binary resolves the important host-open race.

### 1. Function creation creates the gadget-side TTY before UDC bind

Disassembly of the qualified `vmlinux` shows:

```text
acm_alloc_instance
  -> gserial_alloc_line_no_console
     -> tty_register_device_attr
```

Creating `functions/acm.usb0` therefore allocates the line and publishes the
`ttyGS0` class device before the gadget is bound to a UDC. PID1 can read
`/sys/class/tty/ttyGS0/dev`, create the exact character node under the already
proven non-`nodev` `/dev` tmpfs, and open it before host enumeration.

### 2. A disconnected write is queued, not discarded

The qualified `gs_write` unconditionally inserts bytes into the TTY FIFO. It
only calls `gs_start_tx` immediately when `port_usb` is already present.
`gserial_connect` stores the active USB port and calls `gs_start_io`, which
calls `gs_start_tx`.

This matches the upstream gadget-serial contract: opening a disconnected
`ttyGS` allocates the circular buffer, writes queue into it, and connection
starts the I/O stream.

Consequently E3 should:

1. create and verify `acm.usb0`;
2. derive and materialize `/dev/ttyGS0`;
3. open `/dev/ttyGS0`;
4. write one short exact banner and require the full byte count;
5. keep that file descriptor open;
6. set controller speed and peripheral mode with exact readback;
7. bind `a600000.dwc3` last; and
8. park without closing the TTY.

Closing the TTY before connection is forbidden for this design. The
disconnected `gs_close` path frees the FIFO, which would discard the queued
banner. Keeping one owned descriptor open through the terminal park avoids
both that loss and a host polling race.

This is preferable to repeated banner writes. It gives one deterministic
payload, does not need the host to win a timing race, and leaves E4 request
handling out of scope.

## Configfs and role sequence

The generic kernel contract requires gadget, strings, configuration, function,
and function link creation before writing the UDC name. Writing the UDC is the
enable step.

The FYG8 stock evidence adds two target-specific facts:

- the exact controller is `a600000.dwc3`; and
- the effective native-init role lever is
  `/sys/devices/platform/soc/a600000.ssusb/mode=peripheral`, not the empty
  `/sys/class/usb_role` path.

The E3 sequence should also pin both gadget and controller speed to
`high-speed`, then verify every writable attribute by a strict bounded
readback. `soft_connect`, descriptor parity with the Samsung composite gadget,
DT changes, and Type-C policy emulation remain excluded unless a later exact
coordinate requires one of them.

## Available retained-stage geometry

The existing sequence ends its gates at `0x87` and reserves terminal `0x8f`.
The seven unused stage values `0x88..0x8e` fit the minimal E3 sequence without
moving any proven module or E2 gate coordinate:

| Stage | Proposed proof coordinate |
|---|---|
| `0x88` | configfs mounted and filesystem type read back |
| `0x89` | gadget/config/descriptor tree created and read back |
| `0x8a` | `acm.usb0` linked and exact `ttyGS0` class device present |
| `0x8b` | exact `/dev/ttyGS0` node materialized and opened |
| `0x8c` | one exact profile-bound banner fully queued |
| `0x8d` | high-speed and peripheral mode writes read back exactly |
| `0x8e` | exact UDC bind read back |
| `0x8f` | E3 device-side terminal success |

This is a design input, not an activated contract. A new versioned contract
must define the longer sequence explicitly. Under that contract terminal
`0x8f` becomes generation 88 rather than generation 81; old P2.58A records
remain interpretable only by their old source contract.

Every coordinate must use strict bounded reads, exact path/type checks, and
first-failure errno evidence. The `ttyGS0/dev` parser must reject overflow,
trailing data, non-character nodes, and a created node whose `st_rdev` differs
from the sysfs major/minor.

## Process v2 has no ACM observer yet

The current Samsung live backend does this after candidate transfer:

1. wait for the Download endpoint to disappear;
2. sleep for the manifest timeout; and
3. return `candidate_execution_proven=false`.

The manifest currently permits only:

```text
observation = {timeout_sec, acceptance}
```

The current final PASS is based on completed candidate transfer plus accepted
post-rollback retained evidence. It does not consume the candidate observation
result. The `candidate_boot_ready` timeline event also derives its `proof`
field from transfer completion and Download-endpoint absence, not from a live
ACM result.

That behavior was sufficient for retained-only E2. It cannot express E3.

## Minimal host extension

E3 needs one versioned Process v2 extension, not another candidate-specific
live helper:

- a typed, bounded ACM observer in the manifest;
- expected VID, PID, synthetic run-bound USB serial, driver, and exact banner;
- one unambiguous new USB/TTY identity on the target's known physical topology;
- direct host file-descriptor ownership with raw TTY mode;
- bounded `select`/read, a small fixed byte cap, exact byte equality, and a
  short no-extra-byte settle;
- exclusive private raw evidence and a structured receipt flushed before the
  `OBSERVED` transition;
- `candidate_boot_ready.proof=true` only after exact live ACM acceptance; and
- final `all_of` semantics.

E3 PASS must require all of:

1. the candidate transfer completed exactly once;
2. the Download endpoint departed;
3. the expected candidate ACM endpoint was unambiguous;
4. the host received the exact banner bytes;
5. post-rollback retained evidence accepted the E3 terminal record;
6. the exact rollback completed; and
7. final Android/root/partition health passed.

Enumeration without exact bytes is diagnostic only. A retained terminal
without exact host bytes is also diagnostic only. Neither is E3 PASS.

Changing the Process v2 runner or manifest schema triggers the one independent
safety review required by `AGENTS.md`. The review scope is the new ACM
observer, manifest binding, durable evidence, resume behavior, and `all_of`
verdict path; the unchanged Odin and rollback machinery need not be reworked.

## Historical results reinterpreted

### M34 S3

M34 S3 survived configfs and a UDC write but used the non-existent
`/sys/class/usb_role` path. Its host helper checked ACM/ADB/Odin endpoints but
did not retain complete USB-device-level evidence. It therefore proves that
its sequence did not immediately reset the device; it does not prove that the
current generic ACM path cannot enumerate.

### O3F

O3F created generic `acm.usb0`, used the correct `ssusb/mode` path, and then
attempted a full framed request/response loop. Its live run saw no candidate
USB event, but it had:

- the older 59-module plan, before the display/provider closure;
- no retained internal phase coordinate;
- no proof that it reached configfs, mode, UDC bind, or `ttyGS0`; and
- E4-like protocol work combined with the first generic ACM attempt.

P2.58A later proved a materially different 60-module chain through the real
UDC. O3F is therefore not negative evidence against E3 over the proven chain.
Its syscall/configfs helpers and host raw-TTY mechanics are reference material,
not an executable base or reusable live authority.

## What remains unproved

- generic `acm.usb0` has not enumerated live under the exact P2.58A chain;
- the target-specific mode write has not been retained in that chain;
- UDC attribute readback does not by itself prove pull-up or host visibility;
- the host has not received candidate-bound bytes; and
- queued-banner behavior, although verified in the exact binary and matching
  upstream source, still becomes target proof only through E3 live evidence.

These are expected E3 observations, not reasons for broader pre-build
exploration.

## Escalation rules

Do not broaden before a versioned E3 record supplies a coordinate.

- Failure before `0x8c`: fix the exact local configfs/TTY operation.
- Failure at `0x8d`: inspect only the speed/mode path and readback.
- Failure at `0x8e`: inspect only gadget-to-UDC binding.
- Device-side terminal plus no host USB add: then inspect UDC
  `state/current_speed`, role/VBUS timing, and only then `soft_connect`.
- USB device add but no `cdc_acm` TTY: inspect descriptors and host-driver bind.
- Exact TTY but wrong/missing bytes: inspect the queued-write and host raw-TTY
  boundary.

Descriptor parity, Samsung `ss_acm`, companion functions, DT changes, NCM,
shell, Debian, hot reload, and arbitrary control commands remain out of scope.

## Verdict and next unit

`P2.59_ANALYSIS_COMPLETE`.

No broad USB or provider investigation is required before design. The
load-bearing device-side path is present in the qualified kernel, a
single-write prequeue ordering removes the principal host-open race, and the
remaining structural blocker is the absent Process v2 ACM observer and
`all_of` verdict.

The next bounded H0 unit is a versioned E3 design that freezes:

- the seven post-E2 stages;
- the one-open-FD/one-banner lifetime;
- exact descriptor and banner identities;
- the Process v2 observer schema and durable evidence;
- strict `all_of` acceptance and replay behavior; and
- static/no-LTO validation first, with Full-LTO only for the final qualified
  candidate.

## External references

- Linux configfs gadget construction and UDC-last enable:
  <https://docs.kernel.org/usb/gadget_configfs.html>
- Linux gadget serial overview and dynamic TTY identity:
  <https://docs.kernel.org/usb/gadget_serial.html>
- Android common `u_serial.c` lifecycle used to cross-check the exact binary:
  <https://android.googlesource.com/kernel/common/+/29d66b3902962d0a89408abaf6d24a3df5eef518/drivers/usb/gadget/function/u_serial.c>

These references establish generic behavior only. Target proof remains bound
to the exact FYG8 config/binary and the future E3 live result.
