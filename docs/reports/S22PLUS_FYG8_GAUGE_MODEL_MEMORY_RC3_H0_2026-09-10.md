# S22+ v0.1.2-rc.3 model correction and native memory preparation

P380 prepares the smallest correction for P379's authenticated stage-7 model
rejection, plus optional memory observations in the same native boot. The target
is SM-S906N/g0q/S906NKSS7FYG8. v0.1.1 remains the functional version; no live
rc.3 gauge or native memory result is claimed by these host checks.
The subsequent attended run closed NO_PROOF with exact rollback and final health;
its gauge subproof passed, but command-output loss prevented full qualification.
The preparation evidence below is retained as history.
See [the exact scope](../operations/S22PLUS_FYG8_GAUGE_MODEL_MEMORY_V1.md).

## Changes and evidence separation

The telemetry provider replaces the two guessed SoC model strings with the exact
post-close Android-observed `Samsung G0Q PROJECT (board-id,12)`. Its native
probe still checks that value before any bus read. All other identity, resistor,
parent/client ABI, locking, measurement, conversion and latched-fault behavior
remain unchanged. P379 did not reach the later checks; rc.3 may still reject
binding or readings. The measurement core is byte-identical to its predecessor.
Consumed P378/P379 source, artifacts, approvals and journals remain sealed.

The sixth existing console command records two optional bounded memory snapshots
on authenticated stderr, before and after its gauge wait, at least two seconds
apart. It reads uptime, meminfo, PID1 status, root model and a bounded BusyBox
process census without arguments or environment. The exact command is 640 bytes,
inside the existing 1023-byte cap; command count, 15-second timeout, twelve wait
iterations, gauge proof and CONTROL are retained. No collection process persists
beyond the existing console command. Only step six of the fixed qualifications permits diagnostic stderr;
the raw stderr identity remains intact and is authenticated/replay-compared.
Absent or incomplete memory data cannot become gauge success or a gauge failure.
The existing shared deadline/output/transport failure rules still apply.

The HUD metric is `(MemTotal - MemAvailable) / 1024`, not summed RSS. The new
native data will support comparison in that same boot; the prior Android sample
cannot decompose the photographed 1053 MiB. Reservation and runtime categories
will be kept distinct, with overlaps and incomplete captures acknowledged.
Detailed attribution is subsequent host work, separate from gauge qualification.

## Host qualification

The new provider is A/B identical, 304,408 bytes, SHA-256
`0026fcb72d95f787456f44d131e31170c292fe3a9c19665ca691ffec2ee2ba0c`.
Its exact Image imports retain all 21 expected symbol CRCs. The candidate builder
revalidates the complete provider receipt and each bound source input.

Final A/B candidate artifacts:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| AP | 31,129,641 | `c7f8697eb9f72b15f1a02156c50006895a05a01995bd8fa92b9e98291bde1bb8` |
| Image | 41,490,944 | `13e482969b6ecd0498de901e8bb223434d4dbca4f70437740f5b7ad195825417` |
| init | 149,448 | `91df637b09b39d2ec3d2d3920697cb611e0a662f7b7055f8253088d5a90717d3` |
| renderer/collector | 777,336 | `f0775d7bc5f7d5e2389fe000b93a4308a9c576d322230337c29a9f66b58e7e39` |

All 296 bound source inputs are retained in the build result. The
kernel Image has only the existing same-length run-identity transform; imports
and section layout are preserved. The generated userspace is static ARM64.

Root checks passed: two actual-wrapper tests (exact model, wrong model/board,
old SoC rejection, later guards, raw error and no-repeat behavior), two actual
ARM64 BusyBox/optional-stderr tests, sixteen HUD/evidence/integration tests,
and four live receipt invariants. Integration includes real PID1/collector/HUD
IPC, blocked/exited collector behavior and authenticated raw replay. Actual
BusyBox testing exercised the exact shell/applications/caps with only the host
launcher substituted; it is not a live target measurement.

Official static result: 39,666 bytes, SHA-256
`9df9484e0dd54c31a1554652f2b92b3619eb48d487b1faee1e4408c6ae0d17e2`,
`PASS_P380_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY`.

Independent final review returned PASS_GO, binding the actual A/B artifacts,
296 build inputs, 44 static sources, exact official-static regeneration and real
offline promotion. Six updated integration/receipt tests and four earlier
model/memory tests passed independently. Private review SHA-256:
`8664ae91b9c4e098bab4fcde63ae7c174abb41a564af5c8dbe9cddbd19155bba`.
The review covers only the existing foreground-goal `f1_owner` and `target`
source refresh; the prior receipt is retained. No grant is opened or renewed.
HUD image publication remains deferred until actual rc.3 gauge display.

