# S22+ FYG8 P2.94 host USB visibility sidecar H0

Date: 2026-08-01 KST

Scope: host-only inventory, downstream Process-v2 registration, and reuse of
an existing passive host observer. No connected read, device command, Download
transition, Odin invocation, transfer, reboot, D0, D1, or F1 occurred.

## Result

P2.92 cannot be retrospectively classified as "no USB device appeared" versus
"a USB device appeared with an unexpected interface". Its live directory has
the exact candidate ACM observer and Odin endpoint snapshots, but no generic
candidate-window kernel, udev, or lsusb capture. P2.74 created such a sidecar,
but its preserved artifact is a synthetic dry run; it was not running during
P2.92. Older generic USB logs belong to different candidates and do not prove
the P2.92 electrical/session state.

The next P2.94 F1 will therefore run the already reviewed passive sidecar:

`workspace/public/src/scripts/revalidation/device_action_usb_trace_sidecar_v1.py`

It records private, bounded host evidence across the complete attended
transaction:

- host kernel USB messages from `journalctl --dmesg --follow`;
- kernel and udev events for USB and tty;
- `lsusb` snapshots at the start and end; and
- UTC receive timestamps that can be intersected with the canonical F1
  candidate-flash and candidate-observation events.

The sidecar does not open ACM, invoke ADB or Odin, change a device, or alter the
canonical F1 verdict. Download and rollback events remain in the raw private
log; public interpretation must isolate the candidate window by the canonical
timeline and redact serials and topology.

## Why the existing sidecar is reused

A new runner-integrated udev-only sidecar was prototyped and passed host tests,
but was discarded before commit. It duplicated P2.74, omitted the requested
kernel and lsusb views, and would have changed the F1 runner solely to add a
diagnostic that is already safe as a parallel H0 observer. Reusing the existing
sidecar keeps the runner, manifest schema, recovery state machine, transport,
and candidate bytes unchanged.

## P2.94 branch coverage

The P2.94 retained pair and the passive host log are complementary:

- USBLNKST Reset/On plus a host device event means the host saw the device and
  the next problem is descriptor/configuration negotiation.
- Early Suspend/L2 plus a host event localizes the failure to control-transfer
  response or timing.
- Disconnected plus no candidate-window host device event supports the
  never-observed branch. P2.94's terminal tuple still reports UDC state/speed,
  COREIDLE, and SUSPHY, so the next action can distinguish another digital
  mismatch from an analog/PHY/regulator investigation.
- Nominal digital fields plus no host event exhaust this checkpoint channel for
  the missing physical signal; the next unit must use a different observation
  tool rather than add more position markers.

Regulator sysfs reads are deliberately not added to P2.94. They would change a
Tier-1 runtime source after Full-LTO, create another unbounded read boundary,
and still would not measure physical D+/D- voltage.

## Downstream registration

P2.94 now has versioned offline-promotion and ready-manifest adapters. The
typed evidence layer selects the P2.94 decoder and stock closure, and the
Process-v2 source receipt closure binds all 103 Tier-1, 66 Tier-2, and three
Tier-3 receipts. This changes no candidate source or boot artifact.

Exact candidate-contract verification passes for run
`dd20b502d5e45480b9f89c9b5e2232a2`. Current source receipts compare against
the immutable intent as:

```text
SOURCE_KEYS=103 CURRENT=103 RECORDED=103 CHANGED_KEYS=[]
```

## Validation

- The preserved P2.74 sidecar dry run is complete, bounded, non-authoritative,
  contains kernel and udev receipts plus both lsusb snapshots, and reports no
  capture error or truncation.
- A fresh 2026-08-01 actual-tool rehearsal also completes by its 0.5-second
  bound. Installed journalctl and udev capture processes return zero, neither
  truncates nor reports an error, and both current lsusb snapshots are durably
  receipted under private storage.
- Its five focused tests pass with `ResourceWarning` promoted to error.
- P2.94 candidate-contract verification passes.
- P2.94 telemetry closure, Stage-C receipt routing, ready-manifest derivation,
  Process-v2 core/evidence regression, and Tier-2 reentry focused tests pass.
- The final combined focused suite passes 119 tests.
- `py_compile` and `git diff --check` pass for the final touched closure.

Verdict: `PASS_P294_HOST_USB_VISIBILITY_SIDECAR_REUSE_H0`.

No formal static closure, promotion, ready manifest, connected D0, F1 approval
binding, or live action is performed by this unit.
