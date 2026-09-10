# S22+ v0.1.2-rc.5 ordinary close qualification

P382 is a fresh candidate under [Journal Close RC5 V1](../operations/S22PLUS_FYG8_JOURNAL_CLOSE_RC5_V1.md).
Its purpose is to finish v0.1.2 qualification with the repaired host journal
path before implementing the native baseline roundtrip design. P381 remains
consumed NO_PROOF/CLOSED. The attended execution below has now confirmed v0.1.2
by mapping it to the identical successful rc.5 artifacts.

## Implementation

Thirteen small namespace/build/observer wrappers seal the thirteen P381 source
files by hash and derive fresh P382 identities. Generated PID1 source is
identical after normalizing the declared run identity, including its escaped
nonce command. Renderer source is identical after normalizing identity and the
rc.5 label. Kernel changes use only the existing same-length raw/IKCONFIG run-ID
transform. The actual backpressure, gauge provider, collector, memory helper,
HUD, console wire, commands, budgets and recovery behavior are unchanged.

The common live/evidence changes register P382 as root_console with native USB
departure and existing large state/result support, and select its console and
return owners. The target explicitly adopts P382 without changing consumed P381
records. The compact OBSERVED implementation and its 32 KiB journal/64 KiB
eligible state/result limits are unchanged from the independently reviewed
[journal repair](S22PLUS_FYG8_OBSERVED_JOURNAL_H0_2026-09-10.md).

## H0 verification

The full P382 lifecycle test runs generated PID1, the collector and renderer,
real authenticated observer qualification, original raw receipt publication and
reparse, the common close/recovery owner, journal, live-state/result writers and
result validator. The existing Samsung backend's Download-arrival production
and final-health consumers run against fixture USB/Odin/ADB. Native kernel/DRM,
credentials and measurement interfaces are fixtures; the unchanged physical
P300 sidecar is disabled in this H0 platform. This is no target observation.

All four cases passed: normal close, cut before OBSERVED, cut after OBSERVED and
cut after ROLLBACK_FLASHED. Each reaches the actual P382 PASS/CLOSED result with
one candidate, one rollback, final health and no observer restart during
recovery. Original observer raw/receipt and CONTROL intent bytes remain intact;
OBSERVED holds the exact observer receipt hash without the full qualification
body. A changed proof is rejected by the real result validator. Final state is
44,825–44,826 bytes and result 50,152–50,153 bytes under the unchanged caps.
The prior pinned P381 65,160-byte input/common-close regression remains separate
coverage of the oversized historical payload; it is not a P382 live run.

Six HUD/evidence/collector/console/memory-plan tests and eighteen renderer,
receipt and normalized-identity tests passed. All 77 common live-runner tests
also passed. The independent reviewer repeated the final lifecycle and identity
tests, including four close/cut cases and required CONTROL receipt preservation.
Changed Python compilation passed. Unchanged P381 ARM64 backpressure/memory ABI
coverage is reused through the verified source equivalence; no new target ABI
behavior is claimed by host fixtures.

The first projected HUD fixture retained rc.4's literal run-ID bytes and failed
the renderer's same-run check. Correcting only the P382 fixture's ASCII/byte IDs
made the integration pass. Production identity checks were not weakened and no
device run occurred. Initial failure logs are retained privately.

## A/B artifacts and static qualification

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| AP, identical A/B | 31,150,121 | `c417ab34f492ad7a50fb0950a62593c8ecb78d5925003333251b25934df514ef` |
| Image | 41,490,944 | `4d1fc63ef2172ac932e868155af4a3a931e6853f33c939dad52c1793cdb444b1` |
| init | 149,448 | `77289e6d00167b1bb406eca705455d58669e50de7ae94ad70560a9de3284e3c1` |
| renderer/collector/snapshot mode | 778,904 | `3b9836172e6f6b95dda2cbe056c5dc3b15ad67f4e8de1e84ec57063bf5ee66aa` |

Actual init and renderer binaries are static AArch64. The build binds 335 source
inputs; static qualification binds 51 closure entries. The official static
record is 40,345 bytes, SHA-256
`7865aa869aebed79664b5fcbfbbbbf63c18148182245ee49b570c31a8c32945c`,
`PASS_P382_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY`.

