# S22+ FYG8 P3.19 — Stage A answered by probe; Stage A itself is defective

Date: 2026-08-18
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`) only.
Status: **IMPLEMENTED_REVIEW_PENDING; D0 READ-ONLY; NO LIVE AUTHORITY**

## Result first

There is **no `regmap` entry** under the Max77705 `57-0066` I2C client.

Proved twice in one read, by a complete listing and by a direct inode test:

```
reached_end        : True     script ran to completion, so nothing was lost
listing_count      : 15
uevent_in_listing  : True     completeness check: uevent is always present
regmap_in_listing  : False
regmap_present     : no       [ -e "$client/regmap" ]
lsa_rc             : 0
```

The client's real composition:

| Kind | Entries |
|---|---|
| MFD children | `max77705-charger`, `max77705-fuelgauge`, `max77705-usbc` |
| standard | `driver`, `modalias`, `name`, `of_node`, `power`, `subsystem`, `uevent`, `wakeup` |
| device-specific | `fw_update` |
| device link | `supplier:platform:c42d000.qcom,spmi:qcom,pm8350c@2:pinctrl@8800` |

## Stage A is defective and could not have answered this

`s22plus_fyg8_p319_max77705_attribute_stage_a.py` stops with
`entry_count row cardinality is not one`, deterministically, byte-identical
across two runs. The cause is its own entry-name allowlist:

```sh
case "$name" in ''|*[!A-Za-z0-9._:+-]*) exit 23 ;; esac
```

Commas and `@` are not permitted, but the device-link entry
`supplier:platform:c42d000.qcom,spmi:qcom,pm8350c@2:pinctrl@8800` contains both,
and sorts immediately after `subsystem` — exactly where the output stopped. Stage
A therefore exited 23 on a legitimate sysfs name. `supplier:` and `consumer:`
device links embed a full device path and routinely contain such characters.

This is a Stage A defect, not a device or transport problem. It is recorded and
deliberately **not repaired here**, because repairing it changes the pinned safety
contract digest `e60e7104` and would only re-derive a result already obtained
under stricter evidence.

## Why it looked like success

`exec-out su -c` did not surface the remote `exit 23`: adb reported
`returncode 0` with empty stderr, and the capture layer reported no truncation
(`output_exceeded` false, 283 bytes against a 32 KiB bound). A remote script that
died mid-loop was indistinguishable from one that completed.

Three hypotheses were tested and refuted before the cause was found: script POSIX
logic (dash, sh and busybox all print the trailing rows), transport loss (two
other captures in the same run completed normally), and argv flattening of a
multi-line script through `exec-out su -c` (the predecessor
`s22plus_fyg8_max77705_sysfs_d0.py` passes a 62-line, 2,046-byte script the same
unquoted way and returned `PASS` on 2026-08-11).

## What made the answer trustworthy

Stage A's parser refused a listing it could not prove complete. The missing row
was `entry_count`, which exists for exactly that purpose. Without that refusal the
truncated listing — which also lacked `uevent` — would have been reported as
"regmap absent", by luck rather than by evidence.

The probe reproduces that discipline explicitly: no `set -e`, so no single failing
test can end the run before its sentinel; `probe end` as the completeness proof;
the remote status recorded as data rather than asserted; and `uevent` as an
independent check that the listing is whole.

## The probe

`s22plus_fyg8_p319_stage_a_truncation_probe.py`, script digest
`956854d8825f939de49cd2342339e993d1b3e0fae4966a59238ea411f01dc278`, 1307 bytes.
The listing that produced the result above was taken with the 875-byte
`c63bb17d` predecessor; this revision adds the mxim existence question and the
verdict gate below, and changes nothing about how the client is enumerated.

Its safety contract counts zero sysfs writes, zero attribute-body reads, zero
debugfs access, zero `/dev/i2c` access, zero module actions and zero reboots over
the exact script text that is sent. **That contract is a lint, not a proof.** An
adversarial review put ten dangerous scripts through it and nine passed, including
a sysfs write addressed through a shell variable — the idiom this very probe uses
for every path it touches. What is actually machine-checked is the script digest.
The probe is read-only because its operations are `[ -d ]`, `[ -e ]`, glob and
`ls -a`, verified by reading it line by line, not because the contract proved it.

Two corrections to the first draft of this section. It said registering the probe
"forced the registration rather than admitting a new device-touching source
silently, which is the boundary behaving as designed". Measured, the probe's
`_uses_legacy_acquisition` was **False**, so the behavior rule never examined it;
what stopped the audit was `OBSERVER_FILE_RE`, a filename rule matching the
substring `probe`. The *filename* net did the work the behavior net was introduced
to replace, and under a name like `..._mux_reader.py` no registration would have
been required at all. And the probe originally had no stop path: `STOP_VERDICT`
was defined and never used, so a timed-out or truncated capture would have
rendered as `PASS` with an empty listing. Both are fixed — the acquisition rule is
now a process-spawn-capability test, and the verdict is gated on `reached_end`
together with the capture handle's `timed_out`, `output_exceeded` and
`producer_error_type`, which are now recorded rather than dropped.

## Stage B re-derived, then corrected: the path exists and was in the table

An earlier draft of this report said Stage B "was scoped as a single-attribute
CONTROL1 read", then replaced that with a closure claiming no userspace path to
`CONTROL1` exists at all. The first was wrong and the second was also wrong. Both
are corrected here rather than dropped.

What holds. `CONTROL1` is not a sysfs attribute: it is an I2C register reached
through the MUIC command protocol, with `CONTROL1_R`/`CONTROL1_W` as opcodes
`0x05`/`0x06` (`include/linux/usb/typec/maxim/max77705-muic.h:70-71`). Within
`drivers/usb/typec/maxim/max77705-muic.c`, `CONTROL1` occurs once, at `:343`, as
`COMMAND_CONTROL1_WRITE`, with no read opcode. The MUIC attribute group is created
on `switch_device->kobj` (`:2553`), i.e. `/sys/class/sec/switch/`, not on the I2C
client. `usb_sel` returns `pdata->usb_path` and `usb_state`/`attached_dev` return
`muic_data->attached_dev`, all software caches; `adc`, `vbus_value` and
`vbus_value_pd` perform a real single-register read of `USBC_STATUS1` (`:591`,
`:608`), whose eight bits are entirely UIADC and VBADC
(`max77705-muic.h:242-245`), so it genuinely cannot carry the COMN1SW/COMP2SW mux
fields that live only in `CONTROL1` (`:294-299`).

**What was wrong: the conclusion, and the claim that the search location was
wrong.** `57-0066` was the correct directory. `fw_update` — listed in this
report's own table as "device-specific", and never opened — is the driver set's
only userspace `CONTROL1` entry point. `drivers/usb/typec/maxim/max77705_usbc.c`
builds `read_data.opcode = OPCODE_CTRL1_R` and `write_data.opcode = OPCODE_CTRL1_W`
with `write_data.write_data[0] = 0x09` (`:1571-1576`) and calls
`max77705_usbc_opcode_rw()` at `:1587`, and its group is created on
`&max77705->dev->kobj` at `:3711`, which is that client directory. The dead end
was one row below the live path in the same table.

**New hazard, recorded not exercised.** `fw_update` is writable
(`S_IWUSR | S_IWGRP`), and the unconditional `opcode_rw` at `:1587` runs *before*
the `start_fw_update` switch. Any write to it therefore issues a `CONTROL1` write
of `0x09` and enters the firmware-update opcode path. It must not be written
without F1-class authority. Nothing in this campaign has written it.

**A second userspace surface also exists.** `max77705_debug.c` is compiled in
(`CONFIG_CCIC_MAX77705_DEBUG=y` at `arch/arm64/configs/vendor/waipio-gki_defconfig:1202`
and `lego.config:121`; linked at `Makefile:7`) and is initialised at probe
(`max77705_usbc.c:3707-3708`). It registers a misc device and a class
(`max77705_debug.c:476`, `:493`), giving `/dev/mxim_dev` with opcode and register
ioctls, plus `/sys/class/mxim/debug0/{reg,opcode}`.

So the closure's stated consequence — that reaching `CONTROL1` requires a bound
diagnostic module, "a materially larger step than a read" — is **false**. The
command protocol is already exposed to userspace by the shipped kernel through two
independent interfaces. Whether either exists and is reachable on the running unit
is unverified: this is source and config evidence only, SELinux permissiveness is
unknown, and whether reading the response mailbox is side-effect-free cannot be
proved from source. A read-only existence check is the next step, and this report
grants no authority for anything beyond it.

## Authority boundary

Read-only D0. `device_writes` false, `reboot_requested` false,
`partition_transfer` false, `candidate_used` false, `f1_authorized` false,
`live_authorized` false. The A90 attached in recovery on the same host received no
command. No S20+ action occurred. Full regmap dumps remain forbidden.

## The mxim question, answered on the running unit

The extended probe (digest `956854d8`, 1307 bytes) re-ran with the existence
questions the previous version could not ask. Both surfaces exist:

| Question | Answer |
|---|---|
| `/dev/mxim_dev` | present |
| `/sys/class/mxim` | present |
| `/sys/class/mxim/debug0` | present |
| `debug0` entries | `opcode`, `power`, `reg`, `subsystem`, `uevent` |

`reached_end` true, `lsa_rc` 0, `regmap_present` no, `uevent_present` yes,
`timed_out` false, `output_exceeded` false, `producer_error_type` null, 486
stdout bytes. The source-and-config claim of the previous section is therefore
confirmed by observation: the shipped kernel exposes the MAX77705 command
protocol to userspace, and it is reachable on this unit.

## What a `reg` read actually costs, from the table rather than the name

`mxim_debug_reg_show` is not a regmap dump. It walks a fixed 17-entry table
(`max77705_debug.c:32-117`) and skips every entry marked `.ignore`, which is
exactly the three read-to-clear interrupt registers `USBC_IRQ` `0x02`, `CC_IRQ`
`0x03` and `PD_IRQ` `0x04`. A read therefore performs 14 single-byte
`i2c_smbus_read_byte_data` calls over `0x00`-`0x10`: `UIC_HW_REV`, `UIC_FW_REV`,
`RSVD1`, `USBC_STATUS1`, `USBC_STATUS2`, `BC_STATUS`, `RSVD2`, `CC_STATUS1`,
`CC_STATUS2`, `PD_STATUS1`, `PD_STATUS2`, and the three interrupt *masks*
`USBC_IRQM`, `CC_IRQM`, `PD_IRQM`.

This matters because the standing Max77705 hazard in this repository is that a
failed firmware-major or charger-detail read can leave zero values that classify
as old firmware or battery-only, and that a full dump can reach the charger
firmware updater branch. **Neither register is in this table.** The table stops
at `0x10` and the charger and fuelgauge blocks are separate I2C children. The
hazard that motivated the full-dump prohibition is not on this path. The
prohibition on full regmap dumps still stands; this is not one.

The output buffer was checked rather than assumed: `dump[12 * (MXIM_REG_MAX + 1)]`
is 216 bytes, the header writes 10 and each of 14 rows writes 11, totalling 164,
so `strcat` does not overflow.

## Stage B revives, but not as a CONTROL1 read

Stating this carefully, because two previous Stage B claims in this report were
wrong.

**What `reg` does answer.** `CC_STATUS1`/`CC_STATUS2`, `PD_STATUS1`/`PD_STATUS2`
and `BC_STATUS` are not exposed anywhere in the MUIC sysfs group, so this is real
new state — CC attach and orientation, PD contract state, and BC1.2
classification — obtained by a bounded read. That is strictly more than the
closed sysfs branch could offer.

**What `reg` does not answer.** `CONTROL1` is not in the table and is not at any
address it covers. The `COMN1SW`/`COMP2SW` mux fields remain unreachable by
reading. Reaching them requires issuing opcode `CONTROL1_R` `0x05`, which means
*writing* `AP_DATAOUT` — through `opcode` store, or the `MXIM_DEBUG_OPCODE_WRITE`
ioctl. A read opcode delivered by a mailbox write is still a command to the PD
controller, and it is not a D0.

**New hazard, from source, not exercised.** Both `debug0` attributes are mode
`0664` (`:232`, `:286`), so root may write either. `mxim_debug_reg_store` performs
an arbitrary single-register I2C write with no address validation at all
(`:209-230`), and `mxim_debug_opcode_store` writes 33 bytes to `0x21`-`0x41`,
i.e. issues an arbitrary opcode command (`:255-284`). The `/dev/mxim_dev` ioctls
`MXIM_DEBUG_REG_WRITE` and `MXIM_DEBUG_OPCODE_WRITE` are the same primitives with
the same absence of bounds (`:350-360`, `:314-333`). These join `fw_update` as
surfaces that must not be written without F1-class authority. Nothing in this
campaign has written any of them.

**A concurrency hazard that is separate from the write hazard.** The ioctl
handler takes `mxim_pdev->lock`, but neither sysfs `show` nor sysfs `store` takes
any lock, and none of the three participates in the opcode queue that
`max77705_usbc.c` maintains for the driver's own traffic. A debug opcode write
therefore races the driver's in-flight opcode with no arbitration on either side.
This is a reason to treat even the `opcode` *read* as deferred rather than
merely to forbid the write.

## A defect in this probe, found in its own output

`ls -a` on the two mxim directories came back column-collapsed, so
`mxim_class_nodes` is the single element `".  ..  debug0"` and
`mxim_debug0_entries` the single element `".  ..  opcode  power  reg  subsystem
uevent"`, while the `57-0066` listing in the same run came back one entry per
line. The difference is entry-name width, not anything about the directories.

