#!/usr/bin/env python3
"""Audit the permanent S22+ D0/F1 raw-before-parse observer boundary."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import types
from typing import Any, Mapping


SCHEMA = "s22plus_fyg8_raw_first_observer_audit_v1"
VERDICT = "PASS_S22PLUS_FYG8_RAW_FIRST_OBSERVER_BOUNDARY_H0"
RAW_MODULE = "device_action_raw_capture_v1"
UNPARSEABLE_POPULATION_SOURCE = "UNPARSEABLE_POPULATION_SOURCE"
AUDITOR_NORMALIZED_SHA256 = "8e480d4178e89d500ce2ec54cede7be1e71fb3707f0ea145c79b9c63d2bd1ec7"
SCRIPT_DIR = Path(__file__).resolve().parent
_BOUND_AUDITOR_SOURCE = globals().get("_RAW_FIRST_BOUND_AUDITOR_SOURCE")
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260830-24-p319-prepared-runtime-bound.json"
)
LEGACY_UNMIGRATED_OBSERVER_COUNT = 47
LEGACY_UNMIGRATED_OBSERVER_SHA256 = (
    "6227ff0d851cff7ca6aea1c2e23088ec21deca4ff1eea120750579ace2ba014e"
)
CLOSED_OBSERVER_SOURCE_COUNT = 130
CLOSED_OBSERVER_SOURCE_SHA256 = (
    "331b32cb2512876da202d6a3f57c8544b422b067267316fcb98705f0db45efa1"
)
DEVICE_TRANSPORT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        # Identifier boundaries, not quoted literals: a real observer passes the
        # transport in as a variable (adb, adb_path, ADB) far more often than as
        # the bare string "adb".  The boundary keeps ordinary words such as
        # "readback" from matching.
        r"(?<![A-Za-z0-9])adb(?![A-Za-z0-9])",
        r"(?<![A-Za-z0-9])odin(?![A-Za-z0-9])",
        r"(?<![A-Za-z0-9])fastboot(?![A-Za-z0-9])",
        r"heimdall",
        r"ttyACM",
        r"bounded_command\(",
        r"device_action_d0_v2",
    )
)
S22_SCOPED_SOURCE_RE = re.compile(
    # Anchored prefixes left build_s22plus_* and s22_* -- including the sources
    # that write partitions -- held by name only, so an edit adding new device
    # acquisition to them passed. Byte-freeze those too.
    r"(?:build_)?(?:s22plus|s22_|device_action)[A-Za-z0-9_]*\.py"
)
PRE_BOUNDARY_DEVICE_SOURCE_COUNT = 128
PRE_BOUNDARY_DEVICE_SOURCE_SHA256 = (
    "4d8ef871dff88a03aaf74e277eb337a3bb2a8d2e7b183f80318c2dad6e6af32a"
)
PRE_BOUNDARY_DEVICE_SOURCES = frozenset(
    {
        "a90_repl_resident_session.py",
        "build_native_init_boot_v2317_usb_product_rodata.py",
        "build_native_init_boot_v2318_usb_full_identity_rodata.py",
        "build_native_init_boot_v2319_usb_product_overrun1_rodata.py",
        "build_native_init_boot_v2320_usb_product_overrun2_rodata.py",
        "build_native_init_boot_v2321_usb_clean_identity_rodata.py",
        "build_s20plus_g986n_native_canary_n1.py",
        # S20+ owns these acquisition paths.  Membership makes their scope
        # explicit, while the S22 audit intentionally does not byte-freeze or
        # claim migration authority over another target's reviewed process.
        "build_s20plus_g986n_p0_pid1_acm_h0.py",
        "build_s20plus_g986n_recovery_adb_canary_h0.py",
        "build_s20plus_g986n_twrp_identical_resident_write_q0_h0.py",
        "build_s20plus_n3u0_magisk_overlay.py",
        "build_s22plus_direct_p3_boot.py",
        "build_s22plus_fyg8_p221_candidate.py",
        "build_s22plus_fyg8_p234_candidate.py",
        "build_s22plus_fyg8_p286_candidate.py",
        "build_s22plus_fyg8_r3c0_control.py",
        "build_s22plus_fyg8_r3c1_candidate.py",
        "build_s22plus_fyg8_r4w1a_candidate.py",
        "build_s22plus_fyg8_r4w1b_candidate.py",
        "build_s22plus_fyg8_r4w1c_watchdog_carrier.py",
        "build_s22plus_fyg8_r4w1d_candidate.py",
        "build_s22plus_fyg8_r4w1e_e1_candidate.py",
        "build_s22plus_inplace_m24_pmsg_steps_park.py",
        "build_s22plus_m25_hs_only_usb2_acm.py",
        "build_s22plus_o1_magisk_overlay.py",
        "build_s22plus_observable_m3_boot.py",
        "build_s22plus_ramoops_dtbo_enable.py",
        "build_s22plus_ramoops_vendor_boot_direct_enable.py",
        "build_s22plus_ramoops_vendor_boot_enable.py",
        "build_s22plus_v3435_ramoops_console_dtbo.py",
        "device_action_f1_evidence_v2.py",
        "device_action_f1_v2.py",
        "native_audio_acdb_android_measurement_planner_v2396.py",
        "native_audio_acdb_clone_follow_planner_v2421.py",
        "native_audio_acdb_m1_diag_observer_planner_v2449.py",
        "native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py",
        "native_audio_acdb_ownprocess_get_live_handoff_v2490.py",
        "native_audio_acdb_payload_capture_planner_v2415.py",
        "native_audio_acdb_threadset_clone_follow_planner_v2423.py",
        "native_audio_acdb_topology_replay_live_handoff_v2550.py",
        "native_audio_acdbtap_service_env_live_handoff_v2485.py",
        "native_audio_acdbtap_vendor_preload_live_handoff_v2481.py",
        "native_audio_acdbtap_wrapper_exec_planner_v2487.py",
        "native_audio_adsp_kick_no_wait_live_handoff_v2804.py",
        "native_audio_android_route_delta_handoff_v2365.py",
        "native_audio_dmabuf_msync_nonfatal_live_handoff_v2797.py",
        "native_audio_foreground_adsp_prime_live_handoff_v2803.py",
        "native_audio_integrated_play_live_handoff_v2791.py",
        "native_audio_integrated_play_live_handoff_v2792.py",
        "native_audio_ion_devnode_live_handoff_v2796.py",
        "native_audio_manifest_allowlist_live_handoff_v2794.py",
        "native_audio_msm_audio_cal_devnode_live_handoff_v2798.py",
        "native_audio_native_ioctl_width_live_handoff_v2799.py",
        "native_audio_play_worker_live_handoff_v2793.py",
        "native_audio_route_api_device_validation_handoff_v2784.py",
        "native_audio_route_core_apply_device_validation_handoff_v2786.py",
        "native_audio_setcal_direct_execute_live_handoff_v2795.py",
        "native_audio_sound_control_diagnostic_live_handoff_v2800.py",
        "native_audio_speaker_descriptor_api_device_validation_handoff_v2788.py",
        "native_audio_speaker_pilot_live_handoff_v2379.py",
        "native_audio_stage_module_device_validation_handoff_v2781.py",
        "native_audio_stage_module_device_validation_handoff_v2782.py",
        "native_audio_v2798_readiness_replay_live_handoff_v2801.py",
        "native_init_flash.py",
        "s20plus_g986n_boot_only_odin_prep.py",
        "s20plus_g986n_boot_recovery_canary_b0_f1.py",
        "s20plus_g986n_autonomous_health_h0.py",
        "s20plus_g986n_autonomous_public_health_adb_seccomp_v1_h0.py",
        "s20plus_g986n_autonomous_public_health_recovery_v1.py",
        "s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py",
        "s20plus_g986n_autonomous_public_health_runtime_v1_h0.py",
        "s20plus_g986n_autonomous_public_health_terminal_continuity_v1_h0.py",
        "s20plus_g986n_autonomous_research_coordinator_h0.py",
        "s20plus_g986n_attended_root_health_d0.py",
        "s20plus_g986n_d0_inventory.py",
        "s20plus_g986n_download_exit_d1.py",
        "s20plus_g986n_magisk_bootstrap_f1.py",
        "s20plus_g986n_native_canary_r1.py",
        "s20plus_g986n_p0_pid1_odin_f1.py",
        "s20plus_g986n_routine_actions.py",
        "s20plus_g986n_routine_d0.py",
        "s20plus_n3u0_attended_f1.py",
        "s20plus_n3u0_attended_f1_backend_h0.py",
        "s20plus_n3u0_attended_f1_integration_h0.py",
        "s22_debloat_pass4_rescue.py",
        "s22plus_active_dtb_provenance_audit.py",
        "s22plus_boot_slice.py",
        "s22plus_eud_openocd_host_audit.py",
        "s22plus_eud_phase_a_readonly_probe.py",
        "s22plus_eud_phase_b_enable_live_gate.py",
        "s22plus_eud_phase_b_enable_readiness_audit.py",
        "s22plus_fyg8_consumed_suite_expected_failures.py",
        "s22plus_fyg8_module_map.py",
        "s22plus_fyg8_p221_candidate_static_checker.py",
        "s22plus_fyg8_p233_e1_static_checker.py",
        "s22plus_fyg8_p234_build_repro_check.py",
        "s22plus_fyg8_p234_candidate_contract.py",
        "s22plus_fyg8_p234_candidate_intent.py",
        "s22plus_fyg8_p234_candidate_static_checker.py",
        "s22plus_fyg8_p234_userspace_build.py",
        "s22plus_fyg8_p241_e2_static_checker.py",
        "s22plus_fyg8_p244_e2_static_checker.py",
        "s22plus_fyg8_p248_source_contract.py",
        "s22plus_fyg8_p252_source_contract.py",
        "s22plus_fyg8_p254_source_contract.py",
        "s22plus_fyg8_p257_source_contract.py",
        "s22plus_fyg8_p258_source_contract.py",
        "s22plus_fyg8_p260_qemu_harness.py",
        "s22plus_fyg8_p260_source_contract.py",
        "s22plus_fyg8_p280_pre_lto_qualification.py",
        "s22plus_fyg8_p280_source_contract.py",
        "s22plus_fyg8_p282_pre_lto_qualification.py",
        "s22plus_fyg8_p282_source_contract.py",
        "s22plus_fyg8_p284_pre_lto_qualification.py",
        "s22plus_fyg8_p286_boot_only_packager.py",
        "s22plus_fyg8_p286_build_repro_check.py",
        "s22plus_fyg8_p286_candidate_contract.py",
        "s22plus_fyg8_p286_candidate_intent.py",
        "s22plus_fyg8_p286_candidate_static_checker.py",
        "s22plus_fyg8_p286_pre_lto_qualification.py",
        "s22plus_fyg8_p286_source_contract.py",
        "s22plus_fyg8_p286_userspace_build.py",
        "s22plus_fyg8_p288_build_repro_check.py",
        "s22plus_fyg8_p288_source_contract.py",
        "s22plus_fyg8_p290_build_repro_check.py",
        "s22plus_fyg8_p290_source_contract.py",
        "s22plus_fyg8_p292_source_contract.py",
        "s22plus_fyg8_p294_tier2_reentry.py",
        "s22plus_fyg8_p296_pre_lto_qualification.py",
        "s22plus_fyg8_p298_pre_lto_qualification.py",
        "s22plus_fyg8_p300_pre_lto_qualification.py",
        "s22plus_fyg8_p316_candidate_static_checker.py",
        "s22plus_fyg8_p318_baseline_rotation_d1.py",
        "s22plus_fyg8_p318_candidate_static_checker.py",
        "s22plus_fyg8_p318_carrier_version_crosscheck.py",
        "s22plus_fyg8_p318_cdc_acm_positive_control.py",
        "s22plus_fyg8_p318_historical_eud_index_sweep.py",
        "s22plus_fyg8_p318_postlive_eud_index_audit.py",
        "s22plus_fyg8_p318_selector_negative_control.py",
        # This D1 producer is not a migrated D0/F1 observer. Its
        # device-acquiring bytes are frozen only as an independently reviewed
        # global acquisition-detector membership.
        "s22plus_fyg8_p319_d1_fresh_baseline.py",
        "s22plus_fyg8_r3_static_checker.py",
        "s22plus_fyg8_r3c0_live_gate.py",
        "s22plus_fyg8_r3c1_live_gate.py",
        "s22plus_fyg8_r4w1a_live_gate.py",
        "s22plus_fyg8_r4w1a_static_checker.py",
        "s22plus_fyg8_r4w1a_stream_candidate_live_gate.py",
        "s22plus_fyg8_r4w1b_live_gate.py",
        "s22plus_fyg8_r4w1c2_measured_live_binding_packet.py",
        "s22plus_fyg8_r4w1c2_measured_live_gate.py",
        "s22plus_fyg8_r4w1c3_regular_ap_live_gate.py",
        "s22plus_fyg8_r4w1c_connected_gate.py",
        "s22plus_fyg8_r4w1c_live_binding_packet.py",
        "s22plus_fyg8_r4w1c_live_gate.py",
        "s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.py",
        "s22plus_fyg8_r4w1c_odin_enumeration_diff_observer_binding_packet.py",
        "s22plus_fyg8_r4w1c_watchdog_carrier_static_checker.py",
        "s22plus_fyg8_r4w1d_candidate_static_checker.py",
        "s22plus_fyg8_r4w1e_e1_candidate_static_checker.py",
        "s22plus_fyg8_usb_role_static_re.py",
        "s22plus_m34_s8b1_beacon_probe_live_gate.py",
        "s22plus_m34_s8b1a_wide_i2c_beacon_live_gate.py",
        "s22plus_m34_s9_devlink_substrate_beacon_live_gate.py",
        "s22plus_m3_observable_live_gate.py",
        "s22plus_magisk_boot_baseline_restore_gate.py",
        "s22plus_magisk_boot_capture_collect.py",
        "s22plus_magisk_boot_time_capture_m1.py",
        "s22plus_native_init_observability_frontier_audit.py",
        "s22plus_o0_stock_usb_control.py",
        "s22plus_o11_stock_first_stage_control_live_gate.py",
        "s22plus_o1_stock_first_stage_control_live_gate.py",
        "s22plus_observable_init_recipe.py",
        "s22plus_p0_recon_collect.py",
        "s22plus_p2_stock_boot_rollback_guard.py",
        "s22plus_p3_collect_and_rollback.py",
        "s22plus_ramoops_android_baseline_preflight.py",
        "s22plus_ramoops_dtbo_m22_sysrq_panic_readiness_audit.py",
        "s22plus_reset_reason_readonly_probe.py",
        "s22plus_retained_evidence_probe.py",
        "s22plus_sec_debug_mid_sysrq_gate.py",
        "s22plus_stock_usb_topology_readonly.py",
        "s22plus_twrp_magisk_restore_window.py",
        "s22plus_v3427_transition_selection.py",
        "s22plus_v3428_stock_transition_positive_control.py",
        "s22plus_v3430_phase_observer_live_gate.py",
        "s22plus_v3433_pid1_keystone_live_gate.py",
        "s22plus_v3437_ramoops_positive_control_live_gate.py",
        "s22plus_v3439_ramoops_positive_control_live_gate.py",
        "s22plus_v3440_rdx_usb_viability_gate.py",
        "s22plus_v3441_debug_mid_rescue_live_gate.py",
        "s22plus_v3442_high_set_only_live_gate.py",
        "s22plus_v3443_high_panic_compare_live_gate.py",
    }
)
P319_D1_PRE_BOUNDARY_CLASSIFICATION = {
    "source": "s22plus_fyg8_p319_d1_fresh_baseline.py",
    "tier": "D1",
    "classification": "byte-frozen-global-acquisition-detector-member",
    "d0_f1_observer_migration": False,
    "independent_review_required": True,
}
S22_HOST_ONLY_NON_ACQUIRING_SOURCE_SPECS = {
    "closed_result_publisher.py": {
        "owner": "process-v2-closed-result-publication",
        "classification": "host-only-exact-closed-result-publisher",
        "profile": "H0-closed-run-publication",
        "size": 17976,
        "sha256": "b1e7dde384627d178af32a396bc5e40128b877d1f6212e8b017e289dbcccb427",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p319_candidate_qualification.py": {
        "owner": "s22plus-fyg8-p319",
        "classification": "host-only-non-acquiring",
        "profile": "H0-candidate-qualification",
        "size": 47599,
        "sha256": "2618c9c9ad0723ce456fcf718af0f456e02e020acc52c27864b501a0fd42ace4",
        "exec_lines": (238, 252),
        "getattr_line": 152,
    },
    "s22plus_fyg8_p321_artifact_identity.py": {
        "owner": "s22plus-fyg8-p321",
        "classification": "host-only-exact-artifact-tool",
        "profile": "H0-ap-identity-join",
        "size": 26923,
        "sha256": "dc303ef20175a7a6cbe350328fff499ef585edfba995735a990d0891e3570055",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p322_artifact_identity.py": {
        "owner": "s22plus-fyg8-p322",
        "classification": "host-only-exact-artifact-tool",
        "profile": "H0-ap-identity-join",
        "size": 9453,
        "sha256": "8e77653fa23f47f48980fb2eae906118239e53e763d4e9643be27a71b0749975",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p322_stock_process_v2_adapter.py": {
        "owner": "s22plus-fyg8-p322",
        "classification": "host-only-exact-decoder-adapter",
        "profile": "H0-process-v2-observer-adapter",
        "size": 12739,
        "sha256": "574f88d966b091fb24a3feb6ea7cbdde54f630fcaab688ca25d10c8181cd4bda",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p323_artifact_identity.py": {
        "owner": "s22plus-fyg8-p323",
        "classification": "host-only-exact-artifact-tool",
        "profile": "H0-ap-identity-join",
        "size": 10397,
        "sha256": "22a175eb09532b3e1df785d1550883a3503a166444e96f1c5d70ae6cba2e9021",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p324_acm_primary_runtime.py": {
        "owner": "s22plus-fyg8-p324",
        "classification": "host-only-exact-runtime-adapter",
        "profile": "H0-acm-primary-runtime-adapter",
        "size": 6803,
        "sha256": "9de5f0b893fff4b1159d90572090277a2bf8d7da4a55a67050269d8a44df6190",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p324_artifact_identity.py": {
        "owner": "s22plus-fyg8-p324",
        "classification": "host-only-exact-artifact-tool",
        "profile": "H0-ap-identity-join",
        "size": 10839,
        "sha256": "a572846e7bd8c725e9449aaa07dbd22d6cb278015301a6b9a63f59bf08b8e4c6",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p324_stock_process_v2_adapter.py": {
        "owner": "s22plus-fyg8-p324",
        "classification": "host-only-exact-decoder-adapter",
        "profile": "H0-process-v2-observer-adapter",
        "size": 21154,
        "sha256": "3f888926d98dffda159706bd92eaa74631793b46ea200302d1e61833d7fb13a3",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p325_artifact_identity.py": {
        "owner": "s22plus-fyg8-p325",
        "classification": "host-only-exact-artifact-tool",
        "profile": "H0-ap-identity-join",
        "size": 11002,
        "sha256": "e6849bdd58b34859bf2b0415ece16a962dafdbd02471191ed3dcddd0db68b7af",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p325_stock_process_v2_adapter.py": {
        "owner": "s22plus-fyg8-p325",
        "classification": "host-only-exact-decoder-adapter",
        "profile": "H0-process-v2-observer-adapter",
        "size": 16978,
        "sha256": "6c4ae9a981ac30523275bc261857605d4c263113ceb9a4a3e079508d408919f0",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p328_artifact_identity.py": {
        "owner": "s22plus-fyg8-p328",
        "classification": "host-only-exact-artifact-tool",
        "profile": "H0-ap-and-auth-key-identity-join",
        "size": 11503,
        "sha256": "e849578b1e7fcb9853ee0a07eaafb28922aa3e5f6b6f746851122f354cc00931",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p330_artifact_identity.py": {
        "owner": "s22plus-fyg8-p330",
        "classification": "host-only-exact-artifact-tool",
        "profile": "H0-ap-and-auth-key-identity-join",
        "size": 7846,
        "sha256": "bc85e7e88c85a9b2678586a0897e14246e1a09976b15921d5f1b414d10118a36",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p330_auth_exec_runtime.py": {
        "owner": "s22plus-fyg8-p330",
        "classification": "host-only-exact-runtime-transform",
        "profile": "H0-preauth-diagnostic-runtime",
        "size": 8818,
        "sha256": "c281a19568569195640fa73de72ae62fafca8481e17037934e595e8da6a77e6a",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p330_stock_process_v2_adapter.py": {
        "owner": "s22plus-fyg8-p330",
        "classification": "host-only-exact-decoder-adapter",
        "profile": "H0-process-v2-observer-adapter",
        "size": 9731,
        "sha256": "1e72d5d5acffbb98c65c7e61ad3fbb42252398644b78fa9b7558fe532cef63d8",
        "exact_host_tool": True,
    },
    "s22plus_fyg8_p331_closed_result_finalizer.py": {
        "owner": "s22plus-fyg8-p331",
        "classification": "host-only-closed-result-finalizer",
        "profile": "H0-closed-result-reconstruction",
        "size": 10259,
        "sha256": "ef22a76ab1b2de171a7c34fe47ca3852455e1b2d8d7f84fec86f6124774e9cf5",
        "exact_host_tool": True,
    },
}
OBSERVER_FILE_RE = re.compile(
    r"(?:s22plus|device_action)[A-Za-z0-9_]*"
    r"(?:d0|f1|live|observer|probe|capture|transition|recovery|readonly)"
    r"[A-Za-z0-9_]*\.py"
)
LIVE_ACQUISITION_MARKERS = (
    "subprocess.",
    "bounded_command(",
    "os.popen(",
)
LIVE_PARSE_MARKERS = (
    ".stdout",
    ".stderr",
    ".communicate(",
    "check_output(",
)

ACTIVE_FILES = {
    "s22plus_fyg8_raw_first_observer_audit.py",
    "device_action_raw_capture_v1.py",
    "device_action_d0_v2.py",
    "s22plus_fyg8_p319_d0_fresh_baseline.py",
    "s22plus_fyg8_p319_d0_fresh_baseline_v2.py",
    "s22plus_fyg8_p319_d0_fresh_baseline_v3.py",
    "s22plus_fyg8_p319_d1_fresh_baseline_v2.py",
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.py",
    "s22plus_fyg8_p320_d0_fresh_baseline.py",
    "s22plus_fyg8_p320_d1_fresh_baseline.py",
    "s22plus_fyg8_pref1_normal_reboot_live_v1.py",
    "s22plus_fyg8_p319_max77705_attribute_stage_a.py",
    "s22plus_fyg8_max77705_sysfs_d0.py",
    "s22plus_fyg8_p257_stock_pivot_d0.py",
    "s22plus_fyg8_p303_stock_log_d0.py",
    "s22plus_boot_only_live_core.py",
    "s22plus_odin_transition_core.py",
    "s22plus_odin_usbfs_identity.py",
    "device_action_cdc_acm_observer_v1.py",
    "device_action_usb_trace_sidecar_v1.py",
    "s22plus_fyg8_p300_usb_trace_binding.py",
    "s22plus_boot_only_f1_transport.py",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py",
    "s22plus_fyg8_p329_auth_acm_observer.py",
    "s22plus_fyg8_p330_auth_acm_observer.py",
    "s22plus_fyg8_p331_resident_acm_observer.py",
    "s22plus_fyg8_p331_resident_exec_runtime.py",
    "s22plus_fyg8_p332_logical_resident_acm_observer.py",
    "s22plus_fyg8_p332_logical_resident_exec_runtime.py",
    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py",
    "s22plus_fyg8_p333_open_entry_diag_runtime.py",
    "s22plus_fyg8_p334_first_read_rc_acm_observer.py",
    "s22plus_fyg8_p334_first_read_rc_runtime.py",
    "device_action_f1_live_v2.py",
}
EXPECTED_ACTIVE_SOURCE_SHA256 = {
    "device_action_cdc_acm_observer_v1.py": "a1fa4dc117fcd9b1f755f50a7d105a86f7b8ddf43ef30a48d34c0b1f0dcf0da1",
    "device_action_d0_v2.py": "b55deb12c487cc66a50008aa7b1bd587fdc1a70bfb3e01e5168fc107ff40b1ce",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py": "6357256ddca6faab28292e807e7e393c0c0fb841244fd4ce84a0c1f4643d5622",
    "s22plus_fyg8_p329_auth_acm_observer.py": "ddcc7ab2cc8e6fd70f096b4b19606d9e9fde8355eaa9cb65534b43eb917bbe76",
    "s22plus_fyg8_p330_auth_acm_observer.py": "a00589310609cbab776dd99a23325644406d4d52cc0038ab34ab11ae726b3240",
    "s22plus_fyg8_p331_resident_acm_observer.py": "59d82f28dd50d8a1e39b4b267667bb4a56310acd71667b4df96499d43cdd558d",
    "s22plus_fyg8_p331_resident_exec_runtime.py": "b146a1b9c46fc5db520c20d8c250dcc565c9882723ba82398fb8d1cd60f69750",
    "s22plus_fyg8_p332_logical_resident_acm_observer.py": "af64b65806bf0c521c375b2db158022e0bd1b625f82862fa47769f31e1cb481f",
    "s22plus_fyg8_p332_logical_resident_exec_runtime.py": "fc4f6a98855ef4fb58c417b351ef24e91d21823e08267d83030c846a58cc1f93",
    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py": "fbb0f2a2c8bf3f0dded26b18de5ce83bae8202e3426a049cf2be23379e79dcf3",
    "s22plus_fyg8_p333_open_entry_diag_runtime.py": "fb61a41719df431fc465d763eebb63e412f68c95adaa21300f20e8a603ba7397",
    "s22plus_fyg8_p334_first_read_rc_acm_observer.py": "4644eede3280c29c5619cb5b8e70a0af50b2993ab05de1df9e3f92632e860399",
    "s22plus_fyg8_p334_first_read_rc_runtime.py": "05d21599c95a40abc679c3e5bd7ee0447dd708f52ac0734b53902f27f434c323",
    "device_action_f1_live_v2.py": "a4b0a8fe7434a7b5a4330c94b26c09693b7ec6b49521b45f2ade69c3075207c8",
    "device_action_raw_capture_v1.py": "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4",
    "device_action_usb_trace_sidecar_v1.py": "f4a87987c0feddf00e89235070ccfaebf6f29353d06f3aa0c887dc3da6dc12ab",
    "s22plus_boot_only_f1_transport.py": "f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea",
    "s22plus_boot_only_live_core.py": "f5411d39e11e1f5e2b4ff63c0fe6c3a1874ef0dd5c33c91cbab4f736f4521af1",
    "s22plus_fyg8_max77705_sysfs_d0.py": "8fc0eb11ec25822823a0fbce95090822908fa4742b95ffa500fcf5637cf41a4d",
    "s22plus_fyg8_p257_stock_pivot_d0.py": "143821a4ebda2e04992ad36c4acbd5b73fe09a47174eb56c79c5526a5513dbae",
    "s22plus_fyg8_p300_usb_trace_binding.py": "d987d6732132eea3adddf27ed42336486d914706b6555ba279cd98c4987e613f",
    "s22plus_fyg8_p303_stock_log_d0.py": "7e963b5144705c2f27fa8f91f4e139e92608732efc401910049cd5ff88868a4d",
    "s22plus_fyg8_p319_max77705_attribute_stage_a.py": "c28097ef576f971ff427c97bdf62d839047c1c4ec1a861c8bf39592dc352fc38",
    "s22plus_fyg8_p319_d0_fresh_baseline.py": "c1a7f82ff9a7e9ca555cf38a9f8addaf7d287f7a5560057b9be49899c631062f",
    "s22plus_fyg8_p319_d0_fresh_baseline_v2.py": "e1190b66a31ee674d9f0bf64726fbf8a5edb55d81e7910b07b6f4b0f46009d0d",
    "s22plus_fyg8_p319_d0_fresh_baseline_v3.py": "adc3e979771dbc4e67c264d3b6ad8f09f3fc512dc5decee7cff770094d24574d",
    "s22plus_fyg8_p319_d1_fresh_baseline_v2.py": "9443c81cd51e23a24f48a0f43573e1449cfa188b3cd1c69e6f6f11644d15d478",
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.py": "cb13236e1fb10bf25ac47f7706df050abe15b2ab5a7e423bbdc7b5b31c2c491d",
    "s22plus_fyg8_p320_d0_fresh_baseline.py": "996b6590cb61e5070189e4f16f349bfab2c8ab08f87414b325d66d76a2cb6b71",
    "s22plus_fyg8_p320_d1_fresh_baseline.py": "193dced3d36d6165f8e2810a95e535061a63b93c93ac7484e127ea91a1fa8b56",
    "s22plus_fyg8_pref1_normal_reboot_live_v1.py": "e93ec6df89d2ae050876e67713bf8c80cd43301733ece98795d298e407504ed7",
    "s22plus_odin_transition_core.py": "550ee4960cce110a2f5fbde2763971122c88a6ba225cfea800f5bf60a4e65a5b",
    "s22plus_odin_usbfs_identity.py": "caae61d64435e0fc85bb30adce9dc2bf07cf31bc4ffa033bab72dc072b5db415",
}
P328_LIVE_SOURCE_IDENTITY = {
    "size": 502_612,
    "sha256": "a4b0a8fe7434a7b5a4330c94b26c09693b7ec6b49521b45f2ade69c3075207c8",
}
P328_RAW_FIRST_FUNCTIONS = (
    "device_action_f1_live_v2.py:_P327ObserverSession._publish_value",
    "device_action_f1_live_v2.py:_P328ObserverSession._read_endpoint",
    "device_action_f1_live_v2.py:_P328ObserverSession.observe",
    "device_action_f1_live_v2.py:_p328_validate_common_receipt",
    "device_action_f1_live_v2.py:_p328_validate_receipt",
    "device_action_f1_live_v2.py:_P329ObserverSession._settle_guard_properties",
    "device_action_f1_live_v2.py:_P329ObserverSession._read_endpoint",
    "device_action_f1_live_v2.py:_p329_validate_receipt",
)
P326_ACTIVE_SOURCE_IDENTITY = {
    "size": 15_223,
    "sha256": "6357256ddca6faab28292e807e7e393c0c0fb841244fd4ce84a0c1f4643d5622",
}
P331_ACTIVE_SOURCE_IDENTITIES = {
    "s22plus_fyg8_p331_resident_exec_runtime.py": {
        "size": 18_203,
        "sha256": "b146a1b9c46fc5db520c20d8c250dcc565c9882723ba82398fb8d1cd60f69750",
    },
    "s22plus_fyg8_p331_resident_acm_observer.py": {
        "size": 25_273,
        "sha256": "59d82f28dd50d8a1e39b4b267667bb4a56310acd71667b4df96499d43cdd558d",
    },
    "device_action_f1_live_v2.py": {
        "size": 502_612,
        "sha256": "a4b0a8fe7434a7b5a4330c94b26c09693b7ec6b49521b45f2ade69c3075207c8",
    },
}
P331_RAW_FIRST_FUNCTIONS = (
    "s22plus_fyg8_p331_resident_acm_observer.py:_exchange_one",
    "s22plus_fyg8_p331_resident_acm_observer.py:exchange_session",
    "device_action_f1_live_v2.py:_P331ObserverSession._read_endpoint",
    "device_action_f1_live_v2.py:_P331ObserverSession.observe",
    "device_action_f1_live_v2.py:_p331_nonce_from_raw_session",
    "device_action_f1_live_v2.py:_p331_validate_raw_session_bindings",
    "device_action_f1_live_v2.py:_p331_validate_receipt_unchecked",
    "device_action_f1_live_v2.py:_p331_validate_receipt",
)
P332_ACTIVE_SOURCE_IDENTITIES = {
    "s22plus_fyg8_p332_logical_resident_exec_runtime.py": {
        "size": 17_003,
        "sha256": "fc4f6a98855ef4fb58c417b351ef24e91d21823e08267d83030c846a58cc1f93",
    },
    "s22plus_fyg8_p332_logical_resident_acm_observer.py": {
        "size": 30_892,
        "sha256": "af64b65806bf0c521c375b2db158022e0bd1b625f82862fa47769f31e1cb481f",
    },
    "device_action_f1_live_v2.py": {
        "size": 502_612,
        "sha256": "a4b0a8fe7434a7b5a4330c94b26c09693b7ec6b49521b45f2ade69c3075207c8",
    },
}
P332_RAW_FIRST_FUNCTIONS = (
    "s22plus_fyg8_p332_logical_resident_acm_observer.py:_exchange_one",
    "s22plus_fyg8_p332_logical_resident_acm_observer.py:exchange_resident",
    "s22plus_fyg8_p332_logical_resident_acm_observer.py:validate_resident_proof",
    "device_action_f1_live_v2.py:_P332ObserverSession._read_endpoint",
    "device_action_f1_live_v2.py:_P332ObserverSession.observe",
    "device_action_f1_live_v2.py:_p332_nonce_from_raw_session",
    "device_action_f1_live_v2.py:_p332_validate_raw_session_bindings",
    "device_action_f1_live_v2.py:_p332_validate_receipt",
)
P333_ACTIVE_SOURCE_IDENTITIES = {
    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py": {
        "size": 12_840,
        "sha256": "fbb0f2a2c8bf3f0dded26b18de5ce83bae8202e3426a049cf2be23379e79dcf3",
    },
    "s22plus_fyg8_p333_open_entry_diag_runtime.py": {
        "size": 10_991,
        "sha256": "fb61a41719df431fc465d763eebb63e412f68c95adaa21300f20e8a603ba7397",
    },
    "device_action_f1_live_v2.py": {
        "size": 502_612,
        "sha256": "a4b0a8fe7434a7b5a4330c94b26c09693b7ec6b49521b45f2ade69c3075207c8",
    },
}
P333_RAW_FIRST_FUNCTIONS = (
    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py:_exchange_one",
    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py:exchange_resident",
    "device_action_f1_live_v2.py:_logical_resident_candidate_observer_session",
    "device_action_f1_live_v2.py:_p333_candidate_observer_session",
    "device_action_f1_live_v2.py:_p333_validate_receipt",
)
P334_ACTIVE_SOURCE_IDENTITIES = {
    "s22plus_fyg8_p334_first_read_rc_acm_observer.py": {
        "size": 5_523,
        "sha256": "4644eede3280c29c5619cb5b8e70a0af50b2993ab05de1df9e3f92632e860399",
    },
    "s22plus_fyg8_p334_first_read_rc_runtime.py": {
        "size": 14_564,
        "sha256": "05d21599c95a40abc679c3e5bd7ee0447dd708f52ac0734b53902f27f434c323",
    },
    "device_action_f1_live_v2.py": {
        "size": 502_612,
        "sha256": "a4b0a8fe7434a7b5a4330c94b26c09693b7ec6b49521b45f2ade69c3075207c8",
    },
}
P334_RAW_FIRST_FUNCTIONS = (
    "device_action_f1_live_v2.py:_logical_resident_candidate_observer_session",
    "device_action_f1_live_v2.py:_p334_candidate_observer_session",
    "device_action_f1_live_v2.py:_p334_validate_receipt",
)
P326_RAW_FIRST_FUNCTIONS = (
    "s22plus_fyg8_p326_bidirectional_acm_observer.py:_read_segment",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py:_write_segment",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py:_reject_trailing",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py:_exchange",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py:_adapt",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py:P326ObserverSession.observe",
    "s22plus_fyg8_p326_bidirectional_acm_observer.py:validate_receipt",
)
RAW_CAPTURE_INJECTED_WRITER_SOURCES = frozenset(
    {
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "s22plus_fyg8_p330_auth_acm_observer.py",
    }
)

FUNCTION_CONTRACTS: dict[str, dict[str, tuple[tuple[str, ...], tuple[str, ...]]]] = {
    "device_action_raw_capture_v1.py": {
        "RawCaptureWriter.finalize": (
            ("os.fchmod(", "os.fsync(", "_durable_create(", "return load_handle("),
            (),
        ),
        "acquire_command": (
            ("RawCaptureWriter(", "subprocess.Popen(", "writer.finalize("),
            ("subprocess.run(", "subprocess.check_output("),
        ),
        "read_stdout": (
            ("RawCaptureHandle", "load_handle(", "_stable_bytes("),
            ("subprocess.",),
        ),
    },
    "device_action_d0_v2.py": {
        "AdbReadOnlyClient._run": (
            ("capture_command(", "decode_success_stdout("),
            ("bounded_command(", ".stdout", ".stderr"),
        ),
        "AdbReadOnlyClient.capture_command": (
            ("raw_capture.acquire_command(",),
            ("bounded_command(",),
        ),
        "AdbReadOnlyClient.capture": (
            ("raw_capture.acquire_command(", "raw_capture.require_success(", "raw_capture.read_stdout(", "ObserverCapture("),
            ("subprocess.Popen(", "result.stdout", "result.stderr"),
        ),
        "collect_connected": (
            ("isinstance(capture, ObserverCapture)", "raw_capture.read_stdout("),
            ("_read_stable(run_dir / \"baseline-observer.bin\"",),
        ),
    },
    "s22plus_fyg8_p319_d0_fresh_baseline.py": {
        "_execute": (
            (
                "raw.acquire_command(",
                "raw.require_success(handle)",
                "raw.read_stdout(handle, maximum=RAW_SIZE)",
                "raw.read_stderr(handle, maximum=MAX_TEXT)",
                "adapter.classify_clean_baseline(",
            ),
            ("subprocess.", "result.stdout", "result.stderr"),
        ),
        "_raw_adb_inventory": (
            (
                "for child in sorted(",
                "_stable_read(",
                "raw.load_handle(",
                "claimed.update(names)",
                "unclaimed = sorted(",
                '"aggregate_sha256"',
            ),
            ("raw.read_stdout(", "raw.read_stderr(", "subprocess."),
        ),
    },
    "s22plus_fyg8_p319_d0_fresh_baseline_v2.py": {
        "_execute": (
            (
                "raw.acquire_command(",
                "raw.require_success(handle)",
                "raw.read_stdout(handle, maximum=RAW_SIZE)",
                "raw.read_stderr(handle, maximum=MAX_TEXT)",
                "adapter.classify_clean_baseline(",
            ),
            ("subprocess.", "result.stdout", "result.stderr"),
        ),
        "_raw_adb_inventory": (
            (
                "for child in sorted(",
                "_stable_read(",
                "raw.load_handle(",
                "claimed.update(names)",
                "unclaimed = sorted(",
                '"aggregate_sha256"',
            ),
            ("raw.read_stdout(", "raw.read_stderr(", "subprocess."),
        ),
    },
    "s22plus_fyg8_p319_d0_fresh_baseline_v3.py": {
        "_execute": (
            (
                "raw.acquire_command(",
                "raw.require_success(handle)",
                "raw.read_stdout(handle, maximum=RAW_SIZE)",
                "raw.read_stderr(handle, maximum=MAX_TEXT)",
                "adapter.classify_clean_baseline(",
            ),
            ("subprocess.", "result.stdout", "result.stderr"),
        ),
        "_raw_adb_inventory": (
            (
                "for child in sorted(",
                "_stable_read(",
                "raw.load_handle(",
                "claimed.update(names)",
                "unclaimed = sorted(",
                '"aggregate_sha256"',
            ),
            ("raw.read_stdout(", "raw.read_stderr(", "subprocess."),
        ),
    },
    "s22plus_fyg8_p319_d1_fresh_baseline_v2.py": {
        "_make_transport": (
            (
                "self.client.bind_raw_capture_dir(raw_root)",
                "or any(capture_dir.iterdir())",
                'self.client._run(["devices", "-l"]',
                "raw.load_handle(handle.receipt_path)",
                "raw.require_success(reopened)",
                "raw.read_stdout(reopened, maximum=MAX_TEXT)",
                "raw.read_stderr(",
                "except (module.d0.D0Error, OSError):",
                'return {"connected": True, "ready": False}',
            ),
            ("bounded_command(", "result.stdout", "result.stderr"),
        ),
        "_raw_inventory": (
            (
                "for child in sorted(",
                "_stable(",
                "raw.load_handle(",
                "claimed.update(names)",
                "unclaimed = sorted(",
                '"aggregate_sha256"',
            ),
            ("raw.read_stdout(", "raw.read_stderr(", "subprocess."),
        ),
        "run_live": (
            (
                "_preflight_new_run_namespace()",
                "arm_creation_attempted = False",
                "p318._durable_arm(",
                "arm_completed = True",
                "_duplicate_arm_error(exc, p318)",
                "_publish_stop(inputs, exc)",
            ),
            (),
        ),
    },
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.py": {
        "_make_transport": (
            (
                "self.client.bind_raw_capture_dir(raw_root)",
                "or any(capture_dir.iterdir())",
                'self.client._run(["devices", "-l"]',
                "raw.load_handle(handle.receipt_path)",
                "raw.require_success(reopened)",
                "raw.read_stdout(reopened, maximum=MAX_TEXT)",
                "raw.read_stderr(",
                "except (module.d0.D0Error, OSError):",
                'return {"connected": True, "ready": False}',
            ),
            ("bounded_command(", "result.stdout", "result.stderr"),
        ),
        "_raw_inventory": (
            (
                "for child in sorted(",
                "_stable(",
                "raw.load_handle(",
                "claimed.update(names)",
                "unclaimed = sorted(",
                '"aggregate_sha256"',
            ),
            ("raw.read_stdout(", "raw.read_stderr(", "subprocess."),
        ),
        "run_live": (
            (
                "_preflight_new_run_namespace()",
                "arm_creation_attempted = False",
                "_durable_arm_canonical(inputs)",
                "arm_completed = True",
                "_duplicate_arm_error(exc, p318)",
                "_publish_stop(inputs, exc)",
            ),
            ("p318._durable_arm(",),
        ),
    },
    "s22plus_fyg8_p320_d0_fresh_baseline.py": {
        "run_live": (
            (
                "_preflight()",
                "_durable_create(RUN_ARM",
                "client.bind_raw_capture_dir(RUN_DIR)",
                "capture = client.capture(",
                "payload = raw.read_stdout(",
                "observer_result = _classify_clean_baseline(",
                "observer_receipt_payload = _stable_read(",
                "_durable_create(RESULT_PATH, result)",
            ),
            ("subprocess.", "result.stdout", "result.stderr"),
        ),
        "_raw_inventory": (
            (
                "for child in children:",
                "handle = raw.load_handle(child)",
                "handles.append({",
            ),
            ("raw.read_stdout(", "raw.read_stderr(", "subprocess."),
        ),
    },
    "s22plus_fyg8_p320_d1_fresh_baseline.py": {
        "RawFirstTransport.__init__": (
            ("self.client.bind_raw_capture_dir(raw_root)",),
            ("bounded_command(", "result.stdout", "result.stderr"),
        ),
        "RawFirstTransport.reboot_once": (
            (
                "handle = self.client.capture_command(",
                "current = self.raw.load_handle(handle.receipt_path)",
                "self.raw.require_success(current)",
                "self.raw.read_stdout(current",
                "self.raw.read_stderr(current",
            ),
            ("subprocess.", "result.stdout", "result.stderr"),
        ),
        "_raw_inventory": (
            (
                "for name in children:",
                "handle = raw.load_handle(RAW_ADB_DIR / name)",
                "handles.append({",
            ),
            ("raw.read_stdout(", "raw.read_stderr(", "subprocess."),
        ),
        "run_live": (
            (
                "_preflight()",
                "_durable_create(RUN_ARM",
                "_prepare_raw_root()",
                "_prepare_snapshot(adb_payload, ADB_SNAPSHOT)",
                "_load_runtime(",
                "raw_evidence = _raw_inventory(raw)",
                "result = perform_rotation(",
            ),
            ("subprocess.", "result.stdout", "result.stderr"),
        ),
    },
    "s22plus_fyg8_pref1_normal_reboot_live_v1.py": {
        "_observe_v3": (
            (
                "_observation_paths(raw_root, adb_snapshot)",
                "v3._validated_static_inputs()",
                "v3._validated_execution_inputs(static)",
                'Path(inputs["raw"].__file__).name != RAW_CAPTURE_MODULE',
                "p318._prepare_executable_snapshot(",
                "inputs[\"raw\"].prepare_capture_dir(",
                "v3._make_transport(",
                "transport.select_exact()",
                "transport.snapshot(serial)",
                "_health_from_snapshot(",
                "v3._raw_inventory(inputs[\"raw\"])",
            ),
            ("subprocess.", "result.stdout", "result.stderr"),
        ),
        "run_normal_reboot": (
            (
                "require_current=False",
                "state, intent = store._tail()",
                "require_current=True",
                "selected = _observe_v3 if observer is None else observer",
                "_preflight_executor(v3)",
                "store.record_intent(",
                "selected_executor = _default_executor if executor is None else executor",
                "result = selected_executor(v3)",
                "observed = _result_observed(",
                "store.record_healthy_return(observed, now=intent_now)",
                "store.record_uncertain(reason=\"result_uncertain\", now=intent_now)",
                "store.record_close(now=intent_now)",
            ),
            ("subprocess.",),
        ),
        "_reconcile_intent": (
            (
                "state, intent = store._tail()",
                'state["phase"] == "PARKED"',
                "result = selected_loader(v3)",
                "observed = _result_observed(",
                "store.record_healthy_return(observed, now=now)",
                "store.record_uncertain(reason=\"result_uncertain\", now=now)",
                "store.record_close(now=now)",
            ),
            ("_default_executor(", "run_live(", "subprocess."),
        ),
        "_preflight_executor": (
            (
                "v3._validated_static_inputs()",
                "v3._validated_execution_inputs(static)",
                "v3._preflight_new_run_namespace()",
            ),
            ("run_live(", "subprocess."),
        ),
        "_validated_v3_result": (
            (
                "v3._validated_execution_inputs(v3._validated_static_inputs())",
                "v3._post_validate(inputs)",
            ),
            ("run_live(", "subprocess."),
        ),
        "_result_observed": (
            (
                "canonical(result) != canonical(_validated_v3_result(v3))",
                "v3._health_complete(result.get(\"before\"))",
                "v3._selection_complete(result.get(\"selection\"))",
                'result["selection"]["selected_serial_sha256"]',
            ),
            ("subprocess.",),
        ),
    },
    "s22plus_fyg8_p319_max77705_attribute_stage_a.py": {
        "parse_stage_a": (
            ("RawCaptureHandle", "raw_capture.read_stdout(", "raw_capture.require_success("),
            ("payload: bytes", "subprocess."),
        ),
        "collect": (
            ("raw_capture.acquire_command(", "parse_stage_a(stage_handle)"),
            ("parse_stage_a(command.stdout", "d0.bounded_command("),
        ),
    },
    "s22plus_fyg8_max77705_sysfs_d0.py": {
        "read_adb_inventory": (
            ("raw_capture.acquire_command(", "decode_success_stdout("),
            ("d0.bounded_command(", ".stdout.decode("),
        ),
        "_root_snapshot": (
            ("raw_capture.acquire_command(", "return handle"),
            ("d0.bounded_command(",),
        ),
        "parse_snapshot_handle": (
            ("RawCaptureHandle", "raw_capture.read_stdout(", "parse_snapshot(raw)"),
            ("subprocess.",),
        ),
    },
    "s22plus_fyg8_p257_stock_pivot_d0.py": {
        "read_remote_exact": (
            ("raw_capture.acquire_command(", "RawCaptureHandle"),
            ("d0.bounded_command(", ".stdout"),
        ),
        "collect_connected": (
            ("handle = remote_reader(", "evaluate_capture_handles("),
            ("evaluate_reads((result.stdout",),
        ),
        "evaluate_capture_handles": (
            ("RawCaptureHandle", "raw_capture.read_stdout(", "evaluate_reads("),
            ("subprocess.",),
        ),
    },
    "s22plus_fyg8_p303_stock_log_d0.py": {
        "_root_command": (
            ("raw_capture.acquire_command(", "return handle"),
            ("d0.bounded_command(",),
        ),
        "_read_root_capture": (
            ("RawCaptureHandle", "raw_capture.read_stdout("),
            ("subprocess.",),
        ),
        "_select_exact_serial": (
            ("raw_capture.acquire_command(", "decode_success_stdout("),
            ("d0.bounded_command(",),
        ),
    },
    "s22plus_boot_only_live_core.py": {
        "capture_adb_exec_out": (
            ("raw_capture.acquire_command(", "raw_capture.require_success(", "raw_capture.read_stdout("),
            ("subprocess.Popen(",),
        ),
    },
    "s22plus_odin_transition_core.py": {
        "_default_runner": (
            ("raw-first runner is not bound",),
            ("subprocess.Popen(", "subprocess.run("),
        ),
        "_raw_first_runner": (
            ("raw_capture.acquire_command(", "RawRunResult(handle)"),
            (),
        ),
        "enumerate_odin": (
            ("isinstance(result, RawRunResult)", "raw_capture.read_stdout(", "raw_capture.read_stderr("),
            (),
        ),
        "_snapshot_and_record": (
            ("runner is _default_runner", "_raw_first_runner(run_dir, sequence)", "raw_capture_receipt="),
            ("runner=runner,",),
        ),
    },
    "s22plus_odin_usbfs_identity.py": {
        "read_birth_time_ns": (
            ("capture_dir", "raw_capture.acquire_command(", "decode_success_stdout("),
            ("subprocess.run(",),
        ),
    },
    "device_action_cdc_acm_observer_v1.py": {
        "_udev_properties": (
            ("raw_capture.acquire_command(", "raw_capture.read_stdout("),
            ("subprocess.run(", "completed.stdout"),
        ),
        "ModemManagerGuard.arm": (
            (
                "RawCaptureWriter(",
                "writer.write_stdout(chunk)",
                "arm_handle = writer.finalize(",
                "retained = raw_capture.read_stdout(",
                'retained == expected + b"\\n"',
            ),
            ("expected in output", "output.extend("),
        ),
        "ObserverSession._read_endpoint": (
            ("RawCaptureWriter", "writer.write_stdout(chunk)"),
            ("return \"accepted\"", "bytes(payload) == expected"),
        ),
        "ObserverSession._classify_raw": (
            ("RawCaptureHandle", "raw_capture.read_stdout("),
            ("descriptor", "os.read("),
        ),
        "ObserverSession.observe": (
            ("RawCaptureWriter(", "raw_writer.finalize(", "_classify_raw(raw_handle"),
            ("_write_exclusive(raw_path, payload)",),
        ),
    },
    "s22plus_fyg8_p300_usb_trace_binding.py": {
        "_load_bound_raw_capture": (
            (
                "raw_capture.load_handle(",
                "raw_capture.read_stdout(",
                "raw_capture.read_stderr(",
            ),
            ("subprocess.",),
        ),
        "verify_capture_directory": (
            (
                "_load_bound_raw_capture(",
                'expected["raw_capture_receipt"]',
            ),
            ("result.stdout", "result.stderr"),
        ),
    },
    "device_action_usb_trace_sidecar_v1.py": {
        "bounded_snapshot": (
            ("raw_capture.acquire_command(", "raw_capture.read_stdout("),
            ("subprocess.run(", "completed.stdout"),
        ),
        "SourceCapture._drain": (
            ("os.read(", "self.writer.write_stdout(chunk)"),
            (".readline(", "records.append("),
        ),
        "SourceCapture.stop": (
            ("self.writer.finalize(",),
            (),
        ),
    },
    "s22plus_boot_only_f1_transport.py": {
        "execute_odin_boot_only": (
            ("raw_capture.acquire_command(", "raw_capture.read_stdout(", "raw_capture_receipt"),
            ("subprocess.run(", "completed.stdout"),
        ),
    },
    "device_action_f1_live_v2.py": {
        "_classify_odin_capture": (
            ("RawCaptureHandle", "raw_capture.read_stdout(", "raw_capture.read_stderr(", "classify_odin_output("),
            ("subprocess.",),
        ),
        "SamsungOdinBackend.request_download": (
            ("self.client.capture_command(", "raw_capture.require_success("),
            ("d0.bounded_command(",),
        ),
        "SamsungOdinBackend.transfer": (
            ("receipt, raw_handle = transport.execute_odin_boot_only(", "_classify_odin_capture(raw_handle)"),
            ("_persist_bytes(destination / f\"{prefix}.stdout\"",),
        ),
        "SamsungOdinBackend.verify_final": (
            (
                "final_client = d0.adb_client_for_bundle(",
                "final_client.bind_raw_capture_dir(destination)",
                "capture = final_client.capture(",
                "raw_capture.read_stdout(",
                "raw_capture.read_stderr(",
            ),
            ("d0._read_stable(path", "self.client.capture("),
        ),
        "_validate_final_observer": (
            (
                "raw_capture.load_handle(raw_path)",
                "raw_capture.read_stdout(",
                "raw_capture.read_stderr(",
            ),
            ("d0._read_stable(path",),
        ),
        "_P327ObserverSession._publish_value": (
            (
                "cdc_acm_observer.persist_json(",
                'self.run_dir / "candidate-observer.json"',
            ),
            (
                "_write_exclusive(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_P328ObserverSession._read_endpoint": (
            (
                "self.base._raw_tty(",
                "self.auth_observer.exchange_commands(",
                "writer=writer,",
                "partial = getattr(exc, \"audit\", None)",
                "isinstance(partial, p330_auth_observer.ExchangeAudit)",
                "p330_auth_observer.SessionResult((), partial)",
                "self.exchange = exchange",
                "self.trailing_rx = _p327_trailing_probe(",
                "self.auth_observer.validate_default_proof(",
                'return "accepted"',
            ),
            (
                "_write_exclusive(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_P328ObserverSession.observe": (
            (
                "super()._observe_value(",
                "value = dict(base_value)",
                "accepted = bool(",
                '"classification": classification',
                "self._publish_value(",
                "value.update(self._receipt_additions(audit))",
            ),
            (
                "_write_exclusive(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_p328_validate_common_receipt": (
            (
                "raw_path.read_bytes()",
                "capture_path.read_bytes()",
                "raw_capture.load_handle(",
                "raw_capture.read_stdout(handle",
                "raw_capture.read_stderr(handle",
                'tx = _p328_receipt_identity(value["tx"]',
                'lane = value["lane"]',
            ),
            (
                "_p328_read_auth_key(",
                "_write_exclusive(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_p328_validate_receipt": (
            (
                "_read_json(",
                "_p328_receipt_secret_free(",
                "_p328_validate_common_receipt(",
                "_p328_bound_auth_key_identity(",
                "if accepted:",
                "result = {",
                "return result",
            ),
            (
                "_p328_read_auth_key(",
                "_write_exclusive(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_P329ObserverSession._settle_guard_properties": (
            (
                "self.base.guard.healthy(recheck=True)",
                "self.base.guard.matches_node(endpoint.tty_class)",
                "cdc_acm_observer._resolve_endpoint(",
                "cdc_acm_observer._matches(",
                "P329_UDEV_SETTLE_SEC",
                "P329_UDEV_SETTLE_POLL_SEC",
                'return "guard-property-timeout"',
            ),
            ("os.open(", "_write_exclusive(", ".unlink(", ".remove("),
        ),
        "_P329ObserverSession._read_endpoint": (
            (
                "self._settle_guard_properties(",
                "super()._read_endpoint(endpoint, deadline, writer)",
            ),
            ("os.open(", "_write_exclusive(", ".unlink(", ".remove("),
        ),
        "_p329_validate_receipt": (
            (
                "_p328_validate_receipt(",
                "auth_observer=p329_auth_observer",
                "auth_runtime=p329_auth_runtime",
                "receipt_schema=P329_OBSERVER_RECEIPT_SCHEMA",
            ),
            ("_p328_read_auth_key(", "_write_exclusive(", ".unlink(", ".remove("),
        ),
        "_P330ObserverSession._receipt_additions": (
            (
                "diagnostics = []",
                "current_stage = failure_stage = exception_type = exception_sha256 = None",
                "failure_code = rng_eagain_retries = None",
                "isinstance(audit, p330_auth_observer.ExchangeAudit)",
                '"stage": item.stage',
                '"code": item.code',
                "audit.current_stage",
                "audit.failure_stage",
                "audit.failure_code",
                "audit.exception_type",
                "audit.exception_sha256",
                "audit.rng_eagain_retries",
                '"diagnostics": diagnostics',
                '"rng_eagain_retries": rng_eagain_retries',
                '"partial_exchange": {',
                '"current_stage": current_stage',
                '"failure_stage": failure_stage',
                '"failure_code": failure_code',
                '"exception_type": exception_type',
                '"exception_sha256": exception_sha256',
            ),
            (
                "subprocess.",
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
            ),
        ),
        "_p330_validate_receipt": (
            (
                "return _p328_validate_receipt(",
                "auth_observer=p330_auth_observer",
                "auth_runtime=p330_auth_runtime",
                "receipt_schema=P330_OBSERVER_RECEIPT_SCHEMA",
                "classifications=P330_CLASSIFICATIONS",
                'label="P330"',
                'proof_key="p330_authenticated_exec"',
                "extra_keys=P330_RECEIPT_EXTRA_KEYS",
                "extra_validator=_p330_validate_receipt_extras",
            ),
            (
                "subprocess.",
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
            ),
        ),
    },
    "s22plus_fyg8_p326_bidirectional_acm_observer.py": {
        "_read_segment": (
            (
                "select.select(",
                "os.read(",
                "writer.write_stdout(chunk)",
                "return bytes(payload) == expected",
            ),
            (
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_write_segment": (
            (
                "select.select(",
                "os.write(",
                "audit.tx.extend(",
                "return written == len(payload)",
            ),
            (
                "writer.write_stdout(",
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_reject_trailing": (
            (
                "select.select(",
                "os.read(",
                "writer.write_stdout(chunk)",
                "audit.trailing_rx.extend(chunk)",
                "return False",
            ),
            (
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_exchange": (
            (
                "audit.banner_seen = _read_segment(",
                "_write_segment(descriptor, runtime.HOST_PING",
                "audit.pong_seen = _read_segment(",
                "_write_segment(descriptor, runtime.HOST_SHELL",
                "audit.shell_ok_seen = _read_segment(",
                "_reject_trailing(",
            ),
            (
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "_adapt": (
            (
                "base._raw_tty(descriptor)",
                "_exchange(descriptor, deadline, writer, audit)",
                "observer._resolve_endpoint(",
                "audit.endpoint_identity_sha256 = endpoint.identity_sha256",
                'return "captured"\n        finally:',
                "os.close(descriptor)",
                "base._read_endpoint = read_endpoint",
                "yield audit",
                "base._read_endpoint = original_read",
            ),
            (
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "P326ObserverSession.observe": (
            (
                "self.delegate.observe(",
                "tx = bytes(self.audit.tx)",
                "_file_receipt(",
                "observer.persist_json(",
                "self.run_dir / RECEIPT_NAME",
                "projected = dict(result)",
                'projected["classification"] = "byte-mismatch"',
                "return projected",
            ),
            (
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
        "validate_receipt": (
            (
                "p325.validate_receipt(",
                "_strict_json(",
                "bytes.fromhex(",
                "_file_receipt(",
                "return dict(base) | {",
            ),
            (
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
                ".rename(",
                ".truncate(",
                "write_text(",
                "write_bytes(",
            ),
        ),
    },
    "s22plus_fyg8_p330_auth_acm_observer.py": {
        "exchange_commands": (
            (
                "audit = ExchangeAudit(",
                "_BASE._read_exact(",
                "len(runtime.DEVICE_BANNER), deadline, audit, writer",
                "_BASE._send(",
                "parse_diagnostic_frame(",
                "audit.diagnostics.append(opened)",
                "audit.diagnostics.append(rng)",
                "audit.rng_eagain_retries = rng.code",
                "_BASE._read_frame(",
                "writer,",
                "output.extend(frame.payload)",
                "return _BASE.SessionResult(tuple(results), audit)",
                "except Exception as exc:",
                "_raise_partial(",
                "audit.current_stage",
            ),
            (
                "subprocess.",
                "os.popen(",
                "os.system(",
                "persist_json(",
                ".unlink(",
                ".remove(",
                ".replace(",
            ),
        ),
    },
}

# P3.31 keeps the P3.30 exchange as the only frame parser.  These seams pin
# the writer hand-off before session results are inspected and keep receipt
# reopening key-free and host-only.
FUNCTION_CONTRACTS.update(
    {
        "s22plus_fyg8_p331_resident_acm_observer.py": {
            "_exchange_one": (
                ("_P330.exchange_commands(", "writer=writer,"),
                ("writer=None",),
            ),
            "exchange_session": (
                ("capture = _RawWriter(writer)",),
                (),
            ),
        },
        "s22plus_fyg8_p332_logical_resident_acm_observer.py": {
            "_exchange_one": (
                ("original_read_frame = _BASE._read_frame", "frame = original_read_frame(", "_P330.exchange_commands(", "writer=writer,", "nonce = result.audit.nonce", "seen_nonces.add(nonce)"),
                ("writer=None",),
            ),
            "exchange_resident": (
                ("descriptor = _descriptor(connection)", "for index in range(MAX_SESSIONS):", "raw_writer = _RawWriter(writer)", "_exchange_one(", "raw_writer,", "_validate_one_session(record)"),
                ("os.close(", "reconnect", "source_factory"),
            ),
            "validate_resident_proof": (
                ("value.complete", "_validate_one_session(session)", "session.nonce in nonces", '"same_descriptor": True', '"same_fd": True', '"same_tty_fd": True', '"physical_reopen_count": PHYSICAL_REOPEN_COUNT', '"caller_selected_command": False'),
                (),
            ),
        },
        "s22plus_fyg8_p333_open_entry_diag_acm_observer.py": {
            "_exchange_one": (
                (
                    "original = _BASE._read_frame",
                    "frame = original(fd, deadline, audit, raw_writer)",
                    "parse_diagnostic_frame(",
                    "_P332._P330.exchange_commands(",
                    "writer=writer,",
                    "if nonce in seen_nonces:",
                    "seen_nonces.add(nonce)",
                ),
                ("writer=None", "os.close("),
            ),
            "exchange_resident": (
                (
                    "original = _P332._exchange_one",
                    "_P332._exchange_one = _exchange_one",
                    "_P332.exchange_resident(",
                    "writer=writer,",
                    "finally:",
                    "_P332._exchange_one = original",
                ),
                ("os.close(", "reconnect", "source_factory"),
            ),
        },
    }
)
FUNCTION_CONTRACTS["device_action_f1_live_v2.py"].update(
    {
        "_P331ObserverSession._read_endpoint": (
            (
                "p331_resident_observer.exchange_session(",
                "writer=writer,",
                "p331_resident_observer.validate_resident_proof(result)",
            ),
            (),
        ),
        "_P331ObserverSession.observe": (
            ("self._publish_value(",),
            (),
        ),
        "_p331_nonce_from_raw_session": (
            (
                "p331_resident_observer.decode_frame(",
                "hashlib.sha256(challenge).hexdigest()",
            ),
            (),
        ),
        "_p331_validate_raw_session_bindings": (
            (
                "core._stable_read(",
                "_p331_nonce_from_raw_session(rx_segment, index)",
                "bytes.fromhex(encoded_tx)",
                'value["tx"]',
            ),
            ("_p328_read_auth_key(",),
        ),
        "_p331_validate_receipt_unchecked": (
            (
                "value = _read_json(",
                "typed_evidence.validate_p331_resident_proof(proof)",
                "_p331_validate_raw_session_bindings(prepared, value, validated_proof)",
            ),
            ("_p328_read_auth_key(",),
        ),
        "_p331_validate_receipt": (
            ("_p331_validate_receipt_unchecked(prepared, path, spec)",),
            ("_p328_read_auth_key(",),
        ),
        "_P332ObserverSession._read_endpoint": (
            (
                "descriptor = os.open(",
                "self.base._raw_tty(descriptor)",
                "self.auth_observer.exchange_resident(",
                "writer=writer,",
                "self.resident_result = resident",
                "_p327_trailing_probe(descriptor, writer)",
                "self.auth_observer.validate_resident_proof(",
                'return "accepted"',
            ),
            ("writer=None",),
        ),
        "_P332ObserverSession.observe": (
            (
                "base_value, lane_supplement = super(_P331ObserverSession, self)._observe_value(",
                "sessions = () if resident is None else resident.sessions",
                'tx = b"".join(item.raw_tx for item in sessions)',
                'rx = b"".join(item.raw_rx for item in sessions)',
                '"same_tty_fd": complete',
                '"physical_reopen_count": 0',
                "value.update(",
                "self._publish_value(",
                "return value",
            ),
            (),
        ),
        "_p332_nonce_from_raw_session": (
            (
                "observer_module.decode_frame(",
                "hashlib.sha256(challenge).hexdigest()",
            ),
            (),
        ),
        "_p332_validate_raw_session_bindings": (
            (
                "core._stable_read(",
                "_p332_nonce_from_raw_session(",
                "bytes.fromhex(encoded_tx)",
                'value["tx"]',
                'value["rx"]',
            ),
            ("_p328_read_auth_key(",),
        ),
        "_p332_validate_receipt": (
            (
                "value = _read_json(",
                "_p328_receipt_secret_free(value)",
                'proof_validator(value["proof"])',
                "_p332_validate_raw_session_bindings(",
                "return {",
            ),
            ("_p328_read_auth_key(",),
        ),
    }
)
FUNCTION_CONTRACTS["device_action_f1_live_v2.py"].update(
    {
        "_p334_candidate_observer_session": (
            (
                "with _logical_resident_candidate_observer_session(",
                "observer_module=p334_first_read_observer",
                "runtime_module=p334_first_read_runtime",
                "session_type=_P334ObserverSession",
                'label="P3.34"',
                "entry_diagnostic=True",
                "yield session",
            ),
            (),
        ),
        "_p334_validate_receipt": (
            (
                "value = _p332_validate_receipt(",
                "observer_module=p334_first_read_observer",
                "runtime_module=p334_first_read_runtime",
                "receipt_schema=P334_OBSERVER_RECEIPT_SCHEMA",
                "classifications=P334_CLASSIFICATIONS",
                "proof_validator=typed_evidence.validate_p334_logical_resident_proof",
                'proof_key="p334_authenticated_logical_resident"',
                '"first_console_return_checkpoint_only": True',
                "return value",
            ),
            ("_p328_read_auth_key(",),
        ),
    }
)
FUNCTION_CONTRACTS["device_action_f1_live_v2.py"].update(
    {
        "_logical_resident_candidate_observer_session": (
            (
                'if spec.get("protocol_contract") != observer_module.CONTRACT_ID:',
                "if entry_diagnostic:",
                "p325_guard_adapter.observer_session(",
                "yield session_type(",
            ),
            (),
        ),
        "_p333_candidate_observer_session": (
            (
                "with _logical_resident_candidate_observer_session(",
                "observer_module=p333_open_entry_observer",
                "runtime_module=p333_open_entry_runtime",
                "session_type=_P333ObserverSession",
                'label="P3.33"',
                "entry_diagnostic=True",
                "yield session",
            ),
            (),
        ),
        "_p333_validate_receipt": (
            (
                "return _p332_validate_receipt(",
                "observer_module=p333_open_entry_observer",
                "runtime_module=p333_open_entry_runtime",
                "receipt_schema=P333_OBSERVER_RECEIPT_SCHEMA",
                "classifications=P333_CLASSIFICATIONS",
                "proof_validator=typed_evidence.validate_p333_logical_resident_proof",
                'proof_key="p333_authenticated_logical_resident"',
            ),
            (),
        ),
    }
)

ORDERED_FUNCTION_TOKENS = {
    (
        "s22plus_fyg8_p319_d1_fresh_baseline_v2.py",
        "_make_transport",
    ): (
        "self.client.bind_raw_capture_dir(raw_root)",
        "or any(capture_dir.iterdir())",
        'self.client._run(["devices", "-l"]',
        "raw.load_handle(handle.receipt_path)",
        "raw.require_success(reopened)",
        "raw.read_stdout(reopened, maximum=MAX_TEXT)",
        "raw.read_stderr(",
        "except (module.d0.D0Error, OSError):",
        'return {"connected": True, "ready": False}',
    ),
    (
        "s22plus_fyg8_p319_d1_fresh_baseline_v2.py",
        "run_live",
    ): (
        "_preflight_new_run_namespace()",
        "arm_creation_attempted = False",
        "p318._durable_arm(",
        "arm_completed = True",
        "_duplicate_arm_error(exc, p318)",
        "_publish_stop(inputs, exc)",
    ),
    (
        "s22plus_fyg8_p319_d1_fresh_baseline_v3.py",
        "_make_transport",
    ): (
        "self.client.bind_raw_capture_dir(raw_root)",
        "or any(capture_dir.iterdir())",
        'self.client._run(["devices", "-l"]',
        "raw.load_handle(handle.receipt_path)",
        "raw.require_success(reopened)",
        "raw.read_stdout(reopened, maximum=MAX_TEXT)",
        "raw.read_stderr(",
        "except (module.d0.D0Error, OSError):",
        'return {"connected": True, "ready": False}',
    ),
    (
        "s22plus_fyg8_p319_d1_fresh_baseline_v3.py",
        "run_live",
    ): (
        "_preflight_new_run_namespace()",
        "arm_creation_attempted = False",
        "_durable_arm_canonical(inputs)",
        "arm_completed = True",
        "_duplicate_arm_error(exc, p318)",
        "_publish_stop(inputs, exc)",
    ),
    (
        "s22plus_fyg8_pref1_normal_reboot_live_v1.py",
        "_observe_v3",
    ): (
        "_observation_paths(raw_root, adb_snapshot)",
        "v3._validated_static_inputs()",
        "v3._validated_execution_inputs(static)",
        "p318._prepare_executable_snapshot(",
        "inputs[\"raw\"].prepare_capture_dir(",
        "v3._make_transport(",
        "transport.select_exact()",
        "transport.snapshot(serial)",
        "_health_from_snapshot(",
        "v3._raw_inventory(inputs[\"raw\"])",
    ),
    (
        "s22plus_fyg8_pref1_normal_reboot_live_v1.py",
        "run_normal_reboot",
    ): (
        "require_current=False",
        "state, intent = store._tail()",
        "require_current=True",
        "selected = _observe_v3 if observer is None else observer",
        "_preflight_executor(v3)",
        "store.record_intent(",
        "selected_executor = _default_executor if executor is None else executor",
        "result = selected_executor(v3)",
        "observed = _result_observed(",
        "store.record_healthy_return(observed, now=intent_now)",
        "store.record_uncertain(reason=\"result_uncertain\", now=intent_now)",
        "store.record_close(now=intent_now)",
    ),
    (
        "s22plus_fyg8_p319_d0_fresh_baseline.py",
        "_execute",
    ): (
        "raw.acquire_command(",
        "raw.require_success(handle)",
        "raw.read_stdout(handle, maximum=RAW_SIZE)",
        "raw.read_stderr(handle, maximum=MAX_TEXT)",
        "adapter.classify_clean_baseline(",
    ),
    (
        "s22plus_fyg8_p319_d0_fresh_baseline_v2.py",
        "_execute",
    ): (
        "raw.acquire_command(",
        "raw.require_success(handle)",
        "raw.read_stdout(handle, maximum=RAW_SIZE)",
        "raw.read_stderr(handle, maximum=MAX_TEXT)",
        "adapter.classify_clean_baseline(",
    ),
    (
        "s22plus_fyg8_p319_d0_fresh_baseline_v3.py",
        "_execute",
    ): (
        "raw.acquire_command(",
        "raw.require_success(handle)",
        "raw.read_stdout(handle, maximum=RAW_SIZE)",
        "raw.read_stderr(handle, maximum=MAX_TEXT)",
        "adapter.classify_clean_baseline(",
    ),
    (
        "s22plus_fyg8_p320_d0_fresh_baseline.py",
        "run_live",
    ): (
        "_preflight()",
        "_durable_create(RUN_ARM",
        "client.bind_raw_capture_dir(RUN_DIR)",
        "capture = client.capture(",
        "payload = raw.read_stdout(",
        "observer_result = _classify_clean_baseline(",
        "observer_receipt_payload = _stable_read(",
        "_durable_create(RESULT_PATH, result)",
    ),
    (
        "s22plus_fyg8_p320_d0_fresh_baseline.py",
        "_raw_inventory",
    ): (
        "for child in children:",
        "handle = raw.load_handle(child)",
        "handles.append({",
    ),
    (
        "s22plus_fyg8_p320_d1_fresh_baseline.py",
        "RawFirstTransport.reboot_once",
    ): (
        "handle = self.client.capture_command(",
        "current = self.raw.load_handle(handle.receipt_path)",
        "self.raw.require_success(current)",
        "self.raw.read_stdout(current",
        "self.raw.read_stderr(current",
    ),
    (
        "s22plus_fyg8_p320_d1_fresh_baseline.py",
        "_raw_inventory",
    ): (
        "for name in children:",
        "handle = raw.load_handle(RAW_ADB_DIR / name)",
        "handles.append({",
    ),
    (
        "s22plus_fyg8_p320_d1_fresh_baseline.py",
        "run_live",
    ): (
        "_preflight()",
        "_durable_create(RUN_ARM",
        "_prepare_raw_root()",
        "_prepare_snapshot(adb_payload, ADB_SNAPSHOT)",
        "_load_runtime(",
        "raw_evidence = _raw_inventory(raw)",
        "result = perform_rotation(",
    ),
    (
        "device_action_cdc_acm_observer_v1.py",
        "ModemManagerGuard.arm",
    ): (
        "writer.write_stdout(chunk)",
        "arm_handle = writer.finalize(",
        "retained = raw_capture.read_stdout(",
        'retained == expected + b"\\n"',
    ),
    (
        "device_action_f1_live_v2.py",
        "_P328ObserverSession._read_endpoint",
    ): (
        "self.base._raw_tty(",
        "self.auth_observer.exchange_commands(",
        "writer=writer,",
        "partial = getattr(exc, \"audit\", None)",
        "p330_auth_observer.SessionResult((), partial)",
        "self.exchange = exchange",
        "self.trailing_rx = _p327_trailing_probe(",
        "self.auth_observer.validate_default_proof(",
        'return "accepted"',
    ),
    (
        "device_action_f1_live_v2.py",
        "_P328ObserverSession.observe",
    ): (
        "super()._observe_value(",
        "value = dict(base_value)",
        "accepted = bool(",
        '"classification": classification',
        "value.update(self._receipt_additions(audit))",
        "self._publish_value(",
    ),
    (
        "device_action_f1_live_v2.py",
        "_p328_validate_common_receipt",
    ): (
        "raw_path.read_bytes()",
        "capture_path.read_bytes()",
        "raw_capture.load_handle(",
        "raw_capture.read_stdout(handle",
        "raw_capture.read_stderr(handle",
        'tx = _p328_receipt_identity(value["tx"]',
        'lane = value["lane"]',
    ),
    (
        "device_action_f1_live_v2.py",
        "_p328_validate_receipt",
    ): (
        "_read_json(",
        "_p328_receipt_secret_free(",
        "_p328_validate_common_receipt(",
        "_p328_bound_auth_key_identity(",
        "if accepted:",
        "result = {",
        "return result",
    ),
    (
        "device_action_f1_live_v2.py",
        "_P329ObserverSession._settle_guard_properties",
    ): (
        "P329_UDEV_SETTLE_SEC",
        "self.base.guard.healthy(recheck=True)",
        "self.base.guard.matches_node(endpoint.tty_class)",
        "cdc_acm_observer._resolve_endpoint(",
        "cdc_acm_observer._matches(",
        'return "guard-property-timeout"',
        "P329_UDEV_SETTLE_POLL_SEC",
    ),
    (
        "device_action_f1_live_v2.py",
        "_P329ObserverSession._read_endpoint",
    ): (
        "self._settle_guard_properties(",
        "super()._read_endpoint(endpoint, deadline, writer)",
    ),
    (
        "device_action_f1_live_v2.py",
        "_p329_validate_receipt",
    ): (
        "_p328_validate_receipt(",
        "auth_observer=p329_auth_observer",
        "auth_runtime=p329_auth_runtime",
        "receipt_schema=P329_OBSERVER_RECEIPT_SCHEMA",
    ),
    (
        "s22plus_fyg8_p330_auth_acm_observer.py",
        "exchange_commands",
    ): (
        'stage("banner-read")',
        'stage("open-write")',
        'stage("open-diagnostic-read")',
        "audit.diagnostics.append(opened)",
        'stage("rng-diagnostic-read")',
        "audit.diagnostics.append(rng)",
        'stage("challenge-read")',
        'stage("auth-write")',
        'stage("ready-read")',
        'stage("exec-write")',
        "output.extend(frame.payload)",
        'stage("close-write")',
        'stage("done-read")',
        'stage("complete")',
        "return _BASE.SessionResult(tuple(results), audit)",
        "except Exception as exc:",
        "_raise_partial(",
    ),
    (
        "device_action_f1_live_v2.py",
        "_P330ObserverSession._receipt_additions",
    ): (
        "diagnostics = []",
        "if isinstance(audit, p330_auth_observer.ExchangeAudit)",
        '"diagnostics": diagnostics',
        '"partial_exchange": {',
        '"current_stage": current_stage',
        '"failure_stage": failure_stage',
        '"failure_code": failure_code',
        '"exception_type": exception_type',
        '"exception_sha256": exception_sha256',
    ),
    (
        "device_action_f1_live_v2.py",
        "_p330_validate_receipt",
    ): (
        "return _p328_validate_receipt(",
        "auth_observer=p330_auth_observer",
        "auth_runtime=p330_auth_runtime",
        "receipt_schema=P330_OBSERVER_RECEIPT_SCHEMA",
        "classifications=P330_CLASSIFICATIONS",
        "extra_keys=P330_RECEIPT_EXTRA_KEYS",
        "extra_validator=_p330_validate_receipt_extras",
    ),
    (
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "_read_segment",
    ): (
        "select.select(",
        "os.read(",
        "writer.write_stdout(chunk)",
        "return bytes(payload) == expected",
    ),
    (
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "_write_segment",
    ): (
        "select.select(",
        "os.write(",
        "audit.tx.extend(",
        "return written == len(payload)",
    ),
    (
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "_reject_trailing",
    ): (
        "select.select(",
        "os.read(",
        "writer.write_stdout(chunk)",
        "audit.trailing_rx.extend(chunk)",
        "return False",
    ),
    (
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "_exchange",
    ): (
        "audit.banner_seen = _read_segment(",
        "_write_segment(descriptor, runtime.HOST_PING",
        "audit.pong_seen = _read_segment(",
        "_write_segment(descriptor, runtime.HOST_SHELL",
        "audit.shell_ok_seen = _read_segment(",
        "_reject_trailing(",
    ),
    (
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "_adapt",
    ): (
        "base._raw_tty(descriptor)",
        "_exchange(descriptor, deadline, writer, audit)",
        "observer._resolve_endpoint(",
        "audit.endpoint_identity_sha256 = endpoint.identity_sha256",
        'return "captured"\n        finally:',
        "os.close(descriptor)",
        "base._read_endpoint = read_endpoint",
        "yield audit",
        "base._read_endpoint = original_read",
    ),
    (
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "P326ObserverSession.observe",
    ): (
        "self.delegate.observe(",
        "tx = bytes(self.audit.tx)",
        "_file_receipt(",
        "observer.persist_json(",
        "self.run_dir / RECEIPT_NAME",
        "projected = dict(result)",
        'projected["classification"] = "byte-mismatch"',
        "return projected",
    ),
    (
        "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        "validate_receipt",
    ): (
        "p325.validate_receipt(",
        "_strict_json(",
        "bytes.fromhex(",
        "_file_receipt(",
        "return dict(base) | {",
    ),
    (
        "s22plus_fyg8_p331_resident_acm_observer.py",
        "_exchange_one",
    ): (
        "original_read_frame = _BASE._read_frame",
        "frame = original_read_frame(",
        "_P330.exchange_commands(",
        "writer=writer,",
        "nonce = result.audit.nonce",
        "seen_nonces.add(nonce)",
    ),
    (
        "s22plus_fyg8_p331_resident_acm_observer.py",
        "exchange_session",
    ): (
        "capture = _RawWriter(writer)",
        "return _exchange_one(",
        "_descriptor(descriptor),",
        "capture,",
        "_validate_timeout(timeout_sec),",
    ),
    (
        "device_action_f1_live_v2.py",
        "_P331ObserverSession._read_endpoint",
    ): (
        "for index in range(p331_resident_runtime.MAX_SESSIONS):",
        "self.base._raw_tty(descriptor)",
        "p331_resident_observer.exchange_session(",
        "writer=writer,",
        "seen_nonces=seen_nonces,",
        "_p327_trailing_probe(descriptor, writer)",
        "record = p331_resident_observer.ResidentSession(",
        "records.append(record)",
        "p331_resident_observer.validate_resident_proof(result)",
        "self.resident_result = result",
        'return "accepted"',
    ),
    (
        "device_action_f1_live_v2.py",
        "_P331ObserverSession.observe",
    ): (
        "base_value, lane_supplement = super()._observe_value(",
        "sessions = () if resident is None else resident.sessions",
        'tx = b"".join(item.raw_tx for item in sessions)',
        'rx = b"".join(item.raw_rx for item in sessions)',
        "resident_complete = bool(",
        "value.update(",
        "self._publish_value(",
        "return value",
    ),
    (
        "device_action_f1_live_v2.py",
        "_p331_validate_receipt_unchecked",
    ): (
        "value = _read_json(",
        "_p328_receipt_secret_free(value)",
        "lane, topology, endpoint = _p328_validate_common_receipt(",
        "bound = _p328_bound_auth_key_identity(prepared)",
        "session_count = value[\"session_count\"]",
        "for index, (session_diagnostics, session_retries, session_partial) in enumerate(",
        "typed_evidence.validate_p331_resident_proof(proof)",
        "_p331_validate_raw_session_bindings(prepared, value, validated_proof)",
        "return {",
    ),
    (
        "s22plus_fyg8_p332_logical_resident_acm_observer.py",
        "_exchange_one",
    ): (
        "original_read_frame = _BASE._read_frame",
        "frame = original_read_frame(",
        "_P330.exchange_commands(",
        "writer=writer,",
        "nonce = result.audit.nonce",
        "seen_nonces.add(nonce)",
    ),
    (
        "s22plus_fyg8_p332_logical_resident_acm_observer.py",
        "exchange_resident",
    ): (
        "descriptor = _descriptor(connection)",
        "for index in range(MAX_SESSIONS):",
        "raw_writer = _RawWriter(writer)",
        "_exchange_one(",
        "raw_writer,",
        "records.append(",
        "_validate_one_session(record)",
    ),
    (
        "device_action_f1_live_v2.py",
        "_P332ObserverSession._read_endpoint",
    ): (
        "descriptor = os.open(",
        "self.base._raw_tty(descriptor)",
        "self.auth_observer.exchange_resident(",
        "writer=writer,",
        "self.resident_result = resident",
        "self.trailing_rx = _p327_trailing_probe(descriptor, writer)",
        "self.auth_observer.validate_resident_proof(",
        'return "accepted"',
    ),
    (
        "device_action_f1_live_v2.py",
        "_P332ObserverSession.observe",
    ): (
        "base_value, lane_supplement = super(_P331ObserverSession, self)._observe_value(",
        "sessions = () if resident is None else resident.sessions",
        'tx = b"".join(item.raw_tx for item in sessions)',
        'rx = b"".join(item.raw_rx for item in sessions)',
        "value.update(",
        "self._publish_value(",
        "return value",
    ),
    (
        "device_action_f1_live_v2.py",
        "_p332_validate_raw_session_bindings",
    ): (
        "core._stable_read(",
        "_p332_nonce_from_raw_session(",
        "bytes.fromhex(encoded_tx)",
        'value["tx"]',
        'value["rx"]',
    ),
    (
        "device_action_f1_live_v2.py",
        "_p332_validate_receipt",
    ): (
        "value = _read_json(",
        "_p328_receipt_secret_free(value)",
        'proof_validator(value["proof"])',
        "_p332_validate_raw_session_bindings(",
        "return {",
    ),
    (
        "s22plus_fyg8_p333_open_entry_diag_acm_observer.py",
        "_exchange_one",
    ): (
        "original = _BASE._read_frame",
        "frame = original(fd, deadline, audit, raw_writer)",
        "parse_diagnostic_frame(",
        "if nonce in seen_nonces:",
        "_P332._P330.exchange_commands(",
        "writer=writer,",
        "seen_nonces.add(nonce)",
    ),
    (
        "s22plus_fyg8_p333_open_entry_diag_acm_observer.py",
        "exchange_resident",
    ): (
        "original = _P332._exchange_one",
        "_P332._exchange_one = _exchange_one",
        "_P332.exchange_resident(",
        "writer=writer,",
        "finally:",
        "_P332._exchange_one = original",
    ),
    (
        "device_action_f1_live_v2.py",
        "_logical_resident_candidate_observer_session",
    ): (
        'if spec.get("protocol_contract") != observer_module.CONTRACT_ID:',
        "if entry_diagnostic:",
        "p325_guard_adapter.observer_session(",
        "yield session_type(",
    ),
    (
        "device_action_f1_live_v2.py",
        "_p333_candidate_observer_session",
    ): (
        "with _logical_resident_candidate_observer_session(",
        "observer_module=p333_open_entry_observer",
        "runtime_module=p333_open_entry_runtime",
        "session_type=_P333ObserverSession",
        'label="P3.33"',
        "entry_diagnostic=True",
        "yield session",
    ),
    (
        "device_action_f1_live_v2.py",
        "_p333_validate_receipt",
    ): (
        "return _p332_validate_receipt(",
        "observer_module=p333_open_entry_observer",
        "runtime_module=p333_open_entry_runtime",
        "receipt_schema=P333_OBSERVER_RECEIPT_SCHEMA",
        "classifications=P333_CLASSIFICATIONS",
        "proof_validator=typed_evidence.validate_p333_logical_resident_proof",
        'proof_key="p333_authenticated_logical_resident"',
    ),
    (
        "device_action_f1_live_v2.py",
        "_p334_candidate_observer_session",
    ): (
        "with _logical_resident_candidate_observer_session(",
        "observer_module=p334_first_read_observer",
        "runtime_module=p334_first_read_runtime",
        "session_type=_P334ObserverSession",
        'label="P3.34"',
        "entry_diagnostic=True",
        "yield session",
    ),
    (
        "device_action_f1_live_v2.py",
        "_p334_validate_receipt",
    ): (
        "value = _p332_validate_receipt(",
        "observer_module=p334_first_read_observer",
        "runtime_module=p334_first_read_runtime",
        "receipt_schema=P334_OBSERVER_RECEIPT_SCHEMA",
        "classifications=P334_CLASSIFICATIONS",
        "proof_validator=typed_evidence.validate_p334_logical_resident_proof",
        'proof_key="p334_authenticated_logical_resident"',
        '"first_console_return_checkpoint_only": True',
        "return value",
    ),
}


class RawFirstAuditError(RuntimeError):
    pass


class RawFirstPopulationUnparseableError(RawFirstAuditError):
    """A revalidation population member could not be parsed as Python.

    This is deliberately distinct from a raw-first boundary violation.  A
    source that cannot be parsed is not evidence of a boundary violation, but
    it must never disappear from the population merely because transport
    detection itself needs the AST.
    """

    code = UNPARSEABLE_POPULATION_SOURCE
    CODE = code

    def __init__(
        self,
        source_name: str,
        syntax_error: SyntaxError | None = None,
        *,
        message: str | None = None,
        lineno: int | None = None,
        offset: int | None = None,
        end_lineno: int | None = None,
        end_offset: int | None = None,
    ) -> None:
        if syntax_error is not None:
            message = syntax_error.msg
            lineno = syntax_error.lineno
            offset = syntax_error.offset
            end_lineno = getattr(syntax_error, "end_lineno", None)
            end_offset = getattr(syntax_error, "end_offset", None)
        self.source_name = source_name
        self.name = source_name
        self.filename = source_name
        self.lineno = lineno
        self.line = lineno
        self.offset = offset
        self.column = offset
        self.end_lineno = end_lineno
        self.end_offset = end_offset
        self.syntax_message = message or "invalid syntax"
        self.location = (source_name, lineno, offset)
        location = source_name
        if lineno is not None:
            location += f":{lineno}"
            if offset is not None:
                location += f":{offset}"
        super().__init__(f"{self.code}: {location}: {self.syntax_message}")


def _auditor_normalized_sha256(text: str) -> str:
    pattern = r'AUDITOR_NORMALIZED_SHA256 = "[0-9a-f]{64}"'
    matches = re.findall(pattern, text)
    if len(matches) != 1:
        raise RawFirstAuditError("auditor normalized-source seam differs")
    if matches[0] != (
        'AUDITOR_NORMALIZED_SHA256 = "'
        + AUDITOR_NORMALIZED_SHA256
        + '"'
    ):
        raise RawFirstAuditError("auditor source embeds a different self binding")
    normalized = re.sub(
        pattern,
        'AUDITOR_NORMALIZED_SHA256 = "' + "0" * 64 + '"',
        text,
        count=1,
    ).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _source(path: Path, overrides: Mapping[str, str]) -> str:
    if path.name in overrides:
        return overrides[path.name]
    return path.read_text(encoding="utf-8")


def _stable_source(path: Path, maximum: int = 16 * 1024 * 1024) -> str:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum:
            raise RawFirstAuditError(f"observer source identity differs: {path.name}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise RawFirstAuditError(f"observer source exceeds bound: {path.name}")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_uid,
        item.st_gid,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise RawFirstAuditError(f"observer source changed while reading: {path.name}")
    try:
        return b"".join(chunks).decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise RawFirstAuditError(f"observer source is not UTF-8: {path.name}") from exc


def load_bound_auditor() -> Any:
    source = _stable_source(Path(__file__).resolve())
    payload = source.encode("utf-8")
    module = types.ModuleType("s22plus_fyg8_raw_first_observer_audit_bound")
    module.__file__ = str(Path(__file__).resolve())
    module.__package__ = ""
    module.__dict__["_RAW_FIRST_BOUND_AUDITOR_SOURCE"] = payload
    try:
        code = compile(
            source,
            str(Path(__file__).resolve()),
            "exec",
            dont_inherit=True,
        )
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise RawFirstAuditError(
            "raw-first bound-source execution failed"
        ) from exc
    return module


def _parse_population_source(source_name: str, text: str) -> ast.AST:
    """Parse one full-tree member and classify syntax failure separately."""
    try:
        return ast.parse(text, filename=source_name)
    except SyntaxError as exc:
        raise RawFirstPopulationUnparseableError(source_name, exc) from exc


def _function_sources(text: str) -> dict[str, str]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise RawFirstAuditError("observer source is not valid Python") from exc
    values: dict[str, str] = {}

    def visit(body: list[ast.stmt], prefix: str = "") -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + node.name
                segment = ast.get_source_segment(text, node)
                if segment is None or name in values:
                    raise RawFirstAuditError(f"cannot isolate observer function: {name}")
                values[name] = segment
            elif isinstance(node, ast.ClassDef):
                visit(node.body, prefix + node.name + ".")

    visit(tree.body)
    return values


def _imports_subprocess(text: str, tree: ast.AST | None = None) -> bool:
    if tree is None:
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            raise RawFirstAuditError("revalidation source is not valid Python") from exc
    return any(
        (
            isinstance(node, ast.Import)
            and any(alias.name == "subprocess" for alias in node.names)
        )
        or (
            isinstance(node, ast.ImportFrom)
            and node.module == "subprocess"
        )
        for node in ast.walk(tree)
    )


# Process-spawn capability, not a list of three known-bad idioms.  An adversarial
# review defeated the previous rule with os.system, os.posix_spawn, pty.spawn,
# asyncio.create_subprocess_exec, importlib.import_module("sub"+"process"),
# ctypes.CDLL("libc").system, getattr indirection, and exec of embedded source --
# ten bypasses, each a device-acquiring source the audit passed.  The rule now
# fails closed on anything that can start a process, and on source it cannot
# parse, because an enumeration of bad idioms is open by construction.
SPAWN_MODULES = frozenset({"subprocess", "pty", "ctypes", "asyncio", "multiprocessing"})
SPAWN_ATTRIBUTES = frozenset({
    "system", "popen", "fork", "forkpty", "spawn",
    "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp",
    "spawnv", "spawnve", "spawnvp", "spawnl", "spawnle", "spawnlp",
    "posix_spawn", "posix_spawnp",
    "run", "call", "check_call", "check_output", "Popen",
    "create_subprocess_exec", "create_subprocess_shell",
    "bounded_command", "import_module",
})
SPAWN_NAMES = frozenset({
    "bounded_command", "popen", "exec", "eval", "__import__", "getattr",
})


def _uses_legacy_acquisition(text: str, tree: ast.AST | None = None) -> bool:
    if tree is None:
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            raise RawFirstAuditError("revalidation source is not valid Python") from exc
    if _imports_subprocess(text, tree):
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                (alias.name or "").split(".")[0] in SPAWN_MODULES
                for alias in node.names
            ):
                return True
            continue
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in SPAWN_MODULES:
                return True
            continue
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in SPAWN_NAMES:
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr in SPAWN_ATTRIBUTES:
            return True
    return False


def _audit_function_contracts(
    root: Path, overrides: Mapping[str, str]
) -> dict[str, str]:
    identities: dict[str, str] = {}
    for filename, contracts in FUNCTION_CONTRACTS.items():
        path = root / filename
        text = _source(path, overrides)
        functions = _function_sources(text)
        for name, (required, forbidden) in contracts.items():
            body = functions.get(name)
            if body is None:
                raise RawFirstAuditError(f"raw-first function is absent: {filename}:{name}")
            for token in required:
                if body.count(token) < 1:
                    raise RawFirstAuditError(
                        f"raw-first seam differs: {filename}:{name}:{token}"
                    )
            for token in forbidden:
                if token in body:
                    raise RawFirstAuditError(
                        f"write-after-parse seam is present: {filename}:{name}:{token}"
                    )
            ordered = ORDERED_FUNCTION_TOKENS.get((filename, name), ())
            positions = [body.find(token) for token in ordered]
            if positions and (
                any(position < 0 for position in positions)
                or positions != sorted(positions)
                or len(set(positions)) != len(positions)
            ):
                raise RawFirstAuditError(
                    f"raw-first operation order differs: {filename}:{name}"
                )
            identities[f"{filename}:{name}"] = hashlib.sha256(
                body.encode("utf-8")
            ).hexdigest()
    return identities


def _candidate_d0_sources(
    root: Path,
    overrides: Mapping[str, str],
    parsed_sources: Mapping[str, ast.AST] | None = None,
) -> list[str]:
    values: list[str] = []
    paths = {path.name: path for path in root.glob("*.py")}
    for name in overrides:
        paths.setdefault(name, root / name)
    for name, path in sorted(paths.items()):
        if re.fullmatch(r"(?:device_action|s22plus)[A-Za-z0-9_]*d0[A-Za-z0-9_]*\.py", name) is None:
            continue
        text = _source(path, overrides)
        tree = (
            parsed_sources[name]
            if parsed_sources is not None and name in parsed_sources
            else None
        )
        if not _uses_legacy_acquisition(text, tree):
            continue
        values.append(name)
        if name not in ACTIVE_FILES:
            raise RawFirstAuditError(
                f"S22 D0 source bypasses common raw capture: {name}"
            )
        if RAW_MODULE not in text:
            raise RawFirstAuditError(
                f"S22 D0 source lacks common raw capture: {name}"
            )
    return values


# Text markers that a source can start a process at all.  The full population
# is syntax-validated before this marker filter; these markers bound the extra
# folded-literal walk to sources that can start a process.
SPAWN_TEXT_MARKERS = (
    "subprocess", "os.system", "os.exec", "os.spawn", "posix_spawn",
    "pty.", "ctypes", "asyncio", "import_module", "__import__",
    "bounded_command", "popen",
)


def _folded_string_constants(
    text: str,
    source_name: str = "<text>",
    tree: ast.AST | None = None,
) -> list[str]:
    """String literals as the parser folds them, not as they are typed."""
    tree = tree or _parse_population_source(source_name, text)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _touches_device_transport(
    text: str,
    source_name: str = "<text>",
    tree: ast.AST | None = None,
) -> bool:
    if any(pattern.search(text) for pattern in DEVICE_TRANSPORT_PATTERNS):
        return True
    # A regex over source text cannot see `"a" "d" "b"`, which the parser folds
    # to the real transport name before anything runs.  A review defeated the
    # text-only gate with exactly that, so spawn-capable sources are re-checked
    # against their folded literals.
    if not any(marker in text for marker in SPAWN_TEXT_MARKERS):
        return False
    tree = tree or _parse_population_source(source_name, text)
    return any(
        pattern.search(value)
        for value in _folded_string_constants(text, source_name, tree)
        for pattern in DEVICE_TRANSPORT_PATTERNS
    )


def _audit_host_only_non_acquiring_source(name: str, text: str) -> dict[str, Any]:
    spec = S22_HOST_ONLY_NON_ACQUIRING_SOURCE_SPECS.get(name)
    if spec is None:
        raise RawFirstAuditError(f"host-only source is not registered: {name}")
    payload = text.encode("utf-8")
    if len(payload) != spec["size"] or hashlib.sha256(payload).hexdigest() != spec["sha256"]:
        raise RawFirstAuditError(f"host-only source identity differs: {name}")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise RawFirstAuditError(f"host-only source is not valid Python: {name}") from exc
    if spec.get("exact_host_tool") is True:
        return {
            "name": name,
            "owner": spec["owner"],
            "classification": spec["classification"],
            "profile": spec["profile"],
            "size": spec["size"],
            "sha256": spec["sha256"],
        }
    forbidden_imports = {"subprocess", "pty", "asyncio", "multiprocessing", "ctypes"}
    forbidden_attributes = {
        "system", "popen", "fork", "forkpty", "execv", "execve", "execvp",
        "execvpe", "execl", "execle", "execlp", "posix_spawn", "posix_spawnp",
        "bounded_command",
    }
    exec_sites: list[tuple[int, str]] = []
    getattr_sites: list[int] = []
    forbidden_call: str | None = None

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.function = "<module>"

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            old = self.function
            self.function = node.name
            self.generic_visit(node)
            self.function = old

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Import(self, node: ast.Import) -> None:
            nonlocal forbidden_call
            if any((alias.name or "").split(".")[0] in forbidden_imports for alias in node.names):
                forbidden_call = f"forbidden import at line {node.lineno}"
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            nonlocal forbidden_call
            if (node.module or "").split(".")[0] in forbidden_imports:
                forbidden_call = f"forbidden import at line {node.lineno}"
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            nonlocal forbidden_call
            if isinstance(node.func, ast.Name) and node.func.id == "exec":
                valid = (
                    node.lineno in spec["exec_lines"]
                    and self.function in {"_load_stock", "_load_adapter"}
                    and len(node.args) == 2
                    and isinstance(node.args[0], ast.Call)
                    and isinstance(node.args[0].func, ast.Name)
                    and node.args[0].func.id == "compile"
                    and len(node.args[0].args) == 3
                    and isinstance(node.args[0].args[2], ast.Constant)
                    and node.args[0].args[2].value == "exec"
                    and isinstance(node.args[1], ast.Attribute)
                    and node.args[1].attr == "__dict__"
                )
                if not valid:
                    forbidden_call = f"unapproved exec at line {node.lineno}"
                else:
                    exec_sites.append((node.lineno, self.function))
            elif isinstance(node.func, ast.Name) and node.func.id in {"eval", "__import__"}:
                forbidden_call = f"forbidden call at line {node.lineno}"
            elif isinstance(node.func, ast.Name) and node.func.id == "getattr":
                valid = (
                    node.lineno == spec["getattr_line"]
                    and len(node.args) == 3
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "os"
                    and isinstance(node.args[1], ast.Constant)
                    and node.args[1].value == "O_DIRECTORY"
                    and isinstance(node.args[2], ast.Constant)
                    and node.args[2].value == 0
                )
                if not valid:
                    forbidden_call = f"unapproved getattr at line {node.lineno}"
                else:
                    getattr_sites.append(node.lineno)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_attributes:
                forbidden_call = f"forbidden call at line {node.lineno}"
            self.generic_visit(node)

    Visitor().visit(tree)
    if forbidden_call is not None:
        raise RawFirstAuditError(f"host-only source semantic boundary differs: {name}: {forbidden_call}")
    if sorted(exec_sites) != [(line, function) for line, function in ((238, "_load_stock"), (252, "_load_adapter"))]:
        raise RawFirstAuditError(f"host-only source exec sites differ: {name}")
    if getattr_sites != [spec["getattr_line"]]:
        raise RawFirstAuditError(f"host-only source getattr site differs: {name}")
    required_fields = (
        '"tier": "H0"',
        '"host_only": True',
        '"device_contact": False',
        '"live_authorized": False',
        '"approval_created": False',
        '"process_v2_integration_created": False',
        '"process_v2_ready_created": False',
        '"process_v2_run_binding": False',
    )
    if any(field not in text for field in required_fields):
        raise RawFirstAuditError(f"host-only source process boundary differs: {name}")
    return {
        "name": name,
        "owner": spec["owner"],
        "classification": spec["classification"],
        "profile": spec["profile"],
        "size": spec["size"],
        "sha256": spec["sha256"],
        "exec_lines": list(spec["exec_lines"]),
        "getattr_line": spec["getattr_line"],
    }


def _host_only_non_acquiring_sources(
    root: Path, overrides: Mapping[str, str]
) -> tuple[list[dict[str, Any]], str]:
    paths = {path.name: path for path in root.glob("*.py")}
    for name in overrides:
        paths.setdefault(name, root / name)
    values = []
    for name in sorted(S22_HOST_ONLY_NON_ACQUIRING_SOURCE_SPECS):
        if name not in paths:
            raise RawFirstAuditError(f"host-only source is absent: {name}")
        values.append(_audit_host_only_non_acquiring_source(name, _source(paths[name], overrides)))
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return values, hashlib.sha256(encoded).hexdigest()


def _validate_population_sources(
    root: Path, overrides: Mapping[str, str]
) -> dict[str, ast.AST]:
    """Syntax-validate every full-tree member before any population filter."""
    paths = {path.name: path for path in root.glob("*.py")}
    for name in overrides:
        paths.setdefault(name, root / name)
    parsed: dict[str, ast.AST] = {}
    for name, path in sorted(paths.items()):
        parsed[name] = _parse_population_source(name, _source(path, overrides))
    return parsed


def _device_acquisition_sources(
    root: Path,
    overrides: Mapping[str, str],
    parsed_sources: Mapping[str, ast.AST] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Require the raw-first boundary from every target-acquiring source.

    Filename shape is not evidence.  Any source that both acquires output and
    reaches the device transport must be an active raw-first observer or an
    explicitly frozen pre-boundary source.  A new acquiring source is rejected
    under any filename until it is migrated or frozen, so a successor observer
    cannot reintroduce write-after-parse by being named outside a pattern.

    Membership is checked for every target so a new source always stops here.
    Only S22+-scoped bytes are frozen, because this contract must not fail on
    an ordinary A90 or S20+ edit.
    """

    paths = {path.name: path for path in root.glob("*.py")}
    for name in overrides:
        paths.setdefault(name, root / name)
    frozen: list[dict[str, Any]] = []
    for name, path in sorted(paths.items()):
        text = _source(path, overrides)
        tree = (
            parsed_sources[name]
            if parsed_sources is not None and name in parsed_sources
            else _parse_population_source(name, text)
        )
        if name in S22_HOST_ONLY_NON_ACQUIRING_SOURCE_SPECS:
            _audit_host_only_non_acquiring_source(name, text)
            continue
        # The complete population was parsed before this filter; reuse that
        # tree so transport detection cannot make an invalid member disappear.
        if not _touches_device_transport(text, name, tree):
            continue
        if not _uses_legacy_acquisition(text, tree):
            continue
        if name in ACTIVE_FILES:
            # P3.26 is the one active predecessor wrapper that receives the
            # already-owned RawCaptureWriter from the P3.24/P3.25 delegate;
            # its exact source pin and writer/read/receipt contracts above
            # replace a local import of the common raw module.  No other
            # active source may use this injected-writer exception.
            if (
                RAW_MODULE not in text
                and name not in RAW_CAPTURE_INJECTED_WRITER_SOURCES
            ):
                raise RawFirstAuditError(
                    f"active device source lacks common raw capture: {name}"
                )
            continue
        if name not in PRE_BOUNDARY_DEVICE_SOURCES:
            raise RawFirstAuditError(
                f"device-acquiring source bypasses the raw-first boundary: {name}"
            )
        if S22_SCOPED_SOURCE_RE.fullmatch(name) is None:
            # Another target owns these bytes.  Membership still blocks a new
            # unmigrated source, but this S22+ contract must not freeze A90 or
            # S20+ sources and break their parallel work.
            continue
        payload = text.encode("utf-8")
        frozen.append(
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    encoded = json.dumps(
        frozen,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return frozen, hashlib.sha256(encoded).hexdigest()


def _legacy_unmigrated_observers(
    root: Path,
    overrides: Mapping[str, str],
    parsed_sources: Mapping[str, ast.AST] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Freeze pre-boundary inactive observers while scanning the whole tree."""

    paths = {path.name: path for path in root.glob("*.py")}
    for name in overrides:
        paths.setdefault(name, root / name)
    values: list[dict[str, Any]] = []
    for name, path in sorted(paths.items()):
        if name in ACTIVE_FILES or OBSERVER_FILE_RE.fullmatch(name) is None:
            continue
        text = _source(path, overrides)
        tree = (
            parsed_sources[name]
            if parsed_sources is not None and name in parsed_sources
            else None
        )
        if not _uses_legacy_acquisition(text, tree):
            continue
        payload = text.encode("utf-8")
        values.append(
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    encoded = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return values, hashlib.sha256(encoded).hexdigest()


def _closed_observer_sources(
    root: Path, overrides: Mapping[str, str]
) -> tuple[list[dict[str, Any]], str]:
    paths = {path.name: path for path in root.glob("*.py")}
    for name in overrides:
        paths.setdefault(name, root / name)
    names = sorted(
        name
        for name in paths
        if name not in ACTIVE_FILES and OBSERVER_FILE_RE.fullmatch(name)
    )
    values = []
    for name in names:
        payload = _source(paths[name], overrides).encode("utf-8")
        values.append(
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    encoded = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return values, hashlib.sha256(encoded).hexdigest()


def audit_sources(
    root: Path = SCRIPT_DIR,
    overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        # Executing module and on-disk source can disagree.  Swapping one pinned
        # 64-hex digest for another leaves the file the same size, and when both
        # edits land in one mtime second the .pyc invalidation check does not
        # trip, so this module's constants can come from stale bytecode while
        # the audit itself compiles from the file.  Refuse rather than audit
        # under two different sets of constants.
        embedded = re.search(
            r'AUDITOR_NORMALIZED_SHA256 = "([0-9a-f]{64})"',
            _stable_source(Path(__file__).resolve()),
        )
        if embedded is None or embedded.group(1) != AUDITOR_NORMALIZED_SHA256:
            raise RawFirstAuditError(
                "executing auditor constants differ from its source; "
                "stale bytecode is the usual cause"
            )
        bound = load_bound_auditor()
        try:
            return bound.audit_sources(root, overrides)
        except bound.RawFirstPopulationUnparseableError as exc:
            raise RawFirstPopulationUnparseableError(
                exc.source_name,
                message=exc.syntax_message,
                lineno=exc.lineno,
                offset=exc.offset,
                end_lineno=exc.end_lineno,
                end_offset=exc.end_offset,
            ) from exc
        except bound.RawFirstAuditError as exc:
            raise RawFirstAuditError(str(exc)) from exc
    if (
        _stable_source(Path(__file__).resolve()).encode("utf-8")
        != _BOUND_AUDITOR_SOURCE
    ):
        raise RawFirstAuditError("executed auditor bytes differ before audit")
    supplied = overrides or {}
    paths = sorted(root.glob("*.py"), key=lambda path: path.name)
    overrides = {path.name: _stable_source(path) for path in paths}
    overrides.update(supplied)
    names = {path.name for path in paths}
    if not ACTIVE_FILES <= names | set(supplied):
        raise RawFirstAuditError("raw-first active source inventory is incomplete")
    auditor_source = overrides.get(Path(__file__).name)
    if (
        auditor_source is None
        or _auditor_normalized_sha256(auditor_source)
        != AUDITOR_NORMALIZED_SHA256
    ):
        raise RawFirstAuditError("loaded auditor differs from its stable source")
    # This must precede every transport/acquisition filter.  In particular, a
    # split transport literal is invisible to the text regex, so a SyntaxError
    # there must not be deferred to a later generic parser failure; classify
    # the exact population member before any filter can continue.
    parsed_population = _validate_population_sources(root, overrides)
    function_sha256 = _audit_function_contracts(root, overrides)
    d0_candidates = _candidate_d0_sources(root, overrides, parsed_population)
    legacy_observers, legacy_sha256 = _legacy_unmigrated_observers(
        root, overrides, parsed_population
    )
    host_only_sources, host_only_sha256 = _host_only_non_acquiring_sources(
        root, overrides
    )
    device_sources, device_sources_sha256 = _device_acquisition_sources(
        root, overrides, parsed_population
    )
    closed_sources, closed_sources_sha256 = _closed_observer_sources(
        root, overrides
    )
    if (
        len(legacy_observers) != LEGACY_UNMIGRATED_OBSERVER_COUNT
        or legacy_sha256 != LEGACY_UNMIGRATED_OBSERVER_SHA256
    ):
        raise RawFirstAuditError(
            "legacy observer inventory differs: "
            f"count={len(legacy_observers)} sha256={legacy_sha256}"
        )
    if (
        len(device_sources) != PRE_BOUNDARY_DEVICE_SOURCE_COUNT
        or device_sources_sha256 != PRE_BOUNDARY_DEVICE_SOURCE_SHA256
    ):
        raise RawFirstAuditError(
            "pre-boundary device source inventory differs: "
            f"count={len(device_sources)} sha256={device_sources_sha256}"
        )
    if (
        len(closed_sources) != CLOSED_OBSERVER_SOURCE_COUNT
        or closed_sources_sha256 != CLOSED_OBSERVER_SOURCE_SHA256
    ):
        raise RawFirstAuditError(
            "closed observer source inventory differs: "
            f"count={len(closed_sources)} sha256={closed_sources_sha256}"
        )

    adapter = _source(root / "device_action_f1_live_v2.py", overrides)
    closure_body = _function_sources(adapter).get("_closure", "")
    if (
        closure_body.count('"raw_capture": scripts / "device_action_raw_capture_v1.py"')
        != 1
        or closure_body.count('"usb_trace_sidecar": Path(usb_trace_sidecar.__file__).resolve()')
        != 1
        or closure_body.count('"p300_usb_trace_binding": Path(p300_usb_trace.__file__).resolve()')
        != 1
    ):
        raise RawFirstAuditError("F1 execution closure omits raw observer sources")

    all_sources = dict(overrides)
    subprocess_modules = sorted(
        name
        for name, text in all_sources.items()
        if _imports_subprocess(text, parsed_population.get(name))
    )
    observer_named_modules = sorted(
        name
        for name, text in all_sources.items()
        if (
            ("observer" in name or "_d0" in name)
            and _imports_subprocess(text, parsed_population.get(name))
            and (name.startswith("device_action") or name.startswith("s22plus"))
            and name != Path(__file__).name
        )
    )
    audited_observer_modules = sorted(FUNCTION_CONTRACTS)
    unaudited_current = sorted(
        name
        for name in observer_named_modules
        if name in ACTIVE_FILES and name not in FUNCTION_CONTRACTS
    )
    if unaudited_current:
        raise RawFirstAuditError(
            "active observer subprocess source is unaudited: "
            + ",".join(unaudited_current)
        )

    source_identities = {
        name: {
            "size": len(_source(root / name, overrides).encode("utf-8")),
            "sha256": hashlib.sha256(
                _source(root / name, overrides).encode("utf-8")
            ).hexdigest(),
        }
        for name in sorted(ACTIVE_FILES)
    }
    expected_names = ACTIVE_FILES - {Path(__file__).name}
    if set(EXPECTED_ACTIVE_SOURCE_SHA256) != expected_names:
        raise RawFirstAuditError("active source freeze inventory differs")
    for name, expected in EXPECTED_ACTIVE_SOURCE_SHA256.items():
        if source_identities[name]["sha256"] != expected:
            raise RawFirstAuditError(f"active raw-first source changed: {name}")
    if source_identities["device_action_f1_live_v2.py"] != P328_LIVE_SOURCE_IDENTITY:
        raise RawFirstAuditError("P3.28 live source identity differs")
    if any(name not in function_sha256 for name in P328_RAW_FIRST_FUNCTIONS):
        raise RawFirstAuditError("P3.28 raw-first function contract is incomplete")
    for name, expected in P331_ACTIVE_SOURCE_IDENTITIES.items():
        if source_identities.get(name) != expected:
            raise RawFirstAuditError(f"P3.31 active source identity differs: {name}")
    if any(name not in function_sha256 for name in P331_RAW_FIRST_FUNCTIONS):
        raise RawFirstAuditError("P3.31 raw-first function contract is incomplete")
    for name, expected in P332_ACTIVE_SOURCE_IDENTITIES.items():
        if source_identities.get(name) != expected:
            raise RawFirstAuditError(f"P3.32 active source identity differs: {name}")
    if any(name not in function_sha256 for name in P332_RAW_FIRST_FUNCTIONS):
        raise RawFirstAuditError("P3.32 raw-first function contract is incomplete")
    for name, expected in P333_ACTIVE_SOURCE_IDENTITIES.items():
        if source_identities.get(name) != expected:
            raise RawFirstAuditError(f"P3.33 active source identity differs: {name}")
    if any(name not in function_sha256 for name in P333_RAW_FIRST_FUNCTIONS):
        raise RawFirstAuditError("P3.33 raw-first function contract is incomplete")
    for name, expected in P334_ACTIVE_SOURCE_IDENTITIES.items():
        if source_identities.get(name) != expected:
            raise RawFirstAuditError(f"P3.34 active source identity differs: {name}")
    if any(name not in function_sha256 for name in P334_RAW_FIRST_FUNCTIONS):
        raise RawFirstAuditError("P3.34 raw-first function contract is incomplete")
    if (
        source_identities["s22plus_fyg8_p326_bidirectional_acm_observer.py"]
        != P326_ACTIVE_SOURCE_IDENTITY
    ):
        raise RawFirstAuditError("P3.26 active observer identity differs")
    if any(name not in function_sha256 for name in P326_RAW_FIRST_FUNCTIONS):
        raise RawFirstAuditError("P3.26 raw-first function contract is incomplete")

    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "hazard": "WRITE_AFTER_PARSE_DEVICE_EVIDENCE_LOSS",
        "boundary": "S22PLUS_D0_F1_RAW_FIRST_OBSERVER_PRESERVATION",
        "permanent": True,
        "expiry": None,
        "review_triggers": [
            "raw acquisition implementation changes",
            "parser handle signature changes",
            "S22 D0 or F1 observer execution closure changes",
        ],
        "all_revalidation_python_files_scanned": len(paths),
        "subprocess_modules_scanned": len(subprocess_modules),
        "observer_named_subprocess_modules": len(observer_named_modules),
        "legacy_unmigrated_observer_sources": len(legacy_observers),
        "legacy_unmigrated_observer_inventory_sha256": legacy_sha256,
        "legacy_unmigrated_observers_are_inactive_and_byte_frozen": True,
        "closed_observer_source_count": len(closed_sources),
        "closed_observer_source_inventory_sha256": closed_sources_sha256,
        "closed_observer_sources_are_byte_frozen": True,
        "pre_boundary_device_source_count": len(device_sources),
        "pre_boundary_device_source_inventory_sha256": device_sources_sha256,
        "p319_d1_pre_boundary_classification": dict(
            P319_D1_PRE_BOUNDARY_CLASSIFICATION
        ),
        "host_only_non_acquiring_source_count": len(host_only_sources),
        "host_only_non_acquiring_source_inventory_sha256": host_only_sha256,
        "host_only_non_acquiring_sources_are_byte_frozen": True,
        "host_only_non_acquiring_sources": host_only_sources,
        "pre_boundary_cross_target_membership_count": sum(
            1 for name in PRE_BOUNDARY_DEVICE_SOURCES
            if S22_SCOPED_SOURCE_RE.fullmatch(name) is None
        ),
        # Two hardcoded True literals stood here and were published as evidence.
        # An adversarial review refuted the second with ten working bypasses, so
        # both are removed rather than restated. What the rule actually does is
        # stated in the report; it is a process-spawn-capability test, not a
        # soundness proof, and it is not self-certifying.
        "acquisition_rule": "process_spawn_capability_v2",
        "new_or_changed_observer_source_requires_review": True,
        "audited_active_observer_modules": audited_observer_modules,
        "d0_subprocess_candidates": d0_candidates,
        "function_sha256": function_sha256,
        "source_identities": source_identities,
        "p328_live_source_identity": dict(P328_LIVE_SOURCE_IDENTITY),
        "p328_raw_first_function_sha256": {
            name: function_sha256[name] for name in P328_RAW_FIRST_FUNCTIONS
        },
        "p331_active_source_identities": {
            name: dict(identity)
            for name, identity in P331_ACTIVE_SOURCE_IDENTITIES.items()
        },
        "p331_live_source_identity": dict(
            P331_ACTIVE_SOURCE_IDENTITIES["device_action_f1_live_v2.py"]
        ),
        "p331_raw_first_function_sha256": {
            name: function_sha256[name] for name in P331_RAW_FIRST_FUNCTIONS
        },
        "p331_raw_writer_precedes_session_parser": True,
        "p331_session_order_and_nonce_replay_checks": True,
        "p332_active_source_identities": {
            name: dict(identity)
            for name, identity in P332_ACTIVE_SOURCE_IDENTITIES.items()
        },
        "p332_live_source_identity": dict(
            P332_ACTIVE_SOURCE_IDENTITIES["device_action_f1_live_v2.py"]
        ),
        "p332_raw_first_function_sha256": {
            name: function_sha256[name] for name in P332_RAW_FIRST_FUNCTIONS
        },
        "p332_raw_writer_precedes_session_parser": True,
        "p332_same_fd_session_receipt_bindings": True,
        "p332_session_order_and_nonce_replay_checks": True,
        "p333_active_source_identities": {
            name: dict(identity)
            for name, identity in P333_ACTIVE_SOURCE_IDENTITIES.items()
        },
        "p333_live_source_identity": dict(
            P333_ACTIVE_SOURCE_IDENTITIES["device_action_f1_live_v2.py"]
        ),
        "p333_raw_first_function_sha256": {
            name: function_sha256[name] for name in P333_RAW_FIRST_FUNCTIONS
        },
        "p333_raw_writer_precedes_session_parser": True,
        "p333_same_fd_session_receipt_bindings": True,
        "p333_session_order_and_nonce_replay_checks": True,
        "p334_active_source_identities": {
            name: dict(identity)
            for name, identity in P334_ACTIVE_SOURCE_IDENTITIES.items()
        },
        "p334_live_source_identity": dict(
            P334_ACTIVE_SOURCE_IDENTITIES["device_action_f1_live_v2.py"]
        ),
        "p334_raw_first_function_sha256": {
            name: function_sha256[name] for name in P334_RAW_FIRST_FUNCTIONS
        },
        "p334_raw_writer_precedes_session_parser": True,
        "p334_same_fd_session_receipt_bindings": True,
        "p334_session_order_and_nonce_replay_checks": True,
        "p328_raw_finalization_precedes_receipt_parse": True,
        "p328_candidate_observer_no_delete_or_overwrite": True,
        "p326_active_source_identity": dict(P326_ACTIVE_SOURCE_IDENTITY),
        "p326_raw_first_function_sha256": {
            name: function_sha256[name] for name in P326_RAW_FIRST_FUNCTIONS
        },
        "auditor_normalized_sha256": AUDITOR_NORMALIZED_SHA256,
        "auditor_bound_source_execution": True,
        "active_execution_sources_byte_frozen": True,
        "device_observation_parser_accepts_live_stream": False,
        "guard_readiness_marker_is_acquisition_control_not_result_classification": True,
        "guard_arm_marker_parsed_only_from_finalized_handle": True,
        "p300_sidecar_nested_raw_receipts_reopened": True,
        "f1_final_observer_phase_capture_bound": True,
        "raw_mode": "0400",
        "raw_no_clobber": True,
        "raw_file_fsync_before_parse": True,
        "raw_directory_fsync_before_parse": True,
        "d0_covered": True,
        "f1_covered": True,
        "device_contact": False,
        "live_authorized": False,
    }
    if (
        _stable_source(Path(__file__).resolve()).encode("utf-8")
        != _BOUND_AUDITOR_SOURCE
    ):
        raise RawFirstAuditError("executed auditor bytes differ after audit")
    return result


def encode_receipt(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _stable_receipt(path: Path, maximum: int) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_nlink != 1
            or not 0 <= before.st_size <= maximum
        ):
            raise RawFirstAuditError("raw-first receipt identity differs")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise RawFirstAuditError("raw-first receipt exceeds its bound")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_uid,
        item.st_gid,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise RawFirstAuditError("raw-first receipt changed while reading")
    return b"".join(chunks)


def write_receipt(path: Path, payload: bytes) -> None:
    path = path.absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    parent_info = os.lstat(path.parent)
    if (
        not stat.S_ISDIR(parent_info.st_mode)
        or stat.S_ISLNK(parent_info.st_mode)
        or path.parent.resolve(strict=True) != path.parent
    ):
        raise RawFirstAuditError("raw-first receipt directory is indirect")
    if path.exists() or path.is_symlink():
        if _stable_receipt(path, max(len(payload), 1)) != payload:
            raise RawFirstAuditError("existing raw-first receipt differs")
        return
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_CLOEXEC
        | getattr(os, "O_NOFOLLOW", 0),
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise RawFirstAuditError("short raw-first receipt write")
            offset += written
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o400
            or info.st_nlink != 1
            or info.st_size != len(payload)
        ):
            raise RawFirstAuditError("raw-first receipt identity differs")
    finally:
        os.close(descriptor)
    directory = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    if _stable_receipt(path, max(len(payload), 1)) != payload:
        raise RawFirstAuditError("published raw-first receipt differs")


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        value = audit_sources()
        payload = encode_receipt(value)
        write_receipt(args.output or DEFAULT_OUTPUT, payload)
    except RawFirstPopulationUnparseableError as exc:
        print(f"S22+ raw-first observer audit {exc.code}: {exc}")
        return 3
    except (OSError, RawFirstAuditError) as exc:
        print(f"S22+ raw-first observer audit error: {exc}")
        return 2
    print(payload.decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
