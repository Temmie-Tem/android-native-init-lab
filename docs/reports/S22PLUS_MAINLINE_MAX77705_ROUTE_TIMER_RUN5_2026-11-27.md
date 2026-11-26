# S22+ route-timer run 5: first cycle with no host step

Run 5 was the first attended run under the v65 set (`c56dea801f`). It used
the r5 board (AP `217842b2`). It closed `OBSERVED_MAX77705_USB_ROUTE` /
`ANDROID_CLOSED_HEALTHY` (`closed.json` `359eecf9…`).

It is the first route-timer cycle that needed no host-side step, as well as
no physical action. Every gateway continuation (`continue_approved_task`,
`recover_approved_task`, `resume_approved_health`) is `NOT_DISPATCHED`.
- The timer returned the phone to Download.
- The automatic owner observed it and transferred the original A
  (`automatic_original_a_dispatched=true`).
- Health passed on its first attempt.

The run-4 usbfs race recurred and was absorbed by the v65 retry.

## Device side

The response was authenticated as `AUTHENTICATED_MAX77705_ROUTE_TIMER_TRANSCRIPT`
with verdict `ROUTE_CONFIGURED_WITHOUT_REPLUG`, as in runs 1 to 4. This is the
sixth boot with this result.

| Event (s from grant open) | Run 5 |
| --- | ---: |
| candidate transfer start / done | 14.93 / 16.46 |
| candidate evidence complete | 45.70 |
| new Download observed by the automatic owner | 606.25 |
| automatic original-A transfer start / done | 607.86 / 609.41 |
| health complete | 663.86 |

## Automatic return

The host kernel log records these events:
- the candidate's USB device (bus 3) disconnected at 02:48:58;
- the Download device enumerated on bus 2 at 02:49:02.

At 02:48:59.26 the automatic observation's census lost a usbfs node during
its evidence read. Odin listed no endpoint, as in run 4. The diagnostic has
`failure_kind` `usbfs-endpoint-departed`, stage
`enumeration-evidence-before-snapshot` and attempted sequence 193. Under v65
the observation sealed that diagnostic, took a new census and continued. It
recorded `EXACT_DOWNLOAD_OBSERVED` for the new Download generation. The
automatic A transfer followed, bound to the automatic window. This is the
only diagnostic in the run.

Two runs in a row have now hit this race, out of five. In both, it fell
about one second after the candidate's disconnect.

## Readiness settle

The return boot re-attached ADB around boot completion, as in runs 1 and 4:
- transport 64 gave incomplete replies and then a truncated one;
- the target was absent for one poll;
- it returned as transport 65 with `boot_completed=1`.

Every following poll showed transport 65 in both inventories, with the same
boot ID. Health started 10.3 s after the first complete reply and passed on
its first attempt. As in run 4, the re-attach came before the first complete
reply. The run-3 pattern, a vanish after the first complete reply, has not
recurred on the device.

## Evidence ladder

Runs 1 to 5 are five normal runs of the same composition. All reached
`ANDROID_CLOSED_HEALTHY`, with no physical action.

| Run | Host-side steps |
| --- | --- |
| 1 | none (the bracket finished before the ADB window) |
| 2 and 3 | one health resume each |
| 4 | one `recover_approved_task` |
| 5 | none |

Run 5 is therefore the first full no-touch, no-host-step cycle under the
gaps that have been fixed. One run does not show that the cycle is
repeatable. Attendance and an exact grant per run remain required.
Conditional Autonomous F1 is not active.

## Operator statement

After closure, the operator stated that nothing was touched: "아무것도
안만짐" ("didn't touch anything"). No physical action and no host-side step
occurred.

The private run directory is
`workspace/private/outputs/s22plus-max77705-route-timer-h0-20261126-6/`.
