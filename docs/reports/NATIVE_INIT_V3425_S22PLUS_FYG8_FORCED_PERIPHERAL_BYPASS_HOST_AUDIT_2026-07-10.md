# V3425 S22+ FYG8 Forced-Peripheral Bypass Host Audit

## Verdict

`PASS; FORCED PERIPHERAL BYPASS ELF-VERIFIED; MAX77705 CHAIN OMISSION RULED OUT AS O3 NO-USB ROOT CAUSE IF MODE WRITE EXECUTED`.

V3425 closed the remaining interpretation gap from V3424. The exact FYG8
`dwc3-msm.ko` proves that writing `peripheral` to the bound controller's
`mode` sysfs attribute is an active role transition, not a cosmetic state
change. It synthesizes the device/VBUS state needed by the DWC3 OTG state
machine and reaches the peripheral-start path independently of the Samsung
Max77705 automatic-role notifier chain.

The audit and its verdict inputs were host-only. An initial read-only Android
baseline status check was used to select the unit but was not an evidence input.
There was no device write, reboot, module insertion, image build, or flash.

## Exact Input

```text
module=dwc3-msm.ko
sha256=8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1
static_schema=s22plus_fyg8_usb_role_static_re_v2
```

The existing full-module SHA pin remains the primary identity gate. V3425 adds
fail-closed symbol, relocation, string, instruction, and call-edge checks over
that exact binary.

## Verified Path

The module's `dev_attr_mode` data relocations select exact CFI thunks for
`mode_show` and `mode_store`. `mode_store` compares its input with the exact
`peripheral` rodata literal, maps that input to role value 2, and calls
`dwc3_msm_set_role`.

```text
mode_store("peripheral")
  -> dwc3_msm_set_role(role=2)
     -> set byte offset 858 = 1
     -> set word offset 864 = 1
     -> dwc3_ext_event_notify
        -> queue_delayed_work_on
        -> dwc3_otg_sm_work
           -> dwc3_otg_start_peripheral
              -> usb_role_switch_set_role
              -> vbus_session_notify
              -> usb_gadget_connect
```

The same byte offset 858 is written by `dwc_msm_vbus_event`. This is the
load-bearing proof that explicit role 2 establishes the same VBUS-active state
normally supplied by the automatic notifier path. The exact call graph then
reaches OTG work and gadget connect.

Seven forced-path call relocations are pinned:

```text
mode_store -> dwc3_msm_set_role
dwc3_msm_set_role -> dwc3_ext_event_notify
dwc3_ext_event_notify -> queue_delayed_work_on
dwc3_otg_sm_work -> dwc3_otg_start_peripheral
dwc3_otg_start_peripheral -> usb_role_switch_set_role
dwc3_otg_start_peripheral -> vbus_session_notify
dwc3_otg_start_peripheral -> usb_gadget_connect
```

## Consequence for O3/O3F

V3424 proved that stock automatic role policy uses:

```text
pdic_max77705 -> usb_typec_manager -> usb_notifier_qcom
  -> usb_notify_layer -> dwc3-msm events
```

V3425 proves that O3's deliberate fixed-peripheral route bypasses that policy
chain after `dwc3-msm` has successfully bound. Therefore adding the five
Samsung policy modules to the next O3 candidate is not justified by the no-USB
observation.

The O3 and O3F misses still cannot prove whether PID1 reached module loading,
the eight bind gates, the mode write, configfs setup, UDC bind, or a downstream
gadget start. Their host-observed silence is compatible with an earlier failure.
The precise conclusion is:

```text
forced_peripheral_role_bypass = ELF_VERIFIED_AFTER_DWC3_MSM_BIND
max77705_chain_required_for_forced_peripheral = false
o3_role_chain_omission_as_no_usb_root_cause = RULED_OUT_IF_MODE_WRITE_EXECUTED
o3_runtime_phase = UNVERIFIABLE
```

## Frontier Correction

The V3424 close incorrectly repeated `O0 next`. Repository history already
contains these completed layers:

```text
V3403 O0   stock ttyGS0/ttyACM0 control       LIVE PASS
V3409 O1.1 stock-first-stage early control    LIVE PASS + rollback
V3410 O2   native loader parity               HOST PASS
```

Those layers are retired as prerequisites, not repeated. The next bounded unit
is host-only design of a direct-PID1 phase-observation channel. It must not
repeat consumed O3/O3F/O3R1 candidates, must not add the Max77705 chain, and
must not create a live artifact or exception until one internal phase can be
reported independently of ACM success.

## Validation

```text
exact module SHA256                     PASS
sysfs mode callback relocations         PASS
peripheral literal -> role 2            PASS
role 2/shared VBUS-active field         PASS
forced-path call relocations            7/7 PASS
deep-RE focused tests                   8/8 PASS
device writes                           0
```

Generated evidence:

```text
docs/module-map/s22plus-fyg8/deep-usb-re/README.md
docs/module-map/s22plus-fyg8/deep-usb-re/static-analysis.json
```
