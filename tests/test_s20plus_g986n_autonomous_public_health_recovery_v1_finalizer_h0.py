import ast
import copy
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
FINALIZER = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py"
)
LOADER = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py"
)
EVIDENCE_TEST = (
    ROOT / "tests/test_s20plus_g986n_autonomous_public_health_evidence_h0.py"
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load("s20plus_recovery_finalizer_h0_tested", FINALIZER)
L = load("s20plus_recovery_loader_h0_for_finalizer", LOADER)
ET = load("s20plus_evidence_fixture_for_finalizer", EVIDENCE_TEST)
E = ET.M
F = ET.Fixture


def mkdir(path):
    os.mkdir(path, 0o700)
    os.chmod(path, 0o700)


def write_file(path, payload, mode=0o400):
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        mode,
    )
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def deterministic_bundle():
    allocation, accounting, accounting_raw = F.accounting_opening()
    state = E.initial_protocol_state(accounting, accounting_raw)
    lease, lease_raw, _, _ = F.lease(accounting, accounting_raw, state)
    intent = M.model_exact_intent_mirror(
        lease, lease_raw, accounting, lease["issued_at"]
    )
    intent_raw = M.canonical_bytes(intent)
    records = F.records(intent)
    receipts = E.build_command_receipts(intent_raw, records)
    health = E.derive_health_result(intent, records, receipts)
    evidence_files = {"health.json": E.canonical_bytes(health)}
    for ordinal, (record, receipt) in enumerate(
        zip(records, receipts, strict=True), 1
    ):
        evidence_files[f"cmd-{ordinal:02d}.stdout.bin"] = record["stdout"]
        evidence_files[f"cmd-{ordinal:02d}.stderr.bin"] = record["stderr"]
        evidence_files[f"cmd-{ordinal:02d}.receipt.json"] = receipt[1]
    result = M.model_deterministic_read_result(
        intent,
        intent_raw,
        lease,
        lease_raw,
        accounting,
        accounting_raw,
        allocation["guard_raw"],
        allocation["opening_raw"],
        allocation["session_raw"],
        evidence_files,
    )
    result_raw = M.canonical_bytes(result)
    completion = M.model_parked_completion(
        result, result_raw, result["completed_at"]
    )
    return {
        "allocation": allocation,
        "accounting": accounting,
        "accounting_raw": accounting_raw,
        "state": state,
        "lease": lease,
        "lease_raw": lease_raw,
        "intent": intent,
        "intent_raw": intent_raw,
        "records": records,
        "receipts": receipts,
        "health": health,
        "evidence_files": evidence_files,
        "result": result,
        "result_raw": result_raw,
        "completion": completion,
        "completion_raw": M.canonical_bytes(completion),
    }


def tree_snapshot(*roots):
    result = []
    for root in roots:
        for path in sorted((root, *root.rglob("*"))):
            info = os.stat(path, follow_symlinks=False)
            relative = "." if path == root else str(path.relative_to(root))
            if stat.S_ISREG(info.st_mode):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            elif stat.S_ISLNK(info.st_mode):
                digest = os.readlink(path)
            else:
                digest = None
            result.append(
                (
                    str(root),
                    relative,
                    stat.S_IFMT(info.st_mode),
                    stat.S_IMODE(info.st_mode),
                    info.st_nlink,
                    info.st_size,
                    digest,
                )
            )
    return result


