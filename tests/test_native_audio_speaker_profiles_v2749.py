"""Tests for the V2749 reusable audio speaker profile API."""

from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
from pathlib import Path

from _loader import load_revalidation

profiles = load_revalidation("native_audio_speaker_profiles_v2749")
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


def fake_deploy(root: Path) -> Path:
    remote_dir = "/cache/a90-test-v2749"
    files = [fake_file(root / "helper", b"helper", f"{remote_dir}/helper", "helper")]
    argv = [f"{remote_dir}/helper", "--execute"]
    for index, cal_type in enumerate([39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]):
        arg = f"{remote_dir}/{index:02d}-arg-cal{cal_type}.bin"
        files.append(fake_file(root / f"arg{index}", bytes([index + 1]) * 40, arg, "set_arg"))
        argv.extend(["--exact-set", arg])
    argv.extend(["--hold-sec", "10"])
    path = root / "deploy.json"
    write_json(path, {
        "ok": True,
        "all_inputs_ok": True,
        "remote_dir": remote_dir,
        "remote_argv": argv,
        "files": files,
    })
    return path


class NativeAudioSpeakerProfilesV2749(unittest.TestCase):
    def test_internal_speaker_profile_pins_v2748_success_contract(self) -> None:
        profile = profiles.get_profile("internal-speaker-safe")

        self.assertEqual(profile.endpoint, "internal-speaker")
        self.assertEqual(profile.card, 0)
        self.assertEqual(profile.pcm_device, 0)
        self.assertEqual(profile.app_type.app_type, 69941)
        self.assertEqual(profile.app_type.acdb_id, 15)
        self.assertEqual(profile.global_app_type_values(), ("1", "69941", "48000", "16"))
        self.assertEqual(profile.global_app_type_entry(), "69941:48000:16")
        self.assertEqual(profile.stream_app_type_values(), ("69941", "15", "48000", "2"))
        self.assertEqual(profile.acdb_set_order, (39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21))
        self.assertEqual(profile.forbidden_stale_cal_types, (10, 14, 24))

    def test_profile_limits_separate_probe_and_listen_modes(self) -> None:
        profile = profiles.get_profile()

        self.assertEqual(profile.probe_limits.default_amplitude, 0.02)
        self.assertEqual(profile.probe_limits.default_duration_ms, 1000)
        self.assertEqual(profile.listen_limits.default_amplitude, 0.15)
        self.assertEqual(profile.listen_limits.default_duration_ms, 8000)
        profile.validate_playback(mode="listen", amplitude=0.15, duration_ms=8000)
        profile.validate_playback(mode="probe", amplitude=0.02, duration_ms=1000)
        with self.assertRaises(ValueError):
            profile.validate_playback(mode="listen", amplitude=0.0, duration_ms=8000)
        with self.assertRaises(ValueError):
            profile.validate_playback(mode="listen", amplitude=0.21, duration_ms=8000)
        with self.assertRaises(ValueError):
            profile.validate_playback(mode="listen", amplitude=0.15, duration_ms=10001)

    def test_manifest_is_public_metadata_only(self) -> None:
        manifest = profiles.profile_manifest()
        text = repr(manifest)

        self.assertEqual(manifest["profile_id"], "internal-speaker-safe")
        self.assertEqual(manifest["global_app_type_values"], ["1", "69941", "48000", "16"])
        self.assertIn("q6asm", manifest["dmesg_focus_pattern"])
        self.assertIn("Get RMS", manifest["output_observer_controls"])
        self.assertNotIn("local_path_private", text)
        self.assertNotIn("workspace/private", text)

    def test_v2639_dry_run_exports_selected_profile(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2749-"))
        args = v2639.parse_args(["--dry-run", "--v2636-manifest", str(fake_deploy(root))])
        state = v2639.dry_run_payload(args)
        api = state["v2749_audio_speaker_profile"]

        self.assertEqual(args.audio_profile, "internal-speaker-safe")
        self.assertEqual(api["profile_id"], "internal-speaker-safe")
        self.assertEqual(state["v2730_global_app_type_config"]["profile_id"], "internal-speaker-safe")
        self.assertEqual(state["v2730_global_app_type_config"]["values"], ["1", "69941", "48000", "16"])
        self.assertEqual(state["v2741_output_observer"]["profile_id"], "internal-speaker-safe")

    def test_unknown_profile_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            profiles.get_profile("missing")


if __name__ == "__main__":
    unittest.main()
