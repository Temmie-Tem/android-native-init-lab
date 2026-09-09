# S22+ P375 attended root console H0 qualification

Target: SM-S906N/g0q/S906NKSS7FYG8. This report records host qualification,
READY publication and a fresh connected D0 preparation. It grants no candidate
effect or live console authority.

## Bounded capability

P375 gives native PID1 one authenticated CDC ACM transport for five fixed
qualification commands followed by an optional pre-effect sealed plan of at
most 64 exact BusyBox `sh -c` commands. Each plan row binds command bytes, an
absolute cwd and a finite timeout. Commands run one at a time as fresh numeric
root children against the real native proc/sys/dev view. A 64 MiB RAM workspace
persists only within the candidate boot.

Stdout and stderr retain distinct authenticated frames and share a 1 MiB command
budget. One command can emit at most 2,048 output frames; the P375 raw observer
has an 80 MiB bound. STATUS, CANCEL and CONTROL remain admitted while PID1 drains
output and performs nonblocking process-group cleanup. A known command failure
or pre-spawn terminal stops further work when required and still preserves the
single CONTROL path. Unknown authentication, framing, transport or cleanup state
stops without reopening or replay.

Before an optional EXEC, the host reserves the command timeout, ten seconds for
cleanup/return, maximum wire bytes and the CONTROL reply. Insufficient remaining
time or raw capacity records the complete unexecuted suffix and sends no EXEC.
Each sent command has a durable private intent and one terminal disposition.
CONTROL acceptance, Download arrival, exact rollback and final rooted Android
health remain separate evidence.

## Verification and review

The final root-console suite passed 33 tests. It exercises the generated native
producer and host consumer, binary output, output beyond the older 512 KiB
capture, framing/authentication failures, duplicate EXEC, cancellation, busy and
stale identities, raw/session reserve stops, sealed-plan joins, honest unexecuted
suffixes, and a fixed qualification child that exits before any output. Actual
AArch64 execution uses the packaged BusyBox path and exact target UAPI flags.

The independent changed-closure review passed 63 tests, repeated the A/B and AP
archive audit, regenerated candidate static byte-for-byte and separately probed
the early-exit fixed step. It returned `PASS_GO` with no remaining finding. The
private review binds 31 direct execution-closure records and 203 build source
inputs. No device command was used by qualification or review.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Candidate AP (A/B identical) | 31,006,761 | `724185ffadc078933c7c3f3c5274622c1d658d817a90426dd2f27ef55864cfdf` |
| Sole `boot.img.lz4` member | 30,997,452 | `407e0ed2aa4e4a7ef2fc26cafe5f3c571b64ba24c82afc00ef5b9c0c3e1cb091` |
| Candidate static | 34,346 | `0a287f8ac6c0b82858e654ec68ce67a4a7ff4079349854f55753a8edffb7c540` |
| Independent review | 9,320 | `21bfd4ba8bffc3f943e2498785e4c7f3eacb8770c28b373c6fb1c830f81db129` |

The published [READY manifest](../../workspace/public/src/device-action/manifests/s22plus_fyg8_p375_process_v2_ready_1.json)
is 7,745 bytes with SHA-256
`8e545366b8bef85b079b83ff690d38b3e40bfeb5485fe44e08ad033fbf183ebe`.
The actual final-path common bundle reopens with SHA-256
`b5c02b127cc248111bc400dc787685f088b2e3b705d9dabb453d37e71bdf6c42`.

## Connected preparation

The prepared run `p375-ready1-prepared-20260909-1` passed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Its actual consumer reopened
the final prepared record and bundle. The prepared record is 32,986 bytes with
SHA-256 `c9eaed8dfc33303e32f8e8245e96dc0a3a2d434ef6b763cacd876fd2a80ead2a`.
The D0 action made device contact for bounded reads and requested no device
write, reboot, Odin invocation or partition transfer. No run owner, journal,
F1 authorization or live authorization exists.

A canonical three-command private plan is sealed into the prepared run.
It runs system identity, writes and rereads one RAM file across fresh shells,
then checks that file through a pipeline. Its SHA-256 is
`6373ceb74b74962ea57e8dda791a70bdf4f73603a0e8fc73bc8dcec9720954f7`.
The fixed five-command qualification still proves numeric root, real proc/sys/dev,
binary stdout/stderr, nonzero exit, cancellation and post-cancel admission.

A later F1 effect requires current physical attendance and a fresh finite grant.
Hostile-root isolation, escaped-descendant cleanup, reconnect, continuous
liveness, kernel/PID1-stall recovery, unattended use and standing shell authority
remain unproved. A90 and S20+ received no commands from this task.
