import ast
import copy
import hashlib
import importlib.util
import inspect
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
LOADER = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py"
)
FINALIZER = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py"
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


L = load("s20plus_recovery_loader_v1_h0_tested", LOADER)
F = load("s20plus_recovery_finalizer_for_loader_test", FINALIZER)


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


class Bundle:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.recovery = self.root / "recovery-v1"
        mkdir(self.recovery)
        self.core = FINALIZER.read_bytes()
        self.manifest = F.canonical_bytes(F.build_manifest(self.core))
        write_file(self.recovery / L.RECOVERY_CORE_NAME, self.core)
        write_file(self.recovery / L.RECOVERY_MANIFEST_NAME, self.manifest)
        self.descriptor = os.open(
            self.recovery, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        )

    def replace(self, name, payload=None, mode=0o400, kind="file"):
        os.close(self.descriptor)
        path = self.recovery / name
        if path.exists() or path.is_symlink():
            path.unlink()
        if kind == "file":
            write_file(path, payload, mode)
        elif kind == "symlink":
            os.symlink(self.root / "outside", path)
        elif kind == "fifo":
            os.mkfifo(path, mode)
        else:
            raise AssertionError(kind)
        self.descriptor = os.open(
            self.recovery, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        )

    def close(self):
        os.close(self.descriptor)
        self.temporary.cleanup()


