# S22+ FYG8 P2.94 module-delivery static stop (H0)

Date: 2026-08-02

## Outcome

P2.94 remains host-only and is not eligible for a ready manifest, D0, or F1.
The preserved Full-LTO A/B Image pair is valid, but the intended telemetry
closure is not deliverable by the selected boot-only package.

The corrected formal replay reached the linked-symbol audit and stopped with:

`required linked symbol missing: s22_p294_wrapper_vbus_snapshot`

No package, promotion, manifest, connected command, Odin invocation, or device
session followed.

## Attribution

The P2.94 patch adds two telemetry functions to different build products:

- `s22_p294_dwc3_state_snapshot` is in the built-in DWC3 gadget code and is
  present in the linked `vmlinux`;
- `s22_p294_wrapper_vbus_snapshot` is in `dwc3-msm-core.c`, whose output is the
  external `dwc3-msm.ko` module, and is absent from linked `vmlinux`.

The candidate builder replaces the boot Image and userspace ramdisk while its
module closure explicitly records `module_binaries_injected: 0` and
`vendor_ramdisk_modules_reused: true`. The stock FYG8 `dwc3-msm.ko` contains no
P2.94 wrapper symbol. The Full-LTO build receipts recorded a generated module,
but the module is neither a preserved reproducibility artifact nor a permitted
boot-only package input.

The runtime trace descriptor requires the missing wrapper probe, and the final
telemetry classifier requires both `dwc3_seen` and `wrapper_seen`. Relaxing the
formal verifier would therefore permit a candidate that cannot produce the
intended terminal telemetry result.

## Re-entry repair retained

Before this delivery stop, the bounded host-only re-entry repair was completed:

- the frozen P2.94 qualification replays linked-audit and test receipts from
  their recorded bytes;
- current linked-audit, observer, and Process-v2 documentation-test deltas are
  exact-receipt-bound;
- the actual Full-LTO provenance passes the focused formal-verifier replay;
- candidate identity remains `103/103` with `CHANGED_KEYS=[]`.

The corrected formal result is preserved under `workspace/private/`. It is not
device authority.

## Required successor

A successor must keep all required telemetry inside the boot-only delivery
closure. The smallest viable direction is to retain the built-in DWC3 snapshot
and either remove the module-only VBUS snapshot requirement or derive the
needed fact from an already shipped stock-module probe. That is a Tier-1
change, so it requires a new intent and Full-LTO qualification. Non-boot module
delivery is not an available workaround under the permanent boundaries.
