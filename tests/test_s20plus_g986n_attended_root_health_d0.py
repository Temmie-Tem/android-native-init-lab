import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation"
    / "s20plus_g986n_attended_root_health_d0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "s20plus_g986n_attended_root_health_d0", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakeBackend:
    def __init__(
        self,
        owner: "S20PlusG986NAttendedRootHealthD0Tests",
        *,
        inventories: list[str] | None = None,
        snapshots: list[tuple[int, bytes, bytes]] | None = None,
        root_result: tuple[int, bytes, bytes] | None = None,
        devpath_result: tuple[int, bytes, bytes] | None = None,
        receipts: list[dict[str, object]] | None = None,
    ):
        self.owner = owner
        self.inventories = iter(inventories or [owner.inventory(), owner.inventory()])
        canonical_snapshot = (0, owner.snapshot().encode(), b"")
        self.snapshots = iter(snapshots or [canonical_snapshot, canonical_snapshot])
        self.root_result = root_result or (0, MODULE.EXPECTED_ROOT_STDOUT, b"")
        self.devpath_result = devpath_result or (0, b"usb:3-2.1\n", b"")
        self.receipts = iter(receipts or [owner.adb_receipt(), owner.adb_receipt()])
        self.calls: list[tuple[list[str], float, int]] = []
        self.receipt_calls = 0

    def tool_receipt(self):
        self.receipt_calls += 1
        return copy.deepcopy(next(self.receipts))

    def run(self, argv, timeout, maximum):
        self.calls.append((list(argv), timeout, maximum))
        if argv[-2:] == ["devices", "-l"]:
            return 0, next(self.inventories).encode(), b""
        if argv[-1] == "get-devpath":
            return self.devpath_result
        if "exec-out" in argv:
            return next(self.snapshots)
        if "su" in argv:
            return self.root_result
        raise AssertionError(argv)