The conclusion is unaffected: the entries are legible, and the `[ -e ]` and
`[ -d ]` scalar rows answer the existence questions independently of the listing
shape. But the parser is width-dependent, which is the same class of defect as
the Stage A truncation this probe was built to diagnose — a listing whose shape
depends on the environment, parsed as though it were stable. Any successor must
use `ls -a1` and must not derive a count from a row that could be a column.

## Authority boundary for this section

Read-only D0 under the same approval. `device_writes` false, `reboot_requested`
false, `partition_transfer` false, `candidate_used` false, `f1_authorized` false,
`live_authorized` false. `fw_update`, `reg` and `opcode` were neither read nor
written; only their names were listed. The A90 attached in recovery on the same
host received no command. No S20+ action occurred.

## Correction: the `reg` read is not side-effect-free

A fourth interrupt register is read, and the report above said otherwise. The
section "What a `reg` read actually costs" is right that the driver skips three
read-to-clear interrupt registers, and wrong to leave the impression that all of
them are skipped.

The debug driver's own header is mislabelled. `max77705_debug.h:31-42` names the
table entries `MXIM_REG_RSVD1` at `0x05` and `MXIM_REG_RSVD2` at `0x09`, and
`MXIM_REG_RSVD1` carries `.ignore = 0`, so it is read. But `max77705.h:65`
defines `0x05` as `REG_VDM_INT`, and `max77705_usbc.c:170-172` clears the
interrupt block by bulk-reading four registers from `0x02` under the comment
`clear all interrpts`. `0x05` is therefore the fourth member of that block, and
reading it consumes any latched VDM — alternate-mode, Discover ID, Discover
SVIDs, Discover Modes, Enter Mode, DP Status — interrupt before the driver's own
handler can see it.

The same mislabelling runs through the rest of the table, which matters for any
decoder built from the debug header rather than from the driver:

| Debug header name | Address | Real name (`max77705.h`, confirmed by driver reads) |
|---|---|---|
| `MXIM_REG_RSVD1` | `0x05` | `REG_VDM_INT` — read-to-clear |
| `MXIM_REG_RSVD2` | `0x09` | `REG_UIC_FW_MINOR` |
| `MXIM_REG_CC_STATUS1` | `0x0A` | `REG_CC_STATUS0` |
| `MXIM_REG_CC_STATUS2` | `0x0B` | `REG_CC_STATUS1` |
| `MXIM_REG_PD_STATUS1` | `0x0C` | `REG_PD_STATUS0` |
| `MXIM_REG_PD_STATUS2` | `0x0D` | `REG_PD_STATUS1` |
| `MXIM_REG_USBC_IRQM` | `0x0E` | `REG_UIC_INT_M` |

