# S22+ P407 pre-handoff measurement — first run, 2026-09-26

## Result and closure

P407 `v0.4.0-rc.7` consumed one attended operation after the operator returned
the concrete one-operation/1800-second start. Fresh exact original-A health
preceded one experimental N transfer. The fixed 300-second native endpoint
wait expired without reaching the authenticated observer. No preflight record
or native health session was captured. Scientific result: **NO_PROOF**.

The recovery owner then found an exact Download endpoint and transferred the
original Android A once. Download entry was available without another host
control request; its physical or device-side cause is not established by these
records. This does not prove automatic recovery from a stalled bootstrap.

The first final-health attempt stopped on a completed ADB read returning
`device not found` (rc 1, empty stdout, no timeout/overflow/producer fault).
The existing A-transfer proof was rederived before one health-only continuation.
That continuation proved a distinct rooted Android boot, exact original
partition hashes, unchanged full GPT and 34,357,624,832-byte Android32 capacity.
Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=true`, preflight `NO_PROOF`.

Final health completed at 426.472 seconds. Raw audit and grant closure finished
at 474.989 seconds, with one N transfer, one A transfer, no retransmission and
no remaining F1 owner. The image and one-operation budget are consumed. A90 and
S20+ were not contacted by this work.

## What is and is not proved

The actual candidate transfer and original-A recovery transfer are proved by
their original durable intents and raw transport completion. Final Android
health, GPT and capacity are separately proved by the successful read bracket.
The failed health read remains retained; it was not relabelled as success.

There is no `io-preflight-observation` directory because endpoint waiting
stopped before opening the native session. Consequently the initial intent/
exec gate, module insertion, UFS/root checks, partition RO, loader execution,
cleanup, sealed record, observer adoption and USB initialization are all
unlocated on this physical run. The 300-second timeout cannot distinguish
those boundaries. Individual negative endpoint polls are not retained as raw
captures by this V3 waiter; no USB sample count or specific failure mechanism
is claimed. Android health does not prove native_data contents unchanged.

The [H0 qualification](S22PLUS_NATIVE_PREFLIGHT_P407_H0_2026-09-26.md) remains
evidence for its tested source/VM conditions, including its disclosed default
mdev-rule and loader-privilege differences from P405. It is not physical
execution proof or a diagnosis of P404/P405/P407. Debian host PID 1, switch_root,
NCM/SSH and normal native CONTROL return remain unproved.

The next bounded work is H0 analysis of the initial entry-to-observer evidence
path. Preserve the consumed artifacts and source snapshot; this result grants
no replay, additional experiment, root repair or installation.

## Canonical timeline

Times are original host BOOTTIME seconds after the returned grant opened.

| Time | Recorded event |
| ---: | --- |
| 5.823 | Fresh exact Android preflight complete |
| 5.946–9.545 | One Android Download intent and completed transition |
| 18.554–20.049 | One P407 N transfer intent and raw-proved completion |
| 20.072 | Native endpoint wait begins |
| 320.194 | Endpoint wait stops with `TimeoutError` |
| 321.684–323.089 | One original-A recovery transfer intent and completion |
| 323.101 | First recovery-health attempt begins; later ADB read fails |
| 422.854–426.472 | Read-only final-health continuation succeeds |
| 474.989 | Raw audit complete; consumed task closed, F1 owner absent |

Only three device-effect intents exist: `android-download`,
`install-native-first`, and `recover-android`. There is no result-reader EXEC,
partition-RO command intent or native CONTROL intent on the host. The automatic
measurement remains consumed by the N transfer even though its execution stage
is unproved.

## Evidence and provenance

Private base:
`workspace/private/outputs/s22plus-prehandoff-probe-p407-h0-20260926-1/`.
The source commit before the run was `bd14c430e6`. All 15 append-only journal
rows are unchanged. The audit rederived completed step/terminal proofs,
validated all 494 raw-capture receipts and stream hashes, and checked all 226
saved source copies against the original review request.

| Retained record | SHA-256 |
| --- | --- |
| Grant | `8e50ee9ae5c7da49143369965527cfc87509016779a66868f06a80ccb0a1ec34` |
| Operation | `9bf340110639adaa13819d7b42e77100ca87f33b973dd59e50c792e8e48d4b52` |
| Terminal | `20080ba4ed5df3786a762e25bc58ca3f9869c347308892b75b301479e7887f4c` |
| Closure audit | `b3d9e38c4816b6e6cbe58b54b5f1e25292f7aef9b14ee2c62ae7e9d252fd9b7a` |
| Task close | `18a606d29568c5f48de7934274b9ccfb4b2d1612221a4a86afe1d45ad29c7385` |
| Saved source manifest | `d461f5881ec19eadb461ae7a65591a8608646345218e6036d6165e4fb54e995d` |

Raw identifiers, health output, transport captures, firmware and generated
bindings remain private. Reporting did not repeat any device action.
