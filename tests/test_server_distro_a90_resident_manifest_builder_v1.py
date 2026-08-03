"""Host-only tests for the A90 resident manifest builder."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


builder = load_script(
    "workspace/public/src/scripts/server-distro/a90_resident_manifest_builder_v1.py"
)


class ResidentManifestBuilderTests(unittest.TestCase):
    def test_prepare_manifest_rebinds_run_fields_without_string_replacement(self) -> None:
        with tempfile.TemporaryDirectory(dir=builder.staging.PRIVATE_ROOT) as temp_dir:
            run_dir = Path(temp_dir)
            run_id = "a90-v3406-debian-display-f1-20260801-02"
            template = {
                "schema": builder.staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA,
                "status": builder.staging.FINAL_MANIFEST_STATUS,
                "run_id": "a90-v3406-debian-display-f1-20260801-01",
                "candidate_boot": {"path": "/old/candidate", "size": 1, "sha256": "1" * 64},
                "rollback_boot": {"path": "/old/rollback", "size": 1, "sha256": "2" * 64},
                "target": {},
                "debian_rootfs": {
                    "keyed_source": {"device_path": "/old/remote"},
                    "pristine_provenance": {
                        "path": "/old/phase2-clean.img",
                        "sha256": "0" * 64,
                    },
                    "observer": {},
                },
                "host_preparation": {},
                "approval_preparation": {},
                "f1_orchestrator": {},
                "rootfs_staging": {"adapter": {}, "transport": {}},
                "resident_promotion": {"runner": {}, "qualification_helper": {}},
                "transport": {},
            }
            summary = {
                "run_id": run_id,
                "decision": "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS",
                "keyed_image": {
                    "path": str(run_dir / "phase2-display-v1-keyed.img"),
                    "size": 2,
                    "sha256": "3" * 64,
                },
                "observer": {
                    "private_key_path": str(run_dir / "observer-key"),
                    "public_key_sha256": "4" * 64,
                },
                "source": {
                    "path": "/private/phase2-clean.img",
                    "size": 2,
                    "sha256": "a" * 64,
                    "receipt_path": "/private/phase2-receipt.json",
                    "receipt_sha256": "b" * 64,
                },
            }
            connected = {
                "run_id": f"{run_id}-connected-d0-01",
                "target": {
                    "bridge_device": "/dev/serial/by-id/exact-a90",
                    "bridge_selected_realpath": "/dev/ttyACM0",
                },
                "health": {
                    "version": builder.staging.EXPECTED_RESIDENT_VERSION,
                    "version_build": builder.staging.EXPECTED_RESIDENT_BUILD,
                },
            }
            paths = {"run_id": run_id}
            records = {
                "summary": {"path": str(run_dir / "summary"), "size": 1, "sha256": "5" * 64},
                "candidate": {"path": str(run_dir / "candidate"), "size": 1, "sha256": "1" * 64},
                "rollback": {"path": str(run_dir / "rollback"), "size": 1, "sha256": "2" * 64},
                "connected": {"path": str(run_dir / "connected"), "size": 1, "sha256": "6" * 64},
                "paths": {"path": str(run_dir / "paths"), "size": 1, "sha256": "7" * 64},
                "host": {"path": str(run_dir / "host"), "size": 1, "sha256": "8" * 64},
            }
            fake_record = {"path": "/public/current", "size": 10, "sha256": "9" * 64}
            with mock.patch.object(builder, "current_record", return_value=fake_record):
                manifest = builder.prepare_manifest(
                    template=template,
                    run_id=run_id,
                    run_dir=run_dir,
                    evidence_sequence="01",
                    summary=summary,
                    summary_record=records["summary"],
                    candidate_record=records["candidate"],
                    rollback_record=records["rollback"],
                    connected_value=connected,
                    connected_record=records["connected"],
                    paths_value=paths,
                    paths_record=records["paths"],
                    host_preparation_record=records["host"],
                    repository_commit="a" * 40,
                )
            self.assertEqual(manifest["run_id"], run_id)
            self.assertEqual(
                manifest["target"]["connected_d0_result"]["path"],
                records["connected"]["path"],
            )
            self.assertEqual(
                manifest["debian_rootfs"]["keyed_source"]["device_path"],
                str(builder.staging.derive_remote_final(run_id)),
            )
            self.assertNotIn(template["run_id"], json.dumps(manifest, sort_keys=True))

            phase3_summary = {
                **summary,
                "schema": "a90-phase3-network-ssh-keyed-rootfs-v1",
                "decision": "A90_PHASE3_NETWORK_SSH_KEYED_ROOTFS_HOST_PASS",
                "keyed_image": {
                    **summary["keyed_image"],
                    "path": str(run_dir / "phase3-network-ssh-v1-keyed.img"),
                },
                "source": {
                    "path": "/private/phase3-clean.img",
                    "size": 2,
                    "sha256": "c" * 64,
                    "receipt_path": "/private/phase3-receipt.json",
                    "receipt_sha256": "d" * 64,
                },
            }
            phase3_template = json.loads(json.dumps(template))
            phase3_template["approval_scope_template"] = {
                "bind_phase2_materialization_receipt": True,
            }
            with mock.patch.object(
                builder,
                "current_record",
                return_value=fake_record,
            ):
                phase3_manifest = builder.prepare_manifest(
                    template=phase3_template,
                    run_id=run_id,
                    run_dir=run_dir,
                    evidence_sequence="01",
                    summary=phase3_summary,
                    summary_record=records["summary"],
                    candidate_record=records["candidate"],
                    rollback_record=records["rollback"],
                    connected_value=connected,
                    connected_record=records["connected"],
                    paths_value=paths,
                    paths_record=records["paths"],
                    host_preparation_record=records["host"],
                    repository_commit="a" * 40,
                )
            self.assertEqual(
                phase3_manifest["debian_rootfs"]["keyed_source"]["local_path"],
                str(run_dir / "phase3-network-ssh-v1-keyed.img"),
            )
            self.assertEqual(
                phase3_manifest["debian_rootfs"]["keyed_source"]["profile"],
                builder.staging.PHASE3_PROFILE,
            )
            self.assertEqual(
                phase3_manifest["debian_rootfs"]["keyed_source"][
                    "filesystem_label"
                ],
                builder.staging.PHASE3_FILESYSTEM_LABEL,
            )
            self.assertEqual(
                phase3_manifest["target"]["current_version"],
                builder.staging.EXPECTED_RESIDENT_VERSION,
            )
            self.assertEqual(
                phase3_manifest["rootfs_staging"]["review_verdict"],
                "PASS_GO",
            )
            self.assertNotIn(
                "bind_phase2_materialization_receipt",
                phase3_manifest["approval_scope_template"],
            )
            self.assertTrue(
                phase3_manifest["approval_scope_template"][
                    "bind_phase3_materialization_receipt"
                ]
            )
            self.assertEqual(
                phase3_manifest["debian_rootfs"]["pristine_provenance"],
                {
                    "path": "/private/phase3-clean.img",
                    "size": 2,
                    "sha256": "c" * 64,
                    "receipt_path": "/private/phase3-receipt.json",
                    "receipt_sha256": "d" * 64,
                },
            )
            self.assertNotIn(
                "/old/phase2-clean.img",
                json.dumps(phase3_manifest, sort_keys=True),
            )

    def test_prepare_manifest_can_select_resident_install_v2(self) -> None:
        with tempfile.TemporaryDirectory(dir=builder.staging.PRIVATE_ROOT) as temp_dir:
            run_dir = Path(temp_dir)
            run_id = "a90-v3406-debian-display-f1-20260801-02"
            template = {
                "schema": builder.staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA,
                "status": builder.staging.FINAL_MANIFEST_STATUS,
                "run_id": "a90-v3406-debian-display-f1-20260801-01",
                "candidate_boot": {"path": "/old/candidate", "size": 1, "sha256": "1" * 64},
                "rollback_boot": {"path": "/old/rollback", "size": 1, "sha256": "2" * 64},
                "target": {},
                "debian_rootfs": {
                    "keyed_source": {"device_path": "/old/remote"},
                    "observer": {},
                },
                "host_preparation": {},
                "approval_preparation": {},
                "f1_orchestrator": {},
                "rootfs_staging": {"adapter": {}, "transport": {}},
                "resident_promotion": {
                    "mode": builder.promotion.MODE,
                    "runner": {},
                    "qualification_helper": {},
                    "resident_reboot_command": ["reboot"],
                    "resident_reboot_timeout_sec": 240,
                    "candidate_health_checks": 2,
                },
                "transport": {},
            }
            summary = {
                "run_id": run_id,
                "decision": "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS",
                "keyed_image": {
                    "path": str(run_dir / "phase2-display-v1-keyed.img"),
                    "size": 2,
                    "sha256": "3" * 64,
                },
                "observer": {
                    "private_key_path": str(run_dir / "observer-key"),
                    "public_key_sha256": "4" * 64,
                },
                "source": {
                    "path": "/private/phase2-clean.img",
                    "size": 2,
                    "sha256": "a" * 64,
                    "receipt_path": "/private/phase2-receipt.json",
                    "receipt_sha256": "b" * 64,
                },
            }
            records = {
                name: {"path": str(run_dir / name), "size": 1, "sha256": char * 64}
                for name, char in (
                    ("summary", "5"),
                    ("candidate", "1"),
                    ("rollback", "2"),
                    ("connected", "6"),
                    ("paths", "7"),
                    ("host", "8"),
                )
            }
            with mock.patch.object(
                builder,
                "current_record",
                return_value={"path": "/public/current", "size": 10, "sha256": "9" * 64},
            ):
                manifest = builder.prepare_manifest(
                    template=template,
                    run_id=run_id,
                    run_dir=run_dir,
                    evidence_sequence="01",
                    summary=summary,
                    summary_record=records["summary"],
                    candidate_record=records["candidate"],
                    rollback_record=records["rollback"],
                    connected_value={
                        "run_id": f"{run_id}-connected-d0-01",
                        "target": {
                            "bridge_device": "/dev/serial/by-id/exact-a90",
                            "bridge_selected_realpath": "/dev/ttyACM0",
                        },
                        "health": {
                            "version": builder.staging.EXPECTED_BASELINE_VERSION,
                            "version_build": builder.staging.EXPECTED_BASELINE_BUILD,
                        },
                    },
                    connected_record=records["connected"],
                    paths_value={"run_id": run_id},
                    paths_record=records["paths"],
                    host_preparation_record=records["host"],
                    repository_commit="a" * 40,
                    resident_install_v2=True,
                )
        resident = manifest["resident_promotion"]
        self.assertEqual(
            manifest["schema"],
            builder.staging.RESIDENT_INSTALL_MANIFEST_SCHEMA,
        )
        self.assertEqual(resident["mode"], builder.promotion.INSTALL_MODE)
        self.assertEqual(resident["candidate_health_checks"], 1)
        self.assertEqual(resident["success_terminal"], builder.promotion.INSTALL_STATUS)
        self.assertNotIn("resident_reboot_command", resident)
        self.assertNotIn("resident_reboot_timeout_sec", resident)

    def test_canonical_boot_template_rejects_every_binding_mutation(self) -> None:
        candidate = {
            "path": f"/private/{builder.CANDIDATE_NAME}",
            "partition": "boot",
            "size": builder.CANDIDATE_SIZE,
            "sha256": builder.CANDIDATE_SHA256,
            "expected_version": builder.CANDIDATE_VERSION,
            "expected_build": builder.CANDIDATE_BUILD,
        }
        rollback = {
            "path": f"/private/{builder.ROLLBACK_NAME}",
            "partition": "boot",
            "size": builder.ROLLBACK_SIZE,
            "sha256": builder.ROLLBACK_SHA256,
            "expected_version": builder.ROLLBACK_VERSION,
            "expected_build": builder.ROLLBACK_BUILD,
        }
        builder.validate_canonical_boot_template(candidate, rollback)
        for selected, field, replacement in (
            (candidate, "path", "/private/other.img"),
            (candidate, "partition", "recovery"),
            (candidate, "size", builder.CANDIDATE_SIZE + 1),
            (candidate, "sha256", "0" * 64),
            (candidate, "expected_version", "other"),
            (candidate, "expected_build", "other"),
            (rollback, "path", "/private/other.img"),
            (rollback, "partition", "recovery"),
            (rollback, "size", builder.ROLLBACK_SIZE + 1),
            (rollback, "sha256", "0" * 64),
            (rollback, "expected_version", "other"),
            (rollback, "expected_build", "other"),
        ):
            mutated_candidate = json.loads(json.dumps(candidate))
            mutated_rollback = json.loads(json.dumps(rollback))
            target = (
                mutated_candidate if selected is candidate else mutated_rollback
            )
            target[field] = replacement
            selected_name = (
                "candidate" if selected is candidate else "rollback"
            )
            with self.subTest(field=field, selected=selected_name):
                with self.assertRaisesRegex(
                    builder.ContractError,
                    "boot binding is not canonical",
                ):
                    builder.validate_canonical_boot_template(
                        mutated_candidate,
                        mutated_rollback,
                    )

    def test_validate_local_paths_allows_only_absent_approval(self) -> None:
        with tempfile.TemporaryDirectory(dir=builder.staging.PRIVATE_ROOT) as temp_dir:
            run_dir = Path(temp_dir)
            present = run_dir / "present"
            present.write_text("ok", encoding="utf-8")
            present.chmod(0o600)
            manifest = {
                "input": str(present),
                "approval": str(run_dir / "approval-prepared.json"),
            }
            builder.validate_local_paths(manifest, run_dir)
            manifest["missing"] = str(run_dir / "missing")
            with self.assertRaisesRegex(builder.ContractError, "absent or not regular"):
                builder.validate_local_paths(manifest, run_dir)

    def test_publish_occurs_only_after_production_validation(self) -> None:
        with tempfile.TemporaryDirectory(dir=builder.staging.PRIVATE_ROOT) as temp_dir:
            run_dir = Path(temp_dir)
            present = run_dir / "present"
            present.write_text("ok", encoding="utf-8")
            present.chmod(0o600)
            manifest = {
                "input": str(present),
                "approval": str(run_dir / "approval-prepared.json"),
            }
            spec = SimpleNamespace()
            with (
                mock.patch.object(
                    builder.promotion,
                    "load_spec",
                    return_value=(spec, {"mode": builder.promotion.MODE}, []),
                ),
                mock.patch.object(builder.base, "verify_local_closure"),
            ):
                output, digest, _ = builder.write_validate_publish(
                    manifest,
                    run_dir=run_dir,
                    output_name="resident-prepared-manifest-test.json",
                )
            self.assertTrue(output.is_file())
            self.assertEqual(builder.sha256_file(output), digest)

            failed = run_dir / "resident-prepared-manifest-fail.json"
            with mock.patch.object(
                builder.promotion,
                "load_spec",
                side_effect=builder.ContractError("invalid"),
            ):
                with self.assertRaisesRegex(builder.ContractError, "invalid"):
                    builder.write_validate_publish(
                        manifest,
                        run_dir=run_dir,
                        output_name=failed.name,
                    )
            self.assertFalse(failed.exists())


if __name__ == "__main__":
    unittest.main()
