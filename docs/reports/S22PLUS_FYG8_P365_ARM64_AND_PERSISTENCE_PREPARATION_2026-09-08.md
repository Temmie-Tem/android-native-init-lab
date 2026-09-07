# S22+ P365 ARM64 and persistence preparation

## Scope and authority

P365 corrects the two confirmed P364 ARM64 open-flag defects and the native-return
state/prepared serialization capacity. The preparation authorization covered
implementation, H0 qualification, necessary D0/D1 preparation and new F1 code
issuance only. The operator subsequently returned the fresh attended F1 approval;
that one-shot run is now consumed and CLOSED as recorded below. P363/P364 remain
consumed and unchanged.

The P361 renderer, five return-module bytes/order/parameters, diagnostic grammar,
fixed CONTROL, physical fallback and exact Magisk rollback remain unchanged.
The existing diagnostic deadline limitation, stock initialization FULLDUMP window
and NVMEM failure hazard remain explicit in the target contract. No automatic
recovery or new physical output is claimed by host qualification.

## Changes

A source-bound ARM64 declaration supplies O_DIRECTORY=040000 and
O_NOFOLLOW=0100000. The fresh P365 generator replaces exactly the two erroneous
open operands in the sealed predecessor code. It preserves same-FD file metadata,
hash, seek and insertion checks; no provider check was removed. Old candidate
sources, images, source pins and journals were not patched.

Only P365 prepared and live-state records gain the existing 64-KiB allowance.
Other variants retain their selected limits, and journal/general record limits
remain unchanged. Diagnostic registration is shared by the existing declaration;
P365 retains its own run/domain/schema and return intent/window filenames.
The exact inherited shared return-state names remain owner-restricted.

## Behavioral verification

Four ARM64 tests compile static AArch64 code, inspect the ELF architecture and
execute the actual generated provider/module functions under qemu-aarch64:

- Correct directory flags accept the provider directory and reject a regular
  file with ENOTDIR; missing and non-symlink provider links fail as expected.
- Correct module flags accept a valid regular file, while a final symlink fails
  with ELOOP before insertion. Wrong mode or hash also fails before insertion.
- Module open/fstat/read/hash/seek/close are real. The same FD must reach the
  insertion witness at offset zero. Only host fixture owner IDs are normalized,
  and finit_module is a stub; no module is loaded by these tests.
- Static assertions compare target UAPI flag values, syscall numbers and the
  target stat layout. Source-bound constants are in build and static closures.

The complete persistence fixture connects actual generated C, real framed
qualification/raw capture, the production receipt publisher and reparser,
execute/rollback/CLOSED state routing, state/result writers and validators, and
CLOSED recovery with a backend that rejects any operation. Physical ADB/Odin/USB,
initial platform-envelope data and the C peer's kernel operations are fixtures;
the unchanged physical USB trace sidecar is excluded from this H0 platform.
The actual prepared source-binding consumer is a separate later preparation check.

| H0 case | State bytes | Result bytes | Exact expected terminal |
| --- | ---: | ---: | --- |
| Normal CONTROL completion and fixture Download | 34,898 | 39,323 | P365 native-return PASS |
| Late writer-binding failure | 27,406 | 31,387 | NO_PROOF, rollback verified |
| Stalled child after diagnostic deadline | 29,194 | 33,373 | NO_PROOF, rollback verified |
| ACK write failure after intent consumption | 29,877 | 34,088 | NO_PROOF, rollback verified |

All four cases assert their exact verdict/outcome, final health, canonical timeline
and one fixture candidate plus one rollback. The normal state is explicitly
larger than 32 KiB and no larger than 64 KiB. A terminal publication cut leaves
CLOSED state; existing finalization re-emits the result with no backend call and
unchanged prior file contents. This is host-only finalization, not a claim that
repairing journal reopen preserves metadata. Tampered cached progress rejects.
Bound checks confirm old P364/P363/P345 records and oversized journal records
still reject, while P365 also rejects beyond 64 KiB.

The three persistence tests and four ARM64 tests passed. All 24 P363 and 15 P364
regression tests passed; 17 touched Python files passed py_compile. Initial H0
lifecycle fixture errors were missing simulated Type-C/backend/delegate inputs;
those fixtures were completed without weakening production validation or issuing
a connected command. All failed H0 logs remain private.

## Frozen build and review

Before build intent, 109 source inputs and the changed-source comparison were
recorded. All remained byte-identical after the A/B build. Freeze receipt SHA-256:
`75a63d6fcc5ad8654a75a3af65f3a25d41255c74b2c1a76f8c70c56acb22e325`.
The existing same-length raw Image and IKCONFIG identity transform was revalidated.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| A/B boot-only AP | 31,006,761 | `22323fba0726356313e4da67d53a4a27ea9c314822500e76b1d645213417bdae` |
| A/B init | 150,632 | `4e1215ed5eb3426256b092f097371f4e3ea399e586385c7d6a510bea8717cbd9` |
| Retained P361 renderer | 710,040 | `5e66fea1f312aa81853aa499336a35bc397886b7fbdafb7421b8db8d69d68919` |
| Image | 41,490,944 | `b1314bbdad88fe9df3f90f902a8b9f952a9857eb300ff5ad5fa80ea61c2d4faa` |

Build-result SHA-256:
`557469268e3492a05236bc798c50bfa8b3c056a24e5f9759a66999a591a1bdcc`.
Static result is 60,672 bytes, SHA-256
`80ad8b4e2b8b58e55d3c051b001ddb0535eabf5adf54f7e2b6ea3a10c4b7c744`,
with `PASS_P365_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY`.

