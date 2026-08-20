import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_attended_owner_h0.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_n3u0_attended_owner_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusN3U0AttendedOwnerH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.plan = cls.module.render_plan()

    def write_ap(self, path, *, body=b"x", mode=0o644, trailer_valid=True):
        stream = io.BytesIO()
        with tarfile.open(
            fileobj=stream, mode="w:", format=tarfile.USTAR_FORMAT
        ) as archive:
            info = tarfile.TarInfo("boot.img.lz4")
            info.size = len(body)
            info.mode = mode
            info.uid = 0
            info.gid = 0
            info.mtime = 0
            archive.addfile(info, io.BytesIO(body))
        tar_bytes = stream.getvalue()
        md5 = hashlib.md5(tar_bytes).hexdigest().encode()
        if not trailer_valid:
            md5 = b"0" * 32
        payload = tar_bytes + md5 + b"  AP.tar\n"
        path.write_bytes(payload)
        return payload

    def test_plan_is_dormant_and_exact_target_bound(self):
        self.assertFalse(self.plan["active"])
        self.assertFalse(self.plan["live_authority"])
        self.assertEqual(
            self.plan["status"], "H0_DESIGN_ONLY_PASS_GO_NOT_ACTIVE"
        )
        self.assertEqual(
            self.plan["binding"]["target"],
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertEqual(self.plan["device_commands"], [])
        self.assertEqual(self.plan["device_writes"], [])
        self.assertEqual(self.plan["partition_transfers"], [])

    def test_candidate_and_resident_rollback_are_distinct_exact_boot_aps(self):
        candidate = self.plan["binding"]["closure"]["candidate"]
        rollback = self.plan["binding"]["closure"]["rollback"]
        self.assertEqual(candidate["sha256"], self.module.CANDIDATE_AP_SHA256)
        self.assertEqual(rollback["sha256"], self.module.ROLLBACK_AP_SHA256)
        self.assertNotEqual(candidate["sha256"], rollback["sha256"])
        self.assertEqual(candidate["member"]["name"], "boot.img.lz4")
        self.assertEqual(rollback["member"]["name"], "boot.img.lz4")
        self.assertEqual(
            self.plan["binding"]["rollback"]["boot_sha256"],
            "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc",
        )

    def test_binding_is_deterministic_and_pins_reviewed_closure(self):
        first = self.module.binding_value()
        second = self.module.binding_value()
        self.assertEqual(first, second)
        self.assertEqual(self.module.digest(first), self.plan["binding_sha256"])
        closure = first["closure"]
        self.assertEqual(
            closure["observer"]["sha256"],
            "f1c6af4123684be1122950442472de7803995345e125955322a8fd262b25e44f",
        )
        self.assertEqual(
            closure["transport"]["sha256"],
            "4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290",
        )
        self.assertEqual(
            closure["combined_review"]["sha256"],
            "f8419f86a522dae8f82bbfc46a12c11d1ef11edaaad1444d8730a272634cd520",
        )

    def test_effect_budget_is_one_shot_and_rollback_is_mandatory(self):
        budget = self.plan["effect_budget"]
        self.assertEqual(budget["candidate_download_reboots"], 1)
        self.assertEqual(budget["candidate_boot_transfers"], 1)
        self.assertEqual(budget["rollback_mode_reboots_max"], 1)
        self.assertEqual(budget["attended_physical_rollback_entries_max"], 1)
        self.assertEqual(budget["rollback_boot_transfers"], 1)
        self.assertIs(budget["candidate_replay"], False)
        self.assertIs(budget["rollback_replay"], False)
        self.assertIs(
            self.plan["binding"]["rollback"]["mandatory_after_candidate_intent"],
            True,
        )
        self.assertIn(
            "rollback still mandatory",
            self.plan["failure_rules"]["absent_or_malformed_banner"],
        )

    def test_banner_is_proof_only_and_terminal_requires_resident_root(self):
        observer = self.plan["binding"]["observer"]
        terminal = self.plan["binding"]["terminal"]
        self.assertFalse(observer["active_in_this_unit"])
        self.assertFalse(observer["stable_tty_number_required"])
        self.assertTrue(observer["same_prepared_physical_topology_required"])
        self.assertTrue(terminal["candidate_banner_is_not_terminal"])
        self.assertTrue(terminal["resident_rollback_completed"])
        self.assertTrue(terminal["final_boot_id_changed_after_rollback"])
        self.assertTrue(terminal["final_boot_id_reuses_no_prior_durable_boot"])
        self.assertTrue(terminal["exact_target_android_healthy"])
        self.assertTrue(terminal["resident_magisk_root_proved"])

    def test_boot_attribution_requires_completed_rollback_and_distinct_ids(self):
        ids = [character * 64 for character in "1234"]
        accepted = self.module.validate_boot_attribution(
            prepared_boot_id_sha256=ids[0],
            candidate_boot_id_sha256=ids[1],
            rollback_mode_boot_id_sha256=ids[2],
            final_resident_boot_id_sha256=ids[3],
            rollback_transfer_completed=True,
        )
        self.assertEqual(accepted["final_resident_boot_id_sha256"], ids[3])
        for reused in (ids[0], ids[1], ids[2]):
            with self.assertRaisesRegex(
                self.module.OwnerDesignError, "boot ID was reused"
            ):
                self.module.validate_boot_attribution(
                    prepared_boot_id_sha256=ids[0],
                    candidate_boot_id_sha256=ids[1],
                    rollback_mode_boot_id_sha256=ids[2],
                    final_resident_boot_id_sha256=reused,
                    rollback_transfer_completed=True,
                )
        with self.assertRaisesRegex(
            self.module.OwnerDesignError, "rollback completion"
        ):
            self.module.validate_boot_attribution(
                prepared_boot_id_sha256=ids[0],
                candidate_boot_id_sha256=None,
                rollback_mode_boot_id_sha256=None,
                final_resident_boot_id_sha256=ids[3],
                rollback_transfer_completed=False,
            )
        for prepared, final in ((None, ids[3]), (ids[0], None), (None, None)):
            with self.assertRaisesRegex(
                self.module.OwnerDesignError, "boot ID is required"
            ):
                self.module.validate_boot_attribution(
                    prepared_boot_id_sha256=prepared,
                    candidate_boot_id_sha256=None,
                    rollback_mode_boot_id_sha256=None,
                    final_resident_boot_id_sha256=final,
                    rollback_transfer_completed=True,
                )

    def test_symlink_or_hash_drifted_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            symlink = root / "candidate.tar.md5"
            symlink.symlink_to(self.module.CANDIDATE_AP)
            with self.assertRaises(self.module.OwnerDesignError):
                self.module.audit_boot_only_ap(
                    symlink,
                    expected_size=self.module.CANDIDATE_AP_SIZE,
                    expected_sha256=self.module.CANDIDATE_AP_SHA256,
                    expected_member_size=self.module.CANDIDATE_MEMBER_SIZE,
                    expected_member_sha256=self.module.CANDIDATE_MEMBER_SHA256,
                    label="symlink candidate",
                )
            drift = root / "drift.tar.md5"
            drift.write_bytes(b"x" * 128)
            with self.assertRaises(self.module.OwnerDesignError):
                self.module.read_exact_regular(
                    drift,
                    expected_size=128,
                    expected_sha256="0" * 64,
                    label="drift candidate",
                )

    def test_hardlinked_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.tar.md5"
            second = root / "second.tar.md5"
            first.write_bytes(b"x")
            os.link(first, second)
            with self.assertRaisesRegex(self.module.OwnerDesignError, "identity"):
                self.module.read_exact_regular(
                    first,
                    expected_size=1,
                    expected_sha256=hashlib.sha256(b"x").hexdigest(),
                    label="hardlinked AP",
                )

    def test_invalid_md5_trailer_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad-md5.tar.md5"
            payload = self.write_ap(path, trailer_valid=False)
            with self.assertRaisesRegex(self.module.OwnerDesignError, "MD5 trailer"):
                self.module.audit_boot_only_ap(
                    path,
                    expected_size=len(payload),
                    expected_sha256=hashlib.sha256(payload).hexdigest(),
                    expected_member_size=1,
                    expected_member_sha256=hashlib.sha256(b"x").hexdigest(),
                    label="bad MD5 AP",
                )

    def test_noncanonical_member_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad-mode.tar.md5"
            payload = self.write_ap(path, mode=0o600)
            with self.assertRaisesRegex(
                self.module.OwnerDesignError, "member metadata"
            ):
                self.module.audit_boot_only_ap(
                    path,
                    expected_size=len(payload),
                    expected_sha256=hashlib.sha256(payload).hexdigest(),
                    expected_member_size=1,
                    expected_member_sha256=hashlib.sha256(b"x").hexdigest(),
                    label="bad metadata AP",
                )

    def test_member_size_and_hash_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "member-drift.tar.md5"
            payload = self.write_ap(path, body=b"xy")
            common = {
                "path": path,
                "expected_size": len(payload),
                "expected_sha256": hashlib.sha256(payload).hexdigest(),
                "label": "member drift AP",
            }
            with self.assertRaisesRegex(
                self.module.OwnerDesignError, "member metadata"
            ):
                self.module.audit_boot_only_ap(
                    **common,
                    expected_member_size=1,
                    expected_member_sha256=hashlib.sha256(b"xy").hexdigest(),
                )
            with self.assertRaisesRegex(self.module.OwnerDesignError, "boot member"):
                self.module.audit_boot_only_ap(
                    **common,
                    expected_member_size=2,
                    expected_member_sha256="0" * 64,
                )

    def test_extra_tar_member_is_rejected_even_with_valid_md5_trailer(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "extra.tar.md5"
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w:", format=tarfile.USTAR_FORMAT) as archive:
                for name in ("boot.img.lz4", "extra"):
                    info = tarfile.TarInfo(name)
                    info.size = 1
                    info.mode = 0o644
                    info.uid = 0
                    info.gid = 0
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(b"x"))
            tar_bytes = stream.getvalue()
            payload = tar_bytes + hashlib.md5(tar_bytes).hexdigest().encode() + b"  AP.tar\n"
            path.write_bytes(payload)
            with self.assertRaisesRegex(
                self.module.OwnerDesignError, "member count"
            ):
                self.module.audit_boot_only_ap(
                    path,
                    expected_size=len(payload),
                    expected_sha256=hashlib.sha256(payload).hexdigest(),
                    expected_member_size=1,
                    expected_member_sha256=hashlib.sha256(b"x").hexdigest(),
                    label="extra member AP",
                )

    def test_cli_only_renders_plan_and_has_no_execution_surface(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
            text=True,
        )
        rendered = json.loads(completed.stdout)
        self.assertEqual(rendered["binding_sha256"], self.plan["binding_sha256"])
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "os.system",
            "Popen(",
            "--prepare",
            "--execute",
            "--approval",
            "F1_ACTIVE = True",
        ):
            self.assertNotIn(forbidden, source)
        with mock.patch.object(
            self.module,
            "validate_closure",
            side_effect=AssertionError("no validation on invalid CLI"),
        ):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                with mock.patch.object(sys, "argv", [str(SCRIPT)]):
                    self.module.main()


if __name__ == "__main__":
    unittest.main()
