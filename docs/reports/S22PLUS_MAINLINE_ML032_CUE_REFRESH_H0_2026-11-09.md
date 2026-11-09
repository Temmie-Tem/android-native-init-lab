# S22+ ML032: attach-census ordering repair and fresh dwell/link candidate

The caller now selects the latest sealed USB census after its expensive final
owner/source/artifact guard. A new ML032 candidate has been built and qualified
in H0 for the same five-minute witness and bounded UFS-link experiment.
[Exact prospective scope](../plans/S22PLUS_ML032_CUE_REFRESH_DWELL_LINK_SCOPE_2026-11-09.md)
is not adopted for device execution. Independent review returned **PASS_GO**
with no open findings. No device read, transfer, control, approval or grant
occurred.

## Defect and narrow correction

[ML031](S22PLUS_MAINLINE_ML031_RUN_2026-11-09.md) ended without an attach cue,
first response or UFS permit. H0 reproduced the latest-census refusal when
another identical absence record arrived during the expensive second guard.
The exact selected ordinals of the two live failures were not retained, so
this is a demonstrated reachable defect, not a complete reconstruction of
their individual comparisons or a diagnosis of the phone's boot behavior.

Both existing guards still run. After the second, the caller rechecks the
journal and forbidden states, selects and parses the newest complete census,
then rechecks state, latest path, selected raw integrity and the strict
remaining-time boundary. The final latest-path assertion is retained: a newer
record at that point refuses, including one that might indicate device arrival
before endpoint selection. No older-absence fallback, retry loop, new observer,
lease or window extension was added.

CLI refusals now retain the failing phase and available selected/latest
census paths on stderr. A post-publication error never removes the cue or
proves non-delivery. Future prepared invocations must capture stdout, stderr
and exit status in fresh private files before parsing; actual operator replies
still supply completion/cancellation before a separate Download instruction.

## Focused caller validation

All 26 focused tests passed. They exercise the real raw-transfer consumer and
attach interlock, strict census grammar/topology, failed or changed raw data,
endpoint/request/return/stop races, the 60-second boundary, duplicate issuance,
late publication and resolution. Added cases distinguish census advancement
during the guard from advancement or tampering during the final short check.

Two tests run the actual fixed sysfs reader and RawCaptureWriter periodically
against private fake sysfs while the second guard waits through multiple
publications. With absence, exactly one cue is published while that producer
remains running. With a newly present parent but no endpoint file, issuance
is refused. A further actual-publication test injects a CLI display-window
exception: stdout stays empty, stderr records the phase, exit is 1, and the
original cue remains without resolution, closure or another issue call.
These fixtures do not prove live scheduling latency or physical USB arrival.

## Fresh artifacts and protocol evidence

The unchanged recipe generated fresh physical and VM keys and identities,
different from both ML030 and ML031. Complete reproduction with the saved keys,
seal and original inputs matched both observers and canonical CPIO archives.
Image, DTB, fixed module and four signed Debian packages retain their reviewed
bytes and provenance; no kernel rebuild or changed hardware scope was needed.

The new loader passed 20 actual ARM64 cases, 1,051 aligned-copy cases and actual
QEMU EL1/EL2/EL3 checks. Two independent boot/AP packages match. Offline
unpacking joins their single boot member to the exact loader and embedded
Image/DTB/archive. The current live image validator rejects the unknown ML032
AP before admission. That expected refusal does not authorize a bypass.

| Fresh ARM64 case | Guest uptime, seconds | Result |
| --- | --- | --- |
| Actual host collector, emulated UIC and modeled power | 1.952 to 302.098 | One emulated link, result-bound Download and QEMU reset |
| Actual host collector, physical module on QEMU | 1.724 to 301.878 | ENODEV; no normal Download control |
| Early second challenge | Original window | ETIMEDOUT; no module result or Download |
| Invalid late module permit | After dwell | EACCES; no module result or Download |

The first two host gaps after sealing the first responses were 300.014 and
300.018 seconds. The positive fixture explicitly models power and traces one
emulated link with no SCSI command. It does not prove physical g0q power, UFS,
five-minute survival or Download. Unchanged lower-level PHY/RPMh evidence is
reused through exact retained bytes and review provenance.

## Evidence and remaining boundary

Private evidence is under
`workspace/private/outputs/s22plus-mainline-ml032-cue-refresh-h0-20261109-1/`:
the before snapshot, recipes, complete producer reproduction, loader/EL/package
results, four VM cases, sealed raw captures, caller test logs and
`qualification-1.json`. Changed Python passes `py_compile`; content/link/diff
checks cover the documentation. No live binding, policy, bridge selector or
worker was changed. ML030 and ML031 remain consumed and healthy-closed.

Applicable past-failure concerns are HOST/ROUTE (actual caller and periodic
producer), RETURN (unchanged one-shot interlock and recovery ownership),
WIRE/SEMANTIC (fresh host/guest proof and model limits), ARTIFACT (full producer
and embedded-byte joins) and PERSIST/AUDIT (failure diagnostics and preserved
consumed records). New ABI, storage and device-hardware changes are inapplicable.
No unrelated diagnostics are prerequisites for this bounded capability.

## Independent close

The final review binds input SHA-256
`a9e9393d723a48f0656315281b062a7ea00aeb9a39206f3e649f76d11f026cdc`.
Its result at `review/independent-review-1.json` has SHA-256
`f05a06429e00e2583dc9648b7a4ca803fae0f847d4aa1e23e31fb4be836481b8`.
The reviewer independently verified three changed-source pins, six authority
inputs, 69 evidence pins, 32 sealed raw captures and all four guest cases.
Actual ELF symbols and both APs joined the embedded artifacts and retained
original-A outer ramdisk, signature and trailer. Actual EL1/EL2/EL3 raw proof,
new keys/identities and complete producer reproduction were rechecked.

The reviewed cue source differs from the old normal capability's source pin,
so that normal capability correctly refuses it. The unchanged recovery
capability and V35 bridge still validate. No old review was repinned. The
63 protected consumed records and 11 unrelated work files remain unchanged.
The review's supplemental QEMU-file check initially used a session-record pin
function that rejects a hard-linked binary. The failed check is retained; the
corrected check uses the entry qualifier's existing byte-hash semantics.
No production assertion or artifact was changed to obtain the review result.

ML032 needs its own common/target scope adoption, exact admission and current
owner/bridge review before a live task and finite attended approval can be
prepared. H0 success supplies neither live authority nor device proof. A90 and
S20+ are untouched.
