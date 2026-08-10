# S22+ FYG8 Natural-Attach OTG Discriminator Feasibility H0

Date: 2026-08-11 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Verdict: `CONDITIONALLY_FEASIBLE_ROLE_PRODUCER_CLOSURE_REQUIRED`

## Corrective authority notice

The later host-only closure report
`S22PLUS_FYG8_NATURAL_ATTACH_ROLE_PRODUCER_CLOSURE_H0_2026-08-11.md`
supersedes this report's alternative-producer and execution proposal. Exact
P3.15 UCSI is structurally non-operational, and the sole producer selected for
future design is the stock Max77705 chain. Its role event still cannot be used
by bare PID1 until the Samsung `usb_sl` initialization policy and the separate
`otg` power-supply/VBUS closure are designed and reviewed.

The source/DT inventory, forced-host rejection, stock Android positive
control, witness taxonomy, result meanings, and physical-attach hazard
inventory below remain evidence. They do not make the old candidate shape
executable and grant no device authority.

## Scope and authority

This is host-only source, artifact, and existing-evidence analysis. No device
was contacted, no candidate was created, no payload was transferred, and no
D0, D1, or F1 authority exists. P3.15 is consumed and is never replayable. A90
identity, files, devices, and authority are outside this unit and untouched.

The question is whether a later boot-only candidate can use a physical OTG
attach as a discriminator for the remaining USB boundary without an inline
D+/D- breakout. This report establishes feasibility and the minimum result
contract; it does not freeze or qualify an implementation.

## P3.15 boundary correction

`p315_wait_restart_completion()` and the profile-bearing RESTART snapshot are
two separate reads. The first accepted exactly four complete
`dwc3_otg_sm_work` pairs plus one nested start-on pair. The second accepted
either the 41-record clean geometry or the 49-record bounded-drift geometry,
but its count was not retained. The terminal record later proved eight outer
pairs.

Therefore P3.15 establishes an exact restart completion prefix and a complete
final functional tuple, but not that all four extra workers occurred after the
RESTART snapshot. Their execution completed after the completion read; their
enqueue provenance may predate it. The frozen `REFUTED` label and prohibition
on cycle-causal, connector, and pull-up claims remain unchanged.

Queue-provenance measurement is required before reusing that cycle as a causal
experiment. It is not a mandatory predecessor for an independent OTG unit that
does not execute or inherit the `none -> peripheral` cycle.

## Why direct host forcing is rejected

The wrapper's `mode` sysfs implementation accepts host, but that does not make
it an admissible campaign action:

1. `s22plus_fyg8_p282_source_contract.py` rejects a generated runtime header
   containing `"host\\n"` with `SourceContractError`. A direct host-mode
   candidate does not package under the current source contract.
2. `dwc3_msm_set_role(USB_ROLE_HOST)` clears `vbus_active`, grounds `id_state`,
   and queues an external event. It does not call the Samsung `vbus_drive`
   callback and cannot by itself power a passive OTG device.
3. Manually forcing the role would bypass the exact CC/PD and Samsung notifier
   policy that this experiment needs to test.

No successor may work around that rejection by renaming the token, writing a
different role node, forcing the PMIC `otg` supply, or using EUD. Such a change
would be a different action and hazard, not this discriminator.

## Source and artifact feasibility

Two source-real natural attach routes exist, but they are not equivalent in the
current module plan:

```text
current-plan UCSI route:
physical Type-C attach -> PMIC PPM -> pmic_glink / ucsi_glink
  -> UCSI connector work -> usb_role_switch_set_role(HOST)
  -> dwc3-msm role switch

stock Samsung route:
physical Type-C DFP attach -> pdic_max77705 -> usb_typec_manager
  -> usb_notifier_qcom ccic_usb_handle_notification
  -> usb_notify_layer NOTIFY_EVENT_HOST
  -> qcom_set_host -> dwc_msm_id_event

common suffix:
dwc3 OTG worker -> dwc3_otg_start_host
  -> xHCI -> USB core -> usb-storage/UAS -> SCSI sd
```

