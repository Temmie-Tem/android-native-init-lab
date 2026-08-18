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
`c63bb17db51b42598535a7746217d0a4741c635da4a6233b1775df7343193177`, 875 bytes.
Machine-checked safety: zero sysfs writes, zero attribute-body reads, zero debugfs
access, zero `/dev/i2c` access, zero module actions, zero reboots; listing and
inode tests only.

Registering it moved the auditor's closed-observer population from 121 to 122. The
raw-first auditor stopped on `closed observer source inventory differs: count=122`
and forced the registration rather than admitting a new device-touching source
silently, which is the boundary behaving as designed.

## Stage B re-derived: there is no sysfs read path to the mux

An earlier draft of this report said Stage B "was scoped as a single-attribute
CONTROL1 read". That was wrong and is corrected here. `CONTROL1` is not a sysfs
attribute at all: it is an I2C register reached through the MUIC command protocol,
where `CONTROL1_R`/`CONTROL1_W` are opcodes `0x05`/`0x06`. The predecessor stop
report of 2026-08-17 states the real position, that "whether Stage B has one exact
regular attribute target" was itself unproved.

Re-deriving it from the candidate's own materialized sources
(`kernel_platform/msm-kernel`) gives a negative answer, and closes the branch.

**The search location was wrong.** The MUIC attribute group is created on
`switch_device->kobj` (`drivers/usb/typec/maxim/max77705-muic.c:2553`), not on the
I2C client. Nothing the MUIC driver exposes was ever going to appear under
`57-0066`, so the absent `regmap` entry was not the loss of an assumed path.

**No exposed attribute reads `CONTROL1`.** In the whole MUIC driver `CONTROL1`
occurs exactly once, at `:343`, as `COMMAND_CONTROL1_WRITE`. There is no read
opcode issued anywhere in it, and therefore none reachable from sysfs.

What the group does expose, classified by what a read would actually prove:

| Attribute | Mode | What a read returns |
|---|---|---|
| `usb_sel` | 0664 | `pdata->usb_path`, a software cache (`:669-677`) |
| `usb_state`, `attached_dev` | 0444 | `muic_data->attached_dev`, a software cache (`:790-799`, `:817`) |
| `adc`, `vbus_value`, `vbus_value_pd` | 0444 | a real single-register I2C read of `USBC_STATUS1` (`:591`, `:608`) |
| `uart_sel`, `uart_en`, `otg_test`, `apo_factory`, `afc_disable`, `hiccup` | writable | out of scope |

So the three software-cached attributes cannot distinguish "the mux was set" from
"the driver believes it set the mux", which is precisely the question P3.15 left
open. The three genuine reads return `USBC_STATUS1`, a different register from
`CONTROL1`; they are safe and real, but they do not answer the mux question.

**Consequence.** Stage B cannot be a sysfs read. Reaching `CONTROL1` requires the
bound-diagnostic path already described in
`S22PLUS_FYG8_MAX77705_CONTROL_PLANE_SUCCESSOR_FEASIBILITY_H0_2026-08-11.md`,
which drives the command protocol directly. That is a materially larger step than
a read and is not authorized here. This report establishes no Stage B authority
and requests no device action.

## Authority boundary

Read-only D0. `device_writes` false, `reboot_requested` false,
`partition_transfer` false, `candidate_used` false, `f1_authorized` false,
`live_authorized` false. The A90 attached in recovery on the same host received no
command. No S20+ action occurred. Full regmap dumps remain forbidden.