Independent native and host/persistence reviews returned scoped PASS_GO with
no blockers. The native reviewer confirmed actual compiled open masks 0x84000
and 0x88000, init/AP linkage and unchanged renderer/module declarations.
Private review SHA-256 values:

- Native: `d30e97b8ae4f51cfd8c1d14be8163ca2f7e98e13221fae9f4735cf6af5f9527f`.
- Host/persistence: `7baa7722b9f39d4e59fbe609cbf6001af222fe9bcaa1ab2dd177b18231617336`.

Evidence remains under `workspace/private/outputs/s22plus_fyg8_p365/`.

## Past-failure checklist application

Using the [scoped checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md):

| Item | Status and evidence |
| --- | --- |
| ABI | Confirmed by exact constants, real ARM64 positive/negative behavior and final init masks. |
| IO / SEMANTIC | Unchanged corrections retained; normal and error protocol cases assert exact terminal outcomes and no false qualification. |
| WIRE | Actual C through raw writer, production receipt publisher and immutable raw replay passes. |
| PERSIST | Success/late-error state and result roundtrips, publication cut and scoped limits pass. Actual fresh preparation binding remains separate. |
| ROUTE | P365 success/NO_PROOF/CLOSED paths and inherited owner-restricted fields pass. |
| ARTIFACT | Source freeze, raw/embedded identity transform, exact A/B AP/init and unchanged renderer verified. |
| AUDIT | Scratch finalization permits existing repairing index behavior; no read-only metadata claim. Consumed records were not reopened or edited for tests. |
| DISPLAY | Existing P361 renderer bytes reused; no fresh display claim. |
| RETURN | H0 one-candidate/one-rollback accounting and rejecting-backend CLOSED replay pass; real native return remains unproved. |

A90 and S20+ received no command from this implementation/H0 unit.

The publishing entry first passed the real offline bundle rehearsal, then
published and reopened ready1 manifest 5,054 bytes, SHA-256
`cf6bf05acba57180f12334ac7609e2a81f17635d1662e897cb503e09b60f4322`.
Bundle SHA-256 is
`1a81bfdda23f67a0e1495f74763cd1c8eb5bc87ccd1c895cf07d5a4b7749a122`.
This registration created no connected run or F1 authority.

## Connected preparation

Fresh exact-target D0 returned `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`.
No D1 reboot was needed. The production `load_prepared` consumer then reopened
the real bundle and prepared record successfully. Preparation requested no
reboot, invoked no Odin and transferred no partition payload; F1 remains
unauthorized until the operator returns the fresh attended approval code.

Private run: `workspace/private/runs/device-action-f1-live-v2/p365-ready1-prepared-20260908-1/`.
Prepared record: 32,539 bytes, SHA-256
`536836f6371c87b25733f579a0d9f801a99c83a5cf9814d5fd6024ba785b23fb`.
D0 result: 3,261 bytes, SHA-256
`1ce5c6cb6af97f7c40fbb99b7560668fde0d46f7ec7329d33580b9b395cd1faf`.
The reopen summary is retained in the private output directory as
`connected-prepared-reopen.json`. A90 and S20+ received no command from this unit.

## Consumed F1 result

The operator returned the exact fresh approval. Candidate transfer completed
once at 2026-09-07T19:44:11.821313Z. All preparation stages and clone returned:
46 authenticated diagnostic records retained no reported failure or unreturned
stage. The observer accepted ten swap submissions and the fixed Download
CONTROL ACK. ACK establishes acceptance, not successful reboot by itself.

The operator separately reported that the screen changed, then went off and
entered Download automatically, without physical intervention. These two private
observation notes preserve the original statements. They corroborate visible
activity and an operator-observed automatic transition, without upgrading the
machine's missing bounded arrival evidence or establishing pixel-exact output.

After observation, the original execute exited with
`measured USB endpoint inventory failed`, before rollback intent. Retained
snapshot 9 birth-stat evidence returned exit 1 / ENOENT for a vanished USB node;
the snapshot was not successfully published. This identifies the immediate
inventory failure, not an independently proved physical or kernel cause.
The runner stopped as required. No candidate or CONTROL was replayed.

One same-journal `--recover` invocation revalidated the binding and exact
Download endpoint, then transferred the approved Magisk rollback once at
2026-09-07T19:46:05.635963Z. The original software window was not renewed;
its retained outcome is `window-expired-before-observation`. Final rooted FYG8,
original boot/supporting hashes, Android health and absent Download passed.
Journal CLOSED/19 at 2026-09-07T19:46:42.562697Z, recovery_required=false.

Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, outcome
`p365_native_return_control_unproved_rollback_verified`. Native preparation,
swap submissions, CONTROL acceptance, operator observation, machine arrival
qualification and final recovery remain distinct evidence claims.

The 40,414-byte live state and 45,270-byte result passed production publication
without repair. Result SHA-256:
`eed6f721b6fc0d887301a3c6a784ce87734ac02392171a86f6d9eb3b3a18b5c1`.
The execution closure is commit `3ccdae6153` with preparation reporting in
`e2e9dc821c`; consumed source and preparation pins remain unchanged. Raw execute,
recover, USB captures and operator statements remain private. One matching F1
ledger row records this closure. A90/S20+ received no command; no new F1 is active.

Post-run documentation diff/privacy checks passed. The full ledger taxonomy
check fails identically before and after this row on pre-existing row 547's
unknown evidence outcome; both private check outputs are retained. This unit
does not relabel that unrelated historical entry.
