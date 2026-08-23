# S22+ FYG8 P3.19 — SSUSB mode and UDC plan closure (H0)

Date: 2026-08-24 KST

Status: **`PASS_GO_P319_SSUSB_UDC_PLAN_CLOSURE_H0_CAPABILITY_V1`**

This is a host-only answer to the first ranked question left by the stock
recovery control. It contacts no device, changes no candidate byte, creates no
approval or ready/run manifest, and grants no D0, D1, F1, recovery, replay, or
live authority.

## Question

The fresh stock-recovery control proved that the FYG8 stock path can enumerate
after recovery userspace writes:

```text
/sys/bus/platform/devices/a600000.ssusb/mode = peripheral
```

and waits for:

```text
/sys/class/udc/a600000.dwc3
```

The open host-side question was narrower than “does the candidate work?”:

> Does the exact current 73-row P3.19 plan omit a module, declared dependency,
> or known DT supplier needed to create the `mode` attribute and DWC3 UDC?

The reproducible checker is
`workspace/public/src/scripts/analysis/s22plus_fyg8_p319_ssusb_udc_plan_closure.py`.
Its private receipt is:

```text
workspace/private/outputs/s22plus_fyg8_p319/
  ssusb-udc-plan-closure-v1-20260824-01/result.json
15,276 bytes
SHA-256 55d0c115594776cbc3b77e8b385ba0652c0c67a43ef155c722bddaceb689b566
mode 0400, nlink 1
```

The checker itself is 29,253 bytes with SHA-256
`bfe653a9bdc15b32bc49df9d5204e00138d54c21731fd2938eec340cec3b9d0c`.

## Result

`PASS_P319_SSUSB_UDC_PLAN_CLOSURE_H0`

The answer is **yes for static membership, order, and ABI closure**. There is
no evidence-based missing-module branch left for the direct
`ssusb/mode=peripheral` path.

The answer remains **unproved for runtime bind and probe success**. A plan can
contain every driver and still fail because a firmware-node supplier did not
bind, `dwc3_msm_probe()` deferred or failed, or the child DWC3/UDC did not
materialize. This result deliberately keeps those propositions separate.

## Exact 73-row module closure

The checker parses the materialized plan source and independently compares it
with the bound Phase-1 result rather than accepting the declared count alone.

| Check | Result |
|---|---:|
| exact plan rows | 73 |
| custom rows | 1 (`s22plus_dwc3_event_latch.ko`) |
| FYG8 vendor rows | 72 |
| `.modinfo depends=` edges | 110 |
| missing declared dependencies | 0 |
| dependency-order violations | 0 |
| module/Image imports | 3,566 = 3,238 Image + 328 earlier modules |
| missing / ambiguous / duplicate providers | 0 / 0 / 0 |

The previously audited direct and nested SSUSB set is present before
`dwc3-msm.ko` at index 59. It includes the GCC/GDSC/RPMh/QNOC/PDC/IOMMU/EUD
chain, the Waipio pinctrl and regulator wrappers, the HS/eUSB2/QMP PHY modules,
and the exact vendor DWC3 wrapper. This is an audited set, not a claim that
every member is a mandatory direct provider: the exact DT has no redriver
phandle, for example.

The final three plan gates remain:

```text
10  /sys/bus/platform/drivers/msm-dwc3/a600000.ssusb
11  /sys/bus/platform/drivers/dwc3/a600000.dwc3
12  /sys/class/udc/a600000.dwc3
```

Both the direct and folded module loops finish before those gates, and all
twelve gates finish before the experiment runtime calls the role phase.

## Recovery comparison

The checker opens the exact 21,813,545-byte FYG8 vendor ramdisk, decompresses
the 63,974,144-byte newc archive, and reads the real module lists and `.ko`
members.

| Authority | Result |
|---|---:|
| `modules.load` | 140 lines, SHA-256 `8491b842...` |
| `modules.load.recovery` | 446 lines / 441 unique, SHA-256 `616bdb71...` |
| candidate stock rows present in recovery list | 72 / 72 |
| candidate stock module bytes equal to vendor ramdisk | 72 / 72 |
| candidate rows also named by first-stage list | 42 |
| recovery-only unique names outside candidate | 369 |

Thus the 73-row candidate is exactly one custom latch plus 72 modules whose
names all occur in the stock recovery list and whose bytes match the pinned
vendor ramdisk. The preceding recovery-image audit independently established
that the same `616bdb71...` list is the real recovery authority; this unit does
not relabel the vendor-ramdisk byte comparison as a fresh extraction of the
recovery image. The other 369 recovery names are not thereby proved
unnecessary to recovery as a whole. The narrower result is that none is
missing from the already source/DT-audited SSUSB direct and nested supplier
set, and every declared link dependency of all 73 rows is closed.

`modules.load.recovery` remains a `modprobe` input, not a safe direct-insmod
order. The candidate's zero-violation topological order is the relevant order
for its `finit_module` loop.

## Kernel and exact mode producer

The fixed candidate Image is 41,490,944 bytes, SHA-256 `71f573eb...`. Its own
IKCONFIG establishes:

```text
CONFIG_USB=y
CONFIG_USB_GADGET=y
CONFIG_USB_DWC3=y
CONFIG_USB_DWC3_DUAL_ROLE=y
CONFIG_USB_ROLE_SWITCH=y
CONFIG_TYPEC=y
CONFIG_TYPEC_UCSI=y
```

