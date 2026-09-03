# S20+ G986N P0 PID1 Odin F1 owner H0 implementation

Date: 2026-09-01

Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

Tier: H0 only

Status: `H0_REVIEW_PENDING_NOT_ACTIVE`

## Outcome

The shortest live PID1 route is now implemented host-side without completing
the longer TWRP direct-block-write Q0 stack. A new thin owner exact-loads the
already reviewed B0 one-shot Odin/rollback engine in an isolated module
instance, installs one explicit P0 profile, and retains its causal Download
transition, process cage, raw Odin attribution, attended physical Download
recovery, mandatory resident rollback, and final rooted-Android health. The P0
profile additionally binds the existing Process-v2 append-only global
consumed-candidate registry, its fixed nonblocking target-session lease, one
raw ACM evidence node, and pre-effect process-cage recovery records.

This H0 implementation unit used no device, ADB, USB endpoint, Odin process,
reboot, mode transition, candidate claim, or partition transfer. The owner and
observer are mechanically dormant whenever their activation booleans are
false. A later active status authorizes nothing unless all three current
private activation records also validate.

## Why this is smaller than the TWRP Q0 route

The P0 candidate and observer were already complete, while Q0 still lacks the
full stage/cleanup runner, physical choreography owner, recovery continuation,
fresh preparation/approval, and activation. B0 has already demonstrated the
same S20+ boot-only Odin transfer and resident rollback hazard class. Reusing
that frozen engine avoids a second direct-write primitive and avoids copying
its 5,772-line state machine.

The ordinary imported B0 module remains unchanged. The P0 owner loads the
exact 224,559-byte B0 source at SHA-256
`82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a`
under a private module name and gives that private instance a separate run
root, local recovery projection, version, approval prefixes, journal node set,
empty predecessor set, and terminal spelling. The permanent no-replay authority
is the existing append-only hash-chained Process-v2 registry, not that local
projection. Tests import ordinary B0 beside the P0 owner and prove that its
candidate and run root retain their original identities.

Every connected entrypoint acquires the fixed Process-v2 target-session flock
before target rechecks and holds its open descriptor for the whole invocation,
including final health. An internally issued opaque lease binds each nested
call to that descriptor and exact lock inode. Its sentinel, ContextVar,
concrete lease type, mutation grant, and issuance context manager remain
closure-private; a caller-created boolean, token, dictionary, or module global
cannot stand in for the flock. The B0 engine and its inventory, raw-capture,
boot-verifier, and transport dependencies are exact-loaded as P0-private module
instances, leaving ordinary B0 dependencies untouched. Their command,
transport, raw-stream/journal publication, registry-mutation, cgroup-control,
shared-guard, and observer-live primitives are activation-and-lease fenced.
Registry mutation additionally needs a closure-private claim-or-release grant
derived from the exact run journal.

## Exact candidate and rollback

The only candidate is:

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `AP.tar.md5` | 25,733,161 | `58479a25ae2550366d38be4fae6727eafaadcdb98567de4a00c3a1cf5c0015db` |
| `boot.img.lz4` | 25,722,068 | `c02c1ce1c963942d96de500d6caa89118424c36d211ab9aa788a85db0859c2ee` |
| decoded `boot.img` | 67,108,864 | `5c967babf96b8b625c4afe3edbbd473cf55042e252dacf57def8c3809fc697ff` |
| freestanding `/init` | 3,584 | `2a1e7b4a1c485058c790efca6dcc4fd3df1785496795c5fda299a026f77d40ee` |
| build manifest | 14,574 | `75052fd00dd8c1b79aeec85b6dd4599bc81ccec9c0d684cfba7d6ba16b00d916` |

The AP contains exactly one regular `boot.img.lz4`. The first runtime syscall
is raw `getpid`; every non-one result parks before volatile mounts, configfs,
ACM, or the banner. The exact positive banner is 52 bytes with SHA-256
`6441acc62e89d8a92a54626e4635ff5ec26a51ad23f3a14dccdf7fb247913509`.

The mandatory rollback is the already demonstrated resident-Magisk AP,
25,835,561 bytes at SHA-256
`1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`.
It also contains only `boot.img.lz4`. Recovery and every other partition remain
outside the owner.

## Observation and attribution

The P0 USB baseline and complete non-effect transfer preflight are captured
before the global candidate claim. While the
exact prepared Download session is still present, the owner binds USBFS
bus/device to one sysfs node, verifies the prepared `usb:<node>` topology hash,
proves the P0 USB identity absent, publishes a private no-clobber baseline,
reopens the exact Odin/AP/shell inputs, rechecks the Download endpoint, and
allocates a journal-bound empty process cage. Only after that complete preflight
receipt may the append-only global claim be attempted.
On every cut-resume before the claim it repeats the live Download/session,
topology, and candidate-absence reads instead of trusting the stored baseline.
The raw node name is not persisted. A baseline failure therefore occurs before
candidate consumption or transfer.

