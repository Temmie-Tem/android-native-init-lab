# ML055: the 60-second witness floor ran, the fixed module refused

ML055 was the first run of the
[witness-floor variant](../operations/S22PLUS_MAINLINE_UFS_ROUTE_V1.md#witness-floor-variant).
It closed **`NO_PROOF` / `ANDROID_CLOSED_HEALTHY`** (`closed.json` `b71d1aa8…`).
- **The shorter wait worked end to end.** The guest and host floors admitted
  the same-boot witness at 62.8 s of guest uptime, and the permit followed.
- **The module refused before any effect.** The fixed V13 module has its own
  300-second boot-time floor and returned `-ETIMEDOUT` from its init. No
  hardware was touched, no report exists, and recovery was the normal
  Download return with the single original A.

## Run

The operator returned the exact approval for task `8a17d259…` (1800 s, one
operation, attended). Readiness passed with zero device controls. The
target-session lease was free. The approved terminal dispatched once. The
operator was present and was asked to perform no action.

| Event (from N launch) | Seconds |
| --- | ---: |
| first authenticated response | 29.60 |
| guest uptime at the first response | 9.625 |
| witness challenge (host gap 52.999 s) | 82.60 |
| witness sealed, guest uptime 62.775 s | 83.29 |
| module permit | 86.44 |
| authenticated result sealed | 90.49 |

The whole live session took 230 s from grant to Android ready. ML054's
session took 424 s.

Counts: 1 N, 1 original A and 3 controls. There was no host recovery step,
no replug and no physical action. Final rooted Android health passed.

## Result

The sealed result record carries `load_errno = 110`, `read_errno = 0` and
`report_bytes = 0`. The host classified it `NO_PROOF`, with
`recovery_return` true. The automatic Download return, original-A transfer
and final health followed.

Cause: [`g0q_stage.c`](../../workspace/public/src/mainline/s22plus_ufs_link_h0/g0q_stage.c)
`start()` begins with

```c
if (now < 300ULL * NSEC_PER_SEC || now + 15ULL * NSEC_PER_SEC >= 540ULL * NSEC_PER_SEC)
    return -ETIMEDOUT;
```

That check runs before `g0q_rpmh_begin`, the USB coverage, the overlay and
any resource request. Returning an error from init unloads the module, so
the sysfs report never exists. `link-runtime.h` has its own pre-load check,
which blocks only after 525 s and did not fire.

## Why the reviews missed it

The floor change traced the 300-second dwell through the guest dwell, the
host gap, the host wire parser and permit, and the closure facts. Review
round 1 caught the wire parser. Nobody searched the fixed module: the
delegation describes it as unchanged and byte-identical. Its own boot-time
floor duplicates the witness bound inside the kernel. Two code-review rounds
and one owner review passed without opening `g0q_stage.c`.

Lesson: a bound shared between the host, the guest and a kernel module must
be found by searching every artifact for its literal value (`300`), including
the fixed, hash-pinned ones.

## Claims

A completed run can claim:
- the guest and host witness floor works on hardware: one same-boot witness
  at 62.8 s, authenticated, followed by one permit;
- a module refusal before any effect, followed by normal recovery and
  healthy closure.

It does not claim:
- anything about UFS at 60 seconds: the module made no hardware request.

## Next

The floor needs the module's own 300-second check lowered to the same 60
seconds. That is a new module build (one constant), which the current
delegation does not cover: it fixes the V13 module as unchanged. It needs
the operator's approval as a common-contract change, then review, a new
capability and candidate, and a new run approval.
