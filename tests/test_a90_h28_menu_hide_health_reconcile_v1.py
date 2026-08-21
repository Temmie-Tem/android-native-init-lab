from __future__ import annotations

import ast
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OWNER = load("a90_boot_only_f1_minimal_v1")
ADAPTER = load("a90_boot_only_f1_adapter_v1")
R = load("a90_h28_menu_hide_health_reconcile_v1")


class FakeSocket:
    def __init__(self, chunks: list[bytes], *, fail_send: BaseException | None = None):
        self.chunks = list(chunks)
        self.fail_send = fail_send
        self.sent: list[bytes] = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True
        return False

    def settimeout(self, _value):
        return None

    def sendall(self, value: bytes):
        if self.fail_send:
            raise self.fail_send
        self.sent.append(value)

    def recv(self, _size: int) -> bytes:
        if self.chunks:
            return self.chunks.pop(0)
        raise TimeoutError()


class FakeRunner:
    def __init__(self, directory: Path):
        self.log_directory = directory
        self.log_directory.mkdir(mode=0o700, exist_ok=True)
        self.sequence = 2


class MenuHideHealthTest(unittest.TestCase):
    def test_new_capability_and_namespace_are_distinct(self):
        self.assertEqual(R.CAPABILITY, "A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_V1")
        self.assertNotEqual(R.CAPABILITY, "A90_H28_SLOW_HEALTH_RECONCILIATION_V1")
        self.assertNotIn("slow-health-1-logs", str(R.SIDE_ROOT))
        self.assertEqual(R.INTENT_NAME, "10-menu-hide-health-observation-intent.json")

    def test_prior_bindings_and_receipt_inventory_are_closed(self):
        self.assertEqual(R.MANIFEST_SHA256, "e708e45e9cd925229682c76ad3b6359426f2e636eb26eb111ea54e9843e8d1c2")
        self.assertEqual(R.TERMINAL_SHA256, "400a6fe75ea54a738777092f828dede4d7b801bd3fbd8db29baddf26878c4f01")
        self.assertEqual(R.PRIOR_PHYSICAL_INTENT_SHA256, "19377bc18714c7b2b698665a8c9ff96573d3c1fdfb028efba5b86f6b2def9f66")
        self.assertEqual(R.PRIOR_OBSERVATION_INTENT_SHA256, "8f401590bca71575258a2e3d45e1bee6c55fd4e8eeff4c22012fc25f559d05be")
        self.assertEqual(R.PRIOR_SLOW_HEALTH_INTENT_SHA256, "63c26238f332a7bc1bad37a3950d5dc05f383c50a4a09ecfe57e2a119a390ac4")
        self.assertEqual(len(R.PRIOR_SLOW_LOG_HASHES), 12)
        self.assertEqual(set(R.PRIOR_SLOW_LOG_HASHES), {
            f"{n:03d}-{label}.{stream}"
            for n, label in ((1, "usb-inventory"), (2, "bridge-preflight"), (3, "version"), (4, "selftest"), (5, "status"), (6, "boot-id"))
            for stream in ("stdout", "stderr")
        })

    def test_prepare_token_is_bound_to_new_namespace(self):
        token = R._approval_token("a" * 64, "b" * 64)
        self.assertTrue(token.startswith(R.APPROVAL_PREFIX))
        self.assertNotIn("SLOW-HEALTH-V1-APPROVE", token)
        self.assertNotEqual(token, R.APPROVAL_PREFIX + "0" * 64)

    def test_token_substitution_changes_binding(self):
        one = R._approval_token("a" * 64, "b" * 64)
        two = R._approval_token("c" * 64, "b" * 64)
        three = R._approval_token("a" * 64, "d" * 64)
        self.assertNotEqual(one, two)
        self.assertNotEqual(one, three)

    def test_raw_hide_sends_one_unframed_line(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = FakeRunner(Path(temporary))
            sock = FakeSocket([b"hide requested\n"])
            with mock.patch.object(R.socket, "create_connection", return_value=sock):
                digest = R._raw_hide(runner, timeout_sec=1)
            self.assertEqual(sock.sent, [b"hide\n"])
            self.assertEqual(runner.sequence, 3)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertTrue((Path(temporary) / "003-menu-hide.stdout").read_bytes())

    def test_raw_hide_busy_is_terminal_and_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = FakeRunner(Path(temporary))
            sock = FakeSocket([b"[busy] auto menu active\n"])
            with mock.patch.object(R.socket, "create_connection", return_value=sock):
                with self.assertRaises(R.ContractError):
                    R._raw_hide(runner, timeout_sec=1)
            self.assertEqual(sock.sent, [b"hide\n"])

    def test_raw_hide_prompt_or_done_only_is_not_a_hide_receipt(self):
        for response in (b"a90:/#\n", b"[done]\n"):
            with self.subTest(response=response):
                with tempfile.TemporaryDirectory() as temporary:
                    runner = FakeRunner(Path(temporary))
                    sock = FakeSocket([response])
                    with mock.patch.object(R.socket, "create_connection", return_value=sock):
                        with self.assertRaises(R.ContractError):
                            R._raw_hide(runner, timeout_sec=1)
                    self.assertEqual(sock.sent, [b"hide\n"])

    def test_raw_hide_send_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = FakeRunner(Path(temporary))
            sock = FakeSocket([], fail_send=OSError("short transport"))
            with mock.patch.object(R.socket, "create_connection", return_value=sock):
                with self.assertRaises(R.ContractError):
                    R._raw_hide(runner, timeout_sec=1)
            self.assertEqual(sock.sent, [])
            self.assertEqual(runner.sequence, 3)

    def test_settle_uses_existing_three_second_budget(self):
        with mock.patch.object(R.time, "sleep") as sleep:
            R._settle_after_hide()
        sleep.assert_called_once_with(3.0)

    def test_settle_interruption_is_terminal(self):
        with mock.patch.object(R.time, "sleep", side_effect=InterruptedError("interrupted")):
            with self.assertRaises(R.ContractError):
                R._settle_after_hide()

    def _observation(self, *, healthy=True, order=("hide", "boot-id", "version", "selftest", "status", "boot-id-final"), final_boot_id="01234567-89ab-cdef-0123-456789abcdef", same_boot=True):
        snapshot = OWNER.Snapshot(
            target_evidence_sha256="1" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=R.VERSION,
            build=R.BUILD,
            healthy=healthy,
            recovery_available=True,
            recovery_evidence_sha256="2" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="3" * 64,
        )
        return R.Observation(snapshot, "4" * 64, tuple(order), final_boot_id, same_boot)

    def test_observation_requires_hide_then_boot_id_then_health(self):
        expected = {"version": R.VERSION, "build": R.BUILD}
        valid = self._observation()
        self.assertIs(R._validate_observation(valid, expected, "2" * 64), valid)
        for order in (
            ("boot-id", "hide", "version", "selftest", "status", "boot-id-final"),
            ("hide", "version", "boot-id", "selftest", "status", "boot-id-final"),
            ("hide", "boot-id", "version", "status", "selftest", "boot-id-final"),
        ):
            with self.assertRaises(R.ContractError):
                R._validate_observation(self._observation(order=order), expected, "2" * 64)

    def test_final_boot_id_change_missing_or_invalid_parks(self):
        expected = {"version": R.VERSION, "build": R.BUILD}
        changed = self._observation(final_boot_id="fedcba98-7654-3210-fedc-ba9876543210", same_boot=False)
        invalid = self._observation(final_boot_id="not-a-boot-id")
        missing = self._observation(final_boot_id=None)
        for observation in (changed, invalid, missing):
            with self.subTest(observation=observation):
                with self.assertRaises((R.ContractError, TypeError)):
                    R._validate_observation(observation, expected, "2" * 64)

    def test_wrong_resident_or_boot_health_is_rejected(self):
        expected = {"version": R.VERSION, "build": R.BUILD}
        wrong = self._observation()
        object.__setattr__(wrong.snapshot, "version", "wrong")
        with self.assertRaises(R.ContractError):
            R._validate_observation(wrong, expected, "2" * 64)
        wrong_boot = self._observation()
        object.__setattr__(wrong_boot.snapshot, "boot_id", "not-a-boot-id")
        with self.assertRaises(R.ContractError):
            R._validate_observation(wrong_boot, expected, "2" * 64)

    def test_payload_requires_same_boot_and_zero_effects(self):
        observation = self._observation()
        payload = R._payload(observation, "a" * 64, "b" * 64, "c" * 64)
        self.assertTrue(payload["sameBoot"])
        self.assertEqual(payload["finalBootId"], observation.snapshot.boot_id)
        payload["recoveredSnapshot"]["recoveryEvidenceSha256"] = "b" * 64
        payload["recoveredSnapshotSha256"] = R._json_sha(payload["recoveredSnapshot"])
        R._validate_payload(payload, {"rollback": {"version": R.VERSION, "build": R.BUILD}}, "a" * 64, "b" * 64, "c" * 64)
        payload["sameBoot"] = False
        with self.assertRaises(R.ContractError):
            R._validate_payload(payload, {"rollback": {"version": R.VERSION, "build": R.BUILD}}, "a" * 64, "b" * 64, "c" * 64)

    def test_source_reads_boot_id_exactly_twice_and_hides_once(self):
        source = (MODULE_DIR / "a90_h28_menu_hide_health_reconcile_v1.py").read_text()
        self.assertEqual(source.count('self._a90ctl("boot-id",'), 1)
        self.assertEqual(source.count('self._a90ctl("boot-id-final",'), 1)
        self.assertEqual(source.count('sock.sendall(b"hide\\n")'), 1)

    def test_source_publishes_intent_before_raw_hide(self):
        source = (MODULE_DIR / "a90_h28_menu_hide_health_reconcile_v1.py").read_text()
        self.assertLess(source.index("intent_sha = _publish_intent(intent)"), source.index("observer.observe"))
        hide_index = source.index("hide_receipt_sha = _raw_hide")
        settle_index = source.index("_settle_after_hide()", hide_index)
        boot_index = source.index("receipts[\"bootId\"]", settle_index)
        self.assertLess(hide_index, settle_index)
        self.assertLess(settle_index, boot_index)
        self.assertEqual(source.count("sock.sendall(b\"hide\\n\")"), 1)
        self.assertIn("MENU_SETTLE_SEC = 3.0", source)
        self.assertIn('b"hide requested" not in stdout', source)

    def test_source_has_no_second_hide_or_unsafe_effect(self):
        source = (MODULE_DIR / "a90_h28_menu_hide_health_reconcile_v1.py").read_text()
        tree = ast.parse(source)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        hide_calls = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "sendall"]
        self.assertEqual(len(hide_calls), 1)
        self.assertNotIn("--retry-unsafe", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("/dev/block", source)
        self.assertNotIn("/system/bin/rebootsystem.sh", source)

    def test_source_has_only_prepare_and_execute_modes(self):
        parser = R.parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["finalize"])
        self.assertEqual(parser.parse_args(["prepare"]).action, "prepare")
        self.assertEqual(parser.parse_args(["execute", "--approval", "x"]).action, "execute")

    def test_review_closure_includes_new_docs(self):
        closure = R.execution_closure_sha256()
        self.assertRegex(closure, r"^[0-9a-f]{64}$")
        source = (MODULE_DIR / "a90_h28_menu_hide_health_reconcile_v1.py").read_text()
        self.assertIn("set(prior.EXECUTION_SOURCE_RELS)", source)
        design = ROOT / "docs/plans/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_DESIGN_2026-08-21.md"
        self.assertTrue(design.is_file())
        self.assertIn("3.0-second", design.read_text())
        self.assertTrue((ROOT / "docs/plans/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_REVIEW_HANDOFF_2026-08-21.md").is_file())

    def test_physical_reconciler_source_drift_changes_closure(self):
        baseline = R.execution_closure_sha256()
        target = (ROOT / "workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py").resolve()
        original = Path.read_bytes

        def altered(path: Path) -> bytes:
            raw = original(path)
            return raw + b"\n# hostile physical reconciler drift\n" if path.resolve() == target else raw

        with mock.patch.object(Path, "read_bytes", altered):
            self.assertNotEqual(R.execution_closure_sha256(), baseline)

    def test_physical_reconciler_design_drift_changes_closure(self):
        baseline = R.execution_closure_sha256()
        target = (ROOT / "docs/plans/A90_H28_PHYSICAL_SYSTEM_RETURN_RECOVERY_DESIGN_2026-08-21.md").resolve()
        original = Path.read_bytes

        def altered(path: Path) -> bytes:
            raw = original(path)
            return raw + b"\n<!-- hostile physical design drift -->\n" if path.resolve() == target else raw

        with mock.patch.object(Path, "read_bytes", altered):
            self.assertNotEqual(R.execution_closure_sha256(), baseline)


if __name__ == "__main__":
    unittest.main()
