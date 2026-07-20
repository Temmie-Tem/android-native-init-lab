# S22+ FYG8 R4W1-C2 Measured Live Source Host GO

Date: 2026-07-21 KST

## Verdict

`SOURCE_HOST_GO_POLICY_INACTIVE`

The target-specific R4W1-C2 helper is ready for independent adversarial review
and a separate policy-binding commit. This report grants no device contact,
reboot, Download transition, Odin transfer, flash, or recovery authority.

## Scope

- New inert live helper:
  `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c2_measured_live_gate.py`
  size `109425`, SHA256
  `1454cb422b24a895df965d2e7838aaf9614381c3bde41bef64bd570cf970292f`.
- Focused test: size `87770`, SHA256
  `acdf862bb0433b7efcb9dfde834ec10bba735d0356e87ecb5f1342b5201557b0`.
- Inert policy template: size `13701`, SHA256
  `710481ab970133232570baaf2aab9bcef73d82c217fb155a06feb3cbdd4d3d45`.
- Host-only binding helper: size `12169`, SHA256
  `c3dc2c27060f2578daa4f9165949e100320d887d255fb6041f4f87070f277a37`.
- Binding helper test: size `7305`, SHA256
  `9535992ee5637bbe5268f62fc43e7946af2280d7f74ba053eb838bfbcbcdd761`.

## Behavior

The helper preserves the retired R4W1-C transaction, sealed-input, one-shot
consumption, mandatory Magisk-first rollback, recovery, timeline, observer, and
fail-closed state machine under a new R4W1-C2 namespace. It changes endpoint
authority to the explicit `measured_usbfs_observer` for candidate arrival,
pre-transfer ticket revalidation, candidate disappearance, rollback arrival,
and final Odin absence.

The target sysfs topology, Samsung descriptors, absent Download serial, usbfs
major/minor relation, and immutable ticket digest must agree immediately before
each sealed Odin launch. Only atime, ctime, and mtime may vary across `odin4 -l`;
all other node identity fields, birth time, and complete inventory membership
remain fatal on change. `/usr/lib/cargo/bin/coreutils/stat` is exact-path, size,
and SHA-pinned.

The historical R4W1-C connected PASS is reopened as evidence. Current candidate,
rollback, firmware, static result, and Odin identities are independently
rechecked before device contact and immediately before one-shot consumption.

## Validation

- Related focused suite: `141/141` PASS.
- R4W1-C2 focused live helper: `59/59` PASS.
- R4W1-C2 binding helper: `7/7` PASS.
- Common transition and usbfs identity suites: `75/75` PASS.
- Exact historical R4W1-C Odin evidence reconstruction: byte-shape equality
  PASS after fixing the v1 summary compatibility regression.
- Actual source check verdict:
  `PASS_R4W1C2_MEASURED_SOURCE_PACKET_HOST_ONLY`.
- Actual offline live gate verdict:
  `PASS_R4W1C2_LIVE_GATE_OFFLINE_CHECK`.
- Rendered private clause: size `13442`, SHA256
  `6f0f047172f9eb4301d0551986bd3270c2767808546047c9f302782f5c478f8f`.
- Binding packet: size `6030`, SHA256
  `ab3a08b387f55fb2c9d23cbf3a5841c8a2d0d361b776e171cf3944d41ffa107f`.
- `py_compile` and `git diff --check`: PASS.

No device, USB endpoint, ADB, reboot, Download transition, Odin execution,
transfer, flash, candidate consumption, policy activation, or retired-token
reuse occurred.

## Next Gate

Run independent adversarial review against the committed source and exact
rendered clause. Only an explicit GO may be followed by a separate exact
`AGENTS.md` activation commit and post-activation validation. A fresh exact live
acknowledgement remains mandatory after activation.
