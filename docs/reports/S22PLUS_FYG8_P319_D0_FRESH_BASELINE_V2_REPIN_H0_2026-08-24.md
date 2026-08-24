# S22+ FYG8 P3.19 D0 fresh-baseline V2 consumer/reducer repin

Date: 2026-08-24 KST

Status: `P319_D0_FRESH_BASELINE_V2_REPIN_IMPLEMENTED_REVIEW_PENDING`

## Result

The reviewed D1 V2 capability is now consumed by a separately versioned H0 D0
producer and reducer design. The new producer is 72,288 bytes at SHA-256
`e1190b66a31ee674d9f0bf64726fbf8a5edb55d81e7910b07b6f4b0f46009d0d`;
the new reducer is 54,126 bytes at SHA-256
`ea72adab0690b2c2e52e15829a7a98632ef59b7e36d77f8a29a9db6e532f6ef3`.
Their canonical review-pending execution binding is 14,251 bytes at SHA-256
`bda6b82d9689b8968edc9cd2b7b0190c75bef9629b3a3f24443e7096ebb7cd55`.

The binding fixes `d0-p319-fresh-baseline-2`, the V2 schemas and authority
prefix, exact target/profile/current 437-source/73-module/EUD38/latch-only
candidate identity, reviewed D1 V2 source `66357B/9443c81c`, reviewed D1 V2
binding `5351B/65e2953e`, common raw-first runtime, complete adapter graph and
exact host ADB. The historical D1 V2 review-pending binding
`5300B/917daa02` is recorded only as an unconsumed predecessor.

The future authority format is
`DEVICE-ACTION-D0-P319-FRESH-BASELINE-V2-APPROVE:` followed by the complete
binding digest. This is a format, not a current approval. The binding remains
review-pending.

## Exact D1 V2 consumption

The reducer stable-reads the exact D1 V2 source and pass-go binding before
compiling only those pinned source bytes. It then runs the D1 V2 source's own
`_validated_static_inputs`, `_validated_execution_inputs`, `_result_complete`,
selection and raw-inventory validators and performs post-load stable reopens.
Acceptance requires the fixed `p319-fresh-baseline-2` result path and namespace,
exact execution-manifest and approval digests, direct arm/start receipts, exact
ADB snapshot, complete raw-handle inventory, distinct before/after boot IDs,
typed selection, one reboot and every zero-effect/no-replay flag. The reducer
reopens the fixed raw namespace and requires canonical equality with the
result's `raw_evidence`; a summary boolean is not authority.

A V1 D1 result, the consumed V1 stop, or a V2 stop is not an alternative input.
Schema, fixed path, journal, namespace and exact validator checks reject each.
Extra entries, hardlinks, symlinks, receipt replacement and identity drift fail
closed. The D0 producer never writes or traverses the D1 V2 namespace.

## Version separation and inherited contracts

The previous D0 producer, reducer and binding remain exact evidence:

- V1 D0 producer: `71975B/c1a7f82f`;
- V1 reducer: `64375B/2729426d`;
- V1 D0 binding: `14240B/34203813`.

The V2 producer retains the reviewed V1 raw-first acquisition, nine-handle /
27-child inventory, typed stop, no-clobber, cut-state and namespace semantics,
but all producer, D1/D0 journal, result, binding, version and ordinal literals
are V2. The remaining `v1` names are intentional common inputs: current
candidate intent/qualification schemas, `device_action_raw_capture_v1`, the
existing raw-ADB inventory ABI and the stock-witness Carrier contract. Tests
freeze this distinction.

## Current fail-closed state

There is no `d1-fresh-baseline-2` arm, start, result, raw namespace or ADB
snapshot. Consequently there is no V2 D0 approval, arm, run, stop or result,
and no normalized `fresh-baseline-v2/result.json`. The H0 self-test records both
the D1 V2 result and fixed D0 result as absent. Integration consumes only the
V2 reducer/path and still returns exactly `FRESH_BASELINE_MISSING`, with ready
and live authority false. No public candidate, ready or run manifest is made.

## Permanent raw-first and prerequisite evidence

The V2 D0 producer is the 18th active raw-first source; V1 remains the 16th
active predecessor and D1 V2 remains the 17th. The raw auditor is 68,231 bytes
at SHA-256 `0cfd391b2ca26ddd8f51cac9fe2b7fcb14daaeba5985d4541e8b08354e9c0487`
with normalized self-hash
`0aa0a9b10ce55cd0f33b2a23a13e8b06e5ed7ee5d0ec25e298df5d53bbc9f24a`.
Its census is `1742/412`; S22 pre-boundary `128/fcb3bb80` and target-external
52 remain unchanged. The no-clobber `-06` receipt is 12,916 bytes at SHA-256
`66658f6739b8e0116209a13de3fbb2255b040fa68b0ee7bb34c7cb51876207ec`,
mode `0400`, link count one; `-05` and every predecessor remain byte-preserved.

