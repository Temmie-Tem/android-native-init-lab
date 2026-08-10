# S22+ FYG8 Natural-Attach Role-Producer Closure H0

Date: 2026-08-11 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Verdict: `MAX77705_ROLE_PRODUCER_SELECTED_OTG_EXECUTION_NOT_READY`

## Scope and authority

This is host-only source, artifact, and existing-evidence analysis. No device
was contacted, no candidate was created, no module plan was changed, and no
D0, D1, or F1 authority exists. P3.15 remains consumed and non-replayable.
A90 identity, files, devices, and authority are outside this unit and were not
touched.

This report supersedes only the role-producer choice and execution proposal in
`S22PLUS_FYG8_NATURAL_ATTACH_OTG_DISCRIMINATOR_FEASIBILITY_H0_2026-08-11.md`.
That report's hardware/accessory inventory, stock-Android positive control,
forced-host rejection, result meanings, and physical-attach hazard inventory
remain evidence. They do not authorize execution.

## Result

The two previously listed producer routes are not simultaneous live choices in
the exact P3.15 native closure:

- the PMIC-GLINK/UCSI route is structurally non-operational because the exact
  closure has no ADSP remoteproc owner, matching firmware, or `/vendor`
  firmware path; and
- the Samsung Max77705 route is the exact stock role producer, but P3.15 omits
  its I2C substrate, MFD/PDIC drivers, and one symbol dependency.

The only source-supported producer to carry forward is therefore the Samsung
Max77705 chain. It must replace, not accompany, `ucsi_glink.ko` in a future
candidate. Selecting the producer does not make OTG executable: the Samsung
lockscreen-policy gate and the separate `otg` power-supply/charger closure are
still open.

## UCSI is not an operational producer in P3.15

The exact P3.15 plan contains `pmic_glink.ko` and `ucsi_glink.ko`, but it still
lacks `qcom_q6v5_pas.ko`, an embedded ADSP image, and a mounted `/vendor`
firmware source. The prior exact activation audit proved that
`PMIC_RTR_ADSP_APPS` cannot be published under that closure:

```text
qcom,waipio-adsp-pas -- absent qcom_q6v5_pas/adsp.mdt --> no GLINK subdevice
  --> no PMIC_RTR_ADSP_APPS RPMSG endpoint
  --> pmic_glink never reaches UP
  --> qcom,ucsi child is never populated
  --> no UCSI role event
```

Insertion success for the two `.ko` files is therefore not a bind or event
proof. The current native closure has no evidence that could revive this path.
The authoritative activation analysis is
`S22PLUS_FYG8_P279A_PMIC_GLINK_UCSI_ACTIVATION_H0_2026-07-27.md`.

Consequently UCSI cannot explain the four additional P3.15 outer-work
completions. It also must not be loaded alongside Max77705 merely because both
routes exist in source; that would recreate a two-producer attribution problem
without making the dead transport operational.

## Max77705 is the exact stock role producer

The stock vendor ramdisk extraction contains the exact artifacts:

```text
pdic_max77705.ko
mfd_max77705.ko
```

The exact ELF/source/DT reconstruction and rooted-stock read-only cross-check
already establish this role path:

```text
994000.i2c / max77705@66
  -> mfd_max77705
  -> pdic_max77705
  -> usb_typec_manager
  -> usb_notifier_qcom
  -> usb_notify_layer
  -> dwc_msm_id_event(true)
```

The live stock evidence bound `max77705-usbc` to `pdic_max77705`, bound the
Samsung USB notifier, and captured an ordered PDIC-to-Type-C-manager relay. The
exact source supplies the USB branch: a DFP data role schedules
`PDIC_NOTIFY_ID_USB/USB_STATUS_NOTIFY_ATTACH_DFP`,
`ccic_usb_handle_notification()` emits `NOTIFY_EVENT_HOST`, and the host
callback calls `dwc_msm_id_event(true)`. This producer side is kernel
interrupt/workqueue/notifier code; it does not need an Android daemon to
create the PDIC role event.

The prior authority is
`NATIVE_INIT_V3424_S22PLUS_FYG8_USB_ROLE_DEEP_RE_2026-07-10.md` and its pinned
module-map artifacts. The fact that the downstream USB-attach branch was not
captured in that particular stock boot remains `NOT_CAPTURED_THIS_BOOT`; it is
not promoted to live proof here.