## READY publication and connected preparation

The final READY manifest is 10,608 bytes, SHA-256
`8a189d5bd5c9fb5de43a66143b3ae06cbb8b8adce682c9e31a496ae258bb2963`. Publication verified the actual
common bundle `eb5ff231ba42daa9ff09a4a8740edd7b271bbe1ef0457a17058fe7a1fe638386`.
Publication is host-only capability evidence, not F1 permission.

One `--prepare` completed in `p380-ready1-prepared-20260910-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Exact target/firmware and current
health were checked under the existing raw-first mechanism. A90 and S20+
received no command. Device writes, reboot requests, Odin, partition transfers
and live authorization are false. No F1 ledger row or native lease is created.

| Preparation artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| D0 result | 3,261 | `7ca6c88890108ff7cff8567f7365ee3f52df6f39c0a862abbbe305b096927702` |
| prepared record | 39,616 | `ab2b02fd183fa4664f71d01d4287ea0bb2df6edf00bb1e4679c54a08bcef71e8` |
| sealed console plan | 877 | `0f34bf24d10c44a5dcc3577fd12dc80a38fa871283ae25a53eef153b7acbee4e` |

The actual prepared-record consumer reopened the run successfully and sealed
three bounded console/RAM/HUD commands. P379 approval is consumed and is not
reused. A fresh exact approval and current physical attendance remain required
for the new candidate, its one exact rollback and final health. Preparation
does not prove native model matching, gauge readings or memory attribution.

Touched Python compilation, focused tests, content/link checks, goal size and
repository-boundary checks passed. Unrelated S20+ and old P345 changes remain
outside this unit; no push or HUD image publication was performed.

## P380 live close and output-loss incident

The fresh exact approval was consumed once. Original execute completed
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p380_root_console_unproved_rollback_verified`. One candidate and one exact
rollback completed; the actual journal reader validated CLOSED/19.
`final_verified=true`, rooted FYG8/original partition hashes/Android and
Download absence passed, and `recovery_required=false`. No recover invocation
or replay occurred. A90 and S20+ received no command.

All six fixed commands reached terminal responses, but aggregate qualification
was false and all three planned commands remained unexecuted. The sixth command
produced a valid HUD subproof: five matched frames (seq1–5), uptime3671–7708 ms,
four BUSY frames, three distinct fresh memory/CPU/gauge samples (gauge seq1–3).
Authenticated diagnostics show probe13/bound1/read35/error0. The native root
model itself was also observed as `Samsung G0Q PROJECT (board-id,12)`.

| Gauge field | Authenticated observed values |
| --- | --- |
| SOC | 1000 permille (100%, capped gauge estimate) |
| Voltage | 4,336,562 / 4,337,031 / 4,337,968 microvolts |
| Signed current | +607,812 / +576,562 / +557,031 microamps |

These are real native gauge measurements and matched-flip evidence. They do not
prove Android charging policy, physical pixels, or a complete console run. No
operator photograph is included in this close. v0.1.1 remains the confirmed
functional version; rc.3 is not promoted and HUD image publication is deferred.

The sixth terminal reports flags4 (`RC1_FLAG_TRUNCATED`), 19,244 retained bytes,
1,536 dropped bytes and 26 output frames. Its stdout was 4,069 bytes and stderr
15,175 bytes. Authenticated offline replay reconstructed both and matched the
original stream identities. Successful read commands do not erase lost output.

In the exact root-console source, the sole drop branch tests the 1 MiB output
limit, the 2048-frame limit, or a transmit queue count of at least five (eight
slots with three reserved). The monotonic terminal counts exclude both size
limits; queue pressure is the remaining branch. This supports a source-constrained diagnosis of producer/queue backpressure
loss, not failed gauge binding or unit conversion; queue depth itself was not
traced. The record does
not identify every discarded byte or prove a physical USB fault. The aggregate counter does not locate every dropped byte by stream.
Stderr completeness, and therefore the complete process census, is unproved. The raw run remains unchanged.

The host tests proved bounded total size and optional-stderr separation but did
not reproduce this target queue pressure. Optional diagnostic *contents* remain
independent of gauge proof; the existing no-output-loss command requirement
still correctly rejects a truncated run. A future correction must qualify the
actual burst/backpressure path while retaining CONTROL, deadlines and bounded
queues. No next candidate, relaxed assertion or replay is authorized here.

## Native memory finding

Both retained meminfo blocks contain the same 52 strictly parsed numeric fields.
The command reports aggregate output truncation; completeness of either stream
beyond the retained records must not be inferred.
The snapshots are sequential reads rather than atomic system-wide snapshots.

