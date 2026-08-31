from __future__ import annotations

import ast
from contextlib import ExitStack, contextmanager, redirect_stdout
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import pickle
import re
import select
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_start_interlock_v1_h0.py"
)
REVALIDATION = SOURCE.parent


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load test module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INTERLOCK = load_module(SOURCE, "_s20plus_start_interlock_v1_h0_test")


OPEN_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | os.O_DIRECTORY
    | os.O_CLOEXEC
    | os.O_NOFOLLOW
    | os.O_NONBLOCK
)


class TemporaryInterlockRoots:
    """Temp-only descriptor adapter; it never resolves a production root."""

    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.paths = {
            name: self.root / name for name in ("base", "evidence", "leaf")
        }
        for path in self.paths.values():
            path.mkdir()
            path.chmod(0o700)
        self.shared_path = self.root / "routine-actions"
        self.shared_path.mkdir()
        self.shared_path.chmod(INTERLOCK.SHARED_ACTION_GUARD_PARENT_MODE)
        self.descriptors = {
            name: os.open(path, OPEN_DIRECTORY_FLAGS)
            for name, path in self.paths.items()
        }
        self.shared_descriptor = os.open(self.shared_path, OPEN_DIRECTORY_FLAGS)
        return self

    def __exit__(self, exc_type, exc, traceback):
        for descriptor in self.descriptors.values():
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            os.close(self.shared_descriptor)
        except OSError:
            pass
        self.temporary.cleanup()

    def create_guard(self, node_type: str = "regular") -> Path:
        path = self.shared_path / INTERLOCK.SHARED_ACTION_GUARD_NAME
        if node_type == "regular":
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o600,
            )
            try:
                os.write(descriptor, b"fixture-only\n")
            finally:
                os.close(descriptor)
        elif node_type == "symlink":
            os.symlink("missing-fixture-target", path)
        elif node_type == "fifo":
            os.mkfifo(path, 0o600)
        else:
            raise AssertionError(f"unknown fixture node type: {node_type}")
        return path


LOCK_PROBE = r"""
import fcntl
import os
import sys

descriptor = os.open(
    sys.argv[1],
    os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
)
try:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("BUSY")
    else:
        print("ACQUIRED")
        fcntl.flock(descriptor, fcntl.LOCK_UN)
finally:
    os.close(descriptor)
"""


LOCK_HOLDER = r"""
import fcntl
import os
import sys

descriptor = os.open(
    sys.argv[1],
    os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
)
try:
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    print("READY", flush=True)
    sys.stdin.read(1)
    fcntl.flock(descriptor, fcntl.LOCK_UN)
finally:
    os.close(descriptor)
"""