## Role-only module closure

P3.15 has 61 modules and already contains the notifier consumers. Relative to
that exact plan, the smallest source/symbol/DT closure for the Max77705 role
producer adds six modules:

```text
gpi.ko
msm-geni-se.ko
i2c-msm-geni.ko
spu_verify.ko
mfd_max77705.ko
pdic_max77705.ko
```

`{gpi, msm-geni-se} -> i2c-msm-geni` is a probe-time substrate for
`994000.i2c`; it is invisible from the PDIC `modules.dep` line. The exact PDIC
symbol closure adds `spu_verify` and `mfd_max77705`; all its other listed
dependencies are already in P3.15. The future order must bring up the GENI
substrate first, register manager/notifier consumers before the producer, and
load PDIC only after MFD and `spu_verify` are available.

Removing `ucsi_glink.ko` while adding those six names gives a provisional
66-module role-only plan. This is dependency arithmetic, not a packaging
qualification. Only `mfd_max77705.ko` and `pdic_max77705.ko` are staged in the
current small local vendor-ramdisk extraction; the other four exact stock
payloads still need an immutable host extraction/staging proof. Module-stage
capacity, load positions, bind gates, and exact file hashes must be qualified
before implementation.

Keeping `pmic_glink.ko` for an unrelated dependency would not make it a second
producer without operational UCSI. Whether to remove that dead support is a
later minimality decision; `ucsi_glink.ko` itself is excluded from the selected
producer design.

## Android-independent role generation is not Android-independent delivery

The exact `usb_notify_layer.ko` retains the lockscreen USB-restriction code:
its strings and symbols include `reserve_state_check`, `usb_sl`, and
`after wait`. Matching source establishes this sequence:

1. `usb_notifier_qcom` configures a ten-second boot delay.
2. A Max77705 DFP event reaches `send_otg_notify(NOTIFY_EVENT_HOST, 1)`.
3. While the delay is active, the HOST event is saved rather than dispatched.
4. `reserve_state_check()` waits until `lock_state` leaves
   `USB_NOTIFY_INIT_STATE` for a HOST event.
5. The Android policy stack moves the RW attribute
   `/sys/class/usb_notify/usb_control/usb_sl` out of its initial state; bare
   native PID1 has no corresponding policy action.

`usb_sl` accepts `USB_NOTIFY_UNLOCK`, `USB_NOTIFY_LOCK_USB_WORK`, or
`USB_NOTIFY_LOCK_USB_RESTRICT`; the initial value is a separate state. Only the
UNLOCK and USB-WORK branches explicitly wake the boot-delay wait, while the
RESTRICT branch represents a host-blocking policy. A future native runtime
therefore needs a deliberate, reviewed choice between the two releasing
states before relying on natural attach. This is not a forced role write, but
it releases a pending host event and can lead to VBUS sourcing. It is
execution behavior under the new physical-role/VBUS hazard and is not
authorized by this H0 report. The exact value and timing must be frozen in
detailed design rather than guessed during a live run.

This is the precise limit of the stock Android positive control: it proves the
hardware and the complete stack with Android policy present. It does not prove
that loading the same kernel modules under bare PID1 reproduces Android's
policy initialization.

## VBUS is a separate, larger closure

The selected role producer does not by itself provide usable 5 V. When the
Max77705 CC state becomes source, the PDIC code records power-source state and
calls `max77705_vbus_turn_on_ctrl()`. During the boot delay it reserves the
booster. Once the delayed HOST event is released, `usb_notify_layer` has
`auto_drive_vbus == NOTIFY_OP_OFF`; it drives VBUS only when source-role and
reserved-booster state are both present.

Both the Max77705 PD path and the Qualcomm notifier callback look up a power
supply named exactly `otg`. Exact source has one provider for that name:

```text
sec-battery.ko             registers "otg"
  -> battery,otg_name      = "max77705-otg"
  -> max77705_charger.ko   registers "max77705-otg"
  -> charger mode          = OTG boost
```

Neither module is in P3.15. Against the exact `modules.dep`, the
`max77705_charger.ko` closure contributes 23 missing modules, including the
three PDIC symbol modules already counted. The GENI bus trio is a separate DT
dependency. The complete provisional VBUS closure therefore adds 26 names and
removes one UCSI name, taking the plan from 61 to 86 modules:

