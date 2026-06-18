"""Tests for V2639 ACDB SET-cal replay live handoff."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2639 = load_revalidation("native_audio_acdb_setcal_replay_live_handoff_v2639")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fake_file(path: Path, data: bytes, remote: str, kind: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "kind": kind,
        "local": {
            "local_path_private": str(path),
            "exists": True,
            "ok": True,
            "nonzero": True,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "sha256_matches": True,
            "size_matches": True,
        },
        "remote_path": remote,
        "ok": True,
    }


def fake_deploy(root: Path, *, gate2: bool = False) -> Path:
    remote_dir = "/cache/a90-test-v2639"
    files = [fake_file(root / "helper", b"helper", f"{remote_dir}/helper", "helper")]
    files.append(fake_file(root / "topology", b"T" * 4916, f"{remote_dir}/00-core.bin", "topology"))
    argv = [f"{remote_dir}/helper", "--execute", "--basic-payload", f"39:0:{remote_dir}/00-core.bin"]
    for index, cal_type in enumerate([13, 9, 11, 12, 15, 23, 16, 21], start=1):
        arg = f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin"
        files.append(fake_file(root / f"arg{index}", bytes([index]) * 40, arg, "set_arg"))
        if cal_type in {11, 15, 16}:
            payload = f"{remote_dir}/{index:02d}-payload-cal{cal_type}.bin"
            files.append(fake_file(root / f"payload{index}", bytes([cal_type]) * 12, payload, "payload"))
            arg = f"{arg}:{payload}"
        argv.extend(["--exact-set", arg])
    argv.extend(["--hold-sec", "10"])
    path = root / "deploy.json"
    write_json(path, {
        "ok": True,
        "all_inputs_ok": True,
        "operator_gate2_accepted": gate2,
        "remote_dir": remote_dir,
        "remote_argv": argv,
        "files": files,
    })
    return path


class NativeAudioAcdbSetcalReplayLiveHandoffV2639(unittest.TestCase):
    def test_dry_run_uses_v2638_contract_and_self_authorizes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)

        self.assertTrue(state["live_runner_implemented"])
        self.assertTrue(state["execution_contract_ok"])
        self.assertTrue(state["safe_to_run_native_replay"])
        self.assertEqual(state["replay_gate_blockers"], [])
        self.assertEqual(state["remote"]["final_set_index"], 8)

    def test_dry_run_defaults_to_v2730_global_app_type_config(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)
        gate = state["v2730_global_app_type_config"]

        self.assertTrue(gate["enabled"])
        self.assertEqual(gate["control"], "App Type Config")
        self.assertEqual(gate["values"], ["1", "69941", "48000", "16"])
        self.assertEqual(gate["writer"], "atomic-alsa-elem-write")
        self.assertEqual(gate["entry"], "69941:48000:16")
        self.assertIn("a90_alsa_app_type_config_writer_v2733", " ".join(gate["argv"]))
        self.assertTrue(state["v2733_atomic_app_type_writer"]["enabled"])
        self.assertIn("q6core", state["v2730_dmesg_focus_pattern"])
        self.assertIn("bit_width", state["v2730_dmesg_focus_pattern"])
        self.assertTrue(any("global App Type Config" in step for step in state["future_live_sequence"]))

    def test_global_app_type_config_compat_tinymix_path_is_explicit(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args([
            "--dry-run",
            "--v2636-manifest",
            str(fake_deploy(root)),
            "--no-use-atomic-app-type-writer",
        ])
        gate = v2639.global_app_type_plan(args)

        self.assertEqual(gate["name"], "v2730-global-app-type-config")
        self.assertEqual(gate["writer"], "tinymix-per-index-compat")
        self.assertEqual(gate["argv"][-4:], ["1", "69941", "48000", "16"])

    def test_verify_live_gate_accepts_legacy_approval_flags_as_noops(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        manifest = fake_deploy(root, gate2=False)
        args = v2639.parse_args([
            "--run-live",
            "--v2636-manifest",
            str(manifest),
        ])
        deploy = v2639.load_deploy_manifest(manifest)
        state = v2639.dry_run_payload(args)

        v2639.verify_live_gate(args, deploy)
        self.assertTrue(state["safe_to_run_native_replay"])

    def test_runtime_scripts_are_materialized_as_files(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        manifest = fake_deploy(root, gate2=False)
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(manifest)])
        state = v2639.dry_run_payload(args)
        deploy = v2639.load_deploy_manifest(manifest)

        scripts = v2639.runtime_script_files(root, state, deploy)

        self.assertEqual(
            [item[0] for item in scripts],
            ["start_and_wait_all_set", "listen_window", "pcm_output_observer", "deallocate_check", "runtime_cleanup"],
        )
        start_key, start_remote, start_local = scripts[0]
        self.assertEqual(start_key, "start_and_wait_all_set")
        self.assertTrue(start_remote.startswith("/cache/a90-runtime/bin/"))
        self.assertTrue(start_remote.endswith("/setcal-start-and-wait-all-set.sh"))
        self.assertIn("sha256sum -c -", start_local.read_text(encoding="utf-8"))
        self.assertIn("A90_SETCAL_REPLAY_ALL_SET_OK", start_local.read_text(encoding="utf-8"))
        listen_key, listen_remote, listen_local = scripts[1]
        self.assertEqual(listen_key, "listen_window")
        self.assertTrue(listen_remote.endswith("/a90_pcm_listen_window_v2743.sh"))
        listen_text = listen_local.read_text(encoding="utf-8")
        self.assertIn("A90_LISTEN_WINDOW_READY", listen_text)
        self.assertIn("A90_LISTEN_WINDOW_BEGIN", listen_text)
        self.assertIn("A90_LISTEN_WINDOW_END", listen_text)
        self.assertIn("a90_pcm_write_probe_v2386", listen_text)
        observer_key, observer_remote, observer_local = scripts[2]
        self.assertEqual(observer_key, "pcm_output_observer")
        self.assertTrue(observer_remote.endswith("/a90_pcm_output_observer_v2741.sh"))
        observer_text = observer_local.read_text(encoding="utf-8")
        self.assertIn("A90_OUTPUT_OBSERVER_BEGIN", observer_text)
        self.assertIn("mode=direct-controls", observer_text)
        self.assertIn("A90_OUTPUT_OBSERVER_CTL_BEGIN", observer_text)
        self.assertIn("SpkrLeft COMP Switch", observer_text)
        self.assertIn("Get RMS", observer_text)
        self.assertIn("A90_OUTPUT_OBSERVER_SAMPLES_BEGIN", observer_text)
        self.assertIn("a90_pcm_write_probe_v2386", observer_text)

    def test_remote_step_clean_rejects_protocol_noise_and_unknown_command(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        stdout = root / "step.txt"
        stdout.write_text("[err] unknown command: deadbeef\n", encoding="utf-8")

        self.assertFalse(v2639.remote_step_clean({"ok": True, "stdout_path": str(stdout)}))
        self.assertFalse(v2639.remote_step_clean({"ok": True, "stdout_path": str(stdout), "serial_recovery": {"reason": "protocol-noise"}}))

    def test_report_records_blockers(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)
        report = root / "report.md"
        v2639.write_report(report, state)
        text = report.read_text(encoding="utf-8")

        self.assertIn("ACDB SET-cal replay live handoff", text)
        self.assertIn("V2730 Update", text)
        self.assertIn("V2733 replaces", text)
        self.assertIn("global `App Type Config`", text)
        self.assertIn("self-authorized", text)
        self.assertNotIn("local_path_private", text)

    def test_source_captures_post_set_dmesg_before_pcm(self) -> None:
        source = Path(v2639.__file__).read_text(encoding="utf-8")

        self.assertIn("dmesg-after-setcal-replay-before-pcm", source)
        self.assertIn("dmesg-focus-after-setcal-replay-before-pcm", source)
        self.assertIn("post_set_dmesg", source)
        self.assertLess(
            source.index("dmesg-after-setcal-replay-before-pcm"),
            source.index('result["playback_attempted"] = True'),
        )

    def test_source_captures_playback_dmesg_before_route_reset(self) -> None:
        source = Path(v2639.__file__).read_text(encoding="utf-8")

        self.assertIn("dmesg-after-setcal-playback-before-reset", source)
        self.assertIn("dmesg-focus-after-setcal-playback-before-reset", source)
        self.assertIn('result["playback_dmesg"]', source)
        self.assertIn('result["playback_dmesg_focus"]', source)
        self.assertLess(
            source.index("dmesg-after-setcal-playback-before-reset"),
            source.index("route.get(\"route_reset_commands\")"),
        )
        self.assertLess(
            source.index('result["playback"] ='),
            source.index("dmesg-after-setcal-playback-before-reset"),
        )

    def test_source_captures_active_tinymix_snapshots_before_reset(self) -> None:
        source = Path(v2639.__file__).read_text(encoding="utf-8")

        self.assertIn("MIXER_OUTPUT_FOCUS_PATTERN", source)
        self.assertIn("tinymix-all-values-active-before-pcm", source)
        self.assertIn("tinymix-focus-active-before-pcm", source)
        self.assertIn("tinymix-all-values-active-after-pcm-before-reset", source)
        self.assertIn("tinymix-focus-active-after-pcm-before-reset", source)
        self.assertIn('result["active_snapshot_before_pcm"]', source)
        self.assertIn('result["active_focus_after_pcm_before_reset"]', source)
        self.assertLess(
            source.index("tinymix-all-values-active-before-pcm"),
            source.index('result["playback_attempted"] = True'),
        )
        self.assertLess(
            source.index("tinymix-all-values-active-after-pcm-before-reset"),
            source.index("route.get(\"route_reset_commands\")"),
        )

    def test_dry_run_adds_v2741_dynamic_output_observer(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)

        observer = state["v2741_output_observer"]
        self.assertTrue(observer["enabled"])
        self.assertEqual(observer["name"], "v2741-direct-output-observer")
        self.assertEqual(observer["remote_script"], v2639.REMOTE_OUTPUT_OBSERVER_SCRIPT)
        self.assertEqual(observer["sampling_mode"], "direct-control-allowlist")
        self.assertIn("Get RMS", observer["direct_controls"])
        self.assertIn("SpkrLeft COMP Switch", observer["direct_controls"])
        self.assertIn("output-side", observer["role"])
        self.assertIn("pcm_output_observer", state["remote_scripts"])
        self.assertIn("A90_OUTPUT_OBSERVER_PCM_BEGIN", state["remote_scripts"]["pcm_output_observer"])
        self.assertIn("A90_OUTPUT_OBSERVER_CTL_BEGIN", state["remote_scripts"]["pcm_output_observer"])
        self.assertIn("A90_OUTPUT_OBSERVER_THERMAL", state["remote_scripts"]["pcm_output_observer"])
        self.assertEqual(state["v2739_output_observer"], observer)

    def test_dry_run_listen_test_uses_bounded_audible_window(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        args = v2639.parse_args(["--dry-run", "--listen-test", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)

        listen = state["v2743_listening_test"]
        self.assertTrue(listen["enabled"])
        self.assertEqual(listen["name"], "v2743-human-audible-listen-window")
        self.assertEqual(listen["remote_script"], v2639.REMOTE_LISTEN_WINDOW_SCRIPT)
        self.assertEqual(listen["amplitude"], 0.15)
        self.assertEqual(listen["duration_ms"], 8000)
        self.assertEqual(listen["max_amplitude"], 0.20)
        self.assertEqual(listen["max_duration_ms"], 10000)
        self.assertEqual(listen["host_countdown_sec"], 5)
        self.assertIn("A90_LISTEN_WINDOW_BEGIN", listen["markers"])
        self.assertIn("A90_LISTEN_WINDOW_END", listen["markers"])
        self.assertIn("listen_window", state["remote_scripts"])
        self.assertIn("amplitude=0.15", state["remote_scripts"]["listen_window"])
        self.assertIn("duration_ms=8000", state["remote_scripts"]["listen_window"])

    def test_listen_test_caps_amplitude_and_duration(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))

        with self.assertRaises(ValueError):
            v2639.dry_run_payload(v2639.parse_args([
                "--dry-run",
                "--listen-test",
                "--amplitude",
                "0.21",
                "--v2636-manifest",
                str(fake_deploy(root)),
            ]))

        with self.assertRaises(ValueError):
            v2639.dry_run_payload(v2639.parse_args([
                "--dry-run",
                "--listen-test",
                "--duration-ms",
                "10001",
                "--v2636-manifest",
                str(fake_deploy(root)),
            ]))

        with self.assertRaises(ValueError):
            v2639.dry_run_payload(v2639.parse_args([
                "--dry-run",
                "--listen-test",
                "--listen-countdown-sec",
                "11",
                "--v2636-manifest",
                str(fake_deploy(root)),
            ]))

    def test_generate_acdb_pilot_wav_records_hash(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2639-"))
        wav = root / "listen.wav"

        meta = v2639.generate_acdb_pilot_wav(wav, duration_ms=8000, amplitude=0.15)

        self.assertTrue(wav.exists())
        self.assertEqual(meta["duration_ms"], 8000)
        self.assertEqual(meta["amplitude"], 0.15)
        self.assertEqual(meta["frames"], 384000)
        self.assertEqual(meta["sha256"], hashlib.sha256(wav.read_bytes()).hexdigest())
        self.assertGreater(wav.stat().st_size, 384000 * 4)

    def test_source_runs_output_observer_instead_of_plain_pcm_by_default(self) -> None:
        source = Path(v2639.__file__).read_text(encoding="utf-8")

        self.assertIn("pcm-output-observer-during-playback", source)
        self.assertIn('install["scripts"]["pcm_output_observer"]["remote_path"]', source)
        self.assertIn('result["output_observer"]', source)
        self.assertLess(
            source.index("pcm-output-observer-during-playback"),
            source.index("dmesg-after-setcal-playback-before-reset"),
        )

    def test_source_uses_hard_timeout_a90ctl_for_live_observations(self) -> None:
        source = Path(v2639.__file__).read_text(encoding="utf-8")

        self.assertIn("def run_a90ctl_hard_observation", source)
        self.assertIn("snd.a90ctl_command", source)
        self.assertIn("timeout=timeout + 10.0", source)
        self.assertIn('run_a90ctl_hard_observation(args, out_dir, steps, "candidate-status"', source)
        self.assertIn('run_a90ctl_hard_observation(args, out_dir, steps, "snd-status-after-materialize"', source)

    def test_global_app_type_config_runs_before_stream_app_type_and_route(self) -> None:
        source = Path(v2639.__file__).read_text(encoding="utf-8")

        self.assertIn("global_app_type_plan(args)", source)
        self.assertIn('route.get("app_type_command")', source)
        self.assertIn("route.get(\"route_apply_commands\")", source)
        self.assertLess(source.index("global_app_type_plan(args)"), source.index('route.get("app_type_command")'))
        self.assertLess(source.index('route.get("app_type_command")'), source.index("route.get(\"route_apply_commands\")"))


if __name__ == "__main__":
    unittest.main()
