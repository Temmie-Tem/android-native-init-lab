"""Host-only tests for the exact A90 V3406 retained-work cleanup."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


cleanup = load_script(
    "workspace/public/src/scripts/server-distro/"
    "a90_v3405_retained_work_cleanup.py"
)
SOURCE = Path(cleanup.__file__).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Fixture:
    def __init__(self, base: Path) -> None:
        self.base = base
        self.run_id = "a90-v3406-work-cleanup-20260731-01"
        self.f1_run_id = "a90-v3406-debian-display-f1-20260731-01"
        self.run_dir = base / self.run_id
        self.run_dir.mkdir()
        self.host_copy = base / "preserved-work.img"
        self.host_copy.write_bytes(b"retained-work-fixture")
        self.host_copy.chmod(0o600)
        self.work_sha = sha256_file(self.host_copy)
        self.work_size = self.host_copy.stat().st_size
        self.bridge_device = (
            "/dev/serial/by-id/usb-A90-LNX_TEST_A90TEST-if00"
        )
        self.bridge_realpath = "/dev/ttyACM-test"
        self.bridge_realpath_sha256 = hashlib.sha256(
            self.bridge_realpath.encode("utf-8")
        ).hexdigest()
        self.connected = base / "connected-d0.json"
        self.connected.write_text(
            json.dumps(
                {
                    "schema": "a90-v3403-connected-d0-v1",
                    "run_id": f"{self.f1_run_id}-connected-d0-01",
                    "outcome": (
                        "PASS_A90_V3403_CONNECTED_READ_ONLY_"
                        "AWAITING_STAGING_CONTRACT_AND_F1_MANIFEST"
                    ),
                    "target": {
                        "profile": "galaxy-a90-5g-native-init",
                        "matching_a90_usb_devices": 1,
                        "bridge_device": self.bridge_device,
                        "bridge_selected_realpath": self.bridge_realpath,
                        "usb_serial_sha256": "b" * 64,
                    },
                    "health": {
                        "version": cleanup.EXPECTED_VERSION,
                        "version_build": cleanup.EXPECTED_BUILD,
                        "selftest": {"fail": 0},
                        "pstore_entries": 0,
                    },
                    "repository": {
                        "connected_preflight": str(
                            cleanup.CONNECTED_PREFLIGHT.resolve(strict=True)
                        ),
                        "connected_preflight_size": (
                            cleanup.CONNECTED_PREFLIGHT.stat().st_size
                        ),
                        "connected_preflight_sha256": sha256_file(
                            cleanup.CONNECTED_PREFLIGHT
                        ),
                    },
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.connected.chmod(0o600)
        suffix = "20260731-01"
        self.manifest_path = self.run_dir / "manifest.json"
        self.manifest = {
            "schema": cleanup.SCHEMA,
            "status": cleanup.STATUS,
            "run_id": self.run_id,
            "f1_run_id": self.f1_run_id,
            "runner": {
                "path": str(SOURCE),
                "size": SOURCE.stat().st_size,
                "sha256": sha256_file(SOURCE),
            },
            "transport": {
                "path": str(cleanup.A90CTL_SOURCE),
                "size": cleanup.A90CTL_SOURCE.stat().st_size,
                "sha256": sha256_file(cleanup.A90CTL_SOURCE),
            },
            "connected_d0": {
                "path": str(self.connected),
                "size": self.connected.stat().st_size,
                "sha256": sha256_file(self.connected),
            },
            "target": {
                "profile": "galaxy-a90-5g-native-init",
                "bridge_device": self.bridge_device,
                "bridge_realpath_sha256": self.bridge_realpath_sha256,
                "usb_serial_sha256": "b" * 64,
                "expected_vendor_product": cleanup.EXPECTED_VENDOR_PRODUCT,
                "expected_version": cleanup.EXPECTED_VERSION,
                "expected_build": cleanup.EXPECTED_BUILD,
            },
            "work_image": {
                "device_path": cleanup.WORK_PATH,
                "size": self.work_size,
                "mode": cleanup.WORK_MODE,
                "sha256": self.work_sha,
                "host_preservation": {
                    "path": str(self.host_copy),
                    "size": self.work_size,
                    "sha256": self.work_sha,
                },
            },
            "adjacent_paths": {
                "v3406_source": (
                    "/mnt/sdext/a90/runtime/"
                    "debian-bookworm-arm64-phase2-display-v3406-keyed-"
                    f"{suffix}.img"
                ),
                "run_stage": (
                    "/mnt/sdext/a90/runtime/.a90-stage-" + self.f1_run_id
                ),
            },
            "authority": {
                "device_write_authorized": False,
                "fresh_exact_approval_required": True,
                "single_unlink_dispatch": True,
                "unlink_retry_forbidden": True,
            },
        }
        self.write_manifest()

    def write_manifest(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.manifest_path.chmod(0o600)

    def load(self) -> object:
        return cleanup.load_manifest(
            self.manifest_path,
            sha256_file(self.manifest_path),
        )


class RetainedWorkCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.base_patch = mock.patch.object(
            cleanup,
            "PRIVATE_RUN_BASE",
            self.base,
        )
        self.base_patch.start()
        self.addCleanup(self.base_patch.stop)
        self.private_root_patch = mock.patch.object(
            cleanup,
            "PRIVATE_ROOT",
            self.base,
        )
        self.private_root_patch.start()
        self.addCleanup(self.private_root_patch.stop)
        self.fixture = Fixture(self.base)
        self.size_patch = mock.patch.object(
            cleanup,
            "WORK_SIZE",
            self.fixture.work_size,
        )
        self.sha_patch = mock.patch.object(
            cleanup,
            "WORK_SHA256",
            self.fixture.work_sha,
        )
        self.size_patch.start()
        self.sha_patch.start()
        self.addCleanup(self.size_patch.stop)
        self.addCleanup(self.sha_patch.stop)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_host_inspection_and_approval_preparation_do_not_contact_device(self) -> None:
        spec = self.fixture.load()
        inspected = cleanup.inspect(spec)
        self.assertTrue(inspected["ready_for_approval_preparation"])
        self.assertFalse(inspected["device_contact"])
        with mock.patch.object(
            cleanup,
            "remote_command",
            side_effect=AssertionError("device contacted"),
        ):
            prepared = cleanup.prepare_approval(spec)
        self.assertTrue(
            prepared["approval_token"].startswith(cleanup.APPROVAL_PREFIX)
        )
        self.assertEqual(
            prepared["approval_binding"]["transport_sha256"],
            sha256_file(cleanup.A90CTL_SOURCE),
        )
        self.assertEqual(
            (self.fixture.run_dir / "approval-prepared.json").stat().st_mode
            & 0o777,
            0o600,
        )
        self.assertFalse(prepared["live_authorized"])

    def test_live_profile_is_exactly_v3406_and_current_work_hash(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for token in (
            'APPROVAL_PREFIX = "A90-V3406-WORK-CLEANUP-APPROVE:"',
            'WORK_SHA256 = "d1353db59571c3ca4b8be14fed0d19e4a46217ded285e7ceb62ac85b1c6f94c0"',
            'r"^a90-v3406-work-cleanup-[0-9]{8}-[0-9]{2}$"',
            'r"^a90-v3406-debian-display-f1-',
            "debian-bookworm-arm64-phase2-display-v3406-keyed-",
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_connected_d0_requires_one_exact_a90_and_selected_run(self) -> None:
        value = json.loads(self.fixture.connected.read_text(encoding="utf-8"))
        value["target"]["matching_a90_usb_devices"] = 2
        self.fixture.connected.write_text(
            json.dumps(value, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.fixture.connected.chmod(0o600)
        connected = self.fixture.manifest["connected_d0"]
        connected["size"] = self.fixture.connected.stat().st_size
        connected["sha256"] = sha256_file(self.fixture.connected)
        self.fixture.write_manifest()
        with self.assertRaisesRegex(cleanup.ContractError, "connected D0"):
            self.fixture.load()

    def test_manifest_rejects_cross_run_adjacent_source(self) -> None:
        self.fixture.manifest["adjacent_paths"]["v3406_source"] = (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260731-02.img"
        )
        self.fixture.write_manifest()
        with self.assertRaisesRegex(cleanup.ContractError, "adjacent paths"):
            self.fixture.load()

    def test_manifest_rejects_host_preservation_hash_drift(self) -> None:
        self.fixture.manifest["work_image"]["host_preservation"]["sha256"] = (
            "c" * 64
        )
        self.fixture.write_manifest()
        with self.assertRaisesRegex(cleanup.ContractError, "size/hash mismatch"):
            self.fixture.load()

    def test_manifest_rejects_transport_hash_drift(self) -> None:
        self.fixture.manifest["transport"]["sha256"] = "c" * 64
        self.fixture.write_manifest()
        with self.assertRaisesRegex(cleanup.ContractError, "size/hash mismatch"):
            self.fixture.load()

    def test_manifest_requires_private_host_copy_mode_0600(self) -> None:
        self.fixture.host_copy.chmod(0o640)
        with self.assertRaisesRegex(cleanup.ContractError, "mode is not 0600"):
            self.fixture.load()

    def test_manifest_rejects_symlinked_host_copy(self) -> None:
        link = self.base / "preserved-work-link.img"
        link.symlink_to(self.fixture.host_copy)
        self.fixture.manifest["work_image"]["host_preservation"]["path"] = str(
            link
        )
        self.fixture.write_manifest()
        with self.assertRaisesRegex(cleanup.ContractError, "single-link regular"):
            self.fixture.load()

    def test_exact_response_dispatches_cleanup_once(self) -> None:
        spec = self.fixture.load()
        prepared = cleanup.prepare_approval(spec)
        protocol = cleanup.a90ctl.ProtocolResult(
            begin={"cmd": "run"},
            end={"cmd": "run", "rc": "0", "status": "ok"},
            text="work=unlinked\n",
        )
        with (
            mock.patch.object(
                cleanup,
                "require_exact_target",
                return_value={"resolved_bridge": "/dev/ttyACM-test"},
            ),
            mock.patch.object(
                cleanup,
                "require_exact_bridge_process",
                return_value={"matching_bridge_processes": 1},
            ),
            mock.patch.object(
                cleanup,
                "health_preflight",
                return_value={
                    "proven": True,
                    "selftest_fail": 0,
                    "pstore_entries": 0,
                },
            ),
            mock.patch.object(
                cleanup,
                "run_read_preflight",
                return_value={"proof": True},
            ),
            mock.patch.object(
                cleanup,
                "read_presence",
                return_value={
                    "work": "absent",
                    "source": "absent",
                    "stage": "absent",
                },
            ),
            mock.patch.object(
                cleanup,
                "remote_command",
                return_value=protocol,
            ) as dispatch,
        ):
            result = cleanup.execute_cleanup(
                spec,
                prepared["approval_token"],
                self.fixture.run_dir / "live",
                host="127.0.0.1",
                port=cleanup.a90ctl.DEFAULT_PORT,
                read_timeout=cleanup.READ_TIMEOUT_SEC,
                cleanup_timeout=cleanup.CLEANUP_TIMEOUT_SEC,
            )
        self.assertEqual(dispatch.call_count, 1)
        command = dispatch.call_args.args[3]
        self.assertEqual(command[0:4], ["run", "/bin/busybox", "sh", "-c"])
        self.assertIn("/bin/busybox rm --", command[4])
        self.assertNotIn("rm -r", command[4])
        self.assertEqual(
            result["outcome"],
            "PASS_EXACT_RETAINED_WORK_COPY_UNLINKED",
        )
        self.assertEqual(result["dispatch_count"], 1)
        self.assertFalse(result["cleanup_retransmitted"])

    def test_lost_response_reconciles_read_only_without_redispatch(self) -> None:
        spec = self.fixture.load()
        prepared = cleanup.prepare_approval(spec)
        with (
            mock.patch.object(
                cleanup,
                "require_exact_target",
                return_value={"resolved_bridge": "/dev/ttyACM-test"},
            ),
            mock.patch.object(
                cleanup,
                "require_exact_bridge_process",
                return_value={"matching_bridge_processes": 1},
            ),
            mock.patch.object(
                cleanup,
                "health_preflight",
                return_value={
                    "proven": True,
                    "selftest_fail": 0,
                    "pstore_entries": 0,
                },
            ),
            mock.patch.object(
                cleanup,
                "run_read_preflight",
                return_value={"proof": True},
            ),
            mock.patch.object(
                cleanup,
                "read_presence",
                return_value={
                    "work": "absent",
                    "source": "absent",
                    "stage": "absent",
                },
            ),
            mock.patch.object(
                cleanup,
                "remote_command",
                side_effect=TimeoutError("lost response"),
            ) as dispatch,
        ):
            result = cleanup.execute_cleanup(
                spec,
                prepared["approval_token"],
                self.fixture.run_dir / "live",
                host="127.0.0.1",
                port=cleanup.a90ctl.DEFAULT_PORT,
                read_timeout=cleanup.READ_TIMEOUT_SEC,
                cleanup_timeout=cleanup.CLEANUP_TIMEOUT_SEC,
            )
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(
            result["outcome"],
            "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE",
        )
        self.assertTrue(
            (self.fixture.run_dir / "live" / "dispatch-error.json").is_file()
        )
        self.assertFalse(result["cleanup_retransmitted"])

    def test_present_after_ambiguous_response_stops_without_retry(self) -> None:
        spec = self.fixture.load()
        prepared = cleanup.prepare_approval(spec)
        with (
            mock.patch.object(
                cleanup,
                "require_exact_target",
                return_value={"resolved_bridge": "/dev/ttyACM-test"},
            ),
            mock.patch.object(
                cleanup,
                "require_exact_bridge_process",
                return_value={"matching_bridge_processes": 1},
            ),
            mock.patch.object(
                cleanup,
                "health_preflight",
                return_value={
                    "proven": True,
                    "selftest_fail": 0,
                    "pstore_entries": 0,
                },
            ),
            mock.patch.object(
                cleanup,
                "run_read_preflight",
                return_value={"proof": True},
            ),
            mock.patch.object(
                cleanup,
                "read_presence",
                return_value={
                    "work": "present",
                    "source": "absent",
                    "stage": "absent",
                },
            ),
            mock.patch.object(
                cleanup,
                "remote_command",
                side_effect=ConnectionError("response unavailable"),
            ) as dispatch,
        ):
            result = cleanup.execute_cleanup(
                spec,
                prepared["approval_token"],
                self.fixture.run_dir / "live",
                host="127.0.0.1",
                port=cleanup.a90ctl.DEFAULT_PORT,
                read_timeout=cleanup.READ_TIMEOUT_SEC,
                cleanup_timeout=cleanup.CLEANUP_TIMEOUT_SEC,
            )
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(
            result["outcome"],
            "STOP_NO_RETRY_RETAINED_WORK_COPY_NOT_PROVEN_ABSENT",
        )
        self.assertFalse(result["cleanup_retransmitted"])

    def test_pre_dispatch_failure_does_not_create_or_consume_transaction(self) -> None:
        spec = self.fixture.load()
        prepared = cleanup.prepare_approval(spec)
        transaction = self.fixture.run_dir / "live"
        with (
            mock.patch.object(
                cleanup,
                "require_exact_target",
                return_value={"resolved_bridge": "/dev/ttyACM-test"},
            ),
            mock.patch.object(
                cleanup,
                "require_exact_bridge_process",
                return_value={"matching_bridge_processes": 1},
            ),
            mock.patch.object(
                cleanup,
                "health_preflight",
                side_effect=cleanup.ContractError("unhealthy"),
            ),
        ):
            with self.assertRaisesRegex(cleanup.ContractError, "unhealthy"):
                cleanup.execute_cleanup(
                    spec,
                    prepared["approval_token"],
                    transaction,
                    host="127.0.0.1",
                    port=cleanup.a90ctl.DEFAULT_PORT,
                    read_timeout=cleanup.READ_TIMEOUT_SEC,
                    cleanup_timeout=cleanup.CLEANUP_TIMEOUT_SEC,
                )
        self.assertFalse(transaction.exists())

    def test_post_dispatch_read_failure_records_stop_without_redispatch(self) -> None:
        spec = self.fixture.load()
        prepared = cleanup.prepare_approval(spec)
        protocol = cleanup.a90ctl.ProtocolResult(
            begin={"cmd": "run"},
            end={"cmd": "run", "rc": "0", "status": "ok"},
            text="work=unlinked\n",
        )
        with (
            mock.patch.object(
                cleanup,
                "require_exact_target",
                return_value={"resolved_bridge": "/dev/ttyACM-test"},
            ),
            mock.patch.object(
                cleanup,
                "require_exact_bridge_process",
                return_value={"matching_bridge_processes": 1},
            ),
            mock.patch.object(
                cleanup,
                "health_preflight",
                return_value={
                    "proven": True,
                    "selftest_fail": 0,
                    "pstore_entries": 0,
                },
            ),
            mock.patch.object(
                cleanup,
                "run_read_preflight",
                return_value={"proof": True},
            ),
            mock.patch.object(
                cleanup,
                "read_presence",
                side_effect=ConnectionError("post read unavailable"),
            ),
            mock.patch.object(
                cleanup,
                "remote_command",
                return_value=protocol,
            ) as dispatch,
        ):
            result = cleanup.execute_cleanup(
                spec,
                prepared["approval_token"],
                self.fixture.run_dir / "live",
                host="127.0.0.1",
                port=cleanup.a90ctl.DEFAULT_PORT,
                read_timeout=cleanup.READ_TIMEOUT_SEC,
                cleanup_timeout=cleanup.CLEANUP_TIMEOUT_SEC,
            )
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(
            result["outcome"],
            "STOP_NO_RETRY_RETAINED_WORK_COPY_NOT_PROVEN_ABSENT",
        )
        self.assertEqual(result["post_presence"]["work"], "unknown")
        self.assertEqual(result["post_error"]["type"], "ConnectionError")
        self.assertFalse(result["cleanup_retransmitted"])

    def test_post_health_failure_cannot_close_cleanup_pass(self) -> None:
        spec = self.fixture.load()
        prepared = cleanup.prepare_approval(spec)
        protocol = cleanup.a90ctl.ProtocolResult(
            begin={"cmd": "run"},
            end={"cmd": "run", "rc": "0", "status": "ok"},
            text="work=unlinked\n",
        )
        healthy = {"proven": True, "selftest_fail": 0, "pstore_entries": 0}
        with (
            mock.patch.object(
                cleanup,
                "require_exact_target",
                return_value={"resolved_bridge": "/dev/ttyACM-test"},
            ),
            mock.patch.object(
                cleanup,
                "require_exact_bridge_process",
                return_value={"matching_bridge_processes": 1},
            ),
            mock.patch.object(
                cleanup,
                "health_preflight",
                side_effect=[healthy, ConnectionError("post health unavailable")],
            ),
            mock.patch.object(
                cleanup,
                "run_read_preflight",
                return_value={"proof": True},
            ),
            mock.patch.object(
                cleanup,
                "read_presence",
                return_value={
                    "work": "absent",
                    "source": "absent",
                    "stage": "absent",
                },
            ),
            mock.patch.object(
                cleanup,
                "remote_command",
                return_value=protocol,
            ) as dispatch,
        ):
            result = cleanup.execute_cleanup(
                spec,
                prepared["approval_token"],
                self.fixture.run_dir / "live",
                host="127.0.0.1",
                port=cleanup.a90ctl.DEFAULT_PORT,
                read_timeout=cleanup.READ_TIMEOUT_SEC,
                cleanup_timeout=cleanup.CLEANUP_TIMEOUT_SEC,
            )
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(
            result["outcome"],
            "STOP_NO_RETRY_POST_HEALTH_UNPROVEN",
        )
        self.assertFalse(result["post_health"]["proven"])
        self.assertEqual(result["post_error"]["type"], "ConnectionError")
        self.assertTrue(result["effect_proven"])
        self.assertEqual(result["deleted_path"], cleanup.WORK_PATH)

    def test_timeouts_require_exact_approval_bound_values(self) -> None:
        for value in (float("nan"), float("inf"), -1.0, 0.0, 14.99, 15.01):
            with self.subTest(value=value):
                with self.assertRaises(cleanup.ContractError):
                    cleanup.validate_timeout(
                        value,
                        "read timeout",
                        cleanup.READ_TIMEOUT_SEC,
                    )
        self.assertEqual(
            cleanup.validate_timeout(
                cleanup.CLEANUP_TIMEOUT_SEC,
                "cleanup timeout",
                cleanup.CLEANUP_TIMEOUT_SEC,
            ),
            cleanup.CLEANUP_TIMEOUT_SEC,
        )

    def test_duplicate_bridge_flags_are_never_accepted(self) -> None:
        argv = [
            "python3",
            "serial_tcp_bridge.py",
            "--device",
            "/dev/exact",
            "--device",
            "/dev/retargeted",
        ]
        self.assertIsNone(cleanup._argv_unique_value(argv, "--device"))
        self.assertEqual(
            cleanup._argv_unique_value(
                ["bridge", "--device", "/dev/exact"],
                "--device",
            ),
            "/dev/exact",
        )

    def test_dangling_adjacent_symlinks_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            paths = [base / "work", base / "source", base / "stage"]
            for path in paths:
                path.symlink_to(base / f"missing-{path.name}")
            result = subprocess.run(
                [
                    "/bin/sh",
                    "-c",
                    cleanup.presence_script(),
                    "sh",
                    *(str(path) for path in paths),
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
        self.assertEqual(
            result.stdout,
            "work=present source=present stage=present\n",
        )

    def test_source_contract_has_one_nonrecursive_unlink_dispatch(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        body = source[
            source.index("def cleanup_script(") :
            source.index("def presence_script(")
        ]
        self.assertEqual(body.count("rm --"), 1)
        for forbidden in ("rm -r", "rm -f", "sync", "reboot", "sysrq"):
            self.assertNotIn(forbidden, body)
        self.assertGreaterEqual(body.count('[ ! -L "$src" ]'), 1)
        self.assertGreaterEqual(body.count('[ ! -L "$stage" ]'), 1)
        execute = source[
            source.index("def execute_cleanup(") :
            source.index("def inspect(")
        ]
        self.assertLess(
            execute.index('"dispatch.json"'),
            execute.index("result = remote_command("),
        )
        self.assertEqual(execute.count("result = remote_command("), 1)


if __name__ == "__main__":
    unittest.main()
