# S22+ FYG8 P2.46 E2 provider F1 live progress

Date: 2026-07-24 KST
Tier: F1 boot-only candidate plus mandatory rollback
Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
Final state: `CLOSED`
Live authority: consumed

## Result

One exact P2.45 E2 boot-only candidate and its preapproved exact Magisk
rollback were transferred once. Two byte-identical retained reads decoded one
exact E2 progress record. Its active slot is generation 75 at stage `0x82`,
item index 7, outcome progress. Its fallback slot is generation 74 at stage
`0x81`, item index 6.

The source contract maps those stages to successful `apps-rpmh-cxlvl` and
`apps-rpmh-mxlvl` predicates. This proves that the P2.43 provider correction
passed the old P2.42 RPMh timeout boundary and reached the eighth of twelve
provider/USB gates.

No terminal success or failure record was stored. The strict acceptance policy
therefore classified the observation as `E2_PROGRESS_OBSERVED`, did not accept
the candidate, and closed the transaction as
`candidate_not_proven_rollback_verified`.

The operator observed no candidate boot loop. Final Android, root, boot,
supporting partitions, and Odin absence passed. The binding and approval are
consumed and cannot be reused.

## Exact Live Boundary

The complete retained reads were byte identical and contained:

- one exact record for the candidate run identity;
- both A/B slots valid with no fallback use;
- active generation 75 at `0x82`, item index 7, outcome progress;
- preceding generation 74 at `0x81`, item index 6, outcome progress;
- zero success, failure, UNSAT, foreign, historical, malformed, partial,
  delimiter-mismatch, or unterminated records; and
- no integrity issue.

The exact stage map is:

```text
0x40..0x7a  all 59 exact module insertions and prefix checks passed
0x7b        hwspinlock passed
0x7c        smem passed
0x7d        cmd-db passed
0x7e        psci-domain passed
0x7f        apps-rsc at 17a00000.rsc passed
0x80        apps-rpmh-clock passed
0x81        apps-rpmh-cxlvl passed
0x82        apps-rpmh-mxlvl passed
0x83        no stored outcome
```

The run did not prove `gcc-waipio`, SSUSB, DWC3 core, UDC, USB enumeration, or
transport.

## Deterministic `0x83` Contract Blocker

The retained result alone does not prove why execution stopped after `0x82`.
The runtime rechecks every previously completed gate before checking the next
one, and the record cannot exclude a reset or a stop before submission of the
next checkpoint. It therefore provides no `gcc-waipio` result.

Independently, the exact candidate contains a source-contract defect that makes
every normal `0x83` checkpoint unrecordable:

P2.44 correctly extended:

- the userspace gate table from 8 to 12 entries;
- the userspace and decoder stage range through `0x86`; and
- the kernel stage sequence tail from `0x82, 0x8f` to
  `0x82, 0x83, 0x84, 0x85, 0x86, 0x8f`.

It did not extend this kernel request validator:

```c
if (request->stage >= 0x7b && request->stage <= 0x82)
        expected_item = request->stage - 0x7b;
```

If userspace reaches the next successful gate, it submits
`stage=0x83,item_index=8`. The stale kernel range leaves `expected_item` at
zero, so `s22_fyg8_e1_request_allowed()` must reject that request and the proc
writer must return `-ERANGE`. The userspace checkpoint call would then return
nonzero and the runtime would deliberately enter `quiet_park()`.

This is a deterministic blocker for all progress beyond `0x82`, but the
retained evidence does not prove that this particular boot actually submitted
the rejected request. It proves `0x82` success and no later stored outcome.

The next correction is bounded: extend the kernel item-index range through
`0x86` and add a static source/linked check that every profile-3 gate stage maps
to `item_index = stage - 0x7b`. Do not change the module plan, gate paths,
timeouts, transport, or evidence format.

## Transfer, Recovery, And Health

An initial host invocation omitted the explicit candidate manifest and was
rejected during local manifest validation. It created no journal, Odin session,
Download transition, transfer, device write, or approval consumption. The
corrected invocation used the already prepared immutable binding.

The candidate and rollback transfers each completed exactly once. Final health
verified:

- Android boot completion and stopped boot animation;
- the exact expected Magisk boot identity;
- root availability;
- the expected unlocked verified-boot state;
- exact pinned `vendor_boot`, DTBO, and recovery identities; and
- no Odin endpoint remaining.

The append-only journal closed with 19 records and all eight canonical timeline
events in order:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
rollback_boot_ready
live_session_end
```

## Next Bounded Unit

P2.47 is H0-only:

1. extend the exact kernel item-index range from `0x82` through `0x86`;
2. add source, generated-patch, decoder, and linked-binary checks that reject
   any gate-count/item-range mismatch;
3. replay the captured P2.46 record and the full reachable transition model;
4. independently review the changed execution-critical closure; and
5. build a new candidate only after that correction passes.

Any later F1 requires a new reproducible candidate, clean connected D0
preparation, and a fresh exact approval.
