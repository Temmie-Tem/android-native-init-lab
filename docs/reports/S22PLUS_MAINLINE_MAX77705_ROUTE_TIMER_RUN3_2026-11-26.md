# S22+ route-timer normal run 3

The third attended route-timer run used the r3 board (AP `5582ed47`) under the
v63 set (`ff8a7cde8d`). It closed `OBSERVED_MAX77705_USB_ROUTE` /
`ANDROID_CLOSED_HEALTHY`. The route, timer and automatic return repeated runs
1 and 2. As in run 2, the first health attempt stopped after the
original-A transfer had completed. This time the stop came in the
seven-read health bracket, not in readiness. One host-side
`resume_approved_health` completed health, with no physical action.

## Device side

The response was authenticated as `AUTHENTICATED_MAX77705_ROUTE_TIMER_TRANSCRIPT`
with verdict `ROUTE_CONFIGURED_WITHOUT_REPLUG`. The record:
- the switch started at `0x3f`;
- one `COM_USB` write at 3.312 s;
- UDC `default` at 4.127 s and `configured` at 4.331 s;
- `0x09` read back at 4.335 s and again at the request (5.245 s).

This is the fourth boot with this result.

| Event (s from grant open) | Run 1 | Run 2 | Run 3 |
| --- | ---: | ---: | ---: |
| candidate evidence complete | 46.13 | 45.47 | 45.60 |
| new Download observed | 605.29 | 604.36 | 604.48 |
| Download after candidate launch | 590.07 | 589.77 | 589.81 |
| automatic original-A transfer done | 608.53 | 607.54 | 607.60 |
| first health attempt | complete 648.35 | stopped 649.04 | stopped 649.24 |
| health complete | 648.35 | 684.63 (resume) | 683.40 (resume) |

## Health stop

Readiness worked as v63 intended. The final readiness read returned
`boot_completed=1` with the boot ID. The bracket then began:
- the inventory and devpath reads passed;
- the properties read returned rc 0 with empty stdout;
- the root health read returned rc 1 with `adb: device '<serial>' not found`.

The stop followed at 649.24 s. When the resume ran, the target was listed
again under a new ADB transport ID (56, then 57).

## Pattern across the three runs

All three returns show transient ADB failures within about 2 s of Android
first reporting `boot_completed=1`, about 40 s after the A transfer:
- **Run 1.** One readiness read returned an empty rc 0 result. The next
  ones reached `boot_completed=1`, and the bracket finished at 648.35 s,
  before the failure window.
- **Run 2.** A readiness read returned `error: closed` at 649.04 s.
- **Run 3.** Readiness had already seen `boot_completed=1`. The bracket then
  lost the device at 649.24 s.

The changing transport IDs show that ADB re-attached. This is consistent with
Android re-enumerating USB or restarting adbd as boot completes. These
records do not identify the mechanism. The v63 tolerance covers only one
form of the disruption, and only in readiness. The general gap is that
health can start inside this short window.

A candidate next unit is a reviewed change to the mainline original-A health
path, without changing the seven-read acceptance. It would take one of two
forms:
- readiness waits until `boot_completed=1` is stable across a short settle,
  with the same boot ID and transport;
- one bounded bracket restart within the original deadline is allowed after
  such a disconnect, like the existing root-read reobservation.

Either form needs review. Each gives up a different assumption.

## Evidence ladder

Runs 1 to 3 are three normal runs of the same composition. All three reached
`ANDROID_CLOSED_HEALTHY` with automatic Download and automatic original A, and
none needed a physical action. Runs 2 and 3 each needed one host-side health
resume, so the cycle is not yet hands-off end to end.

## Operator statement

After closure, the operator stated that nothing was touched: "아무것도 안만짐"
("didn't touch anything"). No physical action occurred. The one host-side
step was the health resume described above.

The private run directory is
`workspace/private/outputs/s22plus-max77705-route-timer-h0-20261126-4/`.
