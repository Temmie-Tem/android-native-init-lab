# A90 Phase 3 D1 switch-root capability qualification

Status: `H0_PASS_GO_CAPABILITY_QUALIFIED_NO_LIVE_AUTHORITY`

Date: 2026-08-03

## Decision

The A90 resident D1 transaction is qualified for the exact Phase 3
`phase3-network-ssh-v1` rootfs and the reviewed 19-role execution-critical
closure. The independent review verdict is `PASS_GO` with no unresolved
finding.

The canonical reusable review receipt is
`A90_UNATTENDED_RESIDENT_D1_RUNNER_INDEPENDENT_REVIEW_2026-08-03.json`.
Its reviewed closure digest is
`d0a54719756c4ef6bdb2e0ed785c781ff09b68fc6d267bc8a19cd11be94ac5fc`
and its receipt SHA256 is
`42ab84d63c4fb8b524345e7bac8e792d08b7e7eb595652a629372f0f6ca3fd25`.

This `PASS_GO` qualifies the capability rather than an ordinal, manifest,
qualification, or campaign. Reuse ends only when a reviewed role's path,
size, hash, or execution meaning changes; a relevant AGENTS/A90 target
contract meaning changes; or a new hazard or incident occurs.

## Qualified proof boundary

The transaction must prove all of the following as one bounded result:

- exact resident V3406 starting and returned health;
- one durable intent and at most one no-payload D1 handoff dispatch, with no
  replay;
- Debian `/usr/sbin/init` as PID1;
- the exact Phase 3 sysvinit service marker and absence of any failure path;
- the current Dropbear PID and executable, one exact listener endpoint, and
  the listener's owning PID;
- one manifest-bound, public-key-only SSH session over the direct A90 NCM
  interface;
- native display release and Debian direct DRM acquisition;
- automatic native return, exact work cleanup, exact source recheck, and final
  resident health.

The first Phase 3 qualification remains attended and must include physical
operator evidence of `DISPLAY OWNER DEBIAN`. Only that exact qualified
evidence may later feed the reviewed one-ordinal unattended runner. A boolean
or summarized service claim cannot bootstrap qualification: the persisted raw
ready, failure, and live sections are reparsed and must exactly agree with the
structured result.

## Review findings closed

The final closure fixes every independent-review finding:

- stale Phase 2 review hashes and missing Phase 3 observer role;
- a resident-journal validator shape that did not match the production
  resident-install producer;
- empty, unreadable, or symlinked failure paths being confused with absence;
- substring-only health, cleanup, and source evidence;
- persisted Phase 3 summaries not being independently reparsed; and
- Python boolean/integer equality accepting malformed sequence, ordinal,
  interface-count, health-count, or dispatch-count evidence.

The exact production CMDV1 framing is retained while requiring one and only
one full-line success marker from the manifest-bound shell command.

## Validation

- focused Phase 3 observer, attended D1, and unattended D1 tests: `57/57`
  PASS;
- related A90 execution-closure modules, run in isolated module processes:
  `430/430` PASS;
- prior production resident-install journal, 11-record shape replay: PASS;
- generated Phase 3 SSH shell syntax: PASS;
- F1 production default inspection: `contract_issues=[]`,
  `device_contact=false`, resident install ready for approval;
- Python compilation and `git diff --check`: PASS.

The broad A90 discovery run also exposed two unrelated host prerequisites: a
stale Phase 2C pinned native-manifest hash and an absent private kernel
`gfp.h`. Neither belongs to this capability closure or authorizes a device
effect.

## Authority and isolation

This report and receipt are H0 evidence and grant no live authority. The
prepared boot-only F1 still requires current operator attendance and a
demonstrated Download-or-TWRP recovery path. A fresh exact A90 USB inventory
and realpath pin is required immediately before F1. S22+ evidence, endpoints,
commands, and concurrent repository changes are outside this qualification
and remain untouched.
