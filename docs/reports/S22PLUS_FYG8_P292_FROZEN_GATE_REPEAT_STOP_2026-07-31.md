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
