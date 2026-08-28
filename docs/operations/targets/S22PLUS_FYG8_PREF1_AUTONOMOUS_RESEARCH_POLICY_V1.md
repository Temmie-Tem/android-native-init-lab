# S22+ FYG8 pre-F1 autonomous transient action catalog v1

Status: **DEFINED / NOT ACTIVE** (`DEFINED_NOT_ACTIVE`)

Date: 2026-08-29

This is the normative definition for the exact Samsung Galaxy S22+ FYG8 target
`SM-S906N` / `g0q` / `S906NKSS7FYG8`. It is not a runner, coordinator,
activation manifest, approval, or live binding. It grants no current D0, D1,
F1, recovery, or device authority. The common and target contracts remain the
higher-precedence binding layers.

## Scope and proportionality

One fresh attended session activation may replace per-ordinal D1 approval only
inside this finite, monotonic catalog campaign. This is a single-owner
personal lab with a trusted local OS/user, physically controlled host/device,
and private evidence outside hostile principals. The relevant hazards are
mistakes, stale or wrong target selection, accidental parallel drift, duplicate
or uncertain effects, missing recovery, and any observed hazard class.

Malicious same-UID replacement between individual syscalls is out of scope.
Absent a concrete incident, this policy does not require per-syscall
inode/symlink/hardlink race defenses or enterprise multi-principal controls.
The intended implementation is one coordinator using existing target-selection,
raw-first observer, and journal helpers plus declarative descriptors; there is
no bespoke per-action runner or review ladder. One campaign activation manifest
is required, not one manifest per action.

## Normative declaration

The JSON below is the review/test declaration, not an activation manifest. Its
false activation fields are intentional.

```json
{
  "schema": "s22plus_fyg8_pre_f1_autonomous_action_catalog_v1",
  "status": "DEFINED_NOT_ACTIVE",
  "target": {
    "model": "SM-S906N",
    "device": "g0q",
    "build": "S906NKSS7FYG8",
    "other_target_commands": 0
  },
  "activation": {
    "mode": "one_fresh_attended_session",
    "catalog_hash": "required_at_activation",
    "effect_core_hash": "required_at_activation",
    "mechanically_activated": false,
    "activation_manifest_present": false,
    "live_session_approval_present": false,
    "current_live_authority": false,
    "implicit_activation": false,
    "operator_attendance_after_activation": "not_required_until_park_or_close",
    "operator_return_required_on_park": true,
    "requires": [
      "exact_coordinator_runner",
      "versioned_catalog",
      "hostile_tests",
      "independent_pass_go",
      "activation_manifest",
      "fresh_attended_live_session_approval",
      "exact_live_target_and_topology",
      "exact_current_healthy_boot",
      "immutable_effect_core",
      "positive_finite_budgets",
      "immutable_expiry"
    ]
  },
  "campaign": {
    "finite": true,
    "monotonic": true,
    "renewable": false,
    "resettable": false,
    "one_open_campaign": true,
    "new_campaign_requires_fresh_activation": true,
    "f1_requires_campaign_closed": true,
    "d1_effect_max": 8,
    "d1_effect_max_scope": "aggregate_per_campaign",
    "d0_command_group_max": 256,
    "d0_command_group_max_scope": "aggregate_per_campaign",
    "duration_seconds": 43200,
    "journal_root": "workspace/private/runs/s22plus-pref1-autonomous-research",
    "exclusive_campaign_guard": "required_single_coordinator",
    "intent_publication": "atomic_no_replace"
  },
  "catalog": {
    "classes": [
      {"id": "bounded_raw_first_read", "tier": "D0"},
      {"id": "normal_android_reboot_health", "tier": "D1"},
      {"id": "payload_free_download_roundtrip", "tier": "D1", "eligibility": "automatic_return_proof_required", "return_command": "/usr/bin/odin4 --reboot -d <bound-endpoint>", "payload": false},
      {"id": "fixed_privileged_usb_role_or_udc_transient", "tier": "D1", "privileged": true, "descriptor": "fixed_literal_node_and_value_bound_at_activation", "restore_or_reboot_proof": "required"}
    ],
    "activation_descriptor_requirements": {
      "payload_free_download_roundtrip": ["fixed_entry_argv", "pre_entry_zero_download_endpoints", "unique_bound_post_entry_endpoint", "fixed_payload_free_return_argv"],
      "fixed_privileged_usb_role_or_udc_transient": ["fixed_executor_identity", "direct_node_type", "exact_node_path", "exact_before_value", "exact_write_value", "exact_after_value", "exact_restore_action", "exact_restored_value", "exclude_debug_or_security_nodes"]
    },
    "android_recovery_entry": "eligible_only_after_automatic_return_proof"
  },
  "effect_accounting": {
    "pre_intent_host_failure_consumes": false,
    "intent_is_immediately_before_first_device_command": true,
    "durable_effect_intent_consumes_one_ordinal": true,
    "post_intent_pre_command_cut": "uncertain_consumed_no_replay",
    "fresh_target_health_recheck_before_intent": true,
    "d0_group_debit": "one_group_before_first_group_command",
    "one_intent_per_selected_action": true,
    "uncertain_command_replay": false,
    "next_effect_requires_exact_healthy_return": true,
    "stop_state": "park_for_operator_return_and_passive_reads_only"
  },
  "repair": {
    "observer_parser_reporting_h0_if_effect_core_unchanged": true,
    "zero_new_device_command_surface": true,
    "core_selector_state_or_recovery_drift": "fresh_review_and_activation",
    "consumed_ordinal_replay": false
  },
  "evidence": {
    "one_machine_receipt_per_ordinal": true,
    "one_campaign_summary": true,
    "per_read_prose_review": false
  },
  "forbidden": [
    "unattended_f1", "kernel_module_load_or_unload", "panic_or_crash_injection",
    "runtime_code_payload", "f1_or_partition_transfer", "generic_root_or_su",
    "arbitrary_sysfs_configfs_path_or_value", "persistent_property_service_security_configuration_write",
    "package_shared_storage_userdata_write", "odin_payload_transfer",
    "security_state_efs_rpmb_fuse_or_bootloader", "factory_reset_closure"
  ]
}
```

