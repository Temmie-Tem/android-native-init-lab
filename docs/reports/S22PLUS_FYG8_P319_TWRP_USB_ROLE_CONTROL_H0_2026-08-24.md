# S22+ FYG8 P3.19 — TWRP USB role-control reconstruction (H0)

Date: 2026-08-24 KST

Status: **`PASS_GO_P319_TWRP_USB_ROLE_CONTROL_H0_CAPABILITY_V1`**

This is a host-only reconstruction of the exact retained g0q TWRP recovery
image. It performs no device contact, installation, transfer, reboot, USB
action, or candidate mutation. It grants no D0, D1, F1, recovery, replay, or
live authority.

## Question

The stock FYG8 recovery control uses an explicit userspace write to
`a600000.ssusb/mode`. The retained TWRP image historically exposed recovery
ADB, but its ramdisk contains no equivalent role write. The bounded question
was therefore:

> What exact kernel, DT, module, userspace, and ELF paths can explain TWRP's
> USB gadget, and may that explanation replace or expand the current P3.19
> candidate path?

The reproducible auditor is
`workspace/public/src/scripts/analysis/s22plus_fyg8_p319_twrp_usb_role_control.py`.
It is 45,748 bytes, SHA-256
`4ebaef3ae92916bd324d7006889b31f725a290efda5ea02c9bde28bbe6f37b4d`.
Its private deterministic receipt is:

```text
workspace/private/outputs/s22plus_fyg8_p319/
  twrp-usb-role-control-v1-20260824-01/result.json
22,967 bytes
SHA-256 6b08c15b18abcf027253087801412e2b447359c42ef45dbbc339e9223e6f8393
mode 0400, nlink 1
```

## Result

`PASS_P319_TWRP_USB_ROLE_CONTROL_H0`

TWRP has a complete static explanation for how it can reach a gadget without
an explicit recovery-userspace SSUSB role write:

1. its exact DWC3 wrapper queues an initially zeroed OTG state machine;
2. the zero-state arm calls `dwc3_msm_core_init()` and
   `of_platform_populate()` before a cable role is selected;
3. its ramdisk then binds configfs gadget `g1` to `a600000.dwc3`; and
4. its kernel contains two normal automatic role candidates: the Samsung
   PDIC/MUIC notifier path and the PMIC-glink UCSI role-switch path.

This does **not** identify which automatic producer won during the historical
live boot. It also does not prove that child/UDC registration succeeded in a
new run. The retained historical report has no role-transition trace.

Most importantly, it does not transfer to the current candidate. The TWRP
kernel and all eight compared module payloads differ, and its dependency graph
contains two Q6 modules absent from the current 73-row plan. Therefore this
unit justifies neither removing the candidate's direct `mode=peripheral` write
nor adding TWRP modules.

## Exact image identity

The auditor opens the exact 55,437,312-byte tar, SHA-256 `0914c68a...`, and
requires one regular member only:

| Item | Exact result |
|---|---|
| `recovery.img` | 55,435,280 bytes / `e4e18617...` |
| boot header | v2, page 4096, product `SRPUI14B002` |
| compressed kernel | 18,881,335 bytes / `7273b749...` |
| decompressed Image | 41,488,896 bytes / `6beb83aa...` |
| compressed ramdisk | 31,358,693 bytes / `1b155516...` |
| newc ramdisk | 111,237,120 bytes / `d1969834...` |
| base DTB stream | 1,717,704 bytes / `3a4b3cc7...` |
| recovery DTBO | 3,465,249 bytes / `daaa8789...` |

The kernel banner is
`5.10.81-afaneh92-g0418bf01a3e2`, built in June 2022. It is neither the FYG8
stock recovery/boot kernel nor the current candidate Image. IKCONFIG binds
dual-role DWC3, gadget, role-switch, Type-C/UCSI, extcon, configfs, and FunctionFS
support as built in.

## Userspace does not select the role

The exact `init.recovery.usb.rc` is 4,886 bytes / `7266cfcb...`. It creates
configfs gadget `g1` and contains four writes of:

```text
write /config/usb_gadget/g1/UDC ${sys.usb.controller}
```

The bound property is `sys.usb.controller=a600000.dwc3`. There is no wait for
`/sys/class/udc`, and an exhaustive scan of all 3,658 non-module regular
ramdisk files finds zero `a600000.ssusb` and zero `ssusb/mode` tokens.

The four base DTBs all set the child to `dr_mode=otg` and carry
`usb-role-switch`; none makes this a fixed-peripheral kernel. All five recovery
overlays retain the Samsung USB notifier, Max77705 MFD/PDIC, PD role swap, and
UCSI connector fixup, with no default-role property.

## Pre-role DWC3 materialization path

The exact 281,352-byte TWRP `dwc3-msm.ko` is SHA-256 `34c5bf46...`. The audit
binds symbol address and size as well as relocation-backed calls. In
particular:

```text
dwc3_msm_probe -> queue_delayed_work_on
dwc3_otg_sm_work -> dwc3_msm_core_init
dwc3_msm_core_init -> of_platform_populate
```

Instruction checks bind the zero-initialized allocation operands, the queued
OTG work, the state load at offset 792, the call to exact symbol address
`0xaf9c`, and the success transition to state one. This establishes a static
pre-role child/UDC-materialization path. It deliberately does not relabel that
path as runtime probe or UDC success.

