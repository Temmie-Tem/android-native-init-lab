# S22+ FYG8 R4W1-C Pre-Consumption Endpoint Arrival Race

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

## Result

Two separately acknowledged live invocations failed closed before one-shot
consumption and before candidate transfer:

| Attempt | Run | Result SHA256 | Error |
| --- | --- | --- | --- |
| 1 | `workspace/private/runs/s22plus-r4w1c-live-20260719T202244Z` | `8dc81ea6157c2c0e4287164776ab1093529460c087b75d0161909581088755d7` | `Odin endpoint changed during enumeration: /dev/bus/usb/002/011` |
| 2 | `workspace/private/runs/s22plus-r4w1c-live-20260719T202817Z` | `f58b5dd92d5d999f9901f1c2464c08f1810e8a3fb319ca2805f05394d0654f4f` | `Odin endpoint changed during enumeration: /dev/bus/usb/002/014` |

Both verdicts were
`FAIL_R4W1C_PRECONSUMPTION_NO_CANDIDATE_FLASH`. Both results record
`candidate_transfer_attempted=false` and `candidate_transfer_ok=false`; each
timeline contains only `live_session_start` and `live_session_end`. The durable
candidate-consumed state remains absent.

Therefore:

- candidate AP transfers: `0`;
- Magisk or stock AP transfers: `0`;
- partition writes: `0`;
- candidate executions: `0`;
- one-shot consumption: `false`.

## Root Cause

`enumerate_odin()` inventories `/dev/bus/usb` identities before invoking the
bounded `odin4 -l`, then post-stats every path reported by Odin. On both runs,
the normal Download endpoint appeared during that invocation. The pre-call
inventory therefore had no identity for the path while the post-call stat found
a live character node. The safety core correctly refused to classify an
unstable snapshot, but `wait_for_single_live_endpoint()` propagated this normal
arrival edge as fatal instead of waiting for one stable expected-device sample.

The safety distinction is load-bearing:

- a node absent before enumeration and present afterward may be the expected
  Download device arriving normally and can be retried only before consumption;
- a node present before enumeration whose inode, device identity, or ctime
  changes remains a replacement race and must stay fatal;
- any wrong topology, serial digest, multiple endpoint, stale endpoint, or
  repeated instability remains fatal.

## Recovery

After each failure the device remained in normal Samsung Download. The operator
physically exited Download. Final read-only verification after the second exit
proved:

- Android serial `RFCT519XWGK`, completed boot, and stopped boot animation;
- Magisk `uid=0(root)`;
- boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- vendor_boot SHA256
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`;
- DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- recovery SHA256
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- no Odin endpoint and no candidate-consumed state.

## Decision

Fails-twice-stop applies. The exact live helper and ACTIVE rendering used by
these attempts are retired and must not be invoked again. The connected PASS
remains valid because neither connected source nor its evidence changed.

The replacement is host-only until all gates close: add a finite
expected-topology/serial Download-node stabilization step before ticketed Odin
enumeration, keep replacement and ambiguity fatal, add adversarial tests, rerun
the complete artifact and regression gates, obtain independent review, and bind
a newly rendered one-shot policy in a separate commit. This report authorizes no
device contact or live action.