The prerequisite auditor is 45,258 bytes at SHA-256
`8ba7a3312f2a978941d578a2dd06d489a6242d232e0aa7cd33d7b3c26b9b3223`.
Its no-clobber `process-v2-prerequisite-audit-20260824-06.json` receipt is
12,528 bytes at SHA-256
`7a5a824893dc40d2f284d6e719bad0d7e56ff92c358ddc921711fa46ef6955d0`,
mode `0400`, link count one. The V2 integration source is `51990B/e35e2e81`;
its deterministic blocked receipt is `61379B/49745fc2`, mode `0400`, link count
one. All three current artifacts are H0 and authority-free.

## Validation and boundary

The V2 producer hostile suite passes `29/29`; the V2 reducer/D1 authority suite
passes `11/11`, and the integration qualification adds `14/14`, for focused
`54/54`. Permanent raw-first passes `24/24`; prerequisite, raw/integration docs,
taxonomy and consumed-stop evidence pass `79/79`; common Process-v2 passes
`142/142`. Broad P3.19 is exactly 728 total: 727 passed, zero failed and one
known unavailable `/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko`
input error, which is not reported as a pass.

Independent changed-closure review is required. Topic 43 is the only new
obligation. The V1 action remains consumed and non-replayable, the reviewed D1
V2 capability is not a current approval, and the absence of its result keeps
D0 V2 unavailable. This unit creates no approval, arm, run, result, ready/run
manifest, D0, D1, F1, recovery, replay, causal result, candidate success,
device, ADB, USB, Odin or live authority and touches no A90 or S20+ state.

## Append-only independent-review correction — 2026-08-24 15:40:13Z

Independent review blocked the implementation tuple above. The reviewed D1
V2 `_result_complete` predicate compared the result's direct arm/start
receipts with the actual files, but did not apply `_arm_complete` or
`_start_complete` to those files. A canonical `{"foreign":"arm"}` or
`{"foreign":"start"}` replacement, accompanied by the matching updated
result receipt, therefore passed that predicate and the predecessor reducer.

The D1 V2 source and binding are unchanged. The repaired reducer now invokes
the exact compiled D1 V2 `_journal_state` on the fixed arm and start paths,
using `_arm_complete` and `_start_complete`, after `_result_complete` has read
their direct receipts. Both states must be present, node-valid and
bytes-complete, and each stable-reopened receipt must exactly equal the result.
The hostile suite performs the actual foreign canonical replacements and
updates the result receipts; both are rejected.

The predecessor reducer `54126B/ea72adab` and binding `14251B/bda6b82d`
remain unreviewed historical identities. The repaired reducer is
`54939B/d6d4c766047b00475205a7ff945f254b5a2857409f13311352cfacf010028780`;
the canonical review-pending binding is
`14251B/4be15cba9afa7524fe90cf7f97d429e3a6e710d735fa557e7a287fe97386c667`.
The D0 V2 producer remains byte-identical at `72288B/e1190b66`; therefore its
active raw-first source identity and the `-06` receipt remain byte-identical.
The prerequisite `-06` and deterministic blocked integration receipt also
remain byte-identical after independent regeneration. Topic 43 remains the
single open review obligation; the repair creates no PASS_GO or live authority.
The repaired focused split is `29/29 + 12/12 + 14/14 = 55/55`; the added
hostile regression makes the current broad selector 729 tests. The preceding
728-test paragraph is the implementation predecessor result and is not
retroactive validation of this repair.

## Append-only cross-binding correction — 2026-08-24 16:02:57Z

A second independent review retained a schema-valid start journal while
changing only `before.boot_id_sha256` and
`selection.selected_serial_sha256` to other valid digests. Both D1 V2
`_start_complete` and `_result_complete` remained true after the result's
start receipt was updated, and the first repaired reducer accepted it because
it discarded the parsed start value after semantic and receipt validation.

The final reducer stable-reads the fixed start exactly once. From that same
payload it strict-parses the object, applies `_start_complete`, derives the
direct receipt, and requires typed exact equality of parsed start `before` and
`selection` with the D1 result. The regression performs the complete
schema-valid replacement and verifies both D1 predicates remain true before
the reducer rejects it. The arm/result overlap was also audited: manifest,
approval, ordinal and run-directory identities are independently forced to
the same execution inputs/constants, and arm has no free health or selection
field requiring an additional result cross-binding.