`max77705.h` is itself inconsistent — its CC bitfield comment blocks are labelled
`REG_CC_STATUS1`/`REG_CC_STATUS2` while its address defines say
`REG_CC_STATUS0`/`REG_CC_STATUS1` — so the layout was taken from what the driver
actually reads, not from either comment: `max77705_cc.c:340` reads `CCPinStat`
out of `cc_status0`, `:473` `CCIStat`, `:535` `CCVcnStat`, `:584` `CCStat`, and
`:342`/`:344` read `VSAFE0V` and `ConnStat` out of `cc_status1`. The PD side needs
no such correction: `max77705_pd.c:1483` reads `PDMsg` from `pd_status0` and
`:1503`/`:1579`/`:1688` read `PSRDY`, `DataRole` and `FCT_ID` from `pd_status1`,
matching the header labels.

**Severity, stated plainly.** This is not a partition, not firmware, not a brick.
It is one dropped alternate-mode interrupt in the worst case, recoverable by
replug. But it is a state change on a path this report called a read, so it is
recorded as one, and it is gated behind an explicit flag rather than assumed
away.

## Stage B runner: one attribute body, one register set

`s22plus_fyg8_p319_max77705_reg_stage_b_d0.py` reads exactly
`/sys/class/mxim/debug0/reg` and nothing else. It never reads or writes `opcode`,
never writes `reg`, and never names `fw_update` or `/dev/mxim_dev`.

Its safety contract is **structural rather than a token lint**, because the
probe's token contract was reviewed and found to pass nine of ten dangerous
scripts. It asserts the shape of the script: exactly one body-read line, that
line being literally `cat "$target"`, exactly one `target=` assignment, that
assignment being literally `target=/sys/class/mxim/debug0/reg`, zero redirects,
and no occurrence of any forbidden path. Six mutations are executed against it in
the suite — a second body read, an added `opcode` read, a retargeted variable, a
sysfs write, a mention of `fw_update`, and `head` substituted for `cat` — and all
six are rejected.

The verdict is gated, not asserted. A run is complete only if the end sentinel
arrived, the target existed, `cat` returned 0, the header row was seen, the
address set is exactly the fourteen expected, no row failed to parse, the dump is
not all-zero, at least one of the two identity registers is non-zero, and the
capture handle reports no timeout, no truncation and no producer error. The
all-zero refusal exists because `mxim_debug_i2c_read` assigns its `int` return
into an `unsigned char`, so a failed read is not distinguishable from a real
zero by value alone.

The `--collect` path refuses with exit 3 and touches nothing — no run directory,
no ADB — until `--accept-vdm-int-clear` is passed. That refusal is executed in
the suite rather than described.

Registering the runner moved the raw-first boundary's closed-observer population
from 122 to 123 and the auditor stopped until it was declared. Unlike the probe,
this file was deliberately named so the boundary would catch it: `..._d0.py`
matches `OBSERVER_FILE_RE`, whereas a name like `..._reg_reader.py` would not
have. That is a workaround for the residual the boundary review already recorded,
not a fix for it.

## Authority boundary for the Stage B runner

H0 as written: no device contact has occurred through this runner. The read it
performs is a D0 and requires the flag above plus operator approval. `opcode`,
`fw_update` and `/dev/mxim_dev` remain F1-class and untouched. Full regmap dumps
remain forbidden.

## Stage B result: fourteen registers, read once

`PASS_S22PLUS_FYG8_P319_MAX77705_REG_STAGE_B_D0`, complete. Address set exactly
the fourteen expected, `body_rc` 0, 239 stdout bytes, no unparsed row, not
all-zero, both identity registers non-zero, and no timeout, truncation or
producer error.

```
0x00  0x1a  REG_UIC_HW_REV
0x01  0x6e  REG_UIC_FW_REV
0x05  0x00  REG_VDM_INT          <- read-to-clear
0x06  0x27  REG_USBC_STATUS1     VBADC=4.5-5.5V(2) UIDADC=UIADC_OPEN(7)
0x07  0x05  REG_USBC_STATUS2     SYSMsg=SYSMSG_BOOT_POR(5)
0x08  0x82  REG_BC_STATUS        VBUSDet=1 PrChgTyp=UNKNOWN(0) DCDTmo=0 ChgTyp=CHGTYP_CDP(2)
0x09  0x40  REG_UIC_FW_MINOR
0x0a  0xa1  REG_CC_STATUS0       CCPinStat=CC2_ACTIVE(2) CCIStat=CCI_1_5A(2) CCVcnStat=0 CCStat=cc_SINK(1)
0x0b  0x09  REG_CC_STATUS1       VSAFE0V=1 Altmode=1 ConnStat=0 AttachSrcErr=0
0x0c  0x19  REG_PD_STATUS0       PDMsg=HARDRESET_SENT(0x19)
0x0d  0x47  REG_PD_STATUS1       DataRole=0 EnterMode=0 PSRDY=0 FCT_ID=7
0x0e  0x04  REG_UIC_INT_M
0x0f  0x20  REG_CC_INT_M
0x10  0x00  REG_PD_INT_M
```

**The side effect cost nothing this time.** `REG_VDM_INT` read back `0x00`, so no
alternate-mode interrupt was latched and none was consumed. That is a fact about
this run, not a reason to drop the gate: the same read at a different moment
would have taken whatever was pending.

### What this establishes

The controller is alive and normally initialised. All three interrupt masks sit
at their compiled-in initial values — `REG_UIC_INT_M_INIT` `0x04`,
`REG_CC_INT_M_INIT` `0x20`, `REG_PD_INT_M_INIT` `0x00` (`max77705.h:95-98`) — so
the driver's `probe` path ran and nothing has since rewritten them.

The port state is unambiguous: the cable is on **CC2**, the port is a **sink**,
the source advertises **1.5 A** through Rp, VBUS is present at 4.5-5.5 V, the ID
line reads **open** so there is no factory jig and no OTG ground, and BC1.2
classified the far end as a **CDP** — a host port that also charges. There is **no
PD contract**: `PSRDY` is 0 and the data role is UFP.

### Three values that need care rather than a headline

`PDMsg` and `SYSMsg` are *last-event* registers, not live state. `SYSMsg` reads
`SYSMSG_BOOT_POR`, so the USBC MCU has not been reset since power-on, and
`PDMsg` reads `HARDRESET_SENT` — at some point since that power-on the controller
sent a PD hard reset. When is not recoverable from this read.

`VSAFE0V` is 1 while `VBUSDet` is 1 and VBADC reports 4.5-5.5 V. As live levels
those contradict. The reading most consistent with `HARDRESET_SENT` is that the
bit is latched from the hard-reset sequence, which drives VBUS to vSafe0V, and
has not been cleared since. **That is inference, not measurement** — the driver
only ever samples this bit inside an interrupt handler
(`max77705_cc.c:342`), and nothing in the sources states its clear semantics.

`Altmode` is 1 while `PD_ENTER_MODE` is 0 and `REG_VDM_INT` is 0. This report does
not claim an alternate mode is active; it records the bit.

### What it does not answer, and the one thing it constrains

It does not answer the mux question. `CONTROL1` is at no address in this table,
so `COMN1SW`/`COMP2SW` are unread, exactly as the preceding section said they
would be.

One constraint does follow. BC1.2 returning `CHGTYP_CDP` rather than
`CHGTYP_NO_VOLTAGE` means the D+/D- handshake completed, so those lines reach the
charger-detection block electrically. Whether that block sits before or after the
MUIC switch matrix is not established by anything read here, so this **constrains
the "D+/D- never got connected at all" reading without resolving where the
switch sits.** No stronger claim is made from it.

### Boundary

Read-only D0 under explicit approval plus `--accept-vdm-int-clear`. Remote script
digest `17755bf5`, 290 bytes, unchanged by the decoding tables added afterwards,
which are host-side only. `device_writes` false, `reboot_requested` false,
`partition_transfer` false, `candidate_used` false, `f1_authorized` false,
`live_authorized` false. `opcode`, `fw_update` and `/dev/mxim_dev` were neither
read nor written. The A90 attached in recovery received no command and no S20+
action occurred.

## The read-only route to the mux question, and why it did not close it yet

Reaching `CONTROL1` by opcode needs a write, which is F1-class. It is not the
only route. The driver already publishes what it commands:

- `max77705-muic.c:331` — `max77705_switch_path()` does
  `pr_info("%s value(0x%x)")` with the exact `CONTROL1` byte it is about to
  write, then issues `COMMAND_CONTROL1_WRITE`.
- `max77705_usbc.c:1897` and `:1959` — every opcode write and every opcode read
  response is `print_hex_dump`'d at `KERN_INFO`.