Before the candidate claim, registry source/layout/activation/chain failure is
fail-closed. After the durable P0 claim intent or local claim receipt already
crosses that boundary, loss of registry chain readability is represented only
as consumed-uncertain same-run recovery evidence: the candidate cannot run,
but journal-derived rollback and health remain available. The sole release is
a reopened raw `odin_local_parse_failure` proving no device session and no
partition transfer. Its release intent precedes the append-only release record;
afterward only the same-run local recovery projection is removed. The old run
still forbids replay while a future fresh run may rebind the candidate.

After a possible transfer, the observer accepts only one endpoint with all of:

- USB `04e8:6861`;
- manufacturer `Samsung` and product `S20Plus-P0-PID1`;
- no serial descriptor;
- one `cdc_acm` interface zero and dynamic `ttyACM<n>`;
- the prepared physical topology; and
- the exact 52-byte banner from an exclusively opened, rdev-stable character
  descriptor.

The exact 52 bytes read from the descriptor are first stored as a mode-`0400`,
atomic no-clobber private raw file. The structured receipt binds its exact
size/SHA, the endpoint identity, and the descriptor rdev hash; validation
reopens the raw file and rederives the banner. Only that receipt becomes
`claim_verdict=PROVED`. Inherited B0 observations are restricted to
`NO_PROOF`. Conflict, foreign topology,
absence, pending enumeration, banner mismatch, or timeout becomes `NO_PROOF`.
Either outcome keeps candidate replay false and proceeds only toward the
preauthorized resident rollback. Final PASS additionally requires an
Odin-derived completed candidate transfer, one completed resident rollback,
and fresh rooted resident Android health.

## Reviewed activation identities

| File | Size | SHA-256 |
| --- | ---: | --- |
| P0 Odin owner dormant | 222,968 | `9d97a5a4f80cd7a12f7ee9a0d7829d2590780821f7b4b5535330a3f7cf806018` |
| P0 Odin owner active | 222,967 | `82657b47822a85a1a3961bbc362f99f4e9bce9d62dcb49316de9d7a9df218cfd` |
| owner activation-normalized | 222,968 | `03a214c68f0f2725021796ee27155378afc81dcbe381a8a8aadcaab5fbca831e` |
| focused owner test | 146,304 | `98c2d7a6331911d0a57b22f5ef809b472f0632f55a069e38b3fccf588778dd02` |
| P0 observer dormant | 16,479 | `98406b1cb968943f0e9cf62cd698123ecd9aa7aa3b84660838b0ff2c89ad34ab` |
| P0 observer active | 16,478 | `d9304b7b6de1d366d7aea78bc44b785a1149b9d9096ad85c21be7d2d1a1d1ce3` |
| observer activation-normalized | 16,479 | `214e0296c5918d9f8e8512b1617a8f7cc059db739624688382a12ccf14d8e4b1` |
| focused observer test | 12,482 | `f7f039d33230cc864d1f76bf8df18c1e67c59106c9d5ddf00f6477955b57fbd2` |
| P0 C init | 15,549 | `16c21037094529bbce6158658f892aaa6d24412708ceae7251af4f42c4450e51` |
| P0 builder | 23,173 | `de48f3c86812ac5debb007d8d601964670244a3c5def99438460aa83e13d5545` |
| isolated B0 engine | 224,559 | `82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a` |
| global registry source | 53,811 | `0a112d7dd2633d3465137cdb67ed4539949a3c0c0ec90b178a3ec293735dbdc4` |
| immutable registry activation | 21,276 | `aa50c211ee86d4b1534399c6d9fd82d4de3550856724e5788d693b012bce471b` |

The exact current host-closure digest is emitted by the validator and
is bound by the private review record rather than recursively embedded in a
closure input.

## Validation

The focused P0 owner suite passes 74/74. Core combined validation passes
148/148, and the wider retained suite passes 178 tests with ten historical
TWRP skips:

- P0 builder/artifact closure: 8;
- P0 USB observer: 10;
- P0 Odin owner: 74;
- unchanged active B0 owner: 56;
- B0 H0 builder/closure: 10;
- expired TWRP sibling: 12, including ten explicit historical skips; and
- Process-v2 consumed-candidate registry: 8.

