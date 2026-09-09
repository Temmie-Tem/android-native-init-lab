# S22+ v0.1.1-rc.1 system-status HUD

Target: SM-S906N/g0q/S906NKSS7FYG8. Internal candidate P377 extends the completed
v0.1.0/P376 root console and immutable HUD with fixed system-status collection.
This report records H0 qualification and the separately reviewed D0 observation;
no P377 candidate effect has occurred. Existing consumed runs remain unchanged.

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
No F1 ledger row,
standing native console/HUD lease or P377 execution authority exists.
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
bounded final log tail. Execution still requires the exact fresh Process-v2
approval and current physical attendance. One candidate, one exact rollback
and final health are the intended complete run; no F1 ledger row exists yet.
