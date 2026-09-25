# S22+ P405 installed Debian successor — H0, 2026-09-26

## Bounded unit

P405 `v0.4.0-rc.5` prepares one fresh installed-root handoff after the closed
P404 run. The operator requested continuing through preparation and the next
physical experiment. This report records preparation separately from any live
grant or result. The installed P401 root, FYG8 kernel, board module order,
restricted SSH vocabulary, P399 normal return and original-A physical fallback
are retained. P401 installation and the P404 candidate remain consumed.

The [P404 audit](S22PLUS_DEBIAN_P404_NCM_AUDIT_H0_2026-09-26.md) proved a host
selector false negative when the Android USB path was absent. The corrected
selector already checks the other declared path. P405 adds bounded private
host USB diagnostics and an authenticated candidate-specific RAM bootstrap
record. Neither change establishes P404's actual failure cause.

## Implementation and checks

During the existing 180-second wait, the observer captures at most 180 samples,
each at most 32 KiB. It reads only the two fixed USB paths and their associated
interfaces, preserves field bytes before parsing, and separates absent USB,
missing network interface, read failure and identity mismatch. Interface
enumeration and field lengths have fixed bounds. The existing exact selector
independently determines endpoint acceptance; a diagnostic match is never
Debian health proof. The full reachable import closure includes the observer.

The fresh init prints its P405 namespace/version and run identity into the
existing RAM bootstrap log. Authenticated health must contain that exact marker
once alongside the installed-root and initial PID 1/handoff proof. This is an
executed witness, not a renamed old image. The physical AP differs from consumed
P404. It still contains no root archive or installation manifests, and the
P401 compile path remains byte-identical with installed-only selection absent.

The bootstrap checks clean ext4, exact native_data/GPT, installation markers,
witness and root metadata/content before any writable handoff. P404's Android
closure is pinned as predecessor evidence, not as proof of current native_data
health. Dirty or mismatching storage stops without repair or installation.

The physical A/B AP files match. ARM64 cross-compilation and ELF inspection
pass. A real ARM64 virtual boot authenticates installed Debian PID 1/SSH and
the new candidate marker, then completes orderly shutdown. An empty-root
negative stops before handoff/install and leaves its backing disk unchanged.
The virtual board still substitutes Ethernet for physical Samsung USB; it
does not prove NCM or hardware initialization. Actual physical AP readback
verifies the kernel, ramdisk inventory, marker and shutdown-command/VM join.

All 60 focused Debian tests pass, including 12 raw diagnostic cases, 10 endpoint
selector cases and the 38 owner/effect/recovery tests. Malformed and oversized
fields retain raw evidence before rejection; unrelated interface identities
are not collected; inventory overflow cannot yield a successful projection.
The health parser rejects a marker from another candidate.

## Selected private artifacts

Base: `workspace/private/outputs/s22plus-debian-installed-h0-20260926-1/`.

| Input | SHA-256 |
| --- | --- |
| `build-1/artifact.json` | `640670965fb08834f252f0c76d6f0d3bc9057537a614ca5d9a559a89cc483ed7` |
| `build-1/pack-a/AP.tar.md5` | `55bf908b0c1ec3bce4cf9181dd33cbbc2b938874239d77ba2197359609fd6fbe` |
| `vm-1/result.json` | `d235994e9a77fcffe82a05b36e4c27b971963f34794a70374cf8051e5a74f6cd` |
| `qualified-1/qualification.json` | `8e135132db6399a6ce5fc38f6676a61b3cfc538f29656c8f04de8387f49fafb6` |

P405's live source review uses a separate receipt path; P404's review bytes,
source snapshot, journal and receipts are not overwritten. The common and
target definitions select only this fresh successor's finite attended unit;
physical recovery and every no-replay boundary remain in force. Independent
review, current exact target/health and the concrete attended grant must all
be valid before device effects. Preparation alone opens no grant.

The independent reviewer returned **PASS_GO — REACHABLE_OWNER_AND_BOUNDARY**
against all 63 exact source receipts in `review-request-2.json` (SHA-256
`ce229dc70403dfcdfc49009a05fa1e8170c3afb7207d0f53178590493533d323`).
The separate [P405 review receipt](../../workspace/public/src/device-action/bindings/s22plus_debian_installed_boot_p405_review.json)
has SHA-256
`933f97a6cf7b7e6b38a658bdf34009fb490ce0b1546b33bb34eac0e06409441f`.
The reviewer independently passed actual AP readback, all 60 focused tests,
four additional observer/selector separation cases and retained VM raw proof.
The common details digest matches AGENTS Revision 31. Repository-boundary,
selected local-link and diff checks also pass. This qualifies the capability;
it does not establish current device health, attendance or a run outcome.

## Concrete preparation

`live-task-1/plan.json` is the single 3600-second proposal, SHA-256
`d7242e0d10ec6f8a6c6f90b315f55e833ea35dd96825649c1d1d4c78fc06370c`.
The global F1 owner is absent and the new candidate is unconsumed. All 63 actual
execution sources were saved before effects; `source-snapshot.json` SHA-256 is
`c23a5c3849bba70d5280050907d21e95547a3b9bba80e3d896c41b477edef49e`.

The fixed foreground D0 bracket proved current exact rooted original Android,
original partition hashes, full GPT and 34,357,624,832-byte Android32 capacity.
The first complete inventory read returned ADB server-startup stderr and was
rejected by the strict consumer. Its raw evidence remains under
`pregrant-android`; a separate allowed read-only `pregrant-android-r2` bracket
passed. The successful `pregrant-android.json` SHA-256 is
`37f1dbe8843e30baaa320a9d8c344dad03f8118386bc53233b437e73ee8b762b`.
No transition, transfer, finite grant or F1 owner was opened during preparation.
Actual attendance and the concrete finite start remain necessary for execution.
