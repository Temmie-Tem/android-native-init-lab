# S22+ native baseline V1 capability qualification

Status: **Live bootstrap NATIVE_CLOSED; exact P385 admitted; grant consumed and closed.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**.

The [native baseline V1 policy](../operations/S22PLUS_NATIVE_BASELINE_V1.md)
defines a separate finite attended owner for P385 / v0.2.0-rc.3. It can retain a
healthy native terminal and later restore the same admitted image, with exact
Android exit or fallback. The implementation and host qualification are new;
P384's completed roundtrip and consumed claims are unchanged. At H0 completion
there was no P385 device grant, transfer, live qualification or admitted native
baseline. The separately attended 2026-09-11 qualification below now establishes
the exact admission, with the original grant closed and no standing authority.

The common contract incorporates only this exact reviewed exception to ordinary
content-keyed no-repeat and mandatory Android cleanup. An ordinary experimental
candidate remains one-shot. A baseline's original installation claim stays
consumed, and each later role has its own durable one-shot intent. One grant
allows at most three reservations and 600 suspend-aware seconds. Bootstrap uses
two declared N roles within one reservation. Every reservation has one shared
exact A exit/fallback role. A native or session failure stops research and never
authorizes another N role.

## Implementation and evidence limits

The direct `native-baseline-v1` C profile allows clean DETACH followed by fresh
same-boot authentication. It retains boot preparation, rejects every previously
used nonce, and keeps the original eight-authentication/900-second boot limit.
The host closes and reopens the actual descriptor, obtains exclusive access,
revalidates its exact endpoint, and reopens the complete authenticated raw
stream. A healthy native terminal requires the final DETACH ACK, actual close,
remaining admission and remaining original time. It is a bounded health
snapshot, not a future responsiveness or automatic recovery claim.

The present-native guard uses the existing target/lane/ModemManager machinery
and requires both current ignore properties on the exact tty. Missing properties
stop before authentication; cleanup grants no protection between operations.
Host grant, native lifetime and wire-write checks count host suspend. Recovery
reopens durable role state and can finish reporting or Android health without
repeating a transfer. The ordinary Process-v2 terminal graph and P384 runtime
defaults remain unchanged.

Real generated C, renderer, PTY descriptor close/reopen, protocol/HMAC/raw
readers, archive parser, owner/registry, Download observation and D0 consumers
are exercised in H0. Root/mount/UUID, physical hardware, USB/Odin/ADB and small
test archives are explicit fixtures. Separately, the production candidate is
built as static AArch64 code, its A/B APs are byte-identical, and the actual N/A
archives pass their production readers. No new native numeric syscall flags
were introduced. H0 does not prove the target's new runtime, current privileged
guard startup, physical display pixels, unattended recovery or live admission.

## Retained production artifacts

The final private candidate is under
`workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.3/candidate-build-verified-v2/`.
The earlier build remains retained and is not the selected image.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| P385 A/B boot-only AP | 31,150,121 | `32bf9eef176e14a979a8031b0ba2073f88369745a2b07a5bf605e1b70e3ba03b` |
| Sole `boot.img.lz4` member | 31,141,676 | `f248b4808a5b5a603f3d7ea828174b1b13c82231e1add60d6dffaf343997d184` |
| Native init | 149,864 | `74ea230b8b95d0c95e6e380a8d1b936346773869b85255d2e8c51a541694d77f` |
| Exact Android A | 23,367,721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |

The current source-qualified H0 bundle is under the same version's
`h0-review-bundle-final-v1/`. Its 160 execution sources and actual 165,324-byte
request layout pass the real producer/consumer. The serialization probe has an
unbound fixture target and no review authority outside the permitted grant root;
it is not an approval request. The current root contract bytes are retained
privately. Its pre-existing S20+ registry/recovery-note edits remain outside this
unit's staging; only the new details digest belongs to this root change.

| Private H0 record | Bytes | SHA-256 |
| --- | ---: | --- |
| `candidate-static.json` | 62,709 | `c683af027f00ddfdabed7a2a8fd4a0a1c485f4cfe836e45ae871cf21555aabfe` |
| `execution-closure.json` | 49,793 | `e4eb2920484ac1e58c4170c9a9ba9a43c0798fbdfec0a4dbcaf2115dc380dbd0` |
| `review-manifest.json` | 9,479 | `427240a350ff2083b3c947363188b29dadd40a173bc8f77989f2d47f2f9f7981` |
| `result.json` | 33,958 | `7a13aefeeefd212946806ecba1c967d8a01e231e246f0bad5a0dc7a14fabb8f7` |

