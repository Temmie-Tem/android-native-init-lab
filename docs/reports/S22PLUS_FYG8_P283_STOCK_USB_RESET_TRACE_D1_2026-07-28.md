# S22+ FYG8 P2.83 stock USB reset trace D1

Date: 2026-07-28 KST

Scope: one approved transient no-payload D1 on the rooted FYG8 stock Android
boot. No reboot, Download transition, Odin session, payload, partition write,
EUD write, UART action, driver unbind, or persistent setting change occurred.

## Verdict

`NO_TRACE_ACTION; CLEANUP_AND_HEALTH_PASS`

The stock modules and kprobe substrate are a valid positive-control basis, but
Android's `svc usb resetUsbGadget` did not produce an observable USB reset on
this target. Its zero return code is not evidence of a physical or kernel USB
transition.

## D0 preconditions

- exactly one attached `SM-S906N`, `g0q`, FYG8 Android target;
- root UID `0`;
- tracefs mounted and `kprobe_events` readable;
- all seven requested symbols present exactly once;
- `/sys/module/eud/parameters/enable` read `0`;
- parent `a600000.ssusb` and child `a600000.dwc3` runtime status read
  `active`;
- stock `dwc3-msm.ko` SHA256 matched the P2.82 contract; and
- stock `phy-msm-snps-hs.ko` SHA256 matched the P2.82 contract.

The EUD-enable early-return hypothesis is therefore ruled out for this stock
state. The two matching module identities make their call ordering a useful
known-good comparison, but the rebuilt core kernel and bare-PID1 call context
remain different.

## Exact D1

The run created one isolated `p283stock` tracefs instance with a 64-KiB
per-CPU buffer and `global` trace clock. It registered 18 entry/return events
over:

- parent and child runtime suspend/resume;
- femto-HS PHY init, suspend, and connect notification; and
- DWC3 gadget pull-up and run-stop.

Registration readback was `18/18`. The run then invoked exactly one
`svc usb resetUsbGadget`, waited for bounded re-enumeration, captured the
instance trace and host kernel/udev sidecars, removed every event and the
instance, and rechecked Android/root health.

## Result

- `resetUsbGadget` returned zero;
- ADB disappearance was not observed;
- no host USB/udev transition was observed;
- the trace contained zero events;
- the UDC remained `configured` at `super-speed`;
- all 18 events and the trace instance were removed; and
- Android boot-complete, stopped boot animation, root, model, and FYG8
  identity checks passed.

No event in this run may be read as a missing function call because the
requested reset produced no observable transition. The later physical
reconnect positive control proved that `msm_hsphy_init` can run post-boot from
the child runtime-resume path; its absence here is therefore solely another
sign that `resetUsbGadget` did not exercise that path.

Raw trace and host sidecars remain under
`workspace/private/outputs/s22plus_fyg8_p283_stock_trace_d1_v1/`.

## Next

The next valid positive-control unit is a separately approved, attended
physical cable disconnect/reconnect while the same bounded trace is armed.
That unit can compare suspend, connect-notify, PM, pull-up, and run-stop
ordering. Driver unbind/rebind is not justified.