Both dumps sit on the `#else` side of an `#if 0`, so they are **unconditionally
compiled**; there is no CONFIG to check. `com_to_open`, `com_to_usb_ap` and
`com_to_usb_cp` each log their own name as well.

That settles half of the open question — whether the driver ever *commanded* the
mux — with no write and no state change. It does not give the mux's actual bits.

`s22plus_fyg8_p319_usbc_log_harvest_d0.py` collects that log plus two more
read-only surfaces: `/proc/usblog`, which is `0444` and backed by
`single_open`/`single_release` (`usblog_proc_notify.c:1737`, `:1260-1266`) so a
read is a snapshot and not a drain, and the standard Type-C class port
registered at `max77705_usbc.c:3775`. Type-C attributes are read from a **pinned
list of ten names, not a glob**, so what is read stays reviewable.

The one destructive thing a log reader can do is clear the ring it reads.
`dmesg -c`, `-C`, `--clear` and `--read-clear` are refused by the safety
contract. A token list alone was not enough — a bare `-c ` token nearly
false-matched `wc -c`, and `dmesg  -c` with two spaces would have slipped past —
so the contract additionally requires every `dmesg` occurrence to be immediately
followed by a pipe or a closing paren. Eight mutations are executed against it in
the suite, including the two-space form, and all eight are rejected.

### Result, and the control that stops it being over-read

`PASS`, complete. 3,334 kernel lines scanned, 481 driver lines matched,
`/proc/usblog` present with 104 entries, Type-C port present.

```
switch_path_count        : 0
com_to_calls             : []
opcode_write_dumps       : 0
attach_markers_in_window : 0
ring_span_seconds        : 129.364
mux_evidence_conclusive  : False
```

**Zero `switch_path` lines is not evidence that the driver never commanded the
mux.** The ring buffer spans `[178515.036853]` to `[178644.400764]` — about 129
seconds — at roughly 49.6 hours of uptime. The attach happened long before that
and has rotated out. An absent log line and a log line that scrolled away are
indistinguishable without the span.

The first version of this runner did not capture the span at all, and its
`switch_path_count: 0` was therefore uninterpretable. That was caught by reading
the artifact rather than by the runner, so the span is now captured and the
result carries `mux_evidence_conclusive`, which is true only when a
`switch_path` line is present or an attach marker falls inside the window. The
suite executes all three cases.

To make it conclusive the window must contain an attach. That needs a cable
replug immediately before the harvest — a physical action, not a write.

### A live finding from the window that was captured

Within those 129 seconds the source's Rp advertisement is oscillating:

```
rp_currentlvl(2)  x20      Vbus Current is 1.5A  x10
rp_currentlvl(3)  x20      Vbus Current is 3.0A  x10
```

Ten full 1.5 A / 3.0 A cycles in 129 seconds, with transitions as close together
as one second. `usb_typec_handle_notification: CMD[NONE], CABLE_TYPE[1]` repeats
72 times in the same window, and `ic_alt_mode=1` matches the `Altmode` bit Stage
B read. `is_empty_usbc_cmd_queue: usbc_cmd_queue Empty(T)` appears throughout,
which is consistent with — though not proof of — the opcode queue being idle.

This is recorded as an observation. It is **not** claimed to be a fault, a cause,
or related to the mux question: an unstable Rp level can come from the host port
or the cable. It is noted because Stage B separately read `PDMsg =
HARDRESET_SENT`, and a repeatedly renegotiating CC state is the kind of thing
that produces one.

### Redaction

The unredacted capture stays under the gitignored run root. What may be quoted
is passed through a redactor for MAC, IPv4, UUID, kernel pointer and long digit
runs first; this run reported zero redactions, meaning the matched driver lines
contained none of those. The redactor is tested to remove all five while leaving
`max77705_switch_path value(0x01)` intact.

### Boundary

Read-only D0. No writes, no opcodes, no ring clearing, no interrupt consumed —
this runner touches neither `reg` nor `opcode` nor `fw_update` nor
`/dev/mxim_dev`. `device_writes` false, `ring_buffer_cleared` false,
`reboot_requested` false, `partition_transfer` false, `candidate_used` false,
`f1_authorized` false, `live_authorized` false. The A90 attached in recovery
received no command and no S20+ action occurred.

## The boundary caught a stale-bytecode hole in itself

Registering the harvester tripped the byte freeze twice, once per runner edit,
which is the boundary working. The third trip was not.

`test_loaded_auditor_cannot_receipt_different_source_bytes` failed: a mutation
that replaces the auditor's pinned self-binding digest with zeros was **not**
rejected. The cause is not a hole in the rule. Registration replaces one 64-hex
digest with another, so the file keeps **exactly the same size**, and when both
edits land inside a single mtime second CPython's `.pyc` invalidation check —
mtime plus size — does not trip. The imported module therefore carried
`AUDITOR_NORMALIZED_SHA256` from stale bytecode while the file on disk held a
different value. The test built its mutation from the stale constant, found no
occurrence of it in the source, and mutated nothing.

The audits themselves were not wrong: `audit_sources` delegates to
`load_bound_auditor()`, which compiles from the file, so every receipt in this
campaign was produced from the on-disk source. What was wrong is that the module
could report one set of constants while auditing under another.

Deleting the stale `.pyc` fixes the symptom. It is closed instead: `audit_sources`
now parses the digest literal out of its own source and refuses when it differs
from the executing constant, with the message `executing auditor constants differ
from its source`. A test sets the module constant to zeros, asserts the refusal,
and then asserts the unmutated module still audits.

This is worth stating plainly because the failure mode is quiet and general: any
byte-pinned constant that is rotated in place, at the same length, within one
second, can leave a Python process auditing under constants its own file no
longer contains.

## Conclusive: the driver commands the mux, and the command reaches the wire

A replug put an attach inside the window. `mux_evidence_conclusive` is now true:
39.8-second ring span, 733 driver lines, 9 attach markers, 2 `switch_path` calls,
6 opcode write dumps.

```
[179797.899] max77705_ccpinstat_irq: CCPINSTAT (NO_DETERMINATION)
[179797.902] max77705_ccstat_irq_handler: PLUG_DETACHED ---
[179797.906] pdic_max77705: com_to_open
[179797.906] pdic_max77705: max77705_switch_path value(0x3f)
[179797.931] max77705_i2c_opcode_write: opcode 0x6, write_length 2
[179797.931] max77705: opcode_write: 00000000: 06 3f
...
[179807.767] max77705_ccpinstat_irq: CCPINSTAT (CC2_ACTIVE)
[179807.768] max77705_ccstat_irq_handler: PLUG_ATTACHED +++
[179807.768] max77705_ccstat_irq_handler: ccstat : cc_SINK, keep awake for a second.
[179807.846] pdic_max77705: max77705_muic_attach_usb_path usb_path=0
[179807.846] pdic_max77705: com_to_usb_ap
[179807.846] pdic_max77705: max77705_switch_path value(0x9)
[179807.846] max77705_i2c_opcode_write: opcode 0x6, write_length 2
[179807.846] max77705: opcode_write: 00000000: 06 09
```

Both logged values decode exactly, from `max77705-muic.h:384-393` rather than by
inspection:

| Logged | Constant | `NOBCCOMP` | `RCPS` | `COMP2SW` | `COMN1SW` |
|---|---|---|---|---|---|
| `0x3f` | `COM_OPEN` | 0 | 0 | `0x7` open | `0x7` open |
| `0x09` | `COM_USB` | 0 | 0 | `0x1` USB | `0x1` USB |

The arithmetic was recomputed from the header's shifts rather than assumed:
`(0<<7)|(0<<6)|(7<<3)|(7<<0)` is `0x3f` and `(0<<7)|(0<<6)|(1<<3)|(1<<0)` is
`0x09`.

Opcode `0x06` is `COMMAND_CONTROL1_WRITE`. The window contains **exactly one
`06 3f` and exactly one `06 09`** and no other CONTROL1 write, so the command was
not merely computed in software: it was serialised and handed to I2C.

### What this settles, and what it does not

Settled: on the stock running unit the driver **does** command the D+/D- mux to
USB on attach, and the command reaches the wire. The question "did the driver
even try?" is answered yes, with byte-level evidence.

Not settled: whether the MUIC silicon **applied** it. What is observed is the
write leaving the AP, not the resulting switch position. Reading back the
position still means issuing `CONTROL1_R`, which is a write, which is F1-class.
The gap has narrowed from "was it commanded" to "was it applied", and it has not
closed.

