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
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_v1.py"
)
EVIDENCE_TEST = ROOT / "tests/test_s20plus_g986n_autonomous_public_health_evidence_h0.py"

ORACLE_PATHS = {
    "base_coordinator": ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_research_coordinator_h0.py",
    "health": ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_health_h0.py",
    "inventory": ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_d0_inventory.py",
    "evidence_owner": ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_evidence_h0.py",
    "read_leaf": ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_coordinator_h0.py",
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load("s20plus_public_health_recovery_v1_tested", SCRIPT)
ET = load("s20plus_public_health_evidence_fixture_for_recovery", EVIDENCE_TEST)
E = ET.M
F = ET.Fixture


def reject(callable_, *args, **kwargs):
    with unittest.TestCase().assertRaises(M.RecoveryV1Error):
        callable_(*args, **kwargs)


def literal(path, name):
    tree = ast.parse(path.read_text())
    matches = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                matches.append(node.value)
    if len(matches) != 1:
        raise AssertionError(f"literal {name} is ambiguous")
    return ast.literal_eval(matches[0])


def bound_core_bytes():
    source = SCRIPT.read_bytes()
    bound = M.canonical_bytes(
        {
            "binding_complete": True,
            "normalized_sha256": "a" * 64,
            "schema": M.RUNNER_BINDING_SCHEMA,
            "status": "BOUND",
        }
    )
    old_line = (
        b"FUTURE_RUNNER_BINDING_JSON = "
        + repr(M.FUTURE_RUNNER_BINDING_JSON).encode("ascii")
        + b"\n"
    )
    new_line = b"FUTURE_RUNNER_BINDING_JSON = " + repr(bound).encode("ascii") + b"\n"
    if source.count(old_line) != 1:
        raise AssertionError("runner binding source line is not exact")
    return source.replace(old_line, new_line)


def oracle_bundle():
    allocation, opening, opening_raw = F.accounting_opening()
    state = E.initial_protocol_state(opening, opening_raw)
    lease, lease_raw, intent, intent_raw = F.lease(opening, opening_raw, state)
    records = F.records(intent)
    receipts = E.build_command_receipts(intent_raw, records)
    health = E.derive_health_result(intent, records, receipts)
    evidence_files = {"health.json": E.canonical_bytes(health)}
    for ordinal, (record, receipt) in enumerate(zip(records, receipts, strict=True), 1):
        evidence_files[f"cmd-{ordinal:02d}.stdout.bin"] = record["stdout"]
        evidence_files[f"cmd-{ordinal:02d}.stderr.bin"] = record["stderr"]
        evidence_files[f"cmd-{ordinal:02d}.receipt.json"] = receipt[1]
    result = E.model_validated_read_result(
        opening,
        opening_raw,
        state,
        lease,
        lease_raw,
        intent["lease_observed_at"],
        intent,
        intent_raw,
        records,
        receipts,
        1_040,
        None,
    )
    result_raw = E.canonical_bytes(result)
    completion = E.model_future_completion(result, result_raw, 1_040)
    return {
        "allocation": allocation,
        "opening": opening,
        "opening_raw": opening_raw,
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
        "completion_raw": E.canonical_bytes(completion),
    }


def validate_intent_bundle(bundle, intent=None, intent_raw=None):
    actual = bundle["intent"] if intent is None else intent
    raw = bundle["intent_raw"] if intent_raw is None else intent_raw
    return M.validate_intent(
        actual,
        raw,
        bundle["lease"],
        bundle["lease_raw"],
        bundle["opening"],
        bundle["opening_raw"],
        bundle["allocation"]["guard_raw"],
        bundle["allocation"]["opening_raw"],
        bundle["allocation"]["session_raw"],
    )


def validated_allocation(bundle):
    return M.validate_base_allocation(
        bundle["allocation"]["guard"],
        bundle["allocation"]["guard_raw"],
        bundle["allocation"]["opening"],
        bundle["allocation"]["opening_raw"],
        bundle["allocation"]["session"],
        bundle["allocation"]["session_raw"],
    )


def validate_result_bundle(bundle, result=None, result_raw=None):
    actual = bundle["result"] if result is None else result
    raw = bundle["result_raw"] if result_raw is None else result_raw
    return M.validate_read_result(
        actual,
        raw,
        bundle["intent"],
        bundle["intent_raw"],
        bundle["lease"],
        bundle["lease_raw"],
        bundle["opening"],
        bundle["opening_raw"],
        bundle["allocation"]["guard_raw"],
        bundle["allocation"]["opening_raw"],
        bundle["allocation"]["session_raw"],
        bundle["evidence_files"],
    )


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


def root_snapshot(*roots):
    snapshot = []
    for root in roots:
        for path in sorted((root, *root.rglob("*"))):
            relative = str(path.relative_to(root)) if path != root else "."
            info = os.stat(path, follow_symlinks=False)
            if stat.S_ISREG(info.st_mode):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                kind = "file"
            elif stat.S_ISDIR(info.st_mode):
                digest = None
                kind = "directory"
            elif stat.S_ISLNK(info.st_mode):
                digest = os.readlink(path)
                kind = "symlink"
            else:
                digest = None
                kind = "other"
            snapshot.append(
                (
                    str(root),
                    relative,
                    kind,
                    stat.S_IMODE(info.st_mode),
                    info.st_nlink,
                    info.st_size,
                    digest,
                )
            )
    return snapshot


class Tree:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.base = self.root / "base"
        self.evidence = self.root / "evidence"
        self.leaf = self.root / "leaf"
        for path in (self.base, self.evidence, self.leaf):
            mkdir(path)
        self.roots = {
            "base": self.base,
            "evidence": self.evidence,
            "leaf": self.leaf,
        }
        self.patch = mock.patch.object(M, "FIXED_ROOTS", self.roots)
        self.patch.start()
        self.core = bound_core_bytes()
        self.gate_patch = mock.patch.object(
            M,
            "_require_gate",
            side_effect=lambda kind: {
                "core_bytes": self.core,
                "h0_test_model_bypass": kind,
            },
        )
        self.gate_patch.start()

    def close(self):
        self.gate_patch.stop()
        self.patch.stop()
        self.temporary.cleanup()

    def install(self):
        return M._install_recovery_bundle_impl()

    def scan(self):
        return M._scan_fixed_state_impl()

    def populate(self, stage="complete"):
        bundle = oracle_bundle()
        mkdir(self.base / "campaigns")
        campaign_id = bundle["opening"]["campaign_id"]
        session_id = bundle["opening"]["session_id"]
        campaign = self.base / "campaigns" / campaign_id
        mkdir(campaign)
        session = campaign / "session"
        mkdir(session)
        write_file(self.base / "active-campaign.json", bundle["allocation"]["guard_raw"])
        write_file(session / "opening.json", bundle["allocation"]["opening_raw"])
        write_file(
            session / "session-opening.json", bundle["allocation"]["session_raw"]
        )

        mkdir(self.evidence / "campaigns")
        evidence_campaign = (
            self.evidence
            / "campaigns"
            / ("campaign-" + hashlib.sha256(campaign_id.encode()).hexdigest())
        )
        mkdir(evidence_campaign)
        sessions = evidence_campaign / "sessions"
        mkdir(sessions)
        evidence_session = sessions / (
            "session-" + hashlib.sha256(session_id.encode()).hexdigest()
        )
        mkdir(evidence_session)
        write_file(evidence_session / "accounting-opening.json", bundle["opening_raw"])

        levels = {
            "opening": 0,
            "lease": 1,
            "intent": 2,
            "partial": 3,
            "returns": 4,
            "health": 5,
            "result": 6,
            "complete": 7,
        }
        level = levels[stage]
        if level >= 1:
            write_file(
                self.leaf / "public-health-read-lease-000001.json",
                bundle["lease_raw"],
            )
        if level >= 2:
            write_file(evidence_session / "read-intent-000001.json", bundle["intent_raw"])
        if level >= 3:
            read_dir = evidence_session / "read-000001"
            mkdir(read_dir)
            count = {3: 4, 4: 18, 5: 19, 6: 19, 7: 19}[level]
            for name in M.PUBLICATION_ORDER[:count]:
                write_file(read_dir / name, bundle["evidence_files"][name])
        if level >= 6:
            write_file(evidence_session / "read-result-000001.json", bundle["result_raw"])
        if level >= 7:
            write_file(
                self.leaf / "public-health-read-complete-000001.json",
                bundle["completion_raw"],
            )
        return bundle, evidence_session


class RecoveryV1Test(unittest.TestCase):
    def test_01_plan_is_dormant_subset_and_commandless(self):
        plan = M.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_PUBLIC_HEALTH_RECOVERY_V1_STORE_SCANNER_PASS_GO_NOT_ACTIVE",
        )
        self.assertTrue(plan["permanent_h0_only"])
        self.assertFalse(plan["self_contained_finalizer_implemented"])
        for key in (
            "recovery_v1_qualified",
            "scanner_active",
            "writer_active",
            "finalizer_active",
            "reemit_active",
            "manifest_active",
            "contract_active",
            "live_authority",
        ):
            self.assertIs(plan[key], False)
        for key in (
            "device_commands",
            "device_effects",
            "root_commands",
            "control_actions",
            "partition_transfers",
            "callbacks",
            "backends",
        ):
            self.assertEqual(plan[key], [])

    def test_02_cli_render_only(self):
        good = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(json.loads(good.stdout)["cli"], ["--render-plan"])
        for args in ([], ["--scan"], ["--finalize"], ["--render-plan", "--scan"]):
            bad = subprocess.run(
                [sys.executable, str(SCRIPT), *args],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(bad.returncode, 0)

    def test_03_all_public_mutating_or_scanning_entrypoints_gate_before_fs(self):
        with mock.patch.object(M, "_open_fixed_root", side_effect=AssertionError):
            for function in (
                M.scan_fixed_state,
                M.install_recovery_bundle,
                M._scan_fixed_state_impl,
                M._install_recovery_bundle_impl,
                M.finalize_zero_command,
                M.reemit_terminal,
            ):
                reject(function)

    def test_04_even_all_current_flags_cannot_reach_unimplemented_finalizer(self):
        names = (
            "RECOVERY_V1_QUALIFIED",
            "RECOVERY_FINALIZER_ACTIVE",
            "RECOVERY_REEMIT_ACTIVE",
            "RECOVERY_MANIFEST_ACTIVE",
            "RECOVERY_CONTRACT_ACTIVE",
        )
        patches = [mock.patch.object(M, name, True) for name in names]
        for patch in patches:
            patch.start()
        try:
            reject(M.finalize_zero_command)
            reject(M.reemit_terminal)
        finally:
            for patch in reversed(patches):
                patch.stop()

    def test_05_static_source_has_no_oracle_runtime_path_or_command_backend(self):
        payload = SCRIPT.read_bytes()
        for label in ("base_coordinator", "health", "inventory", "evidence_owner"):
            self.assertEqual(payload.count(str(ORACLE_PATHS[label]).encode()), 1)
        self.assertNotIn(str(ORACLE_PATHS["read_leaf"]).encode(), payload)
        tree = ast.parse(payload.decode())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue(imports.isdisjoint({"subprocess", "socket", "requests", "urllib"}))
        for token in (
            b"Popen",
            b"check_output",
            b"adb shell",
            b"odin4",
            b"fastboot",
            b"os.rename",
            b"os.unlink",
            b"os.remove",
            b"os.rmdir",
            b".pending-",
        ):
            self.assertNotIn(token, payload)

    def test_06_oracle_sizes_and_hashes_are_exact(self):
        for label, path in ORACLE_PATHS.items():
            payload = path.read_bytes()
            self.assertEqual(len(payload), M.ORACLE_IDENTITIES[label]["size"])
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(),
                M.ORACLE_IDENTITIES[label]["sha256"],
            )

    def test_07_embedded_inventory_literals_equal_oracle(self):
        path = ORACLE_PATHS["inventory"]
        self.assertEqual(M.PROPERTY_KEYS, literal(path, "PROPERTY_KEYS"))
        self.assertEqual(M.REMOTE_SNAPSHOT, literal(path, "REMOTE_SNAPSHOT"))
        self.assertEqual(M.HEALTH_SCHEMA, literal(path, "SCHEMA"))
        self.assertEqual(M.HEALTH_VERSION, literal(path, "VERSION"))
        self.assertEqual(M.HEALTH_VERDICT, literal(path, "VERDICT"))
        self.assertEqual(M.ADB_SHA256, literal(path, "EXPECTED_ADB_SHA256"))

    def test_08_embedded_health_target_and_transcript_equal_oracle(self):
        path = ORACLE_PATHS["health"]
        self.assertEqual(M.TARGET, literal(path, "TARGET"))
        self.assertEqual(M.FIXED_TRANSCRIPT, literal(path, "FIXED_TRANSCRIPT"))

    def test_09_embedded_evidence_schemas_equal_oracle(self):
        path = ORACLE_PATHS["evidence_owner"]
        mapping = {
            "ACCOUNTING_OPENING_SCHEMA": M.ACCOUNTING_OPENING_SCHEMA,
            "READ_INTENT_SCHEMA": M.READ_INTENT_SCHEMA,
            "COMMAND_EVIDENCE_SCHEMA": M.COMMAND_EVIDENCE_SCHEMA,
            "READ_RESULT_SCHEMA": M.READ_RESULT_SCHEMA,
            "COORDINATOR_LEASE_SCHEMA": M.COORDINATOR_LEASE_SCHEMA,
            "COORDINATOR_COMPLETE_SCHEMA": M.COORDINATOR_COMPLETE_SCHEMA,
        }
        for name, value in mapping.items():
            self.assertEqual(value, literal(path, name))

    def test_10_canonical_json_is_strict(self):
        reject(M.parse_canonical_json, b'{"x":1,"x":2}\n', "duplicate")
        reject(M.parse_canonical_json, b'{"x": 1}\n', "spacing")
        reject(M.parse_canonical_json, b'{"x":NaN}\n', "nan")
        reject(M.parse_canonical_json, b"", "empty")
        reject(M.parse_canonical_json, b'{"x":1}\n', "bool max", True)
        self.assertEqual(M.parse_canonical_json(b'{"x":1}\n', "valid"), {"x": 1})

    def test_11_retained_parser_health_exactly_matches_oracle(self):
        bundle = oracle_bundle()
        actual = M.derive_health_from_retained(
            bundle["intent"], bundle["intent_raw"], bundle["evidence_files"]
        )
        self.assertEqual(actual, bundle["health"])
        self.assertEqual(M.canonical_bytes(actual), E.canonical_bytes(bundle["health"]))

    def test_12_base_accounting_lease_validators_accept_oracle_fixture(self):
        bundle = oracle_bundle()
        allocation = M.validate_base_allocation(
            bundle["allocation"]["guard"],
            bundle["allocation"]["guard_raw"],
            bundle["allocation"]["opening"],
            bundle["allocation"]["opening_raw"],
            bundle["allocation"]["session"],
            bundle["allocation"]["session_raw"],
        )
        M.validate_accounting_opening(
            bundle["opening"],
            bundle["opening_raw"],
            allocation,
            bundle["allocation"]["guard_raw"],
            bundle["allocation"]["opening_raw"],
            bundle["allocation"]["session_raw"],
        )
        M.validate_lease(
            bundle["lease"],
            bundle["lease_raw"],
            bundle["opening"],
            bundle["opening_raw"],
            bundle["allocation"]["session"],
            bundle["allocation"]["session_raw"],
        )

    def test_13_result_and_completion_validators_accept_oracle_fixture(self):
        bundle = oracle_bundle()
        self.assertEqual(validate_intent_bundle(bundle), bundle["intent"])
        self.assertEqual(validate_result_bundle(bundle), bundle["result"])
        self.assertEqual(
            M.validate_parked_completion(
                bundle["completion"],
                bundle["completion_raw"],
                bundle["result"],
                bundle["result_raw"],
            ),
            bundle["completion"],
        )

    def test_14_parser_rejects_raw_receipt_and_inventory_drift(self):
        bundle = oracle_bundle()
        for name in (
            "cmd-01.stdout.bin",
            "cmd-02.stdout.bin",
            "cmd-03.stdout.bin",
            "cmd-04.stdout.bin",
            "cmd-06.receipt.json",
        ):
            changed = copy.deepcopy(bundle["evidence_files"])
            changed[name] += b"x"
            reject(
                M.derive_health_from_retained,
                bundle["intent"],
                bundle["intent_raw"],
                changed,
            )

    def test_15_parser_rejects_identity_snapshot_and_tool_drift(self):
        bundle = oracle_bundle()
        changed_intent = copy.deepcopy(bundle["intent"])
        changed_intent["source_identity"]["boot_id_sha256"] = "f" * 64
        changed_raw = M.canonical_bytes(changed_intent)
        reject(
            M.derive_health_from_retained,
            changed_intent,
            changed_raw,
            bundle["evidence_files"],
        )
        changed = copy.deepcopy(bundle["evidence_files"])
        receipt = M.parse_canonical_json(changed["cmd-01.receipt.json"], "receipt")
        receipt["host_tool_after"]["inode"] += 1
        changed["cmd-01.receipt.json"] = M.canonical_bytes(receipt)
        reject(
            M.derive_health_from_retained,
            bundle["intent"],
            bundle["intent_raw"],
            changed,
        )

    def test_16_result_manifest_hash_counter_and_bool_tamper_reject(self):
        bundle = oracle_bundle()
        mutations = (
            ("actual_evidence_bytes", True),
            ("outcome_proven", 1),
            ("coordinator_lease_sha256", "f" * 64),
            ("device_effect_count", True),
        )
        for key, value in mutations:
            changed = copy.deepcopy(bundle["result"])
            changed[key] = value
            reject(validate_result_bundle, bundle, changed, M.canonical_bytes(changed))

    def test_17_completion_hash_flags_and_time_tamper_reject(self):
        bundle = oracle_bundle()
        for key, value in (
            ("evidence_result_sha256", "f" * 64),
            ("controls_unblocked", True),
            ("campaign_parked", False),
            ("completed_at", True),
        ):
            changed = copy.deepcopy(bundle["completion"])
            changed[key] = value
            reject(
                M.validate_parked_completion,
                changed,
                M.canonical_bytes(changed),
                bundle["result"],
                bundle["result_raw"],
            )

    def test_18_manifest_binds_core_oracles_schemas_caps_and_runner_placeholder(self):
        core = SCRIPT.read_bytes()
        manifest = M.build_manifest(core)
        self.assertEqual(manifest["core"]["sha256"], hashlib.sha256(core).hexdigest())
        self.assertEqual(
            manifest["core"]["normalized_sha256"],
            M.EXPECTED_RECOVERY_NORMALIZED_SHA256,
        )
        self.assertEqual(manifest["oracles"], M._plain(M.ORACLE_IDENTITIES))
        self.assertEqual(
            manifest["retained_source_receipts"],
            M._plain(M.EXPECTED_RETAINED_SOURCE_RECEIPTS),
        )
        self.assertEqual(manifest["future_runner_binding"]["normalized_sha256"], "0" * 64)
        self.assertFalse(manifest["future_runner_binding"]["binding_complete"])
        self.assertNotIn("manifest_sha256", manifest)
        self.assertEqual(manifest["caps"]["completed_total_max_bytes"], 1_441_792)
        self.assertEqual(manifest["caps"]["completed_total_file_count"], 52)

    def test_19_manifest_validation_rejects_every_binding_tamper(self):
        core = SCRIPT.read_bytes()
        manifest = M.build_manifest(core)
        raw = M.canonical_bytes(manifest)
        self.assertEqual(M.validate_manifest(manifest, raw, core), manifest)
        for path, value in (
            (("core", "sha256"), "f" * 64),
            (("future_runner_binding", "binding_complete"), True),
            (("oracles", "health", "sha256"), "f" * 64),
            (("caps", "structural_max_bytes"), 1),
            (("entrypoints", "finalize_zero_command"), "active"),
        ):
            changed = copy.deepcopy(manifest)
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            reject(M.validate_manifest, changed, M.canonical_bytes(changed), core)
        reject(M.validate_manifest, manifest, raw, core + b"x")

    def test_20_manifest_core_and_bundle_size_edges(self):
        core = SCRIPT.read_bytes()
        manifest = M.build_manifest(core)
        self.assertLessEqual(len(M.canonical_bytes(manifest)), M.RECOVERY_MANIFEST_MAX_BYTES)
        self.assertLessEqual(len(core), M.RECOVERY_CORE_MAX_BYTES)
        reject(M.build_manifest, core + b"# unreviewed byte\n")
        reject(M.build_manifest, b"x" * M.RECOVERY_CORE_MAX_BYTES)
        reject(M.build_manifest, b"x" * (M.RECOVERY_CORE_MAX_BYTES + 1))
        reject(M.build_manifest, b"")

    def test_21_cut_classifier_every_stage_never_authorizes_settlement(self):
        cases = (
            (False, False, False, False, False, (), False, False),
            (False, True, False, False, False, (), False, False),
            (True, True, True, False, False, (), False, False),
            (True, True, True, True, False, (), False, False),
            (True, True, True, True, True, M.PUBLICATION_ORDER[:4], False, False),
            (True, True, True, True, True, M.PUBLICATION_ORDER[:18], False, False),
            (True, True, True, True, True, M.PUBLICATION_ORDER, False, False),
            (True, True, True, True, True, M.PUBLICATION_ORDER, True, False),
            (True, True, True, True, True, M.PUBLICATION_ORDER, True, True),
        )
        for opening, core, manifest, lease, intent, names, result, complete in cases:
            value = M.classify_cut(
                opening_present=opening,
                core_present=core,
                manifest_present=manifest,
                lease_present=lease,
                intent_present=intent,
                evidence_names=names,
                result_present=result,
                completion_present=complete,
            )
            self.assertFalse(value["settlement_validated"])
            self.assertFalse(value["replay_authorized"])
            self.assertFalse(value["refund_authorized"])
            self.assertFalse(value["next_action_authorized"])
            self.assertFalse(value["zero_command_finalization_authorized"])

    def test_22_cut_classifier_rejects_gaps_descendants_and_bool_types(self):
        base = dict(
            opening_present=True,
            core_present=True,
            manifest_present=True,
            lease_present=True,
            intent_present=True,
            evidence_names=M.PUBLICATION_ORDER[:2],
            result_present=False,
            completion_present=False,
        )
        changed = dict(base)
        changed["evidence_names"] = (M.PUBLICATION_ORDER[1],)
        reject(M.classify_cut, **changed)
        changed = dict(base)
        changed["completion_present"] = True
        reject(M.classify_cut, **changed)
        changed = dict(base)
        changed["lease_present"] = False
        reject(M.classify_cut, **changed)
        changed = dict(base)
        changed["opening_present"] = 1
        reject(M.classify_cut, **changed)

    def test_23_preopening_partial_bundle_is_only_repair_eligible_case(self):
        partial = M.classify_cut(
            opening_present=False,
            core_present=True,
            manifest_present=False,
            lease_present=False,
            intent_present=False,
            evidence_names=(),
            result_present=False,
            completion_present=False,
        )
        self.assertTrue(partial["bundle_repair_eligible"])
        after = M.classify_cut(
            opening_present=True,
            core_present=True,
            manifest_present=False,
            lease_present=False,
            intent_present=False,
            evidence_names=(),
            result_present=False,
            completion_present=False,
        )
        self.assertFalse(after["bundle_repair_eligible"])
        self.assertTrue(after["campaign_parked"])

    def test_24_atomic_anonymous_publish_and_exact_idempotence(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                self.assertEqual(
                    M._atomic_publish_at(parent, M.RECOVERY_CORE_NAME, b"core"),
                    "PUBLISHED",
                )
                self.assertEqual(
                    M._atomic_publish_at(parent, M.RECOVERY_CORE_NAME, b"core"),
                    "EXACT_ALREADY_PRESENT",
                )
                info = os.stat(M.RECOVERY_CORE_NAME, dir_fd=parent, follow_symlinks=False)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)
            finally:
                os.close(parent)

    def test_25_atomic_existing_different_hardlink_symlink_and_mode_reject(self):
        for variant in ("different", "hardlink", "symlink", "mode"):
            with tempfile.TemporaryDirectory() as temporary:
                os.chmod(temporary, 0o700)
                path = Path(temporary) / M.RECOVERY_CORE_NAME
                if variant == "symlink":
                    os.symlink("foreign", path)
                else:
                    write_file(path, b"wrong" if variant == "different" else b"core")
                    if variant == "hardlink":
                        os.link(path, Path(temporary) / "other")
                    if variant == "mode":
                        os.chmod(path, 0o600)
                parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    reject(M._atomic_publish_at, parent, M.RECOVERY_CORE_NAME, b"core")
                finally:
                    os.close(parent)

    def test_26_atomic_short_writes_complete_and_zero_write_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            original = os.write
            try:
                def short(descriptor, payload):
                    return original(descriptor, payload[: max(1, len(payload) // 2)])

                with mock.patch.object(M.os, "write", side_effect=short):
                    self.assertEqual(
                        M._atomic_publish_at(parent, M.RECOVERY_CORE_NAME, b"x" * 100),
                        "PUBLISHED",
                    )
            finally:
                os.close(parent)
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with mock.patch.object(M.os, "write", return_value=0):
                    reject(M._atomic_publish_at, parent, M.RECOVERY_CORE_NAME, b"x")
            finally:
                os.close(parent)

    def test_27_atomic_file_fsync_and_link_failures_leave_no_final(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with mock.patch.object(M.os, "fsync", side_effect=OSError(errno.EIO, "cut")):
                    reject(M._atomic_publish_at, parent, M.RECOVERY_CORE_NAME, b"x")
                self.assertFalse((Path(temporary) / M.RECOVERY_CORE_NAME).exists())
                with mock.patch.object(
                    M, "_link_anonymous_tmpfile", side_effect=OSError(errno.EIO, "cut")
                ):
                    reject(M._atomic_publish_at, parent, M.RECOVERY_CORE_NAME, b"x")
                self.assertFalse((Path(temporary) / M.RECOVERY_CORE_NAME).exists())
            finally:
                os.close(parent)

    def test_28_atomic_directory_fsync_cut_retries_only_exact_existing(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
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
                    reject(M._atomic_publish_at, parent, M.RECOVERY_CORE_NAME, b"x")
                self.assertEqual(
                    M._atomic_publish_at(parent, M.RECOVERY_CORE_NAME, b"x"),
                    "EXACT_ALREADY_PRESENT",
                )
            finally:
                os.close(parent)

    def test_29_atomic_eexist_race_accepts_only_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                def race(source_fd, parent_fd, name):
                    write_file(Path(temporary) / name, b"x")
                    raise OSError(errno.EEXIST, "race")

                with mock.patch.object(M, "_link_anonymous_tmpfile", side_effect=race):
                    self.assertEqual(
                        M._atomic_publish_at(parent, M.RECOVERY_CORE_NAME, b"x"),
                        "EXACT_RACE_PRESENT",
                    )
            finally:
                os.close(parent)

    def test_30_fixed_lock_is_exclusive_nonblocking_and_mode_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with M._ExclusiveCoordinatorLock(parent, create=True):
                    with self.assertRaises(M.RecoveryV1Error):
                        with M._ExclusiveCoordinatorLock(parent, create=False):
                            pass
                info = os.stat(M.LOCK_NAME, dir_fd=parent, follow_symlinks=False)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
            finally:
                os.close(parent)

    def test_31_directory_symlink_and_wrong_mode_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real"
            mkdir(real)
            link = Path(temporary) / "link"
            os.symlink(real, link)
            reject(M._open_absolute_directory, link, "symlink root")
            os.chmod(real, 0o755)
            reject(M._open_absolute_directory, real, "wrong mode")

    def test_32_held_dirfd_never_writes_replacement_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            original_path = Path(temporary) / "parent"
            mkdir(original_path)
            descriptor = os.open(original_path, os.O_RDONLY | os.O_DIRECTORY)
            moved = Path(temporary) / "moved"
            os.rename(original_path, moved)
            mkdir(original_path)
            try:
                M._atomic_publish_at(descriptor, M.RECOVERY_CORE_NAME, b"safe")
            finally:
                os.close(descriptor)
            self.assertTrue((moved / M.RECOVERY_CORE_NAME).is_file())
            self.assertFalse((original_path / M.RECOVERY_CORE_NAME).exists())

    def test_33_install_manifest_last_and_idempotent_before_opening(self):
        tree = Tree()
        try:
            first = tree.install()
            self.assertEqual(first["core_publication"], "PUBLISHED")
            self.assertEqual(first["manifest_publication"], "PUBLISHED")
            second = tree.install()
            self.assertEqual(second["core_publication"], "EXACT_ALREADY_PRESENT")
            self.assertEqual(second["manifest_publication"], "EXACT_ALREADY_PRESENT")
        finally:
            tree.close()

    def test_34_partial_bundle_repair_after_opening_rejects(self):
        tree = Tree()
        try:
            mkdir(tree.leaf / M.RECOVERY_DIRECTORY)
            write_file(
                tree.leaf / M.RECOVERY_DIRECTORY / M.RECOVERY_CORE_NAME,
                tree.core,
            )
            tree.populate("opening")
            before = root_snapshot(tree.base, tree.evidence, tree.leaf)
            reject(tree.install)
            self.assertEqual(root_snapshot(tree.base, tree.evidence, tree.leaf), before)
        finally:
            tree.close()

    def test_35_install_rejects_foreign_leaf_and_base_campaign_state(self):
        tree = Tree()
        try:
            write_file(tree.leaf / "foreign", b"x")
            reject(tree.install)
        finally:
            tree.close()
        tree = Tree()
        try:
            mkdir(tree.base / "campaigns")
            mkdir(tree.base / "campaigns" / ("a" * 32))
            reject(tree.install)
        finally:
            tree.close()

    def test_36_scanner_preopening_and_opening_no_lease(self):
        tree = Tree()
        try:
            tree.install()
            pre = tree.scan()
            self.assertEqual(pre["cut"]["status"], "PRE_OPENING_NO_CAMPAIGN")
            tree.populate("opening")
            opened = tree.scan()
            self.assertEqual(
                opened["cut"]["status"], "OPENING_NO_LEASE_NO_AUTONOMOUS_AUTHORITY"
            )
            self.assertEqual(opened["structural"]["node_count"], 4)
        finally:
            tree.close()

    def test_37_scanner_all_post_lease_cuts_are_parked_and_zero_command(self):
        expected = {
            "lease": "LEASE_WITHOUT_MIRROR_PARKED",
            "intent": "INCOMPLETE_RETURNS_UNCERTAIN_CONSUMED_PARKED",
            "partial": "INCOMPLETE_RETURNS_UNCERTAIN_CONSUMED_PARKED",
            "returns": "COMPLETE_RETURNS_DERIVATION_CANDIDATE_UNPROVED",
            "health": "HEALTH_PRESENT_RESULT_CANDIDATE_UNPROVED",
            "result": "RESULT_PRESENT_COMPLETION_CANDIDATE_UNPROVED",
            "complete": "COMPLETION_PRESENT_REEMIT_CANDIDATE_UNPROVED",
        }
        for stage, status in expected.items():
            tree = Tree()
            try:
                tree.install()
                tree.populate(stage)
                scan = tree.scan()
                self.assertEqual(scan["cut"]["status"], status)
                self.assertEqual(scan["device_commands"], 0)
                self.assertFalse(scan["live_authority"])
                self.assertFalse(scan["cut"]["settlement_validated"])
            finally:
                tree.close()

    def test_38_complete_scanner_validates_8_structural_and_19_evidence(self):
        tree = Tree()
        try:
            tree.install()
            tree.populate("complete")
            scan = tree.scan()
            self.assertEqual(scan["structural"]["node_count"], 8)
            self.assertLessEqual(scan["structural"]["actual_bytes"], 49_152)
            self.assertEqual(scan["evidence_file_count"], 19)
            self.assertTrue(scan["derived_health_validated"])
            self.assertTrue(scan["result_validated"])
            self.assertTrue(scan["completion_validated"])
            self.assertTrue(scan["manifest_verified"])
        finally:
            tree.close()

    def test_39_scanner_rejects_extra_names_and_evidence_gap(self):
        tree = Tree()
        try:
            tree.install()
            _, evidence_session = tree.populate("partial")
            write_file(evidence_session / "foreign.json", b"{}\n")
            reject(tree.scan)
        finally:
            tree.close()
        tree = Tree()
        try:
            tree.install()
            bundle, evidence_session = tree.populate("intent")
            read_dir = evidence_session / "read-000001"
            mkdir(read_dir)
            write_file(
                read_dir / M.PUBLICATION_ORDER[1],
                bundle["evidence_files"][M.PUBLICATION_ORDER[1]],
            )
            reject(tree.scan)
        finally:
            tree.close()

    def test_40_scanner_rejects_evidence_hardlink_mode_and_raw_hash_drift(self):
        for variant in ("hardlink", "mode", "drift"):
            tree = Tree()
            try:
                tree.install()
                _, evidence_session = tree.populate("complete")
                path = evidence_session / "read-000001" / "cmd-01.stdout.bin"
                if variant == "hardlink":
                    os.link(path, evidence_session / "read-000001" / "alias")
                elif variant == "mode":
                    os.chmod(path, 0o600)
                else:
                    os.chmod(path, 0o600)
                    descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC)
                    try:
                        os.write(descriptor, b"drift")
                    finally:
                        os.close(descriptor)
                    os.chmod(path, 0o400)
                reject(tree.scan)
            finally:
                tree.close()

    def test_41_scanner_lock_contention_rejects_without_reading_state(self):
        tree = Tree()
        try:
            tree.install()
            leaf = M._open_fixed_root("leaf")
            try:
                with M._ExclusiveCoordinatorLock(leaf, create=False):
                    reject(tree.scan)
            finally:
                os.close(leaf)
        finally:
            tree.close()

    def test_42_structural_cap_count_and_completion_closure(self):
        bundle = oracle_bundle()
        raws = {
            "active-campaign.json": bundle["allocation"]["guard_raw"],
            "opening.json": bundle["allocation"]["opening_raw"],
            "session-opening.json": bundle["allocation"]["session_raw"],
            "accounting-opening.json": bundle["opening_raw"],
            "public-health-read-lease-000001.json": bundle["lease_raw"],
            "read-intent-000001.json": bundle["intent_raw"],
            "read-result-000001.json": bundle["result_raw"],
            "public-health-read-complete-000001.json": bundle["completion_raw"],
        }
        proof = M.validate_structural_raws(raws)
        self.assertEqual(proof["node_count"], 8)
        changed = dict(raws)
        changed.pop("read-result-000001.json")
        reject(M.validate_structural_raws, changed)
        changed = dict(raws)
        changed["foreign"] = b"{}\n"
        reject(M.validate_structural_raws, changed)

    def test_43_same_module_h0_model_verifies_bound_copy_not_loader_authority(self):
        tree = Tree()
        try:
            tree.install()
            leaf = M._open_fixed_root("leaf")
            try:
                recovery = M._open_child_directory(leaf, M.RECOVERY_DIRECTORY, "recovery")
                try:
                    verified = M._model_verify_private_core_bytes(recovery)
                finally:
                    os.close(recovery)
            finally:
                os.close(leaf)
            namespace = {"__file__": str(tree.leaf / M.RECOVERY_DIRECTORY / M.RECOVERY_CORE_NAME), "__name__": "private_recovery_copy"}
            exec(compile(verified, namespace["__file__"], "exec"), namespace, namespace)
            self.assertEqual(namespace["ORACLE_IDENTITIES"]["health"]["sha256"], M.ORACLE_IDENTITIES["health"]["sha256"])
            self.assertEqual(namespace["FUTURE_RUNNER_BINDING"]["status"], "BOUND")
            self.assertFalse(M.render_plan()["same_module_private_verifier_authoritative"])
        finally:
            tree.close()

    def test_44_private_copy_parser_survives_all_runtime_open_failures(self):
        bundle = oracle_bundle()
        payload = bound_core_bytes()
        namespace = {"__file__": "/private/recovery-v1/recovery-core.py", "__name__": "private_core_no_oracles"}
        exec(compile(payload, namespace["__file__"], "exec"), namespace, namespace)
        private = types.SimpleNamespace(**namespace)
        with mock.patch.object(private.os, "open", side_effect=AssertionError("no runtime source open")):
            health = private.derive_health_from_retained(
                bundle["intent"], bundle["intent_raw"], bundle["evidence_files"]
            )
        self.assertEqual(health, bundle["health"])

    def test_45_private_copy_oracle_hashes_are_data_not_imports(self):
        source = SCRIPT.read_text()
        self.assertNotIn("importlib", source)
        self.assertNotIn("runpy", source)
        self.assertIn(str(ORACLE_PATHS["evidence_owner"]), source)
        self.assertEqual(set(M.ORACLE_IDENTITIES), set(ORACLE_PATHS))

    def test_46_unbound_runner_blocks_install_even_if_all_public_gates_flip(self):
        gate_names = (
            "RECOVERY_V1_QUALIFIED",
            "RECOVERY_WRITER_ACTIVE",
            "RECOVERY_MANIFEST_ACTIVE",
            "RECOVERY_CONTRACT_ACTIVE",
        )
        patches = [mock.patch.object(M, name, True) for name in gate_names]
        for patch in patches:
            patch.start()
        try:
            with mock.patch.object(M, "_open_fixed_root", side_effect=AssertionError):
                reject(M.install_recovery_bundle)
        finally:
            for patch in reversed(patches):
                patch.stop()

    def test_47_new_lock_is_file_and_parent_fsynced_before_use(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            original = os.fsync
            calls = []

            def record(descriptor):
                calls.append(descriptor)
                return original(descriptor)

            try:
                with mock.patch.object(M.os, "fsync", side_effect=record):
                    with M._ExclusiveCoordinatorLock(parent, create=True):
                        pass
                self.assertGreaterEqual(len(calls), 2)
                self.assertIn(parent, calls)
            finally:
                os.close(parent)

    def test_48_linked_final_must_be_same_inode_as_anonymous_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                def substitute(source_fd, parent_fd, name):
                    write_file(Path(temporary) / name, b"same")

                with mock.patch.object(M, "_link_anonymous_tmpfile", side_effect=substitute):
                    reject(M._atomic_publish_at, parent, M.RECOVERY_CORE_NAME, b"same")
            finally:
                os.close(parent)

    def test_49_result_timing_must_follow_last_receipt_and_cut_window(self):
        bundle = oracle_bundle()
        changed = copy.deepcopy(bundle["result"])
        changed["completed_at"] = 1_000
        reject(validate_result_bundle, bundle, changed, M.canonical_bytes(changed))
        changed = copy.deepcopy(bundle["result"])
        changed["reporting_cut_at"] = 1_000
        changed["reporting_after_expiry_or_drift"] = True
        reject(validate_result_bundle, bundle, changed, M.canonical_bytes(changed))

    def test_50_lease_context_cannot_drift_from_accounting_opening(self):
        bundle = oracle_bundle()
        for key, value in (
            ("current_ordinal", 1),
            ("campaign_expires_at", bundle["lease"]["coordinator_context"]["campaign_expires_at"] + 1),
        ):
            changed = copy.deepcopy(bundle["lease"])
            changed["coordinator_context"][key] = value
            changed["coordinator_context_sha256"] = M.sha256_bytes(
                M.canonical_bytes(changed["coordinator_context"])
            )
            reject(
                M.validate_lease,
                changed,
                M.canonical_bytes(changed),
                bundle["opening"],
                bundle["opening_raw"],
                bundle["allocation"]["session"],
                bundle["allocation"]["session_raw"],
            )

    def test_51_plan_states_ancestor_and_same_uid_limits(self):
        boundary = M.render_plan()["ancestor_consistency_boundary"]
        self.assertTrue(boundary["all_absolute_components_opened_nofollow"])
        self.assertTrue(
            boundary["managed_roots_and_descendants_require_current_uid_gid_mode_0700"]
        )
        self.assertTrue(
            boundary["host_ancestors_above_managed_roots_require_nofollow_but_not_mode_0700"]
        )
        self.assertTrue(
            boundary[
                "all_three_fixed_roots_and_recovery_directory_reopened_after_install"
            ]
        )
        self.assertFalse(boundary["same_uid_concurrent_replacement_closed"])

    def test_52_manifest_binds_structural_and_evidence_namespace(self):
        manifest = M.build_manifest(SCRIPT.read_bytes())
        self.assertEqual(manifest["structural_node_caps"], dict(M.STRUCTURAL_CAPS))
        self.assertEqual(manifest["evidence_names"], list(M.EVIDENCE_NAMES))
        self.assertEqual(
            manifest["evidence_publication_order"], list(M.PUBLICATION_ORDER)
        )
        self.assertEqual(
            manifest["caps"]["recovery_opening_file_count"],
            M.RECOVERY_OPENING_FILE_COUNT,
        )

    def test_53_scanner_rejects_manifest_core_and_recovery_namespace_tamper(self):
        for variant in ("manifest", "core", "extra"):
            tree = Tree()
            try:
                tree.install()
                recovery = tree.leaf / M.RECOVERY_DIRECTORY
                if variant == "extra":
                    write_file(recovery / "extra", b"x")
                else:
                    path = recovery / (
                        M.RECOVERY_MANIFEST_NAME
                        if variant == "manifest"
                        else M.RECOVERY_CORE_NAME
                    )
                    os.chmod(path, 0o600)
                    descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC)
                    try:
                        os.write(descriptor, b"tamper")
                    finally:
                        os.close(descriptor)
                    os.chmod(path, 0o400)
                reject(tree.scan)
            finally:
                tree.close()

    def test_54_completion_scan_is_revalidation_only_not_double_settlement(self):
        tree = Tree()
        try:
            tree.install()
            tree.populate("complete")
            first = tree.scan()
            second = tree.scan()
            self.assertEqual(first, second)
            self.assertFalse(first["cut"]["settlement_validated"])
            reject(M.finalize_zero_command)
            reject(M.finalize_zero_command)
        finally:
            tree.close()

    def test_55_install_reopen_detects_fixed_leaf_root_swap(self):
        tree = Tree()
        original = M._atomic_publish_at
        calls = 0
        moved = tree.root / "leaf-moved"

        def publish_then_swap(parent, name, payload):
            nonlocal calls
            result = original(parent, name, payload)
            calls += 1
            if calls == 2:
                os.rename(tree.leaf, moved)
                mkdir(tree.leaf)
            return result

        try:
            with mock.patch.object(M, "_atomic_publish_at", side_effect=publish_then_swap):
                reject(tree.install)
            self.assertFalse((tree.leaf / M.RECOVERY_DIRECTORY).exists())
            self.assertTrue((moved / M.RECOVERY_DIRECTORY).is_dir())
        finally:
            tree.close()

    def test_56_unbound_runner_also_blocks_scanner_after_boolean_rotation(self):
        names = (
            "RECOVERY_V1_QUALIFIED",
            "RECOVERY_SCANNER_ACTIVE",
            "RECOVERY_MANIFEST_ACTIVE",
            "RECOVERY_CONTRACT_ACTIVE",
        )
        patches = [mock.patch.object(M, name, True) for name in names]
        for patch in patches:
            patch.start()
        try:
            with mock.patch.object(M, "_open_fixed_root", side_effect=AssertionError):
                reject(M.scan_fixed_state)
        finally:
            for patch in reversed(patches):
                patch.stop()

    def test_57_empty_read_directory_before_intent_is_rejected(self):
        tree = Tree()
        try:
            tree.install()
            _, evidence_session = tree.populate("opening")
            mkdir(evidence_session / "read-000001")
            reject(tree.scan)
        finally:
            tree.close()

    def test_58_future_opening_namespace_is_bound_but_not_currently_accepted(self):
        manifest = M.build_manifest(SCRIPT.read_bytes())
        future = manifest["future_leaf_namespace"]
        self.assertEqual(len(future["opening_names"]), 21)
        self.assertEqual(future["opening_directory"], "opening-v1")
        self.assertEqual(future["campaign_binding"], "campaign-binding.json")
        self.assertFalse(future["current_scanner_accepts_opening_or_campaign_binding"])
        tree = Tree()
        try:
            tree.install()
            mkdir(tree.leaf / M.OPENING_DIRECTORY)
            reject(tree.scan)
        finally:
            tree.close()

    def test_59_recovery_anchor_and_runner_binding_normalization_are_noncircular(self):
        source = SCRIPT.read_bytes()
        bound = bound_core_bytes()
        self.assertNotEqual(hashlib.sha256(source).digest(), hashlib.sha256(bound).digest())
        self.assertNotEqual(M.EXPECTED_RECOVERY_NORMALIZED_SHA256, M.ZERO_HASH)
        self.assertEqual(
            M.normalized_self_sha256(source), M.EXPECTED_RECOVERY_NORMALIZED_SHA256
        )
        self.assertEqual(
            M.normalized_self_sha256(bound), M.EXPECTED_RECOVERY_NORMALIZED_SHA256
        )
        self.assertEqual(
            M.validate_core_identity(bound)["runner_binding"]["status"], "BOUND"
        )
        manifest = M.build_manifest(bound)
        self.assertEqual(manifest["future_runner_binding"]["status"], "BOUND")
        self.assertEqual(
            manifest["future_runner_binding_sha256"],
            M.sha256_bytes(M.canonical_bytes(manifest["future_runner_binding"])),
        )
        drift = source.replace(
            b"SELF_CONTAINED_FINALIZER_IMPLEMENTED = False",
            b"SELF_CONTAINED_FINALIZER_IMPLEMENTED = True",
        )
        self.assertNotEqual(
            M.normalized_self_sha256(drift), M.EXPECTED_RECOVERY_NORMALIZED_SHA256
        )
        reject(M.validate_core_identity, drift)

    def test_60_full_intent_validator_reconstructs_exact_oracle_mirror(self):
        bundle = oracle_bundle()
        expected = M.model_exact_intent_mirror(
            bundle["lease"],
            bundle["lease_raw"],
            bundle["opening"],
            bundle["intent"]["mirrored_at"],
        )
        self.assertEqual(expected, bundle["intent"])
        self.assertEqual(validate_intent_bundle(bundle), bundle["intent"])
        for path, value in (
            (("coordinator_head_sha256",), "e" * 64),
            (("source_identity", "boot_id_sha256"), "f" * 64),
        ):
            changed = copy.deepcopy(bundle["intent"])
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            self.assertEqual(
                M._validate_intent_shape(changed, M.canonical_bytes(changed)), changed
            )
            reject(
                validate_intent_bundle,
                bundle,
                changed,
                M.canonical_bytes(changed),
            )

    def test_61_nested_strict_type_substitutions_all_reject(self):
        bundle = oracle_bundle()
        strict_cases = []

        guard = copy.deepcopy(bundle["allocation"]["guard"])
        guard["source_identity"]["healthy_android"] = 1
        strict_cases.append(
            lambda: M.validate_base_allocation(
                guard,
                M.canonical_bytes(guard),
                bundle["allocation"]["opening"],
                bundle["allocation"]["opening_raw"],
                bundle["allocation"]["session"],
                bundle["allocation"]["session_raw"],
            )
        )

        session = copy.deepcopy(bundle["allocation"]["session"])
        session["child_counters"]["normal_reboots"] = False
        strict_cases.append(
            lambda: M.validate_base_allocation(
                bundle["allocation"]["guard"],
                bundle["allocation"]["guard_raw"],
                bundle["allocation"]["opening"],
                bundle["allocation"]["opening_raw"],
                session,
                M.canonical_bytes(session),
            )
        )

        accounting = copy.deepcopy(bundle["opening"])
        accounting["allocation_source_identity"]["healthy_android"] = 1
        strict_cases.append(
            lambda: M.validate_accounting_opening(
                accounting,
                M.canonical_bytes(accounting),
                validated_allocation(bundle),
                bundle["allocation"]["guard_raw"],
                bundle["allocation"]["opening_raw"],
                bundle["allocation"]["session_raw"],
            )
        )

        accounting_expiry = copy.deepcopy(bundle["opening"])
        accounting_expiry["first_current_context"]["campaign_expires_at"] = float(
            accounting_expiry["first_current_context"]["campaign_expires_at"]
        )
        accounting_expiry["first_current_context_sha256"] = M.sha256_bytes(
            M.canonical_bytes(accounting_expiry["first_current_context"])
        )
        strict_cases.append(
            lambda: M.validate_accounting_opening(
                accounting_expiry,
                M.canonical_bytes(accounting_expiry),
                validated_allocation(bundle),
                bundle["allocation"]["guard_raw"],
                bundle["allocation"]["opening_raw"],
                bundle["allocation"]["session_raw"],
            )
        )

        lease_bool = copy.deepcopy(bundle["lease"])
        lease_bool["coordinator_context"]["child_counters"][
            "normal_reboots"
        ] = False
        lease_bool["coordinator_context_sha256"] = M.sha256_bytes(
            M.canonical_bytes(lease_bool["coordinator_context"])
        )
        strict_cases.append(
            lambda: M.validate_lease(
                lease_bool,
                M.canonical_bytes(lease_bool),
                bundle["opening"],
                bundle["opening_raw"],
                bundle["allocation"]["session"],
                bundle["allocation"]["session_raw"],
            )
        )

        lease_expiry = copy.deepcopy(bundle["lease"])
        lease_expiry["coordinator_context"]["session_expires_at"] = float(
            lease_expiry["coordinator_context"]["session_expires_at"]
        )
        lease_expiry["coordinator_context_sha256"] = M.sha256_bytes(
            M.canonical_bytes(lease_expiry["coordinator_context"])
        )
        strict_cases.append(
            lambda: M.validate_lease(
                lease_expiry,
                M.canonical_bytes(lease_expiry),
                bundle["opening"],
                bundle["opening_raw"],
                bundle["allocation"]["session"],
                bundle["allocation"]["session_raw"],
            )
        )

        lease_reservation = copy.deepcopy(bundle["lease"])
        lease_reservation["reservation_bytes"] = float(
            lease_reservation["reservation_bytes"]
        )
        strict_cases.append(
            lambda: M.validate_lease(
                lease_reservation,
                M.canonical_bytes(lease_reservation),
                bundle["opening"],
                bundle["opening_raw"],
                bundle["allocation"]["session"],
                bundle["allocation"]["session_raw"],
            )
        )

        intent_reservation = copy.deepcopy(bundle["intent"])
        intent_reservation["reservation_bytes"] = float(
            intent_reservation["reservation_bytes"]
        )
        strict_cases.append(
            lambda: M._validate_intent_shape(
                intent_reservation, M.canonical_bytes(intent_reservation)
            )
        )

        for wrong_size in (float(bundle["lease"]["expected_host_tool"]["size"]), True):
            lease_tool = copy.deepcopy(bundle["lease"])
            lease_tool["expected_host_tool"]["size"] = wrong_size
            strict_cases.append(
                lambda lease_tool=lease_tool: M.validate_lease(
                    lease_tool,
                    M.canonical_bytes(lease_tool),
                    bundle["opening"],
                    bundle["opening_raw"],
                    bundle["allocation"]["session"],
                    bundle["allocation"]["session_raw"],
                )
            )

        result = copy.deepcopy(bundle["result"])
        result["actual_evidence_bytes"] = float(result["actual_evidence_bytes"])
        strict_cases.append(
            lambda: validate_result_bundle(
                bundle, result, M.canonical_bytes(result)
            )
        )

        self.assertEqual(len(strict_cases), 11)
        for case in strict_cases:
            reject(case)

    def test_62_retained_source_receipts_require_exact_absolute_content(self):
        bundle = oracle_bundle()
        changed = copy.deepcopy(bundle["opening"])
        changed["sources"]["owner"]["path"] = Path(
            changed["sources"]["owner"]["path"]
        ).name
        reject(
            M.validate_accounting_opening,
            changed,
            M.canonical_bytes(changed),
            validated_allocation(bundle),
            bundle["allocation"]["guard_raw"],
            bundle["allocation"]["opening_raw"],
            bundle["allocation"]["session_raw"],
        )

    def test_63_invalid_three_root_preflight_rejections_leave_no_artifact(self):
        for variant in ("leaf", "base", "evidence"):
            tree = Tree()
            try:
                if variant == "leaf":
                    write_file(tree.leaf / "foreign", b"x")
                elif variant == "base":
                    mkdir(tree.base / "campaigns")
                    mkdir(tree.base / "campaigns" / ("a" * 32))
                else:
                    write_file(tree.evidence / "foreign", b"x")
                before = root_snapshot(tree.base, tree.evidence, tree.leaf)
                reject(tree.install)
                self.assertEqual(
                    root_snapshot(tree.base, tree.evidence, tree.leaf), before
                )
            finally:
                tree.close()

    def test_64_existing_lock_retry_reflushes_file_and_leaf_after_fsync_cut(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            original = os.fsync
            failed = False

            def fail_parent_once(descriptor):
                nonlocal failed
                if descriptor == parent and not failed:
                    failed = True
                    raise OSError(errno.EIO, "injected leaf fsync cut")
                return original(descriptor)

            try:
                with mock.patch.object(M.os, "fsync", side_effect=fail_parent_once):
                    reject(M._ExclusiveCoordinatorLock(parent, create=True).__enter__)
                self.assertTrue((Path(temporary) / M.LOCK_NAME).is_file())
                calls = []

                def record(descriptor):
                    calls.append(descriptor)
                    return original(descriptor)

                with mock.patch.object(M.os, "fsync", side_effect=record):
                    with M._ExclusiveCoordinatorLock(parent, create=True):
                        pass
                self.assertIn(parent, calls)
                self.assertGreaterEqual(len(calls), 2)
            finally:
                os.close(parent)

    def test_65_existing_recovery_dir_retry_reopens_across_parent_fsync_cut(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            original = os.fsync
            failed = False

            def fail_parent_once(descriptor):
                nonlocal failed
                if descriptor == parent and not failed:
                    failed = True
                    raise OSError(errno.EIO, "injected recovery-dir fsync cut")
                return original(descriptor)

            try:
                with mock.patch.object(M.os, "fsync", side_effect=fail_parent_once):
                    reject(M._open_or_create_recovery_directory, parent)
                self.assertTrue((Path(temporary) / M.RECOVERY_DIRECTORY).is_dir())
                descriptor = M._open_or_create_recovery_directory(parent)
                try:
                    self.assertEqual(
                        stat.S_IMODE(os.fstat(descriptor).st_mode), 0o700
                    )
                finally:
                    os.close(descriptor)
            finally:
                os.close(parent)

    def test_66_unqualified_self_rejects_before_any_fixed_root_access(self):
        gate_names = (
            "RECOVERY_V1_QUALIFIED",
            "RECOVERY_WRITER_ACTIVE",
            "RECOVERY_MANIFEST_ACTIVE",
            "RECOVERY_CONTRACT_ACTIVE",
        )
        patches = [mock.patch.object(M, name, True) for name in gate_names]
        for patch in patches:
            patch.start()
        try:
            with mock.patch.object(M, "_read_self_bytes", return_value=b"drift"), mock.patch.object(
                M, "_open_fixed_root", side_effect=AssertionError("root opened")
            ):
                reject(M._install_recovery_bundle_impl)
        finally:
            for patch in reversed(patches):
                patch.stop()

    def test_67_install_reopen_detects_base_and_evidence_root_swaps(self):
        for label in ("base", "evidence"):
            tree = Tree()
            original = M._atomic_publish_at
            calls = 0
            original_path = getattr(tree, label)
            moved = tree.root / f"{label}-moved"

            def publish_then_swap(parent, name, payload):
                nonlocal calls
                result = original(parent, name, payload)
                calls += 1
                if calls == 2:
                    os.rename(original_path, moved)
                    mkdir(original_path)
                return result

            try:
                with mock.patch.object(
                    M, "_atomic_publish_at", side_effect=publish_then_swap
                ):
                    reject(tree.install)
            finally:
                tree.close()

    def test_68_unbound_private_bundle_is_inspectable_but_not_loadable(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            core = SCRIPT.read_bytes()
            write_file(Path(temporary) / M.RECOVERY_CORE_NAME, core)
            write_file(
                Path(temporary) / M.RECOVERY_MANIFEST_NAME,
                M.canonical_bytes(M.build_manifest(core)),
            )
            recovery = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                reject(M._model_verify_private_core_bytes, recovery)
            finally:
                os.close(recovery)

    def test_69_runtime_binding_global_cannot_override_unbound_source_bytes(self):
        gate_names = (
            "RECOVERY_V1_QUALIFIED",
            "RECOVERY_WRITER_ACTIVE",
            "RECOVERY_MANIFEST_ACTIVE",
            "RECOVERY_CONTRACT_ACTIVE",
        )
        binding = {
            "binding_complete": True,
            "normalized_sha256": "a" * 64,
            "schema": M.RUNNER_BINDING_SCHEMA,
            "status": "BOUND",
        }
        patches = [mock.patch.object(M, name, True) for name in gate_names]
        for patch in patches:
            patch.start()
        try:
            with mock.patch.object(M, "FUTURE_RUNNER_BINDING", binding), mock.patch.object(
                M, "_open_fixed_root", side_effect=AssertionError("root opened")
            ):
                reject(M._install_recovery_bundle_impl)
        finally:
            for patch in reversed(patches):
                patch.stop()

    def test_70_coherent_float_lease_chain_cannot_self_certify_intent(self):
        bundle = oracle_bundle()
        lease = copy.deepcopy(bundle["lease"])
        lease["reservation_bytes"] = float(lease["reservation_bytes"])
        lease_raw = M.canonical_bytes(lease)
        intent = copy.deepcopy(bundle["intent"])
        intent["coordinator_lease_sha256"] = M.sha256_bytes(lease_raw)
        intent_raw = M.canonical_bytes(intent)
        reject(
            M.validate_intent,
            intent,
            intent_raw,
            lease,
            lease_raw,
            bundle["opening"],
            bundle["opening_raw"],
            bundle["allocation"]["guard_raw"],
            bundle["allocation"]["opening_raw"],
            bundle["allocation"]["session_raw"],
        )

    def test_71_scanner_never_reopens_rotated_public_oracle_paths(self):
        tree = Tree()
        original = os.open
        forbidden = {str(path) for path in ORACLE_PATHS.values()}

        def reject_oracle_open(path, *args, **kwargs):
            if os.fspath(path) in forbidden:
                raise AssertionError("public oracle reopened after private copy")
            return original(path, *args, **kwargs)

        try:
            tree.install()
            tree.populate("complete")
            with mock.patch.object(M.os, "open", side_effect=reject_oracle_open):
                scan = tree.scan()
            self.assertTrue(scan["completion_validated"])
        finally:
            tree.close()

    def test_72_coherent_chronology_rewinds_cannot_certify_chain(self):
        bundle = oracle_bundle()
        accounting = copy.deepcopy(bundle["opening"])
        accounting["recorded_at"] = bundle["allocation"]["opening"]["opened_at"] - 1
        accounting["first_current_context"]["current_time"] = accounting["recorded_at"]
        accounting["first_current_context_sha256"] = M.sha256_bytes(
            M.canonical_bytes(accounting["first_current_context"])
        )
        reject(
            M.validate_accounting_opening,
            accounting,
            M.canonical_bytes(accounting),
            validated_allocation(bundle),
            bundle["allocation"]["guard_raw"],
            bundle["allocation"]["opening_raw"],
            bundle["allocation"]["session_raw"],
        )

        rewound = bundle["opening"]["recorded_at"] - 1
        lease = copy.deepcopy(bundle["lease"])
        lease["issued_at"] = rewound
        lease["coordinator_context"]["current_time"] = rewound
        lease["coordinator_context_sha256"] = M.sha256_bytes(
            M.canonical_bytes(lease["coordinator_context"])
        )
        lease_raw = M.canonical_bytes(lease)
        intent = copy.deepcopy(bundle["intent"])
        intent["coordinator_lease_sha256"] = M.sha256_bytes(lease_raw)
        intent["lease_issued_at"] = rewound
        intent["lease_observed_at"] = rewound
        intent["mirrored_at"] = rewound
        intent_raw = M.canonical_bytes(intent)
        self.assertEqual(M._validate_intent_shape(intent, intent_raw), intent)
        reject(
            M.validate_intent,
            intent,
            intent_raw,
            lease,
            lease_raw,
            bundle["opening"],
            bundle["opening_raw"],
            bundle["allocation"]["guard_raw"],
            bundle["allocation"]["opening_raw"],
            bundle["allocation"]["session_raw"],
        )

    def test_73_fifo_rejects_without_blocking_direct_self_and_existing_publish(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            path = Path(temporary) / M.RECOVERY_CORE_NAME
            os.mkfifo(path, 0o400)
            os.chmod(path, 0o400)
            try:
                reject(
                    M._read_regular_at,
                    parent,
                    M.RECOVERY_CORE_NAME,
                    "fifo core",
                    M.RECOVERY_CORE_MAX_BYTES,
                )
                reject(
                    M._atomic_publish_at,
                    parent,
                    M.RECOVERY_CORE_NAME,
                    b"core",
                )
                with mock.patch.object(M, "__file__", str(path)):
                    reject(M._read_self_bytes)
            finally:
                os.close(parent)

    def test_74_scanner_rejects_fifo_at_every_file_class(self):
        for variant in ("lock", "core", "manifest", "journal", "evidence"):
            tree = Tree()
            try:
                tree.install()
                if variant in ("journal", "evidence"):
                    _, evidence_session = tree.populate(
                        "lease" if variant == "journal" else "partial"
                    )
                if variant == "lock":
                    path = tree.leaf / M.LOCK_NAME
                elif variant == "core":
                    path = tree.leaf / M.RECOVERY_DIRECTORY / M.RECOVERY_CORE_NAME
                elif variant == "manifest":
                    path = (
                        tree.leaf
                        / M.RECOVERY_DIRECTORY
                        / M.RECOVERY_MANIFEST_NAME
                    )
                elif variant == "journal":
                    path = tree.leaf / "public-health-read-lease-000001.json"
                else:
                    path = evidence_session / "read-000001" / "cmd-01.stdout.bin"
                os.unlink(path)
                os.mkfifo(path, 0o400 if variant != "lock" else 0o600)
                os.chmod(path, 0o400 if variant != "lock" else 0o600)
                reject(tree.scan)
            finally:
                tree.close()

    def test_75_directory_enumeration_stops_at_exact_entry_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            for index in range(3):
                write_file(Path(temporary) / f"node-{index}", b"x")
            parent = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try:
                reject(M._directory_names, parent, "bounded directory", 2)
                reject(M._directory_names, parent, "bool bound", True)
                self.assertEqual(
                    M._directory_names(parent, "exact directory", 3),
                    ("node-0", "node-1", "node-2"),
                )
            finally:
                os.close(parent)

    def test_76_evidence_session_open_failure_closes_every_accumulated_fd(self):
        campaign_id = "a" * 32
        session_id = "b" * 32
        campaign_name = "campaign-" + hashlib.sha256(
            campaign_id.encode()
        ).hexdigest()
        session_name = "session-" + hashlib.sha256(session_id.encode()).hexdigest()
        for depth in (
            "missing-campaigns",
            "campaigns-namespace",
            "campaign-namespace",
            "sessions-namespace",
            "session-mode",
        ):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                os.chmod(root, 0o700)
                if depth != "missing-campaigns":
                    mkdir(root / "campaigns")
                if depth == "campaigns-namespace":
                    write_file(root / "campaigns" / "foreign", b"x")
                if depth in (
                    "campaign-namespace",
                    "sessions-namespace",
                    "session-mode",
                ):
                    mkdir(root / "campaigns" / campaign_name)
                campaign = root / "campaigns" / campaign_name
                if depth == "campaign-namespace":
                    write_file(campaign / "foreign", b"x")
                if depth in ("sessions-namespace", "session-mode"):
                    mkdir(campaign / "sessions")
                sessions = campaign / "sessions"
                if depth == "sessions-namespace":
                    write_file(sessions / "foreign", b"x")
                if depth == "session-mode":
                    mkdir(sessions / session_name)
                    os.chmod(sessions / session_name, 0o755)
                descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    before = len(os.listdir("/proc/self/fd"))
                    for _ in range(25):
                        reject(
                            M._open_evidence_session,
                            descriptor,
                            campaign_id,
                            session_id,
                        )
                    self.assertEqual(len(os.listdir("/proc/self/fd")), before)
                finally:
                    os.close(descriptor)

if __name__ == "__main__":
    unittest.main()