The suite covers dormant and active-without-lease fail-before-contact behavior,
whole-entrypoint open-FD target-session lease ownership, absence of exported
issuers/tokens, valid-descriptor forged-context rejection, preclaim registry failure,
post-intent consumed-uncertain recovery, append-only local-parse release and
same-run projection cleanup, intent-before-cgroup allocation,
generation-safe pre-intent recovery, inherited B0 validation of exact P0
candidate/rollback/abort cage generations, reconciled-effect cross-binding,
and journaled Odin-listing cage reconciliation without backend replay, exact
artifact and manifest binding,
ordinary-B0 dependency isolation, topology mapping,
complete-transfer-preflight-before-claim ordering,
stale-baseline cut revalidation, raw banner no-clobber/reopen, endpoint/rdev
binding, inherited-positive rejection, empty P0 predecessor lineage, direct
raw-writer/journal/shared-guard bypass denial, dormant no-create private-root
validation, goal/review/mechanical-record activation binding,
partial-activation and missing-live-activation-record denial, contradictory
global-state rejection, and terminal conjunction. The historical TWRP
sibling suite separately passes two current expiry checks and explicitly skips
ten predecessor-closure checks. `py_compile`, host closure validation, and the
178-test suite pass; final scoped diff validation remains part of the
review handoff.

## First independent review and correction

The first read-only hostile review returned `NO_GO`, HIGH/MEDIUM/LOW `2/4/2`.
It found directly callable dormant helpers, a recreateable local claim root,
inherited B0 positive observations, stale baseline reuse, non-raw ACM evidence,
an incomplete profile/predecessor closure, partial-activation overreporting,
and a stale sibling TWRP-owner qualification.

The first correction gated the P0 wrapper's candidate/USB/raw/registry effect
helpers, but had not yet gated every inherited low-level engine surface. It
uses the already activated global append-only hash chain as the authoritative
candidate record and treats a missing/corrupt registry as a stop before local
root recreation. A post-global-claim cut may reconstruct only the bound local
recovery projection and can never reissue the global claim or candidate. It
freshly revalidates the Download mapping and candidate absence before every
pre-claim continuation, persists and reopens raw banner bytes, rejects every
inherited positive verdict, clears B0 predecessor compatibility, and reports
active authority only when both activation booleans are true. The sibling TWRP
report and target section now mark its old exact-contract qualification
expired. A deterministic no-write fixture additionally proves that the global
key is stable across runs while binding the exact target, AP, and boot member.
These corrections remain review-pending and grant no live authority.

## Second independent review and correction

The corrected first-review bytes received a second read-only hostile `NO_GO`,
HIGH/MEDIUM/LOW `2/2/2`. It found that the loaded engine still exposed
ungated inherited low-level calls, registry loss after a claim could block
mandatory recovery, exact Odin local-parse failure lacked the Process-v2
append-only release, the target-session lease was absent, cage allocation had
an unjournaled cut, and the plan mislabeled the local projection as the global
claim.

The current bytes replace the named inherited live surfaces and private live
aliases with activation-plus-lease gates; wrap every connected entrypoint in
the fixed target-session lease; distinguish preclaim registry failure from
same-run consumed-uncertain recovery; reopen and raw-validate the sole
local-parse release before appending it; remove only the verified local
projection after that release; and durably journal/reconcile a binding-derived
process cage before any backend intent. The plan now names that path
`local_recovery_projection` and separately names the authoritative global
registry. These second-round corrections remain independently review-pending.

## Third independent review and correction

The second-round correction received a third read-only hostile `NO_GO`,
HIGH/MEDIUM/LOW `4/3/0`. It found that `resume` and pre-candidate abort still
reopened the registry before recognizing a durable local claim boundary; the
lease context could be forged with a caller-created boolean; nested inventory,
raw-command, transport, registry-append, and observer helpers remained directly
reachable; the global claim preceded complete transfer preflight; Odin `-l`
used an unjournaled transient cage; two activation booleans did not bind the
policy/review/test closure; and claim-receipt plus consumed-uncertain could
coexist.

The current bytes recognize the exact same-run P0 intent or receipt before any
registry reopen and synthesize only consumed-uncertain recovery when the chain
is unavailable. The lease capability now requires an internally issued token,
an open exclusive-flock descriptor, and repeated exact lock-inode validation.
The B0 dependency graph is loaded privately and its effect primitives are
fenced without changing ordinary B0. Registry writes additionally require one
internal claim/release capability. Candidate AP/Odin/shell/endpoint/cage
preflight is durable before the global claim, while a claim cut can only become
no-backend recovery. Transfer, rollback, abort-return, and Odin-listing cages
use bounded generations with prepare/bound/reconcile records; pre-intent cuts
can allocate a later host-only generation without replaying a backend. The
prepare CLI reacquires the exact lease before reopening its approval output.
Claim receipt and consumed-uncertain are XOR. That revision proposed one
mode-`0400` activation record; the fourth review below found its review/goal
and mechanical-transition closure incomplete. It granted no connected
authority.