**This is a positive control, not a refutation of the campaign hypothesis.** That
hypothesis concerns candidate boot images; this run is the stock unit. Its value
is that it now supplies exact expectations a candidate run can be compared
against: `com_to_usb_ap`, `max77705_switch_path value(0x9)`, and a wire dump of
`06 09` within roughly a second of `PLUG_ATTACHED`. If a candidate attach lacks
`06 09`, the hypothesis is confirmed with wire-level evidence and still without a
single write.

### Two earlier notes this refines

The `fw_update` hazard recorded above said a write issues "a `CONTROL1` write of
`0x09`". That remains true, and `0x09` is now identified: it is `COM_USB`, not an
arbitrary value — the path routes D+/D- to USB before the update. The hazard is
unchanged, since entering the firmware-update opcode path is the danger, not the
mux value.

The concurrency hazard recorded for debug opcode writes is strengthened rather
than softened by this capture. `max77705_usbc_opcode_write: !!!current_cmd.opcode
[0xff][0x70], read_op->opcode[0x06]` appears twice in 40 seconds, which is the
queue-contention branch at `max77705_usbc.c:2499` firing during entirely normal
operation. An unsynchronised debug write would be injected into exactly that
contention.

## /proc/usblog parsed: a ring that actually reaches back to boot

The kernel ring here spans tens of seconds. `/proc/usblog` does not: it is a set
of named rings bounded by **entry count, not time**, and the counts are far below
their caps, so it holds the whole uptime.

| Ring | count | maxline | wrapped |
|---|---|---|---|
| CCIC EVENT | 40 | 512 | no |
| USB STATE | 55 | 256 | no |
| USB EVENT | 10 | 64 | no |
| USB_MODE | 5 | 64 | no |
| EXTRA | 4 | 128 | no |
| PORT | 0 | 128 | no |
| PCM | 0 | 64 | no |

Earliest entry `3.605282`, latest `179808.320553`. Every ring's declared `count`
equals the number of entries that actually parsed, so nothing was dropped by the
parser, and no ring is full, so nothing has been overwritten. `spans_boot` is
true. The header also carries `time sync: [08-18 20:31:24][179813.278371]`, which
maps monotonic time to wall clock.

### It explains the value Stage B flagged

Stage B read `PDMsg = HARDRESET_SENT` and this report recorded it as a
last-event register whose timing could not be recovered. The `EXTRA` ring
recovers it:

```
[     4.215202] PDIC HARDRESET_SENT
[179808.319417] PDIC HARDRESET_SENT
```

Two entries, at the boot attach and at this replug's attach. **A PD hard reset is
sent on every attach here**, so Stage B's reading was routine behaviour and not
an anomaly. The earlier note that it "needed care" is discharged by evidence
rather than left open. It also supports the inference offered for `VSAFE0V`: a
hard reset drives VBUS to vSafe0V, and the attach hard reset is 0.5 s before the
window Stage B sampled.

### It cross-checks the attach against the kernel log

```
[179807.771036] manager notify: id=ID_CONNECT src=CCIC dest=MUIC ... ATTACHED
[179807.774297] ccic notify:    id=ID_USB src=CCIC dest=USB status=ATTACH_UFP
                -> kernel log: [179807.846] com_to_usb_ap, switch_path value(0x9)
```

Two independent rings agree on the same attach within 75 ms, which is what makes
the mux-command evidence more than a single log line.

### Controller identity, and a version comparison stated raw

```
hw  version = 0  0  0 1a
sw  version = 0 40 6e  0
bin version =15 40 6e  0
```

`hw` matches Stage B's `UIC_HW_REV` `0x1a`; `sw` matches `UIC_FW_REV` `0x6e` and
`UIC_FW_MINOR` `0x40`. `bin` is the image carried by the kernel. Two of the four
fields are identical between `sw` and `bin` and the first differs. No claim is
made here about whether an update is pending: the field semantics are not
established from source, so the three strings are recorded as read.

### Gadget enumeration is recorded too

`CONNDONE` 17, `RESET : SUPER` 15, `GET_DES` 6, `SET_CON` 5 across the uptime,
with the replug producing `VBUS_SESSION_EN` -> `CONNDONE SS` -> `RESET : SUPER`
-> `GET_DES` -> `SET_CON`. `SET_CON` means the host set a configuration, so this
ring records whether enumeration completed — persistently, and without a write.

### Why this matters more than the mux line itself

For a candidate boot the interesting events happen at boot, and the kernel ring
will have rotated long before anyone can read it. These rings will not have.
`CONFIG_PSTORE_CONSOLE=y` and `CONFIG_PSTORE_RAM=y` are also set
(`waipio-gki_defconfig:581-584`), so a candidate that never brings up ADB can
still be read after rebooting to stock, from the previous boot's console.
Together they mean the candidate comparison needs no live capture and no write.

### An error of mine, recorded

While re-registering the changed harvester an unanchored `sed` was run with an
empty capture variable, which rewrote the first empty string literal in the
auditor and left it syntactically invalid, and a second one blanked a digest pin
in a test. Both were restored — the auditor from `HEAD`, the pin by hand — and the
full diff was reviewed to confirm only the intended line changed. Registration
edits are byte-pinned digests, so they must be applied with anchored patterns and
a non-empty check, not with a variable that can come back empty.

## Checklist item 3 was wrong, and the repository already knew

The previous section recommended pstore as the read-only fallback for a
candidate that never brings up ADB, on the strength of `CONFIG_PSTORE_CONSOLE=y`
and `CONFIG_PSTORE_RAM=y`. Measured on the running unit:

```
pstore_dir                 : present
pstore entry_count         : 0
last_kmsg_present          : yes
last_kmsg_bytes            : 2097136
```

**`/sys/fs/pstore` is mounted and empty.** A config symbol being set is not a
retained log. Worse, this was already recorded here: the 2026-07-07 M10A3 live
result states `pstore files none` and `/proc/last_kmsg bytes 2097136` — the same
two facts, the same byte count, six weeks earlier. The recommendation was made
without checking the repository's own live evidence.

### What the surface actually is

Not ramoops. `/proc/last_kmsg` on this unit is Samsung's `sec_log_buf`
(`drivers/samsung/debug/log_buf/sec_log_buf_last_kmsg.c`).
`__last_kmsg_pull_last_log` copies the previous boot's log region into a vmalloc
buffer of `___log_buf_get_buf_size()` at probe, optionally compressed, and serves
that through `/proc`. So it is the **previous boot's kernel log ring**, snapshot
at this boot, not a pstore file.

That model predicts what the bounded head read found:

```
last_kmsg_head.lines               : 36
last_kmsg_head.banner              : null
last_kmsg_head.earliest_timestamp  : 39393.729171
last_kmsg_head.starts_at_a_boot    : false
```

It is a circular buffer, so its head sits wherever the ring wrapped — here about
10.9 hours into the previous session — and there is no boot banner. The 2,097,136
figure is the buffer size and reads identically whatever the buffer holds, which
is why size alone was not accepted as evidence and the head was read.

The consequence cuts both ways. A long session wraps and loses its own early
boot. **A candidate that fails early emits little, so its whole console would fit
without wrapping** — which is the case that matters, and it is the case this
measurement cannot confirm from stock.

### The July result that bears directly on it

`S22PLUS_RAMOOPS_DTBO_M18_CAPTURE_LIVE_RESULT_2026-07-08.md:79-89` already tried
this path against a real candidate: the capture "did not find the expected marker
in pstore or retained last-kmsg", and "the retained log looks more like
ABL/download-mode retention than the M18 native-init printk stream". It left two
open questions and one instruction — "next work should analyze the private 2 MiB
`last_kmsg`" — and that analysis was never done.

So checklist item 3 is **not proven usable** for the candidate failure mode. It is
not refuted either; it is untested in the only way that would settle it.

### What is free to do next

`workspace/private/runs/s22plus_v3437_ramoops_20260710T230320Z/postrun/candidate-last_kmsg.bin`
already exists, 2,097,136 bytes, captured after a candidate boot on 2026-07-10,
alongside `first-stock-boot-last_kmsg.bin` from v3439 as a comparison. Deciding
whether the retained-console path can carry a candidate's early boot is therefore
a **host-only analysis of evidence already on disk**, costing no device action at
all. That is the correct next unit, and it is the one July asked for.

