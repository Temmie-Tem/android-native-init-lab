# S22+ FYG8 P2.94 Rule-7 source-shape re-entry stop H0

Date: 2026-08-01 KST

Scope: one exactly approved host-only formal re-entry attempt, its immediate
fail-closed stop, and post-stop read-only attribution. No candidate package,
promotion, manifest, connected read, device command, Odin invocation, Download
transition, partition transfer, reboot, D0, D1, or F1 occurred.

## Result

The approved P2.94 formal build-repro invocation ran exactly once and returned
`FAIL_CLOSED` before package construction or linked/static promotion. Its exact
error was:

```text
FYG8 source tree is missing or indirect
```

The private failure receipt is
`workspace/private/outputs/s22plus_fyg8_p294/build-repro-result.json`, size
`131`, SHA256
`cca7f4268ff7874b16f88597920197b4f49885891f0ae8094cbd5428cdee5392`.
The explicit stop-on-new-failure condition ended that approval scope. The
formal command was not retried, and candidate A/B, static result, promotion,
ready manifest, and connected D0 outputs remain absent.

## Attribution

The candidate and Full-LTO artifacts did not fail. The invocation supplied the
P2.94 source-contract Python file as `--source`. That option is not the source
contract selector; it is the exact FYG8 kernel source tree consumed by
`candidate_intent.audit_patch()`. The production source of truth is
`s22plus_fyg8_p294_candidate_intent.DEFAULT_SOURCE`, which resolves to:

```text
workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae
```

That path exists as a direct directory, both P2.94 driver reference files are
direct regular files, and their frozen source receipts remain intact. The
failure was therefore a host invocation input-shape error before candidate
contract completion, not a payload, A/B, linked-artifact, or device failure.

## Approval-window correction

The next production command must not restate this source path by hand. It must
run from the repository root and omit `--source`, thereby consuming the
versioned producer default. Outside any approval scope, the exact P2.94
candidate-contract CLI was executed with that default and the real immutable
intent and patch. It passed:

```text
schema  = s22plus_fyg8_p294_candidate_contract_v1
verdict = PASS_P294_CANDIDATE_CONTRACT_HOST_ONLY
run_id  = dd20b502d5e45480b9f89c9b5e2232a2
```

The private preflight receipt is
`workspace/private/outputs/s22plus_fyg8_p294/rule7-source-shape-preflight.json`,
size `25223`, SHA256
`07d5bd32cb9ac2150d4ba731461b9a7ac6e32ed073d8c1fefb2b02231cd0bced`.

Any new formal attempt requires a fresh exact Rule-7 approval. It must write a
new result path rather than overwrite the preserved failure receipt, stop on
any new failure, and still grants no F1 authority.

Verdict: `NO_PROOF_P294_RULE7_FORMAL_REENTRY_SOURCE_SHAPE_STOPPED_H0`.
