import json
import tempfile
import unittest
from pathlib import Path

import native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705 as v2705


class NativeAudioAcdbSubsystemTopologyReplayDeployPlanV2705(unittest.TestCase):
    def make_payload(self, path: Path, seed: int, size: int) -> str:
        data = bytes(((seed + index) % 251) + 1 for index in range(size))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return v2705.sha256_file(path)

    def make_v2704_result(self, root: Path) -> Path:
        rows = []
        for seq, (cal_type, cmd, buffer_name, size) in enumerate(
            [
                (24, 0x130DA, "ind-lower-afe-custom-topology", 19),
                (10, 0x11394, "ind-lower-adm-custom-topology", 23),
                (14, 0x12E01, "ind-lower-asm-custom-topology", 29),
            ],
            start=1,
        ):
            raw_path = root / f"raw-cal{cal_type}.bin"
            digest = self.make_payload(raw_path, cal_type, size)
            rows.append(
                {
                    "seq": seq,
                    "cmd": cmd,
                    "ret": 0,
                    "out_len": size,
                    "buffer": buffer_name,
                    "sha256": digest,
                    "success": True,
                    "target_cal_type": cal_type,
                    "raw_status": {
                        "local_path": str(raw_path),
                        "len": size,
                        "sha256": digest,
                        "exists": True,
                        "size_ok": True,
                        "sha_ok": True,
                        "nonzero": True,
                    },
                }
            )
        result = {
            "success": True,
            "large_get_summary": {
                "success": True,
                "target_rows": rows,
                "captured_cal_types": [10, 14, 24],
                "missing_cal_types": [],
            },
        }
        path = root / "v2704-result.json"
        path.write_text(json.dumps(result), encoding="utf-8")
        return path

    def make_base_deploy(self, root: Path) -> Path:
        base_dir = root / "base"
        files = []

        def add_file(kind: str, name: str, *, executable: bool = False) -> dict:
            path = base_dir / name
            digest = self.make_payload(path, len(files) + 1, 11 + len(files))
            entry = {
                "kind": kind,
                "local": {
                    "local_path_private": str(path),
                    "exists": True,
                    "ok": True,
                    "size": path.stat().st_size,
                    "sha256": digest,
                    "nonzero": True,
                    "size_matches": True,
                    "sha256_matches": True,
                    "private_only": True,
                },
                "remote_path": f"/cache/a90-acdb-setcal-replay-v2636/{name}",
                "remote_mode": "0700" if executable else "0600",
                "remote_sha256_command": f"sha256sum /cache/a90-acdb-setcal-replay-v2636/{name}",
                "ok": True,
            }
            files.append(entry)
            return entry

        helper = add_file("helper", "a90_acdb_setcal_replay_execute_v2635", executable=True)
        topology = add_file("topology", "00-core_custom_topologies.bin")
        arg1 = add_file("set_arg", "01-set-arg-cal13.bin")
        arg2 = add_file("set_arg", "02-set-arg-cal11.bin")
        payload2 = add_file("payload", "02-payload-cal11.bin")
        manifest = {
            "run_id": "V2636",
            "build_tag": "v2636-audio-acdb-setcal-replay-deploy-plan",
            "ok": True,
            "all_inputs_ok": True,
            "remote_dir": "/cache/a90-acdb-setcal-replay-v2636",
            "hold_sec": 10,
            "files": files,
            "set_args": [
                {
                    "sequence": 1,
                    "cal_type": 13,
                    "role": "APP_META_HEADER",
                    "dmabuf_expected": False,
                    "arg_remote": arg1["remote_path"],
                    "payload_remote": None,
                    "ok": True,
                },
                {
                    "sequence": 2,
                    "cal_type": 11,
                    "role": "AUDPROC_COMMON_PAYLOAD",
                    "dmabuf_expected": True,
                    "arg_remote": arg2["remote_path"],
                    "payload_remote": payload2["remote_path"],
                    "ok": True,
                },
            ],
            "remote_argv": [
                helper["remote_path"],
                "--execute",
                "--basic-payload",
                f"39:0:{topology['remote_path']}",
                "--exact-set",
                arg1["remote_path"],
                "--exact-set",
                f"{arg2['remote_path']}:{payload2['remote_path']}",
                "--hold-sec",
                "10",
            ],
        }
        path = root / "deploy-plan.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_build_manifest_prepends_subsystem_topology_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = v2705.build_manifest(
                self.make_base_deploy(root),
                self.make_v2704_result(root),
                root / "stable",
                remote_dir="/cache/a90-v2705",
            )
            self.assertTrue(manifest["ok"])
            self.assertEqual(manifest["summary"]["prepended_cal_types"], [24, 10, 14])
            self.assertEqual(manifest["summary"]["custom_topology_file_count"], 3)
            self.assertEqual(manifest["summary"]["replay_entry_count"], 6)
            argv = manifest["remote_argv"]
            basic_specs = [argv[index + 1] for index, token in enumerate(argv) if token == "--basic-payload"]
            self.assertEqual(
                basic_specs[:4],
                [
                    "39:0:/cache/a90-v2705/00-core_custom_topologies.bin",
                    "24:0:/cache/a90-v2705/01-subsystem-custom-topology-cal24-afe.bin",
                    "10:0:/cache/a90-v2705/02-subsystem-custom-topology-cal10-adm.bin",
                    "14:0:/cache/a90-v2705/03-subsystem-custom-topology-cal14-asm.bin",
                ],
            )
            self.assertIn("--exact-set", argv)

    def test_stage_targets_rejects_zero_or_missing_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.make_v2704_result(root)
            payload = json.loads(result.read_text())
            payload["large_get_summary"]["target_rows"][0]["raw_status"]["local_path"] = str(root / "missing.bin")
            result.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "validation failed"):
                v2705.load_v2704_targets(result)

    def test_report_redacts_private_paths_but_keeps_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = v2705.build_manifest(
                self.make_base_deploy(root),
                self.make_v2704_result(root),
                root / "stable",
                remote_dir="/cache/a90-v2705",
            )
            report = root / "report.md"
            private_manifest = root / "private.json"
            v2705.write_report(report, manifest, private_manifest)
            text = report.read_text(encoding="utf-8")
            self.assertIn("cal_type", text)
            self.assertIn("AFE_CUSTOM_TOPOLOGY", text)
            self.assertIn("ADM_CUSTOM_TOPOLOGY", text)
            self.assertIn("ASM_CUSTOM_TOPOLOGY", text)
            self.assertNotIn(str(root / "stable"), text)


if __name__ == "__main__":
    unittest.main()
