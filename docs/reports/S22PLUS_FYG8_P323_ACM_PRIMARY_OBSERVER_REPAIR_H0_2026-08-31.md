# S22+ FYG8 P3.23 ACM-primary observer repair H0

Date: 2026-08-31

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_GO_P323_PROCESS_V2_H0`; host capacity restored and corrected prepare pending

## Finding

P3.22 did not retain a torn Carrier slot. Independent byte-level reanalysis of
both identical post-rollback reads shows valid CRCs for the header and both
slots. The actual transition is generation 92 stage `0x8f`/item 4 progress to
generation 93 stage `0x90`/item 0 failure `0x6726`. The older host semantic
model called the second slot `bad-body` because it did not admit this P3.13
intermediate contradiction route.

The runtime reached `p319_stock_publish()` with an open raw gadget TTY, but the
publisher discarded `tty_fd`. Its stock witness encoder then rejected before
the repaired Carrier bridge. The exact rejected encoder predicate was not
retained. This is two separate defects: the candidate had no direct host
arrival signal, and the retained host decoder mislabeled a valid producer
failure as integrity damage.

The consumed P3.22 formal verdict remains
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; it is not replayable. The correction is
post-live H0 interpretation, not retroactive F1 success.

## Minimal P3.23 repair

P3.23 changes one publisher-entry line. It attempts the existing exact
49-byte, run-bound CDC ACM banner once before witness copy and stock encoding.
The Carrier path always continues unchanged afterward.

The two evidence axes are now explicit:

- Exact ACM receipt: proves native PID-1 reached the post-bind publisher and
  the candidate-bound USB ACM path reached the host.
- Retained Carrier: supplemental Max77705 experiment result or producer-failure
  diagnostic; it cannot erase ACM arrival and ACM cannot promote its missing
  scientific result.

The host terminal class for a complete candidate transfer, exact ACM receipt,
Download departure, topology continuity, guard release, exact rollback, and
healthy final return is
`PASS_F1_V2_ACM_PRIMARY_NATIVE_PID1_USB_ARRIVAL_AND_ROLLED_BACK`. Missing,
partial, extra-byte, wrong-endpoint, topology-drift, guard-failure, or
failed-transfer cases remain no-proof. Existing manifests retain their prior
ACM/Carrier precedence unless they explicitly bind the new versioned role.

## Host build

Private output:
`workspace/private/outputs/s22plus_fyg8_p323/stock-candidate-build-v1-20260831-03`

- Run ID: `c323f1e0a90b5e6d7c8a9b0c1d2e3f4b`
- Result: 39,365 bytes,
  SHA-256 `94075654a8bc4356b1bcda9a5abd822b13a2fe558647d1eaf2810d684e45e3ea`
- Candidate AP A/B: 27,279,401 bytes,
  SHA-256 `5f34e26cb2a0554a6f082ea18848f9a25f1149a38078ef3a5db94552b4040293`
- Image: 41,490,944 bytes,
  SHA-256 `0684c512f77dd4c3659a07fb16eb40fe2b32609483aa9823d7dae450e08925bf`
- Static `/init`: 80,552 bytes,
  SHA-256 `374b4a843e938a87b09754f49b55c2d85bf62f098f656235815932ad148e8bfd`
- Rollback: unchanged exact boot-only AP,
  SHA-256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

The A/B artifacts are byte-identical and contain only `boot.img.lz4`; P319
through P322 identities are rejected. The build and audit-only reopen both
pass. The failed first presentation output and one `/tmp`-exhausted partial
attempt are preserved privately and are not readiness inputs.

## Process-v2 registration

P3.23 is registered under its exact overlay, run ID, adapter source, and
ACM-primary role. A Carrier parser exception is retained as supplemental
`P323_STOCK_PARSER_EXCEPTION`; it cannot discard an accepted ACM receipt or
promote a Max77705 result. The exact CRC-valid `0x6726` transition remains the
separate non-success class `P323_STOCK_ENCODER_FAILURE`.

- Candidate-static: 22,258 bytes, SHA-256
  `67bd51665ccb8b6c8e56801fe9a9648a7611029115f6e05ed436aa040107004d`
- Run manifest: 1,021 bytes, SHA-256
  `836c89621ee6d6935bf2eafa67dc6a9bf708c80e9dd33f93c88371c3d10489f4`
- Static check: 1,835 bytes, SHA-256
  `aa6586ee92ee191e8b9c05201973645124871e1b0ed65b74117d628bb2a1dddc`
- Ready manifest: 3,327 bytes, SHA-256
  `ef8bd5ad6b5b525d77fb69f8d6e24c39900ebf6a2635a07049fd14ea1b37c2ef`

The private outputs are mode `0400`, their promotion directory is `0700`, and
the tracked ready manifest is `0644`. Ready remains a data declaration, not
device authority.

## Validation and boundary

The P323 runtime/artifact/adapter/builder/reanalysis/static/ready suites pass
26 tests. The common evidence, Process-v2, and live suites pass 131 tests,
including exact-role, parser-exception, encoder-failure, and unchanged legacy
behavior. The P322 ready regression passes 3 tests. Python compilation, actual
AArch64 static compilation, deterministic A/B packaging, and diff checks pass.
Independent review returned `PASS_GO` for the exact Process-v2 closure with no
blocker or unnecessary new gate. The combined H0 status is
`PASS_GO_P323_PROCESS_V2_H0`.

The global raw-first current-tree smoke is not counted as a P3.23 failure. It
currently stops on the separately added S20+ host builder
`build_s20plus_g986n_recovery_adb_canary_h0.py`; none of the P3.23 sources is
the reported boundary bypass. That cross-target census coupling is left to the
S20+/auditor owner and is not carried forward as another P3.23 gate.

The host build and registration issued no device command. The connected stop
below performed bounded read-only D0 contact but no write, reboot, Odin command,
payload transfer, or approval. It grants no D1, F1, recovery, replay, or live
authority. P3.23 now requires one corrected connected preparation and a fresh
attended approval before any live action.

## First connected prepare stop

The first fresh prepare contacted the exact healthy target read-only and
stopped before `prepared.json`, approval, reboot, Download, Odin, or transfer.
Its durable D0 stop retained the 2,097,136-byte baseline at SHA-256
`3d186a2a46cdca7eed219d6a915906322d3c2da001e7380b3a75e8b52ef7b4e2`.
That is the consumed P3.22 CRC-valid producer-failure receipt, not a current
P3.23 record.

The first bounded Rule-7 correction admits only that complete raw identity, its exact
P3.22 reanalysis, and Carrier offset 1,634,466 as “current P3.23 run absent.”
Short, appended, shifted, padding-mutated, corrupt, arbitrary predecessor, and
current-P3.23 baselines remain rejected. Common tests pass 131/131 and focused
independent review returned `PASS_GO`.

That corrected prepare passed classification but stopped at the generic D0
result validator, which redundantly required `marker_family_count == 0` before
recomputing the bound raw classification. It also created no `prepared.json`,
approval, write, reboot, Download transition, Odin invocation, or transfer.
The second bounded correction removes only that duplicate zero check;
`exact_marker_count == 0`, `baseline_clean == true`, and the existing exact raw
reclassification comparison remain mandatory. D0 tests pass 23/23, ready audit
passes, and independent review returned `PASS_GO`. One final corrected prepare
remains; neither correction creates F1 or replay authority.

## Final corrected prepare host stop

The final corrected prepare did not create a new live run directory. Runtime-bound
candidate-static regeneration stopped in the inherited P3.21 candidate-A cpio
listing audit; the outer runner reported `P3.23 candidate-static authority rejected
the result`. At that point `/tmp` was 98% used with about 199 MiB free, while this
audit path has previously required substantially more temporary capacity. This is
a host pre-session capacity failure, not USB, target, candidate, or observer
evidence.

No `prepared.json`, approval, reboot, Download transition, Odin invocation,
candidate transfer, or rollback transfer was created. The runner was not retried.
Before another prepare, provide a bounded private temporary directory with enough
space and pass the same runtime-bound audit once; then a fresh prepare may issue a
new exact approval binding.

On 2026-09-01, four stale P3.20 failed-build scratch directories under `/tmp`
were confirmed owned by the operator, inactive, and free of open handles, then
removed. No P3.19, A90, S20+, browser, repository, private run-evidence,
candidate, or rollback path was removed. Available `/tmp` capacity increased
from about 3 MiB to 2.2 GiB. The exact P3.23 runtime-bound candidate-static
regeneration then passed host-only with `device_contact=false`,
`odin_invoked=false`, and `live_authorized=false`. Its temporary audit directory
was removed after completion. A fresh connected prepare, not a reused stopped
run, is the next step.