## Fourth independent review and correction

The third-round correction received a fourth read-only hostile `NO_GO`,
HIGH/MEDIUM/LOW `4/4/0`. It found that P0 generation cage names were rejected
by inherited B0 candidate/rollback/abort validation; the live and registry
mutation sentinels plus ContextVars remained module-accessible; raw-capture and
journal publication primitives were still directly callable; activation did
not bind the current goal or dedicated review and mechanical-diff records;
dormant private-root validation could create directories; shared-guard read
APIs remained outside the lease fence; and a reconciled generation could skip
effect-to-cage cross-binding.

The current bytes replace the inherited B0 cage validators with exact P0-aware
validators while preserving B0's quiescence record contract and prove all
three candidate, rollback, and abort-return kinds. Lease and registry-mutation
sentinels, ContextVars, concrete types, and issuers now exist only inside one
factory closure; the module retains only verifier functions and already-bound
fixed entrypoints. A forged module global, token, context, and even a valid
descriptor cannot enter that closure. Raw stream creation/writing,
`RawCaptureWriter`, fixture publication, journal atomic publication, shared
guard reads, and registry internals are fenced. H0 root validation accepts only
already-present direct mode-`0700` roots and never invokes the inherited
creator. Reconciled and live cage generations now contribute to one exact
effect-binding count. Future activation additionally requires two distinct
mode-`0400` private records: the dormant zero-finding review closure, then the
exact allowlisted dormant-to-active diff with its own zero-finding review. The
final live activation record binds both, the current goal, all current policy
and test receipts, and their semantic active markers. These fourth-round
corrections granted no connected authority.

## Fifth independent review and correction

The fourth-round correction received a fifth read-only hostile `NO_GO`,
HIGH/MEDIUM/LOW `1/2/0`. It found that activation semantics were recognized by
free substring markers that could be moved into comments or history; a raw
capture writer could retain open raw descriptors beyond its target-session
lease; and cage prepare accepted parent traversal while bound-cage validation
did not validate the complete nested cage identity.

The current bytes structurally locate the unique authoritative registry cell,
target section, goal section, and report preamble before accepting each exact
status transition. Misplaced status text grants nothing. Raw file creation and
writing now require a second short-lived closure-private acquisition grant in
addition to activation and the live target-session lease. The public
acquisition surface returns only a completed immutable handle, never the
writer or raw descriptor, and direct fixture publication is denied at runtime.
Cage prepare rejects parent traversal, while the bound validator checks the
complete exact nested process-cage schema and identity.

The same correction also fences the inherited inventory entrypoints whose
default argument retained the original command function, the local candidate
claim writer, and direct cgroup/sysfs identity readers. Tests now prove these
paths fail before contact, alongside misplaced-marker, escaped-writer,
parent-traversal, and incomplete-cage negative cases. These fifth-round
corrections remain exact-byte review-pending and grant no connected authority.

## Sixth independent review and correction

The fifth-round correction received a sixth read-only hostile `NO_GO`,
HIGH/MEDIUM/LOW `5/0/0`. It challenged Python closure introspection, generic
leased-wrapper argument surfaces, writer method lifetime, Markdown status
placement, and stale activation-policy binding. The review made zero device
contacts and zero writes.

The repository threat model explicitly excludes a malicious same-UID owner who
reflects into Python closure cells or replaces the repository/runtime between
individual calls; that would require a separately defined isolation boundary.
The ordinary callable surface is nevertheless narrower: inherited inventory
entrypoints and the unused transport helper are denied outright, bounded ADB
commands accept only fixed command forms and the serial learned from the exact
target row, and every live raw ADB/Odin command is matched to a fixed profile
and its leased journal intent before acquisition.

The raw writer is now a closure-private proxy whose every attribute or method
requires the same short-lived acquisition grant. The grant tracks every proxy,
forces any unfinalized descriptors closed on exit, and fails the invocation;
only a finalized immutable handle survives. Markdown semantics now remove
HTML comments and fenced blocks, require exact heading/status adjacency, bind
the complete exact registry header and all four target-row cells, and require
the exact report preamble field sequence. Negative tests place otherwise valid
active text inside comments and code fences.

