import json
import tempfile
from pathlib import Path
import unittest

import native_audio_acdb_core_topology_replay_deploy_plan_v2684 as v2684


class CoreTopologyReplayDeployPlanV2684Test(unittest.TestCase):
    def write_file(self, root: Path, name: str, data: bytes) -> str:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def test_basic_payload_arg_format(self):
        self.assertEqual(v2684.basic_payload_arg(14, 0, "/x/p.bin"), "14:0:/x/p.bin")

    def test_build_deploy_plan_replaces_stale_cal14_and_adds_cal10(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            helper = self.write_file(root, "helper", b"helper")
            core = self.write_file(root, "core.bin", b"corepayload")
            cand_dir = root / "candidates"
            cand_dir.mkdir()
            cal10 = cand_dir / v2684.CANDIDATES[10]["filename"]
            cal14 = cand_dir / v2684.CANDIDATES[14]["filename"]
            cal10.write_bytes(b"A" * 396)
            cal14.write_bytes(b"B" * 396)
            v2684.CANDIDATES[10]["expected_sha256"] = v2684.sha256_file(cal10)
            v2684.CANDIDATES[14]["expected_sha256"] = v2684.sha256_file(cal14)
            cal24_arg = self.write_file(root, "cal24.arg", b"cal24arg")
            cal24_payload = self.write_file(root, "cal24.payload", b"cal24payload")
            cal14_arg = self.write_file(root, "cal14.arg", b"stale14arg")
            cal14_payload = self.write_file(root, "cal14.payload", b"stale14payload")
            cal13_arg = self.write_file(root, "cal13.arg", b"cal13arg")

            def file_entry(kind, remote, local_path):
                path = Path(local_path)
                return {
                    "kind": kind,
                    "remote_path": remote,
                    "local": {
                        "local_path_private": str(path),
                        "size": path.stat().st_size,
                        "sha256": v2684.sha256_file(path),
                    },
                }

            base = {
                "ok": True,
                "all_inputs_ok": True,
                "hold_sec": 10,
                "files": [
                    file_entry("helper", "/old/helper", helper),
                    file_entry("topology", "/old/core", core),
                    file_entry("set_arg", "/old/cal24.arg", cal24_arg),
                    file_entry("payload", "/old/cal24.payload", cal24_payload),
                    file_entry("set_arg", "/old/cal14.arg", cal14_arg),
                    file_entry("payload", "/old/cal14.payload", cal14_payload),
                    file_entry("set_arg", "/old/cal13.arg", cal13_arg),
                ],
                "set_args": [
                    {"cal_type": 24, "role": "AFE", "source": "old", "dmabuf_expected": True, "arg_remote": "/old/cal24.arg", "payload_remote": "/old/cal24.payload"},
                    {"cal_type": 14, "role": "STALE", "source": "V2675 acdb_loader_send_common_custom_topology SET capture", "dmabuf_expected": True, "arg_remote": "/old/cal14.arg", "payload_remote": "/old/cal14.payload"},
                    {"cal_type": 13, "role": "APP", "source": "old", "dmabuf_expected": False, "arg_remote": "/old/cal13.arg", "payload_remote": None},
                ],
            }
            manifest_path = root / "base.json"
            manifest_path.write_text(json.dumps(base))
            plan = v2684.build_deploy_plan(manifest_path, cand_dir, remote_dir="/cache/test")
            self.assertTrue(plan["ok"])
            self.assertEqual(plan["summary"]["cal_order"], [39, 10, 14, 24, 13])
            argv = plan["remote_argv"]
            self.assertIn("10:0:/cache/test/01-core-derived-payload-cal10-topo10004000.bin", argv)
            self.assertIn("14:0:/cache/test/02-core-derived-payload-cal14-topo10005000.bin", argv)
            self.assertNotIn("/old/cal14.arg", " ".join(argv))


if __name__ == "__main__":
    unittest.main()
