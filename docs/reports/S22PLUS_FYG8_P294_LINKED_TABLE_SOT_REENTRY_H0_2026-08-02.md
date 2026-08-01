# S22+ FYG8 P2.94 linked-table SoT re-entry H0

Date: 2026-08-02
Tier: H0 only
Run: `dd20b502d5e45480b9f89c9b5e2232a2`

## Result

The third Rule-7 formal invocation ran exactly once and stopped before any
candidate packaging or device contact. The Full-LTO candidate did not fail.
The P2.94 linked-audit adapter rejected the valid P2.94 logical table because
its storage helpers delegated through P2.92 to a P2.90 verifier that compared
against the historical P2.90 table bytes.

The escaped exception was:

`P2.90 logical linked table set is invalid`

The redirected formal result is an empty file, size zero and SHA256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
No candidate A/B package, formal static result, promotion, ready manifest, D0,
Odin session, device write, or F1 followed.

## Repair

The P2.94 linked adapter now derives its accepted logical table directly from
`s22plus_fyg8_p294_source_contract.linked_table_bytes()`. It no longer delegates
P2.94 storage-table validation to the historical P2.90 table predicate.
Physical linked bytes must still equal the current logical table exactly.

The formal entry point now catches the linked-audit `AuditError` and emits a
structured `FAIL_CLOSED` JSON result instead of allowing a traceback to leave
an empty receipt.

The frozen-qualification re-entry gate binds the exact P2.94 linked-audit
delta for both alias names, while all other frozen gates remain exact. This is
the linked-audit instance of `CHECKPOINT_SOT_COHERENCE`: the current campaign's
declaration is the table SoT; an ancestor campaign's value is an explicit
negative control, not an inherited acceptance predicate.

## Validation

- candidate contract: `PASS_P294_CANDIDATE_CONTRACT_HOST_ONLY`;
- Tier-1 identity: `103/103`, `CHANGED_KEYS=[]`;
- current declared linked tables accepted and normalized byte-exactly;
- historical P2.90 linked tables rejected;
- one-byte physical table drift rejected;
- escaped linked-audit error rendered as structured `FAIL_CLOSED`;
- P2.94 contract focused suite: 10/10 pass;
- P2.94 Tier-2 re-entry focused suite: 4/4 pass; and
- frozen-qualification re-entry: 50 implementations, 49 unique paths, exact
  declared deltas for observer plus the two linked-audit aliases, all other
  gate receipts unchanged.

The linked-audit and formal verifier remain outside the 103-key payload
identity. The intent, run ID, kernel, and byte-identical Full-LTO A/B outputs
remain valid.

## Re-entry rule

Future approval text distinguishes host qualification from device-adjacent
execution. Before the first candidate package attempt and before device
contact, a first material host/verifier failure follows AGENTS.md rule 7: it
may be diagnosed and repaired in H0 when the payload identity remains exact;
the same material failure a second time stops the line. Once packaging or a
device-adjacent step begins, an unexplained new failure stops the approved
sequence. No such approval grants F1, Odin, or a device write.
