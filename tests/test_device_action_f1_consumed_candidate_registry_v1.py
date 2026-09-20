from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/consumed_candidate_registry_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("consumed_candidate_registry_tested", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("registry source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConsumedCandidateRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def identity(self, *, profile_suffix: str = "", ap: str | None = None, member: str = "c"):
        if ap is None:
            ap = "a" if not profile_suffix else "d"
        profile = {
            "schema": "qualification-profile-v1",
            "profile_id": "profile-1" + profile_suffix,
            "target": {"model": "SM-S906N", "device": "g0q", "firmware_incremental": "FYG8"},
        }
        manifest = {
            "manifest_id": "manifest-1" + profile_suffix,
            "run_id": "run-1" + profile_suffix,
            "allowed_member": "boot.img.lz4",
            "candidate_ap": {"size": 17, "sha256": ap * 64},
        }
        return self.module.derive_candidate_identity(
            profile,
            manifest,
            manifest["candidate_ap"]["sha256"],
            approval_binding_sha256="b" * 64,
            candidate_receipt={
                "size": 17,
                "sha256": manifest["candidate_ap"]["sha256"],
                "member": {"name": "boot.img.lz4", "size": 9, "sha256": member * 64},
            },
        )

    def relocated_fixture(self, root):
        module = self.module
        (root / 'workspace/private').mkdir(parents=True)
        module.initialize(root)
        module.claim(root, self.identity())
        registry = module.registry_root(root)
        activation_bytes = (registry / module.ACTIVATION_NAME).read_bytes()
        activation = module._parse_json(activation_bytes, 'fixture activation')
        for name, payload in ((module.LOCK_NAME, module.LOCK_PAYLOAD),
                              (module.SESSION_LOCK_NAME, module.SESSION_LOCK_PAYLOAD)):
            replacement = registry / (name + '.replacement')
            replacement.write_bytes(payload); replacement.chmod(0o600)
            os.replace(replacement, registry / name)
        evidence = root / 'workspace/private/migration-evidence.json'
        evidence.write_bytes(module._canonical({'old_and_new_bytes_identical': True}))
        evidence.chmod(0o400)
        locks = {'writer_lock_identity': module.LOCK_NAME, 'session_lock_identity': module.SESSION_LOCK_NAME}
        value = dict(schema='device_action_f1_registry_host_relocation_v1',
            activation=module._identity(activation_bytes), old_locks={k: activation[k] for k in locks},
            new_locks={k: module._lock_path_identity(registry / name) for k, name in locks.items()},
            records_prefix=[dict(name=p.name, **module._identity(p.read_bytes()))
                            for p in sorted((registry / module.RECORDS_NAME).iterdir())],
            checkpoint_head=module._identity((registry / module.HEAD_NAME).read_bytes()),
            evidence=dict(path=str(evidence), **module._identity(evidence.read_bytes())))
        data = module._canonical(value)
        module._write_no_replace(root / module.RELOCATION_PATH, data, mode=0o400)
        return value, module._identity(data), activation_bytes

    def test_reviewed_relocation_preserves_claims_and_allows_normal_append(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value, receipt, original = self.relocated_fixture(root)
            with mock.patch.object(self.module, 'RELOCATION_RECORD', receipt):
                self.assertEqual(self.module.validate(root)['record_count'], 1)
                with self.assertRaises(self.module.DuplicateCandidateClaim):
                    self.module.preflight_candidate(root, self.identity())
                with self.module.target_session_lease(root):
                    self.module.claim(root, self.identity(profile_suffix='-after-move'))
                self.assertEqual(self.module.validate(root)['record_count'], 2)
                self.assertEqual((self.module.registry_root(root) / self.module.ACTIVATION_NAME).read_bytes(), original)

    def test_unreviewed_relocation_receipt_cannot_authorize_inode_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.relocated_fixture(root)
            with self.assertRaisesRegex(self.module.RegistryError, 'not the exact reviewed receipt'):
                self.module.validate(root)

    def test_relocation_prefix_cannot_be_lost_even_with_a_valid_older_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value, receipt, _ = self.relocated_fixture(root)
            registry = self.module.registry_root(root)
            (registry / self.module.RECORDS_NAME / value['records_prefix'][0]['name']).unlink()
            self.module._write_head(registry / self.module.HEAD_NAME,
                                    self.module._head_value(0, -1, self.module.ZERO_SHA256))
            with mock.patch.object(self.module, 'RELOCATION_RECORD', receipt):
                with self.assertRaises(self.module.RegistryError): self.module.validate(root)

    def test_relocation_does_not_admit_another_lock_replacement_or_original_lock_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value, receipt, _ = self.relocated_fixture(root)
            registry = self.module.registry_root(root)
            replacement = registry / 'new-lock'
            replacement.write_bytes(self.module.LOCK_PAYLOAD); replacement.chmod(0o600)
            os.replace(replacement, registry / self.module.LOCK_NAME)
            with mock.patch.object(self.module, 'RELOCATION_RECORD', receipt):
                with self.assertRaisesRegex(self.module.RegistryError, 'lock binding differs'):
                    self.module.validate(root)
                def original_identity(path):
                    key = 'writer_lock_identity' if path.name == self.module.LOCK_NAME else 'session_lock_identity'
                    return value['old_locks'][key]
                with mock.patch.object(self.module, '_lock_path_identity', side_effect=original_identity):
                    with self.assertRaisesRegex(self.module.RegistryError, 'lock binding differs'):
                        self.module.validate(root)

    def test_append_chain_duplicate_and_parse_release_are_durable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            identity = self.identity()
            self.module.preflight_candidate(root, identity)
            claim = self.module.claim(root, identity)
            with self.assertRaises(self.module.DuplicateCandidateClaim):
                self.module.claim(root, identity)
            profile_drift = self.identity(profile_suffix="-profile-drift", ap="a", member="c")
            self.assertEqual(profile_drift["candidate_key"], identity["candidate_key"])
            with self.assertRaises(self.module.DuplicateCandidateClaim):
                self.module.preflight_candidate(root, profile_drift)
            firmware_profile = {
                "schema": "qualification-profile-v1",
                "profile_id": "profile-firmware-drift",
                "target": {
                    "model": "SM-S906N",
                    "device": "g0q",
                    "firmware_incremental": "FYG8-successor",
                },
            }
            firmware_manifest = {
                "manifest_id": "manifest-firmware-drift",
                "run_id": "run-firmware-drift",
                "allowed_member": "boot.img.lz4",
                "candidate_ap": {"size": 17, "sha256": "a" * 64},
            }
            firmware_drift = self.module.derive_candidate_identity(
                firmware_profile,
                firmware_manifest,
                "a" * 64,
                approval_binding_sha256="e" * 64,
                candidate_receipt={
                    "size": 17,
                    "sha256": "a" * 64,
                    "member": {
                        "name": "boot.img.lz4",
                        "size": 9,
                        "sha256": "c" * 64,
                    },
                },
            )
            self.assertEqual(firmware_drift["candidate_key"], identity["candidate_key"])
            with self.assertRaises(self.module.DuplicateCandidateClaim):
                self.module.preflight_candidate(root, firmware_drift)
            forged = dict(identity)
            forged["candidate_key"] = "f" * 64
            with self.assertRaises(self.module.RegistryError):
                self.module.claim(root, forged)
            released = self.module.release(root, claim)
            self.assertEqual(self.module.release(root, claim)["record"], released["record"])
            with self.assertRaises(self.module.RegistryError):
                self.module.release(root, claim, device_session_started=True)
            without_owner = dict(claim)
            without_owner.pop("record")
            with self.assertRaises(self.module.RegistryError):
                self.module.release(root, without_owner)
            wrong = dict(claim)
            wrong["claim_id"] = "f" * 64
            with self.assertRaises(self.module.RegistryError):
                self.module.release(root, wrong)
            self.assertEqual(self.module.validate(root)["record_count"], 2)
            self.assertIsNone(self.module.active_claim(root, identity["candidate_key"]))

    def test_same_physical_target_uses_nonblocking_session_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            second = self.identity(profile_suffix="-renamed", ap="d", member="e")
            code = """import importlib.util, pathlib, sys
p = pathlib.Path(sys.argv[1])
r = pathlib.Path(sys.argv[2])
s = importlib.util.spec_from_file_location('registry_busy_test', p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
try:
    with m.target_session_lease(r):
        raise SystemExit(9)
except m.RegistryUnavailable:
    raise SystemExit(0)
raise SystemExit(8)
"""
            with self.module.target_session_lease(root):
                result = subprocess.run(
                    ["python3", "-c", code, str(SCRIPT), str(root)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.module.preflight_candidate(root, second)
            self.module.claim(root, second)

    def test_complete_tail_repairs_once_and_two_or_partial_tails_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            first = self.identity()
            second = self.identity(profile_suffix="-second", ap="d", member="e")
            self.module.claim(root, first)
            registry = root / "workspace/private" / self.module.REGISTRY_DIR_NAME
            records = registry / self.module.RECORDS_NAME
            previous = self.module.history(root)[-1]["record_sha256"]
            claim_id = self.module._claim_id(second["candidate_key"], second["run_id"], second["approval_binding_sha256"], 1)
            tail = {
                "schema": self.module.RECORD_SCHEMA,
                "sequence": 1,
                "event": "claim",
                **{key: value for key, value in second.items() if key != "schema"},
                "claim_id": claim_id,
                "previous_record_sha256": previous,
                "release_reason": None,
                "device_session_started": None,
                "partition_transfer": None,
                "record_sha256": self.module.ZERO_SHA256,
            }
            tail["record_sha256"] = self.module._record_digest(tail)
            self.module._write_no_replace(records / "00000001-claim.json", self.module._canonical(tail), mode=0o400)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)
            # A writer repairs one complete chained tail before appending.
            with self.assertRaises(self.module.DuplicateCandidateClaim):
                self.module.claim(root, second)
            self.assertEqual(self.module.validate(root)["record_count"], 2)
            third = self.identity(profile_suffix="-third", ap="e", member="f")
            previous = self.module.history(root)[-1]["record_sha256"]
            third_id = self.module._claim_id(third["candidate_key"], third["run_id"], third["approval_binding_sha256"], 2)
            tail_one = {
                "schema": self.module.RECORD_SCHEMA,
                "sequence": 2,
                "event": "claim",
                **{key: value for key, value in third.items() if key != "schema"},
                "claim_id": third_id,
                "previous_record_sha256": previous,
                "release_reason": None,
                "device_session_started": None,
                "partition_transfer": None,
                "record_sha256": self.module.ZERO_SHA256,
            }
            tail_one["record_sha256"] = self.module._record_digest(tail_one)
            fourth = self.identity(profile_suffix="-fourth", ap="f", member="a")
            fourth_id = self.module._claim_id(fourth["candidate_key"], fourth["run_id"], fourth["approval_binding_sha256"], 3)
            tail_two = {
                "schema": self.module.RECORD_SCHEMA,
                "sequence": 3,
                "event": "claim",
                **{key: value for key, value in fourth.items() if key != "schema"},
                "claim_id": fourth_id,
                "previous_record_sha256": tail_one["record_sha256"],
                "release_reason": None,
                "device_session_started": None,
                "partition_transfer": None,
                "record_sha256": self.module.ZERO_SHA256,
            }
            tail_two["record_sha256"] = self.module._record_digest(tail_two)
            self.module._write_no_replace(records / "00000002-claim.json", self.module._canonical(tail_one), mode=0o400)
            self.module._write_no_replace(records / "00000003-claim.json", self.module._canonical(tail_two), mode=0o400)
            with self.assertRaises(self.module.RegistryError):
                self.module.claim(root, third)
            (records / "00000002-claim.json").unlink()
            (records / "00000003-claim.json").unlink()
            partial = records / "00000002-claim.json"
            partial.write_bytes(b"{\"partial\":")
            partial.chmod(0o400)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)

    def test_record_symlink_hardlink_and_lock_replacement_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            self.module.claim(root, self.identity())
            registry = root / "workspace/private" / self.module.REGISTRY_DIR_NAME
            records = registry / self.module.RECORDS_NAME
            record = records / "00000000-claim.json"
            symlink = records / "00000001-claim.json"
            symlink.symlink_to(record)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)
            symlink.unlink()
            hardlink = records / "00000001-claim.json"
            hardlink.hardlink_to(record)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)
            hardlink.unlink()
            lock = registry / self.module.LOCK_NAME
            replacement = registry / "writer.lock.replacement"
            replacement.write_bytes(self.module.LOCK_PAYLOAD)
            replacement.chmod(0o600)
            lock.unlink()
            replacement.rename(lock)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)

    def test_synchronized_lock_device_renumber_keeps_inode_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            registry = root / "workspace/private" / self.module.REGISTRY_DIR_NAME
            activation_path = registry / self.module.ACTIVATION_NAME
            activation = self.module._parse_json(
                activation_path.read_bytes(), "fixture activation"
            )
            current = {
                "writer_lock_identity": self.module._lock_path_identity(
                    registry / self.module.LOCK_NAME
                ),
                "session_lock_identity": self.module._lock_path_identity(
                    registry / self.module.SESSION_LOCK_NAME
                ),
            }

            def publish(value):
                activation_path.chmod(0o600)
                activation_path.write_bytes(self.module._canonical(value))
                activation_path.chmod(0o400)

            for name in current:
                activation[name] = {
                    **current[name],
                    "st_dev": current[name]["st_dev"] + 1,
                }
            publish(activation)
            self.assertEqual(self.module.validate(root)["record_count"], 0)

            asymmetric = {
                **activation,
                "session_lock_identity": current["session_lock_identity"],
            }
            publish(asymmetric)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)

            replaced = self.module._parse_json(
                self.module._canonical(activation), "copied activation"
            )
            replaced["writer_lock_identity"]["st_ino"] += 1
            publish(replaced)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)

    def test_lock_replacement_between_layout_check_and_open_fails_closed(self):
        for lock_name, operation in (
            (self.module.LOCK_NAME, lambda root: self.module.claim(root, self.identity())),
            (self.module.SESSION_LOCK_NAME, lambda root: self.module.target_session_lease(root).__enter__()),
        ):
            with self.subTest(lock=lock_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "workspace/private").mkdir(parents=True)
                self.module.initialize(root)
                registry = root / "workspace/private" / self.module.REGISTRY_DIR_NAME
                target = registry / lock_name
                payload = (
                    self.module.LOCK_PAYLOAD
                    if lock_name == self.module.LOCK_NAME
                    else self.module.SESSION_LOCK_PAYLOAD
                )
                real_open = self.module.os.open
                replaced = False

                def replace_before_rw_open(path, flags, *args, **kwargs):
                    nonlocal replaced
                    candidate = Path(path)
                    if (
                        not replaced
                        and candidate == target
                        and flags & os.O_ACCMODE == os.O_RDWR
                    ):
                        replacement = target.with_name(target.name + ".race")
                        replacement.write_bytes(payload)
                        replacement.chmod(0o600)
                        os.replace(replacement, target)
                        replaced = True
                    return real_open(path, flags, *args, **kwargs)

                with mock.patch.object(
                    self.module.os, "open", new=replace_before_rw_open
                ):
                    with self.assertRaises(self.module.RegistryError):
                        operation(root)
                self.assertTrue(replaced)

    def test_single_head_temp_is_writer_recoverable_but_two_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            first = self.identity()
            second = self.identity(profile_suffix="-temp", ap="d", member="e")
            self.module.claim(root, first)
            registry = root / "workspace/private" / self.module.REGISTRY_DIR_NAME
            temp = registry / ".head.json.next-1-2"
            temp.write_bytes((registry / self.module.HEAD_NAME).read_bytes())
            temp.chmod(0o400)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)
            self.module.claim(root, second)
            self.assertFalse(temp.exists())
            self.assertEqual(self.module.validate(root)["record_count"], 2)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            self.module.claim(root, self.identity())
            registry = root / "workspace/private" / self.module.REGISTRY_DIR_NAME
            head = (registry / self.module.HEAD_NAME).read_bytes()
            for name in (".head.json.next-1-2", ".head.json.next-3-4"):
                path = registry / name
                path.write_bytes(head)
                path.chmod(0o400)
            with self.assertRaises(self.module.RegistryError):
                self.module.validate(root)
            with self.assertRaises(self.module.RegistryError):
                self.module.claim(root, self.identity(profile_suffix="-two", ap="d", member="e"))

    def test_legacy_activation_requires_all_42_entries(self):
        authority = self.module._legacy_authority()
        self.assertEqual(len(authority), 42)
        self.assertEqual(len({entry["candidate_ap_sha256"] for entry in authority}), 42)
        entry = authority[0]
        profile = {
            "schema": "qualification-profile-v1",
            "profile_id": "legacy-deny-profile",
            "target": {"model": "SM-S906N", "device": "g0q", "firmware_incremental": "FYG8"},
        }
        manifest = {
            "manifest_id": "legacy-deny-manifest",
            "run_id": "legacy-deny-run",
            "allowed_member": "boot.img.lz4",
            "candidate_ap": {"size": entry["candidate_ap_size"], "sha256": entry["candidate_ap_sha256"]},
        }
        legacy_identity = self.module.derive_candidate_identity(
            profile,
            manifest,
            entry["candidate_ap_sha256"],
            approval_binding_sha256="b" * 64,
            candidate_receipt={
                "size": entry["candidate_ap_size"],
                "sha256": entry["candidate_ap_sha256"],
                "member": {
                    "name": entry["boot_member_name"],
                    "size": entry["boot_member_size"],
                    "sha256": entry["boot_member_sha256"],
                },
            },
        )
        self.module.validate(ROOT)
        with self.assertRaises(self.module.DuplicateCandidateClaim):
            self.module.preflight_candidate(ROOT, legacy_identity)
        with self.assertRaises(self.module.DuplicateCandidateClaim):
            self.module.claim(ROOT, legacy_identity)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "workspace/private").mkdir(parents=True)
            self.module.initialize(root)
            registry = root / "workspace/private" / self.module.REGISTRY_DIR_NAME
            activation = registry / self.module.ACTIVATION_NAME
            value = self.module._parse_json(activation.read_bytes(), "activation")
            value["legacy_candidates"] = authority
            activation.chmod(0o600)
            activation.write_bytes(self.module._canonical(value))
            activation.chmod(0o400)
            original_root = self.module.REPO_ROOT
            self.module.REPO_ROOT = root.resolve()
            try:
                self.module.validate(root)
                value["legacy_candidates"] = authority[:-1]
                activation.chmod(0o600)
                activation.write_bytes(self.module._canonical(value))
                activation.chmod(0o400)
                with self.assertRaises(self.module.RegistryError):
                    self.module.validate(root)
            finally:
                self.module.REPO_ROOT = original_root

    def test_legacy_private_artifact_containment_and_link_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "workspace/private"
            private.mkdir(parents=True)
            direct = private / "candidate.ap"
            direct.write_bytes(b"candidate")
            self.assertEqual(self.module._read_legacy_private_regular(root, direct, "direct", 100), b"candidate")
            outside = root / "outside.ap"
            outside.write_bytes(b"outside")
            with self.assertRaises(self.module.RegistryError):
                self.module._read_legacy_private_regular(root, outside, "outside", 100)
            link = private / "link.ap"
            link.symlink_to(direct)
            with self.assertRaises(self.module.RegistryError):
                self.module._read_legacy_private_regular(root, link, "symlink", 100)
            hardlink = private / "hardlink.ap"
            hardlink.hardlink_to(direct)
            self.assertEqual(self.module._read_legacy_private_regular(root, hardlink, "bounded-hardlink", 100), b"candidate")


if __name__ == "__main__":
    unittest.main()
