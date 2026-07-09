# V3408 S22+ O1.1 Live Gate Ready

## Result

`PASS` for host-side live-gate preparation. No candidate flash occurred in this
unit. The operator explicitly approved one attended O1.1 boot-only live run, and
the fresh SHA-pinned exception is active in `AGENTS.md`.

## Candidate

- Target: `SM-S906N/g0q/S906NKSS7FYG8`
- AP.tar.md5 SHA256:
  `c43eeb83cedb2db3e0758de71050ef2960765740face7378fcc285a5b8188730`
- Padded boot SHA256:
  `1e59b172edda0d2c717a93021c9084af1393c0c4db7d28eeb10e06c0b1787b0d`
- `boot.img.lz4` SHA256:
  `afef7ff56c7efd54cbb094b1a36bc8068cb3c780ccc8e2667baee9493c6ca6e6`
- AP members: exactly `boot.img.lz4`
- Behavioral delta from O1: exactly `seclabel u:r:magisk:s0`
- Kernel, Magisk `/init`, service wrapper, O0 daemon, stock first-stage loader,
  stock gadget behavior, protocol, and timeouts remain pinned and unchanged.

## Rollback

- Primary Magisk boot-only AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- Stock boot-only fallback AP SHA256:
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
- Known-booting Magisk boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Rollback is mandatory after candidate PASS or FAIL. The stock AP remains a
fallback only if the Magisk rollback transfer fails while Download mode is
still available.

## Harness Changes

The checked helper is
`workspace/public/src/scripts/revalidation/s22plus_o11_stock_first_stage_control_live_gate.py`.
It adds these fail-closed gates over the consumed O1 helper:

1. It verifies the O1.1 manifest, source files, exact AP/boot/lz4 identities,
   active policy exception, both rollback APs, current Android/Magisk baseline,
   boot hash, stock `DR-daemon` tty ownership, single ACM target, and absence of
   a concurrent Odin endpoint.
2. A failed `adb reboot download` is retried at most once and only after the
   same Android target is reachable. An already observed single Odin endpoint
   counts as accepted transition and suppresses a duplicate request.
3. Before opening the host tty, candidate readiness must prove the O1.1 boot
   hash, service state, volatile `phase=daemon-running`, and complete stock tty
   ownership handoff.
4. PASS requires 128/128 framed payload equality, sequence continuity, host tty
   close/reopen at sequence 64, final volatile result, and restored stock tty
   ownership.
5. After rollback, the helper automatically collects `/sys/fs/pstore` and
   `/proc/last_kmsg`, then checks Android/root stability and stock tty ownership.
6. `timeline.json` retains the canonical eight required live phases.

## Validation

Combined O0/O1/O1.1 tests:

```text
Ran 39 tests in 0.196s
OK
```

Python compilation and `git diff --check` passed. The post-change offline gate
passed at:

```text
workspace/private/runs/s22plus_o11_stock_first_stage_control_live_gate_20260709T193430Z
```

The device was already in Download mode before this unit's connected check.
Odin `--reboot` with no payload returned it to Android without a partition
write. Android boot completion, Magisk root, FYG8 identity, exact known-booting
boot SHA, and running stock `DR-daemon` were then confirmed. Connected dry-run
passed at:

```text
workspace/private/runs/s22plus_o11_stock_first_stage_control_live_gate_20260709T193436Z
```

The dry-run performed no reboot, flash, service handoff, gadget change, module
insertion, configfs/sysfs write, persistent mount, or block write.

## Live Command

The single approved live run is gated by both acknowledgements:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_o11_stock_first_stage_control_live_gate.py \
  --live \
  --ack S22PLUS-O11-SECLABEL-CONTROL-LIVE-GATE \
  --rollback-ack S22PLUS-O11-SECLABEL-CONTROL-ROLLBACK
```

The exception is consumed when `candidate_flash_start` is recorded. Any missing
protocol/status evidence remains FAIL; it cannot be inferred from boot survival
or source intent.
