# S22+ FYG8 P3.18 Post-Rollback Finalization Incident H0

Status: **PASS_GO_H0_CAPABILITY; RECOVERY_PENDING_PARKED; NO LIVE AUTHORITY**

Date: 2026-08-17 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`) only. A90 and S20+ inputs, authority, endpoints, artifacts,
and device actions are out of scope.

## Result before this H0 unit

The P3.18 Process-v2 attempt consumed its candidate and exact rollback once
each under approval binding
`fd68d3b4713d13afceaabdc5f97240f76808a5be2d09fc59b8853bcfd6e39136`.
The operator observed one normal candidate boot without a boot loop. The exact
300-second candidate observer then closed as `endpoint-timeout`, with no
selected endpoint and zero retained ACM bytes.

The normal unchanged-path rollback receipt is `rollback_bound_exact`: the
fresh rollback Download snapshot has `relationship=same`, is complete, and
permits rollback without reclassifying the experiment. Odin reported one
completed exact candidate transfer and one completed exact rollback transfer.
There is no candidate or rollback attempt 2.

The ordinary final-health path obtained two post-rollback reads before a local
correlation exception. Each read is 2,097,136 bytes, has empty stderr, and is
byte-identical at SHA-256
`4a0d9db45040fca213c9d2a6c730e28217d360809ed8c19c4748d682509cdd5e`.
The retained ring is integrity-clean but contains one E2 progress record, not
a P3.18 terminal:

- active generation: 46;
- stage: 101 (`S22_P313_POSITION_FINAL_WINDOW`);
- outcome/detail: 0/0;
- slot status: `valid`, `bad-body`;
- fallback used: true;
- Max77705 terminal count: zero; and
- classification: `E2_PROGRESS_OBSERVED`.

The fixed P3.18 candidate-end topology record is complete, has no endpoint,
and retains `causal_terminal_ready=false`. Its phase classifier therefore says
`NO_PROOF_OBSERVER_and_park`; rollback cannot retroactively change that proof
class.

## Failure mechanism

The actual ordinary sequence is:

1. exact rollback transfer completes and the journal reaches
   `ROLLBACK_FLASHED`;
2. the ordinary backend obtains fresh rooted FYG8 final-health reads;
3. it reopens the two identical retained raw reads;
4. `s22plus_fyg8_p318_max77705_telemetry_decoder.py` exposes no Max77705
   terminal row for the exact stage-101 record; and
5. `correlate_p318_candidate_receipt()` rejects the missing unique terminal
   before Process-v2 publishes `final_evidence`, `HEALTH_VERIFIED`, `CLOSED`,
   or `live-result.json`.

The error is after both transfers, not authority for either transfer again.
The 15-record append-only journal remains at `ROLLBACK_FLASHED`; candidate and
rollback replay are forbidden. The operator observation of normal boot is not
a substitute for the missing durable final-health receipt.

## Incident-specific finalizer

The new adapter is:

`workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_postrollback_finalize.py`

Its immutable public authority is:

`workspace/public/src/device-action/recovery/s22plus_fyg8_p318_postrollback_finalize_v1.json`

The finalizer is deliberately narrower than ordinary Process-v2 recovery:

- no Download request;
- no endpoint wait;
- no Odin invocation;
- no candidate or rollback transfer;
- no device write;
- only fresh exact-target Android health reads through the bound ADB binary;
- only the two existing byte-identical rollback-observer files; and
- only the existing Process-v2 journal and result publisher.

The exact stage-101 normalization is fail-closed. It requires the complete
single E2 progress record above, the exact candidate-end
`NO_PROOF_OBSERVER_and_park` decision, no causal terminal, no endpoint, and no
rollback reclassification. It emits `causal_result_allowed=false`; it cannot
turn the incident into a MUX, host-silent, or candidate-success claim.

Before any connected read, a separate exact approval must publish one atomic,
no-replace finalizer arm binding the parsed authority bytes, adapter bytes, the
15-record journal prefix, initial live state and journal head, both transfer
receipts, both raw reads, topology receipts, current decoder sources, and the
exact ADB executable. A different authority path or ADB path is rejected.

After arming, the only device operation is the existing bounded final-health
read path. A complete health receipt is atomically published before common
Process-v2 state changes. Re-entry supports the exact host-reporting cuts:
before health publication, after health publication, after live-state
publication, within the `HEALTH_VERIFIED` event tail, and after `CLOSED` but
before `live-result.json`. None repeats a boot transfer.

The exact initial `live-state` and `journal-head` bytes are also preserved as
mode-0400 private snapshots. Authority regeneration derives the mutable-path
identities from those immutable snapshots, so closing the journal does not
erase the reviewed pre-finalization boundary or make its receipt unreproducible.

The only admissible terminal is:

- verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`;
- outcome: `candidate_not_proven_rollback_verified`;
- proof class: `NO_PROOF_OBSERVER`;
- candidate transfers: 1;
- rollback transfers: 1;
- recovery required: false; and
- journal: `CLOSED` with exact final health.

