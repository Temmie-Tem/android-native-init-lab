from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("a90_boot_only_f1_minimal_v1")
A = load("a90_boot_only_f1_adapter_v1")
R = load("a90_h27_pretransfer_abort_reconcile_v1")


def phase(role: str, size: int, digest: str) -> str:
    prefix = "[native-init-flash 00:00:00] "
    common = (
        f"{prefix}local image size: {size}\n"
        f"{prefix}local image sha256: {digest}\n"
        f"{prefix}phase.native_init_flash.inspect_local_image.elapsed_sec=0.001 ok=1\n"
    )
    if role == "candidate":
        return (
            common
            + f"{prefix}phase.native_init_flash.native_to_recovery.elapsed_sec=0.001 ok=1\n"
            + f"{prefix}phase.native_init_flash.wait_recovery_adb.elapsed_sec=1.000 ok=1\n"
            + f"{prefix}phase.native_init_flash.total.elapsed_sec=1.002 ok=0\n"
            + f"{prefix}error: [Errno 27] File too large\n"
        )
    return (
        common
        + f"{prefix}phase.native_init_flash.total.elapsed_sec=0.002 ok=0\n"
        + f"{prefix}error: ADB baseline already contains a recovery endpoint\n"
    )


class PretransferAbortReconcileTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "candidate": {"size": 58_368_000, "sha256": "a" * 64},
            "rollback": {"size": 60_882_944, "sha256": "b" * 64},
        }
        self.candidate = phase(
            "candidate",
            self.manifest["candidate"]["size"],
            self.manifest["candidate"]["sha256"],
        ).encode()
        self.rollback = phase(
            "rollback",
            self.manifest["rollback"]["size"],
            self.manifest["rollback"]["sha256"],
        ).encode()

    def test_receipt_duration_is_recovered_only_from_exact_logs(self):
        argv = ("python", "helper", "candidate")
        receipt = {
            "argv": list(argv),
            "returncode": 1,
            "quiescent": True,
            "stdoutSha256": M.sha256_bytes(b"stdout"),
            "stderrSha256": M.sha256_bytes(b"stderr"),
            "durationMs": 17,
        }
        digest = M.sha256_bytes(M.canonical_json(receipt))
        self.assertEqual(
            R.bind_effect_receipt(
                expected_sha256=digest,
                argv=argv,
                returncode=1,
                quiescent=True,
                stdout=b"stdout",
                stderr=b"stderr",
                maximum_duration_ms=20,
            ),
            17,
        )
        with self.assertRaisesRegex(M.ContractError, "one bound"):
            R.bind_effect_receipt(
                expected_sha256=digest,
                argv=argv,
                returncode=1,
                quiescent=True,
                stdout=b"changed",
                stderr=b"stderr",
                maximum_duration_ms=20,
            )

    def test_empty_direct_log_is_valid_but_symlink_is_not(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            empty = root / "empty.log"
            empty.touch(mode=0o600)
            self.assertEqual(R._read_log(empty, "empty log"), b"")
            link = root / "link.log"
            link.symlink_to(empty)
            with self.assertRaisesRegex(M.ContractError, "identity mismatch"):
                R._read_log(link, "linked log")

    def test_exact_pretransfer_failure_logs_are_accepted(self):
        R.validate_pretransfer_logs(
            candidate_stderr=self.candidate,
            rollback_stderr=self.rollback,
            manifest=self.manifest,
        )

    def test_any_transfer_or_write_stage_is_rejected(self):
        for token in (
            "phase.native_init_flash.adb_push.elapsed_sec=0.001 ok=0",
            "phase.native_init_flash.boot_dd_write.elapsed_sec=0.001 ok=1",
            "phase.native_init_flash.boot_readback_sha256.elapsed_sec=0.001 ok=1",
            "sealed local image copy: /tmp/boot.img",
        ):
            with self.subTest(token=token), self.assertRaisesRegex(
                M.ContractError, "forbidden stage"
            ):
                R.validate_pretransfer_logs(
                    candidate_stderr=self.candidate + (token + "\n").encode(),
                    rollback_stderr=self.rollback,
                    manifest=self.manifest,
                )

    def test_rollback_must_not_enter_recovery_or_transfer(self):
        with self.assertRaisesRegex(M.ContractError, "rollback advanced"):
            R.validate_pretransfer_logs(
                candidate_stderr=self.candidate,
                rollback_stderr=(
                    self.rollback
                    + b"requesting recovery from native init bridge\n"
                ),
                manifest=self.manifest,
            )

    def test_owner_accepts_only_the_appended_reconciliation_record(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir(mode=0o700)
            digest = "c" * 64
            for name in M.PRETRANSFER_ABORT_PATH:
                M.publish_record(
                    run,
                    name,
                    M._record(M.RECORD_KINDS[name], digest, {}),
                )
            self.assertEqual(tuple(M.read_records(run)), M.PRETRANSFER_ABORT_PATH)
            self.assertEqual(
                M.recovery_decision(run),
                "PRETRANSFER_ABORT_RECONCILED_RETRY_ALLOWED",
            )


if __name__ == "__main__":
    unittest.main()