Private artifacts and test evidence are under
`workspace/private/outputs/s22plus-fyg8-v0.1.2-rc.5/` and
`workspace/private/outputs/s22plus_fyg8_p382/`. Final independent review, READY
publication and connected preparation are recorded below when completed.
No v0.1.2 promotion or new device authority follows from these H0 results.

## Independent review

Final capability review returned PASS_GO with no findings. The reviewer
independently verified all 335 build inputs, 51 static closure entries, actual
A/B boot-only AP members and ramdisk entries, Image/init/renderer identities,
generated renderer equality and normalized native-helper equivalence. Two
independent lifecycle/identity tests passed, including all four close/cut cases.
The exact authentication key remains inherited; run/image/overlay identities
are fresh and the existing protocol retains fresh challenges.

The private review record is 14,355 bytes, SHA-256
`55bde3c2a41593279dc9b26770eee806084fde571dc5a94c2890ca7c53f0720c`.
It explicitly covers only current foreground review f1_owner and target source
refreshes. The other seven source roles and all eight actions are unchanged;
the prior review bytes are preserved. The current source-review consumer passed.
No grant is opened/renewed and the historical attended review remains unchanged.

## READY publication and connected preparation

The unchanged publisher validated and published the actual P382 READY manifest:
9,088 bytes, SHA-256
`a92e40137dc6680a9ad42807c45458ac850f58da992361464ad749f080334001`.
The final H0 bundle is
`e8bb9664decb54c56638af2908ab53e2262f2c5a5eb776997fdfc2d5e93a46b3`.
This is readiness only, not a candidate transfer or version confirmation.

