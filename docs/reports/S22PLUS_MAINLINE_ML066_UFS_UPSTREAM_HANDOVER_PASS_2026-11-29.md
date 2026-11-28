# ML066: the upstream UFS driver stack takes the controller, read-only (roadmap step 4b)

One attended run, under one returned single-run approval, of the
[4b](S22PLUS_MAINLINE_UFS_UPSTREAM_4B_H0_2026-11-28.md) composite module
(report V18). Capability-11 (`241c4543…`), candidate a (qualified image
`09981057…`), chained to ML065's closure.

```
APPROVE S22PLUS MAINLINE RAM V1 7d160500299e6173252775e22d39599d9a77df1a8e5514b9790262fb57d4a1fe 1800s 1operation attended
```

**Result: `PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`** (closure
`64ece946…`). The run needed no physical action, replug or recovery. Counts:
1 N transfer, 1 original A transfer, 3 controls.

## Handover

The pinned 7.2.11 `ufshcd` core, `ufs-qcom` and QMP UFS PHY drivers, loaded
as one gated module against the unchanged floor Image, took over the
controller. They brought the device up and read it back.

| Field | Value |
| --- | --- |
| Report | `V18_UPSTREAM_HANDOVER`, step `DONE`, operation errno 0, `timed_out` false |
| Stage start | 68.3 s guest BOOTTIME (admission floor 60 s); overlay settle 55 ms |
| Registration | core 0, PHY 0, `ufs-qcom` 0; overlay errno 0 |
| Host | `OPERATIONAL`; UFS spec 0x0310, manufacturer 408, 9 SCSI devices |
| Power mode | **HS-G4, rate B, 2 lanes each way**, fast mode both directions |
| Link events | link-startup failures 0, PA errors 0, DL errors 0, host resets 0 |
| LU 0 | 62,305,280 × 4096 |
| GPT (LBA 1–3) | matches `a0de4421…`, errno 0 |
| Test block (LBA 62,305,152) | `PATTERN` `1155097a…`, errno 0. ML060's pattern, now read through the upstream block layer |
| Return | normal return and recovery return both proved |

### Gate

- **Capabilities:** cleared from 0x12cf to 0. Writes were not possible.
- **Power management:** auto-hibernate was disabled. W-LU runtime PM was kept forbidden.
- **SCSI:** 289 commands allowed, 0 refused.
- **Device-management requests:** 18 allowed, 6 refused. All 6 refused requests were query opcode 4 (WRITE ATTRIBUTE):
  - IDN 0x0D, `wExceptionEventControl`, 3 times;
  - IDN 0x03, `bActiveICCLevel`, 3 times.

  These are the upstream probe's exception-event enable and ICC-level set,
  each tried three times. The probe tolerated both refusals and reached
  OPERATIONAL.

## Timing (seconds from preflight)

| Event | ML066 | ML065 (V17, fixed stage) |
| --- | ---: | ---: |
| Module permit | 110.3 | 106.1 |
| Download return | 116.5 | 112.7 |
| Final health | 207.0 | 195.1 |

The whole session took 3 min 27 s. The upstream stack took about 6 s from
permit to return, the same as the fixed stage. The stop-or-park shutdown did
not hold the restart.

## What this establishes

- **Generic UFS stack.** The generic Linux UFS stack runs on g0q with three
  board PHY values, a late overlay and fixed rails. It reaches the
  controller's full rate (HS-G4 ×2), with no vendor driver.
- **ML060's pattern.** It was written by the fixed stage. It survived six
  Android returns, and the upstream driver now reads it back unchanged.
- **Gate.** The gate refused only attribute writes from the probe. No refused
  request was needed to reach OPERATIONAL.
- **Run tallies, ML056–ML066.**
  - Eleven consecutive mainline runs completed the UFS link.
  - ML059–ML066 are eight consecutive completed storage stages.

## Evidence

- Run: `workspace/private/outputs/s22plus-ml066-ufs-handover-h0-20261128-1/` (task-1, `operator-approval.json`, `operation-0001/io-mainline-evidence/control-intent.json` with the decoded V18 result, `task-1/closed.json`)
- Capability and candidates: `workspace/private/outputs/s22plus-ufs-upstream-h0-20261128-1/` (capability-11, candidate-handover-1/-2, final-artifacts-11)

## Next

Next is 4c: a read-only mount of `native_data` on top of this stack. It needs
its own report version and contract text. Candidate b (`candidate-handover-2`)
is still qualified-ready, should a repeat be wanted.