class Tree:
    def __init__(self, stage="lease"):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.base = self.root / "base"
        self.evidence = self.root / "evidence"
        self.leaf = self.root / "leaf"
        for path in (self.base, self.evidence, self.leaf):
            mkdir(path)
        write_file(self.leaf / M.LOCK_NAME, b"", 0o600)
        self.recovery = self.leaf / M.RECOVERY_DIRECTORY
        mkdir(self.recovery)
        self.core = FINALIZER.read_bytes()
        self.manifest = M.canonical_bytes(M.build_manifest(self.core))
        write_file(self.recovery / M.RECOVERY_CORE_NAME, self.core)
        write_file(self.recovery / M.RECOVERY_MANIFEST_NAME, self.manifest)
        self.bundle = deterministic_bundle()
        self._populate(stage)
        self.fds = {
            "base": os.open(self.base, os.O_RDONLY | os.O_DIRECTORY),
            "evidence": os.open(self.evidence, os.O_RDONLY | os.O_DIRECTORY),
            "leaf": os.open(self.leaf, os.O_RDONLY | os.O_DIRECTORY),
            "recovery": os.open(self.recovery, os.O_RDONLY | os.O_DIRECTORY),
        }
        self.namespace, self.capability, loaded_manifest = (
            L._load_verified_namespace_at(self.fds["recovery"])
        )
        assert loaded_manifest == self.manifest

    def _populate(self, stage):
        bundle = self.bundle
        allocation = bundle["allocation"]
        campaign_id = bundle["accounting"]["campaign_id"]
        session_id = bundle["accounting"]["session_id"]
        mkdir(self.base / "campaigns")
        campaign = self.base / "campaigns" / campaign_id
        mkdir(campaign)
        session = campaign / "session"
        mkdir(session)
        write_file(self.base / "active-campaign.json", allocation["guard_raw"])
        write_file(session / "opening.json", allocation["opening_raw"])
        write_file(
            session / "session-opening.json", allocation["session_raw"]
        )

        mkdir(self.evidence / "campaigns")
        evidence_campaign = self.evidence / "campaigns" / (
            "campaign-" + hashlib.sha256(campaign_id.encode()).hexdigest()
        )
        mkdir(evidence_campaign)
        sessions = evidence_campaign / "sessions"
        mkdir(sessions)
        self.evidence_session = sessions / (
            "session-" + hashlib.sha256(session_id.encode()).hexdigest()
        )
        mkdir(self.evidence_session)
        write_file(
            self.evidence_session / "accounting-opening.json",
            bundle["accounting_raw"],
        )
        write_file(
            self.leaf / "public-health-read-lease-000001.json",
            bundle["lease_raw"],
        )

        levels = {
            "lease": 0,
            "raw_without_mirror": 1,
            "intent": 2,
            "partial": 3,
            "returns": 4,
            "health": 5,
            "result": 6,
            "complete": 7,
        }
        level = levels[stage]
        if level >= 2:
            write_file(
                self.evidence_session / "read-intent-000001.json",
                bundle["intent_raw"],
            )
        if level in (1, 3, 4, 5, 6, 7):
            read = self.evidence_session / "read-000001"
            mkdir(read)
            count = {1: 1, 3: 4, 4: 18, 5: 19, 6: 19, 7: 19}[level]
            for name in M.PUBLICATION_ORDER[:count]:
                write_file(read / name, bundle["evidence_files"][name])
        if level >= 6:
            write_file(
                self.evidence_session / "read-result-000001.json",
                bundle["result_raw"],
            )
        if level >= 7:
            write_file(
                self.leaf / "public-health-read-complete-000001.json",
                bundle["completion_raw"],
            )

    def _arguments(self):
        return (
            self.capability,
            self.fds["base"],
            self.fds["evidence"],
            self.fds["leaf"],
            self.manifest,
        )

    def finalize(self):
        with L._ExistingCoordinatorLock(self.fds["leaf"]):
            return self.namespace["_finalize_one_node_model"](*self._arguments())

    def reemit(self):
        with L._ExistingCoordinatorLock(self.fds["leaf"]):
            return self.namespace["_reemit_terminal_model"](*self._arguments())

    def scan(self):
        with L._ExistingCoordinatorLock(self.fds["leaf"]):
            state = self.namespace["_scan_held_state"](*self._arguments())
            try:
                return self.namespace["_public_scan_summary"](state)
            finally:
                self.namespace["_close_held_scan"](state)

    def close(self):
        for descriptor in self.fds.values():
            os.close(descriptor)
        self.temporary.cleanup()