One generic `--prepare` completed in `p382-ready1-prepared-20260910-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. The bounded exact-target reader
checked current FYG8 identity, root, original boot/supporting hashes, Android
health and Download absence. No reboot, Download request, Odin invocation or
partition transfer occurred. F1 and live-authority flags are false. A90 and
S20+ received no command.

| Preparation record | Bytes | SHA-256 |
| --- | ---: | --- |
| D0 result | 3,261 | `435c9cdce3fd08fafcadf60f831b522920683431964895a7b2ba673f09ff8522` |
| Prepared record | 39,984 | `26bce6d84246f457cfff1f2eed1396bde3f95ebdff4c834d1bc3a0cb91ad6899` |
| Three-command plan | 521 | `57c2d99d12fd58ebc400cc69954039f596f0697b54fd736650249697038f56ff` |

The actual prepared-record consumer reopened this run successfully, and the
existing P382 owner sealed the plan into the same run with the listed hash.
The plan retains the root/RAM-directory check and the two bounded memory
snapshots, with 15-second command limits and a two-second sleep before the late
snapshot. All remain unexecuted. Fresh attended approval must bind this prepared
candidate before the first effect. Consumed P381 approval and results remain
unchanged; no standing console lease or v0.1.2 confirmation is created.

Changed-path Python tests, compilation, document links, scoped diff checks and
the repository boundary check passed. Only this candidate's files are selected
for commit; unrelated S20+, AGENTS and old P345 work remain outside the unit.
No push or HUD image publication was performed.

## Attended live close and v0.1.2 confirmation

The operator supplied the exact fresh approval for
`p382-ready1-prepared-20260910-1` after the attendance/physical-recovery request.
One original `--execute` completed with
`PASS_F1_V2_P382_ROOT_CONSOLE_AND_ROLLED_BACK`, CLOSED/19 and
recovery_required=false. Candidate and rollback each have one durable attempt;
no recover invocation, candidate/CONTROL replay or repeated rollback occurred.
Execution used the reviewed sources committed at `37fddaff89`, including live
runner SHA-256 `cb318492615b6809aea37ddff689efb623271eb546f1932abade9cfa91855937`.

All six fixed functional qualifications and three sealed plan commands passed.
Every terminal reports zero dropped bytes. Expected nonzero-exit and cancellation
qualification cases retain their original statuses and are not ordinary exit-0
claims. The gauge/HUD command returned 4,399 stdout bytes, no stderr, and five
matched HUD records (sequence 1–5, uptime 3,786–7,821 ms), four during BUSY work.
The gauge predicate qualified fresh measurements. The operator subsequently
supplied the physical photograph described below; machine pixel proof is not
claimed.

The early/late memory commands each returned 1,908 bytes, no stderr and a clean
terminal. Both decoded records are valid/complete, at 9,843–9,847 ms and
12,454–12,458 ms. Their observations do not establish reclaimability or absence
of a leak and do not substitute for functional qualification.

The normal OBSERVED transition is 1,100 bytes and binds the exact original
observer and guard receipt hashes. It reached candidate_boot_ready through the
ordinary path. The return-window record is `exact-download-within-control-window`,
observed_within_software_deadline=true and physical_prompt_required=false.
Physical intervention remains UNOBSERVED and software causal attribution remains
UNPROVED; the existing ACK-only software_download_arrival and supplemental stock
NO_PROOF_OBSERVER values are preserved. Exact timely arrival is separate proof.

One exact Magisk rollback completed and final health verified rooted FYG8,
original boot/supporting partition hashes, completed Android/stopped animation
and both exact-target/global Download absence. A90 and S20+ received no command.
The original execute's returned result matches the durable result, and the
actual journal hash chain and canonical timeline validate without rewriting it.

| Canonical event | UTC |
| --- | --- |
| live_session_start | 2026-09-10T01:45:20.062352Z |
| candidate_flash_start | 2026-09-10T01:45:39.395413Z |
| candidate_flash_done | 2026-09-10T01:45:41.143461Z |
| candidate_boot_ready | 2026-09-10T01:46:02.446038Z |
| rollback_flash_start | 2026-09-10T01:46:09.448412Z |
| rollback_flash_done | 2026-09-10T01:46:11.142642Z |
| rollback_boot_ready | 2026-09-10T01:46:58.079180Z |
| live_session_end | 2026-09-10T01:46:58.094821Z |

| Immutable run evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| candidate-observer.json | 65,160 | `552b3c6f0f955c61978f9d8b9ed393c4af18dd1022caab4187b2bd7aa9c19b87` |
| live-result.json | 61,669 | `4b7c4f43ab5dd4c65b0d41629d73edd08393bdba0da288cae901108857b436d4` |
| p382-return-window.json | 1,473 | `ca24649ad3c5641e7ed23af87c79c3ebfefad095f66be246fc2dc56cb6f589e9` |

The closed live state is 55,615 bytes; the eligible state/result limits remain
64 KiB, and journal records remain bounded by 32 KiB. Full private raw evidence
and the existing consumed source/artifact bindings are retained.

This meets the predeclared bounded v0.1.2 criteria. The functional version maps
to the exact AP/init/renderer hashes listed above, without rebuild, file rename
or new tag. P381 and earlier NO_PROOF records remain unchanged. No standing
native console, native rollback baseline, unattended or kernel-stall recovery
capability is activated by the version confirmation.

## Operator photograph

The operator supplied a photograph as evidence after the successful run. Its
original bytes are preserved without editing or public image publication in
the exact run directory as `operator-hud-photo.jpg`: 165,245 bytes, SHA-256
`8ead4f3e3a6e67522e19e40594df6e066e4a1febfa084dff9a47d4cfdd9e6857`.
The private observation record is 1,163 bytes, SHA-256
`4903df06a2ef65d22f026d9c73173ceafc5c42d8df2e587ea9b585b0e0a4601f`.

The image visibly shows `V0.1.2-RC.5`, `GAUGE STATUS HUD`, uptime 7 seconds,
CONSOLE BUSY, memory 1053/7024 MiB with 5971 MiB available, CPU 0.3%, gauge
SOC 99.9%, voltage 4.337 V and current +548.4 mA. Battery temperature and charge
are N/A; sample and gauge ages read 0.0 seconds. The displayed values and rc.5
label are operator-attributed physical OBSERVED evidence. A single photograph
does not establish cryptographic frame-to-run attribution, sensor calibration
or continuous liveness, and it does not replace the authenticated machine
qualification or rollback/final-health evidence.
