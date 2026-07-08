# S22+ M34 Runtime Gadget Split Design

Date: 2026-07-09 KST / 2026-07-08 UTC

## Verdict

2026-07-09 update: S0/P30 has now passed live. The next unit is M34 S1 host
build: configfs gadget/function/config only, no role force and no UDC bind.
No S1 live flash is authorized yet.

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
- Create/link `functions/ss_acm.0` into the config
- Do not force role
- Do not write `UDC`
- Park after emitting a phase marker
- If S1 fails, configfs/function setup is the boundary

S2: role force only

- Start from S1 state
- Write `device` to each `/sys/class/usb_role/*/role` candidate
- Do not write `UDC`
- Park after emitting per-role rc markers
- If S2 fails, role switching is the boundary

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
- S1 contains configfs/gadget strings but no `/sys/class/usb_role` or UDC write
- S2 contains role-force strings but no UDC write
- S3 contains `a600000.dwc3` UDC bind strings
- no candidate contains `LINUX_REBOOT_CMD_RESTART2`

## Next Gate

Run P30 first under a fresh one-shot `AGENTS.md` exception and explicit operator
approval. If P30 survives, build the M34 S1/S2/S3 host-only artifacts and live
them one at a time under separate SHA-pinned exceptions.
