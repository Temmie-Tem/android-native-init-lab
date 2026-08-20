"""Host-only regression tests for native_init_flash safety helpers."""

from __future__ import annotations

import io
import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation


flash = load_revalidation("native_init_flash")


class NativeInitFlashSafetyHelpers(unittest.TestCase):
    def test_minimal_bridge_command_never_resends_after_post_send_error(self) -> None:
        sends = []

        class Socket:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def settimeout(self, _value):
                pass

            def sendall(self, value):
                sends.append(value)

            def recv(self, _size):
                raise OSError("response lost after send")

        with mock.patch.object(
            flash.socket, "create_connection", return_value=Socket()
        ) as connect:
            with self.assertRaisesRegex(RuntimeError, "one send"):
                flash.bridge_command(
                    "127.0.0.1", 2222, "recovery", 30,
                    retry_transport=False,
                )
        self.assertEqual(len(sends), 1)
        self.assertEqual(connect.call_count, 1)

    def test_minimal_busy_recovery_and_twrp_uncertainty_never_retry(self) -> None:
        args = types.SimpleNamespace(
            bridge_host="127.0.0.1",
            bridge_port=2222,
            bridge_timeout=30,
            require_empty_adb_baseline=True,
            require_stable_adb_baseline=False,
            adb="adb",
        )
        with mock.patch.object(
            flash, "bridge_command", return_value="[busy]"
        ) as bridge:
            with self.assertRaisesRegex(RuntimeError, "does not resend"):
                flash.reboot_native_to_recovery(args)
        self.assertEqual(bridge.call_count, 1)

        result = types.SimpleNamespace(stdout="", stderr="")
        with mock.patch.object(flash.time, "sleep"), mock.patch.object(
            flash, "run_command", return_value=result
        ) as run, mock.patch.object(
            flash, "wait_for_adb_disconnect", return_value=False
        ):
            with self.assertRaisesRegex(RuntimeError, "does not resend"):
                flash.reboot_twrp_to_system(args, "A90")
        self.assertEqual(run.call_count, 1)
        twrp_argv = run.call_args.args[0]
        self.assertEqual(twrp_argv[-1], flash.TWRP_SYSTEM_REBOOT_COMMAND)
        self.assertIn(flash.TWRP_SYSTEM_SCRIPT_SHA256, twrp_argv[-1])
        self.assertIn("exec twrp reboot", twrp_argv[-1])
        self.assertNotIn("dd if=", twrp_argv[-1])

    def test_parse_adb_devices_filters_header_blank_lines_and_keeps_states(self) -> None:
        output = """
List of devices attached

R58M123456 device product:r3q model:SM_A908N
offline-serial offline
recovery-serial recovery
"""

        self.assertEqual(
            flash.parse_adb_devices(output),
            [
                ("R58M123456", "device"),
                ("offline-serial", "offline"),
                ("recovery-serial", "recovery"),
            ],
        )

    def test_strict_adb_inventory_rejects_failure_and_malformed_lines(self) -> None:
        self.assertEqual(
            flash.parse_adb_devices_strict("List of devices attached\n\n"), []
        )
        for output in (
            "",
            "OTHER HEADER\n",
            "List of devices attached\nOTHER\n",
            "List of devices attached\nA recovery\nA device\n",
        ):
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                flash.parse_adb_devices_strict(output)

        for result in (
            types.SimpleNamespace(returncode=1, stdout="", stderr=""),
            types.SimpleNamespace(
                returncode=0,
                stdout="List of devices attached\n\n",
                stderr="daemon warning",
            ),
        ):
            with self.subTest(result=result), mock.patch.object(
                flash.subprocess, "run", return_value=result
            ):
                with self.assertRaisesRegex(RuntimeError, "inventory command"):
                    flash.adb_devices("adb", strict=True)

    def test_strict_disconnect_does_not_turn_inventory_failure_into_absence(self) -> None:
        failure = types.SimpleNamespace(returncode=1, stdout="", stderr="")
        with mock.patch.object(
            flash.subprocess, "run", return_value=failure
        ), self.assertRaisesRegex(RuntimeError, "inventory command"):
            flash.wait_for_adb_disconnect(
                "adb", "A90", 1.0, strict_inventory=True
            )

    def test_unique_recovery_arrival_rejects_multiple_adb_endpoints(self) -> None:
        with mock.patch.object(
            flash,
            "adb_devices",
            return_value=[("A90", "recovery"), ("OTHER", "device")],
        ):
            with self.assertRaisesRegex(RuntimeError, "ADB arrival is ambiguous"):
                flash.wait_for_adb_state(
                    "adb",
                    None,
                    {"recovery"},
                    1.0,
                    require_unique=True,
                )

    def test_stable_foreign_adb_baseline_binds_one_new_recovery(self) -> None:
        baseline = [("OTHER", "device")]
        inventories = [
            baseline,
            [("OTHER", "device"), ("A90", "recovery")],
        ]
        with mock.patch.object(
            flash, "adb_devices", side_effect=inventories
        ), mock.patch.object(flash.time, "sleep"):
            self.assertEqual(
                flash.wait_for_new_recovery_adb(
                    "adb",
                    baseline,
                    5.0,
                    expected_serial_sha256=hashlib.sha256(b"A90").hexdigest(),
                ),
                ("A90", "recovery"),
            )

    def test_stable_baseline_rejects_wrong_recovery_serial(self) -> None:
        baseline = [("OTHER", "device")]
        with mock.patch.object(
            flash,
            "adb_devices",
            return_value=[("OTHER", "device"), ("WRONG", "recovery")],
        ):
            with self.assertRaisesRegex(RuntimeError, "not the bound A90"):
                flash.wait_for_new_recovery_adb(
                    "adb",
                    baseline,
                    1.0,
                    expected_serial_sha256=hashlib.sha256(b"A90").hexdigest(),
                )

    def test_stable_foreign_adb_baseline_rejects_drift_or_ambiguity(self) -> None:
        baseline = [("OTHER", "device")]
        for inventory, message in (
            ([("OTHER", "offline"), ("A90", "recovery")], "changed"),
            (
                [
                    ("OTHER", "device"),
                    ("A90", "recovery"),
                    ("FOREIGN", "device"),
                ],
                "ambiguous",
            ),
        ):
            with self.subTest(inventory=inventory), mock.patch.object(
                flash, "adb_devices", return_value=inventory
            ):
                with self.assertRaisesRegex(RuntimeError, message):
                    flash.wait_for_new_recovery_adb(
                        "adb",
                        baseline,
                        1.0,
                        expected_serial_sha256=hashlib.sha256(b"A90").hexdigest(),
                    )

    def test_stable_foreign_adb_baseline_requires_exact_restoration(self) -> None:
        baseline = [("OTHER", "device")]
        with mock.patch.object(
            flash,
            "adb_devices",
            side_effect=[
                [("OTHER", "device"), ("A90", "recovery")],
                baseline,
            ],
        ), mock.patch.object(flash.time, "sleep"):
            self.assertTrue(
                flash.wait_for_adb_baseline_restored(
                    "adb", "A90", baseline, 5.0
                )
            )

        with mock.patch.object(
            flash, "adb_devices", return_value=[("OTHER", "offline")]
        ):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                flash.wait_for_adb_baseline_restored(
                    "adb", "A90", baseline, 1.0
                )

    def test_empty_baseline_option_is_from_native_and_nonselected_only(self) -> None:
        for argv in (
            ["native_init_flash.py", "boot.img", "--require-empty-adb-baseline"],
            [
                "native_init_flash.py",
                "boot.img",
                "--from-native",
                "--serial",
                "SERIAL",
                "--require-empty-adb-baseline",
            ],
        ):
            with self.subTest(argv=argv), mock.patch("sys.argv", argv):
                with self.assertRaisesRegex(SystemExit, "requires --from-native"):
                    flash.main()

        for argv in (
            ["native_init_flash.py", "boot.img", "--require-stable-adb-baseline"],
            [
                "native_init_flash.py",
                "boot.img",
                "--from-native",
                "--serial",
                "SERIAL",
                "--require-stable-adb-baseline",
            ],
            [
                "native_init_flash.py",
                "boot.img",
                "--from-native",
                "--require-empty-adb-baseline",
                "--require-stable-adb-baseline",
            ],
        ):
            with self.subTest(argv=argv), mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit):
                    flash.main()

    def test_normalize_sha256_accepts_none_and_lowercases_valid_hex(self) -> None:
        self.assertIsNone(flash.normalize_sha256(None, label="hash"))
        self.assertEqual(flash.normalize_sha256("A" * 64, label="hash"), "a" * 64)

        for value in ("a" * 63, "g" * 64):
            with self.assertRaisesRegex(RuntimeError, "64-character hex SHA256"):
                flash.normalize_sha256(value, label="hash")

    def test_quote_remote_path_rejects_non_absolute_and_nul_paths(self) -> None:
        self.assertEqual(flash.quote_remote_path("/tmp/native init.img", label="remote"), "'/tmp/native init.img'")

        for path in ("relative.img", "/tmp/bad\x00name"):
            with self.assertRaisesRegex(RuntimeError, "absolute remote path"):
                flash.quote_remote_path(path, label="remote")

    def test_file_contains_finds_markers_across_chunk_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "image.bin"
            needle = b"v2237-marker"
            path.write_bytes(b"A" * (1024 * 1024 - 4) + needle + b"ZZZ")

            self.assertTrue(flash.file_contains(path, needle))
            self.assertFalse(flash.file_contains(path, b"missing-marker"))

    def test_inspect_local_image_accepts_pinned_aligned_image_with_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "boot.img"
            marker = b"A90 Linux init 0.9.268"
            image.write_bytes(marker + b"\0" * (flash.BOOT_READBACK_BLOCK_SIZE - len(marker)))
            image.chmod(0o600)
            expected_hash = flash.local_sha256(image)

            path, digest, size = flash.inspect_local_image(
                types.SimpleNamespace(
                    boot_image=str(image),
                    expect_version=marker.decode(),
                    expect_sha256=expected_hash,
                )
            )

        self.assertEqual(path, image)
        self.assertEqual(digest, expected_hash)
        self.assertEqual(size, flash.BOOT_READBACK_BLOCK_SIZE)

    def test_inspect_local_image_can_require_android_boot_magic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "android.img"
            image.write_bytes(flash.ANDROID_BOOT_MAGIC + b"\0" * (
                flash.BOOT_READBACK_BLOCK_SIZE - len(flash.ANDROID_BOOT_MAGIC)
            ))
            image.chmod(0o600)
            expected_hash = flash.local_sha256(image)

            path, digest, _size = flash.inspect_local_image(
                types.SimpleNamespace(
                    boot_image=str(image),
                    expect_version=None,
                    expect_sha256=expected_hash,
                    expect_android_magic=True,
                )
            )
            self.assertEqual(path, image)
            self.assertEqual(digest, expected_hash)

            bad = root / "bad.img"
            bad.write_bytes(b"NOTBOOT!" + b"\0" * (flash.BOOT_READBACK_BLOCK_SIZE - 8))
            bad.chmod(0o600)
            with self.assertRaisesRegex(RuntimeError, "Android boot magic"):
                flash.inspect_local_image(
                    types.SimpleNamespace(
                        boot_image=str(bad),
                        expect_version=None,
                        expect_sha256=flash.local_sha256(bad),
                        expect_android_magic=True,
                    )
                )

    def test_inspect_local_image_rejects_unsafe_or_unpinned_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = root / "missing.img"
            with self.assertRaises(FileNotFoundError):
                flash.inspect_local_image(
                    types.SimpleNamespace(boot_image=str(missing), expect_version=None, expect_sha256=None)
                )

            image = root / "boot.img"
            image.write_bytes(b"x" * flash.BOOT_READBACK_BLOCK_SIZE)
            image.chmod(0o664)
            with self.assertRaisesRegex(RuntimeError, "group/world writable"):
                flash.inspect_local_image(
                    types.SimpleNamespace(boot_image=str(image), expect_version=None, expect_sha256=None)
                )

            image.chmod(0o600)
            image.write_bytes(b"unaligned")
            with self.assertRaisesRegex(RuntimeError, "4096-byte aligned"):
                flash.inspect_local_image(
                    types.SimpleNamespace(boot_image=str(image), expect_version=None, expect_sha256=None)
                )

            image.write_bytes(b"x" * flash.BOOT_READBACK_BLOCK_SIZE)
            with self.assertRaisesRegex(RuntimeError, "expected version marker not found"):
                flash.inspect_local_image(
                    types.SimpleNamespace(boot_image=str(image), expect_version="missing", expect_sha256=None)
                )

            with self.assertRaisesRegex(RuntimeError, "local image sha256 mismatch"):
                flash.inspect_local_image(
                    types.SimpleNamespace(boot_image=str(image), expect_version=None, expect_sha256="0" * 64)
                )

    def test_sealed_local_image_copy_rejects_source_mutation_and_yields_private_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "boot.img"
            image.write_bytes(b"a" * flash.BOOT_READBACK_BLOCK_SIZE)
            digest = flash.local_sha256(image)
            with flash.sealed_local_image_copy(image, digest, flash.BOOT_READBACK_BLOCK_SIZE) as sealed:
                self.assertNotEqual(sealed, image)
                self.assertEqual(sealed.stat().st_mode & 0o777, 0o600)
                self.assertEqual(flash.local_sha256(sealed), digest)

            image.write_bytes(b"b" * flash.BOOT_READBACK_BLOCK_SIZE)
            with self.assertRaisesRegex(RuntimeError, "sealed image sha256 mismatch"):
                with flash.sealed_local_image_copy(image, digest, flash.BOOT_READBACK_BLOCK_SIZE):
                    pass

            image.write_bytes(b"c")
            with self.assertRaisesRegex(RuntimeError, "boot image size changed before push"):
                with flash.sealed_local_image_copy(image, digest, flash.BOOT_READBACK_BLOCK_SIZE):
                    pass

    def test_verify_cmdv1_result_rejects_nonzero_rc_or_status(self) -> None:
        flash.verify_cmdv1_result(types.SimpleNamespace(rc=0, status="ok", text="fine"), "version")

        for result in (
            types.SimpleNamespace(rc=1, status="ok", text="bad rc"),
            types.SimpleNamespace(rc=0, status="err", text="bad status"),
        ):
            with self.assertRaisesRegex(RuntimeError, "cmdv1 version failed"):
                flash.verify_cmdv1_result(result, "version")

    def test_verify_android_adb_waits_for_boot_complete_and_optional_root(self) -> None:
        args = types.SimpleNamespace(
            adb="adb",
            serial=None,
            android_timeout=10.0,
            android_root_check=True,
        )

        with mock.patch.object(flash, "wait_for_adb_state", return_value=("SERIAL", "device")) as wait_mock, \
                mock.patch.object(
                    flash,
                    "adb_shell_text",
                    side_effect=["", "0", "1", "", "uid=0(root) gid=0(root)"],
                ) as shell_mock, \
                mock.patch.object(flash.time, "sleep"):
            summary = flash.verify_android_adb(args)

        wait_mock.assert_called_once_with("adb", None, {"device"}, 10.0)
        self.assertIn("android_adb serial=SERIAL", summary)
        self.assertIn("sys.boot_completed='1'", summary)
        self.assertIn("uid=0", summary)
        self.assertEqual(shell_mock.call_args_list[-1].args, ("adb", "SERIAL", "su -c id"))

    def test_verify_android_adb_rejects_failed_root_check(self) -> None:
        args = types.SimpleNamespace(
            adb="adb",
            serial="SERIAL",
            android_timeout=10.0,
            android_root_check=True,
        )

        with mock.patch.object(flash, "wait_for_adb_state", return_value=("SERIAL", "device")), \
                mock.patch.object(
                    flash,
                    "adb_shell_text",
                    side_effect=["1", "", "uid=2000(shell)"],
                ):
            with self.assertRaisesRegex(RuntimeError, "Android root check failed"):
                flash.verify_android_adb(args)

    def test_verify_post_flash_target_dispatches_by_target(self) -> None:
        native_args = types.SimpleNamespace(post_flash_target="native-init")
        android_args = types.SimpleNamespace(post_flash_target="android-adb")

        with mock.patch.object(flash, "verify_native_init", return_value="native") as native_mock, \
                mock.patch.object(flash, "verify_android_adb", return_value="android") as android_mock:
            self.assertEqual(flash.verify_post_flash_target(native_args), "native")
            self.assertEqual(flash.verify_post_flash_target(android_args), "android")

        native_mock.assert_called_once_with(native_args)
        android_mock.assert_called_once_with(android_args)

    def test_parse_args_exposes_android_target_options(self) -> None:
        with mock.patch(
            "sys.argv",
            [
                "native_init_flash.py",
                "android-boot.img",
                "--post-flash-target",
                "android-adb",
                "--android-timeout",
                "42",
                "--android-root-check",
                "--expect-android-magic",
            ],
        ):
            args = flash.parse_args()

        self.assertEqual(args.boot_image, "android-boot.img")
        self.assertEqual(args.post_flash_target, "android-adb")
        self.assertEqual(args.android_timeout, 42.0)
        self.assertTrue(args.android_root_check)
        self.assertTrue(args.expect_android_magic)

    def test_parse_args_exposes_experimental_self_write_options(self) -> None:
        with mock.patch(
            "sys.argv",
            [
                "native_init_flash.py",
                "boot.img",
                "--experimental-self-write",
                "--self-write-plan-only",
                "--self-write-staging-dir",
                "/cache/a90-runtime/flash-staging",
            ],
        ):
            args = flash.parse_args()

        self.assertTrue(args.experimental_self_write)
        self.assertTrue(args.self_write_plan_only)
        self.assertEqual(args.self_write_staging_dir, "/cache/a90-runtime/flash-staging")

    def test_build_experimental_self_write_plan_is_fail_closed_and_bounded(self) -> None:
        args = types.SimpleNamespace(
            bridge_host="127.0.0.1",
            bridge_port=54321,
            expect_sha256="a" * 64,
            expect_version="0.11.124",
            expect_android_magic=True,
            allow_unpinned_image=False,
            self_write_staging_dir="/mnt/sdext/a90/flash-staging",
        )

        plan = flash.build_experimental_self_write_plan(
            args,
            Path("/tmp/boot_linux_v3361.img"),
            "a" * 64,
            4096,
        )

        self.assertEqual(plan["policy_state"], "plan-only-live-blocked")
        self.assertIn("production/default fast-flash remains gated", plan["policy_block"])
        self.assertEqual(plan["remote_image"], "/mnt/sdext/a90/flash-staging/boot_linux_v3361.img")
        self.assertEqual(
            plan["source_plan_command"],
            [
                "boot-flash-plan",
                "/mnt/sdext/a90/flash-staging/boot_linux_v3361.img",
                "a" * 64,
                "0.11.124",
            ],
        )
        self.assertEqual(plan["self_write_command"][0:2], ["boot-flash-f2", "BOOT-FLASH-F2-BOOT-CANDIDATE"])
        self.assertEqual(plan["required_timeline_events"][0], "candidate_flash_start")
        self.assertLess(
            plan["stage_command"].index("--device-binary"),
            plan["stage_command"].index("install"),
        )

    def test_experimental_self_write_rejects_unapproved_inputs(self) -> None:
        base = dict(
            bridge_host="127.0.0.1",
            bridge_port=54321,
            expect_sha256="a" * 64,
            expect_version="0.11.124",
            expect_android_magic=True,
            allow_unpinned_image=False,
            self_write_staging_dir="/mnt/sdext/a90/flash-staging",
        )

        cases = [
            ("expect_sha256", None, "requires --expect-sha256"),
            ("expect_version", None, "requires --expect-version"),
            ("expect_android_magic", False, "requires --expect-android-magic"),
            ("allow_unpinned_image", True, "does not allow --allow-unpinned-image"),
            ("self_write_staging_dir", "/tmp", "must be one of"),
        ]
        for key, value, pattern in cases:
            values = dict(base)
            values[key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(RuntimeError, pattern):
                    flash.build_experimental_self_write_plan(
                        types.SimpleNamespace(**values),
                        Path("/tmp/boot.img"),
                        "a" * 64,
                        4096,
                    )

    def test_main_experimental_self_write_plan_only_prints_json_without_device_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "boot.img"
            marker = b"0.11.124"
            image.write_bytes(flash.ANDROID_BOOT_MAGIC + marker + b"\0" * (
                flash.BOOT_READBACK_BLOCK_SIZE - len(flash.ANDROID_BOOT_MAGIC) - len(marker)
            ))
            image.chmod(0o600)
            digest = flash.local_sha256(image)

            argv = [
                "native_init_flash.py",
                str(image),
                "--expect-sha256",
                digest,
                "--expect-version",
                marker.decode(),
                "--expect-android-magic",
                "--experimental-self-write",
                "--self-write-plan-only",
            ]
            stdout = io.StringIO()
            with mock.patch("sys.argv", argv), \
                    mock.patch("sys.stdout", stdout), \
                    mock.patch.object(flash, "wait_for_adb_state") as wait_mock:
                self.assertEqual(flash.main(), 0)

        wait_mock.assert_not_called()
        plan = json.loads(stdout.getvalue())
        self.assertEqual(plan["mode"], "experimental-self-write")
        self.assertEqual(plan["policy_state"], "plan-only-live-blocked")
        self.assertEqual(plan["local_sha256"], digest)

    def test_experimental_self_write_without_plan_only_is_policy_blocked(self) -> None:
        args = types.SimpleNamespace(
            bridge_host="127.0.0.1",
            bridge_port=54321,
            expect_sha256="a" * 64,
            expect_version="0.11.124",
            expect_android_magic=True,
            allow_unpinned_image=False,
            self_write_staging_dir="/mnt/sdext/a90/flash-staging",
            self_write_plan_only=False,
        )

        with mock.patch("sys.stdout", io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "production/default fast-flash remains gated"):
                flash.run_experimental_self_write(args, Path("/tmp/boot.img"), "a" * 64, 4096)

    def test_self_write_plan_f3_mode_sets_rollback_command_and_live_policy(self) -> None:
        args = types.SimpleNamespace(
            bridge_host="127.0.0.1",
            bridge_port=54321,
            expect_sha256=flash.SELF_WRITE_F4_LIVE_SHA256,
            expect_version=flash.SELF_WRITE_F4_LIVE_VERSION,
            expect_android_magic=True,
            allow_unpinned_image=False,
            self_write_staging_dir="/mnt/sdext/a90/flash-staging",
            self_write_mode="f3",
            self_write_live_authorized=True,
        )
        plan = flash.build_experimental_self_write_plan(
            args,
            Path("/tmp/boot_linux_v2321.img"),
            flash.SELF_WRITE_F4_LIVE_SHA256,
            4096,
        )
        self.assertEqual(plan["self_write_mode"], "f3")
        self.assertEqual(plan["policy_state"], "f4-live-authorized")
        self.assertEqual(
            plan["self_write_command"][0:2],
            ["boot-flash-f3", "BOOT-FLASH-F3-SELF-ROLLBACK"],
        )
        self.assertEqual(plan["self_write_success_marker"], "result=ok rollback-written-ready-to-reboot")

    def test_self_write_live_still_blocked_without_authorization_flag(self) -> None:
        # mode f3 + valid candidate but no --self-write-live-authorized must stay fail-closed.
        args = types.SimpleNamespace(
            bridge_host="127.0.0.1",
            bridge_port=54321,
            expect_sha256=flash.SELF_WRITE_F4_LIVE_SHA256,
            expect_version=flash.SELF_WRITE_F4_LIVE_VERSION,
            expect_android_magic=True,
            allow_unpinned_image=False,
            self_write_staging_dir="/mnt/sdext/a90/flash-staging",
            self_write_mode="f3",
            self_write_plan_only=False,
            self_write_live_authorized=False,
        )
        with mock.patch("sys.stdout", io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "production/default fast-flash remains gated"):
                flash.run_experimental_self_write(
                    args,
                    Path("/tmp/boot_linux_v2321.img"),
                    flash.SELF_WRITE_F4_LIVE_SHA256,
                    4096,
                )

    def test_self_write_live_guards_reject_non_f3_mode(self) -> None:
        args = types.SimpleNamespace(self_write_mode="f2", expect_version=flash.SELF_WRITE_F4_LIVE_VERSION)
        with self.assertRaisesRegex(RuntimeError, "only for --self-write-mode f3"):
            flash.run_self_write_live(args, {"self_write_success_marker": "x"},
                                      Path("/tmp/boot.img"), flash.SELF_WRITE_F4_LIVE_SHA256, 4096)

    def test_self_write_live_guards_reject_non_v2321_candidate(self) -> None:
        args = types.SimpleNamespace(self_write_mode="f3", expect_version=flash.SELF_WRITE_F4_LIVE_VERSION)
        with self.assertRaisesRegex(RuntimeError, "must be the v2321 rollback image"):
            flash.run_self_write_live(args, {"self_write_success_marker": "x"},
                                      Path("/tmp/boot.img"), "b" * 64, 4096)

    def test_parse_native_version_field_is_exact(self) -> None:
        self.assertEqual(
            flash.parse_native_version_field("version: 0.9.285 build=v2321-x\r\n"),
            "0.9.285",
        )
        # a longer string that merely contains the target as a substring must not match exactly
        self.assertEqual(
            flash.parse_native_version_field("version: 10.9.2850 build=other\r\n"),
            "10.9.2850",
        )
        self.assertNotEqual(
            flash.parse_native_version_field("version: 10.9.2850 build=other\r\n"),
            "0.9.285",
        )
        self.assertIsNone(flash.parse_native_version_field("status: ok\r\n"))

    def test_wait_for_native_version_requires_exact_field_and_clean_result(self) -> None:
        args = types.SimpleNamespace(bridge_host="127.0.0.1", bridge_port=54321)
        good = types.SimpleNamespace(rc=0, status="ok", text="version: 0.9.285 build=v2321\r\n")
        wrong = types.SimpleNamespace(rc=0, status="ok", text="version: 0.11.123 build=v3360\r\n")
        errframe = types.SimpleNamespace(rc=1, status="err", text="version: 0.9.285 build=x\r\n")

        # wrong version, then error frame, then good -> must keep polling and return only on exact match
        seq = [wrong, errframe, good]
        with mock.patch.object(flash, "run_cmdv1_command", side_effect=seq), \
                mock.patch.object(flash.time, "sleep"), \
                mock.patch("sys.stdout", io.StringIO()):
            out = flash.wait_for_native_version(args, "0.9.285", overall_timeout=30.0, poll_interval=0.0)
        self.assertIn("0.9.285", out)

        # never-correct version must raise, not false-succeed
        with mock.patch.object(flash, "run_cmdv1_command", return_value=wrong), \
                mock.patch.object(flash.time, "sleep"), \
                mock.patch("sys.stdout", io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "did not report exact version 0.9.285"):
                flash.wait_for_native_version(args, "0.9.285", overall_timeout=0.05, poll_interval=0.0)

    def test_parse_args_exposes_f4_live_options(self) -> None:
        with mock.patch("sys.argv", [
            "native_init_flash.py",
            "boot.img",
            "--experimental-self-write",
            "--self-write-mode", "f3",
            "--self-write-live-authorized",
        ]):
            args = flash.parse_args()
        self.assertEqual(args.self_write_mode, "f3")
        self.assertTrue(args.self_write_live_authorized)

        with mock.patch("sys.argv", ["native_init_flash.py", "boot.img"]):
            defaults = flash.parse_args()
        self.assertEqual(defaults.self_write_mode, "f2")
        self.assertFalse(defaults.self_write_live_authorized)
        # flash-cycle tuning knobs: skip-source-plan opt-in, tight reboot poll, safe menu settle
        self.assertFalse(defaults.self_write_skip_source_plan)
        self.assertEqual(defaults.reboot_poll_interval_sec, 0.5)
        self.assertEqual(defaults.menu_settle_sec, 3.0)


if __name__ == "__main__":
    unittest.main()
