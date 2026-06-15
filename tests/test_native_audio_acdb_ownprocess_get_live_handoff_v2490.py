"""Host-only tests for the V2490 own-process ACDB GET live runner."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2490 = load_revalidation("native_audio_acdb_ownprocess_get_live_handoff_v2490")
v_helper = load_revalidation("build_android_acdb_ownprocess_get_exec_linked_v2512")
v_ioctltrace = load_revalidation("build_android_ioctl_trace_preload_v2531")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2490-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "build_helper": False,
        "build_ioctl_trace": False,
        "disable_ioctl_trace": False,
        "fake_audio_cal_allocate": False,
        "out_dir": root / "run",
        "adb": "adb",
        "serial": None,
        "from_native": False,
        "android_timeout": 240.0,
        "flash_timeout": 420.0,
        "adb_command_timeout": 90.0,
        "adb_pull_timeout": 120.0,
        "helper_timeout": 60.0,
        "android_root_recheck_attempts": 4,
        "android_root_recheck_sleep_sec": 2.0,
        "android_settle_adb_retry_attempts": v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
        "android_settle_adb_retry_sleep_sec": v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
        "helper_path": None,
        "helper_sha256": None,
        "helper_build_root": v_helper.DEFAULT_BUILD_ROOT,
        "helper_manifest_path": v_helper.DEFAULT_MANIFEST,
        "ioctl_trace_so": None,
        "ioctl_trace_sha256": None,
        "ioctl_trace_build_root": v_ioctltrace.DEFAULT_BUILD_ROOT,
        "ioctl_trace_manifest_path": v_ioctltrace.DEFAULT_MANIFEST,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def fake_helper_args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2490-helper-"))
    helper = root / "v2529-acdb-ownprocess-softfail-get-host-only" / "bin" / v_helper.ARTIFACT_NAME
    helper.parent.mkdir(parents=True)
    helper.write_bytes(b"fake-arm32-helper-for-dry-run")
    digest = hashlib.sha256(helper.read_bytes()).hexdigest()
    trace = root / "v2531-acdb-ioctl-trace-preload-host-only" / "bin" / v_ioctltrace.ARTIFACT_NAME
    trace.parent.mkdir(parents=True)
    trace.write_bytes(b"fake-arm32-ioctl-trace-preload-for-dry-run")
    trace_digest = hashlib.sha256(trace.read_bytes()).hexdigest()
    defaults = {
        "helper_path": helper,
        "helper_sha256": digest,
        "ioctl_trace_so": trace,
        "ioctl_trace_sha256": trace_digest,
    }
    defaults.update(overrides)
    return args(**defaults)


class NativeAudioAcdbOwnprocessGetV2490(unittest.TestCase):
    def test_adb_su_quotes_multiline_script_as_single_remote_command(self) -> None:
        command = v2490.adb_su(args(), "set +e\necho 'quoted value'\nid -Z")

        self.assertEqual(command[:2], ["adb", "shell"])
        self.assertEqual(len(command), 3)
        self.assertTrue(command[2].startswith("su -c "), command)
        self.assertIn("quoted value", command[2])
        self.assertNotEqual(command[2], "su -c set +e")

    def test_dry_run_is_ownprocess_only_and_live_ready_when_artifact_exists(self) -> None:
        payload = v2490.dry_run_payload(fake_helper_args())

        self.assertEqual(payload["decision"], "v2490-acdb-ownprocess-get-live-runner-dry-run")
        self.assertTrue(payload["live_ready"], payload.get("live_blockers"))
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertTrue(payload["helper"]["ok"], payload["helper"])
        self.assertTrue(payload["ioctl_trace_preload"]["ok"], payload["ioctl_trace_preload"])
        self.assertTrue(payload["ioctl_trace_preload"]["enabled"], payload["ioctl_trace_preload"])
        self.assertIn("v2529-acdb-ownprocess-softfail-get-host-only", payload["helper"].get("path", ""))
        self.assertIn("v2531-acdb-ioctl-trace-preload-host-only", payload["ioctl_trace_preload"].get("path", ""))
        self.assertTrue(payload["android_settle_adb_retry"]["enabled"])
        self.assertEqual(payload["android_settle_adb_retry"]["attempts"], v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS)
        self.assertIn("error: closed", payload["android_settle_adb_retry"]["retry_markers"])
        self.assertIn("ownget-setup", payload["android_settle_adb_retry"]["early_staging_scope"])
        self.assertFalse(payload["android_settle_adb_retry"]["helper_execution_retry"])
        self.assertTrue(payload["acdb_dependencies"]["ok"], payload["acdb_dependencies"])
        dep_names = [item["name"] for item in payload["acdb_dependencies"]["libs"]]
        self.assertIn("libaudcal.so", dep_names)
        self.assertIn("libacdbloader.so", dep_names)
        if payload["acdb_dependencies"].get("source_kind") == "v2506-vendor-ext4-closure":
            self.assertIn("libdiag.so", dep_names)
            self.assertIn("libacdb-fts.so", dep_names)
            self.assertIn("libacdbrtac.so", dep_names)
            self.assertIn("libadiertac.so", dep_names)
            self.assertIn("libtinyalsa.so", payload["acdb_dependencies"]["runtime_external_libs"])
        self.assertIn("own-process helper only", "\n".join(payload["hard_boundary"]))
        flat_commands = json.dumps(payload["commands"], sort_keys=True)
        self.assertIn("/data/local/tmp/a90-acdb-ownget/libaudcal.so", flat_commands)
        self.assertIn("LD_LIBRARY_PATH=/data/local/tmp/a90-acdb-ownget:", flat_commands)
        self.assertIn("LD_PRELOAD=/data/local/tmp/a90-acdb-ownget/liba90_ioctl_trace_v2531.so", flat_commands)
        self.assertIn("/data/local/tmp/a90-acdb-ownget/liba90_ioctl_trace_v2531.so", flat_commands)
        self.assertIn("/vendor/etc/acdbdata", flat_commands)
        self.assertIn("/vendor/etc/audconf/OPEN", flat_commands)
        self.assertIn("find /vendor/etc/audconf", flat_commands)
        self.assertIn("-exec ls -l", flat_commands)
        self.assertIn("chown shell:shell /data/local/tmp/a90-acdb-ownget", flat_commands)
        self.assertIn("find . -maxdepth 1 -type f -exec chmod 644", flat_commands)
        self.assertIn("logcat -c", flat_commands)
        self.assertIn("logcat-acdb-loader.txt", flat_commands)
        self.assertIn("logcat-avc-acdb-filter.txt", flat_commands)
        self.assertIn("dmesg-avc-acdb-filter.txt", flat_commands)
        self.assertIn("ownget-exec-context.txt", flat_commands)
        self.assertIn("ownget-run-context.txt", flat_commands)
        self.assertIn("id -Z", flat_commands)
        self.assertIn("ls -lZ /dev/msm_audio_cal", flat_commands)
        self.assertIn("persist.vendor.audio.calfile0", flat_commands)
        if payload["acdb_dependencies"].get("source_kind") == "v2506-vendor-ext4-closure":
            self.assertIn("/data/local/tmp/a90-acdb-ownget/libdiag.so", flat_commands)
        self.assertNotIn("magisk --install-module", flat_commands)
        self.assertNotIn("android.hardware.audio.service", flat_commands)
        self.assertNotIn("AudioTrack", flat_commands)
        self.assertNotIn("0xc00461cb", flat_commands.lower())


    def test_dry_run_fake_allocate_sets_explicit_env_only(self) -> None:
        payload = v2490.dry_run_payload(fake_helper_args(fake_audio_cal_allocate=True))

        self.assertTrue(payload["live_ready"], payload.get("live_blockers"))
        self.assertTrue(payload["ioctl_trace_policy"]["fake_audio_cal_allocate"])
        self.assertEqual(payload["ioctl_trace_policy"]["fake_mode_env"], "A90_ACDB_FAKE_ALLOCATE=1")
        flat_commands = json.dumps(payload["commands"], sort_keys=True)
        self.assertIn("A90_ACDB_FAKE_ALLOCATE=1", flat_commands)
        self.assertIn("LD_PRELOAD=/data/local/tmp/a90-acdb-ownget/liba90_ioctl_trace_v2531.so", flat_commands)
        self.assertIn("AUDIO_ALLOCATE/DEALLOCATE/SET", "\n".join(payload["hard_boundary"]))
        self.assertNotIn("0xc00461cb", flat_commands.lower())

    def test_step_has_transient_settle_adb_failure_for_error_closed(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-step-"))
        stderr = root / "step.stderr.txt"
        stderr.write_text("error: closed\n")
        step = {"ok": False, "stdout": str(root / "missing.stdout.txt"), "stderr": str(stderr)}

        self.assertTrue(v2490.step_has_transient_settle_adb_failure(step))

    def test_step_has_transient_settle_adb_failure_ignores_semantic_boot_failure(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-step-"))
        stdout = root / "step.stdout.txt"
        stdout.write_text("boot-complete recheck failed: sys= dev=\n")
        step = {"ok": False, "stdout": str(stdout), "stderr": str(root / "missing.stderr.txt")}

        self.assertFalse(v2490.step_has_transient_settle_adb_failure(step))

    def test_early_staging_retry_recovers_after_transport_closed(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="a90-v2490-staging-retry-"))
        steps: list[dict[str, object]] = []
        calls: list[str] = []
        original_run_step = v2490.route.run_step
        original_settle = v2490.v2396.android_post_handoff_settle_commands

        def fake_run_step(name: str, command: list[str], out_dir_arg: Path, timeout_sec: float, check: bool = True) -> dict[str, object]:
            calls.append(name)
            stdout = out_dir / f"{name}.stdout.txt"
            stderr = out_dir / f"{name}.stderr.txt"
            if name == "ownget-setup":
                stdout.write_text("")
                stderr.write_text("error: closed\n")
                return {"name": name, "ok": False, "rc": 1, "stdout": str(stdout), "stderr": str(stderr)}
            stdout.write_text("ok\n")
            stderr.write_text("")
            return {"name": name, "ok": True, "rc": 0, "stdout": str(stdout), "stderr": str(stderr)}

        try:
            v2490.route.run_step = fake_run_step
            v2490.v2396.android_post_handoff_settle_commands = lambda _args: [
                ["adb", "wait-for-device"],
                ["adb", "shell", "boot-complete-check"],
                ["adb", "shell", "su", "-c", "id"],
            ]

            record = v2490.run_early_staging_command_with_transport_retry(
                args(android_settle_adb_retry_attempts=2, android_settle_adb_retry_sleep_sec=0.0),
                name="ownget-setup",
                command=["adb", "shell", "setup"],
                out_dir=out_dir,
                steps=steps,  # type: ignore[arg-type]
                timeout_sec=1.0,
            )
        finally:
            v2490.route.run_step = original_run_step
            v2490.v2396.android_post_handoff_settle_commands = original_settle

        self.assertTrue(record["ok"])
        self.assertTrue(record["early_staging_retry_recovered"])
        self.assertIn("ownget-setup", calls)
        self.assertIn("ownget-setup-retry-2-resettle-wait-for-device", calls)
        self.assertIn("ownget-setup-retry-2-resettle-boot-complete", calls)
        self.assertIn("ownget-setup-retry-2-resettle-root-id", calls)
        self.assertIn("ownget-setup-retry-2", calls)

    def test_early_staging_retry_fails_closed_for_semantic_error(self) -> None:
        out_dir = Path(tempfile.mkdtemp(prefix="a90-v2490-staging-retry-"))
        steps: list[dict[str, object]] = []
        calls: list[str] = []
        original_run_step = v2490.route.run_step

        def fake_run_step(name: str, command: list[str], out_dir_arg: Path, timeout_sec: float, check: bool = True) -> dict[str, object]:
            calls.append(name)
            stdout = out_dir / f"{name}.stdout.txt"
            stderr = out_dir / f"{name}.stderr.txt"
            stdout.write_text("")
            stderr.write_text("permission denied\n")
            return {"name": name, "ok": False, "rc": 1, "stdout": str(stdout), "stderr": str(stderr)}

        try:
            v2490.route.run_step = fake_run_step
            with self.assertRaisesRegex(RuntimeError, "ownget-setup failed"):
                v2490.run_early_staging_command_with_transport_retry(
                    args(android_settle_adb_retry_attempts=3, android_settle_adb_retry_sleep_sec=0.0),
                    name="ownget-setup",
                    command=["adb", "shell", "setup"],
                    out_dir=out_dir,
                    steps=steps,  # type: ignore[arg-type]
                    timeout_sec=1.0,
                )
        finally:
            v2490.route.run_step = original_run_step

        self.assertEqual(calls, ["ownget-setup"])

    def test_command_safety_rejects_inhal_and_native_calibration_paths(self) -> None:
        payload = {
            "commands": {
                "bad": [
                    "adb",
                    "shell",
                    "su",
                    "-c",
                    "magisk --install-module x; restart android.hardware.audio.service; echo /dev/msm_audio_cal 0xc00461cb; tinyplay x",
                ]
            }
        }
        safety = v2490.command_safety(payload)

        self.assertFalse(safety["ok"])
        names = {item["name"] for item in safety["findings"]}
        self.assertIn("magisk_install", names)
        self.assertIn("hal_restart", names)
        self.assertIn("native_msm_audio_cal_set_combo", names)
        self.assertIn("native_cal_set_constant", names)
        self.assertIn("tinyplay", names)

    def test_parse_ownget_artifacts_classifies_4916_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        event = root / "acdb-ownget-events.jsonl"
        raw = root / "acdb-ownget-00000001-000130da-in0-out4916.bin"
        raw.write_bytes(b"x" * 4916)
        event.write_text(json.dumps({
            "event": "acdb_ioctl",
            "seq": 1,
            "cmd": "0x000130da",
            "in_len": 0,
            "out_len": 4916,
            "ret": 0,
            "is_target_4916": True,
            "sha256": "0" * 64,
            "raw_path": f"/data/local/tmp/a90-acdb-ownget/{raw.name}",
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "acdb-get-success-4916")
        self.assertTrue(summary["full_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])

    def test_parse_ownget_artifacts_rejects_failed_zero_4916_buffers(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        event = root / "acdb-ownget-events.jsonl"
        raw = root / "acdb-ownget-00000002-000130da-in0-out4916.bin"
        raw.write_bytes(b"\0" * 4916)
        event.write_text(json.dumps({
            "event": "acdb_ioctl",
            "seq": 2,
            "cmd": "0x000130da",
            "in_len": 0,
            "out_len": 4916,
            "ret": -2,
            "is_target_4916": True,
            "sha256": hashlib.sha256(b"\0" * 4916).hexdigest(),
            "raw_path": f"/data/local/tmp/a90-acdb-ownget/{raw.name}",
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "acdb-get-dispatch-ret-failed-zero-outbuf")
        self.assertFalse(summary["full_success"])
        self.assertFalse(summary["partial_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["counts_toward_fails_twice"])
        self.assertEqual(summary["target_4916_count"], 1)
        self.assertEqual(summary["diagnostics"]["target_4916_success_count"], 0)
        self.assertEqual(summary["diagnostics"]["successful_row_count"], 0)
        self.assertEqual(summary["diagnostics"]["zero_outbuf_count"], 1)
        self.assertEqual(summary["diagnostics"]["zero_hash_by_len"]["4916"], hashlib.sha256(b"\0" * 4916).hexdigest())

    def test_parse_ownget_artifacts_extracts_allocate_ioctl_errno(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "ioctl-trace-events.jsonl").write_text(json.dumps({
            "event": "ioctl_trace",
            "pid": 123,
            "tid": 123,
            "fd": 7,
            "request": "0xc00461c8",
            "name": "AUDIO_ALLOCATE_CALIBRATION",
            "arg": "0xbeef0000",
            "ret": 0,
            "errno": 0,
            "intercept": "fake-success",
            "arg_snapshot": {
                "available": True,
                "requested_size": 32,
                "sample_len": 32,
                "cal_type": 39,
                "cal_type_size": 16,
                "cal_size": 4916,
                "mem_handle": 45,
            },
        }) + "\n")
        (root / "ownget-run-context.txt").write_text("uid=0(root)\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["diagnostics"]["ioctl_trace_event_count"], 1)
        self.assertEqual(summary["diagnostics"]["audio_allocate_ioctl_count"], 1)
        self.assertEqual(summary["diagnostics"]["audio_allocate_ioctl_ret_values"], [0])
        self.assertEqual(summary["diagnostics"]["audio_allocate_ioctl_errno_values"], [0])
        self.assertEqual(summary["diagnostics"]["audio_allocate_ioctl_intercepts"], ["fake-success"])
        self.assertEqual(summary["diagnostics"]["audio_allocate_ioctl_fake_success_count"], 1)
        self.assertEqual(summary["diagnostics"]["audio_allocate_arg_snapshots"][0]["cal_size"], 4916)
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_count"], 0)


    def test_parse_ownget_artifacts_flags_real_audio_set_passthrough(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "ioctl-trace-events.jsonl").write_text(json.dumps({
            "event": "ioctl_trace",
            "pid": 123,
            "tid": 123,
            "fd": 7,
            "request": "0xc00461cb",
            "name": "AUDIO_SET_CALIBRATION",
            "arg": "0xbeef1000",
            "ret": 0,
            "errno": 0,
            "intercept": "pass-through",
            "arg_snapshot": {
                "available": True,
                "data_size": 32,
                "cal_type": 39,
                "cal_size": 4916,
                "mem_handle": 30,
            },
        }) + "\n")
        (root / "ownget-run-context.txt").write_text("uid=0(root)\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "ownprocess-real-audio-set-passthrough")
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_count"], 1)
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_intercepts"], ["pass-through"])
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_fake_success_count"], 0)
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_pass_through_count"], 1)

    def test_parse_ownget_artifacts_allows_fake_audio_set_intercept(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "ioctl-trace-events.jsonl").write_text(json.dumps({
            "event": "ioctl_trace",
            "pid": 123,
            "tid": 123,
            "fd": 7,
            "request": "0xc00461cb",
            "name": "AUDIO_SET_CALIBRATION",
            "arg": "0xbeef1000",
            "ret": 0,
            "errno": 0,
            "intercept": "fake-success",
        }) + "\n")
        (root / "ownget-run-context.txt").write_text("uid=0(root)\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "ownprocess-context-only-no-events")
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_count"], 1)
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_fake_success_count"], 1)
        self.assertEqual(summary["diagnostics"]["audio_set_ioctl_pass_through_count"], 0)

    def test_parse_ownget_artifacts_preserves_no_4916_partial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        event = root / "acdb-ownget-events.jsonl"
        raw = root / "acdb-ownget-00000001-00011394-in0-out4.bin"
        raw.write_bytes(b"\x34\x13\x00\x00")
        event.write_text(json.dumps({
            "event": "acdb_ioctl",
            "seq": 1,
            "cmd": "0x00011394",
            "in_len": 0,
            "out_len": 4,
            "ret": 0,
            "is_target_4916": False,
            "sha256": "1" * 64,
            "raw_path": f"/data/local/tmp/a90-acdb-ownget/{raw.name}",
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "acdb-get-full-outbuf-set-no-4916")
        self.assertTrue(summary["partial_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])

    def test_parse_ownget_artifacts_maps_namespace_api_error_bucket(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "symbol_probe",
            "scope": "libdl",
            "symbol": "__loader_android_dlopen_ext",
            "found": False,
        }) + "\n" + json.dumps({
            "event": "error",
            "stage": "dlsym-android_dlopen_ext",
            "code": -3,
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "namespace-api-symbol-missing")
        self.assertEqual(summary["symbol_event_count"], 1)
        self.assertEqual(summary["symbol_events"][0]["symbol"], "__loader_android_dlopen_ext")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["counts_toward_fails_twice"])

    def test_parse_ownget_artifacts_classifies_dlopen_error(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "dlopen-libaudcal",
            "code": -1,
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "ownprocess-error-dlopen-libaudcal")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["counts_toward_fails_twice"])

    def test_parse_ownget_artifacts_classifies_init_v3_acdb_load_log(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "acdb_loader_init_v3",
            "code": -19,
        }) + "\n")
        (root / "logcat-acdb-loader.txt").write_text("ACDB-LOADER: ACDB -> Could not load .acdb files!\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "init-v3-block-acdb-files-load")
        self.assertTrue(summary["diagnostics"]["has_acdb_files_load_error"])

    def test_parse_ownget_artifacts_classifies_init_v3_acph_log(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "acdb_loader_init_v3",
            "code": -19,
        }) + "\n")
        (root / "logcat-acdb-loader.txt").write_text("ACDB-LOADER: Error initializing ACPH returned = -19\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "init-v3-block-acph-init")
        self.assertTrue(summary["diagnostics"]["has_acph_init_error"])

    def test_parse_ownget_artifacts_classifies_allocate_calibration_failure(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "acdb_loader_init_v3",
            "code": -12,
        }) + "\n")
        (root / "logcat-acdb-loader.txt").write_text(
            "ACDB-LOADER: ACDB -> ACPH INIT\n"
            "ACDB-LOADER: ACDB -> RTAC INIT\n"
            "ACDB-LOADER: ACDB -> MCS, FTS INIT\n"
            "ACDB-LOADER: ACDB -> ADIE RTAC INIT\n"
            "ACDB-LOADER: ACDB -> Error: Sending AUDIO_ALLOCATE_CALIBRATION, result = -1\n"
            "ACDB-LOADER: ACDB -> allocate_cal_block failed!\n"
            "ACDB-LOADER: ACDB -> Cannot allocate memory!\n"
        )
        (root / "ownget-run-context.txt").write_text(
            "uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0\n"
            "u:r:magisk:s0\n"
            "vendor_audio_prop:s0 readable metadata line without denial\n"
        )
        (root / "dmesg-avc-acdb-filter.txt").write_text("audit: avc: denied { kill } unrelated\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "init-v3-block-audio-allocate-calibration-failed")
        self.assertTrue(summary["diagnostics"]["has_audio_allocate_calibration_failed"])
        self.assertFalse(summary["diagnostics"]["has_vendor_audio_prop_denied"])


    def test_parse_ownget_artifacts_classifies_helper_sigsegv_without_events(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "ownget.rc").write_text("139\n")
        (root / "ownget.stderr.txt").write_text("Segmentation fault \n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "ownprocess-helper-sigsegv-no-events")
        self.assertEqual(summary["diagnostics"]["helper_rc"], 139)
        self.assertTrue(summary["diagnostics"]["helper_sigsegv"])
        self.assertIn("Segmentation fault", summary["diagnostics"]["helper_stderr_tail"])

    def test_parse_ownget_artifacts_classifies_init_v3_avc_denial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "acdb_loader_init_v3",
            "code": -19,
        }) + "\n")
        (root / "logcat-avc-acdb-filter.txt").write_text("avc: denied { read } for path=/vendor/etc/audconf/OPEN/Speaker_cal.acdb\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "init-v3-block-avc-denial")
        self.assertTrue(summary["diagnostics"]["has_avc_or_denial"])

    def test_parse_ownget_artifacts_classifies_msm_audio_cal_denial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "acdb_loader_init_v3",
            "code": -19,
        }) + "\n")
        (root / "logcat-acdb-loader.txt").write_text(
            "ACDB-LOADER: ACDB -> Cannot open /dev/msm_audio_cal errno: 13\n"
        )
        (root / "ownget-run-context.txt").write_text(
            "uid=2000(shell) gid=2000(shell) groups=2000(shell)\n"
            "u:r:shell:s0\n"
        )

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "init-v3-block-msm-audio-cal-open-denied")
        self.assertTrue(summary["diagnostics"]["has_msm_audio_cal_open_denied"])
        self.assertTrue(summary["diagnostics"]["has_shell_domain_context"])

    def test_parse_ownget_artifacts_classifies_vendor_audio_prop_denial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "acdb_loader_init_v3",
            "code": -19,
        }) + "\n")
        (root / "logcat-avc-acdb-filter.txt").write_text(
            'libc: Access denied finding property "persist.vendor.audio.calfile0"\n'
            'audit: avc: denied { read } name="u:object_r:vendor_audio_prop:s0"\n'
        )

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "init-v3-block-vendor-audio-prop-denied")
        self.assertTrue(summary["diagnostics"]["has_vendor_audio_prop_denied"])

    def test_parse_ownget_artifacts_does_not_infer_vendor_prop_from_unrelated_denial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "acdb_loader_init_v3",
            "code": -19,
        }) + "\n")
        (root / "ownget-exec-context.txt").write_text(
            "-r--r--r-- root root u:object_r:vendor_audio_prop:s0 "
            "/dev/__properties__/u:object_r:vendor_audio_prop:s0\n"
        )
        (root / "dmesg-avc-acdb-filter.txt").write_text("audit: avc: denied { kill } unrelated\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "init-v3-block-avc-denial")
        self.assertFalse(summary["diagnostics"]["has_vendor_audio_prop_denied"])

    def test_parse_ownget_artifacts_keeps_context_only_timeout_evidence(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "ownget-exec-context.txt").write_text("uid=0(root) context=u:r:magisk:s0\n")
        (root / "ownget-run-context.txt").write_text("uid=0(root) context=u:r:magisk:s0\n")
        (root / "logcat-avc-acdb-filter.txt").write_text("")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "ownprocess-context-only-no-events")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["counts_toward_fails_twice"])
        self.assertEqual(summary["diagnostics"]["exec_context_line_count"], 1)
        self.assertEqual(summary["diagnostics"]["run_context_line_count"], 1)

    def test_timeout_step_record_points_to_step_outputs(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-timeout-"))
        command = ["adb", "shell", "su -c true"]

        record = v2490.timeout_step_record("ownget-run-helper", command, root, 60.0, RuntimeError("timed out"))

        self.assertEqual(record["name"], "ownget-run-helper")
        self.assertTrue(record["timeout"])
        self.assertFalse(record["ok"])
        self.assertEqual(record["command"], command)
        self.assertIn("ownget-run-helper.stdout.txt", record["stdout"])
        self.assertIn("timed out", record["error"])

    def test_select_pulled_artifact_dir_accepts_flat_adb_pull_layout(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-pull-"))
        (root / "acdb-ownget-events.jsonl").write_text("{}\n")

        self.assertEqual(v2490.select_pulled_artifact_dir(root), root)

    def test_select_pulled_artifact_dir_accepts_nested_adb_pull_layout(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-pull-"))
        nested = root / "a90-acdb-ownget"
        nested.mkdir()
        (nested / "acdb-ownget-events.jsonl").write_text("{}\n")

        self.assertEqual(v2490.select_pulled_artifact_dir(root), nested)

    def test_cli_dry_run_outputs_json(self) -> None:
        import subprocess
        import sys

        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py",
                "--dry-run",
            ],
            cwd=v2490.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2490-acdb-ownprocess-get-live-runner-dry-run")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
