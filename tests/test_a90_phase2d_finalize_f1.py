"""Host-only tests for the A90 Phase 2D F1 finalizer."""

from __future__ import annotations

import hashlib
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

    def test_parser_requires_explicit_mode(self) -> None:
        parser = finalizer.build_parser()
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parser.parse_args([])
        args = parser.parse_args(["--audit-only"])
        self.assertTrue(args.audit_only)
        self.assertFalse(args.finalize)

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
                '"candidate_transfer_authorized": False',
                '"candidate_transfer_authorized": True',
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
