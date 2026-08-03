# A90 Campaign Ledger

Append-only. One line per experiment action or material health/recovery state
transition under the Interim Fast-Loop Rules in `AGENTS.md`. This replaces
per-run prose reports for routine work only. It does not replace the private
structured result, append-only journal, raw logs, or transfer accounting
required by the selected tier and target contract.

For trial retirement, count only the first `CAMPAIGN_CLOSED` action row for
each distinct campaign ID across both ledgers. Duplicate close, parked, and
per-action health rows do not count.

Write a separate report only for a new capability, a new hazard class, an
incident, or a genuinely ambiguous device-safety result.

Metrics:

- information-bearing results per week: `PROVED + REFUTED`;
- information yield: `(PROVED + REFUTED) / all device attempts`; and
- observer no-proof rate: `NO_PROOF_OBSERVER / all device attempts`.

Device safety is recorded independently from experiment proof. A timeout or
late endpoint may be `HEALTH_PENDING`, `HOST_OBSERVER_FAILURE`, or
`RECOVERY_PENDING_PARKED` without closing the campaign.

## Format

`<UTC> | <campaign> | <ordinal> | <tier> | <action> | <HEALTHY|HEALTH_PENDING|HOST_OBSERVER_FAILURE|RECOVERY_PENDING_PARKED|RECOVERY_REQUIRED> | <PROVED|REFUTED|NO_PROOF_OBSERVER|N/A> | <candidate-transfers>/<rollback-transfers> | <one-line finding>`

## Log

<!-- append below; never edit or remove an earlier line -->
2026-08-02T19:42:06Z | a90-resident-switchroot-display-ssh-20260802 | 1 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | PROVED | 0/0 | Debian PID1, Dropbear SSH, direct DRM master, and operator-visible DISPLAY OWNER DEBIAN proved; exact resident return and cleanup passed; retained-pmsg observer warning
2026-08-03T04:05:39Z | a90-resident-switchroot-display-ssh-20260802 | N/A | D0 | RESIDENT_D0_PREFLIGHT | HEALTHY | N/A | 0/0 | Exact A90 pin, resident version and build, selftest fail=0, and source precheck exact; no handoff or effect; S22+ untouched
2026-08-03T04:40:04Z | a90-resident-switchroot-display-ssh-20260802 | 2 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | PROVED | 0/0 | Qualified unattended one-shot proved Debian PID1, Dropbear SSH, direct DRM master, automatic native return, cleanup, and resident health; physical visibility unavailable; no replay; S22+ untouched
2026-08-03T04:49:16Z | a90-resident-switchroot-display-ssh-20260802 | 3 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | PROVED | 0/0 | Second qualified unattended one-shot repeated Debian PID1, Dropbear SSH, direct DRM master, automatic native return, cleanup, and resident health; physical visibility unavailable; no replay; S22+ untouched
2026-08-03T06:05:24Z | a90-resident-switchroot-display-ssh-20260802 | N/A | D0 | RESIDENT_D0_PREFLIGHT | HEALTHY | N/A | 0/0 | Exact A90 ttyACM0 pin, resident 0.11.161 identity, selftest fail=0, immutable rootfs size and SHA256, and absent work path passed; no handoff; S22+ untouched
2026-08-03T06:14:24Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_B_QUALIFICATION | HEALTHY | N/A | 0/0 | Deterministic no-authority A/B replaced the operational Doom bridge with an inert ENOTSUP boundary; zero device contact, transfer, or flash
2026-08-03T06:21:38Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_B_SCOPE_FINDING | HEALTHY | N/A | 0/0 | Review limited PASS scope to the inert bridge API: inherited loop-start may fork and record audio before the API; global Doom command inertness is not claimed and caller removal continues H0
2026-08-03T06:27:43Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_B_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO qualifies the exact nine-entry inert bridge API until its implementation, API/output layouts, named semantics, or hazard state changes; caller-wide inertness excluded
2026-08-03T06:36:19Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_C_QUALIFICATION | HEALTHY | N/A | 0/0 | Deterministic no-authority A/B removed Doom menu and dedicated shell entry points, blocks video demo doom before caller effects, and removes both bridge implementations; review pending; zero device contact
2026-08-03T06:56:11Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_C_REVIEW_FINDING | HEALTHY | REFUTED | 0/0 | Subagent refused PASS_GO because generic CMD_DISPLAY dispatch could stop HUD and clear files before the handler reject; closure repaired with an earlier dedicated no-effect reject and requalification continues H0
2026-08-03T07:14:05Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_C_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO closes the repaired pre-dispatch no-Doom command surface and is reusable until any of 14 bound source/effect semantics changes or a new hazard or incident occurs; no device authority
2026-08-03T07:24:53Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_D_QUALIFICATION | HEALTHY | N/A | 0/0 | Deterministic no-authority A/B removes 11 boot-write/flash shell entries and two implementation objects while retaining current no-Doom semantics; Phase3-C receipt retired by three bound-source changes and combined review is pending; zero device contact
2026-08-03T07:27:14Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_D_REVIEW_FINDING | HEALTHY | REFUTED | 0/0 | Subagent refused PASS_GO because the a90_controller.c qualification pin contained one duplicated hex character; record repaired to the actual 64-digit SHA256 and review resumes H0; no source or device change
2026-08-03T07:37:38Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_D_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO closes the combined no-Doom and no-callable boot-write/flash surface over 15 bound sources; unknown-command effects remain explicitly outside scope; reusable until closure or named semantics changes or a new hazard or incident occurs; no device authority
2026-08-03T07:49:29Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_E_QUALIFICATION | HEALTHY | N/A | 0/0 | Deterministic no-authority A/B removes the dedicated cpustress shell/menu surface and app object while retaining generic run, helper, changelog, and longsoak paths explicitly out of scope; combined review pending; zero device contact
2026-08-03T07:59:48Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_MINIMAL_E_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO closes the combined inherited surface and dedicated native-init cpustress removal over 15 bound sources; helper, generic run, history, header, longsoak, and unknown-command effects remain explicit scope limits; no device authority
2026-08-03T08:05:25Z | a90-resident-switchroot-display-ssh-20260802 | N/A | D0 | RESIDENT_D0_HEALTH | HEALTHY | N/A | 0/0 | Fresh exact A90-LNX ttyACM0 pin, resident 0.11.161, selftest 12/1/0, PID1 guard 12/0/0, and bounded status passed; no effect, payload, or handoff; S22+ ttyACM1 untouched
2026-08-03T08:19:04Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_DEBIAN_NETWORK_SSH_QUALIFICATION | HEALTHY | N/A | 0/0 | Deterministic no-authority A/B separates return-arm from Debian sysvinit NCM/Dropbear ownership with bounded exact health markers; review pending; zero device contact
2026-08-03T08:21:45Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE2_FLAT_CLOSURE_PIN_REPAIR | HEALTHY | N/A | 0/0 | Focused replay repaired one stale host-only Phase2 manifest closure hash to the exact current Phase3-E expanded source closure; 42 retained/new tests pass; no source semantics or device action
2026-08-03T08:41:07Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_DEBIAN_NETWORK_SSH_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO closes exact Debian sysvinit NCM/Dropbear ownership, child-listener binding, and fail-closed cleanup over final ab-05 closure; reusable until closure/semantics change or new hazard/incident; no device authority
2026-08-03T09:05:19Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_NETWORK_SSH_KEYED_ROOTFS_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Fresh canonical -02 keying qualification and subagent PASS_GO close absent-only Ed25519/new-inode rootfs materialization; stale runs excluded; reusable until closure/semantics or hazard/incident changes; no device authority
