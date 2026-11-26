# S22+ route-timer run 4: settle verification

Run 4 was the first attended run under the v64 set (`fa2acb0ee2`). It used
the r4 board (AP `a9686f8a`). It closed `OBSERVED_MAX77705_USB_ROUTE` /
`ANDROID_CLOSED_HEALTHY` (`closed.json` `278c8eb1…`), with no physical
action.

- **The readiness settle window worked as designed.** Health passed on its
  first attempt, with no `resume_approved_health`.
- **The automatic original-A return did not run.** The automatic-recovery
  USB observer stopped at the Download transition. One host-side
  `recover_approved_task` transferred the original A under the saved
  approval.

The cycle is therefore still not hands-off end to end. The remaining gap has
moved from health start to the automatic-recovery observer.

## Device side

The response was authenticated as `AUTHENTICATED_MAX77705_ROUTE_TIMER_TRANSCRIPT`
with verdict `ROUTE_CONFIGURED_WITHOUT_REPLUG`, as in runs 1 to 3. This is the
fifth boot with this result.

| Event (s from grant open) | Run 4 |
| --- | ---: |
| candidate transfer start / done | 14.81 / 16.34 |
| candidate evidence complete | 45.63 |
| automatic-recovery observer stopped | 595.48 |
| `recover_approved_task` A transfer start / done | 668.54 / 670.06 |
| health complete | 725.11 |

## Automatic-recovery stop

The timer child returned the phone to Download as in runs 1 to 3. The host
kernel log records these events:
- the candidate's USB device (bus 3) disconnected at 01:49:22;
- the Download device enumerated on bus 2 at 01:49:26.

The automatic-recovery owner scans every usbfs node on buses 2 and 3 in
order to see the new Download generation. Each run makes about 7,000 such
captures. At 01:49:23.198 the scan stopped with
`OdinMeasuredEvidenceFailure`. The diagnostic record has `failure_kind`
`usbfs-endpoint-departed` and stage `enumeration-evidence-before-snapshot`.
A node departed while the scan was reading it. That fits the candidate's
own disconnect about a second earlier. In runs 1 to 3 the same departure
fell between scans, so this stop is timing-dependent.

The owner stopped before any A intent. The phone stayed in Download. The
gateway's `recover_approved_task` then ran the stopped owner's fixed
recovery with the exact original A, under the saved approval and grant. A
transferred once. No candidate replay and no transfer retry occurred. As a
result the closure records `automatic_recovery_proved=false` and
`recovered=true`.

## Readiness settle

The return boot again re-attached ADB around boot completion. This time the
re-attach came before the first complete reply, as in run 1:
- transport 58 gave incomplete replies and then a truncated one;
- the target was absent for two polls;
- it returned as transport 59 with `boot_completed=1`.

Every following poll showed transport 59 in both the preceding and the
confirming inventory, with the same boot ID. Readiness accepted after
10.3 s of identical replies. The seven-read bracket then ran on transport 59
and passed on its first attempt.

This run shows the window working in practice. Under the v64 rules, it would
have restarted on the run-3 pattern, where the device vanished after the
first complete reply. This run did not reproduce that pattern, so it does
not test that path on the device. The unit tests cover it.

## Next gap

The automatic-recovery usbfs scan treats a node that departs during its
enumeration read as a measured-evidence failure. At the Download transition
the candidate's own departure can race that read. A reviewed change would
treat that exact departure as a not-yet-observed scan and keep the original
window. It would leave the new-generation identity requirements unchanged.

## Operator statement

After closure, the operator stated that nothing was touched: "ㅇㅇ 안만지고
기다리는중" ("yes, not touching, waiting"). No physical action occurred. The
one host-side step was the `recover_approved_task` described above.

The private run directory is
`workspace/private/outputs/s22plus-max77705-route-timer-h0-20261126-5/`.
