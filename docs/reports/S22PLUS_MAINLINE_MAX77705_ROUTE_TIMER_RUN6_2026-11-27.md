# S22+ route-timer run 6: repeatability 1 of 3

Run 6 was the first repeatability run under the v66 set (`0ea046353f`). It
used the r6 board (AP `b32e38eb`). It closed `OBSERVED_MAX77705_USB_ROUTE` /
`ANDROID_CLOSED_HEALTHY` (`closed.json` `bb1fcacd…`), with no physical
action.

The automatic-recovery observation stopped on the usbfs departure race.
This time the race hit the census's initial inventory read, before
`odin -l`, which v65 deliberately kept strict. One host-side
`recover_approved_task` transferred the original A. Health then passed on its
first attempt.

The run started about 25 minutes after approval. A Codex S20+ F1 run held
the target-session lease. The first readiness attempt exited, and the run
started once the lease was free.

## Device side

The response was authenticated as `AUTHENTICATED_MAX77705_ROUTE_TIMER_TRANSCRIPT`
with verdict `ROUTE_CONFIGURED_WITHOUT_REPLUG`. This is the seventh boot with
this result.

| Event (s from grant open) | Run 6 |
| --- | ---: |
| candidate transfer start / done | 15.82 / 17.33 |
| candidate evidence complete | 46.60 |
| automatic-recovery observation stopped | 595.82 |
| `recover_approved_task` A transfer start / done | 616.13 / 617.66 |
| health complete | 672.31 |

## Automatic-recovery stop

The host kernel log records these events:
- the candidate's USB device (bus 3) disconnected at 03:49:15;
- the Download device enumerated on bus 2 at 03:49:19.

At 03:49:16.00 the census lost a usbfs node during its initial inventory
read. The diagnostic has `failure_kind` `usbfs-endpoint-departed`, stage
`initial-inventory-before-enumeration` and attempted sequence 199. v65 retries
only a departure at the final evidence read after an empty Odin listing. It
keeps the initial-inventory stage strict, as the v65 review advised, so the
observation stopped. The owner stopped before any A intent and the phone
stayed in Download. `recover_approved_task` transferred A once.

The race has now hit three runs in a row:

| Run | Stage | Time after the candidate's disconnect | Outcome |
| --- | --- | ---: | --- |
| 4 | final evidence | ~1.2 s | stop (before v65) |
| 5 | final evidence | ~1.3 s | retried under v65 |
| 6 | initial inventory | ~1.0 s | stop |

A census reads every usbfs node twice, once before and once after
`odin -l`. The candidate's own departure can fall in either read. At the
initial inventory nothing has been listed or selected yet, so a retry there
would take a fresh census in the same way.

## Readiness settle

As in runs 4 and 5, ADB re-attached before the first complete reply
(transport 70, then 71). Health started 10.2 s after the first complete reply
on transport 71 and passed on its first attempt.

## Evidence ladder

| Run | Host-side steps |
| --- | --- |
| 1 | none |
| 2 and 3 | one health resume each |
| 4 | one `recover_approved_task` (evidence-read race) |
| 5 | none |
| 6 | one `recover_approved_task` (initial-inventory race) |

Repeatability is not shown yet. The remaining gap is the same race at the
other read of the census.

## Operator statement

Status: **pending**.

The private run directory is
`workspace/private/outputs/s22plus-max77705-route-timer-h0-20261126-7/`.