The exact P3.15 module plan includes `pmic_glink.ko`, `ucsi_glink.ko`,
`usb_notify_layer.ko`, `pdic_notifier_module.ko`,
`usb_typec_manager.ko`, `phy-msm-snps-hs.ko`, `dwc3-msm.ko`, and
`usb_notifier_qcom.ko`. It does **not** include `pdic_max77705.ko` or its exact
dependency closure, even though the stock live role-path proof did. Therefore
the Samsung route cannot be inherited from P3.15. Detailed design must either:

1. prove that the loaded UCSI glink connector binds on the exact G0Q graph and
   naturally supplies host data-role events; or
2. add the stock Max77705 producer with its complete dependency/order closure
   and requalify the expanded module plan.

This is the first H0 gate, not something to discover in F1.

The UCSI source supports the first option: connector change handling derives
`USB_ROLE_HOST` for a UFP partner, reports Type-C data and power roles, and calls
the firmware-linked USB role switch. The exact G0Q overlays connect UCSI and
the DWC3 role-switch graph. That is source/DT feasibility, not live native-init
bind proof.

The fixed kernel config has `CONFIG_USB_OTG`, xHCI, DWC3, USB storage, UAS,
SCSI, and `BLK_DEV_SD` enabled. No functional kernel change or Full-LTO need
has been identified by this feasibility pass; module-plan expansion, encoding,
or probe audit may still invalidate fixed-Image reuse and must decide that
before implementation.

`dwc3_otg_start_host()` has one important silent branch: if `xhci_pm_ops` is
null it logs at debug level and returns success without starting host. A
role-readback alone is therefore insufficient. A detailed observer must prove
entry and passage beyond that guard or record the guard as the first failed
stage.

VBUS is a separate control plane. With `CONFIG_PDIC_NOTIFIER` enabled, the
Samsung notifier object's `auto_drive_vbus = NOTIFY_OP_PRE` initializer is
compiled out. On the UCSI route the PMIC PPM reports connector power direction;
the UCSI tracepoint exposes a `sourcing` bit but Linux's role report is not
itself proof of wire voltage. Physical power-role policy and any Samsung
PMIC/power-supply action must therefore be observed independently.
Enumeration of the exact passive device is the first conclusive positive proof
that usable VBUS and the data path both existed.

## Existing positive control

On 2026-08-10 the operator confirmed the exact S22+ under stock rooted FYG8
Android with the same known USB storage device and passive OTG adapter. Host
role, PMIC VBUS, xHCI, USB storage, `sd`, and filesystem mount all worked. The
accessory was also checked on a separate phone only as accessory evidence.

This is not Process-v2 evidence and grants no authority. It is a strong
hardware/accessory positive control: a native-init negative means some Android
host prerequisite was not reproduced. It does not make that negative a
single-valued shared-hardware result.

## Admissible candidate shape

A later candidate must not force host role or VBUS. The attended sequence is:

1. Flash and boot the boot-only candidate while the PC is the only USB peer.
2. Reach a durable, visually distinguishable `OTG READY` state after the exact
   notifier, wrapper, host, and storage observers are armed.
3. Detach the PC completely. Attach only the exact known passive adapter and
   storage device within one bounded physical-attach deadline.
4. Record a retained stage result, detach the accessory, and park. Do not mount
   or write the storage; exact USB identity plus mass-storage driver and new
   `sd` block appearance are sufficient for the discriminator.
5. Reconnect the PC, enter physical Download mode, transfer the one exact
   rollback, and verify final FYG8 health under Process-v2.

No powered hub, Y-cable, simultaneous PC/accessory connection, manual
power-supply write, filesystem write, or raw electrical/MMIO operation belongs
to this unit.

The attach wait needs one derived deadline and registered terminal details.
Deadline expiry after an integrity-clean wait is `ATTACH_NOT_SEEN`, a bounded
stage result. A malformed trace, missing retained commit, ring loss, or helper
failure is `NO_PROOF_OBSERVER`. The two classes must never share a detail.

## Witness and result contract

