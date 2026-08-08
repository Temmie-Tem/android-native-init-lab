"""Host-only tests for the A90 Phase 2D F1 finalizer."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

from _loader import load_script


finalizer = load_script(
    "workspace/public/src/scripts/server-distro/a90_phase2d_finalize_f1.py"
)
SOURCE = Path(
    "workspace/public/src/scripts/server-distro/a90_phase2d_finalize_f1.py"
)


class A90Phase2DFinalizerTests(unittest.TestCase):
    def test_source_contract_is_closed(self) -> None:
        self.assertEqual(
            finalizer.source_contract_issues(
                SOURCE.read_text(encoding="utf-8")
            ),
            (),
        )

    def test_audit_binds_exact_candidate_without_authority(self) -> None:
        result = finalizer.audit_payload()
        self.assertTrue(result["ready_for_finalization_inputs"])
        self.assertEqual(
            result["candidate_profile"],
            finalizer.LEGACY_CANDIDATE_PROFILE,
        )
        self.assertEqual(result["candidate_sha256"], finalizer.CANDIDATE_SHA256)
        self.assertEqual(result["candidate_size"], finalizer.CANDIDATE_SIZE)
        self.assertEqual(result["rollback_sha256"], finalizer.ROLLBACK_SHA256)
        self.assertEqual(result["rollback_size"], finalizer.ROLLBACK_SIZE)
        self.assertEqual(
            finalizer.ROLLBACK_SOURCE,
            finalizer.staging.PRIVATE_ROOT
            / "inputs"
            / "boot_images"
            / "boot_linux_v2321_usb_clean_identity_rodata.img",
        )
        self.assertEqual(finalizer.ROLLBACK_SIZE, 60882944)
        self.assertEqual(
            finalizer.ROLLBACK_SHA256,
            "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb",
        )
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["device_write"])
        self.assertFalse(result["f1_authorized"])
        self.assertFalse(result["live_authority"])

    def test_minimal_f_candidate_profile_is_exact_and_auditable(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_F_CANDIDATE_PROFILE
        )
        self.assertEqual(
            selected.copy_name,
            "candidate-boot-phase3-minimal-f.img",
        )
        self.assertEqual(selected.size, 61440000)
        self.assertEqual(
            selected.sha256,
            "93ac207f6008959f663ec3df60e9bfd43ee855f72e57a4967c93bd0aa49d2d6f",
        )
        self.assertEqual(selected.version, "0.11.167")
        self.assertEqual(selected.build, "phase3-minimal-f-power-recovery-ui")
        result = finalizer.audit_payload(selected.profile)
        self.assertTrue(result["ready_for_finalization_inputs"])
        self.assertEqual(result["candidate_profile"], selected.profile)
        self.assertEqual(result["candidate_sha256"], selected.sha256)
        self.assertEqual(result["candidate_size"], selected.size)
        self.assertEqual(result["candidate_version"], selected.version)
        self.assertEqual(result["candidate_build"], selected.build)

    def test_minimal_g_candidate_profile_is_exact_and_auditable(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_G_CANDIDATE_PROFILE
        )
        self.assertEqual(
            selected.copy_name,
            "candidate-boot-phase3-minimal-g.img",
        )
        self.assertEqual(selected.size, 58306560)
        self.assertEqual(
            selected.sha256,
            "f6eccc8e8b372e957d67e64e088acea4f7fddf351873d7c297e1fa4393f4169a",
        )
        self.assertEqual(selected.version, "0.11.168")
        self.assertEqual(selected.build, "phase3-minimal-g-server-core")
        result = finalizer.audit_payload(selected.profile)
        self.assertTrue(result["ready_for_finalization_inputs"])
        self.assertEqual(result["candidate_profile"], selected.profile)
        self.assertEqual(result["candidate_sha256"], selected.sha256)
        self.assertEqual(result["candidate_size"], selected.size)
        self.assertEqual(result["candidate_version"], selected.version)
        self.assertEqual(result["candidate_build"], selected.build)

    def test_minimal_h2_candidate_profile_binds_two_phase_first_boot(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_H2_CANDIDATE_PROFILE
        )
        self.assertEqual(
            selected.copy_name,
            "candidate-boot-phase3-minimal-h2.img",
        )
        self.assertEqual(selected.size, 58372096)
        self.assertEqual(
            selected.sha256,
            "97cfbb149361773e895a2a1cff0f13961c06f0a4710119159d6d2a104bc69802",
        )
        self.assertEqual(selected.version, "0.11.170")
        self.assertEqual(
            selected.build,
            "phase3-minimal-h2-two-phase-auto-benchmark",
        )
        self.assertEqual(
            finalizer.candidate_first_boot_contract(selected),
            {
                "schema": "a90-auto-handoff-first-boot-v1",
                "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h2.enable",
                "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h2.done",
                "pre_transfer_state": "both-absent",
                "post_boot_status": "binding=1-enable=0-latch=0",
                "post_boot_log": "A90AUTO state=unarmed-stay-native",
            },
        )
        result = finalizer.audit_payload(selected.profile)
        self.assertEqual(result["candidate_profile"], selected.profile)
        self.assertEqual(result["candidate_sha256"], selected.sha256)
        self.assertEqual(result["candidate_size"], selected.size)
        self.assertIsNone(
            finalizer.candidate_first_boot_contract(
                finalizer.MINIMAL_G_CANDIDATE
            )
        )

    def test_minimal_h3_candidate_binds_build_receipt_and_exact_rootfs(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_H3_CANDIDATE_PROFILE
        )
        contract = finalizer.candidate_first_boot_contract(selected)
        self.assertEqual(contract["schema"], "a90-auto-handoff-first-boot-v2")
        self.assertEqual(
            contract["compiled_binding"],
            selected.compiled_auto_handoff,
        )
        with mock.patch.object(finalizer, "sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(
                finalizer.ContractError,
                "build receipt SHA256 changed",
            ):
                finalizer.validate_candidate_build_receipt(selected)

    def test_minimal_h4_candidate_binds_observer_complete_receipt(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_H4_CANDIDATE_PROFILE
        )
        contract = finalizer.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.172")
        self.assertEqual(
            selected.build,
            "phase3-minimal-h4-observer-complete-auto-benchmark",
        )
        self.assertEqual(contract["schema"], "a90-auto-handoff-first-boot-v2")
        self.assertEqual(
            contract["compiled_binding"],
            selected.compiled_auto_handoff,
        )
        self.assertEqual(
            contract["compiled_binding"]["image_path"],
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-11.img",
        )

    def test_minimal_h5_candidate_binds_fresh_campaign_receipt(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_H5_CANDIDATE_PROFILE
        )
        contract = finalizer.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.173")
        self.assertEqual(
            selected.sha256,
            "8ceda5ac0924c0fc1f8526bbd3632fd5e6f1a8cdd59b03c978efb09bbb1acd9b",
        )
        self.assertEqual(
            contract["compiled_binding"]["image_sha256"],
            "874291801573d96bf7731b2cdc27deca066221450534365eddfa2acf41ab681e",
        )
        self.assertEqual(
            contract["compiled_binding"]["binding_sha256"],
            "243c65b770393e31c34048a4ec5ffea3032022b4de1d437e4e3ef1e7637d14f0",
        )

    def test_minimal_h6_candidate_binds_observer_complete_baseline(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_H6_CANDIDATE_PROFILE
        )
        contract = finalizer.candidate_first_boot_contract(selected)
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

    def test_minimal_h7_candidate_binds_readonly_source_evidence(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_H7_CANDIDATE_PROFILE
        )
        contract = finalizer.candidate_first_boot_contract(selected)
        self.assertEqual(selected.version, "0.11.175")
        self.assertEqual(
            selected.sha256,
            "9edcbf8821c5fb5069576ca403ed04e873e9dfcf79dedb59e2d976d6981af4a2",
        )
        self.assertEqual(
            selected.build_receipt.name,
            "ab-receipt.json",
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

    def test_minimal_h8_candidate_binds_dev_tmpfs_repair(self) -> None:
        selected = finalizer.select_candidate_profile(
            finalizer.MINIMAL_H8_CANDIDATE_PROFILE
        )
        contract = finalizer.candidate_first_boot_contract(selected)
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

    def test_unknown_candidate_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(finalizer.ContractError, "not exact"):
            finalizer.select_candidate_profile("arbitrary")

    def test_parser_requires_explicit_mode(self) -> None:
        parser = finalizer.build_parser()
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parser.parse_args([])
        args = parser.parse_args(["--audit-only"])
        self.assertTrue(args.audit_only)
        self.assertFalse(args.finalize)
        self.assertEqual(
            args.candidate_profile,
            finalizer.LEGACY_CANDIDATE_PROFILE,
        )
        selected = parser.parse_args(
            [
                "--audit-only",
                "--candidate-profile",
                finalizer.MINIMAL_F_CANDIDATE_PROFILE,
            ]
        )
        self.assertEqual(
            selected.candidate_profile,
            finalizer.MINIMAL_F_CANDIDATE_PROFILE,
        )

    def test_review_report_binds_current_execution_closure(self) -> None:
        source_lines = []
        for record in finalizer.required_review_source_records():
            relative = Path(record["path"]).relative_to(
                finalizer.REPO_ROOT.resolve(strict=True)
            )
            source_lines.append(f"- `{relative}`: `{record['sha256']}`")
        review = "\n".join(
            (
                "Independent verdict: GO",
                "Unresolved HIGH: 0",
                "Unresolved MEDIUM: 0",
                "Device actions: none",
                f"Review decision: `{finalizer.REVIEW_DECISION}`",
                *source_lines,
            )
        )
        finalizer.validate_independent_review_report(review)
        with self.assertRaisesRegex(
            finalizer.ContractError,
            "does not bind current source",
        ):
            finalizer.validate_independent_review_report(
                review.replace(source_lines[0], "", 1)
            )
        with self.assertRaisesRegex(
            finalizer.ContractError,
            "does not bind current source",
        ):
            finalizer.validate_independent_review_report(
                review + "\n" + source_lines[0].replace(
                    source_lines[0].rsplit("`", 2)[1],
                    "0" * 64,
                    1,
                )
            )
        for conflict in (
            "Independent verdict: NO-GO",
            "Unresolved HIGH: 1",
            "Unresolved MEDIUM: 1",
            "Device actions: present",
            "Review decision: `GO_OLD_CLOSURE`",
        ):
            with self.subTest(conflict=conflict), self.assertRaisesRegex(
                finalizer.ContractError,
                "not an exact GO",
            ):
                finalizer.validate_independent_review_report(
                    review + "\n" + conflict
                )

    def test_phase3_review_binds_exact_current_execution_closure(self) -> None:
        closure = {}
        for record in finalizer.required_phase3_review_source_records():
            relative = str(
                Path(record["path"]).relative_to(
                    finalizer.REPO_ROOT.resolve(strict=True)
                )
            )
            closure[relative] = {
                "bytes": record["size"],
                "sha256": record["sha256"],
            }
        report = {
            "schema": finalizer.PHASE3_REVIEW_SCHEMA,
            "status": "PASS_GO",
            "unresolved_findings": [],
            "permanent_boundaries_unchanged": True,
            "device_authority_granted": False,
            "named_execution_critical_closure": closure,
        }
        text = json.dumps(report)
        finalizer.validate_phase3_independent_review_report(text)
        first = next(iter(closure))
        report["named_execution_critical_closure"][first]["sha256"] = "0" * 64
        with self.assertRaisesRegex(finalizer.ContractError, "not exact PASS_GO"):
            finalizer.validate_phase3_independent_review_report(
                json.dumps(report)
            )

    def test_phase3_manifest_selects_resident_start_and_exact_keyer(self) -> None:
        template_path = (
            finalizer.staging.PRIVATE_RUN_BASE
            / "a90-v3406-debian-display-f1-20260802-01"
            / "prepared-manifest.json"
        )
        run_id = "a90-v3406-debian-display-f1-20260803-02"
        run_dir = finalizer.staging.PRIVATE_RUN_BASE / run_id
        summary_path = run_dir / finalizer.KEYED_SUMMARY_NAME
        if not template_path.is_file() or not summary_path.is_file():
            self.skipTest("private Phase 3 finalizer integration inputs absent")
        template = json.loads(template_path.read_text(encoding="utf-8"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        record = {"path": "/private/evidence", "size": 1, "sha256": "1" * 64}
        manifest = finalizer.prepare_manifest(
            template=template,
            run_id=run_id,
            run_dir=run_dir,
            summary=summary,
            summary_record=record,
            candidate_record={
                "path": str(run_dir / finalizer.CANDIDATE_COPY_NAME),
                "size": finalizer.CANDIDATE_SIZE,
                "sha256": finalizer.CANDIDATE_SHA256,
            },
            rollback_record={
                "path": str(run_dir / finalizer.ROLLBACK_COPY_NAME),
                "size": finalizer.ROLLBACK_SIZE,
                "sha256": finalizer.ROLLBACK_SHA256,
            },
            connected_value={
                "target": {
                    "bridge_device": "/dev/serial/by-id/private-a90",
                    "bridge_selected_realpath": "/dev/ttyACM9",
                },
                "health": {
                    "version": finalizer.staging.EXPECTED_RESIDENT_VERSION,
                    "version_build": finalizer.staging.EXPECTED_RESIDENT_BUILD,
                },
            },
            connected_record=record,
            paths_record={"path": "/private/paths", "size": 1, "sha256": "2" * 64},
            host_preparation_record={
                "path": "/private/host",
                "size": 1,
                "sha256": "3" * 64,
            },
            repository_commit="a" * 40,
        )
        keyed = manifest["debian_rootfs"]["keyed_source"]
        self.assertEqual(keyed["profile"], finalizer.staging.PHASE3_PROFILE)
        self.assertEqual(
            keyed["filesystem_label"],
            finalizer.staging.PHASE3_FILESYSTEM_LABEL,
        )
        self.assertEqual(
            manifest["target"]["current_version"],
            finalizer.staging.EXPECTED_RESIDENT_VERSION,
        )
        support = {
            Path(item["path"]).name
            for item in manifest["rootfs_staging"]["support_files"]
        }
        self.assertIn("a90_phase3_network_ssh_keyed_rootfs_v1.py", support)
        self.assertNotIn("a90_phase2d_keyed_rootfs.py", support)
        self.assertFalse(manifest["authority"]["live_authority"])

    def test_phase3_start_accepts_only_exact_canonical_identities(self) -> None:
        self.assertEqual(
            finalizer.allowed_starting_identities(phase3=True),
            finalizer.staging.PHASE3_ALLOWED_STARTING_IDENTITIES,
        )
        self.assertEqual(
            finalizer.allowed_starting_identities(phase3=False),
            finalizer.staging.PHASE2_ALLOWED_STARTING_IDENTITIES,
        )
        self.assertNotIn(
            ("unknown", "unknown"),
            finalizer.allowed_starting_identities(phase3=True),
        )

    def test_copy_is_new_inode_exact_hash_and_absent_only(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=finalizer.staging.PRIVATE_ROOT
        ) as temp_dir:
            root = Path(temp_dir)
            source = root / "source.img"
            destination = root / "copy.img"
            source.write_bytes(b"boot")
            source.chmod(0o600)
            digest = hashlib.sha256(b"boot").hexdigest()
            result = finalizer.copy_absent_private(
                source,
                destination,
                expected_size=4,
                expected_sha256=digest,
            )
            self.assertEqual(result["sha256"], digest)
            self.assertNotEqual(source.stat().st_ino, destination.stat().st_ino)
            with self.assertRaises(finalizer.ContractError):
                finalizer.copy_absent_private(
                    source,
                    destination,
                    expected_size=4,
                    expected_sha256=digest,
                )

    def test_template_must_bind_canonical_v2321_rollback(self) -> None:
        template = {
            "rollback_boot": {
                "path": str(finalizer.ROLLBACK_SOURCE.resolve(strict=True)),
                "size": finalizer.ROLLBACK_SIZE,
                "sha256": finalizer.ROLLBACK_SHA256,
                "partition": "boot",
                "expected_version": finalizer.staging.EXPECTED_BASELINE_VERSION,
                "expected_build": finalizer.staging.EXPECTED_BASELINE_BUILD,
            }
        }
        with mock.patch.object(
            finalizer,
            "regular_record",
            return_value={"size": finalizer.ROLLBACK_SIZE},
        ):
            finalizer.validate_template_rollback(template)
            for field, bad in (
                ("path", "/private/arbitrary.img"),
                ("size", finalizer.ROLLBACK_SIZE + 1),
                ("sha256", "0" * 64),
                ("expected_version", "not-v2321"),
            ):
                mutated = {
                    "rollback_boot": {
                        **template["rollback_boot"],
                        field: bad,
                    }
                }
                with self.subTest(field=field), self.assertRaisesRegex(
                    finalizer.ContractError,
                    "canonical V2321",
                ):
                    finalizer.validate_template_rollback(mutated)

    def test_direct_symlink_private_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=finalizer.staging.PRIVATE_ROOT
        ) as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.write_bytes(b"exact")
            target.chmod(0o600)
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(
                finalizer.ContractError,
                "symbolic link",
            ):
                finalizer.regular_record(link, private=True)

    def test_source_mutations_remove_readiness(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        mutations = (
            source.replace("--reflink=never", "--reflink=auto", 1),
            source.replace(
                "staging.validate_connected_d0_evidence(",
                "removed_connected_gate(",
                1,
            ),
            source.replace(
                "candidate_spec = select_candidate_profile(args.candidate_profile)",
                "candidate_spec = LEGACY_CANDIDATE",
                1,
            ),
            source.replace(
                '"candidate_transfer_authorized": False',
                '"candidate_transfer_authorized": True',
                1,
            ),
            source.replace("    if phase3:\n", "    if phase3 or True:\n", 1),
            source.replace(
                "    return staging.PHASE2_ALLOWED_STARTING_IDENTITIES\n",
                "    return staging.PHASE3_ALLOWED_STARTING_IDENTITIES\n",
                1,
            ),
            source.replace(
                "starting_identity not in allowed_starting_identities(phase3=phase3)",
                "starting_identity not in allowed_starting_identities(phase3=phase3) and False",
                1,
            ),
        )
        for mutation in mutations:
            with self.subTest():
                self.assertTrue(finalizer.source_contract_issues(mutation))

    def test_tracked_source_has_no_concrete_target_identity(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"/dev/serial/by-id/[^\"']+")
        self.assertNotRegex(text, r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
        self.assertNotIn("ttyACM0", text)


if __name__ == "__main__":
    unittest.main()
