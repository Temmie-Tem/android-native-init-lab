# S22+ FYG8 P2.79A PMIC GLINK and UCSI activation analysis

Date: 2026-07-27 KST

## Verdict

This unit answers two pre-design questions for the prospective P2.80
candidate.

```text
pmic_glink.ko in the exact P2.76 60-module closure: YES
ucsi_glink.ko in the exact P2.76 60-module closure: YES

PMIC_RTR_ADSP_APPS can become operational from that exact closure: NO
UCSI can act as an external DEVICE-role producer in that exact candidate: NO
P2.76 took the explicit PID1 peripheral-write branch: STRONGLY INFERRED
```

The first pair proves only module insertion. It does not prove platform bind,
RPMSG endpoint creation, PMIC GLINK UP, UCSI child creation, or a UCSI role
request.

The exact FYG8 transport requires the ADSP remoteproc path. The P2.76 closure
contains neither the matching `qcom_q6v5_pas.ko` driver nor another owner that
registers the ADSP GLINK subdevice. The rebuilt kernel contains no built-in
replacement. The bare PID1 runtime also does not mount `/vendor`, and the
candidate embeds no firmware.

The P2.79 conclusion that UCSI can structurally reach the parent DWC3 role
callback remains correct. Its open branch in which UCSI could have raced the
P2.76 PID1 request does not survive this activation analysis.

## Boundary

This is host-only, read-only analysis. It performs no source mutation, build,
image generation, D0, approval, transaction, reboot, flash, or device write.

Inputs are:

- the exact P2.76/P2.60 v6 materialized runtime and module plan;
- the exact candidate `.config`, `System.map`, and static result;
- the FYG8 stock DTB set and stock vendor modules;
- the matching FYG8 DWC3-MSM and UCSI source;
- the existing exact FYG8 USB module map; and
- upstream Android common and Linux firmware documentation as method
  cross-checks only.

## A. Exact Closure Membership

The historical P2.41 plan has 59 modules. It contains:

```text
original index 46: pmic_glink.ko
original index 58: ucsi_glink.ko
```

P2.57 inserts `dispcc-waipio.ko` at index 33 and changes the checked module
count from 59 to 60. The exact P2.60 v6 materialized plan therefore contains:

```text
materialized index 47: pmic_glink.ko
materialized index 59: ucsi_glink.ko
```

The same plan contains no:

```text
qcom_q6v5_pas.ko
usb_notifier_qcom.ko
max77705*.ko
```

The exact static result independently records `module_count=60`. P2.76 passed
the complete module sequence, so both named modules were inserted. No bind
gate or retained record proves that either module acquired its operational
transport.

## B. PMIC GLINK Is an RPMSG Consumer

The exact FYG8 `pmic_glink.ko` imports:

```text
__register_rpmsg_driver
rpmsg_send
of_platform_populate
pdr_add_lookup
```

Its RPMSG ID table contains:

```text
PMIC_RTR_ADSP_APPS
PMIC_LOGS_ADSP_APPS
```

The exact binary establishes this order:

1. `pmic_glink_probe()` registers the platform-side state and PDR/SSR
   machinery.
2. `pmic_glink_rpmsg_probe()` runs only when a matching RPMSG device exists.
3. That RPMSG probe stores the endpoint, marks the link state UP, and queues
   `pmic_glink_init_work`.
4. `pmic_glink_init_work()` notifies registered clients and calls
   `of_platform_populate()` for the PMIC GLINK children.
5. Before UP, `pmic_glink_register_client()` returns `-EPROBE_DEFER`.

The exact `ucsi_glink.c` then registers through
`pmic_glink_register_client()`. All UCSI reads and writes use
`pmic_glink_write()`, and its state callback creates or destroys the UCSI core
according to PMIC GLINK UP/DOWN.

Consequently:

```text
finit_module(pmic_glink.ko) == 0
finit_module(ucsi_glink.ko) == 0
```

