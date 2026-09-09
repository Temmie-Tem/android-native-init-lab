# S22+ v0.1.1 system-status HUD — rc.1 / run-001

Target: SM-S906N/g0q/S906NKSS7FYG8. Internal candidate P377 extends the completed
v0.1.0/P376 root console and immutable HUD with fixed system-status collection.
The attended rc.1/run-001 completed PASS, one exact rollback and final health.
Version v0.1.1 maps to those identical successful rc.1 artifacts; no image was
rebuilt or consumed record renamed. Existing consumed runs remain unchanged.

## Behavior and evidence limits

The 120-pixel grid places uptime, console state, memory used/total and available,
aggregate CPU usage, battery capacity, charge status and battery temperature on
the exact 1080×2340 surface. The bottom rows identify `v0.1.1-rc.1` and
`SYSTEM STATUS HUD`. Missing values show N/A, old samples show STALE. GPU and
other thermal interfaces are outside scope.

A separately owned collector reads only the fixed procfs/sysfs fields in
[Status HUD V1](../operations/S22PLUS_FYG8_STATUS_HUD_V1.md). PID1 and DRM work
never perform those reads. Nonblocking fixed packets and bounded diagnostics
preserve console/CONTROL when collection exits or stalls; kernel/PID1-stall
recovery is not claimed. Existing immutable buffer and matched flip-event
retirement rules remain intact. At most two GEM buffers are retained.

The sixth fixed qualification waits for three distinct fresh memory/CPU samples
while the console works. Battery availability remains independent. Frame log
freshness is recomputed at the matched completion event, not before a possibly
slow synchronous commit. Pixels retain the state painted for that update;
physical display remains operator observation, not machine pixel proof.

## Fixed Android D0 observation

The independently reviewed `status-hud` D0 action completed PASS, with exact
before/after target and same-boot identity. Its foreground grant is closed.
It observed MemTotal 7,394,168 KiB and MemAvailable 4,484,296 KiB, two valid
aggregate CPU counter samples, and battery type Battery, capacity 100, status
Full and temperature 262 tenths Celsius (26.2°C). These are Android observations;
they do not establish provider availability in the prospective native boot.

An initial H0 grant-opening attempt rejected the extra schema key in the prior
private target record before any device contact. The next invocation projected
only the existing serial/topology keys, preserving their exact values, then
performed the single D0 action. Neither attempt rebooted or flashed a device.
Private raw capture and the closed grant remain retained under
`workspace/private/runs/s22plus-goal-research-v1/`.

## Host validation

- The complete P377 suite passed 19 tests: generated PID1/collector/renderer
  integration with real IPC, absent/blocked collection with console and CONTROL,
  immutable DRM fault fixtures, rendering margins, malformed and stale metrics,
  evidence negatives and raw receipt reopen/claim tampering.
- The common live execution suite passed 76 tests, including rollback timeline
  and prepare/execute/recovery separation.
- Real AArch64 collector tests passed fixed parsing, overflow/decreasing/zero CPU
  counters, missing fields, procfs filesystem binding, packets, and descriptor 3
  preservation across exec with higher descriptors closed. Existing AArch64 HUD
  IPC/UAPI tests also passed; target headers confirm procfs/sysfs magic values.
- The final candidate A/B build is byte-identical. Native C compiled as static
  AArch64; the AP audit permits only `boot.img.lz4`. Candidate-static validation
  and the common promotion rehearsal passed without device contact.
- The actual generated H0 paint was inspected with its 4,352-byte row stride.
  Text fits the intended margins. This is a host preview, not live display proof.

Review found two host-only issues that were corrected before final build:
completion logs reused pre-commit sample age, and unavailable temperature could
reach an unnecessary signed absolute conversion. Regression cases cover both.
An integration timing race also showed that fresh frames can reuse a collector
sample; the fixed capture now waits for distinct sample sequences. No acceptance
predicate was relaxed and no device effect was repeated.

| Final artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Candidate AP (A/B identical) | 31,017,001 | `a097e3059b1201f0bcc2b9af010ea1071dae0d4ea282c92eed7b917a546c46c9` |
| Sole `boot.img.lz4` | 31,006,794 | `7f83996df5cc90837d95ddd240fda190af5ba385b368d0465567d6730429701d` |
| Native `/init` | 149,448 | `8cd5b95df8f4bd68887a0fb4bacfa8e1ffa65714f45d8e71d547fa0c1d4b4aaa` |
| Renderer/collector binary | 711,208 | `27e1f6d118bd50ff11768a076ebd0d1fa967692e0a4a12c3f4942bfb9fce8256` |
| Candidate static | 36,640 | `6063d4daff7d56ce39fb2bc88906d22f8e7ad61fa215d3c6b22124e70203df54` |

The final build binds 239 source inputs; static validation binds 38 direct
closure records. Draft and final outputs remain separate private evidence.
Independent final review returned PASS_GO after 20 independently executed tests,
current source rehashing, exact static regeneration, actual artifact checks and
the common rehearsal. Its private receipt is 55,986 bytes, SHA-256
`2724907bbcc22d0e1964bc180c583b6f8dfcc5afdd0e00e363a7809b4a539835`.
The foreground D0 review was refreshed for the changed owner/target bindings,
retaining prior provenance.