The observer should retain a monotonic witness mask plus first error; it should
not require a total order between independent Type-C, power, and host workers.
The minimum witness domains are:

| Domain | Required witness | Negative scope |
|---|---|---|
| Natural attach | UCSI connected/UFP source-role status or DFP/host notification from a qualified Samsung producer | CC/PD/PPM or notifier policy did not reach host request |
| Wrapper role | `dwc_msm_id_event(true)` and host OTG worker transition | notification reached qcom but wrapper host state did not |
| VBUS control | source-role/PMIC `otg` power action with return status | native power-source control did not complete; wire voltage remains unproved |
| Host controller | `dwc3_otg_start_host` past the `xhci_pm_ops` guard and xHCI role start | wrapper reached host but xHCI start did not |
| USB core | a new non-root USB device with the exact private accessory identity | host controller started but no device attached in USB core |
| Storage | mass-storage/UAS binding and a new `sd` block device for that USB parent | USB device attached but storage stack did not complete |

Later-stage evidence without an earlier software witness is not silently
rejected or reordered. It is a distinct provenance/observer contradiction,
because concurrent workers and incomplete attribution are possible.

The result meanings are:

- `OTG_STORAGE_PRESENT`: strong positive. The shared USB2 connector/data path,
  host-side PHY/controller path, usable VBUS, and storage stack worked under
  native init. This does not prove the peripheral pull-up circuit, but it
  removes a broad shared connector/data-path family.
- a bounded partial mask: identifies the first unproved native-init stage. It
  does not prove a dead PHY, cable, connector, or peripheral pull-up.
- `ATTACH_NOT_SEEN`: no natural DFP transition was captured within the attended
  bound. It is limited to the attach/CC/PD/policy boundary.
- observer-integrity failure: no device-path conclusion and mandatory rollback.

Filesystem mount is unnecessary for the discriminator. If a later objective
requires it, that is a separate design amendment and may use only an explicitly
reviewed read-only mount; it cannot be smuggled into this result.

## New hazard class and closure conditions

This candidate shape introduces two linked hazards not present in the
peripheral ACM units:

1. a physical Type-C data/power-role transition that causes the phone to source
   VBUS; and
2. intentional absence of the PC observer during the candidate measurement.

Before packaging, one independent review must cover the exact passive
accessory topology, overcurrent/VBUS-off evidence, operator swap instructions,
attach and park deadlines, retained-record integrity, Download re-entry, exact
rollback, and final health. The review is reusable only while that closure and
the execution-critical hashes remain unchanged. It reopens if the accessory
class, power topology, forced-control policy, observer machinery, or recovery
sequence changes.

The live hazard closes only after the accessory is detached, VBUS-source state
is observed off or superseded by physical Download recovery, the exact rollback
has completed once, and final rooted FYG8 health is durable. Until then the
target remains F1-armed and no other candidate may start.

## Remaining H0/D0 inputs

Before detailed implementation:

1. prove current-plan UCSI bind plus natural role delivery, or derive the full
   Max77705 module dependency/order expansion; then freeze exactly one role
   producer for the candidate;
2. derive the exact trace/sysfs witness coordinates and linked-symbol/offset
   validity for all six domains;
3. obtain a freshly authorized stock D0 only if exact Type-C role,
   power-supply, xHCI, and accessory sysfs coordinates cannot be proven from
   existing private evidence;
4. prove record, carrier, deadline, and Process-v2 single-port budgets through
   the real evidence adapter;
5. bind the exact accessory identity privately without committing serials or
   other identifiers; and
6. complete the new-hazard independent review before any candidate package is
   promoted.

P3.02 passive electrical attribution remains parked and may be prepared in
parallel. A positive OTG result can narrow its value; a negative OTG result
does not replace it.

## Non-conclusions

This report does not prove host operation under native init, does not authorize
an attach, role change, reboot, flash, or VBUS action, and does not choose a
P3.16 candidate ID. It does not reclassify P3.15, recover its lost work-queue
provenance, or prove that the peripheral pull-up did or did not reach the
connector.