does not imply:

```text
PMIC_RTR_ADSP_APPS exists
PMIC GLINK is UP
the qcom,ucsi child was populated
ucsi_glink probed
a UCSI connector event reached DWC3
```

## C. Exact FYG8 Transport Owner

All four concatenated FYG8 stock DTBs have the same load-bearing topology:

```text
/soc/remoteproc-adsp@03000000
  compatible = "qcom,waipio-adsp-pas"
  status = "ok"

/soc/qcom,pmic_glink
  compatible = "qcom,pmic-glink"
  qcom,pmic-glink-channel = "PMIC_RTR_ADSP_APPS"
  qcom,subsys-name = "lpass"
  qcom,protection-domain =
    "tms/servreg", "msm/adsp/charger_pd"

/soc/qcom,pmic_glink/qcom,ucsi
  compatible = "qcom,ucsi-glink"
```

The exact stock `qcom_q6v5_pas.ko`:

- matches `qcom,waipio-adsp-pas`;
- names `adsp.mdt`;
- imports `request_firmware`, `qcom_mdt_load_no_free`,
  `qcom_add_glink_subdev`, and `rproc_add`; and
- is therefore the owner that binds the ADSP node, loads the remote image, and
  adds the AP-side GLINK subdevice.

The exact `qcom_glink_smem.ko` is support code. It exports
`qcom_glink_smem_register/start/unregister` and has no platform or RPMSG
matching table that independently instantiates the ADSP edge.

The P2.76 closure does load `rproc_qcom_common.ko`, `qcom_glink.ko`, and
`qcom_glink_smem.ko`. Those are dependencies and transport implementations;
none is the missing owner that binds `qcom,waipio-adsp-pas` and calls
`qcom_add_glink_subdev()`.

The candidate kernel confirms there is no built-in substitute:

```text
CONFIG_REMOTEPROC=y
CONFIG_RPMSG=y
CONFIG_EXTRA_FIRMWARE=""
System.map: no qcom_q6v5_pas or qcom_add_glink_subdev owner
```

Even a bootloader-retained ADSP would not create the AP-side RPMSG device by
itself. The exact candidate still lacks the kernel owner that registers the
GLINK remoteproc subdevice and publishes `PMIC_RTR_ADSP_APPS`.

Disposition:

```text
PMIC GLINK platform module inserted: PROVED
PMIC GLINK RPMSG endpoint available: STRUCTURALLY RULED OUT
PMIC GLINK UP: STRUCTURALLY RULED OUT
UCSI child operational: STRUCTURALLY RULED OUT
```

These dispositions apply to the exact P2.76 closure, not to stock Android or
to a future closure that deliberately adds the ADSP remoteproc stack and
firmware.

## D. Complete `vbus_active` Producer Filter

The matching DWC3-MSM source initializes `mdwc` with `devm_kzalloc()`.
`vbus_active` therefore starts false.

The source assignments that can make it true were filtered as follows.

| Producer | Exact-candidate disposition |
|---|---|
| `dwc3_msm_set_role(USB_ROLE_DEVICE)` | available to PID1 and structurally available to UCSI |
| `dwc_msm_vbus_event(true)` | exported, but its exact Samsung caller `usb_notifier_qcom.ko` is absent |
| extcon VBUS notifier | not active in the exact module build |
| default probe peripheral mode | excluded because the parent role switch is registered |
| DP start/stop helper | only restores DEVICE when `vbus_active` was already true; not an initial producer |

The base DTB contains an `extcon` phandle to EUD, while the applied FYG8
overlay supplies the USB role-switch topology. This does not reactivate the
extcon producer. The matching source returns immediately from
`dwc3_msm_extcon_register()` when `CONFIG_USB_NOTIFIER` is enabled, and the
exact `dwc3-msm.ko` has no undefined references to
`extcon_register_notifier()` or `extcon_get_edev_by_phandle()`. It does contain
the exported Samsung notifier entry point, whose caller is absent from the
60-module plan.