### Corrections carried by this section

- Item 3's named path was wrong: `/sys/fs/pstore` is empty here; the surface is
  `/proc/last_kmsg`.
- The mechanism was wrong: `sec_log_buf`, not ramoops/pstore.
- The claim that a candidate "can still be read from the previous boot's console"
  is downgraded from stated capability to untested hypothesis.

## The 2 MiB analysis July asked for, done

`S22PLUS_RAMOOPS_DTBO_M18_CAPTURE_LIVE_RESULT_2026-07-08.md:88` instructed that
next work analyse the private 2 MiB `last_kmsg`. It never happened. It is done
here, host-only, against the two captures already on disk. Their digests match
the July summaries byte for byte — `d6a7bc92…` and `4e706127…` — so these are the
same files that produced the original conclusions.

```
                                candidate-last_kmsg   first-stock-boot-last_kmsg
boot_kind                       stock_android_boot    stock_android_boot
pid1_comms                      ['init']              ['init']
span_seconds                    29.8                  24.406
head_overwritten                true                  true
banner_present                  false                 false
backward_timestamp_steps        0                     0
xbl_lines                       1107                  1110
panic_lines                     0                     1
panic_is_userspace_echo_only    n/a                   true
run id aa96a1cf…                0                     0
```

### Neither capture holds a candidate boot

**PID 1's comm is `init` in both.** A native-init candidate *is* PID 1, so a
capture of a candidate boot cannot show `init` there. That single field settles
it without trusting a filename, and it is corroborated by ~2,400-2,600 `init:`
messages, ~290 `apexd`, and zygote traffic in each.

So `candidate-last_kmsg.bin` is a stock Android boot. The July conclusion that
the marker was missing did not need either of the explanations offered at the
time — that M18 reset before emitting it, or that the DTBO ramoops node made no
retained path. **The buffer was simply not the candidate's boot.**

### `panic_text_present=true` was a false positive

The stock capture's only `PANIC` occurrence is inside a userspace line:

```
[    6.379502] [7:  apexd: 1166] apexd: panic_message : "RWC":"0",
                                 PANIC:sysrq triggered crash PC:rcu_read_unloc…
```

That is `apexd` reading the previous boot's reset reason and printing it during
the *next* boot. It is not a retained kernel panic record. The July report read
this as "confirming Samsung's retained panic path"; the file does not support
that. The analyser now separates the two, and refuses to count an `apexd:
panic_message :` echo as a retained panic.

### What the buffer actually is, measured

2,097,136 bytes holds roughly **25 to 30 seconds** of this device's boot logging.
Both captures start mid-message around 3.4 s with no `Linux version` banner and
run forward with zero backward steps, so the head was overwritten rather than
reordered. The last ~1,110 lines are XBL/UEFI bootloader output with its own
`{ n }[ XBL ]` counter — July's "looks more like ABL/download-mode retention" was
literally right about the tail, though the head is an ordinary kernel log.

### The consequence is a procedure, not a dead end

The mechanism is not disproven; the sampling was wrong. Since an early-failing
candidate emits far less than 25 seconds of log, its console **would** fit
without wrapping. To capture it, `/proc/last_kmsg` must be read on the **first**
boot after the candidate, before any further reboot overwrites the region. The
July runs read it after a recovery sequence that had already booted at least once
more.

### A defect this analyser found in itself

Its first version counted markers across whole lines, which also counts the comm
column — `[7: apexd: 1166]` matched `apexd`. That inflated every figure:
`init:` 3595 to 2589, `apexd` 462 to 297, `binder` 731 to 47. Markers are now
scoped to the message body, and PID 1's comm is extracted separately as the
discriminator that does not depend on counting at all. The suite exercises the
inflation case directly.

## The mux is switched by a vendor module that Android's modprobe loads

The F1 was approved. Before arming it, the same two captures were searched for the
mux sequence, and it is there — in both, from 2026-07-10, at boot:

```
[4.088544] [2: modprobe:  758] modprobe: Loading module /vendor/lib/modules/pdic_max77705.ko
[4.164515] [6: modprobe:  769] pdic_max77705: max77705_muic_probe
[4.190293] [6: modprobe:  769] pdic_max77705: com_to_usb_ap
[4.190297] [6: modprobe:  769] pdic_max77705: max77705_switch_path value(0x9)
[4.191075] [6: modprobe:  769] max77705: opcode_write: 00000000: 06 09
[4.219691] [7: modprobe:  769] modprobe: Loaded kernel module /vendor/lib/modules/pdic_max77705.ko
```

**The process that writes `CONTROL1` is `modprobe`.** Not the kernel's own boot
path — Android userspace, loading a vendor module.

The build confirms it. `CONFIG_CCIC_MAX77705=m` and `CONFIG_MFD_MAX77705=m`
(`waipio-gki_defconfig:1165`, `:1201`), and
`drivers/usb/typec/maxim/Makefile:5-11` links `max77705_cc.o`, `max77705_pd.o`,
`max77705_usbc.o`, `max77705_alternate.o`, `max77705_debug.o` **and
`max77705-muic.o`** into one object: `pdic_max77705.ko`. The mux code is inside a
loadable module. Android's boot loads 333 distinct `.ko` files from
`/vendor/lib/modules` this way.

### What that means for the campaign

A native-init candidate replaces PID 1. It does not run Android's `init`, so it
does not run `modprobe`, so **none of those 333 vendor modules load** —
`pdic_max77705.ko` among them. Without it there is no `max77705_muic_probe`, no
`com_to_usb_ap`, no `CONTROL1` write, and the D+/D- pair is never routed to USB.

That is this campaign's live hypothesis, and it now has a complete mechanical
chain established **entirely from stock evidence already on disk, at zero device
cost**. It also explains the whole symptom the campaign has been chasing: a
candidate cannot expose ACM or ADB because the data pair was never switched.

The earlier reading in this report — that `switch_path` is kernel-driven because
`pdata->usb_path` has a non-userspace default — was too narrow. The default does
come from platform data rather than `usb_sel`, but the code holding that default
only exists once the module is loaded, and loading it is a userspace act.

### What this does to the approved F1

It changes the target. An F1 that boots an existing candidate and looks for
`06 09` would now confirm something already strongly evidenced, and would consume
a candidate to do it. The F1 worth spending is a candidate that **loads
`pdic_max77705.ko` itself**, because that tests the repair rather than the
diagnosis.

That is not the same experiment and it is not ready. It needs host-only work
first, none of which touches the device:

- the module's dependency order — `pdic_max77705.ko` sits on `CONFIG_MFD_MAX77705=m`
  and the notifier modules, and `modules.dep` on the device names the exact chain
- whether a native-init PID 1 can reach `/vendor/lib/modules` at all, which means
  mounting the vendor partition before `insmod`
- what else in those 333 modules the USB path depends on

The F1 approval is therefore recorded and **not consumed**. No candidate was
armed, no transfer occurred, and nothing was flashed.

## Correction: the module-load chain is not the diagnosis

The section above concluded that a native-init candidate loads none of the 333
vendor modules, therefore never issues the `CONTROL1` write, therefore never
routes D+/D-, and called that "this campaign's live hypothesis, now with a
complete mechanical chain". **That overreaches, and the campaign's own record
refutes it.**

Two facts already held here contradict it:

- **Candidates have loaded `pdic_max77705` and still failed.** M7, M11, M12, M18
  and in particular S7A2 (2026-07-09) included it, with the GENI-I2C transport
  closure and the dep-safe order `i2c-msm-geni` before `pdic_max77705`, and
  host-visible enumeration failed anyway. A candidate is not obliged to inherit
  Android's `modprobe`; this campaign has been loading modules deliberately for
  months, and the module plan is explicitly designed (custom-65 / stock-67).
- **P3.17 read `CONTROL1` as `0x3f -> 0x09 -> 0x09` on two complete candidate
  boots.** The mux has been observed in the USB position on a candidate. So "the
  mux is never switched on a candidate" is false as stated.

There is also a standing reason it could be switched without any module at all:
Download mode enumerates with no kernel modules, so S-Boot can leave the mux in
the USB position, and a candidate may simply inherit it. That premise is recorded
as open, not closed.

### What the finding actually is

