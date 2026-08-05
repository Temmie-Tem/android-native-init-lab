"""Static and pure tests for the fixed-path A90 cache tmp cleanup."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a90_cache_tmp_cleanup_v1 as cleanup  # noqa: E402


class A90CacheTmpCleanupV1Tests(unittest.TestCase):
    @staticmethod
    def _manifest() -> dict:
        private = REPO_ROOT / "workspace/private/runs/server-distro/cache-test"
        return {
            "schema": cleanup.SCHEMA,
            "capability": cleanup.CAPABILITY,
            "target": {
                "product": "SM-A908N",
                "device": "r3q",
                "resident_version": cleanup.EXPECTED_VERSION,
                "resident_build": cleanup.EXPECTED_BUILD,
            },
            "resident_manifest": {
                "path": str(private / "resident.json"),
                "sha256": "1" * 64,
            },
            "execution_closure_sha256": "2" * 64,
            "selected_file": {
                "path": cleanup.FIXED_PATH,
                "size": 38354944,
                "sha256": "3" * 64,
                "mode": 0o644,
                "uid": 0,
                "gid": 0,
                "nlink": 1,
                "device": 66338,
                "inode": 1740,
                "blocks": 74920,
            },
            "host_preserved": {
                "path": str(private / "preserved.img"),
                "size": 38354944,
                "sha256": "3" * 64,
                "mode": 0o600,
            },
            "rollback": {
                "path": str(private / "rollback.img"),
                "size": 60882944,
                "sha256": "4" * 64,
            },
            "recovery_profile": cleanup.RECOVERY_PROFILE,
            "inventory": {
                "captured_utc": "2026-08-05T09:20:00Z",
                "sequence": 50,
                "cache_available_kib": 0,
                "cache_inodes_available": 36520,
                "enable_absent": True,
                "latch_absent": True,
                "mount_hits": 0,
                "loop_hits": 0,
                "open_hits": 0,
            },
        }

    @staticmethod
    def _spec() -> cleanup.CleanupSpec:
        value = A90CacheTmpCleanupV1Tests._manifest()
        selected = value["selected_file"]
        return cleanup.CleanupSpec(
            manifest_sha256="5" * 64,
            resident_manifest_path=Path(value["resident_manifest"]["path"]),
            resident_manifest_sha256=value["resident_manifest"]["sha256"],
            execution_closure_sha256=value["execution_closure_sha256"],
            path=selected["path"],
            size=selected["size"],
            sha256=selected["sha256"],
            mode=selected["mode"],
            uid=selected["uid"],
            gid=selected["gid"],
            nlink=selected["nlink"],
            device=selected["device"],
            inode=selected["inode"],
            blocks=selected["blocks"],
            host_preserved_path=Path(value["host_preserved"]["path"]),
            rollback_path=Path(value["rollback"]["path"]),
            rollback_size=value["rollback"]["size"],
            rollback_sha256=value["rollback"]["sha256"],
        )

    def test_manifest_selects_only_fixed_single_regular_file(self) -> None:
        with mock.patch.object(cleanup, "_read_private_json", return_value=self._manifest()):
            actual = cleanup.load_cleanup_spec(Path("ignored"), "5" * 64)
        self.assertEqual(actual.path, cleanup.FIXED_PATH)
        self.assertEqual(actual.mode, 0o644)
        self.assertEqual(actual.nlink, 1)
        self.assertEqual(actual.blocks, 74920)

        widened = self._manifest()
        widened["selected_file"]["path"] = "/cache/other"
        with (
            mock.patch.object(cleanup, "_read_private_json", return_value=widened),
            self.assertRaises(cleanup.ContractError),
        ):
            cleanup.load_cleanup_spec(Path("ignored"), "5" * 64)

    def test_contract_names_fixed_capability_and_recovery_limits(self) -> None:
        text = cleanup.TARGET_CONTRACT.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn(cleanup.CAPABILITY, text)
        self.assertIn(cleanup.FIXED_PATH, text)
        self.assertIn("One durable intent permits one nonrecursive unlink dispatch", normalized)
        self.assertIn("any restore is a separate reviewed attended transaction", normalized)
        self.assertIn("never applies to S22+", text)

    def test_effect_is_one_fixed_unlink_with_in_use_rechecks(self) -> None:
        script = cleanup._effect_script()
        self.assertEqual(script.count('/bin/busybox rm -- "$P"'), 1)
        self.assertIn("/proc/[0-9]*/mountinfo", script)
        self.assertIn("/sys/block/loop*/loop/backing_file", script)
        self.assertIn("/proc/[0-9]*/fd/*", script)
        self.assertIn(cleanup.ENABLE_PATH, script)
        self.assertIn(cleanup.LATCH_PATH, script)
        self.assertNotIn("rm -r", script)
        self.assertNotIn("reboot", script)
        self.assertNotIn("dd ", script)

    def test_state_and_effect_frames_fit_resident_envelope(self) -> None:
        spec = self._spec()
        commands = (
            [
                "run", "/bin/busybox", "sh", "-c", cleanup._state_script(True),
                "a90-cache-tmp-state", spec.path, spec.sha256, cleanup._meta(spec),
            ],
            [
                "run", "/bin/busybox", "sh", "-c", cleanup._effect_script(),
                "a90-cache-tmp-unlink", spec.path, spec.sha256, cleanup._meta(spec),
            ],
        )
        for command in commands:
            with self.subTest(command=command[5]):
                encoded = cleanup.a90ctl.encode_cmdv1_line(command).encode("ascii")
                self.assertLessEqual(len(encoded), 3800)

    def test_state_parser_accepts_exact_present_and_absent_markers(self) -> None:
        spec = self._spec()
        present_text = (
            "A90CACHE_TMP state=present available_kib=0 inodes_available=36520 "
            f"enable=0 latch=0 meta={cleanup._meta(spec)} sha256={spec.sha256} "
            "mount=0 loop=0 open=0\n"
        )
        absent_text = (
            "A90CACHE_TMP state=absent available_kib=37460 inodes_available=36521 "
            "enable=0 latch=0\n"
        )
        with (
            mock.patch.object(
                cleanup,
                "_command_receipt",
                side_effect=[{"text": present_text}, {"text": absent_text}],
            ),
            mock.patch.object(
                cleanup.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda value, *_: value,
            ),
        ):
            _, present = cleanup.read_cleanup_state(
                SimpleNamespace(), spec, require_present=True
            )
            _, absent = cleanup.read_cleanup_state(
                SimpleNamespace(), spec, require_present=None
            )
        self.assertEqual(present["sha256"], spec.sha256)
        self.assertEqual(present["open"], 0)
        self.assertEqual(absent["state"], "absent")
        self.assertGreater(absent["available_kib"], 0)

    def test_live_effect_call_has_allow_error_but_no_retry_override(self) -> None:
        source = Path(cleanup.__file__).read_text(encoding="utf-8")
        execute = source[source.index("def execute_cleanup(") : source.index("def reconcile_cleanup(")]
        self.assertEqual(execute.count("base.run_f1_cmd("), 1)
        self.assertIn("allow_error=True", execute)
        self.assertNotIn("retry_unsafe", execute)
        self.assertLess(execute.index('"unlink-intent"'), execute.index("base.run_f1_cmd("))
        self.assertIn('"retransmit": False', execute)

    def test_reconcile_is_device_read_only_and_never_unlinks(self) -> None:
        source = Path(cleanup.__file__).read_text(encoding="utf-8")
        reconcile = source[source.index("def reconcile_cleanup(") : source.index("def build_parser(")]
        self.assertNotIn("_effect_script", reconcile)
        self.assertNotIn("rm --", reconcile)
        self.assertNotIn("base.run_f1_cmd", reconcile)
        self.assertIn("read_auto_status(args)", reconcile)
        self.assertIn('"retransmit": False', reconcile)

    def test_reconcile_pass_requires_exact_unarmed_status_receipt(self) -> None:
        state = {
            "state": "absent",
            "available_kib": 37460,
            "inodes_available": 36521,
            "enable": 0,
            "latch": 0,
        }
        private_parent = REPO_ROOT / "workspace/private"
        terminals: list[str] = []
        for status in ({"enable": 0, "latch": 0}, {"enable": 1, "latch": 0}):
            with tempfile.TemporaryDirectory(dir=private_parent) as temp_dir:
                path = Path(temp_dir)
                with (
                    mock.patch.object(cleanup, "require_execution_closure", return_value={}),
                    mock.patch.object(cleanup, "load_journal_prefix", return_value=[{}, {}]),
                    mock.patch.object(cleanup, "require_host_preserved", return_value={}),
                    mock.patch.object(
                        cleanup,
                        "read_cleanup_state",
                        return_value=({"text": "state"}, state),
                    ),
                    mock.patch.object(
                        cleanup.resident,
                        "resident_d0_preflight",
                        return_value=(SimpleNamespace(), {"healthy": True}),
                    ),
                    mock.patch.object(
                        cleanup,
                        "read_auto_status",
                        return_value=({"text": "status"}, status),
                    ) as status_read,
                ):
                    result = cleanup.reconcile_cleanup(
                        SimpleNamespace(),
                        self._spec(),
                        expected_closure="0" * 64,
                        transaction_dir=path,
                    )
                status_read.assert_called_once()
                self.assertEqual(result["auto_handoff_status"], status)
                self.assertEqual(result["auto_handoff_status_record"], {"text": "status"})
                terminals.append(result["terminal"])
        self.assertEqual(terminals[0], "PASS_CACHE_TMP_RECLAIMED_INFERRED_NO_REPLAY")
        self.assertEqual(terminals[1], "RECOVERY_PENDING_PARKED_NO_REPLAY")

    def test_reconcile_rejects_forged_prefix_before_device_reads(self) -> None:
        private_parent = REPO_ROOT / "workspace/private"
        with tempfile.TemporaryDirectory(dir=private_parent) as temp_dir:
            path = Path(temp_dir)
            (path / "0000-open.json").write_text("{}\n", encoding="utf-8")
            (path / "0001-unlink-intent.json").write_text("{}\n", encoding="utf-8")
            (path / "0000-open.json").chmod(0o600)
            (path / "0001-unlink-intent.json").chmod(0o600)
            with (
                mock.patch.object(cleanup, "require_execution_closure", return_value={}),
                mock.patch.object(
                    cleanup,
                    "read_cleanup_state",
                    side_effect=AssertionError("forged journal must not read device state"),
                ),
                mock.patch.object(
                    cleanup,
                    "read_auto_status",
                    side_effect=AssertionError("forged journal must not read H2 status"),
                ),
                mock.patch.object(
                    cleanup.resident,
                    "resident_d0_preflight",
                    side_effect=AssertionError("forged journal must not read health"),
                ),
                self.assertRaisesRegex(cleanup.ContractError, "schema/action/key set"),
            ):
                cleanup.reconcile_cleanup(
                    SimpleNamespace(),
                    self._spec(),
                    expected_closure="0" * 64,
                    transaction_dir=path,
                )

    def test_exact_open_and_intent_prefix_binds_manifest_closure_and_selection(self) -> None:
        spec = self._spec()
        closure = {"sha256": "0" * 64, "files": {}}
        status = {"enable": 0, "latch": 0}
        state = {
            "state": "present",
            "available_kib": 0,
            "inodes_available": 36520,
            "enable": 0,
            "latch": 0,
            "meta": cleanup._meta(spec),
            "sha256": spec.sha256,
            "mount": 0,
            "loop": 0,
            "open": 0,
        }
        private_parent = REPO_ROOT / "workspace/private"
        with tempfile.TemporaryDirectory(dir=private_parent) as temp_dir:
            path = Path(temp_dir)
            cleanup._write_new(path / cleanup.JOURNAL_NAMES[0], cleanup.JOURNAL_ACTIONS[0], {
                "manifest_sha256": spec.manifest_sha256,
                "execution_closure": closure,
                "host_preserved": {
                    "path": str(spec.host_preserved_path),
                    "size": spec.size,
                    "sha256": spec.sha256,
                    "mode": 0o600,
                },
                "opening_health": {"healthy": True},
                "status_record": {"receipt": "status"},
                "status": status,
                "state_record": {"receipt": "state"},
                "state": state,
            })
            cleanup._write_new(path / cleanup.JOURNAL_NAMES[1], cleanup.JOURNAL_ACTIONS[1], {
                "manifest_sha256": spec.manifest_sha256,
                "selected_path": spec.path,
                "selected_sha256": spec.sha256,
                "unlink_dispatch_count_max": 1,
                "retransmit": False,
                "s22plus_command_count": 0,
            })
            with (
                mock.patch.object(cleanup, "require_execution_closure", return_value=closure),
                mock.patch.object(cleanup, "parse_auto_status_receipt", return_value=status),
                mock.patch.object(cleanup, "parse_cleanup_state_receipt", return_value=state),
            ):
                records = cleanup.load_journal_prefix(spec, path, "0" * 64)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["selected_path"], cleanup.FIXED_PATH)
        self.assertEqual(records[1]["unlink_dispatch_count_max"], 1)
        self.assertFalse(records[1]["retransmit"])
        self.assertEqual(records[1]["s22plus_command_count"], 0)

    def test_execution_closure_binds_transitive_transport_and_contract(self) -> None:
        closure = cleanup.execution_closure()
        self.assertEqual(
            set(closure["files"]),
            {"runner", "resident", "base", "d1_transport", "a90ctl", "a90_bridge", "target_contract"},
        )
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")

    def test_live_effect_args_use_canonical_managed_bridge(self) -> None:
        args = cleanup._effect_args()
        self.assertEqual(args.bridge_host, "127.0.0.1")
        self.assertEqual(args.bridge_port, cleanup.a90ctl.DEFAULT_PORT)
        self.assertEqual(args.bridge_port, 54321)
        self.assertEqual(args.remote_timeout, 120.0)

    def test_preservation_accepts_existing_exact_private_parent(self) -> None:
        source = Path(cleanup.__file__).read_text(encoding="utf-8")
        preserve = source[source.index("def preserve_to_host(") : source.index("def _write_new(")]
        self.assertIn("mkdir(parents=True, mode=0o700, exist_ok=True)", preserve)
        self.assertIn("destination.parent.lstat()", preserve)
        self.assertIn("destination.parent.is_symlink()", preserve)
        self.assertIn("stat.S_ISDIR", preserve)
        self.assertIn("os.chmod(destination.parent, 0o700)", preserve)


if __name__ == "__main__":
    unittest.main()
