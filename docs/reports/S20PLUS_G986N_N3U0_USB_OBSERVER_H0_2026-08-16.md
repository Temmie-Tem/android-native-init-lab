# S20+ G986N N3-U0 USB observer H0 report

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`)

Status: **PASS HOST FIXTURES - REVIEW PENDING - NOT ACTIVE**

Machine state: `REVIEW_PENDING_NOT_ACTIVE`; live authority: `false`.

## Scope

This unit implements the dormant host-side observer for the temporary N3-U0
ACM boot overlay. It performed no live `/sys` or `/dev` inventory, USB open,
ADB, `su`, reboot, Download transition, Odin invocation, partition transfer,
or device write. All endpoint and stream behavior was exercised with temporary
fake sysfs trees and pseudoterminals.

The observer is not a run owner. It does not create a boot approval, durable
F1 journal, Download attribution, rollback authority, or final-health result.
Those remain requirements of a future independently reviewed S20+-only
attended boot process.

## Frozen public closure

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_usb_observer.py` | 16,713 | `f1c6af4123684be1122950442472de7803995345e125955322a8fd262b25e44f` |
| `tests/test_s20plus_n3u0_usb_observer.py` | 15,132 | `e6f2c72e8b5ef267af49814db23f2f629592c51a1916135a8be6c739fe70a5a0` |

The executable gate is `OBSERVER_ACTIVE = False`. Its only CLI operation is
`--render-plan`; that plan reports `active: false`, `live_authority: false`,
and empty device-command, device-write, and partition-transfer arrays.

## Exact observation grammar

The future integrated owner must first capture an empty candidate baseline and
bind the prepared physical USB node. An accepted arrival then requires all of:

- exactly one USB device on that same node with vendor/product `04e8:6861`;
- exact manufacturer `Samsung` and product string `S20Plus-N3U0`;
- no USB serial descriptor, matching the reviewed configfs witness;
- exactly one descendant `cdc_acm` interface number `00`;
- exactly one descendant `ttyACM<n>`, discovered dynamically rather than
  assuming `ttyACM0`;
- an exclusive character descriptor whose major/minor matches sysfs;
- the first complete `S20PLUS_N3U0_ACM_V1\n` record, reassembled across
  fragmented reads within the fixed 12-second bound; the witness may continue
  its reviewed repeated emission after that first accepted record; and
- the same endpoint identity after the banner read.

The arrival loop has a fixed 180-second bound. A missing endpoint, competing
candidate, wrong manufacturer, unexpected serial, zero or multiple ACM TTYs,
foreign topology, TTY identity drift, partial/wrong banner, timeout, or
exclusive-open failure is no proof. None permits a candidate replay.

Stock Android may use the same Samsung VID/PID. The observer therefore ignores
that pair unless the exact N3-U0 product string is present; once that string is
present, malformed or conflicting identity is a hard rejection rather than an
unrelated endpoint.

No raw topology or dynamic TTY name is placed in the returned receipt. The
receipt carries their SHA-256-bound endpoint identity and explicitly states
that the TTY number is not stable.

## Host validation

The focused suite passes **14/14**. It covers:

- dormant-before-inventory behavior and the no-action plan;
- exact empty baseline plus topology and bool/integer forgery rejection;
- stale candidate rejection at baseline;
- dynamic `ttyACM37` selection without a `ttyACM0` assumption;
- coexistence with a same-VID/PID stock-Android product;
- wrong manufacturer, unexpected serial, bounded pending zero-TTY enumeration,
  two TTYs, two candidate devices, and foreign topology;
- fragmented and repeated exact banners, wrong bytes, and partial timeout;
- descriptor major/minor verification, post-read endpoint revalidation, and
  receipt redaction; and
- absence of subprocess, ADB, `su`, Odin, USB-mode write, device-write open,
  or active-observer surface in the public source.

`python3 -m py_compile` and the dormant `--render-plan` path also pass.
The exact eleven-module S20+ aggregate, including the prior overlay and N1/R1
closures, passes **315/315**.

## Remaining gates

Before any connected candidate boot:

1. independently review this observer together with the already frozen N3-U0
   witness, builder, tests, and private artifact identities;
2. define one S20+-only attended boot owner that binds a fresh exact target,
   empty Download/USB baseline, this observer, the exact N3-U0 AP, and the
   exact resident Magisk rollback boot;
3. durably record candidate intent before the sole boot transfer and preserve
   candidate no-replay across every observer/reporting cut;
4. classify absent or malformed banner only as unproved candidate outcome and
   immediately follow the predeclared resident-boot recovery; and
5. finish only after exact healthy rooted Android on the resident boot.

No existing R1/F1 approval, S22+ observer, A90 result, or this H0 PASS grants
those actions.