Narrower, and still worth having. The campaign's record states that in the
earlier attempts that did load the module, "load/bind, initial detect, and the
COM_USB command/response were never preserved as evidence", so those runs neither
support nor refute the mux hypothesis. **That is exactly the gap this measurement
fills.** The stock captures now supply the complete signature of a successful
sequence, preserved and reproducible:

```
modprobe: Loading module /vendor/lib/modules/pdic_max77705.ko
pdic_max77705: max77705_muic_probe
pdic_max77705: com_to_usb_ap
pdic_max77705: max77705_switch_path value(0x9)
max77705: opcode_write: 00000000: 06 09
modprobe: Loaded kernel module /vendor/lib/modules/pdic_max77705.ko
```

Six lines, in order, within ~130 ms, all inside the retained-log window and all
recoverable on the next boot. "Module in the list" is not "driver bound and
commanded COM_USB", and this is what the difference looks like in evidence.

So the contribution is a **positive control and a comparison procedure**, not a
diagnosis. A candidate run that carries the module and preserves these six lines
would settle whether it bound and commanded; the earlier runs could not.

### Why this keeps happening

This is the third time in this session that the repository's own record corrected
a conclusion of mine, and this one was specifically warned about in prior
guidance — do not claim the module was never loaded, because that error was made
before and is false. The evidence I gathered was sound; the inference from stock
behaviour to candidate behaviour was not, and it was made without reading what the
campaign already knew about candidates that did load it.

The F1 remains approved and unconsumed, and its target is unchanged by this
correction: a candidate whose module load, bind, and COM_USB command are
preserved as evidence.

## Gate 0 is closed

The normal-boot second-stage module list has never been recovered. `vendor_boot`
carries the first-stage list (140 lines) and the recovery order (446 lines);
neither is the order that runs at normal boot. That order lives in
`vendor_dlkm/lib/modules/modules.load` inside `super.img`, 5,843 bytes, SHA-256
`8411620a0384d0…` — a digest recorded from firmware metadata while the bytes
themselves stayed unread.

They are read now, from the running unit, and they match:

```
load_present : yes
load_rc      : 0
load_bytes   : 5843
load_sha256  : 8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360
load_entries : 356
ko_count     : 356
```

The read is self-verifying by construction: the digest was known before the
bytes were, so a match proves the device's list and the firmware's list are the
same 5,843 bytes, and a mismatch would itself have been the finding. Every one
of the 356 listed modules is present in the directory.

The digest is of the file, not of the transcript. `cat` output is framed by
`printf` sentinels, and the parser slices between them and strips the trailing
`load_rc` line before hashing; the suite checks that a leaked frame line would
change the digest.

### The mux stack's place in the normal-boot order

```
218  max77705_charger.ko
221  common_muic.ko
238  usb_typec_manager.ko
240  pdic_notifier_module.ko
250  max77705-fuelgauge.ko
260  mfd_max77705.ko
264  pdic_max77705.ko
```

This is a different order from the recovery list, which is why the recovery list
could not stand in for it: there the same five sit at 362, 379, 381, 401 and 405
of 446.

### The dependency closure, which is the other half

`modules.dep` was read in the same pass. `pdic_max77705.ko` closes over
**thirteen** modules:

```
mfd_max77705.ko        usb_typec_manager.ko    switch_class.ko
dwc3-msm.ko            common_muic.ko          usb_notify_layer.ko
usb_f_ss_mon_gadget.ko vbus_notifier.ko
qc_usb_audio.ko        pdic_notifier_module.ko
redriver.ko            if_cb_manager.ko
spu_verify.ko
```

and `mfd_max77705.ko` closes over `usb_notify_layer.ko` alone. So a candidate
that wants to load the mux driver itself needs fourteen modules, not one, and
the set reaches into the USB stack — `dwc3-msm.ko` and
`usb_f_ss_mon_gadget.ko` are in it. `spu_verify.ko` is in the closure too,
which is worth noting against the custom-65 design that drops it.

Both facts came from one read-only D0. No writes, two body reads of pinned
paths, `device_writes` false, `reboot_requested` false, `partition_transfer`
false, `candidate_used` false, `f1_authorized` false, `live_authorized` false.

### The firmware path was taken too, and agrees

`super.img` is being extracted from the 9.68 GB firmware ZIP to the SD card in
parallel, streaming so that neither the 8.87 GB `super.img.lz4` nor the result
has to be resident: `unzip -p` into `tar -xO super.img.lz4` into a streaming LZ4
decoder. It reuses `s22plus_boot_verify`'s block decoder and header rules rather
than reimplementing them, and was checked against that module by decoding
`dtbo.img.lz4` both ways to the same SHA-256. `boot.img`, `vendor_boot.img`,
`dtbo.img`, `recovery.img` and both `vbmeta` images are already extracted.

It finished: `super.img` decoded to 10,352,130,812 bytes, exactly the size the
LZ4 frame declared, which verifies the decode without holding the output in
memory to checksum it.

The image is Android-sparse, and the raw super partition does not fit in the
remaining space, so it was never materialised. The reader indexes the sparse
chunk table — headers only — and serves random reads by seeking into the
covering chunk, which is enough to parse LP metadata directly out of the sparse
file. That gives the logical partition table: `system` 6.67 GB, `vendor`
2.18 GB, `product` 1.31 GB, `system_ext` 183 MB, `odm` 21 MB, and
**`vendor_dlkm` 57,610,240 bytes**.

`vendor_dlkm` was extracted to 57,610,240 bytes, SHA-256 `e5386d68…`, and is
**F2FS** — no ext4 or EROFS reader applies, and no F2FS tooling is installed. It
did not need one. The 5,843 bytes read from the device appear **verbatim** in
that image at offset 33,624,064.

So Gate 0 closes from two independent sources that agree byte for byte: the
running unit's `/vendor/lib/modules/modules.load`, and the firmware's
`vendor_dlkm` extracted from the 9.68 GB ZIP without ever writing the raw super
partition to disk.

## The hand-written readers, checked against reference tools

`lz4`, `f2fs-tools`, `python3-pyelftools` and `device-tree-compiler` were
installed after the extraction, through a GUI polkit prompt. Nothing above
depended on them — every step was done without them — so installing them turned
into an independent check of the readers this campaign wrote, which is more
useful than the convenience.

**The streaming LZ4 decoder matches the reference implementation exactly.**
Decoding each already-extracted image again with `lz4 -d -c` gives the same
SHA-256:

| image | this campaign's decoder | `lz4` 1.10.0 |
|---|---|---|
| `dtbo.img` | `97a4864fee4e6189…` | `97a4864fee4e6189…` |
| `boot.img` | `4150b962314e6136…` | `4150b962314e6136…` |
| `vendor_boot.img` | `096e433e049fb088…` | `096e433e049fb088…` |

**The sparse reader and the LP extent arithmetic check out too.**
`fsck.f2fs --dry-run` on the extracted `vendor_dlkm.img` reports a fully
consistent filesystem — unreachable NAT entries `0x0`, SIT bitmap OK, hard-link
check OK, `valid_block_count` `0x25a1`, `valid_node_count` `0x178` by both
lookups, `valid_inode_count` `0x171`, no corrupted structures. A partition
extracted with the extent maths off by a single block would not check out clean,
so this validates the sparse chunk indexing, the LP metadata parse and the
extent offsets together.

`f2fs-tools` does not provide a file extractor, so the byte-verbatim match at
offset 33,624,064 remains the file-level proof; `fsck` is the image-level one.

**One documented gap is now closed.** The streaming decoder skips the LZ4 frame
content checksum by design, because verifying it needs the whole 10 GB output
resident, which is the thing being avoided; the report recorded that as an
explicit non-verification. Native `lz4 -t` verifies exactly that checksum
without keeping the output, so the stream was re-run through it.

## Step 3: a candidate does not have to mount anything

The question was whether a native-init PID 1 can reach `/vendor/lib/modules`.
Framed that way it looks hard: that path is on `vendor_dlkm`, a **logical**
partition inside `super`, so mounting it means reading LP metadata on the device,
building dm-linear maps through `/dev/mapper/control`, then mounting F2FS.

It does not have to. The `vendor_boot` ramdisk carries **441 `.ko` files** in its
own `lib/modules`, and the candidate already has that ramdisk as its rootfs.

`pdic_max77705.ko`'s closure there is 23 modules, 24 with itself, and **all 24 are
present in the vendor_boot ramdisk**. Every one carries the same vermagic:

