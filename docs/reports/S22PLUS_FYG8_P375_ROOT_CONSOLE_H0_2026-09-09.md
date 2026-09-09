# S22+ P375 attended root console H0 qualification

Target: SM-S906N/g0q/S906NKSS7FYG8. This report records host qualification, READY publication, connected D0
preparation and the subsequently completed attended F1 run. The run is closed
and grants no further candidate effect or live console authority.

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
write, reboot, Odin invocation or partition transfer. At preparation time no run owner, journal,
F1 authorization or live authorization existed.

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

## Attended F1 closure

The operator supplied the exact prepared approval. The original execute ran once
and returned `PASS_F1_V2_P375_ROOT_CONSOLE_AND_ROLLED_BACK`, outcome
`p375_root_console_rollback_verified`, CLOSED with 19 journal records and
`recovery_required=false`. One candidate and one exact rollback completed;
there was no recover invocation, reconnect, replay or later-action lease.

All five fixed qualification commands passed, including numeric root, real
proc/sys/dev, RAM state across shells, binary stderr/nonzero exit, STATUS,
process-group cancellation and post-cancel admission. All three sealed plan
commands completed with exit zero: identity, RAM-file write/read and pipeline.
The authenticated qualification reports `proved=true`, eight command terminals,
one transport session and zero physical reopenings. CONTROL acceptance is
proved separately from the subsequently observed exact Download rollback path.
Final health verified rooted FYG8 Android, boot completion, original boot and
supporting partition hashes, and target/global Download absence.

Preserve the narrower evidence: the observer's `software_download_arrival`
remains `UNPROVED` (CONTROL ACK alone proves acceptance). Supplemental stock
projection retains `P320_STOCK_WITNESS_BASE_SHAPE_FAILURE` and
`p375_proof_class=NO_PROOF_OBSERVER`; it does not establish stock-carrier causal
proof. These fields are not rewritten or promoted by the successful primary
ACM console qualification or rollback verdict. No hostile-root isolation,
kernel/PID1-stall recovery, unattended recovery, PTY or standing shell is proved.

Canonical UTC timeline:

| Event | UTC |
| --- | --- |
| live_session_start | 2026-09-09T10:34:07.834520Z |
| candidate_flash_start | 2026-09-09T10:34:25.196267Z |
| candidate_flash_done | 2026-09-09T10:34:26.860006Z |
| candidate_boot_ready | 2026-09-09T10:34:43.377501Z |
| rollback_flash_start | 2026-09-09T10:34:50.121408Z |
| rollback_flash_done | 2026-09-09T10:34:51.834799Z |
| rollback_boot_ready | 2026-09-09T10:35:38.187301Z |
| live_session_end | 2026-09-09T10:35:38.208136Z |

Private evidence remains in `p375-ready1-prepared-20260909-1`:

- `live-result.json`: 48,983 bytes, SHA-256 `d1a2a19d62287b05df5686e6e3394c873536c5036f778929730363c2c9c2bf2e`.
- `candidate-observer.json`: 40,805 bytes, SHA-256 `558abf6d2b0b26be56cba425826b9e215a97f2fd9bc9d51dd83d05715db391ab`.

A90 and S20+ received no commands. Reporting changes only; consumed evidence
and execution closure remain unchanged.
