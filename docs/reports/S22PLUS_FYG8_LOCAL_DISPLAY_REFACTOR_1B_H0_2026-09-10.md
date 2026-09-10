# S22+ local display refactor 1B H0

Status: **implementation, H0 validation and independent PASS_GO complete.**
Target: SM-S906N / g0q / S906NKSS7FYG8. This implements phase1B of the
[refactoring plan](../plans/S22PLUS_FYG8_REFACTOR_PHASE1_PREPARATION_2026-09-10.md)
under the prospective [Local Display Lifecycle V1](../operations/S22PLUS_FYG8_LOCAL_DISPLAY_LIFECYCLE_V1.md).
It creates no live candidate, AP, READY manifest, grant, tag or device effect.
P382/v0.1.2 and consumed P383 NO_PROOF/CLOSED/19 remain unchanged.

## Result and start boundary

The explicit `local-display-v1` profile owns local display from the existing
native publication boundary, after unchanged platform/USB bootstrap and before
boot-ID read and OPEN/AUTH. PID1 creates the fixed RAM work directory/mount once,
starts the existing renderer/collector, and services snapshots and housekeeping
during bounded protocol I/O and console ticks. Host absence, authentication
failure, preparation/runtime failure, expiry and closing have distinct local
states. The default `console-v1` profile retains the exact P381/P382/P383 emitted
helper and renderer bytes. Historical candidate generators are untouched.

Commands, cancellation, output credits, sequence/nonce authentication and the
single CONTROL path remain. Only numeric PID1 can mutate the lifecycle inherited
by forked children. No TTY reopen, listener re-entry or child restart is added.
An accepted CONTROL reaches its existing single Download syscall only after the
authenticated ACK flush; cleanup never waits for a DRM syscall or successful
reap. Signal attempts, exact-child WNOHANG results and actual recovery remain
different facts. Kernel stalls remain outside cooperative service guarantees.

The source join replaces the historical publication function wholesale and marks
three now-unreachable publication-only witnesses unused without changing their
bodies. It keeps the rest of the fully bound platform envelope. Tests execute
the actual new publication function, including its boot-ID failure path; they do
not establish startup through the earlier platform/USB stages.

## Timing, capacity and provenance

- One read keeps its original 30-second deadline. Before the first OPEN byte,
  zero/EIO/ENODEV/EPIPE can wait on that same FD; other failures terminate it.
  Any consumed-byte failure is terminal. The 120-second preauth ceiling is
  checked again immediately before authenticated admission.
- The console retains its ten-minute session budget. Local display has a
  separate 15-minute ceiling from first start. A failure/expiry terminal hold is
  at most five seconds and cannot exceed that local deadline. CONTROL does not
  wait for this hold. No timer or terminal path renews authority.
- The local renderer/GEM reader accepts 916 frames, including finite lifecycle
  transition reserves. Command-state churn retains 1Hz. Existing 601-sample
  collector/gauge limits remain; late values become STALE/N/A.
- Local RAM logging is capped at 1MiB; the default remains 256KiB. The complete
  conservative fixed-output bound is 1,016,832 bytes, including existing limited
  gauge/GEM records, 32KiB kernel-log failure output and 32KiB miscellaneous
  startup/failure/exit allowance. The 512-byte nonblocking drain, short-write
  and overflow stops remain. No host capture or collector budget is expanded.
- Authenticated stages61/62 report cached preauth directory/mount syscall
  results. Their wire bytes are compatible but do not prove contemporaneous
  syscall execution at frame emission. Stage60 still checks current credentials.

## H0 evidence

The final new-profile suite passed **37 tests in 108.490 seconds**. Five default
source-equivalence tests passed in 0.752 seconds: **42 tests total**. These include:

- actual production publication/helper with absent and delayed peers, malformed
  OPEN, incorrect AUTH, a final valid AUTH crossing the preauth deadline,
  consumed-byte disconnect, boot-ID failure and cached RAM preparation failure;
- actual authenticated command/STATUS/cancel/CONTROL and binary stdout/stderr
  behavior, paused-reader backpressure and CONTROL while output is incomplete;
- renderer/collector exit, stall and flood, bounded logs and at-most-once cleanup;
- forked-child ownership rejection, no re-entry, no command-state rate-limit
  bypass, exact local expiry and no restart;
- all nine renderer states, rejection of unknown states, existing run/sequence/
  stale-parent/DRM-event/immutable-buffer failures, and **916 complete immutable
  frames with 915 matched retirements**, a final CLOSING record and stale metrics;
