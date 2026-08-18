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
AUDITOR_NORMALIZED_SHA256 = "725f0f5878ca1fe392bd8e610b64df31766d368ae2010d678e591551cadfbc8d"
SCRIPT_DIR = Path(__file__).resolve().parent
_BOUND_AUDITOR_SOURCE = globals().get("_RAW_FIRST_BOUND_AUDITOR_SOURCE")
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260817-01.json"
)
LEGACY_UNMIGRATED_OBSERVER_COUNT = 47
LEGACY_UNMIGRATED_OBSERVER_SHA256 = (
    "088d6a19e69378e9072edb203caa482fb7ea4f47aa90821b2d43ecfdcc57c51a"
)
CLOSED_OBSERVER_SOURCE_COUNT = 125
CLOSED_OBSERVER_SOURCE_SHA256 = (
    "8e7fc3369b3b868e3febbb9e43c18447ea1daa3dfe003fbac33d2615547c6d86"
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
PRE_BOUNDARY_DEVICE_SOURCE_COUNT = 127
PRE_BOUNDARY_DEVICE_SOURCE_SHA256 = (
    "c7029746710d2f83d710a3abbecbba5a6bbc3367c7a5f20a559b63a92f1677db"
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
        "s20plus_g986n_d0_inventory.py",
        "s20plus_g986n_download_exit_d1.py",
        "s20plus_g986n_magisk_bootstrap_f1.py",
        "s20plus_g986n_native_canary_r1.py",
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
    "device_action_f1_live_v2.py",
}
EXPECTED_ACTIVE_SOURCE_SHA256 = {
    "device_action_cdc_acm_observer_v1.py": "a1fa4dc117fcd9b1f755f50a7d105a86f7b8ddf43ef30a48d34c0b1f0dcf0da1",
    "device_action_d0_v2.py": "e71894396ca0c9ba0657a1c83d45883b99f53887c1fb87076ea0a38bbee5c37a",
    "device_action_f1_live_v2.py": "1acb93802479ed6061cb7dd0f97859b7dfbc232cc25f28c210d6a0482d6823f1",
    "device_action_raw_capture_v1.py": "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4",
    "device_action_usb_trace_sidecar_v1.py": "f4a87987c0feddf00e89235070ccfaebf6f29353d06f3aa0c887dc3da6dc12ab",
    "s22plus_boot_only_f1_transport.py": "f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea",
    "s22plus_boot_only_live_core.py": "f5411d39e11e1f5e2b4ff63c0fe6c3a1874ef0dd5c33c91cbab4f736f4521af1",
    "s22plus_fyg8_max77705_sysfs_d0.py": "8fc0eb11ec25822823a0fbce95090822908fa4742b95ffa500fcf5637cf41a4d",
    "s22plus_fyg8_p257_stock_pivot_d0.py": "143821a4ebda2e04992ad36c4acbd5b73fe09a47174eb56c79c5526a5513dbae",
    "s22plus_fyg8_p300_usb_trace_binding.py": "d987d6732132eea3adddf27ed42336486d914706b6555ba279cd98c4987e613f",
    "s22plus_fyg8_p303_stock_log_d0.py": "7e963b5144705c2f27fa8f91f4e139e92608732efc401910049cd5ff88868a4d",
    "s22plus_fyg8_p319_max77705_attribute_stage_a.py": "c28097ef576f971ff427c97bdf62d839047c1c4ec1a861c8bf39592dc352fc38",
    "s22plus_odin_transition_core.py": "a44e5ce43eebc3d254c1cc428b986484f244d47ae13a4125399c26c4b3e4014c",
    "s22plus_odin_usbfs_identity.py": "e337026d70f4c231468bfddab4a28e9ae65ab142f82859370c926332fb7bb9b5",
}

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
    },
}

ORDERED_FUNCTION_TOKENS = {
    (
        "device_action_cdc_acm_observer_v1.py",
        "ModemManagerGuard.arm",
    ): (
        "writer.write_stdout(chunk)",
        "arm_handle = writer.finalize(",
        "retained = raw_capture.read_stdout(",
        'retained == expected + b"\\n"',
    ),
}


class RawFirstAuditError(RuntimeError):
    pass


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


def _imports_subprocess(text: str) -> bool:
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


def _uses_legacy_acquisition(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise RawFirstAuditError("revalidation source is not valid Python") from exc
    if _imports_subprocess(text):
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
    root: Path, overrides: Mapping[str, str]
) -> list[str]:
    values: list[str] = []
    paths = {path.name: path for path in root.glob("*.py")}
    for name in overrides:
        paths.setdefault(name, root / name)
    for name, path in sorted(paths.items()):
        if re.fullmatch(r"(?:device_action|s22plus)[A-Za-z0-9_]*d0[A-Za-z0-9_]*\.py", name) is None:
            continue
        text = _source(path, overrides)
        if not _uses_legacy_acquisition(text):
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


# Text markers that a source can start a process at all.  Only these files are
# worth the AST pass below, which keeps a full audit bounded instead of parsing
# every file in the tree.
SPAWN_TEXT_MARKERS = (
    "subprocess", "os.system", "os.exec", "os.spawn", "posix_spawn",
    "pty.", "ctypes", "asyncio", "import_module", "__import__",
    "bounded_command", "popen",
)


def _folded_string_constants(text: str) -> list[str]:
    """String literals as the parser folds them, not as they are typed."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _touches_device_transport(text: str) -> bool:
    if any(pattern.search(text) for pattern in DEVICE_TRANSPORT_PATTERNS):
        return True
    # A regex over source text cannot see `"a" "d" "b"`, which the parser folds
    # to the real transport name before anything runs.  A review defeated the
    # text-only gate with exactly that, so spawn-capable sources are re-checked
    # against their folded literals.
    if not any(marker in text for marker in SPAWN_TEXT_MARKERS):
        return False
    return any(
        pattern.search(value)
        for value in _folded_string_constants(text)
        for pattern in DEVICE_TRANSPORT_PATTERNS
    )


def _device_acquisition_sources(
    root: Path, overrides: Mapping[str, str]
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
        # Cheap transport substring first: the AST parse is the expensive half
        # and only device-facing sources can ever reach the boundary rule.
        if not _touches_device_transport(text):
            continue
        if not _uses_legacy_acquisition(text):
            continue
        if name in ACTIVE_FILES:
            if RAW_MODULE not in text:
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
    root: Path, overrides: Mapping[str, str]
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
        if not _uses_legacy_acquisition(text):
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
    function_sha256 = _audit_function_contracts(root, overrides)
    d0_candidates = _candidate_d0_sources(root, overrides)
    legacy_observers, legacy_sha256 = _legacy_unmigrated_observers(
        root, overrides
    )
    device_sources, device_sources_sha256 = _device_acquisition_sources(
        root, overrides
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
        name for name, text in all_sources.items() if _imports_subprocess(text)
    )
    observer_named_modules = sorted(
        name
        for name, text in all_sources.items()
        if (
            ("observer" in name or "_d0" in name)
            and _imports_subprocess(text)
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
        if args.output is not None:
            write_receipt(args.output, payload)
    except (OSError, RawFirstAuditError) as exc:
        print(f"S22+ raw-first observer audit error: {exc}")
        return 2
    print(payload.decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