The zero-finding record now carries exact dormant document semantics and
activation-normalized receipts for every changing policy file. The mechanical
record requires those normalized receipts to remain identical, an exact
before/after replacement allowlist, the complete dormant-to-active semantic
map, and the already required exact byte receipts. Unchanged policy and every
test receipt remain full-byte equal. These sixth-round corrections remain
exact-byte review-pending and grant no connected authority.

## Seventh independent review and activation-baseline correction

The sixth-round bytes received a seventh read-only hostile `PASS_GO`,
HIGH/MEDIUM/LOW `0/0/0`. The supplied owner, observer, B0 engine, policy,
report, goal, and focused-test hashes matched; the reviewer made zero device
contacts and zero writes. Its read-only sandbox could run five dormant tests;
the complete writable host run remained the separately recorded 160-test pass.

Before mechanical activation, a local consistency audit found that the
focused owner and observer tests still relied on the module booleans being
false, so changing the reviewed booleans would make the bound test closure
self-contradictory. One exact seventh-review record was created, reopened, and
then retired before any activation atom or device authority because that
closure was superseded. The current tests explicitly force false only when
testing dormant rejection and otherwise accept either exact reviewed
activation state. The standalone observer plan also distinguishes an active
bound component from standalone live authority, which remains false. These
follow-on source/test bytes require their own exact independent review.

## Eighth independent review and host-registry repair

The activation-neutral follow-up received `NO_GO`, CRITICAL/MAJOR/MINOR
`1/3/2`. It found that ADB inherited caller redirection and loader variables,
the owner pinned only the dormant observer bytes, the review-test receipt
accepted an arbitrary nonempty mapping, the partial-activation test depended
on ambient state, the observer test did not require exactly one activation
atom, and the activation prose incorrectly implied test-byte changes.

That correction started one transaction-private pinned ADB server on an
internally random localabstract socket, admits only that exact executable and
peer PID/UID/GID, and gives both structured and raw ADB paths the same closed
five-key execution environment. It binds exact dormant/active observer hashes
to one activation-normalized observer identity, requires exact raw unittest
logs and fixed module/count/skip terminals, makes partial activation explicit,
and requires exactly one observer atom. Activation still changes no test byte.
These corrections pass focused owner 60/60, observer 10/10, core 134/134, and
wider 164 with ten historical skips, but remain final-review pending.

That validation initially stopped host-only because a host mount identity
rotation left both registry lock records with stale `st_dev` while every other
lock field, all six records, the head, chain, and 42-entry legacy deny list
were unchanged. A separately reviewed private one-shot repair changed only
those two activation fields. Its first apply exchanged the exact successor,
then safely rolled back when a direct-reader check mistook normal post-rename
`atime` advancement for identity drift. The narrow correction excludes only
read access time while retaining device, inode, mode, link, owner, size,
modification-time, and change-time comparisons; a second independent review
returned `PASS_GO` at 0/0/0. The resumed repair closed terminally with current
activation SHA-256
`aa50c211ee86d4b1534399c6d9fd82d4de3550856724e5788d693b012bce471b`,
recoverable old backup SHA-256
`d205d1d5818d738f162d0509d9a5e4b80650bf631098987173c7b778f546c953`,
and private result SHA-256
`e71cea321374a67d93b698dbbf04fad7d1eebaecabf572087b116cf8200f57ba`.
Candidate replay remains false; device contacts and record mutations were zero.

## Ninth independent review and active-test receipt correction

The next full-closure review reproduced the host closure, dormant pre-contact
stop, focused 10/10 and 60/60 tests, and wider 164-test result with ten skips,
but returned `NO_GO`, HIGH/MEDIUM/LOW `1/0/0`. One owner test still rewrote
only `OBSERVER_ACTIVE=false` to true and asserted the dormant bytes, so the
required unchanged test file would fail after activation. The mechanical
record also had no distinct active-state test receipt and could reuse its
dormant raw logs.

The corrected test now derives both exact observer forms from either reviewed
atom, verifies both full hashes and their common normalized hash, and requires
the loader's reported atom to equal the file. Host-closure testing isolates
the still-absent live record so the unchanged suite can run after the status
atoms change but before activation records exist. The mechanical record now
requires a separate active-test closure binding the exact activation diff,
normalized closure, unchanged engine/registry/tests/policies, and a distinct
mode-`0400` active raw-log namespace. The active logs must independently prove
the same fixed 10/60/164 counts and ten skips. This exact correction remains
final-review pending and grants no live authority.

## Pre-record active observer size correction

After the ninth correction passed dormant tests, the six allowlisted status
atoms were applied while mechanical/live records remained absent. The first
active owner import stopped before any backend because the observer loader
still required the 16,487-byte dormant size even though the reviewed
`False`-to-`True` atom produces an exact 16,486-byte active file. No P0 test,
ADB, USB, Odin, reboot, claim, or transfer was reached.

