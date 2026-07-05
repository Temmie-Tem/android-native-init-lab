from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta227_cloudflared_egress_route_artifact.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta227_cloudflared_egress_route_artifact.py")


class ServerDistroWsta227CloudflaredEgressRouteArtifactTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def route(self, suffix: str) -> str:
        return "198.51.100." + suffix

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def observation(self) -> dict:
        return {
            "schema": runner.OBSERVATION_SCHEMA,
            "state": runner.OBSERVATION_STATE,
            "source": "attended-live-runtime",
            "observed_at_utc": "20260705T140000Z",
            "dns4": [self.route("53"), self.route("53")],
            "tls4": [self.route("10") + "/32"],
            "evidence": {
                "resolver_ready": True,
                "dns_route_observed": True,
                "tls_route_observed": True,
            },
            "route_values_private": True,
            "route_values_logged": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }

    def valid_args(self, root: Path):
        observation_path = root / "inputs" / "route_observation.json"
        self.write_json(observation_path, self.observation())
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta227"),
            "--emit-route-artifact",
            "--route-observation-json",
            str(observation_path),
        ])

    def test_default_run_is_fail_closed_and_host_only(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta227"),
            ]))

        self.assertEqual(result["decision"], "wsta227-blocked-explicit-emit-route-artifact-required")
        for key in ("device_action", "boot_flash", "native_reboot", "wifi_connect", "packet_filter_mutation"):
            self.assertFalse(result["safety"][key])

    def test_valid_private_observation_emits_wsta226_route_artifact(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.valid_args(root))
            artifact_path = root / "wsta227" / runner.ARTIFACT_NAME
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            saved = json.loads((root / "wsta227" / runner.RESULT_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta227" / runner.MARKDOWN_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        self.assertEqual(artifact["schema"], runner.wsta226.ROUTE_SCHEMA)
        self.assertEqual(artifact["state"], runner.wsta226.ROUTE_STATE)
        self.assertEqual(artifact["dns4"], [self.route("53")])
        self.assertEqual(artifact["tls4"], [self.route("10") + "/32"])
        self.assertTrue(runner.wsta226.validate_route_artifact(artifact)["dns4_present"])
        self.assertEqual(result["route_artifact_public"]["dns4_count"], 1)
        self.assertEqual(result["route_artifact_public"]["tls4_count"], 1)
        self.assertTrue(result["route_artifact_public"]["route_values_redacted"])
        public_text = json.dumps(runner.public_summary(result), sort_keys=True)
        self.assertNotIn(self.route("53"), public_text)
        self.assertNotIn(self.route("10"), public_text)
        self.assertIn("WSTA227 Cloudflared Egress Route Artifact", markdown)

    def test_invalid_observation_fails_closed_before_artifact(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            observation = self.observation()
            observation["tls4"] = []
            observation_path = root / "inputs" / "route_observation.json"
            self.write_json(observation_path, observation)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta227"),
                "--emit-route-artifact",
                "--route-observation-json",
                str(observation_path),
            ]))

        self.assertEqual(result["decision"], "wsta227-blocked-route-observation-invalid")
        self.assertFalse(result["checks"]["observation_tls4_present"])
        self.assertFalse((root / "wsta227" / runner.ARTIFACT_NAME).exists())

    def test_nonprivate_run_or_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observation_path = root / "route_observation.json"
            self.write_json(observation_path, self.observation())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta227"),
                "--emit-route-artifact",
                "--route-observation-json",
                str(observation_path),
            ]))

        self.assertEqual(result["decision"], "wsta227-blocked-nonprivate-run-dir")

        with self.private_tmp() as private_tmp, tempfile.TemporaryDirectory() as public_tmp:
            private_root = Path(private_tmp)
            public_root = Path(public_tmp)
            observation_path = public_root / "route_observation.json"
            self.write_json(observation_path, self.observation())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(private_root / "wsta227"),
                "--emit-route-artifact",
                "--route-observation-json",
                str(observation_path),
            ]))

        self.assertEqual(result["decision"], "wsta227-blocked-route-observation-nonprivate")

    def test_source_keeps_live_and_public_value_surfaces_out(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--emit-route-artifact", source)
        self.assertIn("a90-wsta227-cloudflared-egress-route-observation-v1", source)
        self.assertIn("wsta226.ROUTE_SCHEMA", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn('"route_values_logged": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("try" + "cloudflare.com", source)
        self.assertNotIn("ssid" + "=", source.lower())
        self.assertNotIn("psk" + "=", source.lower())


if __name__ == "__main__":
    unittest.main()
