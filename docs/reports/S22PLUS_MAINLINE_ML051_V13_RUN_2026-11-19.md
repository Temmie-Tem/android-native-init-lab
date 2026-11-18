# ML051: V13 run closed without a USB first response (operator-side cue miss)

ML051 is the first attended run of the V13 upstream-link capability
(`3532b540…`, module `5628f299…`), under the operator's exact one-operation
approval for task `f4b7dc2c…`. It closed `NO_PROOF` with
`ANDROID_CLOSED_HEALTHY`. The V13 module was never dispatched, so this run
says nothing about UFS link startup.

## What happened

| Time (2026-11-19) | Event |
| --- | --- |
| 04:18:22 | Approved entry dispatched through the reviewed terminal worker (backend review v51) |
| ~04:18:52 | Android → Download, then one boot-only N transfer completed |
| N+0 … N+120 s | 86 USB census samples; the selected path was absent in all of them |
| ~N+100 s (04:20:35) | Attach cue call refused by its own guard: `cue needs more than 60 seconds` |
| N+120 s | Owner stopped: `ML030 first observation expired` |
| N+589.533 s | Exact new-generation Download observed (child timer at guest 555 s) |
| — | One original-A transfer completed |
| 04:29 | First recovery-health read failed (`raw producer returned rc=1`) |
| 04:30 | Health-only continuation passed all seven reads; `ANDROID_CLOSED_HEALTHY` |

N and A each transferred once. The paged H0 finalizer closed the task
(`scientific_status=NO_PROOF`, `recovered=true`).

## Cause of the missing first response

The attach cue was never issued. The assistant's monitoring loop waited for
an N-transfer event name that does not exist in this journal (the actual
sequence is `effect-intent` → `step-complete` → `step-start mainline-evidence`),
so it noticed the N completion about 95 seconds late. By then less than 60
seconds remained and the reviewed cue caller correctly refused. Without a
replug, the first response did not arrive, as in ML030–ML032, ML037, ML038,
ML041, ML048 and ML050. No guard, window or retry was changed and no cue was
issued late.

## What this run does and does not show

It again shows healthy automatic Download return after a missing first
response (N+589.5 s, inside the 660 s window) and original-owner recovery
with a health-only continuation. It does not test V13: no witness, permit,
module load, UIC command or link attempt occurred.

## Reuse and next run

The capability is unchanged and remains reviewed. A fresh key-only candidate,
current D0 and a new attended approval are required; ML051's candidate,
grant and task are consumed and cannot replay. For the next run the cue is
issued from the operation journal's `step-start` of `mainline-evidence`
(the observation window), aiming near N+25 s.

Private evidence:
`workspace/private/outputs/s22plus-ufs-v13-upstream-link-h0-20261119-1/`
(`task-1/`, `cue-issue-raw/`, `close-h0-1.json`).
