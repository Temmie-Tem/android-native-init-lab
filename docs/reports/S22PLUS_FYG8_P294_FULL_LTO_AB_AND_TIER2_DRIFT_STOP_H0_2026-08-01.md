# P2.94 Full-LTO A/B and Tier-2 drift stop H0

Date: 2026-08-01

Verdict: `STOP_P294_POSTBUILD_TIER2_OBSERVER_DRIFT_HOST_ONLY`

P2.94 run `dd20b502d5e45480b9f89c9b5e2232a2` retains its immutable
103-key payload identity. Its `21/21` pre-LTO qualification passed on the
qualified build host. Full-LTO A and B then completed without swap, each in
about 44 minutes, with the same 41,490,944-byte `Image` and 1,536 bytes of
configured slot slack.

All nine preserved artifacts are byte-identical across A and B. The principal
receipts are:

- `Image`: `8161a50d0eb5acea89a0c4a3343d73236a59c1223dee55840e5c8695587bb719`;
- `Image.lz4`: `633d63b5e9549fdabeba451c1efb3e969b5af0de421e16355f64d0e975c3c3c2`;
- `vmlinux`: `26b71c17fc1a30c5d871805193d8c5f9fa758cb0b55b6557471cd8d5b3f19f30`;
- `System.map`: `7fd41ce28e9e4a5a5778fad60c83dfe98e89c19ca9e28a1b28fe584d5ff38e0e`;
- `.config`: `7c439fa784d4c7a021894f6a4bab43423ab5ac1dfa66c9a907ef953dad0baada`.

The A-only private-path gate passed before B. It found zero random private
namespace strings and zero absolute host clang-resource strings in `Image` and
`vmlinux`; the mapped clang-resource spelling occurred 138 times as expected.
No selected payload source changed during either build. A post-build source
receipt check still reports exactly `103/103`, no missing or extra key, and
`CHANGED_KEYS=[]`.

## Formal closure stop

The final build-repro invocation fails closed with:

`P2.86 gate implementation is stale`

This is not a kernel, candidate, or A/B reproducibility failure. The stored
P2.94 qualification was created after commit `9b062785` and binds the shared
observer as:

- path: `workspace/public/src/scripts/revalidation/device_action_cdc_acm_observer_v1.py`;
- SHA256: `a2536c44f8585cb41e58eab97c4bb97e4f957533139c847b49f55ef729f7586a`;
- size: 51,304 bytes.

Later A90 commit `28515909` changed only that observer entry in the current
51-entry gate-implementation closure. It raised the maximum guard duration
and added the runtime-rule path constant, producing SHA256
`6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9`
and size 51,402 bytes. That commit occurred after qualification and after the
P2.94 payload implementation commits. The observer is absent from all 103
Tier-1 SOURCE_KEYS; its change cannot alter run ID or built bytes.

The failure is therefore post-qualification Tier-2 drift. It is nevertheless
the same frozen-gate stale failure class that previously stopped P2.92, so
AGENTS.md rule 7 stops candidate experimentation. The earlier exact-inventory
and private-GNU-loader setup failures are retained as diagnostic receipts and
were not converted into a passing result.

## Consequence

The P2.94 intent and byte-identical Full-LTO pair remain valid evidence. Formal
static closure, promotion, package construction, ready manifest, D0, approval
binding, and F1 are not passed or authorized. No device was contacted and no
Odin or partition action occurred.

Any re-entry must be a separately bounded host-only unit that reconciles the
qualification-bound Tier-2 closure without changing the 103 payload receipts
or rebuilding the already byte-identical A/B pair. It must not weaken the
stale-implementation comparison merely to obtain PASS.