def child_lock_result(path: Path) -> str:
    completed = subprocess.run(
        [sys.executable, "-c", LOCK_PROBE, str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return completed.stdout.strip()


@contextmanager
def child_holds_lock(path: Path):
    process = subprocess.Popen(
        [sys.executable, "-c", LOCK_HOLDER, str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        close_fds=True,
    )
    try:
        assert process.stdout is not None
        readable, _, _ = select.select([process.stdout], [], [], 5)
        if not readable:
            raise AssertionError("child lock holder did not become ready")
        if process.stdout.readline().strip() != "READY":
            raise AssertionError("child lock holder failed before readiness")
        yield process
    finally:
        if process.poll() is None:
            assert process.stdin is not None
            try:
                process.stdin.write("x")
                process.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            _, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate(timeout=5)
            raise AssertionError("child lock holder did not terminate")
        if process.returncode != 0:
            raise AssertionError(stderr)


class StartInterlockPlanTests(unittest.TestCase):
    def test_exact_target_and_three_fixed_roots(self):
        self.assertEqual(
            dict(INTERLOCK.TARGET),
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertEqual(set(INTERLOCK.FIXED_ROOTS), {"base", "evidence", "leaf"})
        self.assertEqual(len(set(INTERLOCK.FIXED_ROOTS.values())), 3)
        for path in INTERLOCK.FIXED_ROOTS.values():
            self.assertTrue(path.is_absolute())
            self.assertIn("s20plus-g986n", str(path))

    def test_all_operational_and_integration_gates_are_false(self):
        names = (
            "START_INTERLOCK_V1_QUALIFIED",
            "FIXED_ROOT_OPENER_ACTIVE",
            "EXACT_RECOVERY_SCANNER_ACTIVE",
            "LEAF_DIRECTORY_FLOCK_ACTIVE",
            "SHARED_ACTION_GUARD_CHECK_ACTIVE",
            "NEW_START_INTEGRATION_ACTIVE",
            "OBSERVER_INTEGRATION_ACTIVE",
            "OWNED_RECOVERY_BYPASS_INTEGRATED",
            "CONTRACT_ACTIVE",
            "MECHANICAL_ACTIVATION",
            "LIVE_AUTHORITY",
        )
        self.assertTrue(all(getattr(INTERLOCK, name) is False for name in names))

    def test_render_plan_is_non_authorizing_and_effect_free(self):
        plan = INTERLOCK.render_plan()
        self.assertTrue(all(value is False for value in plan["gates"].values()))
        self.assertEqual(plan["production_entrypoint"], "inactive-unimplemented")
        for key in (
            "caller_inputs",
            "callbacks",
            "backends",
            "device_commands",
            "device_effects",
            "root_commands",
            "odin_commands",
            "partition_transfers",
            "private_writes",
            "runner_integrations",
        ):
            self.assertEqual(plan[key], [])

    def test_render_only_cli(self):
        parser = INTERLOCK.build_parser()
        action_destinations = {
            action.dest for action in parser._actions if action.dest != "help"
        }
        self.assertEqual(action_destinations, {"render_plan"})
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(INTERLOCK.main(["--render-plan"]), 0)
        self.assertEqual(json.loads(output.getvalue())["schema"], INTERLOCK.PLAN_SCHEMA)

    def test_self_identity_is_exact_and_normalized(self):
        source = SOURCE.read_bytes()
        plan = INTERLOCK.render_plan()
        self.assertEqual(plan["self"]["size"], len(source))
        self.assertEqual(plan["self"]["sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(
            plan["self"]["normalized_sha256"],
            INTERLOCK.EXPECTED_SELF_NORMALIZED_SHA256,
        )

    def test_normalized_identity_allows_only_status_and_gate_rotation(self):
        source = SOURCE.read_bytes()
        expected = INTERLOCK.normalized_source_sha256(source)
        rotated = re.sub(
            rb'^STATUS = "[A-Z0-9_]+"$',
            b'STATUS = "H0_TEST_STATUS_NOT_ACTIVE"',
            source,
            count=1,
            flags=re.MULTILINE,
        )
        for name in INTERLOCK.render_plan()["gates"]:
            constant = name.upper()
            rotated = re.sub(
                rf"^{constant} = False$".encode(),
                f"{constant} = True".encode(),
                rotated,
                count=1,
                flags=re.MULTILINE,
            )
        self.assertEqual(INTERLOCK.normalized_source_sha256(rotated), expected)

    def test_normalized_identity_rejects_logic_drift(self):
        source = SOURCE.read_bytes()
        changed = source.replace(
            b'wait_or_retry": False',
            b'wait_or_retry": True',
            1,
        )
        self.assertNotEqual(changed, source)
        self.assertNotEqual(
            INTERLOCK.normalized_source_sha256(changed),
            INTERLOCK.normalized_source_sha256(source),
        )

    def test_public_entry_stops_before_any_fixed_root_access(self):
        with mock.patch.object(INTERLOCK, "_open_exact_fixed_roots") as opener:
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "operational owner is inactive",
            ):
                INTERLOCK.acquire_new_start_interlock()
        opener.assert_not_called()

    def test_even_forced_true_gates_reach_only_unimplemented_stub(self):
        gate_names = (
            "START_INTERLOCK_V1_QUALIFIED",
            "FIXED_ROOT_OPENER_ACTIVE",
            "EXACT_RECOVERY_SCANNER_ACTIVE",
            "LEAF_DIRECTORY_FLOCK_ACTIVE",
            "SHARED_ACTION_GUARD_CHECK_ACTIVE",
            "NEW_START_INTEGRATION_ACTIVE",
            "OBSERVER_INTEGRATION_ACTIVE",
            "OWNED_RECOVERY_BYPASS_INTEGRATED",
            "CONTRACT_ACTIVE",
            "MECHANICAL_ACTIVATION",
            "LIVE_AUTHORITY",
        )
        with ExitStack() as stack:
            for name in gate_names:
                stack.enter_context(mock.patch.object(INTERLOCK, name, True))
            with mock.patch.object(INTERLOCK, "_open_exact_fixed_roots") as opener:
                with self.assertRaisesRegex(
                    INTERLOCK.StartInterlockV1Error,
                    "not implemented",
                ):
                    INTERLOCK.acquire_new_start_interlock()
                opener.assert_not_called()

    def test_render_does_not_open_fixed_or_shared_private_roots(self):
        with mock.patch.object(
            INTERLOCK,
            "_open_exact_fixed_roots",
            side_effect=AssertionError("must not open roots"),
        ) as opener:
            plan = INTERLOCK.render_plan()
        opener.assert_not_called()
        self.assertEqual(plan["private_writes"], [])

    def test_source_has_no_device_transport_or_private_mutation_primitive(self):
        source_text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported.isdisjoint({"subprocess", "socket", "urllib"}))
        for token in (
            "O_CREAT",
            "os.mkdir(",
            "os.makedirs(",
            "os.unlink(",
            "os.remove(",
            "os.rename(",
            "os.replace(",
            "os.write(",
        ):
            self.assertNotIn(token, source_text)

    def test_all_pinned_raw_identities_match_current_exact_files(self):
        for label, identity in INTERLOCK.PINNED_IDENTITIES.items():
            with self.subTest(label=label):
                path = REVALIDATION / identity["name"]
                payload = path.read_bytes()
                self.assertEqual(len(payload), identity["size"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), identity["sha256"])

    def test_coordinator_lock_is_recovery_only(self):
        plan = INTERLOCK.render_plan()
        self.assertEqual(plan["coordinator_lock"]["name"], "coordinator.lock")
        self.assertTrue(plan["coordinator_lock"]["recovery_only"])
        self.assertFalse(plan["coordinator_lock"]["used_for_new_start"])
        self.assertFalse(plan["coordinator_lock"]["used_by_fixture_flock"])
        function_source = inspect.getsource(INTERLOCK._fixture_new_start_slot)
        self.assertNotIn("RECOVERY_COORDINATOR_LOCK_NAME", function_source)

    def test_owned_recovery_bypass_grants_no_new_start_or_replay(self):
        bypass = INTERLOCK.model_owned_recovery_bypass()
        self.assertFalse(bypass["acquires_leaf_directory_flock"])
        self.assertTrue(bypass["requires_exact_preexisting_owned_shared_guard"])
        self.assertTrue(bypass["requires_exact_owned_journal"])
        for key in (
            "creates_shared_action_guard",
            "new_start_authorized",
            "device_commands_authorized_by_interlock",
            "replay_authorized_by_interlock",
            "recovery_authorized_by_interlock",
            "live_authority",
        ):
            self.assertFalse(bypass[key])


class StartInterlockScanTests(unittest.TestCase):
    def test_only_empty_and_parked_complete_are_allowlisted(self):
        self.assertEqual(
            INTERLOCK.ALLOWED_START_STATES,
            frozenset({"EMPTY", "PARKED_COMPLETE"}),
        )
        self.assertTrue(
            {"ACTIVE", "INCOMPLETE", "EXPIRED", "MALFORMED", "UNKNOWN"}
            <= INTERLOCK.BLOCKED_STATES
        )

    def test_empty_receipt_is_exact_and_non_authorizing(self):
        payload = INTERLOCK.model_scan_payload("EMPTY")
        self.assertFalse(payload["campaign_present"])
        self.assertFalse(payload["completion_present"])
        self.assertEqual(payload["state_sha256"], INTERLOCK.ZERO_HASH)
        self.assertTrue(payload["durable_content_validated"])
        self.assertTrue(payload["complete_chain_validated"])
        self.assertFalse(payload["device_commands_authorized"])

    def test_parked_complete_receipt_is_exact_and_non_authorizing(self):
        payload = INTERLOCK.model_scan_payload("PARKED_COMPLETE")
        self.assertTrue(payload["campaign_present"])
        self.assertTrue(payload["completion_present"])
        self.assertTrue(payload["campaign_parked"])
        self.assertNotEqual(payload["state_sha256"], INTERLOCK.ZERO_HASH)
        self.assertFalse(payload["replay_authorized"])
        self.assertFalse(payload["finalizer_resume_authorized"])

    def test_both_allowlisted_states_enter_only_fixture_claim_window(self):
        with TemporaryInterlockRoots() as roots:
            for status_value in sorted(INTERLOCK.ALLOWED_START_STATES):
                with self.subTest(status=status_value):
                    scan = INTERLOCK.model_verified_scan(status_value)
                    with INTERLOCK._fixture_new_start_slot(
                        roots.descriptors,
                        roots.shared_descriptor,
                        scan,
                    ) as lease:
                        decision = lease.decision()
                        self.assertEqual(decision["campaign_state"], status_value)
                        self.assertTrue(decision["leaf_directory_flock_held"])
                        self.assertFalse(
                            decision["new_start_authorized_by_live_contract"]
                        )
                        self.assertFalse(decision["device_commands_authorized"])
                        self.assertFalse(decision["live_authority"])

    def test_every_blocked_state_fails_closed_after_lock(self):
        with TemporaryInterlockRoots() as roots:
            for status_value in sorted(INTERLOCK.BLOCKED_STATES):
                with self.subTest(status=status_value):
                    with self.assertRaisesRegex(
                        INTERLOCK.StartInterlockV1Error,
                        "blocks every new connected start",
                    ):
                        with INTERLOCK._fixture_new_start_slot(
                            roots.descriptors,
                            roots.shared_descriptor,
                            INTERLOCK.model_verified_scan(status_value),
                        ):
                            self.fail("blocked state entered a start slot")

    def test_empty_flag_drift_is_rejected(self):
        changes = {
            "durable_content_validated": False,
            "campaign_present": True,
            "completion_present": True,
            "campaign_parked": True,
            "complete_chain_validated": False,
            "expired": True,
            "incomplete": True,
            "malformed": True,
            "state_sha256": "3" * 64,
        }
        for key, replacement in changes.items():
            with self.subTest(key=key):
                payload = INTERLOCK.model_scan_payload("EMPTY")
                payload[key] = replacement
                with self.assertRaisesRegex(
                    INTERLOCK.StartInterlockV1Error,
                    "allowlisted interlock state is not exact",
                ):
                    INTERLOCK.validate_scan_payload(payload)

    def test_parked_complete_flag_drift_is_rejected(self):
        changes = {
            "durable_content_validated": False,
            "campaign_present": False,
            "completion_present": False,
            "campaign_parked": False,
            "complete_chain_validated": False,
            "expired": True,
            "incomplete": True,
            "malformed": True,
            "state_sha256": INTERLOCK.ZERO_HASH,
        }
        for key, replacement in changes.items():
            with self.subTest(key=key):
                payload = INTERLOCK.model_scan_payload("PARKED_COMPLETE")
                payload[key] = replacement
                with self.assertRaisesRegex(
                    INTERLOCK.StartInterlockV1Error,
                    "allowlisted interlock state is not exact",
                ):
                    INTERLOCK.validate_scan_payload(payload)

    def test_target_drift_is_rejected(self):
        payload = INTERLOCK.model_scan_payload("EMPTY")
        payload["target"]["model"] = "SM-S906N"
        with self.assertRaisesRegex(
            INTERLOCK.StartInterlockV1Error,
            "target differs",
        ):
            INTERLOCK.validate_scan_payload(payload)

    def test_source_identity_drift_is_rejected(self):
        payload = INTERLOCK.model_scan_payload("EMPTY")
        payload["source_identities"]["campaign_model"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(
            INTERLOCK.StartInterlockV1Error,
            "source identities differ",
        ):
            INTERLOCK.validate_scan_payload(payload)

    def test_authority_bits_must_remain_false(self):
        for key in (
            "device_commands_authorized",
            "replay_authorized",
            "finalizer_resume_authorized",
        ):
            with self.subTest(key=key):
                payload = INTERLOCK.model_scan_payload("PARKED_COMPLETE")
                payload[key] = True
                with self.assertRaisesRegex(
                    INTERLOCK.StartInterlockV1Error,
                    "allowlisted interlock state is not exact",
                ):
                    INTERLOCK.validate_scan_payload(payload)

    def test_strict_boolean_fields_reject_integer_substitution(self):
        payload = INTERLOCK.model_scan_payload("EMPTY")
        payload["expired"] = 0
        with self.assertRaisesRegex(
            INTERLOCK.StartInterlockV1Error,
            "is not strict bool",
        ):
            INTERLOCK.validate_scan_payload(payload)

    def test_state_digest_rejects_noncanonical_hex(self):
        for replacement in ("A" * 64, "0" * 63, True, 0):
            with self.subTest(replacement=replacement):
                payload = INTERLOCK.model_scan_payload("EMPTY")
                payload["state_sha256"] = replacement
                with self.assertRaisesRegex(
                    INTERLOCK.StartInterlockV1Error,
                    "not lowercase SHA-256",
                ):
                    INTERLOCK.validate_scan_payload(payload)

    def test_schema_and_exact_key_set_are_enforced(self):
        payload = INTERLOCK.model_scan_payload("EMPTY")
        payload["schema"] = "wrong"
        with self.assertRaisesRegex(INTERLOCK.StartInterlockV1Error, "schema differs"):
            INTERLOCK.validate_scan_payload(payload)
        for mutation in ("missing", "extra"):
            with self.subTest(mutation=mutation):
                payload = INTERLOCK.model_scan_payload("EMPTY")
                if mutation == "missing":
                    del payload["campaign_present"]
                else:
                    payload["extra"] = False
                with self.assertRaisesRegex(
                    INTERLOCK.StartInterlockV1Error,
                    "keys differ",
                ):
                    INTERLOCK.validate_scan_payload(payload)

    def test_unknown_status_token_is_rejected(self):
        payload = INTERLOCK.model_scan_payload("EMPTY")
        payload["status"] = "TERMINAL"
        with self.assertRaisesRegex(
            INTERLOCK.StartInterlockV1Error,
            "status differs",
        ):
            INTERLOCK.validate_scan_payload(payload)

    def test_sealed_scan_rejects_raw_or_payload_mutation(self):
        scan = INTERLOCK.model_verified_scan("EMPTY")
        scan.raw = b"{}\n"
        with self.assertRaisesRegex(
            INTERLOCK.StartInterlockV1Error,
            "bytes changed",
        ):
            INTERLOCK._require_fixture_scan(scan)
        scan = INTERLOCK.model_verified_scan("PARKED_COMPLETE")
        scan.payload["expired"] = True
        with self.assertRaises(INTERLOCK.StartInterlockV1Error):
            INTERLOCK._require_fixture_scan(scan)

    def test_scan_seal_cannot_be_replaced_and_receipt_is_not_serializable(self):
        payload = INTERLOCK.model_scan_payload("EMPTY")
        with self.assertRaisesRegex(
            INTERLOCK.StartInterlockV1Error,
            "seal differs",
        ):
            INTERLOCK._FixtureVerifiedScan(payload, object())
        with self.assertRaises(TypeError):
            pickle.dumps(INTERLOCK.model_verified_scan("EMPTY"))

    def test_fixture_lease_expires_at_context_exit(self):
        with TemporaryInterlockRoots() as roots:
            with INTERLOCK._fixture_new_start_slot(
                roots.descriptors,
                roots.shared_descriptor,
                INTERLOCK.model_verified_scan("EMPTY"),
            ) as lease:
                lease.decision()
                with self.assertRaises(TypeError):
                    pickle.dumps(lease)
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "no longer held",
            ):
                lease.decision()


class StartInterlockFilesystemAndRaceTests(unittest.TestCase):
    def test_exact_temp_root_descriptor_set_is_accepted(self):
        with TemporaryInterlockRoots() as roots:
            metadata = INTERLOCK.validate_held_roots(roots.descriptors)
            self.assertEqual(set(metadata), {"base", "evidence", "leaf"})
            self.assertEqual(
                len({(item.st_dev, item.st_ino) for item in metadata.values()}),
                3,
            )

    def test_missing_extra_and_duplicate_root_descriptors_are_rejected(self):
        with TemporaryInterlockRoots() as roots:
            missing = dict(roots.descriptors)
            del missing["evidence"]
            extra = dict(roots.descriptors)
            extra["other"] = roots.descriptors["base"]
            duplicate = dict(roots.descriptors)
            duplicate["evidence"] = roots.descriptors["base"]
            for label, descriptors in (
                ("missing", missing),
                ("extra", extra),
                ("duplicate", duplicate),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(INTERLOCK.StartInterlockV1Error):
                        INTERLOCK.validate_held_roots(descriptors)

    def test_wrong_private_root_mode_is_rejected(self):
        with TemporaryInterlockRoots() as roots:
            roots.paths["evidence"].chmod(0o755)
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "identity differs",
            ):
                INTERLOCK.validate_held_roots(roots.descriptors)

    def test_wrong_shared_guard_parent_mode_is_rejected(self):
        with TemporaryInterlockRoots() as roots:
            roots.shared_path.chmod(0o700)
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "shared action guard parent identity differs",
            ):
                with INTERLOCK._fixture_new_start_slot(
                    roots.descriptors,
                    roots.shared_descriptor,
                    INTERLOCK.model_verified_scan("EMPTY"),
                ):
                    self.fail("wrong shared-parent mode entered a start slot")

    def test_componentwise_opener_accepts_only_expected_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "exact"
            path.mkdir()
            path.chmod(0o700)
            descriptor = INTERLOCK._open_absolute_directory(
                path,
                "temp exact directory",
                expected_mode=0o700,
            )
            try:
                self.assertTrue(stat.S_ISDIR(os.fstat(descriptor).st_mode))
            finally:
                os.close(descriptor)
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "identity differs",
            ):
                INTERLOCK._open_absolute_directory(
                    path,
                    "temp wrong-mode directory",
                    expected_mode=0o775,
                )

    def test_componentwise_opener_rejects_symlink_component(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            child = real / "child"
            real.mkdir()
            child.mkdir()
            child.chmod(0o700)
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaises(OSError):
                INTERLOCK._open_absolute_directory(
                    alias / "child",
                    "temp symlinked directory",
                    expected_mode=0o700,
                )

    def test_shared_guard_absence_is_checked_only_under_held_lock_order(self):
        function_source = inspect.getsource(INTERLOCK._fixture_new_start_slot)
        lock_index = function_source.index("fcntl.flock(")
        scan_index = function_source.index("_require_fixture_scan(scan)")
        guard_index = function_source.index("_require_shared_guard_absent_at(")
        self.assertLess(lock_index, scan_index)
        self.assertLess(scan_index, guard_index)

    def test_existing_regular_shared_guard_blocks_new_start(self):
        with TemporaryInterlockRoots() as roots:
            roots.create_guard("regular")
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "already present",
            ):
                with INTERLOCK._fixture_new_start_slot(
                    roots.descriptors,
                    roots.shared_descriptor,
                    INTERLOCK.model_verified_scan("EMPTY"),
                ):
                    self.fail("existing shared guard admitted a new start")

    def test_symlink_and_fifo_shared_guard_nodes_block_without_open(self):
        for node_type in ("symlink", "fifo"):
            with self.subTest(node_type=node_type):
                with TemporaryInterlockRoots() as roots:
                    roots.create_guard(node_type)
                    started = time.monotonic()
                    with self.assertRaisesRegex(
                        INTERLOCK.StartInterlockV1Error,
                        "already present",
                    ):
                        with INTERLOCK._fixture_new_start_slot(
                            roots.descriptors,
                            roots.shared_descriptor,
                            INTERLOCK.model_verified_scan("PARKED_COMPLETE"),
                        ):
                            self.fail("special guard node admitted a new start")
                    self.assertLess(time.monotonic() - started, 1.0)

    def test_leaf_flock_is_exclusive_against_another_process(self):
        with TemporaryInterlockRoots() as roots:
            with INTERLOCK._fixture_new_start_slot(
                roots.descriptors,
                roots.shared_descriptor,
                INTERLOCK.model_verified_scan("EMPTY"),
            ) as lease:
                self.assertTrue(lease.decision()["leaf_directory_flock_held"])
                self.assertEqual(child_lock_result(roots.paths["leaf"]), "BUSY")
            self.assertEqual(child_lock_result(roots.paths["leaf"]), "ACQUIRED")

    def test_external_leaf_lock_contention_is_nonblocking(self):
        with TemporaryInterlockRoots() as roots:
            with child_holds_lock(roots.paths["leaf"]):
                started = time.monotonic()
                with self.assertRaisesRegex(
                    INTERLOCK.StartInterlockV1Error,
                    "interlock is busy",
                ):
                    with INTERLOCK._fixture_new_start_slot(
                        roots.descriptors,
                        roots.shared_descriptor,
                        INTERLOCK.model_verified_scan("EMPTY"),
                    ):
                        self.fail("contended interlock entered a start slot")
                self.assertLess(time.monotonic() - started, 1.0)

    def test_body_exception_releases_leaf_lock(self):
        with TemporaryInterlockRoots() as roots:
            with self.assertRaisesRegex(ValueError, "fixture body cut"):
                with INTERLOCK._fixture_new_start_slot(
                    roots.descriptors,
                    roots.shared_descriptor,
                    INTERLOCK.model_verified_scan("EMPTY"),
                ):
                    raise ValueError("fixture body cut")
            self.assertEqual(child_lock_result(roots.paths["leaf"]), "ACQUIRED")

    def test_leaf_identity_drift_blocks_exit_and_releases_lock(self):
        with TemporaryInterlockRoots() as roots:
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "leaf root changed before unlock",
            ):
                with INTERLOCK._fixture_new_start_slot(
                    roots.descriptors,
                    roots.shared_descriptor,
                    INTERLOCK.model_verified_scan("EMPTY"),
                ):
                    roots.paths["leaf"].chmod(0o711)
            self.assertEqual(child_lock_result(roots.paths["leaf"]), "ACQUIRED")

    def test_guard_appearance_during_claim_window_fails_before_unlock(self):
        with TemporaryInterlockRoots() as roots:
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "already present",
            ):
                with INTERLOCK._fixture_new_start_slot(
                    roots.descriptors,
                    roots.shared_descriptor,
                    INTERLOCK.model_verified_scan("PARKED_COMPLETE"),
                ):
                    roots.create_guard("regular")
            self.assertEqual(child_lock_result(roots.paths["leaf"]), "ACQUIRED")

    def test_scan_failure_releases_leaf_lock(self):
        with TemporaryInterlockRoots() as roots:
            with self.assertRaisesRegex(
                INTERLOCK.StartInterlockV1Error,
                "blocks every new connected start",
            ):
                with INTERLOCK._fixture_new_start_slot(
                    roots.descriptors,
                    roots.shared_descriptor,
                    INTERLOCK.model_verified_scan("EXPIRED"),
                ):
                    self.fail("expired campaign entered a start slot")
            self.assertEqual(child_lock_result(roots.paths["leaf"]), "ACQUIRED")


if __name__ == "__main__":
    unittest.main()