class RecoveryFinalizerH0Test(unittest.TestCase):
    def test_01_plan_is_implemented_but_every_gate_is_false(self):
        plan = M.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_PUBLIC_HEALTH_RECOVERY_V1_FINALIZER_PASS_GO_NOT_ACTIVE",
        )
        self.assertTrue(plan["self_contained_finalizer_implemented"])
        self.assertTrue(plan["permanent_h0_only"])
        for key in (
            "recovery_v1_qualified",
            "scanner_active",
            "writer_active",
            "finalizer_publication_active",
            "finalizer_active",
            "reemit_active",
            "manifest_active",
            "contract_active",
            "live_authority",
        ):
            self.assertIs(plan[key], False)
        self.assertFalse(
            plan["future_reserved_completed_closure"][
                "current_scanner_accepts_future_opening_and_binding"
            ]
        )

    def test_02_cli_and_direct_operations_are_inactive(self):
        good = subprocess.run(
            [sys.executable, str(FINALIZER), "--render-plan"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(json.loads(good.stdout)["cli"], ["--render-plan"])
        for args in ([], ["--finalize"], ["--reemit"]):
            bad = subprocess.run(
                [sys.executable, str(FINALIZER), *args],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(bad.returncode, 0)
        with self.assertRaises(M.RecoveryV1Error):
            M.finalize_zero_command()
        with self.assertRaises(M.RecoveryV1Error):
            M.reemit_terminal()

    def test_03_no_device_network_or_runtime_oracle_backend(self):
        source = FINALIZER.read_bytes()
        tree = ast.parse(source.decode())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(
            imports.isdisjoint(
                {"subprocess", "socket", "requests", "urllib", "importlib", "runpy"}
            )
        )
        for token in (b"Popen", b"fastboot", b"odin4", b"adb shell"):
            self.assertNotIn(token, source)

    def test_04_loader_capability_and_manifest_bytes_are_both_required(self):
        tree = Tree("lease")
        try:
            arguments = list(tree._arguments())
            arguments[0] = object()
            with self.assertRaises(tree.namespace["RecoveryV1Error"]):
                tree.namespace["_scan_held_state"](*arguments)
            arguments = list(tree._arguments())
            arguments[-1] += b"x"
            with self.assertRaises(tree.namespace["RecoveryV1Error"]):
                tree.namespace["_scan_held_state"](*arguments)
        finally:
            tree.close()

    def test_05_deterministic_mirror_uses_only_lease_issued_at(self):
        bundle = deterministic_bundle()
        intent = bundle["intent"]
        self.assertEqual(intent["mirrored_at"], bundle["lease"]["issued_at"])
        self.assertEqual(intent["lease_observed_at"], bundle["lease"]["issued_at"])
        changed = M.model_exact_intent_mirror(
            bundle["lease"],
            bundle["lease_raw"],
            bundle["accounting"],
            bundle["lease"]["issued_at"] + 1,
        )
        with self.assertRaises(M.RecoveryV1Error):
            M._require_deterministic_chain(
                intent=changed,
                intent_raw=M.canonical_bytes(changed),
                lease=bundle["lease"],
                lease_raw=bundle["lease_raw"],
                accounting=bundle["accounting"],
                accounting_raw=bundle["accounting_raw"],
                guard_raw=bundle["allocation"]["guard_raw"],
                opening_raw=bundle["allocation"]["opening_raw"],
                session_raw=bundle["allocation"]["session_raw"],
                evidence_files={},
                result=None,
                result_raw=None,
                completion=None,
                completion_raw=None,
            )

    def test_06_result_uses_receipt_06_lower_bound_and_cut_time_is_unproved(self):
        bundle = deterministic_bundle()
        receipt = M.parse_canonical_json(
            bundle["evidence_files"]["cmd-06.receipt.json"],
            "receipt",
        )
        expected = receipt["receipt_published_at"]
        self.assertEqual(bundle["result"]["completed_at"], expected)
        self.assertIsNone(bundle["result"]["reporting_cut_at"])
        self.assertFalse(bundle["result"]["reporting_after_expiry_or_drift"])
        self.assertEqual(bundle["completion"]["completed_at"], expected)

    def test_07_raw_without_mirror_is_rejected_with_zero_change(self):
        tree = Tree("raw_without_mirror")
        try:
            before = tree_snapshot(tree.base, tree.evidence, tree.leaf)
            with self.assertRaises(tree.namespace["RecoveryV1Error"]):
                tree.finalize()
            self.assertEqual(
                tree_snapshot(tree.base, tree.evidence, tree.leaf), before
            )
        finally:
            tree.close()

    def test_08_incomplete_return_prefix_parks_without_write(self):
        tree = Tree("partial")
        try:
            before = tree_snapshot(tree.base, tree.evidence, tree.leaf)
            result = tree.finalize()
            self.assertIsNone(result["attempted_operation"])
            self.assertIsNone(result["publication"])
            self.assertTrue(result["campaign_parked"])
            self.assertEqual(
                tree_snapshot(tree.base, tree.evidence, tree.leaf), before
            )
        finally:
            tree.close()

    def test_09_one_invocation_publishes_only_mirror(self):
        tree = Tree("lease")
        try:
            result = tree.finalize()
            self.assertEqual(result["attempted_operation"], "publish-exact-mirror")
            self.assertEqual(result["publication"], "PUBLISHED")
            self.assertTrue(
                (tree.evidence_session / "read-intent-000001.json").is_file()
            )
            self.assertFalse((tree.evidence_session / "read-000001").exists())
        finally:
            tree.close()

    def test_10_one_invocation_publishes_only_health(self):
        tree = Tree("returns")
        try:
            result = tree.finalize()
            self.assertEqual(
                result["attempted_operation"], "publish-derived-health"
            )
            self.assertEqual(result["publication"], "PUBLISHED")
            self.assertEqual(
                (tree.evidence_session / "read-000001" / "health.json").read_bytes(),
                tree.bundle["evidence_files"]["health.json"],
            )
            self.assertFalse(
                (tree.evidence_session / "read-result-000001.json").exists()
            )
        finally:
            tree.close()

    def test_11_one_invocation_publishes_only_result(self):
        tree = Tree("health")
        try:
            result = tree.finalize()
            self.assertEqual(
                result["attempted_operation"], "publish-deterministic-result"
            )
            self.assertEqual(
                (tree.evidence_session / "read-result-000001.json").read_bytes(),
                tree.bundle["result_raw"],
            )
            self.assertFalse(
                (tree.leaf / "public-health-read-complete-000001.json").exists()
            )
        finally:
            tree.close()

    def test_12_one_invocation_publishes_only_parked_completion(self):
        tree = Tree("result")
        try:
            result = tree.finalize()
            self.assertEqual(
                result["attempted_operation"], "publish-parked-completion"
            )
            self.assertEqual(
                (
                    tree.leaf / "public-health-read-complete-000001.json"
                ).read_bytes(),
                tree.bundle["completion_raw"],
            )
            self.assertEqual(
                result["next_operation"],
                "reemit-sanitized-repeatable-terminal",
            )
            self.assertFalse(result["controls_unblocked"])
            self.assertFalse(result["terminal_unblocked"])
        finally:
            tree.close()

    def test_13_reemit_is_sanitized_repeatable_and_zero_filesystem_write(self):
        tree = Tree("complete")
        try:
            before = tree_snapshot(tree.base, tree.evidence, tree.leaf)
            first = tree.reemit()
            second = tree.reemit()
            self.assertEqual(first, second)
            terminal = json.loads(first)
            self.assertEqual(terminal["status"], "PARKED_COMPLETE")
            self.assertNotIn(tree.bundle["accounting"]["campaign_id"].encode(), first)
            self.assertNotIn(tree.bundle["accounting"]["session_id"].encode(), first)
            self.assertFalse(terminal["replay_authorized"])
            self.assertTrue(terminal["campaign_parked"])
            self.assertEqual(
                tree_snapshot(tree.base, tree.evidence, tree.leaf), before
            )
        finally:
            tree.close()

    def test_14_legacy_valid_but_nondeterministic_result_is_rejected(self):
        tree = Tree("health")
        try:
            bundle = tree.bundle
            legacy = E.model_validated_read_result(
                bundle["accounting"],
                bundle["accounting_raw"],
                bundle["state"],
                bundle["lease"],
                bundle["lease_raw"],
                bundle["intent"]["mirrored_at"],
                bundle["intent"],
                bundle["intent_raw"],
                bundle["records"],
                bundle["receipts"],
                1_040,
                None,
            )
            write_file(
                tree.evidence_session / "read-result-000001.json",
                E.canonical_bytes(legacy),
            )
            with self.assertRaises(tree.namespace["RecoveryV1Error"]):
                tree.scan()
        finally:
            tree.close()

    def test_15_existing_health_result_completion_mismatch_rejects(self):
        variants = ("health", "result", "completion")
        for variant in variants:
            tree = Tree("complete")
            try:
                if variant == "health":
                    path = tree.evidence_session / "read-000001" / "health.json"
                elif variant == "result":
                    path = tree.evidence_session / "read-result-000001.json"
                else:
                    path = tree.leaf / "public-health-read-complete-000001.json"
                os.chmod(path, 0o600)
                with path.open("ab") as stream:
                    stream.write(b"x")
                os.chmod(path, 0o400)
                with self.assertRaises(tree.namespace["RecoveryV1Error"]):
                    tree.scan()
            finally:
                tree.close()

    def test_16_structural_aggregate_is_actually_enforced(self):
        bundle = deterministic_bundle()
        raws = {
            "active-campaign.json": bundle["allocation"]["guard_raw"],
            "opening.json": bundle["allocation"]["opening_raw"],
            "session-opening.json": bundle["allocation"]["session_raw"],
            "accounting-opening.json": bundle["accounting_raw"],
            "public-health-read-lease-000001.json": bundle["lease_raw"],
            "read-intent-000001.json": bundle["intent_raw"],
            "read-result-000001.json": bundle["result_raw"],
            "public-health-read-complete-000001.json": bundle["completion_raw"],
        }
        proof = M.validate_structural_raws(raws)
        self.assertLessEqual(proof["actual_bytes"], M.STRUCTURAL_MAX_BYTES)
        oversized = {
            name: M.canonical_bytes({"x": "a" * (cap - 16)})
            for name, cap in M.STRUCTURAL_CAPS.items()
        }
        with self.assertRaises(M.RecoveryV1Error):
            M.validate_structural_raws(oversized)

    def test_17_publication_allowlist_and_caps_are_exact(self):
        self.assertEqual(
            {
                "read-intent-000001.json": 4 * 1024,
                "health.json": 64 * 1024,
                "read-result-000001.json": 8 * 1024,
                "public-health-read-complete-000001.json": 4 * 1024,
            },
            {
                key: M.PUBLISH_CAPS[key]
                for key in (
                    "read-intent-000001.json",
                    "health.json",
                    "read-result-000001.json",
                    "public-health-read-complete-000001.json",
                )
            },
        )
        self.assertEqual(M.COMPLETED_TOTAL_MAX_BYTES, 1_441_792)
        self.assertEqual(M.COMPLETED_TOTAL_FILE_COUNT, 52)
        self.assertEqual(M.EVIDENCE_PROOF_MAX_BYTES, 507_904)

    def test_18_normalized_identity_masks_only_reviewed_activation_fields(self):
        source = FINALIZER.read_bytes()
        self.assertEqual(
            M.normalized_self_sha256(source),
            M.EXPECTED_RECOVERY_NORMALIZED_SHA256,
        )
        status = source.replace(
            b' STATUS = "never"', b' STATUS = "changed"'
        )
        self.assertEqual(status, source)
        changed_status = source.replace(
            b'STATUS = "H0_PUBLIC_HEALTH_RECOVERY_V1_FINALIZER_PASS_GO_NOT_ACTIVE"',
            b'STATUS = "H0_REVIEWED_STATUS"',
        )
        self.assertEqual(
            M.normalized_self_sha256(changed_status),
            M.EXPECTED_RECOVERY_NORMALIZED_SHA256,
        )
        changed_gate = source.replace(
            b"RECOVERY_FINALIZER_ACTIVE = False",
            b"RECOVERY_FINALIZER_ACTIVE = True",
        )
        self.assertEqual(
            M.normalized_self_sha256(changed_gate),
            M.EXPECTED_RECOVERY_NORMALIZED_SHA256,
        )
        changed_logic = source.replace(
            b'"campaign_parked": True,', b'"campaign_parked": False,', 1
        )
        self.assertNotEqual(
            M.normalized_self_sha256(changed_logic),
            M.EXPECTED_RECOVERY_NORMALIZED_SHA256,
        )

    def test_19_bool_and_timestamp_tamper_remains_rejected(self):
        bundle = deterministic_bundle()
        for key, value in (
            ("completed_at", True),
            ("reporting_cut_at", bundle["result"]["completed_at"] + 1),
            ("outcome_proven", 1),
        ):
            result = copy.deepcopy(bundle["result"])
            result[key] = value
            with self.assertRaises(M.RecoveryV1Error):
                M._require_deterministic_chain(
                    intent=bundle["intent"],
                    intent_raw=bundle["intent_raw"],
                    lease=bundle["lease"],
                    lease_raw=bundle["lease_raw"],
                    accounting=bundle["accounting"],
                    accounting_raw=bundle["accounting_raw"],
                    guard_raw=bundle["allocation"]["guard_raw"],
                    opening_raw=bundle["allocation"]["opening_raw"],
                    session_raw=bundle["allocation"]["session_raw"],
                    evidence_files=bundle["evidence_files"],
                    result=result,
                    result_raw=M.canonical_bytes(result),
                    completion=None,
                    completion_raw=None,
                )

    def test_20_public_operational_loader_functions_still_refuse(self):
        tree = Tree("complete")
        try:
            with self.assertRaises(tree.namespace["RecoveryV1Error"]):
                tree.namespace["loader_finalize_zero_command"](*tree._arguments())
            with self.assertRaises(tree.namespace["RecoveryV1Error"]):
                tree.namespace["loader_reemit_terminal"](*tree._arguments())
        finally:
            tree.close()

    def test_21_atomic_file_fsync_failure_leaves_no_final(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            name = "read-intent-000001.json"
            try:
                with mock.patch.object(
                    M.os, "fsync", side_effect=OSError(errno.EIO, "cut")
                ):
                    with self.assertRaises(M.RecoveryV1Error):
                        M._atomic_publish_at(parent, name, b"{}\n")
                self.assertFalse((Path(temporary) / name).exists())
            finally:
                os.close(parent)

    def test_22_atomic_directory_fsync_cut_retries_exact_idempotently(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            name = "read-intent-000001.json"
            payload = b"{}\n"
            original = os.fsync
            calls = 0

            def cut(descriptor):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError(errno.EIO, "directory cut")
                return original(descriptor)

            try:
                with mock.patch.object(M.os, "fsync", side_effect=cut):
                    with self.assertRaises(M.RecoveryV1Error):
                        M._atomic_publish_at(parent, name, payload)
                self.assertEqual((Path(temporary) / name).read_bytes(), payload)
                self.assertEqual(
                    M._atomic_publish_at(parent, name, payload),
                    "EXACT_ALREADY_PRESENT",
                )
            finally:
                os.close(parent)

    def test_23_atomic_eexist_accepts_exact_and_rejects_different(self):
        for exact in (True, False):
            with tempfile.TemporaryDirectory() as temporary:
                os.chmod(temporary, 0o700)
                parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
                name = "read-intent-000001.json"
                payload = b"{}\n"

                def race(source_fd, parent_fd, final_name):
                    write_file(
                        Path(temporary) / final_name,
                        payload if exact else b'{"different":true}\n',
                    )
                    raise OSError(errno.EEXIST, "race")

                try:
                    with mock.patch.object(
                        M, "_link_anonymous_tmpfile", side_effect=race
                    ):
                        if exact:
                            self.assertEqual(
                                M._atomic_publish_at(parent, name, payload),
                                "EXACT_RACE_PRESENT",
                            )
                        else:
                            with self.assertRaises(M.RecoveryV1Error):
                                M._atomic_publish_at(parent, name, payload)
                finally:
                    os.close(parent)

    def test_24_atomic_short_writes_complete_and_zero_write_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            original = os.write

            def short(descriptor, payload):
                return original(descriptor, payload[: max(1, len(payload) // 2)])

            try:
                with mock.patch.object(M.os, "write", side_effect=short):
                    self.assertEqual(
                        M._atomic_publish_at(
                            parent, "read-intent-000001.json", b"x" * 100
                        ),
                        "PUBLISHED",
                    )
            finally:
                os.close(parent)
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with mock.patch.object(M.os, "write", return_value=0):
                    with self.assertRaises(M.RecoveryV1Error):
                        M._atomic_publish_at(
                            parent, "read-intent-000001.json", b"x"
                        )
                self.assertFalse(
                    (Path(temporary) / "read-intent-000001.json").exists()
                )
            finally:
                os.close(parent)

    def test_25_atomic_existing_symlink_hardlink_and_fifo_reject(self):
        for variant in ("symlink", "hardlink", "fifo"):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                os.chmod(root, 0o700)
                name = "read-intent-000001.json"
                path = root / name
                if variant == "symlink":
                    write_file(root / "target", b"{}\n")
                    os.symlink(root / "target", path)
                elif variant == "hardlink":
                    write_file(path, b"{}\n")
                    os.link(path, root / "alias")
                else:
                    os.mkfifo(path, 0o400)
                parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    with self.assertRaises(M.RecoveryV1Error):
                        M._atomic_publish_at(parent, name, b"{}\n")
                finally:
                    os.close(parent)

    def test_26_seventeen_return_boundary_parks_without_health(self):
        tree = Tree("intent")
        try:
            read = tree.evidence_session / "read-000001"
            mkdir(read)
            for name in M.PUBLICATION_ORDER[:17]:
                write_file(read / name, tree.bundle["evidence_files"][name])
            before = tree_snapshot(tree.base, tree.evidence, tree.leaf)
            result = tree.finalize()
            self.assertIsNone(result["attempted_operation"])
            self.assertFalse((read / "health.json").exists())
            self.assertEqual(
                tree_snapshot(tree.base, tree.evidence, tree.leaf), before
            )
        finally:
            tree.close()


if __name__ == "__main__":
    unittest.main()