The default probe assignment is also inapplicable. The source executes it only
when both `mdwc->role_switch` and `mdwc->extcon` are absent. The exact FYG8
overlay registers the parent role switch before the extcon/default check.

After excluding the non-operational UCSI path, no external producer remains in
the exact P2.76 runtime. The remaining DEVICE-role producer is the candidate's
own `mode_store("peripheral") -> dwc3_msm_set_role()` path.

## E. What P2.76 Therefore Means

The exact runtime first reads the parent `mode` attribute:

```text
peripheral -> skip write
none/host  -> write "peripheral"
```

Stage `0x8d` proves the final `peripheral` readback plus exact
`a600000.dwc3` membership. It does not retain the initial read or a
write-taken bit.

Static closure now removes every supported source of an initial external
DEVICE assertion. Within the exact source and module model, the initial read
was therefore `none` and PID1 executed the peripheral write.

Classification is deliberately:

```text
candidate peripheral write executed: SOURCE-DEDUCED / STRONGLY INFERRED
candidate peripheral write executed: not separately LIVE-PROVED
```

The distinction matters because the old retained ABI did not record the
branch. It would be incorrect to rewrite the historical F1 result as direct
live proof.

## F. P2.80 Design Steer

Do not make `none -> peripheral` retriggering the headline P2.80
discriminator. The first DEVICE request is already strongly inferred to have:

- set `vbus_active=true`;
- called `dwc3_ext_event_notify()`;
- flushed prior delayed work; and
- queued parent `sm_work`.

A second role cycle can remain a later recovery experiment, but by itself it
would not explain why the first request produced no host-visible
enumeration.

The next contract should instead locate parent-worker progress with the
smallest bounded evidence surface. Candidate design should distinguish at
least:

```text
role request accepted
parent sm_work entered
runtime-PM resume completed or failed
dwc3_otg_start_peripheral entered
PHY/redriver connect notification completed or failed
child role update completed
parent in_device_mode reached
generic gadget pull-up and terminal link/UDC state
```

Existing stable userspace attributes cannot fence all of these points.
P2.80 must therefore choose one minimal source-owned observation mechanism
before implementation. It must not add the ADSP remoteproc, PMIC firmware, or
UCSI stack merely to recreate an external role producer that the candidate
does not need.

Mandatory independent host tracing remains part of any later live candidate.
The P2.76 result still lacks host connect/reset/descriptor evidence.

## Proof Limits

- P2.76 did not retain the initial mode string or an explicit branch bit.
- This unit proves the supported transport topology and exact closure, not the
  nonexistence of undocumented firmware behavior outside the inspected
  kernel/module model.
- No new runtime evidence was collected.
- The cause of the post-bind electrical/enumeration timeout remains open.
- This unit does not authorize P2.80 implementation, build, D0, or F1.

## Primary Cross-Checks

- Android common `pmic_glink.c` shows that PMIC GLINK is an RPMSG driver
  matched on `PMIC_RTR_ADSP_APPS`:
  https://android.googlesource.com/kernel/common/+/115e74a29b530d121891238e9551c4bcdf7b04b5/drivers/soc/qcom/pmic_glink.c
- Android common `qcom_q6v5_pas.c` shows the remoteproc owner adding the GLINK
  subdevice and registering the remote processor:
  https://android.googlesource.com/kernel/common/+/refs/tags/ASB-2024-05-05_11-5.4/drivers/remoteproc/qcom_q6v5_pas.c
- Linux 5.10 firmware documentation defines `request_firmware()` as a
  filesystem-backed firmware request:
  https://docs.kernel.org/5.10/driver-api/firmware/request_firmware.html

The exact FYG8 DTBs, modules, source, and candidate artifacts remain the
authoritative evidence for this target. The upstream sources only confirm the
transport model.
