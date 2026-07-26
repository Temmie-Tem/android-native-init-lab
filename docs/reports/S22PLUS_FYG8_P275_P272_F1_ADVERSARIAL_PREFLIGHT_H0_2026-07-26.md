# S22+ FYG8 P2.75 P2.72 F1 adversarial preflight

Date: 2026-07-26 KST

Scope: H0 host-only adversarial review. No connected D0, approval, transaction,
Download request, Odin session, transfer, reboot, device contact, or device
write occurred.

Status: superseded before D0 by P2.76. Its ready2 manifest changes only the
observation timeout and preserves the exact APs and execution closure.

## Verdict

`GO_TO_CONNECTED_D0_WITH_PRELIVE_CONDITIONS`

No execution-critical defect was found in the frozen P2.72 candidate line.
This verdict authorizes neither D0 nor F1. F1 remains conditional on one fresh
healthy connected D0, the exact emitted approval token, an attended physical
Download recovery path, and the unchanged manifest-bound closure.

## Findings

### MUST-FIX-1 closed: active contract regression

The focused suite initially returned 261 passes and one failure because
`AGENTS.md` had grown to 227 lines while the active-contract test still enforced
220. The current-live history was reflowed without changing any boundary,
authority, recovery rule, or frozen execution source. `AGENTS.md` is now 219
lines and the existing test passes without weakening its limit.

### MUST-FIX-2 closed: incomplete recovery rehearsal

The P2.73 rehearsal described `--recover` only for the known
`ROLLBACK_FLASHED` inventory deviation. The implementation also safely handles
an interruption after a durable candidate-attempt start:

- candidate transfer is never retried;
- an unknown candidate outcome is normalized conservatively;
- only observation and the exact preapproved rollback can continue;
- `RECOVERY_DOWNLOAD` can consume only the remaining rollback attempt; and
- `ROLLBACK_FLASHED`/`HEALTH_VERIFIED` resume verification without retransmit.

The rehearsal now states these journal/attempt-ledger cases explicitly. It also
records that a pre-candidate Download abort needs physical Android return plus
a fresh D0 health check because the runner does not claim that return-health
step.

## Execution-critical review

- The approval binding includes the exact target evidence, private topology
  continuity receipt, candidate and rollback identities, observation contract,
  runner/core bundle, and execution-source closure.
- Preparation and execution each perform a complete D0. Execution refuses a
  changed target, topology, health baseline, artifact, manifest, or source.
- Candidate and rollback APs are direct regular `.tar.md5` paths. Each is
  SHA/size pinned, parsed as exactly one regular `boot.img.lz4`, held open,
  and path/descriptor identity checked before and after Odin.
- Download selection requires one measured endpoint at the D0-bound physical
  topology with exact Samsung VID/PID/product/manufacturer and absent serial.
- Candidate and rollback attempt-start records are fsynced before Odin.
  Interrupted or ambiguous Odin outcomes are treated as possible sessions.
- Candidate PASS requires completed Odin transfer, exact Download departure,
  exact candidate-bound CDC-ACM identity/banner, released transient guard,
  accepted retained terminal evidence, exact rollback, final Android/root and
  partition health, and all eight canonical events.
- Recovery requires the original binding and durable journal, takes no second
  approval, and has no candidate-transfer path.

## Upstream contract cross-check

- The official [Linux gadget-configfs
  documentation](https://docs.kernel.org/usb/gadget_configfs.html) specifies
  the same ordered contract used by the candidate: mount configfs, create
  gadget/configuration and function objects, link the function into the
  configuration, then bind the composed gadget by writing an exact
  `/sys/class/udc/*` name to `UDC`.
- The [ModemManager udev-tag
  reference](https://www.freedesktop.org/software/ModemManager/api/latest/ModemManager-Common-udev-tags.html)
  defines `ID_MM_DEVICE_IGNORE` as a device-specific request to ignore every
  port exposed by that device. This supports the candidate-exact transient
  guard design; it does not remove the guard lifetime and host-prompt timing
  risks recorded below.

## Host and recovery readiness

- Live `--validate` reopens bundle
  `52e2e95c3d346a1e2936f3ec2a7a7f6efd5e3ed080ceacb7803b250cdca70347`
  and execution closure
  `950992db8cf69d610bfd787acdbea91a04dca11bfc96b01c441d3b06de79a764`.
- Candidate, rollback, and pinned `/usr/bin/odin4` identities match.
- The full FYG8 stock ZIP independently hashes to the exact recovery-policy
  value `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`.
- All historical Process v2 transaction journals are terminal (`CLOSED` or
  `ABORTED`); no stale live process or transient udev guard rule exists.
- The filesystem has about 41 GiB free. `journalctl`, `udevadm`, `lsusb`,
  `pkexec`, `setpriv`, ADB, and Odin are present. Kernel-journal and udev-monitor
  reads work for the operator account.
- ModemManager is active, so the candidate-exact transient udev guard is
  necessary. The KDE polkit agent is present. The operator must answer its
  prompt within the observer's 30-second arm bound; failure is pre-candidate
  and cannot invoke Odin.

## Residual risks and live conditions

1. The known post-rollback USBFS baseline race can still stop the first process
   after durable `ROLLBACK_FLASHED`. Keep the P2.74 sidecar running and use the
   same-run `--recover`; do not repeat candidate or rollback.
2. The transient udev guard has a 300-second lifetime from arm, shorter than
   the sum of all outer runner timeouts. A pathologically slow run can therefore
   produce `guard-lost` and lose host proof after a valid device terminal
   record. Treat that as a host-observer failure, not a candidate failure.
3. The sidecar is diagnostic only. Empty, truncated, or failed sidecar output
   cannot change the F1 verdict or recovery authority.
4. Keep the direct D0-bound cable/topology unchanged and the host awake. Do not
   run another ACM reader, serial terminal, repeated USB poller, or Odin process.
5. The candidate AP is mode `0664`, but every access path crosses private
   `0700` directories and execution rehashes plus pins it. This is not a live
   blocker; do not mutate frozen artifact metadata merely for cosmetic
   hardening.
6. If D0, observer guard arm, Download identity, rollback availability, journal
   consistency, or physical recovery fails, stop before candidate transfer.

## Validation

- Live host-only bundle validation passed with the frozen hashes above.
- Full FYG8 stock recovery evidence SHA passed.
- All 262 focused Process v2, D0, live adapter, evidence, CDC-ACM, sidecar, AP
  transport, Odin transition/USBFS, P2.72 ready-manifest, and docs tests pass
  with `ResourceWarning` promoted to error.
- Tracked diffs contain no private identifier or artifact.
