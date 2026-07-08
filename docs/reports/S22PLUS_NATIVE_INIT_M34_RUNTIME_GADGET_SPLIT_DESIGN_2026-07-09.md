# S22+ M34 Runtime Gadget Split Design

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

2026-07-09 update: S0/P30 has now passed live. The next unit is M34 S1 host
build/live: stock-ordered configfs gadget/function/config with `UDC=none`, but
no `max_speed=high-speed`, no role force, and no final UDC bind. No S1 live
flash is authorized yet.

2026-07-09 later update: M34 S1/S2/S3 v0.2 host artifacts are now rebuilt from
the live stock ACM recipe and source-ready. Current state is tracked in
`docs/reports/S22PLUS_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_HOST_BUILD_2026-07-09.md`.

M34 should isolate the runtime gadget bring-up sequence, not continue module
list bisection.

P30 remains the next live gate, but only as S0 of this runtime split: prove that
loading `usb_f_ss_acm.ko` and parking does not reset before touching configfs.

No live flash is authorized by this report. `AGENTS.md` still has no active P30
or M34 exception.

## Evidence

M33 P28 survived the full observation window with the 44-module USB/DWC3/TypeC/
PD closure loaded and no runtime gadget setup. M32 failed around the same PMIC/
PON reset window with the P28 module set plus:

- `usb_f_ss_acm.ko`
- configfs ACM gadget creation
- `usb_role=device`
- UDC bind / pullup on `a600000.dwc3`

Therefore the high-value split is the runtime sequence.

The live stock gadget pull in
`docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md` further
corrected the exact sequence: stock creates `ss_acm.0`, writes `UDC=none`,
sets IDs, links the function, then writes `UDC=a600000.dwc3` last. Stock does
not force `usb_role` in init rc. M34 therefore treats `max_speed=high-speed`
and `usb_role=device` as the two explicit off-stock knobs before the final
pullup.

## Proposed Sequence

S0: ACM module only

- Existing artifact: M33 P30
- Load the same module closure as P40/M32, including `usb_f_ss_acm.ko`
- Do not mount/write configfs beyond the existing minimal fs setup
- Do not force role
- Do not bind UDC
- Park for the normal observation window
- If S0 fails, the ACM function module load is the boundary

S1: configfs object creation only

- Start from S0 module closure
- Mount configfs if needed
- Create `/config/usb_gadget/g1`
- Create string/config/function directories and static attributes
- Write `UDC=none`
- Set stock-style IDs (`0x04E8:0x6860`)
- Create/link `functions/ss_acm.0` into the config
- Do not set `g1/max_speed=high-speed`
- Do not force role
- Do not write final `UDC=a600000.dwc3`
- Park after emitting a phase marker
- If S1 fails, configfs/function setup is the boundary

S2: HS-only + role-force knobs, no pullup

- Start from S1 state
- Write `high-speed` to `/config/usb_gadget/g1/max_speed`
- Write `device` to each `/sys/class/usb_role/*/role` candidate
- Do not write final `UDC=a600000.dwc3`
- Park after emitting per-role rc markers
- If S2 fails, one of the two off-stock knobs is the boundary; bisect
  `max_speed` vs role in the next host-only unit

S3: UDC bind / pullup

- Start from S2 state
- Select only `a600000.dwc3`
- Write `a600000.dwc3` to `/config/usb_gadget/g1/UDC`
- Park and observe host USB enumeration and retained evidence
- If S3 fails, UDC pullup is the boundary; then re-enter HS/device runtime
  mitigations before any DTBO phandle surgery

## Safety Shape

All candidates should keep the current recoverable envelope:

- boot partition only
- AP tar contains exactly `boot.img.lz4`
- no DTBO/vendor_boot/recovery/vbmeta/non-boot flash
- no raw host `dd`, fastboot, multidisabler, format data, or EUD write
- no Android/Magisk handoff
- no persistent partition mount
- no reboot syscall or Download beacon in the candidate
- manual Download rollback only after survival proof or helper stop
- Magisk boot-only rollback first; stock boot-only fallback only if Magisk
  rollback fails and Download remains available

## Implementation Notes

The least risky builder shape is to reuse the M33 P30/P40 boot packaging and the
M31B/M33 module-loading skeleton, then add the runtime gadget step functions
from the older M5/M6 ACM sources under explicit stage compile-time switches.

Required static checks for every generated stage:

- required marker includes `S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_<stage>`
- required marker includes the stage name and `runtime_step=<stage>`
- all earlier stages are present and later stages are absent
- S0 contains no `/config`, `usb_gadget`, `ss_acm.0`, `ttyGS0`, or UDC strings
- S1 contains configfs/gadget strings plus `UDC=none`, but no max-speed,
  `/sys/class/usb_role`, or final UDC bind strings
- S2 contains max-speed and role-force strings but no final UDC bind strings
- S3 contains `a600000.dwc3` UDC bind strings
- no candidate contains `LINUX_REBOOT_CMD_RESTART2`

## Next Gate

Run M34 S1 first under a fresh one-shot `AGENTS.md` exception and explicit
operator approval. S2/S3 remain host-only until the previous stage has a live
result.
