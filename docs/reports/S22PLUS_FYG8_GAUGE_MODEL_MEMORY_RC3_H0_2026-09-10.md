# S22+ v0.1.2-rc.3 model correction and native memory preparation

P380 prepares the smallest correction for P379's authenticated stage-7 model
rejection, plus optional memory observations in the same native boot. The target
is SM-S906N/g0q/S906NKSS7FYG8. v0.1.1 remains the functional version; no live
rc.3 gauge or native memory result is claimed by these host checks.
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
