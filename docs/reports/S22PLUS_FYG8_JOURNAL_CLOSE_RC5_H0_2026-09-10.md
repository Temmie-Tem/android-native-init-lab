# S22+ v0.1.2-rc.5 ordinary close qualification

P382 is a fresh candidate under [Journal Close RC5 V1](../operations/S22PLUS_FYG8_JOURNAL_CLOSE_RC5_V1.md).
Its purpose is to finish v0.1.2 qualification with the repaired host journal
path before implementing the native baseline roundtrip design. P381 remains
consumed NO_PROOF/CLOSED; the retained functional version remains v0.1.1.

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