Therefore the DWC3 and gadget cores are built into this exact Image; the child
UDC does not require a missing `dwc3.ko` row.

The exact 308,624-byte `dwc3-msm.ko`, SHA-256 `8913b050...`, carries the
`qcom,dwc-usb3-msm` OF alias and the following relocation-backed call edges:

```text
mode_store -> dwc3_msm_set_role
dwc3_msm_set_role -> dwc3_ext_event_notify
dwc3_msm_usb_role_switch_set_role -> dwc3_msm_set_role
dwc3_msm_probe -> usb_role_switch_register
dwc3_otg_start_peripheral -> usb_gadget_connect
```

This binds the `mode` attribute to the exact shipped wrapper rather than to a
source-only name. The materialized runtime has two bounded direct writes —
`p260_wait_role_and_udc` and `p282_role_write_once` — and both target the exact
path with value `peripheral` before the configfs UDC bind.

## UCSI is a separate path

The plan contains `pmic_glink.ko` at 48 and `ucsi_glink.ko` at 61, and the
Image contains the UCSI core. It does not contain `qcom_q6v5_pas.ko` or
`qcom_q6v5.ko`, so the known stock ADSP-backed UCSI path is not functionally
closed by this plan. Another producer of that channel is not established
either way.

That gap does **not** reopen the direct recovery-style role path. The exact
`mode_store` edge calls `dwc3_msm_set_role` directly, so the explicit
`mode=peripheral` write does not wait for UCSI to choose the role. Stock
recovery is the positive control for that design shape, although its stock
Image is not the candidate Image and therefore does not prove candidate bind.

## What changed in the frontier

The next failure branch is not “add another USB module.” The exact plan already
contains and orders the known static closure. The next discriminator is the
one the runtime already carries:

1. bind gate 10: `a600000.ssusb`;
2. the bounded `waiting_for_supplier` and provider diagnostics on timeout;
3. bind gate 11: the built-in DWC3 child;
4. gate 12: the UDC class device;
5. only after those pass, the direct `peripheral` role write and gadget bind.

This matters because P2.50 already demonstrated the methodological limit:
module insertion can finish while `a600000.ssusb` still fails to bind. Static
closure removes a missing-member explanation; it cannot replace the runtime
gates.

## Reproducibility note

The historical P2.51 and P2.51b composite entrypoints currently fail closed
before their pure DT checks because their exact pin for
`stock-usb-runtime-topology.json` no longer matches the tracked file. This unit
does not silently repin that historical authority or claim those entrypoints
are currently green. It executes their pure exact-DTB direct and nested graph
audits against the pinned FYG8 DTB, then binds the current 73-row plan, Image,
module bytes, and vendor ramdisk independently.

## Proof limits

This unit does not prove:

- that any candidate module loaded or any platform driver bound;
- that `dwc3_msm_probe()` was entered or returned successfully;
- that the parent, child, or UDC exists in a candidate boot;
- which supplier would block a future candidate;
- that the natural UCSI path is required or operational;
- that the 73-row plan is sufficient for recovery as a whole;
- candidate success, host enumeration, MUX continuity, or a causal result; or
- readiness, fresh-baseline authority, F1 approval, replay, or live authority.

The current candidate boot/AP bytes and the `FRESH_BASELINE_MISSING` machine
blocker are unchanged. The independent review resolves topic 37 only; other
open topics remain unchanged.

## Independent changed-closure review

An independent Luna review returned
`PASS_GO_P319_SSUSB_UDC_PLAN_CLOSURE_H0_CAPABILITY_V1` with no load-bearing
finding. It rechecked the exact 73-row plan, 110 declared dependency edges,
zero missing/order violations, the `3,566 = 3,238 + 328` provider partition,
the fixed Image and module identities, all 72 vendor-module byte matches, and
the immutable private receipt.

The reviewer separately confirmed that dynamic supplier bind,
`dwc3_msm_probe()` success, candidate UDC creation, and a complete natural
UCSI path remain unproved. This PASS_GO therefore approves only the static
membership/order/ABI closure and cannot replace the runtime gates.

After the topic-34 review, this scoped review changes full-tail accounting
from 56 / 37 / 19 to 56 / 38 / 18. It grants no baseline, ready/run/approval,
D0, D1, F1, recovery, replay, causal, candidate-success, device, or live
authority.

## Validation

- focused current-plan, candidate, Process-v2-doc, taxonomy and closure tests:
  **118/118 OK**;
- common Process-v2 four-module selection: **142/142 OK**;
- the new closure module itself: **12/12 OK**;
- broad `test_s22plus_fyg8_p319*.py`: **566 total = 565 passed, zero
  failed, one error** in 252.594 seconds. The sole error is the pre-existing
  independent materialization path requiring the unavailable
  `/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko`; it is not a
  closure assertion failure and is not reported as a green 566/566 run.

## Reproduction

```bash
PYTHONPYCACHEPREFIX=/tmp/p319-ssusb-udc-pycache \
python3 workspace/public/src/scripts/analysis/\
s22plus_fyg8_p319_ssusb_udc_plan_closure.py --audit-only

PYTHONPYCACHEPREFIX=/tmp/p319-ssusb-udc-pycache \
python3 -m unittest -v \
tests.test_s22plus_fyg8_p319_ssusb_udc_plan_closure
```

Expected verdict:

```text
PASS_P319_SSUSB_UDC_PLAN_CLOSURE_H0
```