## Automatic role candidates

The Samsung path is relocation-bound through:

```text
max77705_usbc_probe -> max77705_muic_probe
max77705_muic_probe -> max77705_muic_detect_dev
max77705_ccic_event_notifier -> pdic_notifier_notify
usb_notifier_probe -> manager/muic/vbus notifier registration
ccic or muic callback -> send_otg_notify
qcom_set_peripheral -> dwc_msm_vbus_event
```

The callback table at `.data+0x140` resolves to
`qcom_set_peripheral.cfi_jt` at `0xb98`; this is not inferred from a function
name alone.

The UCSI path is independently present:

```text
ucsi_probe -> pmic_glink_register_client
ucsi_probe -> ucsi_setup
ucsi_qti_state_cb -> queue_work_on
ucsi_qti_setup_work -> ucsi_setup
```

Presence of both paths is not proof that both ran or that either one was the
historical winner.

## Module population and candidate comparison

TWRP's `modules.load.recovery` has 440 lines / 438 unique names. Its
`dwc3-msm.ko` dependency closure has 28 members and includes PMIC glink, UCSI,
the Type-C manager, and its generation's SSUSB redriver. Relevant one-based
load positions include DWC3 254, UCSI 267, USB notifier 271, MFD 394, and PDIC
398. Q6 common/PAS modules are also listed at 317/318.

The current P3.19 plan remains 73 modules with EUD index 38. For the eight
shared names—EUD, PMIC glink, Type-C manager, DWC3, USB notifier, UCSI, MFD,
and PDIC—**zero** payloads are byte-identical between TWRP and P3.19. The
current plan also lacks `qcom_q6v5.ko` and `qcom_q6v5_pas.ko`.

Thus TWRP is an architectural comparison, not a provider-byte control for the
candidate. Its historical ADB result cannot close candidate bind, DWC3 probe,
UDC creation, or role-producer execution.

## Historical evidence boundary

The tracked 2026-07-06 report records that the exact `e4e18617...` recovery
prefix matched and that recovery ADB came up as TWRP. This unit preserves that
fact without replaying the action. The report retained no raw role transition
or winning-producer identity, so it cannot select between the two static paths.

## Frontier and proof limits

The current P3.19 design remains the narrower and better discriminator:

1. retain the existing SSUSB, DWC3, and UDC bind gates;
2. retain `waiting_for_supplier` and provider diagnostics;
3. retain the current bounded direct role write; and
4. decide from candidate-side evidence, not from TWRP's older kernel.

This result does not prove candidate module load, bind, probe, UDC creation,
host enumeration, MUX continuity, causal success, recovery availability, or
readiness. It changes no candidate byte and does not clear
`FRESH_BASELINE_MISSING`.

At implementation time topics 33 through 37 were independently unresolved and
this unit opened topic 38. Subsequent topic-34 and topic-37 reviews changed the
pre-review snapshot to 56 total / 38 resolved / 18 unresolved.

## Independent changed-closure review

An independent Luna review returned
`PASS_GO_P319_TWRP_USB_ROLE_CONTROL_H0_CAPABILITY_V1` with no load-bearing
finding. It regenerated the exact 22,967-byte receipt, rechecked the exact
TWRP image/kernel/ramdisk/DT/module identities, and confirmed that the older
TWRP kernel plus all eight byte-different shared modules remain architecturally
informative but non-transferable to the current 73-row candidate.

The review also confirmed that both automatic role-producer paths remain only
static candidates, the historical ADB observation selects neither one, and no
TWRP fact proves current candidate bind, probe, UDC creation, host enumeration,
or readiness. The current direct `mode=peripheral` path and all topic-37
candidate-side runtime gates therefore remain unchanged.

This review resolves only topic 38 and changes full-tail accounting from
56 / 38 / 18 to 56 / 39 / 17. It grants no baseline, ready/run/approval,
D0, D1, F1, recovery, replay, causal-result, candidate-success, device, or live
authority.

## Validation

- new TWRP role-control tests: **15/15 OK**;
- TWRP + current SSUSB/UDC + taxonomy + integration-doc selection:
  **73/73 OK**;
- common Process-v2 four-module selection: **142/142 OK**;
- taxonomy auditor: `PASS_P318_CAMPAIGN_LEDGER_TAXONOMY_H0_V3`;
- broad `test_s22plus_fyg8_p319*.py`: **581 total = 580 passed, zero
  failed, one error** in 246.500 seconds. The only error is the pre-existing
  independent materialization test requiring unavailable
  `/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko`; this is not
  reported as a green 581/581 run.

## Reproduction

```bash
PYTHONPYCACHEPREFIX=/tmp/p319-twrp-role-pycache \
python3 workspace/public/src/scripts/analysis/\
s22plus_fyg8_p319_twrp_usb_role_control.py --audit-only

PYTHONPYCACHEPREFIX=/tmp/p319-twrp-role-pycache \
python3 -m unittest -v \
tests.test_s22plus_fyg8_p319_twrp_usb_role_control
```

Expected verdict:

```text
PASS_P319_TWRP_USB_ROLE_CONTROL_H0
```
