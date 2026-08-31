#!/usr/bin/env python3
"""Hostile tests for the inactive S20+ root-health public exec repair model."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import ast
import difflib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_attended_root_health_public_exec_repair_v1_h0.py"
)


def load_module():
    name = "s20plus_g986n_attended_root_health_public_exec_repair_v1_h0_tested"
    spec = importlib.util.spec_from_file_location(name, SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load public exec repair model")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class PublicExecRepairV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()
        cls.source = SOURCE.read_bytes()
        cls.candidate = cls.m.ACTIVE_RUNNER_PATH.read_bytes()
        cls.predecessor = cls.m.reconstruct_qualified_predecessor(cls.candidate)
        cls.assert_candidate = cls.m.apply_candidate_transform(cls.predecessor)
        cls.qualification = cls.m.validate_candidate(cls.predecessor)

    def test_render_is_exact_inactive_h0(self):
        plan = self.m.render_plan()
        self.assertEqual(plan["schema"], self.m.SCHEMA)
        self.assertEqual(plan["status"], self.m.STATUS)
        self.assertEqual(plan["authority"]["tier"], "H0")
        self.assertFalse(plan["authority"]["device_contact"])
        self.assertFalse(plan["authority"]["adb_executed"])
        self.assertFalse(plan["authority"]["su_executed"])
        self.assertEqual(plan["authority"]["device_effects"], 0)
        self.assertEqual(
            plan["gates"],
            {
                "repair_reviewed": True,
                "active_runner_exact_bound": True,
                "adb_source_correspondence_reviewed": True,
                "focused_test_rotation_reviewed": True,
                "target_contract_rotated": True,
                "document_assertions_rotated": True,
                "active_runner_rotated": True,
                "mechanical_activation_complete": True,
                "fresh_direct_request_present": False,
                "live_authority": False,
            },
        )
        self.assertTrue(plan["candidate_application"]["performed"])
        self.assertTrue(
            plan["candidate_application"]["current_runner_matches_candidate"]
        )
        self.assertFalse(plan["candidate_application"]["device_retry_authorized"])
        self.assertEqual(plan["caller_inputs"], [])
        self.assertEqual(plan["connected_modes"], [])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["root_commands"], [])
        self.assertEqual(plan["private_writes"], [])

    def test_self_identity_normalizes_only_self_hash_and_gates(self):
        observed = self.m.normalized_source_sha256(self.source)
        self.assertEqual(observed, self.m.EXPECTED_SELF_NORMALIZED_SHA256)
        changed = self.source.replace(
            b'PUBLIC_SCRIPT_SIZE = 423', b'PUBLIC_SCRIPT_SIZE = 424', 1
        )
        self.assertNotEqual(observed, self.m.normalized_source_sha256(changed))
        duplicate = self.source + b"\nLIVE_AUTHORITY = False\n"
        with self.assertRaisesRegex(self.m.PublicExecRepairV1Error, "ambiguous"):
            self.m.normalized_source_sha256(duplicate)
        with self.assertRaises(self.m.PublicExecRepairV1Error):
            self.m.normalized_source_sha256(bytearray(self.source))

    def test_active_and_candidate_identities_are_exact(self):
        self.assertEqual(
            len(self.predecessor), self.m.QUALIFIED_PREDECESSOR_IDENTITY["size"]
        )
        self.assertEqual(
            hashlib.sha256(self.predecessor).hexdigest(),
            self.m.QUALIFIED_PREDECESSOR_IDENTITY["sha256"],
        )
        self.assertEqual(
            len(self.candidate), self.m.CANDIDATE_RUNNER_IDENTITY["size"]
        )
        self.assertEqual(
            hashlib.sha256(self.candidate).hexdigest(),
            self.m.CANDIDATE_RUNNER_IDENTITY["sha256"],
        )
        self.assertEqual(self.assert_candidate, self.candidate)

    def test_current_candidate_reconstructs_only_exact_predecessor(self):
        self.assertEqual(
            self.m.reconstruct_qualified_predecessor(self.candidate),
            self.predecessor,
        )
        for changed in (
            self.candidate + b"\n",
            self.candidate.replace(b"SM-G986N", b"SM-G986X", 1),
            self.candidate.replace(self.m.NEW_ARGUMENT_LINE, b"", 1),
            bytearray(self.candidate),
        ):
            with self.subTest(kind=type(changed).__name__, size=len(changed)):
                with self.assertRaises(self.m.PublicExecRepairV1Error):
                    self.m.reconstruct_qualified_predecessor(changed)

    def test_transform_is_exactly_two_reviewed_line_changes(self):
        diff = list(
            difflib.unified_diff(
                self.predecessor.decode().splitlines(),
                self.candidate.decode().splitlines(),
                lineterm="",
            )
        )
        removed = [line for line in diff if line.startswith("-") and not line.startswith("---")]
        added = [line for line in diff if line.startswith("+") and not line.startswith("+++")]
        self.assertEqual(
            removed,
            [
                "-PUBLIC_SHELL_ARGUMENT = shlex.quote(PUBLIC_SNAPSHOT_SCRIPT)",
                '-            "<single-shlex-quoted-fixed-literal>",',
            ],
        )
        self.assertEqual(
            added,
            [
                "+PUBLIC_SHELL_ARGUMENT = PUBLIC_SNAPSHOT_SCRIPT",
                '+            "<single-raw-fixed-script-argv-ADB-escaped-once>",',
            ],
        )

    def test_transform_rejects_any_active_source_drift(self):
        variants = (
            self.predecessor + b"\n",
            self.predecessor.replace(b"SM-G986N", b"SM-G986X", 1),
            self.predecessor.replace(self.m.OLD_ARGUMENT_LINE, b"", 1),
            bytearray(self.predecessor),
        )
        for variant in variants:
            with self.subTest(kind=type(variant).__name__, size=len(variant)):
                with self.assertRaises(self.m.PublicExecRepairV1Error):
                    self.m.apply_candidate_transform(variant)

    def test_fixed_remote_script_literals_are_byte_identical(self):
        active = self.m._literal_assignments(self.predecessor)
        candidate = self.m._literal_assignments(self.candidate)
        self.assertEqual(active, candidate)
        public = active["PUBLIC_SNAPSHOT_SCRIPT"].encode()
        root = active["ROOT_READ_SCRIPT"].encode()
        self.assertEqual(len(public), self.m.PUBLIC_SCRIPT_SIZE)
        self.assertEqual(hashlib.sha256(public).hexdigest(), self.m.PUBLIC_SCRIPT_SHA256)
        self.assertEqual(len(root), self.m.ROOT_SCRIPT_SIZE)
        self.assertEqual(hashlib.sha256(root).hexdigest(), self.m.ROOT_SCRIPT_SHA256)

    def test_public_assignment_changes_from_prequote_to_direct_reference(self):
        active = self.m._assignment_shape(
            self.predecessor, "PUBLIC_SHELL_ARGUMENT"
        )
        candidate = self.m._assignment_shape(
            self.candidate, "PUBLIC_SHELL_ARGUMENT"
        )
        self.assertIsInstance(active, ast.Call)
        self.assertIsInstance(candidate, ast.Name)
        self.assertEqual(candidate.id, "PUBLIC_SNAPSHOT_SCRIPT")

    def test_root_assignment_remains_exact_shlex_quote(self):
        active = ast.dump(
            self.m._assignment_shape(self.predecessor, "ROOT_SHELL_ARGUMENT"),
            include_attributes=False,
        )
        candidate = ast.dump(
            self.m._assignment_shape(self.candidate, "ROOT_SHELL_ARGUMENT"),
            include_attributes=False,
        )
        self.assertEqual(active, candidate)
        self.m._assert_shlex_quote_assignment(
            self.candidate, "ROOT_SHELL_ARGUMENT", "ROOT_READ_SCRIPT"
        )

    def test_adb_escape_arg_matches_single_quote_algorithm(self):
        self.assertEqual(self.m.adb_escape_arg(""), "''")
        self.assertEqual(self.m.adb_escape_arg("abc"), "'abc'")
        self.assertEqual(self.m.adb_escape_arg("a'b"), "'a'\\''b'")
        with self.assertRaises(self.m.PublicExecRepairV1Error):
            self.m.adb_escape_arg("bad\x00arg")
        with self.assertRaises(self.m.PublicExecRepairV1Error):
            self.m.adb_escape_arg(b"bytes")

    def test_exec_out_constructor_escapes_every_argument_after_command(self):
        service = self.m.exec_out_service("sh", "-c", "printf '%s' x")
        self.assertEqual(
            service,
            "exec:sh '-c' 'printf '\\''%s'\\'' x'",
        )
        self.assertEqual(
            shlex.split(service.removeprefix("exec:")),
            ["sh", "-c", "printf '%s' x"],
        )

    def test_qualified_predecessor_exec_service_delivers_prequoted_script(self):
        public = self.m._literal_assignments(self.predecessor)[
            "PUBLIC_SNAPSHOT_SCRIPT"
        ]
        prequoted = shlex.quote(public)
        service = self.m.exec_out_service("sh", "-c", prequoted)
        remote = shlex.split(service.removeprefix("exec:"))
        self.assertEqual(
            len(service.encode()), self.m.PREDECESSOR_EXEC_SERVICE_SIZE
        )
        self.assertEqual(
            hashlib.sha256(service.encode()).hexdigest(),
            self.m.PREDECESSOR_EXEC_SERVICE_SHA256,
        )
        self.assertEqual(remote, ["sh", "-c", prequoted])
        self.assertNotEqual(remote[-1], public)

    def test_candidate_exec_service_delivers_raw_script_exactly_once(self):
        public = self.m._literal_assignments(self.candidate)["PUBLIC_SNAPSHOT_SCRIPT"]
        service = self.m.exec_out_service("sh", "-c", public)
        remote = shlex.split(service.removeprefix("exec:"))
        self.assertEqual(len(service.encode()), self.m.CANDIDATE_EXEC_SERVICE_SIZE)
        self.assertEqual(
            hashlib.sha256(service.encode()).hexdigest(),
            self.m.CANDIDATE_EXEC_SERVICE_SHA256,
        )
        self.assertEqual(remote, ["sh", "-c", public])

    def test_shell_join_requires_root_prequote_and_remains_correct(self):
        root = self.m._literal_assignments(self.candidate)["ROOT_READ_SCRIPT"]
        argument = shlex.quote(root)
        command = self.m.shell_join("su", "-c", argument)
        self.assertEqual(shlex.split(command), ["su", "-c", root])
        self.assertNotEqual(shlex.split(self.m.shell_join("su", "-c", root)), ["su", "-c", root])
        with self.assertRaises(self.m.PublicExecRepairV1Error):
            self.m.shell_join("su", "-c", "bad\x00arg")

    def test_incident_signature_and_zero_root_count_are_exact(self):
        material = (
            self.m.INCIDENT["failure_class"]
            + ":"
            + self.m.INCIDENT["failure_message"]
        ).encode()
        self.assertEqual(
            hashlib.sha256(material).hexdigest(),
            self.m.INCIDENT["failure_signature_sha256"],
        )
        self.assertEqual(self.m.INCIDENT["host_commands"], 3)
        self.assertEqual(self.m.INCIDENT["public_snapshots"], 1)
        self.assertEqual(self.m.INCIDENT["root_commands"], 0)
        self.assertEqual(self.m.INCIDENT["device_effects"], 0)

    def test_qualification_preserves_claim_boundary(self):
        self.assertFalse(
            self.qualification[
                "qualified_predecessor_public_argument_equals_raw_script"
            ]
        )
        self.assertFalse(
            self.qualification["qualified_predecessor_exec_service"][
                "remote_final_argv_equals_raw_script"
            ]
        )
        self.assertTrue(
            self.qualification["qualified_predecessor_exec_service"][
                "remote_final_argv_equals_prequoted_script"
            ]
        )
        self.assertTrue(
            self.qualification["candidate_exec_service"][
                "remote_final_argv_equals_raw_script"
            ]
        )
        self.assertTrue(self.qualification["root_transport_unchanged"])
        claims = self.m.render_plan()["claims"]
        self.assertIn("double-escaping-was-the-only-runtime-cause", claims["unknown"])
        self.assertIn("current-root-health", claims["unknown"])

    def test_fixed_scripts_have_no_mutation_or_partition_surface(self):
        literals = self.m._literal_assignments(self.candidate)
        scripts = (literals["PUBLIC_SNAPSHOT_SCRIPT"] + literals["ROOT_READ_SCRIPT"]).lower()
        for forbidden in (
            "setprop ",
            "settings ",
            " chmod ",
            " chown ",
            " mount ",
            " umount ",
            " mkdir ",
            " rm ",
            " mv ",
            " cp ",
            " reboot",
            "odin",
            "/dev/block",
            "magisk --install",
        ):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, scripts)

    def test_model_source_has_no_connected_backend_or_process_api(self):
        tree = ast.parse(self.source.decode())
        imports = {
            alias.name.split(".")[0]
            for node in tree.body
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue(
            {"subprocess", "socket", "ctypes", "fcntl", "os"}.isdisjoint(imports)
        )
        self.assertNotIn(b'"--connected"', self.source)
        self.assertNotIn(b"Popen(", self.source)
        self.assertNotIn(b"execve", self.source)

    def test_live_gate_is_unconditionally_unimplemented(self):
        self.assertTrue(self.m._gates()["repair_reviewed"])
        self.assertTrue(self.m._gates()["active_runner_rotated"])
        self.assertTrue(self.m._gates()["mechanical_activation_complete"])
        self.assertFalse(self.m._gates()["fresh_direct_request_present"])
        self.assertFalse(self.m._gates()["live_authority"])
        with self.assertRaisesRegex(
            self.m.PublicExecRepairV1Error, "H0-only and not active"
        ):
            self.m._require_live_gates()

    def test_cli_renders_json_and_accepts_no_inputs(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(self.m.run(["--render-plan"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], self.m.STATUS)
        for argv in ([], ["--connected"], ["--render-plan", "serial"]):
            with self.subTest(argv=argv):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        self.m.run(argv)

    def test_exact_target_and_adb_binding(self):
        self.assertEqual(
            dict(self.m.TARGET),
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertEqual(self.m.ADB_IDENTITY["path"], "/usr/lib/android-sdk/platform-tools/adb")
        self.assertEqual(self.m.ADB_IDENTITY["platform_tools_tag"], "platform-tools-34.0.5")
        self.assertRegex(self.m.ADB_IDENTITY["sha256"], r"\A[0-9a-f]{64}\Z")

    def test_current_parser_metadata_matches_exact_applied_candidate(self):
        active_plan = self.m.OLD_PLAN_BLOCK.decode()
        candidate_plan = self.m.NEW_PLAN_BLOCK.decode()
        self.assertIn("single-shlex-quoted-fixed-literal", active_plan)
        self.assertIn("single-raw-fixed-script-argv-ADB-escaped-once", candidate_plan)
        self.assertIn(self.m.OLD_PLAN_BLOCK, self.predecessor)
        self.assertNotIn(self.m.OLD_PLAN_BLOCK, self.candidate)
        self.assertIn(self.m.NEW_PLAN_BLOCK, self.candidate)
        self.assertIn(self.m.OLD_ARGUMENT_LINE, self.predecessor)
        self.assertNotIn(self.m.NEW_ARGUMENT_LINE, self.predecessor)


if __name__ == "__main__":
    unittest.main()