class RecoveryLoaderV1H0Test(unittest.TestCase):
    def test_01_plan_is_permanent_render_only_and_all_gates_false(self):
        plan = L.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_PUBLIC_HEALTH_RECOVERY_LOADER_V1_PASS_GO_NOT_ACTIVE",
        )
        self.assertTrue(plan["permanent_versioned_loader"])
        for key in (
            "loader_v1_qualified",
            "finalizer_identity_active",
            "manifest_identity_active",
            "finalizer_operation_active",
            "reemit_operation_active",
            "future_runner_binding_active",
            "contract_active",
            "mechanical_activation",
            "live_authority",
        ):
            self.assertIs(plan[key], False)
        self.assertEqual(plan["caller_inputs"], [])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["writes_before_activation"], [])

    def test_02_cli_has_only_render_plan_and_rejects_caller_fields(self):
        good = subprocess.run(
            [sys.executable, str(LOADER), "--render-plan"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(json.loads(good.stdout)["cli"], ["--render-plan"])
        for args in (
            [],
            ["--finalize"],
            ["--reemit"],
            ["--root", "/tmp/x"],
            ["--version", "v1"],
            ["--id", "x"],
        ):
            bad = subprocess.run(
                [sys.executable, str(LOADER), *args],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(bad.returncode, 0)
        self.assertEqual(len(inspect.signature(L.finalize_zero_command).parameters), 0)
        self.assertEqual(len(inspect.signature(L.reemit_terminal).parameters), 0)

    def test_03_operations_gate_before_any_fixed_root_open(self):
        with mock.patch.object(L, "_open_fixed_root", side_effect=AssertionError):
            with self.assertRaises(L.RecoveryLoaderV1Error):
                L.finalize_zero_command()
            with self.assertRaises(L.RecoveryLoaderV1Error):
                L.reemit_terminal()

    def test_04_static_source_has_no_command_network_or_install_surface(self):
        source = LOADER.read_bytes()
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
        for token in (
            b"Popen",
            b"check_output",
            b"adb",
            b"odin4",
            b"fastboot",
            b"os.mkdir",
            b"os.rename",
            b"os.unlink",
            b"os.remove",
        ):
            self.assertNotIn(token, source)

    def test_05_exact_bundle_verifies_and_capability_is_fresh(self):
        bundle = Bundle()
        try:
            core, manifest_raw, manifest = L._verify_bundle_at(bundle.descriptor)
            self.assertEqual(core, bundle.core)
            self.assertEqual(manifest_raw, bundle.manifest)
            self.assertEqual(manifest["core"]["sha256"], L.ALLOWED_CORE_SHA256)
            first, first_capability, _ = L._load_verified_namespace_at(
                bundle.descriptor
            )
            second, second_capability, _ = L._load_verified_namespace_at(
                bundle.descriptor
            )
            self.assertIsNot(first_capability, second_capability)
            self.assertIs(first["_LOADER_CAPABILITY"], first_capability)
            self.assertIs(second["_LOADER_CAPABILITY"], second_capability)
        finally:
            bundle.close()

    def test_06_exact_source_manifest_and_normalized_identities_match(self):
        core = FINALIZER.read_bytes()
        manifest = F.canonical_bytes(F.build_manifest(core))
        self.assertEqual(len(core), L.ALLOWED_CORE_SIZE)
        self.assertEqual(hashlib.sha256(core).hexdigest(), L.ALLOWED_CORE_SHA256)
        self.assertEqual(
            L.normalized_core_sha256(core), L.ALLOWED_CORE_NORMALIZED_SHA256
        )
        self.assertEqual(len(manifest), L.ALLOWED_MANIFEST_SIZE)
        self.assertEqual(
            hashlib.sha256(manifest).hexdigest(), L.ALLOWED_MANIFEST_SHA256
        )
        self.assertLessEqual(
            len(core) + len(manifest), L.RECOVERY_BUNDLE_MAX_BYTES
        )

    def test_07_self_consistent_rogue_core_manifest_pair_rejects(self):
        bundle = Bundle()
        try:
            rogue_core = bundle.core + b"# rogue\n"
            rogue_manifest = copy.deepcopy(
                json.loads(bundle.manifest.decode("ascii"))
            )
            rogue_manifest["core"]["size"] = len(rogue_core)
            rogue_manifest["core"]["sha256"] = hashlib.sha256(
                rogue_core
            ).hexdigest()
            rogue_raw = L.canonical_bytes(rogue_manifest)
            bundle.replace(L.RECOVERY_CORE_NAME, rogue_core)
            bundle.replace(L.RECOVERY_MANIFEST_NAME, rogue_raw)
            with self.assertRaises(L.RecoveryLoaderV1Error):
                L._verify_bundle_at(bundle.descriptor)
        finally:
            bundle.close()

    def test_08_manifest_semantic_and_canonical_tamper_rejects(self):
        bundle = Bundle()
        try:
            changed = json.loads(bundle.manifest)
            changed["replay_authorized"] = True
            bundle.replace(L.RECOVERY_MANIFEST_NAME, L.canonical_bytes(changed))
            with self.assertRaises(L.RecoveryLoaderV1Error):
                L._verify_bundle_at(bundle.descriptor)
        finally:
            bundle.close()
        bundle = Bundle()
        try:
            bundle.replace(
                L.RECOVERY_MANIFEST_NAME,
                bundle.manifest.replace(b'"caps":', b'"caps": '),
            )
            with self.assertRaises(L.RecoveryLoaderV1Error):
                L._verify_bundle_at(bundle.descriptor)
        finally:
            bundle.close()

    def test_09_core_symlink_fifo_wrong_mode_and_size_reject(self):
        for variant in ("symlink", "fifo", "mode", "size"):
            bundle = Bundle()
            try:
                if variant == "symlink":
                    (bundle.root / "outside").write_bytes(bundle.core)
                    bundle.replace(L.RECOVERY_CORE_NAME, kind="symlink")
                elif variant == "fifo":
                    bundle.replace(L.RECOVERY_CORE_NAME, kind="fifo")
                elif variant == "mode":
                    bundle.replace(L.RECOVERY_CORE_NAME, bundle.core, 0o600)
                else:
                    bundle.replace(L.RECOVERY_CORE_NAME, bundle.core + b"x")
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    L._verify_bundle_at(bundle.descriptor)
            finally:
                bundle.close()

    def test_10_manifest_symlink_fifo_wrong_mode_and_size_reject(self):
        for variant in ("symlink", "fifo", "mode", "size"):
            bundle = Bundle()
            try:
                if variant == "symlink":
                    (bundle.root / "outside").write_bytes(bundle.manifest)
                    bundle.replace(L.RECOVERY_MANIFEST_NAME, kind="symlink")
                elif variant == "fifo":
                    bundle.replace(L.RECOVERY_MANIFEST_NAME, kind="fifo")
                elif variant == "mode":
                    bundle.replace(
                        L.RECOVERY_MANIFEST_NAME, bundle.manifest, 0o600
                    )
                else:
                    bundle.replace(
                        L.RECOVERY_MANIFEST_NAME, bundle.manifest + b"x"
                    )
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    L._verify_bundle_at(bundle.descriptor)
            finally:
                bundle.close()

    def test_11_core_and_manifest_hardlinks_reject(self):
        for name in (L.RECOVERY_CORE_NAME, L.RECOVERY_MANIFEST_NAME):
            bundle = Bundle()
            try:
                os.link(bundle.recovery / name, bundle.root / (name + ".alias"))
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    L._verify_bundle_at(bundle.descriptor)
            finally:
                bundle.close()

    def test_12_recovery_directory_symlink_and_wrong_mode_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            mkdir(real)
            link = root / "link"
            os.symlink(real, link)
            parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    L._open_child_directory(parent, "link", "link")
                os.chmod(real, 0o755)
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    L._open_child_directory(parent, "real", "wrong mode")
            finally:
                os.close(parent)

    def test_13_existing_lock_is_exact_and_exclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            leaf = Path(temporary)
            os.chmod(leaf, 0o700)
            write_file(leaf / L.LOCK_NAME, b"", 0o600)
            descriptor = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with L._ExistingCoordinatorLock(descriptor):
                    with self.assertRaises(L.RecoveryLoaderV1Error):
                        with L._ExistingCoordinatorLock(descriptor):
                            pass
                os.chmod(leaf / L.LOCK_NAME, 0o400)
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    with L._ExistingCoordinatorLock(descriptor):
                        pass
            finally:
                os.close(descriptor)

    def test_14_status_and_gate_mutations_keep_normalized_but_fail_full_hash(self):
        core = FINALIZER.read_bytes()
        for changed in (
            core.replace(
                b'STATUS = "H0_PUBLIC_HEALTH_RECOVERY_V1_FINALIZER_PASS_GO_NOT_ACTIVE"',
                b'STATUS = "H0_REVIEWED_STATUS"',
            ),
            core.replace(
                b"RECOVERY_FINALIZER_ACTIVE = False",
                b"RECOVERY_FINALIZER_ACTIVE = True",
            ),
        ):
            self.assertEqual(
                L.normalized_core_sha256(changed),
                L.ALLOWED_CORE_NORMALIZED_SHA256,
            )
            self.assertNotEqual(hashlib.sha256(changed).hexdigest(), L.ALLOWED_CORE_SHA256)

    def test_15_loader_normalization_masks_binding_cycle_literals_only(self):
        source = LOADER.read_bytes()
        self.assertEqual(
            L.normalized_self_sha256(source),
            L.EXPECTED_LOADER_NORMALIZED_SHA256,
        )
        changed_size = source.replace(
            b"ALLOWED_CORE_SIZE = 162_875",
            b"ALLOWED_CORE_SIZE = 999_999",
            1,
        )
        self.assertNotEqual(changed_size, source)
        self.assertEqual(
            L.normalized_self_sha256(changed_size),
            L.EXPECTED_LOADER_NORMALIZED_SHA256,
        )
        changed_hash = source.replace(
            L.ALLOWED_CORE_SHA256.encode(), b"a" * 64, 1
        )
        self.assertNotEqual(changed_hash, source)
        self.assertEqual(
            L.normalized_self_sha256(changed_hash),
            L.EXPECTED_LOADER_NORMALIZED_SHA256,
        )
        changed_logic = source.replace(
            b'"fixed roots are not distinct"', b'"fixed roots may alias"', 1
        )
        self.assertNotEqual(
            L.normalized_self_sha256(changed_logic),
            L.EXPECTED_LOADER_NORMALIZED_SHA256,
        )

    def test_16_unbound_manifest_cannot_satisfy_operational_binding(self):
        manifest = json.loads(
            F.canonical_bytes(F.build_manifest(FINALIZER.read_bytes()))
        )
        with self.assertRaises(L.RecoveryLoaderV1Error):
            L._require_bound_loader_manifest(manifest)
        self.assertFalse(manifest["future_runner_binding"]["binding_complete"])
        self.assertEqual(
            manifest["future_runner_binding"]["normalized_sha256"], "0" * 64
        )

    def test_17_direct_finalizer_execution_has_no_loader_capability(self):
        self.assertIsNone(F._LOADER_CAPABILITY)
        self.assertIsNone(F._VERIFIED_CORE_BYTES)
        self.assertIsNone(F._VERIFIED_MANIFEST_BYTES)
        with self.assertRaises(F.RecoveryV1Error):
            F._require_injected_loader(object(), b"{}\n")

    def test_18_reopened_fixed_root_detects_path_swap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "base"
            mkdir(original)
            held = os.open(original, os.O_RDONLY | os.O_DIRECTORY)
            moved = root / "moved"
            os.rename(original, moved)
            mkdir(original)
            with mock.patch.object(L, "FIXED_ROOTS", {"base": original}):
                try:
                    with self.assertRaises(L.RecoveryLoaderV1Error):
                        L._require_reopened_fixed_root("base", held)
                finally:
                    os.close(held)

    def test_19_caps_are_reserved_not_misclaimed_as_current_scanner_namespace(self):
        plan = L.render_plan()
        closure = plan["future_reserved_completed_closure"]
        self.assertEqual(closure["total_max_bytes"], 1_441_792)
        self.assertEqual(closure["total_file_count"], 52)
        self.assertEqual(closure["structural_max_bytes"], 49_152)
        self.assertEqual(closure["evidence_proof_max_bytes"], 507_904)
        self.assertFalse(closure["current_scanner_accepts_future_opening_and_binding"])

    def test_20_extra_bundle_name_rejects_without_compilation(self):
        bundle = Bundle()
        try:
            write_file(bundle.recovery / "extra", b"x")
            with mock.patch("builtins.compile", side_effect=AssertionError):
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    L._load_verified_namespace_at(bundle.descriptor)
        finally:
            bundle.close()

    def test_21_loader_self_read_rejects_oversized_regular_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            oversized = Path(temporary) / "oversized-loader.py"
            oversized.write_bytes(b"x" * (L.LOADER_SOURCE_MAX_BYTES + 1))
            os.chmod(oversized, 0o600)
            with mock.patch.object(L, "__file__", str(oversized)):
                with self.assertRaises(L.RecoveryLoaderV1Error):
                    L._read_self_bytes()


if __name__ == "__main__":
    unittest.main()