## Exact reviewed H0 closure

Independently approved identities:

- finalizer: 51,413 bytes,
  `a23eafbd2f7be73fe2ac1ef20ed9a079683b047cd038c23749f6bf92cc3a3596`;
- authority: 12,635 bytes,
  `fc8556fb61601a575b95be17a20d57f5ba5677f909280be2220e961519e257c7`;
- tests: 19,216 bytes,
  `35926ce79b6a7696ee1cfc0a457d50569803b15a66c1e0ca0f428ba7b8ccda7b`;
- finalizer approval binding:
  `131c6d13ee7710b22b75cfe55381a612d1403c5e0013528e0e49d5ec38633751`;
- original Process-v2 execution closure:
  `fb4805c6828599d4d263a0c2ba77b9d9c8e3eb6593bd76dffd96f9370d9d27d4`;
  and
- candidate-end topology record: 1,494 bytes,
  `6fad6a0c0c90b51e4926471a48878f542f576dcc3afdbc144994864a95747c41`.

The canonical host-only `--validate` reopened the exact incident and returned
`PASS_P318_POSTROLLBACK_FINALIZE_HOST_READY_REVIEW_REQUIRED`, journal
`ROLLBACK_FLASHED`, transfer counts 1/1, no device contact, and no live
authority. Focused tests pass 21/21. The exclusive hardlink publisher also
repairs only its exact single same-inode final-plus-temporary crash cut back to
one durable link; ambiguous, foreign, or differently linked cuts stop closed.
Its fd-owned writer normalizes and verifies mode 0400 before publication even
under a hostile ambient umask.

Health commands execute only the already reviewed private D1 ADB snapshot,
716,968 bytes at SHA-256 `05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226`,
mode 0500 and link count one. The authority binds that stable repository-private
path directly rather than mutable system ADB. Every entry path, including
`CLOSED` result re-emission, reopens it; the connected path also reopens it
after the health command. `CLOSED` re-emission additionally requires the exact
finalizer arm and never creates a missing arm after the effect.
The same arm-before-health invariant is enforced by host-only validation and
the `ROLLBACK_FLASHED` health-publication cut: a present health receipt with a
missing arm is never converted into a newly armed run. Health receipt parsing
also requires `boot_id_sha256` to be a JSON string, not a decimal integer that
happens to spell 64 hexadecimal digits.

## Authority boundary

This implementation and its authority JSON do not authorize connected use.
Because this is incident-specific recovery/finalization machinery, its exact
changed closure required and received an independent safety review. That
`PASS_GO` qualifies only this H0 capability. Connected use still requires a
new, separate exact operator approval for binding `131c6d13ee7710b22b75cfe55381a612d1403c5e0013528e0e49d5ec38633751`.
The earlier F1 approval is consumed and cannot authorize this finalizer.

No device command, ADB command, reboot, Download request, Odin invocation,
partition transfer, candidate replay, rollback replay, A90 action, or S20+
action occurred during this H0 unit.