The first repair's reducer `54939B/d6d4c766` and binding
`14251B/4be15cba` remain unreviewed predecessors. The final reducer is
`55631B/13496ebaf0b7a9c83b1d73841b8ef3213f2a21b4b1ef4408dfae4ba13bbb23c0`;
the canonical review-pending binding is
`14251B/151c2f1a9bb9752260e48b4b015e0265142358bc1801639e6d0cae5fb6843386`.
The repaired focused split is `29/29 + 13/13 + 14/14 = 56/56`, and the
current broad selector is 730 tests. Raw, prerequisite and integration
receipts independently regenerate byte-identically; topic 43 remains open.
Broad was not rerun, so neither predecessor broad result is claimed as
validation of this cross-binding repair.

## Append-only fixed-result-path correction — 2026-08-24 16:26:00Z

A third independent review copied the complete canonical D0 result to another
direct regular `0400`/single-link path. All nested journal paths still named
the fixed producer namespace, but caller-selected `--d0` supplied the copied
path and the reducer accepted it, recording that arbitrary copy as the
normalized D0 receipt.

The reducer now passes the actual D0 input path into `_validate_d0`, whose
first gate requires an absolute path exactly equal to `DEFAULT_D0`. Canonical
alternate copies, symlinks and relative aliases are rejected. A symmetry audit
applies the same absolute-exact gate to D1 input, normalized publication
validation and exclusive output publication. CLI `--d0` and `--out` remain
parseable for compatibility but cannot escape those semantic gates; alternate
output is rejected before a file is created. Tests retain a normal fixed D0
fixture as the positive control.

The cross-binding repair's reducer `55631B/13496eba` and binding
`14251B/151c2f1a` remain unreviewed predecessors. The final reducer is
`56272B/0658ca3094ccaa1929cbb1d85512d732adb82c66dd19cb8d2af2dbebd43e91ab`;
the canonical review-pending binding is
`14251B/b0cc446f5cb9861d1f91a03b375e8eb917da3cd2fbf1c9d8800d1852abe9dfed`.
The repaired focused split is `29/29 + 14/14 + 14/14 = 57/57`; the current
broad selector is 731 tests. Raw, prerequisite and integration receipts
independently regenerate byte-identically and topic 43 remains open. Broad
was not rerun; no predecessor broad result validates this repair.

## Append-only direct-output-namespace correction — 2026-08-24 16:44:00Z

A fourth independent review replaced the fixed output parent with a symlink.
The predecessor's lexical path equality still held, while path-based
`mkdir`/`chmod`/`open`/`fsync` followed the link and wrote or validated an
external `result.json`.

The final reducer traverses the output parent from `/` one component at a time
using directory fds opened with `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`. Missing
components are created only with `mkdirat` below a verified parent fd and then
reopened nofollow. The final parent must be a direct current-uid `0700`
directory. Publication uses exclusive nofollow `openat`, a complete write loop
that retries `InterruptedError` and rejects zero progress, file fsync plus exact
regular/mode/link/owner/size checks, parent-fd fsync, and a fresh direct-chain
reopen whose bytes must equal the payload. Validation uses the same parent-fd
and final-fd stable read before parsing JSON.

Hostile tests prove a symlinked parent creates no external file, a preexisting
external canonical file cannot validate, partial writes complete exactly, and
zero-progress writes fail closed. The fixed direct parent remains the positive
control. The fixed-path repair's reducer `56272B/0658ca30` and binding
`14251B/b0cc446f` remain unreviewed predecessors. The final reducer is
`62093B/12aa83bfae64fb9b0589ad0c3cba79e2f6ca2029cdb28f7e6446edee0bf7cf1c`;
the canonical review-pending binding is
`14251B/bc3b44bc603cad83e58662e8ae613a61348397b59b22f35d7c987e1838cd84cd`.
Focused remains `57/57`; the broad selector remains 731 because the hostile
cases extend the existing path-boundary test. Retained receipts independently
regenerate byte-identically, topic 43 remains open, and broad was not rerun.

## Append-only atomic-publication correction — 2026-08-24 16:59:53Z

A fifth independent review injected zero write progress and a one-byte write
followed by `OSError`. Direct exclusive creation had already exposed the final
name, leaving a zero- or one-byte final after failure. It also replaced the
fixed final during `normalize`; validation had no final reopen and returned an
authoritative result from the initial bytes.

Publication now writes only the fixed same-parent `.result.json.partial`
staging name. The stage is exclusive, nofollow, `0400`, fully written with the
interruption-safe loop, file-fsynced, identity-checked and stable-reopened
before final can exist. A hard link publishes the complete inode to final
without replacement; parent fsync precedes staging unlink, a second parent
fsync follows, staging must be absent, and a direct final reopen requires exact
payload bytes and link count one. Before link, failure cleanup may unlink only
the exact current-invocation regular staging inode and fsync its parent; final
remains absent. After link, any stage/link uncertainty remains complete but
fail-closed.