## Validation and review

The final 11 owner/backend tests pass, including a complete bootstrap, native
restoration and native-origin Android exit; health/nonce/boot/transfer failures;
21 cuts around N/A intent, delivery, result and terminal publication; interrupted
lane/phase/final-health preparation; original claim retention; uncertain A
without replay; wrong approval, attendance, host epoch and elapsed grant;
different physical target rejection; zero-byte pre-AUTH/pre-write expiry; and
the exact one-MiB writer/reader boundary. The final 27 shared-wire, P384 observer,
P384 roundtrip, new protocol and retained-guard tests also pass, as do all 24
touched Python compilations and 12 repository-boundary regression tests. Earlier
source equivalence and shared CDC/P324/P325 guard checks also passed; the final
runs cover the later owner/protocol changes. Private `parent-validation.json`
retains the final test logs. Both the working-tree boundary check and a scan of
all 14,841 selected index text files with the same detector pass. Scoped diff,
Markdown links and the common/root incorporation digests also pass.

Independent **PASS_GO**, with no findings, covers the exact capability and its
common/target interaction. The reviewer revalidated all 160 current sources,
the actual production bundle and all 112 native byte inputs, the real fixed-key
reader through the P385 factory, the full request writer/reader, the joined owner
and publication cuts, and retained-guard lifecycle negatives. Its canonical
source-map digest is
`113b447c4405647c2bba1c9b434a7e4a8525b4c43b610c86c7e70fa1ba4909e5`.
The [capability review](../../workspace/public/src/device-action/bindings/s22plus_native_baseline_v1_review.json)
records the exact source receipts and permanent limits. A private identical copy
is retained as `independent-review.json`. The review starts no privileged helper,
opens no grant and grants no live native admission.

The first live proposal bound only bootstrap, one reservation and 600 seconds,
its exact P385 N and Android A, the reviewed source closure and private physical
target. The operator separately returned that approval under the proposal's
current attendance/physical Download condition. A90 and S20+ received no device
action in this work.

## Attended live bootstrap on 2026-09-11

The exact proposal `p385-bootstrap-20260910-1/request.json` is 165,563 bytes,
SHA256 `de858ef356895812becc6d65a22a65b63353083defbb363464016c23367a1928`.
Its returned approval opened one 600-second grant against execution commit
`bed168e00e`. The current common/policy/review pins and all 160 execution sources
matched. The previously demonstrated P384 Android recovery remained closed;
this invocation performed a fresh exact-target rooted FYG8/original-hash/Android
health check before its first Download request.

The reviewed owner completed its original invocation without a recovery call:

- **First N:** one exact boot-only transfer, two authenticated fixed native
  health checks, clean DETACH and actual close/reopen, same kernel boot identity,
  distinct nonce, cached second preparation, then accepted Download CONTROL.
  The exact Download arrival was inside the original 30-second return window.
- **Same N restoration:** one separately intended normal transfer followed by
  a different kernel boot identity. Both fresh authentications qualified health;
  clean DETACH and actual close/reopen proved same-boot reentry. The final
  DETACH ACK and actual descriptor close completed without a further CONTROL.
- **Terminal:** `NATIVE_CLOSED`, `recovery_required=false`, no research stop,
  exact native admission published, original installation claim retained and F1
  owner released. The one-reservation grant is consumed and closed. Android A
  remained available; no A transfer or post-native Android-health claim occurred.

Each boot has two successful authentications and one physical descriptor reopen.
The first observation took 28.394 seconds and the final observation 18.386
seconds. Each optional HUD acquisition returned seven valid frame records,
matched flips, four fresh gauge samples and four fresh memory/CPU samples.
Physical pixels remain unproved. The fixed native health and terminal proof are
independent of those supplemental display observations.

Six authentication slots and **893.438 seconds** of the original native lifetime
remained at final descriptor close. The terminal explicitly has health scope
`past-authenticated-native-snapshot`. It neither refreshes that time nor proves
later responsiveness. A new native-origin owner and its present-native guard
remain H0-qualified but have not yet run as a separate live operation. Any later
normal restoration or Android exit needs fresh finite authority/current binding;
an expired native may use only the separately authorized physical-Download A exit.
Unlimited service, automatic stall recovery, persistent data work and a v0.2.0
release are not established.

