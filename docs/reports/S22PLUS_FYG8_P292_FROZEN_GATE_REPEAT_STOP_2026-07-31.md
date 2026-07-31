# S22+ FYG8 P2.92 frozen-gate repeat stop

Date: 2026-07-31 KST

Verdict: `STOP_P292_REPEATED_FROZEN_GATE_STALE_HOST_FAILURE`

Scope: host only. No manifest, D0, device control, Odin invocation, transfer,
or F1 authority was created or used.

## Completed evidence

- Run `029c8b1739f06242008c0a7657cef9e2` retains 93/93 exact payload-source
  receipts.
- Full-LTO A/B and all six payload artifacts are byte-identical.
- The final postbuild audit passes 7,077,888 validator inputs with exactly
  107 accepted positions, 171 accept-to-resume cases, 214 continuous-walk
  snapshots, and checkpoint errno observability.
- Candidate A/B boot images, compressed frames, boot-only AP archives, and
  artifact results are byte-identical. Each AP contains one regular member
  named `boot.img.lz4`.
- The first formal P2.92 static closure passed.
- Process-v2 registration selects the P2.92 decoder and stock closure and
  binds 93 payload, 52 qualification, and three live-tier receipts.

## Repeated failure

The frozen pre-LTO qualification rejects any changed gate implementation.
Earlier in this line, placing a noreturn CFG correction in the frozen P2.92
linked-audit file produced `P2.86 gate implementation is stale`; moving the
correction to the postbuild-only audit restored the frozen gate.

During downstream registration, a one-line terminal-stage adapter was placed
in the frozen P2.92 repair decoder. The next fresh static replay produced the
same `P2.86 gate implementation is stale` failure. Although the files and
immediate causes differ, both failures are the same material class: a
post-intent support correction changed a file whose bytes are bound by the
frozen pre-LTO qualification.

AGENTS.md rule 7 stops candidate experimentation when the same material
host-side failure occurs twice. No static retry, promotion, manifest, D0, or
live preparation follows this second occurrence.

## Restored state

The repair decoder was restored byte-for-byte to its frozen version. The
terminal adapter now lives in the Process-v2 evidence layer, which reads the
stage from the already-declared terminal position pair. Focused
accept-to-resume and Process-v2 tests pass. Host revalidation confirms:

- exact run ID unchanged;
- 93 payload source receipts present;
- frozen qualification verified;
- linked audit verified; and
- current Stage C inventory remains 52 Tier-2 and three Tier-3 receipts.

The existing Full-LTO and package artifacts remain valid. Promotion and D0
remain intentionally incomplete under the rule-7 stop. No S22+ F1 is
authorized.

## Preventive H0 guard

`s22plus_fyg8_p292_frozen_qualification_guard.py` now fails closed before a
future static or promotion replay if the exact frozen P2.92 qualification or
any implementation receipt bound by that qualification has changed. The guard
pins the complete qualification receipt, then stable-reads and byte-verifies
all 51 logical implementation entries. Those entries resolve to 50 unique
regular repository files; the only accepted alias pair is `linked_audit` and
`p292_linked_audit` over the same P2.92 linked-audit file.

The focused fault suite rejects a changed implementation, an unexpected path
alias, an indirect final path, and a changed qualification receipt. The exact
current qualification passes with `51/51` logical entries, `50/50` unique
paths, and zero changed bytes. This is a host-only recurrence-prevention guard.
It does not erase the two prior failures, lift the rule-7 stop, authorize a
promotion retry, or create D0/F1 authority.

## Scoped host-only re-entry

The operator subsequently issued a separate policy decision for run
`029c8b1739f06242008c0a7657cef9e2`. At guard commit `55e477a3`, it authorized
exactly one formal static closure and, only after that closure passed, exactly
one offline promotion. Any new failure ended the re-entry. D0 and F1 remained
unauthorized.

The exact frozen guard passed before the attempt with 51 logical entries, 50
unique files, and zero changes. The single static invocation then returned
exit status one in 3.57 seconds and emitted exact fail-closed error
`No such file or directory: 'aarch64-linux-gnu-nm'`. It created no static
result. The offline promotion was therefore never invoked and no promotion
directory, ready manifest, D0 evidence, or live authority was created.

The failure is an execution-environment preflight omission. The static CLI's
explicit GNU-tool arguments do not cover the fresh userspace sub-audit, which
resolves `aarch64-linux-gnu-nm` by basename. The controlled GNU binary exists
under the pinned private cross-tool directory, but that directory was absent
from the attempted process PATH. A post-failure guard rerun still passes with
zero changes, so no candidate or qualification byte moved. The policy's
explicit stop-on-new-failure clause prohibits retrying this attempt or
starting promotion.

## Static-environment recurrence control

The host-only `s22plus_fyg8_p292_static_environment_guard.py` now verifies the
complete nested tool-resolution surface before a future bounded attempt. It
first reruns the exact frozen-qualification guard. It then derives the six
userspace basenames from the frozen userspace builder, adds the linked
`aarch64-linux-gnu-objdump` and host `cc` consumers, and requires all eight
names to resolve from one explicit pinned environment.

The guard binds final GNU `nm` and `objdump` plus host `cc` to the passing
postbuild receipt and QEMU to the passing static receipt. It executes every
tool's version probe and a real two-build AArch64 smoke using the same
compiler-environment stripping as the nested userspace audit. The smoke proves
byte-identical static ELF output, `file`/`readelf`/`nm`/`objdump` acceptance,
strip, and QEMU exit zero.

Five focused tests cover the source-derived basename inventory, exact
resolution, missing `nm`, a pinned-name escape, and a baseline-receipt
mismatch. The actual build host passes with frozen implementation `51/51`,
unique files `50/50`, zero changes, eight resolved tools, and a 504-byte
byte-identical smoke binary. Its safety result explicitly records
`static_attempt_started=false`, `promotion_started=false`, and no D0/F1
authority. This closes the PATH recurrence mechanism but does not authorize a
second static attempt.

## Offline-promotion adapter closure

The H0 readiness audit also found that the historical
`prepare_s22plus_fyg8_p234_process_v2.py` CLI remains directly bound to the
P2.34 candidate checker and the historical E2 closure selector. Its common
implementation supports the P2.92 evidence model, but invoking that CLI
directly would reject the P2.92 static schema or source-contract ID before
creating promotion evidence.

`prepare_s22plus_fyg8_p292_process_v2.py` is a logic-free version adapter. It
binds that unchanged common implementation to the P2.92 static checker and
`s22plus_fyg8_p292_e2_stock_closure`, while retaining the existing promotion
schema, safety result, and `O_EXCL` evidence writes. The adapter and its focused
test are outside all 93 payload source keys and outside the frozen 51-entry
qualification implementation. Thirty-eight focused P2.92 and common
Process-v2 tests pass; the frozen mutation guard remains `51/50/0`.

This closes a future promotion-command ambiguity only. It does not execute or
authorize the stopped formal static replay, offline promotion, manifest, D0,
or F1.

The same readiness pass removes the remaining manual ready-manifest assembly.
`prepare_s22plus_fyg8_p292_ready_manifest.py` consumes only final private
promotion evidence and AP paths. Before its one `O_EXCL` manifest creation it
revalidates the P2.92 acceptance, source-derived candidate observer, candidate
and rollback archive policies, complete offline evidence contract, and a
private proposal through the unchanged Process-v2 bundle verifier. Seventy
focused promotion, manifest, evidence, F1-core, and D0 tests pass. The builder
and test are outside the 93 payload keys and frozen implementation; the guard
remains `51/50/0`. No manifest or device action was performed during this H0
validation.