class S20PlusG986NAttendedRootHealthD0Tests(unittest.TestCase):
    BOOT_ID = "12345678-1234-1234-1234-123456789abc"

    def adb_receipt(self, **changes):
        value = {
            "path": MODULE.EXPECTED_ADB_PATH,
            "device": 11,
            "inode": 22,
            "mtime_ns": 33,
            "size": MODULE.EXPECTED_ADB_SIZE,
            "sha256": MODULE.EXPECTED_ADB_SHA256,
        }
        value.update(changes)
        return value

    def inventory(self, extra: str = "") -> str:
        return (
            "List of devices attached\n"
            "S20SERIAL device usb:3-2.1 product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
            "S22SERIAL device usb:3-3 product:g0qksx model:SM_S906N device:g0q transport_id:2\n"
            "A90SERIAL device usb:3-4 product:a90qksx model:SM_A908N device:a90q transport_id:3\n"
            + extra
        )

    def snapshot(self, **changes: str) -> str:
        values = {
            "model": "SM-G986N",
            "device": "y2q",
            "product_name": "y2qksx",
            "incremental": "G986NKSS8IYC2",
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
            "boot_id": self.BOOT_ID,
        }
        values.update(changes)
        return "".join(f"{key}={values[key]}\n" for key in MODULE.PUBLIC_SNAPSHOT_KEYS)

    def collect(self, backend: FakeBackend, evidence=None):
        recorder = MODULE.CommandRecorder(backend)
        return MODULE.collect(recorder, evidence), recorder

    def test_render_plan_is_active_and_binds_the_fixed_surface(self):
        plan = MODULE.render_plan()
        self.assertTrue(MODULE.ATTENDED_ROOT_HEALTH_D0_ACTIVE)
        self.assertTrue(plan["attended_root_health_d0_active"])
        self.assertTrue(plan["live_authorized"])
        self.assertEqual(plan["status"], "ACTIVE_ATTENDED_ROOT_HEALTH_D0")
        self.assertEqual(
            plan["fixed_private_root"],
            "workspace/private/runs/s20plus-g986n-attended-root-health-d0",
        )
        self.assertEqual(plan["public_snapshot_keys"], list(MODULE.PUBLIC_SNAPSHOT_KEYS))
        self.assertEqual(plan["root_output_keys"], list(MODULE.ROOT_OUTPUT_KEYS))
        self.assertEqual(plan["expected_root_output"], MODULE.EXPECTED_ROOT_OUTPUT)
        self.assertEqual(plan["planned_counts"]["host_command_count"], 6)
        self.assertEqual(plan["planned_counts"]["device_effect_count"], 0)
        self.assertEqual(plan["root_timeout_seconds"], 30.0)
        self.assertEqual(plan["root_transcript_maximum_bytes"], 4096)
        with mock.patch.object(MODULE, "ATTENDED_ROOT_HEALTH_D0_ACTIVE", False):
            dormant_plan = MODULE.render_plan()
        self.assertFalse(dormant_plan["attended_root_health_d0_active"])
        self.assertFalse(dormant_plan["live_authorized"])
        self.assertEqual(dormant_plan["status"], "DORMANT_NOT_ACTIVE")

    def test_connected_cli_rejects_before_backend_or_evidence_allocation(self):
        output = io.StringIO()
        with (
            mock.patch.object(MODULE, "ATTENDED_ROOT_HEALTH_D0_ACTIVE", False),
            mock.patch.object(MODULE, "FixedBackend", side_effect=AssertionError),
            mock.patch.object(MODULE.EvidenceOwner, "allocate", side_effect=AssertionError),
            contextlib.redirect_stdout(output),
        ):
            status = MODULE.main(["--connected"])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue().strip(), MODULE.DORMANT_VERDICT)
        output = io.StringIO()
        with (
            mock.patch.object(MODULE, "ATTENDED_ROOT_HEALTH_D0_ACTIVE", False),
            mock.patch.object(MODULE, "FixedBackend", side_effect=AssertionError),
            mock.patch.object(MODULE.EvidenceOwner, "allocate", side_effect=AssertionError),
            contextlib.redirect_stdout(output),
        ):
            status = MODULE._execute_connected()
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue().strip(), MODULE.DORMANT_VERDICT)

    def test_fixed_backend_methods_repeat_the_dormant_gate(self):
        backend = MODULE.FixedBackend()
        with (
            mock.patch.object(MODULE, "ATTENDED_ROOT_HEALTH_D0_ACTIVE", False),
            mock.patch.object(MODULE.base, "tool_receipt", side_effect=AssertionError),
        ):
            with self.assertRaisesRegex(MODULE.RootHealthD0Error, "dormant"):
                backend.tool_receipt()
        with (
            mock.patch.object(MODULE, "ATTENDED_ROOT_HEALTH_D0_ACTIVE", False),
            mock.patch.object(MODULE.base, "bounded_command", side_effect=AssertionError),
        ):
            with self.assertRaisesRegex(MODULE.RootHealthD0Error, "dormant"):
                backend.run([MODULE.EXPECTED_ADB_PATH, "devices", "-l"], 10, 1024)

    def test_fake_activated_cli_publishes_success_without_real_device_backend(self):
        backend = FakeBackend(self)
        output = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(MODULE, "FixedBackend", return_value=backend),
            mock.patch.object(MODULE, "repo_root", return_value=Path(temporary)),
            contextlib.redirect_stdout(output),
        ):
            status = MODULE.main(["--connected"])
            runs = list((Path(temporary) / MODULE.FIXED_PRIVATE_ROOT).iterdir())
            self.assertEqual(len(runs), 1)
            self.assertTrue((runs[0] / "result.json").is_file())
            self.assertFalse((runs[0] / "failure.json").exists())
            result = json.loads((runs[0] / "result.json").read_text())
        self.assertEqual(status, 0)
        self.assertIn(MODULE.PASS_VERDICT, output.getvalue())
        self.assertEqual(result["verdict"], MODULE.PASS_VERDICT)
        self.assertEqual(len(backend.calls), 6)

    def test_fake_activated_cli_publishes_failure_without_raw_error_or_retry(self):
        backend = FakeBackend(
            self, root_result=(1, b"bounded-safe-output", b"bounded-safe-error")
        )
        output = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(MODULE, "FixedBackend", return_value=backend),
            mock.patch.object(MODULE, "repo_root", return_value=Path(temporary)),
            contextlib.redirect_stdout(output),
        ):
            status = MODULE.main(["--connected"])
            runs = list((Path(temporary) / MODULE.FIXED_PRIVATE_ROOT).iterdir())
            self.assertEqual(len(runs), 1)
            self.assertTrue((runs[0] / "failure.json").is_file())
            self.assertFalse((runs[0] / "result.json").exists())
            self.assertFalse((runs[0] / "root-stdout.bin").exists())
            self.assertFalse((runs[0] / "root-stderr.bin").exists())
            failure_bytes = (runs[0] / "failure.json").read_bytes()
            failure = json.loads(failure_bytes)
        self.assertEqual(status, 1)
        self.assertIn(MODULE.FAIL_VERDICT, output.getvalue())
        self.assertNotIn(b"bounded-safe-output", failure_bytes)
        self.assertNotIn(b"bounded-safe-error", failure_bytes)
        self.assertEqual(failure["host_command_count"], 4)
        self.assertEqual(len(backend.calls), 4)

    def test_cli_has_only_the_two_fixed_modes_and_requires_one(self):
        options = MODULE.build_parser()._option_string_actions
        self.assertEqual(set(options), {"-h", "--help", "--render-plan", "--connected"})
        for forbidden in (
            "--adb",
            "--serial",
            "--command",
            "--path",
            "--run-dir",
            "--root",
            "--reboot",
            "--odin",
        ):
            self.assertNotIn(forbidden, options)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                MODULE.build_parser().parse_args([])
            with self.assertRaises(SystemExit):
                MODULE.build_parser().parse_args(["--render-plan", "--connected"])
            for abbreviation in (
                "--r",
                "--re",
                "--render-p",
                "--c",
                "--co",
                "--con",
                "--connect",
            ):
                with self.subTest(abbreviation=abbreviation), self.assertRaises(SystemExit):
                    MODULE.build_parser().parse_args([abbreviation])

    def test_success_uses_exact_six_command_order_and_only_selected_serial(self):
        backend = FakeBackend(self)
        result, recorder = self.collect(backend)
        calls = backend.calls
        self.assertEqual(len(calls), 6)
        adb = MODULE.EXPECTED_ADB_PATH
        self.assertEqual(calls[0][0], [adb, "devices", "-l"])
        self.assertEqual(calls[1][0], [adb, "-s", "S20SERIAL", "get-devpath"])
        self.assertEqual(
            calls[2][0],
            [
                adb,
                "-s",
                "S20SERIAL",
                "exec-out",
                "sh",
                "-c",
                MODULE.PUBLIC_SHELL_ARGUMENT,
            ],
        )
        self.assertEqual(
            calls[3][0],
            [
                adb,
                "-s",
                "S20SERIAL",
                "shell",
                "su",
                "-c",
                shlex.quote(MODULE.ROOT_READ_SCRIPT),
            ],
        )
        self.assertEqual(calls[4][0], calls[2][0])
        self.assertEqual(calls[5][0], [adb, "devices", "-l"])
        self.assertTrue(
            all(
                argv[argv.index("-s") + 1] == "S20SERIAL"
                for argv, _timeout, _maximum in calls
                if "-s" in argv
            )
        )
        self.assertEqual(calls[0][1:], (10.0, 32 * 1024))
        self.assertEqual(calls[1][1:], (10.0, 32 * 1024))
        self.assertEqual(calls[2][1:], (20.0, 8 * 1024))
        self.assertEqual(calls[3][1:], (30.0, 4096))
        self.assertEqual(calls[4][1:], (20.0, 8 * 1024))
        self.assertEqual(calls[5][1:], (10.0, 32 * 1024))
        self.assertEqual(recorder.evidence()["host_command_count"], 6)
        self.assertEqual(recorder.evidence()["selected_target_command_count"], 4)
        self.assertEqual(recorder.evidence()["root_command_count"], 1)
        self.assertEqual(backend.receipt_calls, 2)
        self.assertEqual(result["verdict"], MODULE.PASS_VERDICT)
        self.assertTrue(result["root_used"])
        self.assertFalse(result["root_writes"])
        self.assertEqual(result["device_effect_count"], 0)

    def test_fake_adb_argument_join_preserves_one_public_inner_script(self):
        backend = FakeBackend(self)
        self.collect(backend)
        public_argv = backend.calls[2][0]
        tail = public_argv[public_argv.index("exec-out") + 1 :]
        joined_by_adb = " ".join(tail)
        self.assertEqual(
            shlex.split(joined_by_adb),
            ["sh", "-c", MODULE.PUBLIC_SNAPSHOT_SCRIPT],
        )
        raw_tail = ["sh", "-c", MODULE.PUBLIC_SNAPSHOT_SCRIPT]
        self.assertNotEqual(
            shlex.split(" ".join(raw_tail)),
            ["sh", "-c", MODULE.PUBLIC_SNAPSHOT_SCRIPT],
        )
        self.assertNotEqual(public_argv[-1], MODULE.PUBLIC_SNAPSHOT_SCRIPT)
        self.assertEqual(public_argv[-1], shlex.quote(MODULE.PUBLIC_SNAPSHOT_SCRIPT))
        root_argv = backend.calls[3][0]
        root_tail = root_argv[root_argv.index("shell") + 1 :]
        self.assertEqual(
            shlex.split(" ".join(root_tail)),
            ["su", "-c", MODULE.ROOT_READ_SCRIPT],
        )

    def test_success_result_hashes_all_private_identity(self):
        backend = FakeBackend(self)
        result, _recorder = self.collect(backend)
        encoded = json.dumps(result, sort_keys=True)
        for private in (
            "S20SERIAL",
            "S22SERIAL",
            "A90SERIAL",
            "usb:3-2.1",
            self.BOOT_ID,
        ):
            self.assertNotIn(private, encoded)
        self.assertEqual(
            result["target"]["adb_serial_sha256"],
            hashlib.sha256(b"S20SERIAL").hexdigest(),
        )
        self.assertEqual(result["root_health"], MODULE.EXPECTED_ROOT_OUTPUT)
        self.assertEqual(result["public_health"]["selinux"], "Enforcing")
        self.assertNotIn("boot_id", result["public_health"])
        self.assertEqual(result["other_target_command_count"], 0)
        self.assertEqual(result["s22plus_command_count"], 0)
        self.assertEqual(result["a90_command_count"], 0)

    def test_initial_wrong_partial_offline_or_ambiguous_target_stops_before_selection(self):
        rows = (
            "",
            "WRONG device usb:3-2.1 product:y2qksx model:SM_G986B device:y2q transport_id:1\n",
            "WRONG device usb:3-2.1 product:g0qksx model:SM_G986N device:g0q transport_id:1\n",
            "WRONG device usb:3-2.1 product:wrong model:SM_G986N device:y2q transport_id:1\n",
            "WRONG offline usb:3-2.1 product:y2qksx model:SM_G986N device:y2q transport_id:1\n",
            "WRONG unauthorized usb:3-2.1 product:y2qksx model:SM_G986N device:y2q transport_id:1\n",
            (
                "ONE device usb:3-2.1 product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
                "TWO device usb:3-2.2 product:g0qksx model:SM_G986N device:g0q transport_id:2\n"
            ),
        )
        for rows_text in rows:
            with self.subTest(rows=rows_text):
                inventory = "List of devices attached\n" + rows_text
                backend = FakeBackend(self, inventories=[inventory, inventory])
                recorder = MODULE.CommandRecorder(backend)
                with self.assertRaises(MODULE.RootHealthD0Error):
                    MODULE.collect(recorder)
                self.assertEqual(len(backend.calls), 1)
                self.assertNotIn("-s", backend.calls[0][0])

    def test_duplicate_serial_and_conflicting_metadata_stop_at_inventory(self):
        duplicate = self.inventory(
            "S20SERIAL device usb:3-2.1 product:y2qksx model:SM_G986N device:y2q transport_id:4\n"
        )
        conflict = (
            "List of devices attached\n"
            "S20SERIAL device usb:3-2.1 product:y2qksx product:g0qksx "
            "model:SM_G986N device:y2q transport_id:1\n"
        )
        for inventory in (duplicate, conflict):
            with self.subTest(inventory=inventory):
                backend = FakeBackend(self, inventories=[inventory, inventory])
                recorder = MODULE.CommandRecorder(backend)
                with self.assertRaises(MODULE.base.InventoryError):
                    MODULE.collect(recorder)
                self.assertEqual(len(backend.calls), 1)

    def test_snapshot_parser_rejects_schema_order_identity_health_and_framing(self):
        canonical = self.snapshot()
        cases = (
            self.snapshot(model="SM-G986B"),
            self.snapshot(device="g0q"),
            self.snapshot(product_name="wrong"),
            self.snapshot(incremental="G986NKSS7IYA1"),
            self.snapshot(boot_completed="0"),
            self.snapshot(bootanim="running"),
            self.snapshot(selinux="Permissive"),
            self.snapshot(boot_id="not-a-boot-id"),
            canonical.replace("model=SM-G986N\n", ""),
            canonical + "model=SM-G986N\n",
            canonical.replace(
                "model=SM-G986N\ndevice=y2q\n",
                "device=y2q\nmodel=SM-G986N\n",
            ),
            canonical.rstrip("\n"),
            canonical.replace("\n", "\r\n"),
        )
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(MODULE.RootHealthD0Error):
                MODULE.parse_public_snapshot((0, payload.encode(), b""))
        for result in (
            (1, canonical.encode(), b""),
            (0, canonical.encode(), b"warning"),
            (0, b"\xff", b""),
            (0, b"x" * (MODULE.MAX_SNAPSHOT_BYTES + 1), b""),
            (True, canonical.encode(), b""),
        ):
            with self.subTest(result=result), self.assertRaises(MODULE.RootHealthD0Error):
                MODULE.parse_public_snapshot(result)

    def test_pre_post_snapshot_drift_stops_before_final_inventory(self):
        changed = self.snapshot(
            boot_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        ).encode()
        backend = FakeBackend(
            self,
            snapshots=[(0, self.snapshot().encode(), b""), (0, changed, b"")],
        )
        recorder = MODULE.CommandRecorder(backend)
        with self.assertRaisesRegex(MODULE.RootHealthD0Error, "changed"):
            MODULE.collect(recorder)
        self.assertEqual(len(backend.calls), 5)
        self.assertEqual(recorder.root_command_count, 1)

    def test_final_inventory_replacement_reorder_or_metadata_drift_is_rejected(self):
        final_variants = (
            self.inventory().replace("S20SERIAL", "REPLACED"),
            (
                "List of devices attached\n"
                "S22SERIAL device usb:3-3 product:g0qksx model:SM_S906N device:g0q transport_id:2\n"
                "S20SERIAL device usb:3-2.1 product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
                "A90SERIAL device usb:3-4 product:a90qksx model:SM_A908N device:a90q transport_id:3\n"
            ),
            self.inventory().replace("transport_id:1", "transport_id:9"),
            self.inventory().replace("usb:3-2.1", "usb:3-2.9", 1),
        )
        for final in final_variants:
            with self.subTest(final=final):
                backend = FakeBackend(self, inventories=[self.inventory(), final])
                recorder = MODULE.CommandRecorder(backend)
                with self.assertRaises(MODULE.RootHealthD0Error):
                    MODULE.collect(recorder)
                self.assertEqual(len(backend.calls), 6)

    def test_malformed_devpath_stops_before_snapshot_or_root(self):
        for result in (
            (0, b"/sys/devices/private\n", b""),
            (0, b"usb:3-2.1", b""),
            (0, b"usb:3-2.1\n\n", b""),
            (0, b" usb:3-2.1\n", b""),
            (0, b"usb:3-2.1 \n", b""),
            (0, b"usb:3-2\n", b"warning"),
            (1, b"usb:3-2\n", b""),
            (0, b"\xff", b""),
        ):
            with self.subTest(result=result):
                backend = FakeBackend(self, devpath_result=result)
                recorder = MODULE.CommandRecorder(backend)
                with self.assertRaises(MODULE.RootHealthD0Error):
                    MODULE.collect(recorder)
                self.assertEqual(len(backend.calls), 2)
                self.assertEqual(recorder.root_command_count, 0)

    def test_inventory_usb_token_must_be_single_and_equal_get_devpath(self):
        variants = (
            self.inventory().replace("usb:3-2.1 ", "", 1),
            self.inventory().replace("usb:3-2.1", "usb:3-2.9", 1),
            self.inventory().replace(
                "usb:3-2.1", "usb:3-2.1 usb:3-2.9", 1
            ),
            self.inventory().replace(
                "usb:3-2.1", "usb:3-2.1 usb:3-2.1", 1
            ),
        )
        for inventory in variants:
            with self.subTest(inventory=inventory):
                backend = FakeBackend(self, inventories=[inventory, inventory])
                recorder = MODULE.CommandRecorder(backend)
                with self.assertRaises(MODULE.RootHealthD0Error):
                    MODULE.collect(recorder)
                self.assertIn(len(backend.calls), (1, 2))
                self.assertEqual(recorder.root_command_count, 0)

    def test_root_parser_accepts_only_exact_ordered_canonical_bytes(self):
        self.assertEqual(
            MODULE.parse_root_result((0, MODULE.EXPECTED_ROOT_STDOUT, b"")),
            MODULE.EXPECTED_ROOT_OUTPUT,
        )
        canonical = MODULE.EXPECTED_ROOT_STDOUT
        cases = (
            canonical.replace(b"uid=0", b"uid=1", 1),
            canonical.replace(b"gid=0", b"gid=1000", 1),
            canonical.replace(b"u:r:magisk:s0", b"u:r:shell:s0", 1),
            canonical.replace(b"30.7:MAGISK:R", b"30.6:MAGISK:R", 1),
            canonical.replace(b"30700", b"30600", 1),
            canonical.replace(b"Enforcing", b"Permissive", 1),
            canonical.replace(b"/system/bin/init", b"/init", 1),
            canonical.replace(b"u:r:init:s0", b"u:r:su:s0", 1),
            canonical.replace(b"uid=0\ngid=0\n", b"gid=0\nuid=0\n", 1),
            canonical + b"uid=0\n",
            canonical.replace(b"uid=0\n", b"", 1),
            canonical.rstrip(b"\n"),
            canonical.replace(b"\n", b"\r\n"),
            canonical + b"\x00",
            b"\xff",
        )
        for stdout in cases:
            with self.subTest(stdout=stdout), self.assertRaises(MODULE.RootHealthD0Error):
                MODULE.parse_root_result((0, stdout, b""))

    def test_root_parser_rejects_rc_stderr_type_and_combined_bound(self):
        canonical = MODULE.EXPECTED_ROOT_STDOUT
        cases = (
            (1, canonical, b""),
            (0, canonical, b"warning"),
            (True, canonical, b""),
            (0, "not-bytes", b""),
            (0, canonical, "not-bytes"),
            (0, b"x" * (MODULE.MAX_ROOT_TRANSCRIPT_BYTES + 1), b""),
            [0, canonical, b""],
        )
        for value in cases:
            with self.subTest(value=type(value)), self.assertRaises(MODULE.RootHealthD0Error):
                MODULE.parse_root_result(value)

    def test_root_backend_timeout_is_counted_once_and_never_retried(self):
        backend = FakeBackend(self)
        original_run = backend.run

        def timeout_at_root(argv, timeout, maximum):
            if "su" in argv:
                backend.calls.append((list(argv), timeout, maximum))
                raise TimeoutError("bounded fake timeout")
            return original_run(argv, timeout, maximum)

        backend.run = timeout_at_root
        recorder = MODULE.CommandRecorder(backend)
        with self.assertRaises(TimeoutError):
            MODULE.collect(recorder)
        self.assertEqual(len(backend.calls), 4)
        self.assertEqual(recorder.root_command_count, 1)
        self.assertEqual(backend.calls[-1][1:], (30.0, 4096))

    def test_tool_receipt_schema_and_drift_are_rejected(self):
        bad_receipts = (
            self.adb_receipt(path="/usr/bin/adb"),
            self.adb_receipt(size=1),
            self.adb_receipt(sha256="0" * 64),
            self.adb_receipt(device=True),
            {"path": MODULE.EXPECTED_ADB_PATH},
        )
        for receipt in bad_receipts:
            with self.subTest(receipt=receipt):
                backend = FakeBackend(self, receipts=[receipt, receipt])
                recorder = MODULE.CommandRecorder(backend)
                with self.assertRaises(MODULE.RootHealthD0Error):
                    MODULE.collect(recorder)
                self.assertEqual(backend.calls, [])
        backend = FakeBackend(
            self,
            receipts=[self.adb_receipt(), self.adb_receipt(mtime_ns=34)],
        )
        recorder = MODULE.CommandRecorder(backend)
        with self.assertRaisesRegex(MODULE.RootHealthD0Error, "changed"):
            MODULE.collect(recorder)
        self.assertEqual(len(backend.calls), 6)

    def test_private_evidence_is_atomic_no_clobber_and_identifier_free(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            with MODULE.EvidenceOwner.allocate(repo) as owner:
                backend = FakeBackend(self)
                result, _recorder = self.collect(backend, owner)
                result_receipt = owner.publish_json("result.json", result)
                self.assertEqual(
                    set(owner.receipts),
                    {"root-stdout.bin", "root-stderr.bin", "result.json"},
                )
                self.assertEqual(result_receipt["mode"], "0400")
                self.assertEqual(result_receipt["link_count"], 1)
                for path in owner.path.iterdir():
                    self.assertFalse(path.name.startswith(".tmp-"))
                    observed = path.lstat()
                    self.assertTrue(stat.S_ISREG(observed.st_mode))
                    self.assertEqual(stat.S_IMODE(observed.st_mode), 0o400)
                    self.assertEqual(observed.st_nlink, 1)
                self.assertEqual(
                    (owner.path / "root-stdout.bin").read_bytes(),
                    MODULE.EXPECTED_ROOT_STDOUT,
                )
                self.assertEqual((owner.path / "root-stderr.bin").read_bytes(), b"")
                combined = b"".join(path.read_bytes() for path in owner.path.iterdir())
                for private in (
                    b"S20SERIAL",
                    b"S22SERIAL",
                    b"A90SERIAL",
                    b"usb:3-2.1",
                    self.BOOT_ID.encode(),
                ):
                    self.assertNotIn(private, combined)
                with self.assertRaises(FileExistsError):
                    owner.publish("result.json", b"replacement")

    def test_private_token_in_root_transcript_is_never_persisted(self):
        for private in (
            b"S20SERIAL",
            b"S22SERIAL",
            b"A90SERIAL",
            b"usb:3-2.1",
            self.BOOT_ID.encode(),
        ):
            with self.subTest(private=private), tempfile.TemporaryDirectory() as temporary:
                malicious = MODULE.EXPECTED_ROOT_STDOUT + private + b"\n"
                with MODULE.EvidenceOwner.allocate(Path(temporary)) as owner:
                    backend = FakeBackend(self, root_result=(0, malicious, b""))
                    recorder = MODULE.CommandRecorder(backend)
                    with self.assertRaisesRegex(MODULE.RootHealthD0Error, "private"):
                        MODULE.collect(recorder, owner)
                    self.assertEqual(owner.receipts, {})
                    self.assertEqual(list(owner.path.iterdir()), [])

    def test_failure_receipt_hashes_error_and_reports_actual_zero_effect_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            with MODULE.EvidenceOwner.allocate(Path(temporary)) as owner:
                backend = FakeBackend(
                    self,
                    root_result=(1, b"safe-root-output", b"safe-private-error"),
                )
                recorder = MODULE.CommandRecorder(backend)
                with self.assertRaises(MODULE.RootHealthD0Error) as raised:
                    MODULE.collect(recorder, owner)
                failure = MODULE.failure_result(recorder, raised.exception, owner)
                encoded = json.dumps(failure, sort_keys=True)
                self.assertNotIn("safe-private-error", encoded)
                self.assertNotIn("safe-root-output", encoded)
                self.assertEqual(failure["host_command_count"], 4)
                self.assertEqual(failure["root_command_count"], 1)
                self.assertTrue(failure["root_used"])
                self.assertEqual(failure["device_effect_count"], 0)
                self.assertFalse(failure["device_writes"])
                self.assertEqual(failure["private_raw_evidence"], {})
                digest = failure["root_transcript_digest"]
                self.assertFalse(digest["raw_published"])
                self.assertEqual(digest["returncode"], 1)
                self.assertEqual(
                    digest["stdout_sha256"], hashlib.sha256(b"safe-root-output").hexdigest()
                )
                self.assertEqual(
                    digest["stderr_sha256"],
                    hashlib.sha256(b"safe-private-error").hexdigest(),
                )
                self.assertEqual(list(owner.path.iterdir()), [])

    def test_evidence_owner_rejects_symlink_roots_names_and_final_nodes(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            repo = Path(temporary)
            (repo / "workspace").mkdir()
            (repo / "workspace/private").symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaises(MODULE.RootHealthD0Error):
                MODULE.EvidenceOwner.allocate(repo)
        with tempfile.TemporaryDirectory() as temporary:
            with MODULE.EvidenceOwner.allocate(Path(temporary)) as owner:
                with self.assertRaises(MODULE.RootHealthD0Error):
                    owner.publish("arbitrary.json", b"x")
                with self.assertRaises(MODULE.RootHealthD0Error):
                    owner.publish(
                        "root-stdout.bin",
                        b"x" * (MODULE.MAX_ROOT_TRANSCRIPT_BYTES + 1),
                    )
                outside = Path(temporary) / "outside"
                outside.write_bytes(b"untouched")
                (owner.path / "failure.json").symlink_to(outside)
                with self.assertRaises(MODULE.RootHealthD0Error):
                    owner.publish("failure.json", b"replacement")
                self.assertEqual(outside.read_bytes(), b"untouched")

    def test_fixed_private_root_and_run_are_direct_owned_0700_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            with MODULE.EvidenceOwner.allocate(repo) as owner:
                fixed = repo / MODULE.FIXED_PRIVATE_ROOT
                self.assertEqual(owner.path.parent, fixed)
                for path in (fixed, owner.path):
                    observed = path.lstat()
                    self.assertTrue(stat.S_ISDIR(observed.st_mode))
                    self.assertFalse(stat.S_ISLNK(observed.st_mode))
                    self.assertEqual(stat.S_IMODE(observed.st_mode), 0o700)
                    self.assertEqual(observed.st_uid, os.geteuid())

    def test_inventory_helper_closure_is_exact_and_rejects_symlink_or_hardlink(self):
        receipt = MODULE.INVENTORY_HELPER_RECEIPT
        self.assertEqual(receipt["size"], MODULE.INVENTORY_HELPER_SIZE)
        self.assertEqual(receipt["sha256"], MODULE.INVENTORY_HELPER_SHA256)
        self.assertEqual(Path(receipt["path"]), SCRIPT.with_name(MODULE.INVENTORY_HELPER_NAME))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            direct = root / "direct"
            payload = b"exact-source"
            direct.write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(
                MODULE._direct_regular_receipt(
                    direct, expected_size=len(payload), expected_sha256=expected
                )["sha256"],
                expected,
            )
            symlink = root / "symlink"
            symlink.symlink_to(direct)
            with self.assertRaises(OSError):
                MODULE._direct_regular_receipt(
                    symlink, expected_size=len(payload), expected_sha256=expected
                )
            hardlink = root / "hardlink"
            os.link(direct, hardlink)
            with self.assertRaises(MODULE.RootHealthD0Error):
                MODULE._direct_regular_receipt(
                    direct, expected_size=len(payload), expected_sha256=expected
                )

    def test_self_receipt_normalizes_only_the_activation_literal(self):
        source = SCRIPT.read_bytes()
        receipt = MODULE.self_receipt()
        self.assertEqual(receipt["size"], len(source))
        self.assertEqual(receipt["sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(
            receipt["normalized_sha256"], MODULE.normalized_source_sha256(source)
        )
        dormant = source.replace(
            b"ATTENDED_ROOT_HEALTH_D0_ACTIVE = True",
            b"ATTENDED_ROOT_HEALTH_D0_ACTIVE = False",
            1,
        )
        self.assertNotEqual(hashlib.sha256(source).hexdigest(), hashlib.sha256(dormant).hexdigest())
        self.assertEqual(
            MODULE.normalized_source_sha256(source),
            MODULE.normalized_source_sha256(dormant),
        )
        unrelated = source.replace(
            b'VERSION = "s20plus-g986n-attended-root-health-d0-v1"',
            b'VERSION = "s20plus-g986n-attended-root-health-d0-v2"',
            1,
        )
        self.assertNotEqual(
            MODULE.normalized_source_sha256(source),
            MODULE.normalized_source_sha256(unrelated),
        )
        with self.assertRaises(MODULE.RootHealthD0Error):
            MODULE.normalized_source_sha256(
                source
                + b"\nATTENDED_ROOT_HEALTH_D0_ACTIVE = False\n"
            )

    def test_fixed_remote_scripts_have_no_write_control_or_partition_surface(self):
        scripts = (MODULE.PUBLIC_SNAPSHOT_SCRIPT + MODULE.ROOT_READ_SCRIPT).lower()
        for forbidden in (
            "setprop ",
            "settings ",
            " chmod ",
            " chown ",
            " mount ",
            " umount ",
            " mkdir ",
            " rm ",
            " mv ",
            " cp ",
            " reboot",
            "odin",
            "/dev/block",
            "magisk --install",
            "disable",
            "ro.serialno",
            "imei",
        ):
            self.assertNotIn(forbidden, scripts)
        self.assertEqual(MODULE.ROOT_SHELL_ARGUMENT, shlex.quote(MODULE.ROOT_READ_SCRIPT))
        self.assertEqual(
            MODULE.PUBLIC_SHELL_ARGUMENT, shlex.quote(MODULE.PUBLIC_SNAPSHOT_SCRIPT)
        )
        self.assertEqual(
            hashlib.sha256(MODULE.ROOT_READ_SCRIPT.encode()).hexdigest(),
            MODULE.render_plan()["root_script_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