Validation retains the initial direct payload and stable node identity. After
normalization and semantic validation it direct-reopens final and requires
both bytes and identity to match before returning authority. The hostile test
atomically substitutes an identical-byte new inode during normalization and is
rejected. Zero-progress and one-byte-plus-error paths leave no final and no
authoritative receipt; completed partial writes leave exact final bytes and no
stage.

The direct-namespace repair's reducer `62093B/12aa83bf` and binding
`14251B/bc3b44bc` remain unreviewed predecessors. The final reducer is
`66217B/cd4aa54e943900d9269e549c6e7a6f78da8ceb060465a97ed107fefc95db39ed`;
the canonical review-pending binding is
`14251B/e41d40fa730f3ecb459ca8e6ac06d495e03772a2158aab4399ff34a1fa40ce2b`.
Focused remains `57/57`, the broad selector remains 731, retained receipts
independently regenerate byte-identically, topic 43 stays open and broad was
not rerun.

## Append-only nameless-atomic-publication correction — 2026-08-24 17:31:41Z

A seventh independent review demonstrated that no sequence of checks makes a
named staging path race-free: a foreign inode could replace it immediately
before unlink, or a new `.partial` child could appear immediately after an
absence check. The predecessor could delete foreign state or return success
with an extra child.

The final reducer has no staging pathname. Its exact 1271-byte helper at SHA-256 `0387869a286a925669ef0125ffec0619495acac01782fd60b38eef8e1c1bc886` is pinned transitively in the reducer and kept outside the revalidation acquisition population; the raw-first detector is not relaxed. It opens an unnamed same-filesystem
inode below the verified parent fd with `O_TMPFILE|O_RDWR|O_CLOEXEC` and never
combines `O_TMPFILE` with `O_EXCL`. Unsupported `O_TMPFILE` or `linkat` stops
with final absent; there is no named fallback. The unnamed descriptor receives
the complete interruption-safe write, `0400`/current-uid/nlink-zero/size/fsync
checks, and exact seek/read verification on that same fd. Narrow libc
`linkat(tmpfd, "", parentfd, final, AT_EMPTY_PATH)` atomically publishes that
inode without replacement. Final device/inode/core must match the unnamed fd
with link count one, parent fsync follows, the parent child set must be exactly
the final name, and the last direct snapshot must match payload, final identity
and parent identity.

Tests assert `.result.json.partial` never exists and the successful parent has
only final. Injected unsupported `O_TMPFILE`, linkat error and EEXIST all fail
closed; zero/partial/error writes plus final/parent replacement and all prior
regressions remain covered. The actual workspace filesystem passed a bounded
host-only `O_TMPFILE + AT_EMPTY_PATH` probe; absence on another filesystem is a
blocker, not permission to fall back.

The inode-continuity repair's reducer `68081B/60ab41da` and binding
`14251B/42e7d146` remain unreviewed predecessors. The final reducer is
`68400B/241c216e85d5644899d54702a318b5bc3b6db9b39f12d9cc79f8d8796fc0a9cb`;
the canonical review-pending binding is
`14251B/f4ccb03ad38a44e0417f3150797ed9d4af9129dd67b2da33341d1589de4830cb`.
Focused remains `57/57`, broad selector remains 731, retained receipts
independently regenerate byte-identically, topic 43 stays open and broad was
not rerun.

## Append-only publication-inode-continuity correction — 2026-08-24 17:15:49Z

A sixth independent review replaced the complete staging name with an
identical-byte new inode immediately before link, and separately replaced the
complete final with an identical-byte new inode immediately before the last
reopen. The predecessor compared stage with final only after link and compared
only bytes at the last reopen, so both races could report success.

The final reducer retains the complete original staging descriptor identity.
Its pre-link stable reopen must match that identity exactly. After hard link,
stage and final must share the original device/inode and core metadata with
link count two. After stage unlink, final must retain the original core with
link count one; that full expected identity is captured. The last direct
reopen must match exact payload, expected final identity, and the final-parent
device/inode captured when publication began. Published-result validation also
compares initial/final bytes, file identity and final-parent identity across
normalization.

Hostile tests replace stage before link, final before reopen, and the complete
parent directory before reopen while preserving bytes. All fail closed; the
normal atomic path still succeeds. The atomic-publication repair's reducer
`66217B/cd4aa54e` and binding `14251B/e41d40fa` remain unreviewed predecessors.
The final reducer is
`68081B/60ab41da22c11775e4b98204165c6f16fbf78cb8432e3b5787371a12f4ec4a66`;
the canonical review-pending binding is
`14251B/42e7d146855dc573218ad69701d0582a39963406d2f263b981f04d43a0d65ad3`.
Focused remains `57/57`, broad selector remains 731, retained receipts
independently regenerate byte-identically, topic 43 stays open and broad was
not rerun.