## Catalog and accounting rules

Only the exact target/build above is eligible; other targets, endpoints,
identities, or builds receive zero commands. One attended opening binds the
catalog/effect-core hashes, exact live target/topology, healthy current boot,
fixed private journal, positive budgets, and immutable expiry. Counters do not renew, reset, roll
over, or permit a concurrent campaign. A later campaign requires a new attended
activation and journal after this one closes; F1 requires it closed first. The
operator need not remain present during a healthy activated campaign, but a
park or close requiring intervention waits for operator return.

The four closed classes are:

1. Bounded raw-first D0 reads of exact identity, Android health, approved
   public sysfs/procfs state, and host inventory. Existing raw capture is
   bounded, no-clobber, mode 0400, file-fsynced before parsing, and parser input
   is that immutable raw handle.
2. One fixed normal Android reboot followed by exact health and fresh-baseline
   observation.
3. A payload-free Download enter/return roundtrip, eligible only after
   independently proved automatic return. Activation binds a fixed entry argv,
   zero-endpoint pre-entry baseline, one unique post-entry endpoint, and exact
   `/usr/bin/odin4 --reboot -d <bound-endpoint>` return; no payload is permitted.
4. One fixed privileged sysfs/configfs USB-role or UDC transient with literal
   executor, direct node type/path, before/write/after values, and restore
   action/result. Debug/security nodes and caller-supplied path/value are rejected.

Android Recovery entry is eligible only after automatic return proof; Download
is the separate roundtrip above. Generic root/su,
arbitrary sysfs/configfs access, persistent property/service/security/config
writes, packages/shared-storage/userdata mutation, module load/unload,
runtime-code payload, panic/crash injection, F1, and every partition payload
remain outside this catalog. Factory reset is not ordinary recovery.

Host preparation failure proven before durable effect intent consumes no
ordinal or budget. Immediately before the first actual device command, one
durable intent binds the campaign, ordinal, exact target/current boot,
descriptor, effect-core hash, and post-debit counters after a fresh
target/health recheck; publication of that intent consumes one ordinal. A cut
after intent, including before command dispatch, is uncertain-consumed and never replayed. No next effect is permitted
until exact healthy return is durable. Control loss, unhealthy Android, unowned
reboot, ambiguity, changed effect core, or missing return parks for operator
return and passive reads; the catalog has no autonomous recovery transition.
Each D0 descriptor atomically debits one aggregate command group before its
first command; all D1 descriptors share the aggregate D1 cap.

Observer/parser/reporting repairs remain H0 when a machine audit proves the
effect core and device-command surface unchanged. Selector, literal/value,
state-transition, target, recovery, or effect-core drift requires fresh review
and activation. Each ordinal gets one private machine receipt and the campaign
gets one summary; per-read prose is not required.

## Activation boundary

The catalog remains `DEFINED_NOT_ACTIVE` until the exact coordinator/runner,
versioned catalog, hostile tests, independent `PASS_GO`, immutable activation
manifest, and fresh attended live-session approval exist and pass mechanical
checks. No readiness label, capability result, user direction, or policy text
implicitly activates it. F1 remains attended and continues under ordinary
Process-v2 boot-only candidate, rollback, and final-health rules.
