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
