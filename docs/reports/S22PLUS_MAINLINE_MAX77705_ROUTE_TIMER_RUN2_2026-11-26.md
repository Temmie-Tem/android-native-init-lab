# S22+ route-timer normal run 2

The second attended route-timer run used the r2 board (AP `ab4c68d5`). It
closed `OBSERVED_MAX77705_USB_ROUTE` / `ANDROID_CLOSED_HEALTHY` under the
v62 set (`1074da5b1c`). The candidate, the routed USB evidence, the automatic
Download and the automatic original-A transfer all repeated
[run 1](S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN_2026-11-26.md). The first
health attempt stopped on a transient ADB error during the Android boot.
One host-side `resume_approved_health` then completed health, with no
physical action and no transfer.

## Phone-side record

The response was authenticated as `AUTHENTICATED_MAX77705_ROUTE_TIMER_TRANSCRIPT`
with verdict `ROUTE_CONFIGURED_WITHOUT_REPLUG`.

| Time | Kind | UDC | CONTROL1 |
| ---: | --- | --- | ---: |
| 0.011 s | begin | — | `0x3f` |
| 0.241 s | udc | not attached | — |
| 3.302 s | prewrite | not attached | `0x3f` |
| 3.311 s | write | not attached | — (`COM_USB`) |
| 4.126 s | udc | default | — |
| 4.329 s | udc | configured | — |
| 4.334 s | readback | configured | `0x09` |
| 5.165 s | request | configured | `0x09` |

The record has five mailbox commands, one route write and three FSA4480 read
errors, as in the earlier runs. This is the third boot to start at `0x3f`
and reach configuration after one write, with the cable untouched.

## Timeline

Seconds from grant open:

| Event | Seconds |
| --- | ---: |
| candidate transfer start / done | 14.69 / 16.22 |
| candidate evidence complete | 45.47 |
| new Download generation observed | 604.36 |
| automatic original-A transfer start / done | 605.99 / 607.54 |
| first health attempt stopped | 649.04 |
| `resume_approved_health` health complete | 684.63 |

The new Download arrived 589.77 s after the candidate launch. Run 1 took
590.07 s and ML050 590 s. The A launch carries the automatic window receipt,
so the terminal reports `automatic_original_a_dispatched=true`.

## Health stop

The readiness wait polls `adb devices -l` and, once the target is listed as
`device`, reads the boot ID and `sys.boot_completed`. Three such reads
returned an empty `boot_completed`. The fourth returned rc 1 with stderr
`error: closed`. That happened while Android's adbd was still starting. The
mainline return class tolerates only `device not found` there, so the error
stopped the owner with `RawCaptureError` at 649 s. The Android transfer had
already completed (`recover-android.json`, `completed: true`).

`resume_approved_health` reran health under the same approval and owner,
with no transfer. It passed on its first attempt. The paged finalizer then
closed the task (`closed.json` `d873fe1f…`).

The loader Android access class already treats `error: closed` as a
readiness disconnect (`READY_DISCONNECT_STDERR`). The mainline return class
does not. For a hands-off cycle, this is the first observed gap: one
transient error turned a completed return into a stop that needed a host
step. A reviewed change that adds the same tolerance to the mainline
readiness wait is a candidate next unit. It would cover readiness only, not
the seven-read health bracket.

## Reading

This run confirms run 1 on the device side: route, timer and automatic
return. It counts as a normal run on the evidence ladder, with one recorded
host-side health resume. It does not show which caller reset the device, and
it does not cover a hang before the timer is armed.

## Operator statement

After closure, the operator stated that nothing was touched: "ㅇㅇ 안만짐"
("yes, didn't touch"). No physical action occurred. The one host-side step
was the health resume described above.

The private run directory is
`workspace/private/outputs/s22plus-max77705-route-timer-h0-20261126-2/`.
