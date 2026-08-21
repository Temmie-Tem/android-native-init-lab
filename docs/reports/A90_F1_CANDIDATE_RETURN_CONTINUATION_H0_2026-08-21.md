# A90 candidate-return continuation — H0 implementation report

Date: 2026-08-21
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only
Status: implemented, fixed backend wired; H0/non-authoritative

## Result

The candidate-neutral continuation is implemented in
`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py`.
It provides only fixed `prepare`, `resume`, and `finalize` modes. `prepare`
derives a fresh token without contact or journal writes. The core resume and
finalize state machine uses exact owner records, receipt joins, guards, strict
candidate/TWRP observations, intent-before-contact ordering, physical-action
confirmation only for the TWRP branch, and the existing one-shot rollback.

The fixed production backend is part of this H0 unit and is selected only by
the checked execution closure. Its availability is not authority:
`resume`/`finalize` still require a fresh independent review, current
qualification and manifest binding, an exact attended token, and the target
contract's live activation. No review JSON was added to the execution
closure, and this H0 task created no token or device contact.
The previous static live-availability value was removed. `review_gate_present()`
now recognizes only a direct regular canonical current `PASS_GO` review with
the exact closure and zero findings/contacts; absent, symlink, malformed,
wrong, or stale review stops before backend creation. The review file remains
outside the execution closure, and PASS alone still grants no token,
attendance, intent, or contact.
The backend performs only fixed USB/ADB inventory and exact A90 Native/TWRP
observations, never uses ADB on Native, never contacts another Samsung
endpoint, and never sends a host reboot. The operational precondition is
exactly one Samsung USB endpoint (`04e8`); non-Samsung host USB devices may
remain, but every other Samsung device must be disconnected before the
attended run. This is an A90 speed/safety precondition, not a permanent common
boundary; multi-device support is out of scope and requires a new design/review.
Native is exactly one `04e8:6861` endpoint with zero ADB rows. Recovery is
exactly one `04e8:6860` endpoint and exactly one total ADB row in `recovery`
whose serial hash matches the manifest. Extra Samsung/ADB rows, wrong
product/state, or ambiguity parks before per-serial contact.
Raw serials never enter receipts, logs, or tracked state. Owner mode persists
only fixed digest/length/status inventory markers and redacts registered
serials as `<A90-ADB-SERIAL-SHA256:...>`.
Owner mode registers the bound hash before the first inventory and persists
valid or invalid inventory stdout/stderr only as fixed digest/length/status
markers. Later registered command/exception/child output uses only
`<A90-ADB-SERIAL-SHA256:...>` markers.
The backend is contact-capable only through a continuation-issued activation
lease created after the durable phase intent and guard checks. The lease binds
the exact manifest/run/pending receipt/approval/phase and review/closure
callbacks; every public method and subprocess call validates it before and
after contact. Direct construction, fake sentinels, stale intent/guard state,
and restored review swaps fail before a runner call. This is a fail-closed
workflow API, not same-UID Python isolation. The activation intent callback
also rereads the strict current journal prefix, requires every envelope to bind
the current manifest, and requires the live 22/23 receipt join to equal the
activation-bound pending receipt; cross-manifest or substituted receipts stop
before contact.
The backend effect surface is rollback-only. Candidate or caller-selected
artifacts are rejected even when their SHA matches; the exact manifest-bound
rollback object must pass strict schema/type checks and direct regular-file
identity/hash checkpoints before and after the existing helper.
Native rollback additionally requires matching strict managed-bridge
preflight generations immediately before the helper; the owner helper repeats
the fixed preflight immediately before its sole Native recovery frame. A
present bound recovery endpoint does not invoke Native bridge recovery.
Immediately before the owner helper, both branches bind the complete raw
`/usr/bin/lsusb` output SHA-256 and the helper re-captures and compares it in
owner receipt mode before any ADB, bridge, push, or boot-write effect. This is
an owner-only pre-effect join; malformed/nonzero/surviving producers,
digest/role/single-Samsung drift, and recovery ambiguity stop with zero effect, while
legacy helper behavior remains unchanged.
For Native-to-Recovery, a separate pre-frame gate repeats the bound initial
USB/ADB raw digests and strict Native role/product immediately before bridge
preflight and the sole recovery frame;
post-transition Recovery validation is not being used to cover that gap. The
owner inventory binding is accepted only together with the fixed bridge-preflight
flag, so a verified pre-frame gate cannot fall through to the legacy bridge path.
The same owner-only pre-effect join now binds the complete raw
`/usr/bin/adb devices -l` digest and exact parsed A90 role
(`NATIVE_NO_RECOVERY` or `BOUND_RECOVERY_PRESENT`). The helper verifies both
before bridge recovery, per-serial ADB, push, or boot write; ADB state,
duplicate/extra endpoint, and initial raw-digest drift stops with zero effect.
The post-transition gate again requires exactly one Samsung `04e8:6860`
endpoint and exactly one bound recovery ADB row. Native-to-Recovery may change
product, bus/device numbers, and raw bytes; those returned digests are evidence
only and are not compared with the pre-recovery digest. Already-Recovery keeps
the same-epoch digest check before effect; multi-device coexistence is not
modeled.
On candidate PASS, the owner releases only the active-run guard; the
candidate-SHA guard remains present as the durable consumed no-replay marker.
Candidate and rollback health validation now requires the exact
manifest-bound qualification-review digest in `recoveryEvidenceSha256`; a
valid mismatched digest parks with no PASS or rollback-success terminal.
TWRP identity validation is exact-key/exact-type before equality and rejects
numeric bool/float/string substitutions without issuing a physical instruction.
Rollback now revalidates both guards after durable `31`; removing either guard
before flash results in zero backend effect calls and a no-replay park.
Continuation execution now leases both direct review identities/SHAs and the
continuation computed closure, revalidating around contacts, journal writes,
rollback, and the owner terminal release callback; same-byte swaps of either
review are rejected.
The qualification-review SHA is explicit in approval/intents without entering
the continuation execution closure, avoiding a self-reference cycle.
The owner terminal path now reopens and strictly validates durable `40` before
active-guard release; mutation, deletion, symlink, short/extra/duplicate, or
read failure retains guards and does not republish or retry.
The consumed H28 qualification review remains pinned at its original closure
`0dca4f3ddc98eb4625411c93ad7c1748f3c016aab0075a570652ca946fc4eb1f`; the current owner rejects it for a new run. H28
terminal-only readers validate the fixed historical review/manifest/journal
bytes (including review SHA-256
`51474c2d323971c07ca1425be613ea48cdd6c13f870606b166fba76835e6a9b2`)
without turning them into current qualification. A future H29 requires a
fresh qualification/review/manifest and current owner closure.

## Validation

- continuation/owner focused suite: `153/153` passed (the suite includes the
  shared owner regression corpus); fixed-backend hostile suite: `19/19` passed;
  adapter suite: `24/24`; USB identity hostile suite: `5/5`; owner receipt
  suite: `7/7`; bridge suite: `16/16`; combined continuation/backend/adapter/
  USB identity public suite: `201/201` passed;
- `test_native_init_flash`: `52/52` passed;
- H27/H28 qualification and recovery standalone suite: `112/112` passed;
- owner serial-redaction suite: `4/4` passed; combined helper/backend/
  continuation/native/redaction suite: `252/252` passed;
- `py_compile` passed for the continuation, fixed backend, USB identity,
  adapter, native helper, and owner modules;
- `git diff --check` passed.

## Boundary

Device, `/dev`, USB, network, `workspace/private`, S22+, and S20+ access were
zero. No image, reboot, physical instruction, rollback, candidate transfer,
approval token, ordinal, or live authority was created. No commit was made.
The first owner ADB inventory now uses a bounded two-pass capture. It registers
recoverable endpoint tokens, then persists every valid or invalid stdout/stderr
stream only as fixed SHA-256/length/status markers.