- profile-specific GEM accounting and the complete log capacity bound;
- exact FYG8 target UAPI `__NR_getpid=172`, plus real AArch64 syscall/fork behavior
  under QEMU. Numeric PID1, credentials, mounts, modules and DRM are explicit
  fixtures in host integration tests; these are not on-device PID1/DRM proofs.

The frozen P381 HUD observer rejects the new preauth states, so its aggregate HUD
qualification remains NO_PROOF for this profile. Tests preserve that limitation
and check its actual command/CONTROL results separately. The current P383 fixed
native-health observer passes, including delayed authentication and raw replay.
No historical live observer is relaxed. Future adoption needs an explicitly
compatible observer/profile binding, including cached-stage semantics.

The H0 harness built static ARM64 init/child/renderer components twice from the
actual new helper and publication join. A/B component identities match:

| Component | Bytes | SHA256 |
| --- | ---: | --- |
| Materialized helper C | 74,401 | `44585c4894e83854f06dcd0d607c78b48dc3f007c462df3be96d517f7c177f32` |
| Joined platform runtime C | 527,651 | `2802449c8d31a26a6cffe17fc33a7964e11231d0d892efc1730797f5c48ea34a` |
| Renderer C | 73,678 | `ed74ed108e6cc9c46747b762cec5a5938e44db6f2f48152a3281775846e73448` |
| ARM64 init | 149,344 | `401ca9cb86d7becc907f4ee42a6b3df6af9332bbc92d7eef2728e990bf8a26d4` |
| ARM64 renderer | 778,968 | `b3d08ae8cf523ed53911e436c5f90fde74585b2aa2585c939b7cf7538e37caca` |

The frozen P383 identity/key is only an H0 comparison input. Keyed sources and
compiled files remain private. No image is rebuilt or packaged. The harness
checks 16 direct source inputs, its own source, the supporting 1A H0 helper,
348 historical source inputs and 187 toolchain inputs. It verifies the exact
default platform source remains unchanged before selecting the local profile.
All 86 consumed prepared execution-source receipts were separately rechecked.

Private evidence root: `workspace/private/outputs/s22plus-native-refactor-phase1b-20260910-1/`.
Final component result: `build-5/result.json`, 7,237 bytes,
SHA256 `9c999546219ab6a5a4b7ff91af57772776bf824fd5b8d93301a7ed0a59234726`.
Final suite logs are `local-tests-final.log` and `default-equivalence-final.log`;
`historical-source-preservation.json` records the unchanged consumed inputs.
Earlier H0 compilation/fixture failures and superseded build results remain
private. They involved a missing harness child-source input, newly unreachable
publication helpers, fixture naming/bounds/formatting and a buffered fixture
success marker. The final actual production builds and all tests pass.

## Independent review and remaining scope

Independent review identified and resolved the moved-start frame/log capacity,
boot-ID error classification, final authentication admission deadline and H0
supporting-source binding. Final disposition is **PASS_GO**, with no remaining
actionable finding. The reviewer independently passed 11 selected tests in
3.558 seconds, including real ARM64 getpid/fork, owner/expiry, both corrected
failure boundaries and both production-C backpressure cases. It rehashed all
16 direct inputs, supporting oracle, harness, 348 historical inputs, 187 toolchain
inputs and 86 prepared sources, regenerated both source joins, and verified both
compiled component sets. These 11 checks overlap the parent's 42 tests.

| Approved input | SHA256 |
| --- | --- |
| 16-entry source-inputs JSON | `2f3f1b3bed9202867905d584a0b618bf1ede0eaf53ddda8e1f0e7acc6e4c5413` |
| Direct generator | `dd5b6d3c6057331b48462e9e6b1f7fe01c0f7ad08556cdc513a43bd84b0c598f` |
| Local H0 harness | `12591949edc5b8c3cbbb7117693427848b59b23561c937936dc1b084c7806282` |
| Local test suite | `85945ca412cff9c43dd446aea23391443a42cbf876bff5a2b1442ab30fc9b090` |
| Production test adapter | `bd7332f912900511c562c9988d595585ab50c07dbaa0cb1c6fcb52dc66459417` |

Touched Python compiles; scoped document links/fragments, repository boundary,
private identifier/key exclusion and whitespace checks pass.

This completes phase1B implementation, H0 validation and independent review. The separate host USB
arrival race remains unrepaired. Live profile/observer adoption, new candidate
qualification and any attended device run are separate future work under the
existing contracts. No second P383 native boot or automatic recovery claim is
promoted by this refactor.