The atoms were returned to dormant. The prior zero-finding record was not
deleted; it was moved outside the live namespace under its exact SHA and is
superseded. The corrected loader binds a dormant/active size map before the
already fixed full-hash pair and normalized hash. The focused test additionally
writes the exact active bytes into a temporary host fixture and loads them with
the production activation-normalized loader. The current dormant suite passes
60/60 and host closure passes; a new exact review, zero-finding record, and
mechanical activation are still required.

## Active document-normalization test correction

The next full-closure review returned `PASS_GO`, HIGH/MEDIUM/LOW `0/0/0`, and
a fresh dormant zero-finding record was published. A second inert six-atom
activation loaded successfully, and the focused observer passed 10/10. The
focused owner then stopped at 59/60 because its document-normalization test
still assumed the repository files were dormant while running under the active
atoms. No ADB, USB, Odin, reboot, candidate claim, or transfer occurred.

All six atoms were restored to dormant. The exact zero-finding record and
partial active logs were retained outside the live namespace as superseded
evidence. The corrected test parses the current authoritative document states,
derives both exact dormant and active forms from that state, and verifies their
normalized receipts remain equal while an unrelated change does not. A fresh
exact review and all three activation records remain required.

The following inert activation passed the focused 10/10 and 60/60 suites but
the wider suite stopped because the expired TWRP-owner test required a
target-contract error even though the active repository-registry atom is
validated first. The legacy owner did fail closed. The six atoms were restored
before device contact, and the test now accepts either exact repository- or
target-contract identity rejection. Fresh review remains required.

## Connected prepare pre-contact stop and correction

The first connected `--prepare` after the activation commit stopped at the
initial global candidate-presence check with `P0 registry mutation lacks its
exact internal capability`. The inherited preflight helper enters the registry
writer path, while the P0 fence had reserved that path for claim/release
mutation grants. The failure happened before run allocation,
shared guard creation, ADB server startup, target inventory, reboot, Download
intent, candidate claim, Odin, or transfer. The P0 run namespace gained no run,
the local claim directory remained empty, and the global registry remained at
seven non-P0 records.

Review of that writer path found it may remove a leftover head-staging file or
repair a valid uncommitted tail before yielding, so it is not a read-only
preflight. The correction does not grant it. The pinned activation is instead
reopened as canonical exact bytes to prove the P0 AP is absent from all legacy
candidates, then the existing shared-reader `active_claim` query checks only
the fixed candidate key. Any head staging or tail inconsistency fails closed
without recovery mutation. Regressions drive the real prepare entrypoint
against an isolated initialized registry, prove the complete namespace and
bytes unchanged, and prove a staged-head condition remains untouched. All
prior active records were retired before changing these bytes; fresh review
and activation are required.

## Connected private-ADB ownership stop and simplification

Two later connected preparations created and then cleaned their transient
shared guard, and stopped before candidate claim, Download intent, Odin, or
transfer with `exact S20+ ADB inventory is absent or ambiguous`. The first had
no S20+ endpoint. During the second, the
ordinary server saw exact healthy `SM_G986N/y2q` alongside S22+, but it already
held both USB interfaces, so the transaction-private P0 server could not
enumerate either. Both attempts left only empty private run directories and no
retained guard; the P0 candidate remains unclaimed and no device effect
occurred.

The current correction removes only the private ADB daemon lifecycle. Both
structured and raw ADB clients use the already reviewed B0 fixed executable,
one closed five-key environment, and the fixed local `tcp:5037` server socket.
All device commands still require the leased exact S20+ serial, while every
inventory, model/device/build, boot, root/Magisk, topology, and pre-effect
revalidation remains unchanged. It never starts, stops, detaches, or rehomes an
ADB server and introduces no new handoff mechanism. Fresh focused validation,
one independent review, and new activation records are required.

## Activation sequence

The authoritative current state is the preamble status line. The one-time
activation sequence is:

1. independently review the exact owner, observer, inherited B0 execution
   closure, tests, target section, Process-v2 interaction, and physical
   rollback path;
2. remediate every finding and obtain exact-byte `PASS_GO`;
3. separately review and commit the mechanical activation of owner and
   observer plus target/registry/goal/report status, while keeping the reviewed
   test bytes unchanged and rerunning them under the active atoms; bind the
   resulting exact identities and private activation-record contract;
4. physically return the retained TWRP device to healthy rooted Android;
5. perform one fresh connected preparation and copy back only its exact
   short-lived approval; and