```text
gpi.ko
msm-geni-se.ko
i2c-msm-geni.ko
kryo_arm64_edac.ko
max77705_charger.ko
memory_dump_v2.ko
mfd_max77705.ko
pdic_max77705.ko
qcom-cpufreq-hw.ko
sb-core.ko
sched-walt.ko
sec-battery.ko
sec_crashkey_long.ko
sec_debug_region.ko
sec_key_notifier.ko
sec_param.ko
sec_pd.ko
sec_pm_log.ko
sec_qc_dbg_partition.ko
sec_qc_hw_param.ko
sec_qc_smem.ko
sec_qc_summary.ko
sec_qc_upload_cause.ko
sec_qc_user_reset.ko
sec_upload_cause.ko
spu_verify.ko
```

This is an exact missing-name count, not approval to carry the whole stock
battery/debug closure into a candidate. Every added module, stage position,
probe side effect, and retained-observer budget still requires proportional
review. An alternative that changes the power-supply consumer or manually
drives a supply is a different implementation and hazard; it is not silently
substitutable.

## Fuel-gauge disposition

`max77705-fuelgauge.ko` is not required for the narrow `otg` provider/backend
bridge:

- it is absent from the exact `sec-battery.ko` and
  `max77705_charger.ko` dependency lines;
- `sec_battery_probe()` registers the `otg` proxy before any fuel-gauge
  availability check;
- `max77705_charger_probe()` registers `max77705-otg` without binding the
  fuel-gauge driver; and
- runtime `psy_do_property("max77705-fuelgauge", ...)` calls fail with a
  bounded `-ENOENT` and zero value rather than becoming a probe dependency.

The DT fuel-gauge node must exist because the charger reads its jig properties,
but the node exists independently of its driver. This finding excludes the
fuel-gauge only from the minimal OTG-power dependency proof. It does not claim
full stock battery behavior, suppress background error logs, or preclude a
future design from adding it for a separately justified reason.

## Relation to the P3.15 provenance gap

P3.15 loaded neither an operational UCSI transport nor the Max77705 MFD/PDIC
producer. The unexplained four additional outer-work completions therefore
cannot be attributed to either complete role-producer chain under that exact
closure. They remain compatible with the other already enumerated work/PM/
power queue sources. This narrows the old candidate list but does not recover
the destroyed enqueue ordering and does not upgrade P3.15's frozen result.

Selecting Max77705 for a new, independent natural-attach unit avoids a dual
producer. It does not make queue-provenance closure a mandatory predecessor
unless that new unit reuses the consumed `none -> peripheral` cycle or tries
to inherit a causal claim from it.

## Successor gates

No P3.16 candidate should be implemented from this report alone. Detailed H0
design must first close all of the following:

1. stage the exact six role-producer module payloads and prove their
   dependency/order, module-stage capacity, and I2C/MFD/PDIC bind gates;
2. choose whether the much larger 26-module VBUS closure is admissible or
   reject the candidate shape before packaging;
3. freeze and independently review the native `usb_sl` initialization value,
   timing, rollback behavior, and its VBUS consequence;
4. prove that exactly one producer is active and that no UCSI event can enter
   the observer contract;
5. derive retained witnesses for PDIC attach, delayed-policy release,
   `dwc_msm_id_event`, reserved-booster/VBUS status, xHCI, USB core, and exact
   storage identity without mounting or writing the accessory; and
6. re-run module-stage, record/carrier, single-port timing, Process-v2 adapter,
   Download recovery, and final-health qualification under the expanded plan.

P3.02 passive electrical attribution remains parked and independent. No D0 is
needed merely to select the producer; a future read-only stock comparison may
be requested only for coordinates not already fixed by the retained stock
evidence.

## Non-conclusions

This report does not prove native-init host operation, VBUS voltage, xHCI
start, storage enumeration, or peripheral pull-up behavior. It does not
authorize a sysfs write, module insertion, attach, role transition, VBUS
source, reboot, flash, or payload. It does not qualify an 86-module plan or
claim that all of those modules are an acceptable minimal runtime. Its only
producer-selection conclusion is that exact P3.15 UCSI is dead and Max77705 is
the sole source-supported natural-attach role producer to design against.
