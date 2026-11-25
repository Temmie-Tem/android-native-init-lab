# S22+ one-write MAX77705 USB route run and Android return

The 2026-11-26 attended Stage 2 run on SM-S906N / g0q / FYG8 closed
`OBSERVED_MAX77705_USB_ROUTE` / `ANDROID_CLOSED_HEALTHY`. The record
verdict is `ROUTE_CONFIGURED_WITHOUT_REPLUG`, and no attach cue was issued.
The owner authenticated the mainline response and rederived the
observation at closure. The run used the task prepared under the
[route policy](../operations/S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md) and
the v60 review set adopted in `807c012dd2`.

## Phone-side record

Times are the observer's, from its first sequence.

| Time | Kind | UDC | CONTROL1 | Note |
| ---: | --- | --- | ---: | --- |
| 0.011 s | begin | — | `0x3f` | `BC_STATUS=0x82` (VBUS, CDP), `CC_STATUS0=0xa1` (sink) |
| 0.241 s | udc | not attached | — | dwell starts |
| 3.302 s | prewrite | not attached | `0x3f` | fresh mailbox read with echo |
| 3.306 s | write | not attached | — | `[0x21, 0x06, 0x09]` once, status ok |
| 3.922 s | udc | default | — | bus reset from the host |
| 4.126 s | udc | configured | — | |
| 4.334 s | readback | configured | `0x09` | write held |
| 5.160 s | request | configured | `0x09` | read at the authenticated request |

The gate reached `written`. The record has eight events, five mailbox
commands, one route write and no rejected write. `BC_STATUS` and
`CC_STATUS0` did not change across the record. The three I/O errors are the
FSA4480 reads (failure mask `0xff`), the same as in Stage 1.

## Host side

The window opened at W. The cue helper ran with `--issue-delay 45` and
recorded `CUE_NOT_ISSUABLE` at W+45 s, because the evidence step had already
ended. The attach closure carries `cue: null` and `resolution: null`.

The read-only host port watch saw no activity on the USB2 port `3-1.3`
before the gadget. It went `not attached → powered → default → configured`
at about W+29.4 to W+29.7 s, and the host kernel logged the new high-speed
device at W+29.52 s. The authenticated request attempt opened at W+30.6 s
and the evidence step completed at W+30.8 s. The SuperSpeed port stayed
unattached until Download. The cable type was not recorded (`unknown`).

No cable change was requested or reported before the physical Download for
the return, and the phone-side status registers show no VBUS or CC change.

## Reading

In this boot, the switch was open (`0x3f`) with VBUS, a CDP port and a CC
sink present, and the UDC stayed "not attached" for 3 s. One `COM_USB`
write was followed 0.6 s later by the host's bus reset and 0.8 s later by
configuration, with the cable untouched. The Stage 1 replug dependency is
therefore explained in this boot by the open D+/D− switch, and one write was
sufficient to remove it.

This is one boot. It does not show that every boot starts at `0x3f`, or
which kernel component should own the write. The 0.6 s between the write
and the bus reset is consistent with the host's attach debounce, but this
record cannot exclude another cause.

## Return to Android

After the operator confirmed physical Download, the same owner restored
original Android once and passed final health on the first attempt. The
H0 close rederived the closure. The timeline from grant open:

| Event | Seconds |
| --- | ---: |
| candidate transfer start / done | 15.15 / 16.66 |
| candidate evidence complete | 45.89 |
| original-A transfer start / done | 98.10 / 99.48 |
| Android health complete | 131.70 |

There was one candidate transfer, one original-A transfer and one device
control. The candidate and grant are consumed.

The private run directory is
`workspace/private/outputs/s22plus-max77705-route-h0-20261125-1/`.
`task-1/closed.json` binds the terminal result, source snapshot, timeline
and raw index. The cue helper log and the host port watch are in the same
directory.