The [READY manifest](../../workspace/public/src/device-action/manifests/s22plus_fyg8_p377_process_v2_ready_1.json)
was published and verified at its final path: 9,010 bytes, SHA-256
`576f2d6a49b4141570f1eb6a6c7dc3483737e01b84b571ec1719b44a40ca742d`.
The verified bundle SHA-256 is
`5e8486010c21fcae6d6af719e2be6046486844b8d304bee9b0e48e6c54f53592`.
At publication no F1 ledger row or execution grant existed. The subsequent
run is now consumed and closed; no standing native console/HUD lease remains.
A90 and S20+ received no commands from this task.


## Connected read-only preparation

Run `p377-ready1-prepared-20260909-1` completed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. The prepared record is 36,355
bytes, SHA-256 `68123a310e5dc0626c97dc85a0f47d7216528ad4ef52a4b4dafc7391d5d56ecb`.
The actual prepared record was reopened through the live owner. The three-command
plan is sealed at 881 bytes, SHA-256
`efe5c3d63f16579efafaab1398aaec15a0411bdf19b6a8383d4b40bd9f7caeb2`.
The preparation records no device write, reboot request, Odin invocation, partition transfer
or F1 authorization. It grants no standing console or candidate replay.

The planned attended run contains the six fixed qualifications followed by
three console commands: identity plus five seconds of viewing time, a same-boot
RAM-file round trip, and fifteen seconds of continued HUD observation with a
bounded final log tail. The operator supplied the exact fresh Process-v2 approval in response to the
attendance request, and the planned run subsequently completed as recorded below.


## Completed attended run

Display ID: `s22plus-fyg8-v0.1.1-rc.1-run-001`; immutable internal run ID:
`p377-ready1-prepared-20260909-1`.
Result: `PASS_F1_V2_P377_ROOT_CONSOLE_AND_ROLLED_BACK`, outcome
`p377_root_console_rollback_verified`. The original execute completed with
CLOSED/19 and `recovery_required=false`; no recovery invocation or replay occurred.

All six fixed qualifications and three sealed plan commands passed. The initial
HUD proof contains four matched frames, sequences 1–4, uptime 3,693–6,712 ms,
including three BUSY frames and three distinct fresh memory/CPU samples.
The final planned command confirmed continued updates and retained a bounded
tail through sequence 24, uptime 26,867 ms. This is retained sample evidence,
not a claim that every intermediate frame was captured or continuously observed.

The later retained samples mark memory and CPU valid (`valid=3`), with MemTotal
7,193,460 KiB and CPU values including 0 and 2 permille. Battery capacity,
charge and temperature validity bits are absent; their N/A display is the
expected unavailable-data behavior, not battery measurement proof. Android D0
battery availability must not be transferred to this native result.

CONTROL acceptance, observed exact Download, one candidate transfer, one exact
rollback and final rooted FYG8 Android/original partition hashes/Download absence
passed as separate evidence. Supplemental stock projection remains
`NO_PROOF_OBSERVER`; the ACK-only `software_download_arrival=UNPROVED` field is
not promoted to causal stock or kernel-stall recovery proof.

| Canonical event | UTC |
| --- | --- |
| Session start | 2026-09-09T13:17:13.131026Z |
| Candidate flash start | 2026-09-09T13:17:34.497360Z |
| Candidate flash done | 2026-09-09T13:17:36.166456Z |
| Candidate boot ready | 2026-09-09T13:18:12.912251Z |
| Rollback flash start | 2026-09-09T13:18:21.705258Z |
| Rollback flash done | 2026-09-09T13:18:23.524745Z |
| Rollback boot ready | 2026-09-09T13:19:10.246416Z |
| Session end | 2026-09-09T13:19:10.267220Z |

## Operator photograph

The operator supplied a photograph during this run's closeout. It visibly shows
NATIVE INIT, UPTIME 000010 S, CONSOLE BUSY, MEM 1052/7024 MiB, AVAILABLE 5972 MiB,
CPU 0.0%, SAMPLE AGE 0.0 S, and the version/purpose footer, without visible text
clipping. All three battery-related fields show N/A.

Classification: OBSERVED physical output. A single operator-provided photograph
does not establish continuous updates, exact frame sequence, capture timestamp
or independent machine pixel proof. The original photograph was copied
byte-for-byte into the private run; it is not committed or publicly embedded.
The separate observation record leaves the machine result and journal unchanged.

| Retained private evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| `live-result.json` | 50,318 | `9f6d77e4b958c7869f741fd55fc81df9e237a9d279144c3c37548bb00e98f455` |
| `candidate-observer.json` | 44,357 | `54182165a86fc6527f7e43071e3bc44bb7c9784a5ab85388150a7e60ee720d1a` |
| Original operator photograph | 80,400 | `5fc18426a2b1049f7dfdafde8d87f9a318f739f956203bd186549d3a6b2f4fc4` |
| Operator observation record | 1,120 | `62247de7665c4c593d89cb00b095c14cfd9fd06d056502414b9420305614f155` |

The agreed bounded status-HUD goal is complete. `v0.1.1` denotes this verified
functional scope, including honest unavailable battery data. It does not denote
a resident installation, long-duration operation or a new recovery capability.