| Field | Early (uptime6.39 s), KiB | Late (uptime8.42 s), KiB |
| --- | ---: | ---: |
| MemTotal | 7,193,456 | 7,193,456 |
| MemAvailable | 6,114,428 | 6,114,244 |
| MemFree | 6,147,192 | 6,146,812 |
| RbinTotal | 819,200 | 819,200 |
| RbinAlloced | 0 | 0 |
| RbinFree | 0 | 0 |
| Cached | 91,744 | 91,744 |
| Shmem | 91,744 | 91,744 |
| Slab | 66,680 | 67,172 |
| SReclaimable | 19,392 | 19,784 |
| SUnreclaim | 47,288 | 47,388 |
| AnonPages | 224 | 312 |
| KernelStack | 2,752 | 2,752 |
| PageTables | 104 | 132 |
| VmallocUsed | 25,068 | 25,088 |
| CmaTotal | 454,656 | 454,656 |
| CmaFree | 451,204 | 451,084 |

The exact target source explains the dominant 800 MiB component:
`of_reserved_mem.c` sets `rbin_total` from the reserved `rbin` region;
`si_meminfo()` adds it to MemTotal. Availability gains only reported RBIN
free/cached pages, which are zero in both observations. `CONFIG_RBIN=y` is
confirmed from the actual candidate Image, and the QCOM heap provider is absent
from the packaged module set. Without an installed statistics callback,
`rbin_oem_func()` leaves the caller's zero-initialized statistics unchanged.
The prepared vendor-module .config is a different input and is not substituted
for the actual Image configuration. Zero RBIN counters alone do not prove that
the reserved memory is unused.

Consequently, the HUD's 1053.738 / 1053.918 MiB includes the 800 MiB reservation
in the accounting difference. Separating that component leaves 253.738 /
253.918 MiB. This is an accounting explanation, not recovered RAM or proof that
the whole reserved area can safely be released. Do not simply relabel all of
that space as available. The same mechanism explains the scale of the previous
1053 MiB display, without inventing that earlier boot's full decomposition.

PID1 status reports VmSize384 KiB and VmRSS4 KiB at both times; this is a proc
status observation, not exact process physical-footprint accounting. AnonPages
is only224/312 KiB. This does not support a 1 GiB PID1 allocation. Cache/Shmem
are both91744 KiB, Slab is about65 MiB, and CMA is mostly free; these categories
overlap and must not be summed. The remaining accounting difference includes
other kernel allocations and availability reserves. Exact attribution remains
incomplete. The 184 KiB increase across2.03 seconds is not a long-duration
leak test and proves neither a leak nor its absence.

Canonical timeline (UTC):

| Event | Timestamp |
| --- | --- |
| `live_session_start` | 2026-09-09T21:55:00.117228Z |
| `candidate_flash_start` | 2026-09-09T21:55:19.776617Z |
| `candidate_flash_done` | 2026-09-09T21:55:21.438607Z |
| `candidate_boot_ready` | 2026-09-09T21:55:52.304589Z |
| `rollback_flash_start` | 2026-09-09T21:56:00.519040Z |
| `rollback_flash_done` | 2026-09-09T21:56:02.235804Z |
| `rollback_boot_ready` | 2026-09-09T21:56:49.052343Z |
| `live_session_end` | 2026-09-09T21:56:49.081604Z |

Private evidence remains under the exact P380 run directory:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `live-result.json` | 47,146 | `4721dc951c864fb4589033ed245bd9ca6ffd122c8092093031f396833d57e324` |
| `candidate-observer.json` | 38,814 | `50cc445c3b3b62ec11617775509ae8a9c100c6af32acaf49e58ca1f55d1435ad` |
| `authenticated-hud-log.bin` | 4,069 | `895ec472fc32c3552f04824eb0becc111cf462fed1e0976a32f0ed1f40b24323` |
| `authenticated-memory-stderr.bin` | 15,175 | `1271d8c34afb749ed5dbc4f80f9b3fbc1cd6b2e9ff95395d5203152b9cb484a1` |
| `memory-analysis.json` | 6,280 | `8c886a23774d483371bcd730091a3fe8d0f3ef4fa6c111577c2714a38c8ecf9e` |

An independent post-close review verified both stream hashes, all 52 retained
meminfo fields per snapshot, source pins and actual Image CONFIG_RBIN. It
confirmed the gauge subproof and accounting interpretation, with the queue-depth,
per-stream loss, reclaimability, RSS and leak limits stated above. This review
qualifies no fix or future device action. The private derived analysis's earlier
truncated-stderr wording is limited here to unproved stderr completeness under
an aggregate command-loss counter; it is not a per-stream loss trace.
