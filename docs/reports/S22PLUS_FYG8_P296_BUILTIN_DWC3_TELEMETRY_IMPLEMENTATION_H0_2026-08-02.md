# S22+ FYG8 P2.96 built-in DWC3 telemetry implementation (H0)

Date: 2026-08-02

## Outcome

P2.94's candidate identity and Full-LTO pair were not promoted because its
terminal telemetry required `s22_p294_wrapper_vbus_snapshot` from external
`dwc3-msm.ko`, while the boot-only candidate reused stock vendor-ramdisk
modules. P2.96 is the bounded successor that removes that undeliverable input.

The successor retains only `s22_p294_dwc3_state_snapshot`, defined in built-in
`drivers/usb/dwc3/gadget.c` and therefore delivered by `boot.img`. It keeps the
same two-slot value design:

- record A: one of 16 `DSTS.USBLNKST` values;
- terminal record B: one of 132 conditional final states, one of seven
  built-in fixed-predicate mismatch masks, or one of two contradiction values.

No candidate module binary is injected. No external-module symbol is required
by the runtime, trace descriptor, linked audit, or package closure.

## Host closure

The implementation gates:

- enumerate all 32,256 raw built-in snapshot/final-state inputs and compare
  the production C classifier with the Python SoT;
- retain 141 distinct terminal classification values;
- prove record A and terminal B are adjacent with zero intervening publish
  call;
- reject any residual wrapper symbol, trace descriptor, source patch, or
  external-module dependency;
- bind the exact 107-position sequence and its current detail table; and
- require the built-in snapshot symbol in linked `vmlinux`.

The first focused host compile exposed one escaped-newline error in the test
harness. It was a novel pre-session H0 failure, was repaired in the closure
file only, and the corrected focused unit passed. No candidate intent existed
and no device was contacted.

## Scope and authority

P2.96 is a fresh identity. P2.94 files and artifacts remain immutable. The
successor changes no partition boundary, recovery mechanism, F1 runner, or
hazard class. This report is H0 evidence only and grants no D0, D1, or F1
authority.
