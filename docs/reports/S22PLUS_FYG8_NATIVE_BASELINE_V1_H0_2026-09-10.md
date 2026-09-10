# S22+ native baseline V1 capability qualification

Status: **H0 capability PASS_GO; no live grant or admitted native image.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**.

The [native baseline V1 policy](../operations/S22PLUS_NATIVE_BASELINE_V1.md)
defines a separate finite attended owner for P385 / v0.2.0-rc.3. It can retain a
healthy native terminal and later restore the same admitted image, with exact
Android exit or fallback. The implementation and host qualification are new;
P384's completed roundtrip and consumed claims are unchanged. No P385 device
grant, transfer, live qualification or admitted native baseline exists.

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

The first live proposal will bind only bootstrap, one reservation and 600
seconds, its exact P385 N and Android A, the reviewed source closure and private
physical target. Opening it requires the separately returned exact approval and
actual attendance required by the policy. No old P384 grant is reusable. A90
and S20+ received no device action in this work.
