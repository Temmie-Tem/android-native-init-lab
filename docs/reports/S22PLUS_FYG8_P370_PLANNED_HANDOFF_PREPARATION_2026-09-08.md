# S22+ FYG8 P370 planned host handoff preparation

P370 asks whether one predeclared host tty close/reopen can retain the same
native display child and permit freshly authenticated Download CONTROL. P369's
fixed wait experiment is consumed and CLOSED; its approval cannot be reused.
This preparation is H0 until a fresh exact connected preparation and separately
returned attended F1 approval. No device effect is granted by this report.

## Bounded behavior

The renderer retains P369's three submissions, fixed wait marker and userspace
nanosleep loop under the fresh P370 identity. PID1's existing preparation,
privilege drop, child state and original sixty-second budget remain. After
READY and ten seconds, the host sends authenticated DETACH 5. PID1 consumes its
one handoff before ACK and pauses tty traffic for two seconds while continuing
child drain/reap. The same device descriptor and child state are retained.

After complete DETACH_ACK, the existing guarded host owner clears exclusivity,
closes once, checks the exact endpoint during at least 200 ms, opens once and
reapplies exclusivity/tty setup. Resume OPEN/challenge 6 binds a fresh nonce to
the first authenticated nonce, same kernel boot identity and retained state.
Resume AUTH/ACK 7 then permits the single CONTROL 8. No deadline renewal, child
relaunch, second handoff or tolerance of unexpected transport errors is added.

The receipt records two authenticated legs, one session on each descriptor,
separate raw byte ranges and distinct nonces. A completed reopening stays count
1 even if later authentication fails. An intent without completed reopening
has unknown count; absent intent has count 0. Success and failure consumers
validate any present records against the exact prepared binding and actual raw
READY; completed reopening additionally requires raw authenticated DETACH_ACK.
CONTROL intent remains bound to the current reopened descriptor.

Qualification still requires the signed three-submission/exact-marker/two-second
age/unreaped-child checkpoint, then exact bounded Download arrival, one exact
rollback and final health. Missing wait facts do not gate CONTROL. This does
not establish arbitrary disconnection recovery, client-process restart tolerance,
continuous child liveness, visible pixels, kernel/PID1-stall recovery or an
unattended F1 capability. Physical Download recovery remains attended.

## H0 validation and review

The real generated native C and host protocol run across actual PTY descriptors.
The integration fixture uses the actual common descriptor owner, exclusivity
ioctls, private record producer, paired raw consumer and final result validator;
ADB/Odin/USB platform operations and target syscalls remain fixtures.

The host PTY showed that TIOCEXCL can survive the last slave close while its
master exists. The owner therefore clears TIOCEXCL only after authenticated
DETACH_ACK and reapplies it immediately on reopening, under the existing guard.
This observation does not establish that the real ACM endpoint requires it.
Independent review confirmed the bounded ownership transition and required
negative-path record/count/raw joins, which were implemented before building.

Initial H0 fixture failures were repaired without changing production assertions:
the unscaled test clock's unchecked deadline helper was initialized/checked;
the mocked base receipt now carries the actual pre-CONTROL lane; tamper tests
use the fixture authentication binding and temporarily make their own test file
writable. Actual native/owner failures retain raw output and never replay a
CONTROL or device transfer. Final validation results and artifact identities
will be recorded after the source freeze and build.

Final focused tests passed 5/5, independently repeated. Combined P370,
P369/P368/P367, common live-runner and goal-research regressions passed 122/122.
Seventeen changed/new Python files compiled. The 174 build source inputs were
frozen and rechecked unchanged; both compiled binaries are static AArch64.
No new target numeric syscall flags were introduced: existing qualified target
wrappers remain, and host exclusivity uses the host termios symbols.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| A/B-identical boot-only AP | 31,006,761 | `42e29af50d64ed4bc430cfaa1a613fee090ede231dd1301259ce8549dfec1cf4` |
| Native init | 151,408 | `0549e50e275a50c52af4e2501e66f11ca1812987e0688d7cda835a44a189ddf4` |
| Fixed-wait renderer | 710,040 | `50031047521746a7556e41f7cc6c73fba29b91000dac7c083551c6036f32a96a` |
| Candidate-static receipt | 75,961 | `3a74ab0099e28b307369d8dc145263d37974f6ded5f60491b080009b693aad88` |

The package contains only `boot.img.lz4`; its fresh run identity joins the
source, image and init. Raw builds, test logs, source freeze and review evidence
remain in `workspace/private/outputs/s22plus_fyg8_p370/`. No P370 device run or
F1 closure ledger row exists at this preparation stage.

## Final review and publication

Final source/artifact review returned PASS_GO with no blocking findings. It
verified 174 build inputs, 222 static closure entries, A/B equality, the 122
regressions and an independent five-test run. The private review receipt is
SHA-256 `6c2a50b2fc73059b330b8e0d725888f037f9fa84fd35a478979fed94b1d4c87f`.

Actual common offline verification and publication passed. The ready manifest
is `workspace/public/src/device-action/manifests/s22plus_fyg8_p370_process_v2_ready_1.json`,
5348 bytes, SHA-256 `d7f919325447131dd0db461d5b0b2a98492f3dedc30256b74bd7de05bb1cf2ac`.
The published bundle SHA-256 is `46f02118eb77b35ca0d25d9b4608949bf11f272eb7e2620ea9d1f9367dea469d`.
Publication made no device contact.

The prospective goal-research review was refreshed for the changed live owner
and target clause; its prior exact receipt is retained privately. The current
receipt SHA-256 is `6511a0d85a0eac0418ca44bb4d4be64a7b965e8bc7f2dc18f94c44180d373c4b`.
Review verified P369 CLOSED/19 with rollback and final health, no pending D1,
F1 owner or research grants, and the current runtime review gate. No historical
grant/consumed binding was rewritten and no new research grant was opened.

## Fresh connected preparation

One fixed read-only `--prepare` completed on 2026-09-09 KST in
`p370-ready1-prepared-20260909-1` with
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. Exact rooted S22+ FYG8,
original boot/supporting hashes, completed Android/stopped boot animation and
Download absence passed. This sent no reboot, mode-change or transfer request;
other targets received no commands. The separately returned fresh approval and
physical Download recovery availability remain required before any F1 effect.

The actual `load_prepared` consumer reopened the final published/prepared paths
successfully. The prepared record has 34484 bytes and SHA-256
`4d95e6d743bbf4ee170abe59f15b2c1b3fa72c77a329fb5e6ba4c93ca8805da0`. All implementation,
qualification and connected preparation work is complete; only the separately
returned attended F1 approval is pending. No live handoff/recovery claim follows
from H0 or D0 results.
