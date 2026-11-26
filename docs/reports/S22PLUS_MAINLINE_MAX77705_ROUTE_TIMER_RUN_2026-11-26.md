# S22+ no-touch route-timer run

The 2026-11-26 attended route-timer run on SM-S906N / g0q / FYG8 closed
`OBSERVED_MAX77705_USB_ROUTE` / `ANDROID_CLOSED_HEALTHY`. The cycle had no
cue and no physical return step. It went from Android to Download, then the
candidate, the routed USB evidence, an automatic Download, original Android
and health. The run used the task prepared under the
[route-timer policy](../operations/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_V1.md)
and the v61 review set adopted in `1e12f415a2`. The design and H0 checks are
in the [H0 report](S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_H0_2026-11-26.md).

## Phone-side record

The owner authenticated the response as
`AUTHENTICATED_MAX77705_ROUTE_TIMER_TRANSCRIPT`, with runtime schema
`s22plus-fyg8-debian-max77705-route-timer-v1`. The record verdict is
`ROUTE_CONFIGURED_WITHOUT_REPLUG`. Times are the observer's, from its first
sequence.

| Time | Kind | UDC | CONTROL1 | Note |
| ---: | --- | --- | ---: | --- |
| 0.010 s | begin | — | `0x3f` | `BC_STATUS=0x82`, `CC_STATUS0=0xa1` |
| 0.243 s | udc | not attached | — | dwell starts |
| 3.304 s | prewrite | not attached | `0x3f` | fresh mailbox read |
| 3.313 s | write | not attached | — | `COM_USB` once, status ok |
| 4.128 s | udc | default | — | bus reset from the host |
| 4.331 s | udc | configured | — | |
| 4.336 s | readback | configured | `0x09` | write held |
| 5.252 s | request | configured | `0x09` | read at the authenticated request |

The record has eight events, five mailbox commands, one route write and no
rejected write. The three I/O errors are the FSA4480 reads (failure mask
`0xff`), as in Stages 1 and 2. This is the second boot to start at `0x3f`
with the UDC unattached, and the second in which one write led to
configuration with the cable untouched. The write-to-reset interval was
0.8 s here and 0.6 s in Stage 2.

## Timeline

Seconds from grant open:

| Event | Seconds |
| --- | ---: |
| Android-to-Download command | 2.23 |
| candidate transfer start / done | 15.22 / 16.83 |
| candidate evidence complete | 46.13 |
| new Download generation observed | 605.29 |
| automatic original-A transfer start / done | 606.99 / 608.53 |
| Android health complete | 648.35 |

The new Download arrived 590.07 s after the candidate launch. This matches
ML050's 590 s and lies inside the 660 s window. The guest timer fires at
BOOTTIME 555 s, and boot to PID1 accounts for the rest.

## Return

The automatic owner observed a Download generation whose measured node birth
was later than the candidate's. It then dispatched original A once through
`_recover_android` with its window receipt. The A launch names
`io-mainline-auto-recovery/window.json`, so the terminal reports
`automatic_original_a_dispatched=true`. The terminal also reports
`automatic_download_arrival_observed=true` and
`automatic_recovery_trigger_proved=false`. Health passed on the first
attempt. No `continue_approved_task` or `recover_approved_task` was
dispatched.

The run had one candidate transfer, one original-A transfer and one device
control, which was the initial Android-to-Download command. The candidate and
grant are consumed.

## Closure

The paged finalizer `s22plus_mainline_close_h0_v2.py` closed the task under
its existing independent reporting review. Its source is unchanged since that
review (`4b6dfcc6…`). `task-1/closed.json` (`c3f8e3aa…`) binds the terminal,
source snapshot, timeline and paged raw index. Closure performed no device
actions.

## Operator statement

The policy's no-touch criterion also needs the operator's post-run statement
that nothing was touched between approval and health.
Status: **pending**.

## Reading

This one boot completed the whole cycle without a cue or a physical return
step. The routing part reproduced the Stage 2 result.

The run does not show:
- which caller reset the device (`recovery_proved=false`);
- recovery from a hang before the child is armed;
- that every boot starts at `0x3f`.

It counts as one normal run toward the plan's evidence ladder. It does not
activate Conditional Autonomous F1.

The private run directory is
`workspace/private/outputs/s22plus-max77705-route-timer-h0-20261126-1/`.
