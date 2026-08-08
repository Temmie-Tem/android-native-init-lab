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
                    candidate_spec=builder.MINIMAL_F_CANDIDATE,
                )
            self.assertEqual(
                phase3_manifest["candidate_boot"],
                {
                    **records["candidate"],
                    "partition": "boot",
                    "expected_version": builder.MINIMAL_F_CANDIDATE.version,
                    "expected_build": builder.MINIMAL_F_CANDIDATE.build,
                },
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

    def test_candidate_profiles_preserve_default_and_bind_minimal_profiles(self) -> None:
        self.assertIs(
            builder.select_candidate_profile(builder.LEGACY_CANDIDATE_PROFILE),
            builder.LEGACY_CANDIDATE,
        )
        selected = builder.select_candidate_profile(
            builder.MINIMAL_F_CANDIDATE_PROFILE
        )
        self.assertEqual(selected.name, "candidate-boot-phase3-minimal-f.img")
        self.assertEqual(selected.size, 61440000)
        self.assertEqual(
            selected.sha256,
            "93ac207f6008959f663ec3df60e9bfd43ee855f72e57a4967c93bd0aa49d2d6f",
        )
        self.assertEqual(selected.version, "0.11.167")
        self.assertEqual(selected.build, "phase3-minimal-f-power-recovery-ui")
        selected_g = builder.select_candidate_profile(
            builder.MINIMAL_G_CANDIDATE_PROFILE
        )
        self.assertEqual(selected_g.name, "candidate-boot-phase3-minimal-g.img")
        self.assertEqual(selected_g.size, 58306560)
        self.assertEqual(
            selected_g.sha256,
            "f6eccc8e8b372e957d67e64e088acea4f7fddf351873d7c297e1fa4393f4169a",
        )
        self.assertEqual(selected_g.version, "0.11.168")
        self.assertEqual(selected_g.build, "phase3-minimal-g-server-core")
        selected_h2 = builder.select_candidate_profile(
            builder.MINIMAL_H2_CANDIDATE_PROFILE
        )
        self.assertEqual(
            selected_h2.name,
            "candidate-boot-phase3-minimal-h2.img",
        )
        self.assertEqual(selected_h2.size, 58372096)
        self.assertEqual(
            selected_h2.sha256,
            "97cfbb149361773e895a2a1cff0f13961c06f0a4710119159d6d2a104bc69802",
        )
        self.assertEqual(selected_h2.version, "0.11.170")
        self.assertEqual(
            selected_h2.build,
            "phase3-minimal-h2-two-phase-auto-benchmark",
        )
        self.assertEqual(
            builder.candidate_first_boot_contract(selected_h2),
            {
                "schema": "a90-auto-handoff-first-boot-v1",
                "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h2.enable",
                "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h2.done",
                "pre_transfer_state": "both-absent",
                "post_boot_status": "binding=1-enable=0-latch=0",
                "post_boot_log": "A90AUTO state=unarmed-stay-native",
            },
        )
        self.assertIsNone(builder.candidate_first_boot_contract(selected_g))
        with self.assertRaisesRegex(builder.ContractError, "not exact"):
            builder.select_candidate_profile("arbitrary")

    def test_prior_closed_run_binder_uses_exact_contiguous_private_json(self) -> None:
        run_id = "a90-v3406-debian-display-f1-20260804-09"
        with tempfile.TemporaryDirectory(dir=builder.staging.PRIVATE_ROOT) as temp_dir:
            private_run_base = Path(temp_dir)
            run_dir = private_run_base / run_id
            journal_dir = run_dir / "f1-live" / "journal"
            journal_dir.mkdir(parents=True)

            def write_json(path: Path, value: dict) -> None:
                path.write_text(json.dumps(value), encoding="utf-8")
                path.chmod(0o600)

            for name in ("prepared-manifest.json", "approval-prepared.json"):
                write_json(run_dir / name, {"run_id": run_id})
            for name in ("result.json", "timeline.json"):
                write_json(run_dir / "f1-live" / name, {"run_id": run_id})
            for sequence, action in enumerate(("preflight", "approved")):
                write_json(
                    journal_dir / f"{sequence:04d}-{action}.json",
                    {"sequence": sequence, "action": action, "run_id": run_id},
                )
            with mock.patch.object(
                builder.staging,
                "PRIVATE_RUN_BASE",
                private_run_base,
            ):
                bound = builder.bind_prior_closed_run(run_id)
            self.assertEqual(bound["run_id"], run_id)
            self.assertEqual(len(bound["journal"]), 2)
            self.assertTrue(bound["manifest"]["path"].endswith("prepared-manifest.json"))

            (journal_dir / "0001-approved.json").rename(
                journal_dir / "0002-approved.json"
            )
            with (
                mock.patch.object(
                    builder.staging,
                    "PRIVATE_RUN_BASE",
                    private_run_base,
                ),
                self.assertRaisesRegex(builder.ContractError, "not contiguous"),
            ):
                builder.bind_prior_closed_run(run_id)

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


    def test_h3_candidate_binds_receipt_to_compiled_rootfs(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H3_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(contract["schema"], "a90-auto-handoff-first-boot-v2")
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-10.img",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_sha256"],
            "34de408d868ff0651d0f6efb1d1d9cc810e3dfe23acaac178e73e2840b2979a4",
        )

    def test_h4_candidate_binds_observer_complete_receipt(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H4_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.172")
        self.assertEqual(
            selected.sha256,
            "6bc133937f19482739037b67a44b1f2b5da6da9a178a3edf8a9f2e74bd097935",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-11.img",
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "783a528a541e3a8edf82543d7352ed2e47f5d3393245d413ee8507df6e797e09",
        )

    def test_h5_candidate_binds_fresh_campaign_receipt(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H5_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.173")
        self.assertEqual(
            selected.sha256,
            "8ceda5ac0924c0fc1f8526bbd3632fd5e6f1a8cdd59b03c978efb09bbb1acd9b",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-12.img",
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "243c65b770393e31c34048a4ec5ffea3032022b4de1d437e4e3ef1e7637d14f0",
        )

    def test_h6_candidate_binds_observer_complete_baseline(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H6_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.174")
        self.assertEqual(
            selected.sha256,
            "aa7cba7f730e12b08f6498a3307493eed033674d51c968b4ea4d2d3280ea98bb",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-03.img",
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "238a1ae3aa1f4a2a1a8c46d8368fa4e025d0a0be7fb4ed77e7ccd80b410d1483",
        )

    def test_h7_candidate_binds_readonly_source_evidence(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H7_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.175")
        self.assertEqual(
            selected.sha256,
            "9edcbf8821c5fb5069576ca403ed04e873e9dfcf79dedb59e2d976d6981af4a2",
        )
        self.assertEqual(
            selected.build_receipt_sha256,
            "5786bc0a5a9999a158647203afe5d51d60569d42c6fc76bb3a063e7bdd483773",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-05.img",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_sha256"],
            "b92a5437d3854b0f01e4b2acc4a241ad9c8ad8f0b17d7cc36e246d2fbb01d10a",
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "12fd4ad71f9e976455737d2671006cab77c8da916fad87d6e09eaae8f6253f7c",
        )

    def test_h8_candidate_binds_dev_tmpfs_repair(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H8_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.176")
        self.assertEqual(
            selected.sha256,
            "cfffb68a4d47f8ae1a76cee7faef8085e1681f1c53155cd6d03d7d87c15f7409",
        )
        self.assertEqual(
            selected.build_receipt_sha256,
            "5285e0e6c1119151aa98d7cd5ee27b320939901a68408aa4a3c45defe5408ac6",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-01.img",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_sha256"],
            "e2028b021cd67ebf16ad3cb917e9b548e1fcc434d5e42f10117854f202d01b24",
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "4221d365c10a86a85c2ebaeb64cdbe1d1ea8c240226ce5868b6c20afeb6b51a3",
        )

    def test_h9_candidate_binds_fresh_rootfs_with_fast_receipt_identity(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H9_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.177")
        self.assertEqual(
            selected.sha256,
            "c78cd6b4eee5b44c6249ad20729f0379a97cd83db67cab2287271813cd91439f",
        )
        self.assertEqual(
            selected.build_receipt_sha256,
            "2c8e45edcb9a1604c5b905b6dc956446d38ef94504ab44a2bb3dc5a16b06bd1e",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_sha256"],
            "e2028b021cd67ebf16ad3cb917e9b548e1fcc434d5e42f10117854f202d01b24",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-02.img",
        )
        h8_contract = builder.candidate_first_boot_contract(
            builder.select_candidate_profile(
                builder.MINIMAL_H8_CANDIDATE_PROFILE
            )
        )
        self.assertNotEqual(
            contract["compiled_binding"]["image_path"],
            h8_contract["compiled_binding"]["image_path"],
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "02f441da4ccb982e52ce8b75438df38a68eb6b3f3e4de0cd6f7616e250876a88",
        )
        self.assertEqual(contract["schema"], "a90-auto-handoff-first-boot-v3")
        self.assertEqual(
            contract["receipt_path"],
            "/cache/a90-source-receipt-phase3-minimal-h9",
        )
        self.assertEqual(
            contract["compiled_binding"]["receipt_path"],
            contract["receipt_path"],
        )
        self.assertEqual(
            contract["pre_transfer_state"],
            "enable-latch-receipt-absent",
        )
        manifest = {
            "candidate_boot": {
                "expected_version": selected.version,
                "expected_build": selected.build,
                "first_boot_contract": contract,
            },
            "debian_rootfs": {
                "keyed_source": {
                    "device_path": contract["compiled_binding"]["image_path"],
                    "sha256": contract["compiled_binding"]["image_sha256"],
                },
                "handoff_command": [
                    "switch-root-to-distro",
                    "SERVER-DISTRO-D3B-SWITCHROOT",
                    contract["compiled_binding"]["image_path"],
                    contract["compiled_binding"]["image_sha256"],
                ],
            },
        }
        builder.require_compiled_rootfs_binding(manifest)
        changed = json.loads(json.dumps(manifest))
        changed["candidate_boot"]["first_boot_contract"]["receipt_path"] += ".old"
        with self.assertRaisesRegex(builder.ContractError, "binding mismatch"):
            builder.require_compiled_rootfs_binding(changed)

    def test_h10_candidate_binds_new_keyed_rootfs_and_namespace(self) -> None:
        selected = builder.select_candidate_profile(
            builder.MINIMAL_H10_CANDIDATE_PROFILE
        )
        contract = builder.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.178")
        self.assertEqual(
            selected.sha256,
            "145ab5d0d2eff02e20d75149e62bd929084a9a1014a13f9b79e9dbd3269655f1",
        )
        self.assertEqual(
            selected.build_receipt_sha256,
            "a8323448364a3bfbc4edc0661b61493574bd7302c92699c07a5aa53d0465653a",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_sha256"],
            "38d9ce41503483996d14a18fb51275fbbe47e898ce51aee37f9f88b61295018e",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-03.img",
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "decc69954c2f57067d56062b1a1dd61a394b0587ab86d17905eae070e5b71d2d",
        )
        self.assertEqual(contract["schema"], "a90-auto-handoff-first-boot-v3")
        self.assertEqual(
            contract["receipt_path"],
            "/cache/a90-source-receipt-phase3-minimal-h10",
        )
        self.assertNotEqual(
            contract["receipt_path"],
            builder.candidate_first_boot_contract(
                builder.MINIMAL_H9_CANDIDATE
            )["receipt_path"],
        )
        manifest = {
            "candidate_boot": {
                "expected_version": selected.version,
                "expected_build": selected.build,
                "first_boot_contract": contract,
            },
            "debian_rootfs": {
                "keyed_source": {
                    "device_path": contract["compiled_binding"]["image_path"],
                    "sha256": contract["compiled_binding"]["image_sha256"],
                },
                "handoff_command": [
                    "switch-root-to-distro",
                    "SERVER-DISTRO-D3B-SWITCHROOT",
                    contract["compiled_binding"]["image_path"],
                    contract["compiled_binding"]["image_sha256"],
                ],
            },
        }
        builder.require_compiled_rootfs_binding(manifest)


if __name__ == "__main__":
    unittest.main()