6. attend the candidate observation and physical Download rollback.

The intended terminal is
`PROVED_P0_PID1_ACM_RETURNED_RESIDENT_HEALTHY`. A candidate boot or banner
alone is not the terminal. Unless the active status and all three exact private
records validate together, there is no connected preparation, approval,
device authority, or live PID1 proof.

## 2026-09-02 candidate-preflight false positive

The first approved P0 candidate never invoked the Odin candidate backend. The
preclaim record proved `backend_invoked=false`, but the postclaim validator
compared its prepared endpoint digest against a later endpoint object whose
only change was USBFS `st_ctime_ns`. The stable device path, inode, `st_rdev`,
topology, and USB descriptors remained equal, and the inherited
`same_download_session` predicate already intentionally excludes that volatile
fourth identity field. The redundant exact comparison therefore stopped a
same-session transfer after the global claim and consumed the candidate
without sending it.

Recovery created no candidate backend invocation, performed the preapproved
prebound resident-Magisk boot rollback once, returned to healthy rooted resident Android,
and closed `NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY`; other-target commands and
all recovery-partition access were zero. The active records were retained under
`workspace/private/retired/`, and this owner is dormant while the validator is
corrected to bind the exact prepared receipt separately from stable live
same-session comparison. The consumed candidate is not reusable.

## 2026-09-02 V2 transfer and physical-rollback re-enumeration incident

The distinct V2-banner candidate was approved and consumed exactly once. Its
Odin outcome is unknown: `candidate-result.json` records
`ProcessCageError`, `host_process_quiescence_proved=false`, and
`possible_partition_effect=true`. The bounded 180-second ACM observation
returned `NO_PROOF`. These facts neither prove nor refute native PID1 and never
permit candidate replay.

The attended physical fallback then bound the sole exact Download endpoint and
consumed the operator's exact physical confirmation. Before rollback intent,
the same `usb:2-2` physical topology re-enumerated from USBFS address
`/002/032` to `/002/034`. The Samsung `04e8:685d`/SM8250 profile and absent
serial remained exact, but USBFS path, inode, and device number changed. The
owner stopped with `physical rollback endpoint changed`. No
`rollback-intent.json`, rollback raw capture, or rollback result exists, so the
resident rollback attempt count remains zero. The original confirmation is
consumed and is not replayed.

The narrow recovery candidate adds one incident-only rebind chain. It accepts
only a changed USBFS address on the same bus with the exact already-allowlisted
topology and Download profile. The first invocation records the exact current
endpoint and emits a new short-lived
`S20PLUS-G986N-P0-PHYSICAL-ROLLBACK-REENUM-CONFIRM:` token without invoking
Odin. Copying back that exact token records one confirmation and rebound
arrival before calling only the existing fixed resident-Magisk rollback path.
It accepts no artifact, command, path, topology, or device-profile input and
adds no candidate path. A wrong token, expiry before durable rebind
confirmation, second rebind, endpoint drift, malformed predecessor, or
existing rollback intent stops. A reporting cut after timely durable
confirmation may resume the same exact endpoint/rollback chain after expiry
without repeating confirmation or granting a second effect. After durable
confirmation, every unproved or changed Download identity before rollback
intent publishes an immutable rebind-miss receipt and blocks retry.

The first six-atom activation draft remained mechanically inert because no
mechanical or live record existed. Its independent H0 review returned
`NO_GO` after finding that fixed present-tense dormant wording contradicted the
active status. No connected entrypoint or device contact occurred. All six
atoms were restored to dormant, the superseded zero-finding and raw-test
evidence was preserved under `workspace/private/retired/`, and the reviewed
identity descriptions and authority wording were made valid in either state.

After the reviewed activation, the operator supplied the exact rebind token.
The owner durably recorded confirmation and a rebound arrival, then stopped
before rollback intent because the arrival validator compared the complete
endpoint object to the arm even though only volatile USBFS `st_ctime_ns`
changed. Device path/hash, identity prefix, topology, and USB profile all
remained equal. No rollback intent, capture, result, or transfer exists. The
correction validates the complete arrival and applies the same stable-session
predicate already used immediately before transfer; it changes no effect,
artifact, endpoint selection, or replay rule. The existing durable
confirmation is resumed as a reporting cut rather than repeated.

The corrected dormant and active suites passed 74/74 focused and 178 wider
tests with ten historical skips, followed by independent `PASS_GO` reviews at
`0/0/0`. The existing confirmation then resumed once. The fixed
resident-Magisk rollback result is `odin_transfer_completed`, host process
quiescence is proved, and final health proves healthy resident Android.
Rollback-result SHA-256 is
`42fa97fa826b3170c710550c610fd857ff6db9acb3c4306748ceb7e6249b8b40`;
final-health SHA-256 is
`797d02ac2513720648cbf3e6663bc5a615ad575ef832e4b914bbc782d3d273aa`.

