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
2026-08-03T09:41:02Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_RESIDENT_REFRESH_F1_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO closes exact V3406 start, Phase3 rootfs staging, one boot-only candidate, canonical V2321 rollback, and resident-install health over 25 bound sources after five host defects were fixed; reusable until closure/semantics or hazard/incident changes; no live authority
2026-08-03T10:13:51Z | a90-resident-switchroot-display-ssh-20260802 | N/A | D0 | RESIDENT_D0_PREFLIGHT | HEALTHY | N/A | 0/0 | Fresh exact A90 pin, resident 0.11.161 identity, selftest fail=0, pstore empty, direct NCM, candidate and rollback hashes, and three absent staging paths passed; no write, payload, reboot, handoff, or flash; other Samsung endpoint untouched
2026-08-03T10:33:49Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PHASE3_D1_SWITCHROOT_CAPABILITY_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO closes the 19-role Phase3 PID1, exact service and listener, key-only SSH, display, automatic return, cleanup, final-health, one-dispatch, and persisted-evidence capability; reusable until closure or related semantics change or a new hazard or incident occurs; no live authority
2026-08-03T11:02:55Z | a90-resident-switchroot-display-ssh-20260802 | N/A | F1 | PHASE3_RESIDENT_REFRESH_INSTALL | HEALTHY | NO_PROOF_OBSERVER | 1/1 | Exact candidate health passed, normal console/pmsg boot records tripped an overstrict empty-pstore observer, and exact V2321 rollback restored final health; no replay; other Samsung endpoint untouched
2026-08-03T11:27:37Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | PSTORE_CLASSIFIER_INCIDENT_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO closes malformed-line fail-open, source-audit, and legacy/new consumer compatibility over the combined 33-file F1/D1 closure; reusable until closure/semantics or hazard/incident changes; no device contact
2026-08-03T11:54:27Z | a90-resident-switchroot-display-ssh-20260802 | N/A | F1 | PHASE3_RESIDENT_REFRESH_GUARD_AUTH_ABORT | HOST_OBSERVER_FAILURE | NO_PROOF_OBSERVER | 0/0 | Exact -03 rootfs staged, then host pkexec guard authorization failed closed before candidate intent; run is STOP_RESUME and staged rootfs PRESERVE_INERT; no boot transfer, rollback, or replay; S22+ untouched
2026-08-03T12:00:10Z | a90-resident-switchroot-display-ssh-20260802 | N/A | D0 | POST_GUARD_ABORT_NATIVE_HEALTH | HEALTHY | N/A | 0/0 | Fresh -04 exact A90 ttyACM0 pin proved V2321, pstore entries=0, selftest fail=0, direct NCM, exact artifacts, and three new run paths absent; other Samsung endpoint untouched
2026-08-03T12:07:48Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | GUARD_AUTHORIZATION_INCIDENT_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO_NEW_CAMPAIGN_ONLY preserves -03 inert, forbids resume, requalifies unchanged 25-file closure, and permits only fresh -04 after exact host guard authorization; no device contact
2026-08-03T12:24:57Z | a90-resident-switchroot-display-ssh-20260802 | N/A | F1 | PHASE3_RESIDENT_REFRESH_INSTALL | HEALTHY | PROVED | 1/0 | Fresh -04 exact Phase3 rootfs and one boot-only candidate installed resident V3406; candidate replay false, rollback zero, final RESIDENT_HEALTHY; S22+ untouched
2026-08-03T12:43:09Z | a90-resident-switchroot-display-ssh-20260802 | 4 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | NO_PROOF_OBSERVER | 0/0 | Exact preflight passed but pkexec guard authorization timed out before handoff intent; dispatch zero, session permanently closed, resident V3406 healthy; S22+ untouched
2026-08-03T12:48:20Z | a90-resident-switchroot-display-ssh-20260802 | N/A | H0 | D1_GUARD_AUTHORIZATION_INCIDENT_REVIEW | HEALTHY | PROVED | 0/0 | Subagent PASS_GO_NEW_CAMPAIGN_ONLY classifies -06 as the same fail-closed host incident, forbids resume, and permits one fresh campaign after exact pkexec probe and zero guard residue; no device contact
2026-08-03T12:56:44Z | a90-resident-switchroot-display-ssh-20260802 | 5 | D1 | SWITCHROOT_EXPERIMENT | HEALTHY | PROVED | 0/0 | Phase3 Debian PID1, key-only SSH, exact service/listener, direct DRM master, operator-visible DISPLAY OWNER DEBIAN, automatic native return, work cleanup, immutable source, and final V3406 health proved; one dispatch, no replay; S22+ untouched
2026-08-03T12:57:45Z | a90-resident-switchroot-display-ssh-20260802 | N/A | D0 | SD_RUNTIME_CAPACITY_INVENTORY | HEALTHY | N/A | 0/0 | Exact A90 read-only inventory found work absent, 61408048 KiB total, 1765452 KiB available, and 54279768 KiB runtime use dominated by retained rootfs images; S22+ untouched
