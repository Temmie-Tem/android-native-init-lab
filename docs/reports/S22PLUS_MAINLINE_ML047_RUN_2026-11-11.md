# ML047 observed UIC_ERROR during UFS link startup

The S22+ issued one DME_LINK_STARTUP after six successful local UniPro
commands. The first rejected interrupt sample was **`0x00000004`**, solely
**UIC_ERROR** in the selected kernel's UFSHCI header. The V12 producer saved
that word and returned EIO. The diagnostic met its criterion. Link success
remains **NO_PROOF**. Automatic Download return and one original-A transfer
restored Android. The original owner closed **ANDROID_CLOSED_HEALTHY**.

[H0 implementation and independent review](S22PLUS_MAINLINE_ML047_LINK_IRQ_H0_2026-11-11.md)
is recorded at commit `40c0b5f4b5`. The final host suite passed 177 tests.
The operator returned the prepared task's exact 1800-second, one-operation
approval and confirmed current attendance and usable physical Download
recovery. All seven preapproval health captures passed. The approved terminal
dispatched the candidate once.

## What the hardware reported

| V12 field | Authenticated observation |
| --- | --- |
| First CFG1 reads and outcome | `0x1c00052c` before and after, bit clear, original budget passed |
| Initial preparation | All eleven guards passed, timely initial IS-zero acknowledgement, eleven power records settled |
| Stage and local UIC commands | Stage 6, PCS ready, 6 local commands |
| Link issue and pre-command HCS | Issued once, HCS `0x00000008` |
| First rejected link-poll sample | `0x00000004` |
| Unexpected bits after removing `0x500` | `0x00000004` |
| Branch and return | `UNEXPECTED_STATUS`, EIO (`-5`) |

The sample contains neither UIC_COMMAND_COMPL (`0x400`) nor UIC_LINK_STARTUP
(`0x100`). The early EIO occurs before the reads of command result and
post-command HCS. Their zero storage values carry no measurement at this site.
The result identifies the UIC error indication. Its originating protocol
layer and the state of the peer remain unobserved. ML046's missing interrupt
sample retains its original classification. ML047's word belongs to ML047.

The first authenticated RAM PID 1 response arrived at **N+55.762 seconds**,
with zero block devices and a fresh recovery-child response. The same-boot
witness measured **300.343 seconds on the host** and **300.433 seconds in the
guest**. One module permit followed. Its authenticated result was sealed at
**N+360.002 seconds**. Offline rederivation verified the witness and frame
authentication, the raw 33 fields and the typed V12 result.

## Reconnect cue and host notification incident

The single guarded cue was published at N+37.328 seconds. The operator
reported completing one phone-end reconnection, recorded at N+67.087 seconds.
The first authenticated response preceded the completion report. The actual
physical reconnection time was not instrumented. The fixed cue and resolution
receipts contain the child streams and status for each call.

The host notification process returned. Its exit status was not persisted
before the audio wait raised TimeoutExpired. The host wrapper gave `paplay`
six seconds to finish a sound file whose measured duration is 6.128 seconds.
Audible completion is unverified. The operator received the chat instruction
and returned the completion statement. The timeout did not cause a second cue
or reconnection. The host incident and original cue envelope were retained
privately and verified separately from the device evidence.

## Original Android recovery and closure

The complete authenticated negative result selected the existing automatic
Download path. Result-bound control, ACK, EOF, exact Download arrival and
the only original-A transfer were verified. No physical Download action
was requested or reported. The first final-health ADB read returned 1.
The same executor preserved this failure, took its existing health-only path
after raw proof of the original-A transfer and passed all seven final reads.
The task-owned network profile was verified absent and no F1 owner remains.

| Canonical event | Seconds from grant opening |
| --- | ---: |
| Session start | 0.000 |
| Candidate transfer start / complete | 24.447 / 26.264 |
| Candidate observation step complete | 398.283 |
| Original-A transfer start / complete | 411.161 / 413.017 |
| Final health and durable session close | 459.097 |

The paged H0 finalizer and offline audit verified **531 task captures over
three pages**, plus both cue captures, the source snapshot, canonical timeline
and journal. They rederived one N transfer, one A transfer, final rooted
health and the functional result. The only nonzero task producers were the
initial ADB health read and two expected observations of an absent owned
profile. The approved terminal reports `CLOSED_BY_ORIGINAL_OWNER`. Its
separate recovery/continuation ingresses were unused. This run is consumed.

The private run is
`workspace/private/outputs/s22plus-ml047-link-irq-h0-20261111-1/`.
It contains `result-audit-1.json`, `run-audit-1.json`,
`attach-attention-incident.json`, `task-1/closed.json`,
`task-1/timeline.json`, the paged raw index and the source/review bindings.
The experiment and its recovery used only the selected S22+ lane.
