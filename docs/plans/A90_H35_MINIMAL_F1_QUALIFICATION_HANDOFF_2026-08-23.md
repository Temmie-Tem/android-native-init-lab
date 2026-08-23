# A90 H35 minimal F1 qualification handoff — H0

Target: operator-owned Samsung Galaxy A90 5G only

Authority: none; no D0, approval, F1, transfer, reboot, rollback, or live effect

## Review subject

Request one independent public review of
`docs/reports/A90_H35_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-23.json`.
The frozen input is 6,607 bytes at SHA-256
`1f70b880b482db50b3347102ad60f911bf9f28d07434db5adc06abf061dfff7a` and
binds the current minimal-F1 owner closure
`455c486c3e4da2ec07b4ccf674c69625a4eb9661ae30c89924ab5f2c3363c0c8`, H35
`0.11.202 / phase3-minimal-h35-public-mpgen-rtic-canary`, exact V2321
rollback, fresh H35 state, aggregate H1-H6 hazard, and first-opportunity
failed-boot evidence. The input is frozen with
`PENDING_INDEPENDENT_REVIEW`, a null verdict, and `liveAuthority=false`.

The current reusable continuation review is
`docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json`, 577
bytes at SHA-256
`22fba68f002bf7e35b9e15d1b12cfed906e33de4bd1a0e56982bcc78f4acd120`, with
closure
`981a3f06ce38a288a8ab9c5ef76234bc38c97b51359fd2f46bfb4ed714d7ae3d`.
The current reusable postrollback review is
`docs/reports/A90_F1_POSTROLLBACK_RECOVERY_CURRENT_REVIEW.json`, 467 bytes at
SHA-256
`20aaed0b4e3d7aefb940c06db421a55b9113dcc7bf2cc9e074a36328ebf3e9a0`, with
closure
`148525430a5cd9f875df4cb39766c6c72a8093f2155ea1bc6e312aea8f45cf5d`.
Both are current `PASS_GO` reviews with zero contacts/findings and
`liveAuthority=false`; they are reusable capability reviews, not H35
authority.

The H0 evidence reviews are also bound but do not substitute for this fresh
candidate review: the aggregate hazard review is
`d180b3637bb36eefce7c28251a8c17ddb73393068135b4dff16972e5f86a8c94` with
verdict `PASS_GO_H0_CANARY_HAZARD`, and the package review is
`843524b45415ef09d1c311ecf88bdb3243b32c65f01a781bb167cbd8a56ec397` with
verdict `PASS_H0_PACKAGE_GATE`. Both are H0-only and `liveAuthority=false`.

## Required independent output

Write only the exact canonical UTF-8 JSON bytes for the future public review
at
`docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H35_INDEPENDENT_REVIEW_2026-08-23.json`:
no trailing newline, duplicate keys, extra keys, or semantic JSON aliases.
The owner-compatible schema is
`a90-boot-only-f1-minimal-independent-review-v1`, with this exact canonical
top-level key order and binding:

```json
{"candidateSha256":"5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759","capability":"A90_BOOT_ONLY_F1_MINIMAL_V1","contacts":{"dev":0,"device":0,"network":0,"otherTargets":0,"usb":0,"workspacePrivate":0,"writes":0},"executionClosureSha256":"455c486c3e4da2ec07b4ccf674c69625a4eb9661ae30c89924ab5f2c3363c0c8","findings":{"high":[],"low":[],"medium":[]},"freshState":{"enablePath":"/cache/a90-auto-handoff-phase3-minimal-h35.enable","latchPath":"/cache/a90-auto-handoff-phase3-minimal-h35.done"},"hazard":{"accepted":true,"id":"A90_H35_PUBLIC_MPGEN_RTIC_CANARY_H1_H6","statementSha256":"460afc03331024a79d051cb3a55ba878ae65f83610c1405d4a03671e4e3dd6c8"},"liveAuthority":false,"recovery":{"demonstrated":true,"method":"NATIVE_TO_STABLE_ADB_BASELINE_SINGLE_NEW_RECOVERY_ARRIVAL_BOOT_READBACK_V1","profile":"A90_ATTENDED_PHYSICAL_RECOVERY_V1"},"reviewDate":"YYYY-MM-DD","reviewer":"PUBLIC_INDEPENDENT_REVIEWER","rollbackSha256":"ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb","schema":"a90-boot-only-f1-minimal-independent-review-v1","scope":"A90_MINIMAL_BOOT_ONLY_F1_EXECUTION_AND_CANDIDATE_HAZARD","targetProfile":"SAMSUNG_A90_5G","verdict":"PASS_GO"}
```

`reviewDate` and `reviewer` must be the reviewer's actual bounded values, not
the placeholders shown above. `contacts` must retain exactly the seven
integer zeros, `findings` must retain exactly the three empty arrays, and
`liveAuthority` must be the JSON boolean `false`. The review may qualify only
the exact H35 capability bytes and leaves candidate, D0, F1, approval, and live
authority absent. A later `PASS_GO` is not an approval token.

## Fixed limits and deferred boundaries

H35 remains one future attended boot-only Native-health canary with exact
V2321 rollback. current V2321 health is unproved and must be freshly established
by the later target-bound D0 process; physical recovery identity remains private
and unbound in this public packet. The private manifest, run ID, recovery serial,
D0, approval, F1 intent, journal, transfer, reboot, and live authority are
absent here and remain later steps. No device, `/dev`, USB, ADB, network, or
private-file contact occurred in this H0 preparation.

The failed-boot channel is limited to the first opportunity before
journal-bound rollback/recovery: read-only TWRP `/proc/last_kmsg` and
`/proc/cmdline`, with no mount and a 60-second total bound. Evidence absence is
`NO_PROOF_OBSERVER`; it never permits candidate replay and cannot specifically
attribute a boot failure to RTIC. H29-H34 are consumed and non-replayable.
No Debian, Wi-Fi, external-module, Android, stock-equivalence, or
production-stability claim is made.