### Canonical event order and normal restoration

The eight ordinary event names are retained below. Their Android rollback events
are unused under this native-terminal exception; the same-N restoration has its
own linked role. Times shown are observed immutable host-record mtimes for
orientation. Effect order and acceptance come from the journal, role records and
authenticated raw proof, rather than native timestamps inferred from those mtimes.

| Event | Host record mtime, UTC on 2026-09-11 |
| --- | --- |
| `live_session_start` — operation reservation | `05:55:45.007324` |
| `candidate_flash_start` — first N intent | `05:56:01.909231` |
| `candidate_flash_done` — first N result | `05:56:03.684221` |
| `candidate_boot_ready` — first qualified observer record | `05:56:33.680057` |
| Linked first normal Download return | `05:56:40.635019` |
| Linked same-N restoration intent/result | `05:56:46.764985` / `05:56:48.548975` |
| Linked final qualified native observer record | `05:57:08.643865` |
| `rollback_flash_start` | Not used |
| `rollback_flash_done` | Not used |
| `rollback_boot_ready` | Not used |
| `live_session_end` — native terminal/completion | `05:57:08.970863` / `05:57:09.587860` |

### Terminal evidence and retained-reader validation

Paths below are relative to private operation
`workspace/private/runs/s22plus-native-baseline-v1/p385-bootstrap-20260910-1/operation-01/`.

| Record | Bytes | SHA-256 |
| --- | ---: | --- |
| `android-start/health/result.json` | 3,308 | `bc3bb8d129a34be483297996294b6b86f39862d7756b5ef648a7207a0d56ef7a` |
| `bootstrap-first/native-baseline-attempt-01.result.json` | 2,188 | `6eb8fea53c23abc2959c5376da70c919b816ed9b6990873f1d4d23274b5d56fe` |
| `bootstrap-first/candidate-observer.json` | 60,068 | `d0d27bbee5b47a5da4e6b640f4fa0c169647d612095943e896803fde815da217` |
| `native-final/native-baseline-attempt-01.result.json` | 2,179 | `f7e5bc51602a147be4019fa3e89a053216be2e8181777007b04a649ba3a0c444` |
| `native-final/candidate-observer.json` | 59,407 | `076b7abb99d408172ec9e9846e0597e1f6425d7b756fc378dd15ffca14f4301c` |
| `terminal.json` | 32,489 | `8d3f51f8f6b1200bb7b918bb7d13c295233171bbf1debfde9f6de34d480ec68b` |
| `completed.json` | 611 | `efd888dd9a75af5c6ca7474e836bf8b1ffe0069453608664b5555ad8eb5a37dd` |

Unchanged `load_operation`, `validate_terminal` and `admission` reopened the
complete raw health/reentry/close proof and native qualification. They also
confirmed the consumed installation claim, exact completion, released F1 owner
and closed grant. No descriptor was opened or command sent during this retained
validation. Private `h0-review-bundle-final-v1/terminal-reopen.json` records
`PASS_P385_NATIVE_BASELINE_LIVE_TERMINAL_REOPEN`, 3,083 bytes, SHA256
`ae7af1cdf86486580a0b3a43dfbe6f3ad92186c0e935f719568150fcdcdc4350`.
The exact admission is 21,351 bytes, SHA256
`76e3aa54a862f534937de58f05bd6dd9a62ed74d399f72337cb242cec8aef9b5`.
Original invocation output and host/source/approval context remain private in
`execute-1.log` and `execute-host-context-1.json`. An initial H0 context-reader
field lookup was corrected from `state` to the actual `current_state` before
grant creation or any device command; production sources and prior evidence
were unchanged.

The ledger records the distinct `NATIVE_BASELINE_CLOSED` action with ordinary
installation/Android counters **1/0** and the separate same-N restoration stated
explicitly. Its older ordinary-Android terminal classifier does not classify
this new native close; the native owner's terminal/admission above is the
authority for its completion. The pre-existing full-ledger row-547 taxonomy
failure remains separate. No historical row, consumed source, approval or
terminal record is rewritten for reporting.