The exact terminal is `NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY`, SHA-256
`67a291732731e244a942b376779f4c493a8f8e61ccbee764bb84625994362005`.
Candidate/rollback attempts are 1/1; both replays are false; recovery
partition read/write/transfer and other-target command counts are zero; the
shared guard is absent. Native PID1 remains unproved rather than disproved.
The owner was returned to dormant and the terminal activation records were
preserved under `workspace/private/retired/`; no further P0 device action is
authorized.

## 2026-09-03 V3 successor and pre-intent cage-order repair

Read-only reconstruction of the V2 journal found a host ordering defect, not a
kernel or PID1 result. The first candidate cage was bound at `10:27:44`, then
the post-claim Download endpoint census ran its own caged `odin4 -l`; that
listing's recovery finalizer correctly treated the still-pre-intent candidate
cage as orphaned and removed it at `10:27:46`. The owner did not publish
`candidate-intent.json` until `10:27:51`, so `execute_odin_exact` stopped on the
already-absent cage. The durable result consequently had no attributable Odin
capture and could not prove whether any device effect occurred. V2 remains
consumed and is not reclassified or replayed.

At this H0 review snapshot, the successor kept the same direct PID1 ACM design
and changed only the banner to byte-distinct V3. Its first runtime syscall is
raw `getpid`; only
return value one reaches volatile proc/sys/devtmpfs/configfs and the exact
52-byte ACM banner. It has no block path, persistent mount/write, reboot,
Android, Magisk, module, storage, network, exec, clone, or panic path. The new
boot-only AP is 25,733,161 bytes at SHA-256
`90a25e4a946e24a469380735aff5cdf250d2b107696353839a9030870e72b67b`;
its sole `boot.img.lz4` is 25,722,068 bytes at SHA-256
`17cf78f5ceef3ef1a69bc829190fb2e99ff47a692702faf4a82239e8aa9fefae`,
and decoded boot SHA-256 is
`dd4f1d0347983ac35f7d2692ff6fc4ad89ccc1a895b948bf7c330c736f6af073`.

For candidate dispatch, the endpoint census now completes first. Its finalizer
reconciles the pre-claim cage, after which the owner allocates a new journaled
candidate cage generation and returns only that generation to
`candidate-intent.json` and Odin. This preserves complete pre-claim closure,
intent-before-effect, one-shot consumption, and mandatory rollback while
removing the impossible reference to an already-reconciled cage.

The global registry also now distinguishes a synchronized host filesystem
device-number renumber from lock replacement. Only when both writer/session
locks move together and their activated inode, size, mode, link count, fixed
bytes, namespace, and complete append-only chain remain exact may `st_dev`
differ. A one-lock drift or any stable-field change still fails closed.

Host validation passes 74/74 focused owner tests, 9/9 registry tests, and
179/179 wider tests with ten historical TWRP skips. Host closure verdict is
`PASS_P0_HOST_CLOSURE_ONLY`, digest
`8473934c17a84a4aa827c13145ab56db692d01a0d76090780cdcaad9bc874797`.
At this snapshot the owner and observer were dormant and all old live
activation records remained retired. This H0 result by itself grants no
prepare, approval, device contact, reboot, Odin invocation, candidate claim,
transfer, or PID1 result.

## 2026-09-03 V3 live terminal

One earlier fresh preparation expired before candidate intent and closed
`ABORTED_PRE_CANDIDATE_RESIDENT_HEALTHY` with candidate/rollback attempts 0/0.
The next freshly prepared and approved run completed the byte-distinct V3
boot-only candidate transfer and proved process quiescence. The exact ACM
banner did not appear during the full bounded 180-second observation, so the
claim remains `NO_PROOF`; absence of the banner does not disprove native PID1.

The operator entered physical Download once. The fixed resident-Magisk boot
rollback transfer completed and exact rooted resident Android passed final
health. The terminal is `NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY`, SHA-256
`3e306e703a68017850b206221454c5d311fe7cc88daad62b6fb8f19b5d2f6193`.
Candidate/rollback attempts are 1/1, both replay permissions are false,
recovery-partition reads/writes/transfers and other-target commands are zero,
and the shared guard is absent. V3 is globally consumed. The owner and
observer are returned to dormant and the activation records are retained
under `workspace/private/retired/`; this exact profile grants no further
device action.
