# Device Action Process v2 D0 Qualification PASS

Date: 2026-07-21 KST

## Verdict

`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`

P2.4 is complete. The reusable Process v2 adapter performed one bounded
connected read-only qualification against the profiled S22+ FYG8 target. It
created no reboot, Download, Odin, partition-transfer, F1, or live authority.

## Implementation

- Adapter:
  `workspace/public/src/scripts/revalidation/device_action_d0_v2.py`
- Adapter SHA256:
  `b856c4711b1fd4e65853723758e15e9baca04e193d214a7c01c8e66b479d7f23`
- Focused tests: `tests/test_device_action_d0_v2.py`
- Test SHA256:
  `4b3672e05dbcbab79b78873a1ffedd1da202075e936626ed24021f5e8ebe68ec`

The adapter reuses the Process v2 H0 bundle validator. Its CLI contains only
`--validate`, `--render-plan`, and `--connected-read-only`. The connected path
uses bounded ADB reads and host USB inventory; it has no transport call or
write-capable command.

## Review And Static Validation

An independent Claude Opus high-effort read-only review returned
`GO_D0_CONNECTED_READ_ONLY`. It found no HIGH issue. The reviewed MEDIUM
bootloader/incremental overconstraint was removed. USB inventory and output
bounds were tightened before device contact.

The focused suite covers target mismatch, partition-hash mismatch, target
change, marker contamination, Download endpoint presence, empty USB inventory,
unsafe observer paths, symlink output, run-directory escape, remote argument
shape, result/raw-observer tampering, and absence of control/transfer CLI paths.

## Connected Evidence

The final run began at `2026-07-20T21:38:34Z`. Private raw evidence is retained only
under `workspace/private/runs/device-action-d0-v2/`; no device serial or raw
device log is committed.

- Exactly one profiled Android target was observed and remained continuous.
- Android boot completed and boot animation stopped.
- Magisk root, orange verified-boot state, expected boot hash, and stock
  supporting-partition hashes passed.
- `/proc/last_kmsg` produced 2,097,136 bytes to EOF in 0.167921 seconds.
- Observer stderr was empty; exact-marker and marker-family counts were zero.
- Host USB inventory contained 16 devices before and after, with zero Samsung
  Download endpoints in both snapshots.
- Strict result reopening passed against the private raw observer.
- Public output and private `result.json` were byte-identical.
- Structured result SHA256:
  `95cb2b2f6ef7cb9fd5df2251353440d29993b13f29c4894b9195c8d8cf9938b2`

Every authority flag was false: device write, reboot request, Download
transition, Odin invocation, partition transfer, F1 authorization, and live
authorization.

## Scope

This result proves that the reusable Process v2 target/profile preflight works
on the real FYG8 device without bespoke policy machinery. It does not authorize
or prove an F1 transfer. P2.5 remains host-only until the reusable F1 adapter
and execution-critical closure pass independent review and receive one fresh
operator approval for the exact binding.
