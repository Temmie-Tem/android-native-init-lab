# S22+ FYG8 P2.73 freeze, rehearsal, and rollback deviation analysis

Date: 2026-07-26 KST

Scope: H0 host-only. No D0, approval, transaction, Download request, Odin
session, transfer, reboot, device contact, or device write occurred.

## Freeze

The P2.72 execution line is frozen through the next attended transaction:

- ready manifest;
- candidate and rollback APs;
- three offline observation-contract artifacts;
- candidate source contract, runtime, decoder, and checker closure;
- Process v2 core and live adapter;
- D0 adapter, CDC-ACM observer, Odin transition core, USBFS identity code, and
  regular-path transport.

No source-bound or execution-closure change is permitted during this interval.
If a candidate defect is found, the F1 run is postponed. It is not repaired,
rebuilt, or re-promoted under time pressure.

The unchanged live adapter reopened the complete bundle:

- verdict: `PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY`;
- bundle SHA256:
  `52e2e95c3d346a1e2936f3ec2a7a7f6efd5e3ed080ceacb7803b250cdca70347`;
- execution-closure SHA256:
  `950992db8cf69d610bfd787acdbea91a04dca11bfc96b01c441d3b06de79a764`;
- manifest status: `ready-for-f1-approval`;
- `prepare_is_d0_only=true`;
- `execute_requires_fresh_exact_approval=true`;
- `rollback_preapproved=true`;
- `recover_can_transfer_candidate=false`; and
- all device/write/authorization flags are false.

The private receipts are under:

`workspace/private/outputs/s22plus_fyg8_p273_freeze_rehearsal/`

## Exact rehearsal

Run from the repository root. These variables prevent path substitutions:

```bash
MANIFEST=workspace/public/src/device-action/manifests/s22plus_fyg8_p270_process_v2_ready_1.json
LIVE=workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py
```

The candidate AP is exactly:

`workspace/private/outputs/s22plus_fyg8_p260_v6/candidate-a/odin4/AP.tar.md5`

The rollback AP is exactly:

`workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5`

The manifest pins both hashes and sizes. Do not substitute
`candidate-a/AP.tar.md5`, `candidate-b`, a symlink, or another rollback.

### 1. Host reopen

Already passed:

```bash
PYTHONPYCACHEPREFIX=/tmp/p270_f1 python3 "$LIVE" --validate --manifest "$MANIFEST"
```

The expected bundle hash is the frozen value above.

### 2. Connected D0

With one healthy attended FYG8 target connected:

```bash
PYTHONPYCACHEPREFIX=/tmp/p270_f1 python3 "$LIVE" --prepare --manifest "$MANIFEST"
```

Do not pre-create or hand-name the run directory. Preserve the emitted
`run_dir` and `approval_token` verbatim. `--prepare` is read-only D0 and grants
no F1 authority.

### 3. Fresh approval and execute

Only after D0 passes, the operator returns the exact emitted approval token.
Use the exact values without reconstruction:

```bash
PYTHONPYCACHEPREFIX=/tmp/p270_f1 python3 "$LIVE" --execute --manifest "$MANIFEST" --run-dir "$RUN_DIR" --approval "$APPROVAL"
```

`--execute` is invoked at most once for this prepared binding. Once candidate
execution starts, rollback is already authorized.

### 4. Recovery branch

If execution stops after the journal has durably reached
`ROLLBACK_FLASHED`, do not repeat `--execute`, the candidate, or rollback.
Resume only from the same run directory:

```bash
PYTHONPYCACHEPREFIX=/tmp/p270_f1 python3 "$LIVE" --recover --manifest "$MANIFEST" --run-dir "$RUN_DIR"
```

Recovery takes no second approval and cannot transfer the candidate. A
different unexplained failure or an earlier journal state is a stop, not a
license to force this branch.

## Repeated rollback deviation

P2.57 and P2.67 have the same durable shape:

1. rollback Odin transfer returns `odin_transfer_completed`;
2. the journal reaches `ROLLBACK_FLASHED` and records
   `rollback_flash_done`;
3. the initial process exits with
   `measured USB endpoint inventory failed`;
4. no post-rollback absence snapshot is written by that process;
5. later `--recover` reopens `ROLLBACK_FLASHED`, observes Android, performs
   final health and retained reads, and closes without retransmission.

The outer error has one source: the initial
`MeasuredUsbfsIdentityObserver.inventory()` call inside `enumerate_odin()`,
before `odin4 -l` and before a snapshot receipt. The final absence poll passes
`allow_live_departure=true`, but that only handles a departure after a
complete baseline inventory. It does not catch a USBFS node disappearing while
the baseline itself is being scanned.

Both retained run histories show the live Download node before rollback and a
different Android USB node after recovery. The failed call sits exactly in
that re-enumeration interval. A focused host reproduction also proves that one
baseline `UsbfsIdentityError` terminates the absence poll after one observer
call even when the existing deadline could permit another poll.

Therefore the strongest supported diagnosis is:

`STRONGLY_LOCALIZED`: Download-to-Android USBFS membership churn races the
baseline inventory scan, and the absence poll lacks a bounded retry for that
pre-snapshot race.

The exact inner exception was not persisted, so the narrower class
(`ENOENT`, birth-time read failure, or before/after stat change) remains
`UNRESOLVED`. This is not a candidate, rollback-transfer, or final-health
failure.

No bound code is changed before the attended transaction. The operational
response to the same exact post-`ROLLBACK_FLASHED` error is the tested recovery
branch above.

After the transaction closes, the smallest code unit is:

- introduce a typed baseline-snapshot race for node disappearance/change;
- retry only that class in `wait_for_no_live_endpoint()` when
  `allow_live_departure=true`, within the existing deadline;
- keep malformed nodes, permission failures, replacements, unrelated arrivals,
  and all default callers fail-closed; and
- add exact-departure, replacement, unrelated-arrival, persistent-failure, and
  bounded-retry tests.

## E4 sketch

E4 remains separate and is not implemented before E3 live proof. Its smallest
contract preserves the E3 banner and then performs one exchange:

- host request: `S22E4Q:<32 lowercase nonce hex>\n` (40 bytes);
- device response:
  `S22E4R:<32 run-id hex>:<32 nonce hex>\n` (73 bytes);
- one host-generated 128-bit nonce, stored only in private run evidence;
- one bounded exact read and one bounded exact write;
- malformed, duplicate, truncated, extra, or timed-out input records failure
  and parks;
- no shell, command dispatcher, NCM, networking, Debian, or persistent state.

The generic dummy-HCD QEMU harness can prove framing, exact lengths,
malformation rejection, timeout, and response matching. A later F1 remains
necessary for physical DWC3/CDC-ACM bidirectional proof.
