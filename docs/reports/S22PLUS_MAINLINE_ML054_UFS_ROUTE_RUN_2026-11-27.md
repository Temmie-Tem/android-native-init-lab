# ML054: first completed mainline UFS link startup, with no replug

ML054 ran the report-v13 late-UFS experiment under the
[S22PLUS_LATE_UFS_ROUTE_V1 scope](../operations/S22PLUS_MAINLINE_UFS_ROUTE_V1.md).
It closed **`PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`**
(`closed.json` `8e865905…`).

This is the first mainline S22+ run whose UFS link startup completed:
- One `DME_LINK_STARTUP` returned result code 0.
- The controller then reported Device Present.

USB enumerated with no cue and no physical action. The return to Android
needed no host-side recovery step.

[Preparation and reviews](S22PLUS_MAINLINE_UFS_ROUTE_H0_2026-11-27.md)

## Run

The operator returned the exact approval for task `2db30bfb…bf6` (1800 s, one
operation, attended). Readiness passed with zero device controls. The
target-session lease was free. The approved terminal dispatched once.

| Event | Seconds |
| --- | ---: |
| candidate transfer start / done (from grant open) | 24.79 / 26.62 |
| first authenticated response (from N launch) | 21.45 |
| guest uptime at the first response | 7.212 |
| same-boot witness, host gap / guest uptime | 300.364 / 307.724 |
| module permit sent (from N launch) | 325.94 |
| authenticated result sealed (from N launch) | 325.99 |
| original-A transfer start / done (from grant open) | 380.35 / 382.22 |
| final Android health complete (from grant open) | 424.34 |

Totals:
- one N transfer and one original-A transfer;
- three device controls;
- zero `continue`, `recover` or `resume_health` dispatches.

After the result, the authenticated Download control returned the device
(`automatic_download_return_proved`). The V13 timer child was not needed.

## USB without a replug

The attach closure records `cue: null` and `resolution: null`. The host first
saw the gadget about 19.6 s after the N launch. At the first response the
guest had been up 7.2 s, so most of the delay came before the kernel started.

Before the route write, every mainline run since ML021 needed a cued replug,
including both earlier V13 runs, ML051 and ML052.

The response layout carries no route record. So no record shows that the
write ran in this boot. This is the accepted limitation of the scope.

## UFS result (report v13, typed by the host decoder)

| Field | Observation |
| --- | --- |
| Status | `UFS_LINK_COMPLETED`, operation errno 0, normal return |
| Initial preparation | All eleven stage-two conditions PASS; HCE handoff `STOP_COMPLETE` (pre HCE 1, HCS `0x10f`, IS `0x400`); initial UCCS acknowledged, zero in time |
| Power | 11 records; claimed, triggered and acknowledged `0x7ff`; none reclaimed; no error |
| USB coverage | Covered, released, reason OK, one attempt |
| CFG1 | `0x1c00052c` before and after: `BIT_CLEAR_BUDGET_PASS` |
| Stage and local UniPro commands | Stage 6, PCS ready, 6 local commands |
| Link | Issued once; pre-command HCS `0x8` |
| Link interrupt | `0x404` (UCCS + UIC_ERROR); branch `COMPLETION`, no unexpected bits |
| Command result | 0 |
| Post-command HCS | `0xf`: Device Present, UTRLRDY, UTMRLRDY, UCRDY |
| UIC error codes (one pass) | PA `0x80000010`: error bit plus code 16 (`pa_line_reset`); DL 0; N, T and DME 0 |

Facts about the result:
- **The ML047 stop point.** ML047 stopped at the same link poll on UIC_ERROR
  alone (`0x4`), before the completion. V13 tolerates UIC_ERROR in the link
  poll, as upstream does. Here the completion followed, with a zero result
  and Device Present.
- **The UIC error.** The only error code was the PA generic bit. Upstream
  `ufshcd_update_uic_error` handles this bit as a LINERESET indication. This
  run does not test whether it had any effect.
- **CFG1.** The QUNIPRO_SEL bit (CFG1 bit 0) still read clear after the
  upstream-position write, as in ML045. The link completed with it clear.
  The audit's second explanation for ML047, that the bit never latched, is
  therefore not needed to explain a failed link startup.

## What this does not show

- No SCSI, UPIU, LU, block device or media access. The guest reported zero
  block devices, and the scope allows nothing after link startup.
- No power-mode change, gear or rate negotiation beyond the link startup.
- That the route write ran.
- That SE5 sharing had no effect on UFS beyond the module's own report.
- Repeatability. This is one boot.

## Operator statement

After closure, the operator stated that nothing was touched: "ㄴㄴ 만진거
없음" ("no, didn't touch anything"). No physical action occurred, and no
host-side recovery step was needed.

The private run directory is
`workspace/private/outputs/s22plus-ml054-ufs-route-h0-20261127-1/`.
