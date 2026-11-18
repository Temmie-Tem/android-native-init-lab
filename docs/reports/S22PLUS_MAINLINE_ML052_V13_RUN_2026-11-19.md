# ML052: USB first response authenticated; attach resolution recorded too late

ML052 reused the V13 capability (`3532b540…`) with a fresh key-only
candidate (task `8d80deb4…`) after ML051. It closed `NO_PROOF` with
`ANDROID_CLOSED_HEALTHY`. The V13 module was again not dispatched.

## Timeline (W = opening of the 120-second first-response window)

| Time | Event |
| --- | --- |
| 04:36:08 | Approved entry dispatched (backend review v51) |
| W | Download, one boot-only N transfer, observation window opened (04:36:41) |
| W+26.9 s | Attach cue issued by the prepared watcher; host popup and sound |
| — | Operator replugged the phone end after seeing the cue (time not recorded) |
| **W+75.7 s** | **Authenticated base response over USB; recovery child armed** |
| W+120 s | Owner stopped: `original attach lock window expired` (no recorded resolution) |
| W+370.8 s | Operator's completion statement recorded as the cue resolution |
| later | Automatic Download, one original-A transfer, recovery health passed first time |

N and A each transferred once. The paged H0 finalizer closed the task.

## Why the module was not reached

After the authenticated base, the owner closes the attach issuance before the
witness and permit; that closure requires a recorded operator resolution
inside the original 120-second window (`s22plus_mainline_attach_v1.py`
`close_issuance`). The assistant kept a polling call open after issuing the
cue, so the operator could not answer in time, and then asked about the
replug only after the authentication. The resolution arrived about 250
seconds after the deadline. The interlock behaved as specified.

## What this run shows

A cued replug at about W+27 s produced an authenticated USB first response at
W+75.7 s: the replug dependency recorded in GOAL holds again. The automatic
recovery child was armed and returned the device without physical help.
Nothing about UFS link startup was observed.

## Next run

Same capability, fresh key-only candidate, current D0, new approval. The
operator records the resolution directly right after replugging, with a
prepared one-line command typed at the prompt (`! …resolve…`), so it does
not depend on the assistant's turn. The assistant ends its turn immediately
after the cue is issued.

Private evidence:
`workspace/private/outputs/s22plus-ml052-v13-reuse-h0-20261119-1/`.
