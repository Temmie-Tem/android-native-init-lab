# ML056: UFS link startup at the 60-second floor

ML056 ran the witness-floor variant of the
[UFS V13 route composition](../operations/S22PLUS_MAINLINE_UFS_ROUTE_V1.md#witness-floor-variant),
this time with the floor kernel and module. It closed
**`PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`** (`closed.json` `396220c6…`).

- **The link result repeats ML054's at a fifth of the wait.** One
  `DME_LINK_STARTUP` returned result 0. The controller then reported Device
  Present (HCS `0xf`). The module ran at 62.4 s of guest uptime instead of
  about 308 s.
- **The session took 202 s.** ML054's took 424 s and ML055's took 230 s.
- **No physical action, replug or host recovery step was needed.**

## Run

The operator returned the exact approval for task `f3471114…` (1800 s, one
operation, attended). Readiness passed with zero device controls. The
target-session lease was free. The approved terminal dispatched once. The
operator was present and was asked to perform no action.

| Event (from N launch) | Seconds |
| --- | ---: |
| first authenticated response | 32.38 |
| guest uptime at the first response | 6.967 |
| witness challenge (host gap 55.383 s) | 87.77 |
| witness sealed, guest uptime 62.439 s | 88.20 |
| module permit | 89.88 |
| authenticated result sealed | 91.94 |

Counts: 1 N, 1 original A and 3 controls, with no recovery. Final rooted
Android health passed.

## Link result

| Field | Observation |
| --- | --- |
| Status | `UFS_LINK_COMPLETED`, operation errno 0, normal return |
| Initial preparation | All eleven stage-two conditions PASS; HCE handoff `STOP_COMPLETE`; initial UCCS acknowledged, zero in time |
| Power | 11 records; claimed, triggered and acknowledged `0x7ff`; none reclaimed |
| USB coverage | Covered, released, reason OK, one attempt |
| CFG1 | `0x1c00052c` before and after: `BIT_CLEAR_BUDGET_PASS` |
| Stage and local UniPro commands | Stage 6, PCS ready, 6 local commands |
| Link | Issued once; pre-command HCS `0x8` |
| Link interrupt | `0x404` (UCCS + UIC_ERROR); branch `COMPLETION`, no unexpected bits |
| Command result | 0 |
| Post-command HCS | `0xf`: Device Present, UTRLRDY, UTMRLRDY, UCRDY |
| UIC error codes | PA `0x80000010` (`pa_line_reset`); DL, N, T and DME 0 |

Every field above equals ML054's. ML054 ran the 300-second witness, kernel
and module ([run](S22PLUS_MAINLINE_ML054_UFS_ROUTE_RUN_2026-11-27.md)).

## What changed from ML055

ML055 used the floor witness with the V13 kernel and module. The module
refused below 300 s
([run](S22PLUS_MAINLINE_ML055_UFS_FLOOR_RUN_2026-11-27.md)). v71
(`276462cd0c`) adopted the floor kernel and module. Each is a rebuild whose
only source change sets one boot-time comparison to 60 s instead of 300 s:
- the RPMh transport authority (`g0q_rpmh_begin`), in the kernel;
- the module's `start()`.

The disassembly of each binary differs only in the immediate `300e9−1` →
`60e9−1`, with equal instruction counts. Capability-4 and its candidate
passed owner review.

## Claims

A completed run can claim:
- a second completed mainline UFS link startup with Device Present, now at
  62 s of guest uptime;
- the same link result as ML054 in every reported field;
- an authenticated USB first response with no physical action.

It does not claim:
- stability: these are two boots, at two dwell lengths;
- anything beyond link startup: no media command, LU discovery, partition or
  filesystem access is in scope;
- recovery from a hung kernel.

## Next

Step 1 of the operator's roadmap (a shorter wait) is complete. Step 2 is UFS
read/write and persistence across a reboot. It needs a new design (media
commands, LU access and a fixed test block), a common-contract change and
the operator's approval.
