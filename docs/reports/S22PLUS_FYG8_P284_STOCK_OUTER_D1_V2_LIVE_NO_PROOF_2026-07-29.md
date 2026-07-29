# S22+ FYG8 P2.84 stock outer-work D1 v2 live no-proof

Date: 2026-07-29 KST

Scope: one approved stock-Android D1 under
`DEVICE-ACTION-D1-P284-STOCK-OUTER-V2-APPROVE:0766047f20233f9462aeac490d81c7e413e25fb3`.
No payload, partition action, F1 action, candidate replay, or P2.84 rebuild
occurred.

## Verdict

`NO_PROOF_CONTROL_OUTER_RETURNED_BEFORE_REACTOR_READY_RUNNER_CLASSIFIER_AND_COMM_ENCODING_DEFECTS_CLEANUP_HEALTH_PASS`

The actual trace rejects the runner's internal
`CONTROL_OUTER_RETURN_TIMEOUT`. The stop-side outer work and every instrumented
parent-suspend boundary returned in milliseconds. The userspace reactor did not
observe child suspend until after the relevant outer returns, so the exact
challenge result is:

`CONTROL_OUTER_RETURNED_BEFORE_REACTOR_READY`

Challenge was therefore forbidden and was not attempted. This is a useful
stock control observation but does not clear the bare-PID1 context.

## Authority and exact action counts

The approval is consumed and closed.

- volatile `service.adb.tcp.port=5555` sets: 1;
- `adbd` restarts: 1;
- trace setups: 1;
- control attempts: 1;
- NONE writes: 1;
- PERIPHERAL restoration writes: 1;
- challenge attempts: 0;
- watchdog arms: 2;
- watchdog fires: 0;
- normal cleanup reboots: 1; and
- hardware restarts: 0.

No same-approval retry is permitted. No D1 or F1 authority remains.

## Preflight and TCP transport

Immediately before mutation:

- HEAD was exactly `0766047f20233f9462aeac490d81c7e413e25fb3`;
- tracked status was clean;
- all 60 frozen P2.84 source receipts matched;
- the private runner SHA256 was
  `8c653b7612e46c694f83c63c67266735d4a9eb02fcf89ad21ad0f3b663f8c001`;
- exactly one USB target matched the private FYG8 identity;
- Android, root, parent/child USB runtime state, EUD, and both module hashes
  passed;
- all eight required symbols had cardinality one;
- tracefs had no `p284stock` object; and
- one global Wi-Fi address was host-reachable while all TCP ADB properties were
  unset.

The approved volatile property set and one `adbd` restart succeeded. TCP
connected within the bound and its private target fingerprint, model, device,
build, and root identity matched the pre-restart USB target.

The first host classifier additionally demanded that USB had already
re-advertised at the exact TCP verification instant. It saw one transport and
reported a generic failure even though every documented identity predicate
passed. A read-only check shortly afterward found both transports. No property
or restart was retried. This extra simultaneous-endpoint predicate was not part
of the approved identity contract and is not retained as a gate.

## Trace setup

All 27 definitions registered. Kernel readback contained 19 `p:` entries and
eight normalized `r16:` entries. The permanent live readback audit verified
exact event name, probe kind, module, symbol, and offset with zero issues.

The instance used the exact `mono` clock and 128-KiB buffer. The final control
trace contains 83 entries.

## What the trace actually proves

The first control NONE sequence measured:

| Boundary | Time |
| --- | ---: |
| NONE `mode_store` entry to return | `0.091 ms` |
| stop helper entry to return | `0.087 ms` |
| stop-helper return to first outer return | `0.020 ms` |
| NONE `mode_store` entry to first outer return | `0.264 ms` |
| NONE `mode_store` entry to child-suspend return | `16.653 ms` |
| NONE `mode_store` entry to parent-suspend return | `19.504 ms` |

The trace contains six `dwc3_otg_sm_work` entries and six returns. Both
observed parent-suspend passes reached every completion marker:

- mutex acquired;
- perf cancellation done;
- prepare done;
- PWR event IRQ disabled;
- HS PHY done;
- SS PHY done;
- clocks done;
- GDSC done;
- bus vote done;
- wake-IRQ block done or skipped;
- mutex released;
- parent suspend return; and
- parent runtime-suspend return.

The two lane-owned `mode_store` calls used the expected PID, and no third
`mode_store` entry occurred. The trace-visible comm contract itself failed,
however, as described below.

## Why the runner reported a false timeout

Three independent runner defects make its internal control verdict
non-authoritative.

### 1. Wrong instance-trace event spelling

`poll_outer_return()` searched for:

```text
p284stock:outer_sm_work_out:
```

The actual trace instance renders:

```text
outer_sm_work_out:
```

Six returns were present, but the polling expression could match none of them.

### 2. Watchdog disarm waited for the full sleep

Both role writes returned promptly in trace, yet each
`disarm_watchdog()` completed only after approximately 20 seconds. The pending
watchdog sleep was not promptly terminated before `wait`.

For NONE, the trace shows `mode_store` return followed by the runner's
`CONTROL_NONE_RETURN` marker `20,137.274 ms` later. This artificial delay moved
the first child-suspended observation behind every relevant outer return.

The later false outer-timeout interval consumed `20,926.371 ms`, not the
intended 15-second classifier bound.

### 3. Newline-bearing comm write

The runner used newline-emitting `print` when writing `/proc/self/comm`.
Trace headers consequently split `p284-lane` and the PID across lines. All
lane-owned PIDs matched, but the promised exact trace-visible comm/PID pair was
not machine-parseable under the frozen representation. The comm identity gate
therefore does not pass.

These are observer/runner defects. They do not show a DWC3 parent wedge.

## Challenge decision

Even without the watchdog delay, the first outer return occurred at
`0.264 ms`, while child suspend itself did not return until `16.653 ms`.
Userspace cannot react to the required suspended read before the outer return.

Therefore `W = To - Ts` is negative and the selected result is
`CONTROL_OUTER_RETURNED_BEFORE_REACTOR_READY`. Challenge execution would have
violated the quantitative gate. It remained at zero attempts.

## Cleanup, reboot, and health

Before reboot:

- all 27 trace events were removed;
- the trace instance was absent;
- parent mode was `peripheral`;
- parent and child runtime status were `active`;
- the volatile service port was still exactly `5555`; and
- persistent/listen-address properties remained unset.

The host durably recorded `normal_reboot_issued=host-cleanup` and issued one
normal reboot. No watchdog or hardware fallback fired. The operator confirmed
the Samsung boot splash and normal Android boot.

Final D0 proved:

- the exact private target identity;
- FYG8 Android boot complete and boot animation stopped;
- root UID 0;
- parent `peripheral`, parent runtime `active`, and child runtime `active`;
- both exact live module hashes;
- no `p284stock` event or instance;
- all three TCP ADB properties unset;
- the temporary eight-file device run directory absent; and
- the host TCP endpoint disconnected.

## Next bounded unit

H0 only:

1. parse the actual instance-trace spelling and replay this exact trace as a
   fixture;
2. make watchdog disarm terminate promptly and test measured disarm latency;
3. write `/proc/self/comm` without a newline and mechanically test the actual
   trace header;
4. remove the unapproved simultaneous USB/TCP endpoint-count assumption; and
5. rerun static and detached-lifecycle validation.

Do not request another D1 until all four execution defects are corrected and
the revised closure has a new commit and fresh approval. The present stock
result neither proves the P2.84 wedge mechanism nor clears bare PID1.