```
5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 SMP preempt mod_unload modversions aarch64
```

which is the stock kernel the candidate boots, and none of them is signed.

### The marginal set is 14, derived twice and agreeing

The ramdisk's first-stage `modules.load` is 140 lines and already contains 10 of
the 24. The remaining **14** are what a candidate must load itself:

```
usb_notify_layer  mfd_max77705  switch_class  common_muic  pdic_notifier_module
vbus_notifier  usb_typec_manager  usb_f_ss_mon_gadget  redriver  if_cb_manager
qc_usb_audio  dwc3-msm  spu_verify  pdic_max77705
```

That is exactly the device's `modules.dep` closure of 13 plus `pdic_max77705.ko`
itself — two independent derivations, one from the running unit and one from the
ramdisk minus the first-stage list, landing on the same fourteen.

### `modules.load.recovery` is not an insmod order

This is the part that would have broken a candidate quietly. The 446-line
recovery list is a **`modprobe` input**; `modprobe` resolves order from
`modules.dep` itself. Read as a sequence for `finit_module`, it violates
dependencies **ten times** for this set alone:

```
dwc3-msm needs usb_notify_layer, usb_f_ss_mon_gadget, redriver,
               if_cb_manager, qc_usb_audio, usb_typec_manager  — all later
usb_f_ss_mon_gadget needs usb_typec_manager, usb_notify_layer  — both later
usb_typec_manager needs pdic_notifier_module                   — later
pdic_max77705 needs spu_verify                                 — later
```

A freestanding PID 1 inserting in list order fails at the first of those with an
unknown-symbol error. The computed topological order does not:

```
 1 usb_notify_layer     6 vbus_notifier         11 qc_usb_audio
 2 mfd_max77705         7 usb_typec_manager     12 dwc3-msm
 3 switch_class         8 usb_f_ss_mon_gadget   13 spu_verify
 4 common_muic          9 redriver              14 pdic_max77705
 5 pdic_notifier_module 10 if_cb_manager
```

`s22plus_fyg8_p319_module_closure_plan.py` computes all of this from the images,
reading `depends=` out of each `.modinfo` with a minimal ELF section reader so it
adds no dependency of its own, and it checks a proposed order rather than
assuming one. The suite exercises the violating-order case, a cycle, a missing
`.modinfo`, and the first-stage subtraction against synthetic ELF fixtures.

### One difference between the two module sets, stated as unresolved

The ramdisk's `modules.dep` closure for `pdic_max77705.ko` is 23; the device's is
13. Every member of the device's 13 is in the ramdisk's 23, and the extra ten —
`abc`, `clk-qcom`, `debug-regulator`, `gdsc-regulator`, `minidump`,
`proxy-consumer`, `qcom_ipc_logging`, `sec_class`, `sec_debug`, `smem` — are all
in the first-stage list, which is consistent with `vendor_dlkm`'s list not
needing to re-declare what the first stage already loaded.

Whether the two `pdic_max77705.ko` files are the same build is **not settled**.
The ramdisk copy is 423,456 bytes and does not appear verbatim in
`vendor_dlkm.img`, but that image has F2FS compression enabled, so a byte search
proves nothing either way. `.modinfo depends=` differs between what the ramdisk
copy declares and what the device's `modules.dep` lists, which is expected from
the first-stage subtraction but has not been checked against the device copy's
own `.modinfo`. A candidate loads the ramdisk copy, so this does not block the
plan; it is recorded because "same name" is not "same module".

## Independent review (Codex GPT-5.6-Luna, reasoning max, read-only sandbox)

The review was run with `codex exec -s read-only`, so the no-device and no-write
constraints were enforced by the sandbox rather than by prompt text. A parallel
Claude reviewer was also started and died on a session limit before reporting;
its stub carried no checkable claim, so nothing from it is recorded here.

Two of its findings are corrections to text this report already published. Both
were verified against the source before being accepted.

### Correction: "reached the wire" is overstated

This report said the CONTROL1 write "was serialised and handed to I2C" and the
commit said "proved at the wire". The hex dump does not prove that:

```
max77705_usbc.c:1903   print_hex_dump("max77705: opcode_write: ", write_values, …)
max77705_usbc.c:1909   ret = max77705_bulk_write(usbc_data->muic, OPCODE_WRITE, …)
```

The dump prints the **buffer about to be sent**, before the transfer. And the
caller discards the result: `max77705_switch_path` is `static void`
(`max77705-muic.c:326`), so no MUIC-level code observes whether the write
succeeded.

What the trace actually proves is that the kernel constructed a `CONTROL1` write
carrying `0x09` and called the bulk write. What it does not prove is I2C
acknowledgement, or that D+/D- conducts.

One piece of corroboration is available and was checked rather than assumed:
`max77705_usbc_cmd_run` logs `i2c write fail. dequeue opcode` when the write
returns negative (`max77705_usbc.c:2451`). That string appears **zero** times in
the capture. Absence of the failure log is evidence the write returned success;
it is still not a bus trace.

### Correction: the 14-module set is not the candidate's plan

The review warns against conflating two different sets, and it is right. The 14
modules derived here are specifically the `pdic_max77705` closure after
first-stage subtraction. The **active P3.17 candidate plan is 69 entries**, of
which 42 overlap first-stage names and **27 are genuinely late** — DWC3, EUD,
both PHYs, GLINK, GENI/I2C, Type-C/MUIC, redriver and the USB notifier modules.
The 14 is a subset of a different question, and this report should not be read as
specifying what a candidate must load.

### What the review says about the frontier

It does not reject the mux; it demotes it. `0x09` is the encoded `COM_USB`
protocol value, and P3.17's diagnostic issues SMBus commands directly rather than
exercising `max77705_muic_attach_usb_path`, so P3.17 shows that **the command
protocol can be reached and CONTROL1 can retain COM_USB** — not that the analog
path conducts. It proposes the stronger current frontier is
`role request → UDC bind → DWC3 pull-up/connect → physical host attach`, and
notes a successful UDC bind reaches `usb_gadget_connect()` and
`dwc3_gadget_pullup(true)` while still not proving host attach.

It also states P3.17 enumerated CDC-ACM at high speed after a topology change, so
"nothing ever enumerated" is literally false, and that P3.18 must not be used as
mux evidence at all: inserting the latch shifted `eud.ko` from index 37 to 38
while the runtime still read index 37, so the diagnostic was never reached.

### Where it agrees with the DTBO work done here

Independently of this session's DTBO analysis, the review confirms the overlays
do carry USB/MUIC topology — role-switch `dr_mode=otg`, `maximum-speed`, the
Max77705/PDIC nodes and the Samsung USB notifier — and corrects an older campaign
claim: the DWC3 `usb-phy` array lives in the **base vendor DTB**, not the
overlay, so a plan to "edit DTBO to remove the SS PHY phandle" would not target
the real property. That is consistent with what was found here: `fragment@63`
supplies `max77705@66` onto `qupv3_se5_i2c`, and `ramoops_region` is in the
vendor_boot DTB rather than the DTBO.

### Its ranked host-only work, none of which needs a device

1. Extract `system`, `vendor`, `product`, `system_ext`, `odm` from the `super.img`
   already on disk and search stock init/HAL for `sys.usb.*`, `usb_role`,
   `a600000.ssusb/mode`, `UDC`, `configfs`, `typec`, `pdic` — to find the Android
   choreography PID 1 omits. A prior report's "system/vendor unavailable" is now
   stale because `super.img` is present.
2. Diff the 69-entry P3.17 plan against the 140-entry first-stage list.
3. Compare `.modinfo`, `__versions` and ELF identity of the ramdisk vs
   `vendor_dlkm` `pdic_max77705.ko` — the identity this report left unresolved.
4. Complete the static `CONTROL1` writer graph, including whether a later MUIC
   event (water handling can issue `COM_OPEN` or `COM_USB_CP`,
   `max77705-muic.c:1824`) can reopen the path after `COM_USB`.
5. Trace `dwc3_msm_probe`, `dwc3_msm_set_role`, `mode_store`,
   `usb_gadget_connect`, `dwc3_gadget_pullup` and the `dwc3_event` tracepoint.
6. Bootloader analysis is **not** possible from the extracted set — the AP
   material contains no analyzable BL/S-Boot/ABL/XBL image, so "Download-only mux
   programming" versus "all-boots inheritance" stays undecidable.
