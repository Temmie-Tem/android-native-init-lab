import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s20plus_g986n_routine_actions.py"

import sys
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20plus_g986n_routine_actions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class S20PlusG986NRoutineActionsTests(unittest.TestCase):
    def inventory(self, s20_serial: str = "S20SERIAL") -> str:
        return (
            "List of devices attached\n"
            f"{s20_serial} device product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
            "S22SERIAL device product:g0qksx model:SM_S906N device:g0q transport_id:2\n"
            "A90SERIAL device product:a90 model:SM_A908N device:a90q transport_id:3\n"
        )

    def snapshot(self) -> str:
        values = {key: "" for key in MODULE.base.PROPERTY_KEYS}
        values.update(
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product_name": "y2qksx",
                "build_product": "y2q",
                "fingerprint": "samsung/y2qksx/y2q:13/TP1A/G986NKSS8IYC2:user/release-keys",
                "incremental": "G986NKSS8IYC2",
                "build_id": "TP1A",
                "android_release": "13",
                "sdk": "33",
                "security_patch": "2025-03-01",
                "build_type": "user",
                "build_tags": "release-keys",
                "build_characteristics": "phone",
                "verified_boot_state": "orange",
                "flash_locked": "0",
                "vbmeta_device_state": "unlocked",
                "hardware": "qcom",
                "board_platform": "kona",
                "soc_manufacturer": "QTI",
                "soc_model": "SM8250",
                "cpu_abilist": "arm64-v8a,armeabi-v7a,armeabi",
                "first_api_level": "29",
                "boot_completed": "1",
                "bootanim": "stopped",
                "kernel_release": "4.19.113-27166950",
                "machine": "aarch64",
                "selinux": "Enforcing",
                "shell_identity": "uid=2000(shell) gid=2000(shell)",
                "boot_id": "11111111-2222-3333-4444-555555555555",
            }
        )
        return "".join(f"{key}={values[key]}\n" for key in MODULE.base.PROPERTY_KEYS)

    def fake_artifact(self, root: Path, relative: Path, size: int, sha256: str):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
        return mock.patch.object(
            MODULE,
            "require_artifact",
            return_value={"path": str(path.resolve()), "size": size, "sha256": sha256},
        )

    def common_command(self, calls: list[list[str]], extra):
        def command(argv, _timeout, _maximum):
            calls.append(argv)
            if argv[-2:] == ["devices", "-l"]:
                return 0, self.inventory().encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2.1\n", b""
            if "exec-out" in argv and argv[-1] == MODULE.base.REMOTE_SNAPSHOT:
                return 0, self.snapshot().encode(), b""
            return extra(argv)
        return command

    def test_dry_run_is_device_hidden_and_actions_are_closed(self):
        for action in MODULE.IMPLEMENTED_ACTIONS:
            plan = MODULE.dry_run_plan(action)
            self.assertFalse(plan["live_authorized"])
            self.assertFalse(plan["partition_access"])
            self.assertFalse(plan["flash_requested"])
        options = MODULE.build_parser()._option_string_actions
        for forbidden in ("--adb", "--artifact", "--destination", "--serial", "--shell"):
            self.assertNotIn(forbidden, options)
        self.assertTrue(MODULE.PATCHED_AP_RETRIEVAL_ACTIVE)
        self.assertEqual(MODULE.ACTIONS.count(MODULE.PATCHED_AP_ACTION), 1)
        self.assertIn(MODULE.PATCHED_AP_ACTION, options["--action"].choices)

    def test_exact_target_preflight_rejects_wrong_identity_before_effect(self):
        calls: list[list[str]] = []
        wrong = self.inventory().replace("product:y2qksx", "product:g0qksx")

        def command(argv, _timeout, _maximum):
            calls.append(argv)
            return 0, wrong.encode(), b""

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(MODULE.RoutineActionError):
                MODULE.run_action("reboot-system", root=Path(temporary), command=command)
        self.assertEqual(len(calls), 1)
        self.assertFalse(any("reboot" in call for call in calls))

    def test_reboot_and_mode_actions_dispatch_exactly_once_without_retry(self):
        for action, argument in (
            ("reboot-system", None),
            ("enter-download", "download"),
            ("enter-recovery", "recovery"),
        ):
            with self.subTest(action=action):
                calls: list[list[str]] = []

                def extra(argv):
                    if "reboot" in argv:
                        return 0, b"", b""
                    raise AssertionError(argv)

                with tempfile.TemporaryDirectory() as temporary:
                    result, _ = MODULE.run_action(
                        action,
                        root=Path(temporary),
                        command=self.common_command(calls, extra),
                    )
                effect_calls = [call for call in calls if "reboot" in call]
                self.assertEqual(len(effect_calls), 1)
                self.assertEqual(effect_calls[0][effect_calls[0].index("-s") + 1], "S20SERIAL")
                self.assertEqual(effect_calls[0][-1], argument or "reboot")
                self.assertTrue(result["verification"]["terminal_health_pending"])
                self.assertFalse(result["verification"]["replay_permitted"])
                self.assertEqual(result["s22plus_command_count"], 0)
                self.assertEqual(result["a90_command_count"], 0)

    def test_install_magisk_is_exact_and_verifies_package(self):
        calls: list[list[str]] = []

        def extra(argv):
            if "install" in argv:
                return 0, b"Success\n", b""
            if argv[-3:] == ["pm", "path", MODULE.MAGISK_PACKAGE]:
                return 0, b"package:/data/app/example/base.apk\n", b""
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.fake_artifact(
                root, MODULE.MAGISK_APK_REL, MODULE.MAGISK_APK_SIZE, MODULE.MAGISK_APK_SHA256
            ):
                result, _ = MODULE.run_action(
                    "install-magisk",
                    root=root,
                    command=self.common_command(calls, extra),
                )
        install = [call for call in calls if "install" in call]
        self.assertEqual(len(install), 1)
        self.assertIn("--no-streaming", install[0])
        self.assertIn("-r", install[0])
        self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_MAGISK_APK_INSTALLED")
        self.assertTrue(result["effect"]["package_install"])
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn("S20SERIAL", encoded)
        self.assertNotIn("S22SERIAL", encoded)
        self.assertNotIn("A90SERIAL", encoded)

    def test_stage_ap_is_no_clobber_hash_verified_and_exact(self):
        calls: list[list[str]] = []

        def extra(argv):
            if "df" in argv:
                return 0, b"Filesystem 1K-blocks Used Available Use% Mounted on\n/data 100000000 1 50000000 1% /data\n", b""
            if "mkdir" in argv:
                return 0, b"", b""
            if "push" in argv:
                return 0, b"1 file pushed\n", b""
            if "sha256sum" in argv:
                path = argv[-1]
                return 0, f"{MODULE.AP_SHA256}  {path}\n".encode(), b""
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.fake_artifact(root, MODULE.AP_REL, MODULE.AP_SIZE, MODULE.AP_SHA256):
                result, _ = MODULE.run_action(
                    "stage-ap",
                    root=root,
                    command=self.common_command(calls, extra),
                )
        push = [call for call in calls if "push" in call]
        self.assertEqual(len(push), 1)
        self.assertEqual(push[0][-1], MODULE.AP_REMOTE)
        self.assertEqual(sum("sha256sum" in call for call in calls), 1)
        self.assertEqual(sum("mkdir" in call for call in calls), 1)
        self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_AP_STAGED_VERIFIED")
        self.assertTrue(result["effect"]["user_storage_stage"])
        self.assertFalse(result["effect"]["partition_access"])

    def test_retrieve_patched_ap_is_single_match_private_no_clobber_and_hash_exact(self):
        calls: list[list[str]] = []
        payload = b"patched-ap-fixture"
        digest = MODULE.hashlib.sha256(payload).hexdigest()
        remote = "/sdcard/Download/magisk_patched-30700_AbC12.tar"

        def extra(argv):
            if argv[-1] == MODULE.PATCHED_AP_DISCOVERY:
                return 0, f"{remote}\n".encode(), b""
            if "stat" in argv:
                return 0, f"{len(payload)}\n".encode(), b""
            if "sha256sum" in argv:
                return 0, f"{digest}  {remote}\n".encode(), b""
            if "pull" in argv:
                Path(argv[-1]).write_bytes(payload)
                return 0, b"1 file pulled\n", b""
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE, "PATCHED_AP_MIN_SIZE", 1
        ), mock.patch.object(MODULE, "PATCHED_AP_MAX_SIZE", 1024), mock.patch.object(
            MODULE, "PATCHED_AP_HOST_RESERVE", 0
        ):
            root = Path(temporary)
            result, _ = MODULE.run_action(
                MODULE.PATCHED_AP_ACTION,
                root=root,
                command=self.common_command(calls, extra),
            )
            final_path = Path(result["verification"]["host_private_path"])
            self.assertEqual(final_path.read_bytes(), payload)
            self.assertEqual(final_path.stat().st_mode & 0o777, 0o400)
            self.assertEqual(final_path.parent, root / MODULE.PATCHED_AP_DEST_REL)
            self.assertEqual(list(final_path.parent.glob(".*.partial-*")), [])
        pulls = [call for call in calls if "pull" in call]
        self.assertEqual(len(pulls), 1)
        self.assertEqual(pulls[0][-2], remote)
        self.assertEqual(result["verification"]["sha256"], digest)
        self.assertTrue(result["d0_authorized"])
        self.assertFalse(result["d1_authorized"])
        self.assertEqual(result["effect_command_count"], 0)
        self.assertFalse(result["effect"]["device_write"])
        self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_PATCHED_AP_RETRIEVED_VERIFIED")

    def test_retrieve_rejects_zero_multiple_or_malformed_candidates_before_pull(self):
        candidates = (
            "",
            "/sdcard/Download/magisk_patched-30700_A.tar\n"
            "/sdcard/Download/magisk_patched-30700_B.tar\n",
            "/sdcard/Download/not-magisk.tar\n",
            "/sdcard/Download/../magisk_patched-30700_A.tar\n",
        )
        for discovery in candidates:
            with self.subTest(discovery=discovery):
                calls: list[list[str]] = []

                def extra(argv):
                    if argv[-1] == MODULE.PATCHED_AP_DISCOVERY:
                        return 0, discovery.encode(), b""
                    raise AssertionError(argv)

                with tempfile.TemporaryDirectory() as temporary, self.assertRaises(
                    MODULE.RoutineActionError
                ):
                    MODULE.run_action(
                        MODULE.PATCHED_AP_ACTION,
                        root=Path(temporary),
                        command=self.common_command(calls, extra),
                    )
                self.assertFalse(any("pull" in call for call in calls))

    def test_device_side_discovery_filter_emits_only_closed_ascii_grammar(self):
        valid = "/sdcard/Download/magisk_patched-30700_AbC12_-x.tar"
        invalid = (
            "/sdcard/Download/magisk_patched-30700_has space.tar",
            "/sdcard/Download/magisk_patched-30700_한글.tar",
            "/sdcard/Download/magisk_patched-30700_" + "A" * 65 + ".tar",
            "/sdcard/Download/magisk_patched-30700_.tar",
        )
        mixed = "\n".join((invalid[0], valid, *invalid[1:])) + "\n"
        filtered = subprocess.run(
            ["grep", "-E", MODULE.PATCHED_AP_DEVICE_ERE],
            input=mixed.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertEqual(filtered.stdout.decode(), valid + "\n")
        invalid_only = subprocess.run(
            ["grep", "-E", MODULE.PATCHED_AP_DEVICE_ERE],
            input=("\n".join(invalid) + "\n").encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(invalid_only.returncode, 1)
        self.assertEqual(invalid_only.stdout, b"")
        self.assertIn(
            f"LC_ALL=C toybox grep -E '{MODULE.PATCHED_AP_DEVICE_ERE}'",
            MODULE.PATCHED_AP_DISCOVERY,
        )

    def test_retrieve_wrong_target_rejects_before_discovery_or_pull(self):
        calls: list[list[str]] = []
        wrong = self.inventory().replace("device:y2q", "device:g0q", 1)

        def command(argv, _timeout, _maximum):
            calls.append(argv)
            return 0, wrong.encode(), b""

        with tempfile.TemporaryDirectory() as temporary, self.assertRaises(
            MODULE.RoutineActionError
        ):
            MODULE.run_action(
                MODULE.PATCHED_AP_ACTION,
                root=Path(temporary),
                command=command,
            )
        self.assertEqual(len(calls), 1)
        self.assertFalse(any(MODULE.PATCHED_AP_DISCOVERY in call for call in calls))
        self.assertFalse(any("pull" in call for call in calls))

    def test_retrieve_rejects_size_hash_and_existing_destination_before_pull_or_publish(self):
        remote = "/sdcard/Download/magisk_patched-30700_AbC12.tar"
        for case in ("size", "hash", "existing"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                calls: list[list[str]] = []
                root = Path(temporary)
                payload = b"patched"
                digest = MODULE.hashlib.sha256(payload).hexdigest()
                if case == "existing":
                    destination = root / MODULE.PATCHED_AP_DEST_REL
                    destination.mkdir(parents=True)
                    (destination / Path(remote).name).write_bytes(b"keep")

                def extra(argv):
                    if argv[-1] == MODULE.PATCHED_AP_DISCOVERY:
                        return 0, f"{remote}\n".encode(), b""
                    if "stat" in argv:
                        return 0, (b"0\n" if case == "size" else f"{len(payload)}\n".encode()), b""
                    if "sha256sum" in argv:
                        value = "0" * 64 if case == "hash" else digest
                        return 0, f"{value}  {remote}\n".encode(), b""
                    if "pull" in argv:
                        Path(argv[-1]).write_bytes(payload)
                        return 0, b"pulled\n", b""
                    raise AssertionError(argv)

                with mock.patch.object(MODULE, "PATCHED_AP_MIN_SIZE", 1), mock.patch.object(
                    MODULE, "PATCHED_AP_MAX_SIZE", 1024
                ), mock.patch.object(MODULE, "PATCHED_AP_HOST_RESERVE", 0), self.assertRaises(
                    MODULE.RoutineActionError
                ):
                    MODULE.run_action(
                        MODULE.PATCHED_AP_ACTION,
                        root=root,
                        command=self.common_command(calls, extra),
                    )
                if case in ("size", "existing"):
                    self.assertFalse(any("pull" in call for call in calls))
                if case == "existing":
                    self.assertEqual((destination / Path(remote).name).read_bytes(), b"keep")

    def test_retrieve_unexpected_partial_node_retains_guard_and_fails_closed(self):
        calls: list[list[str]] = []
        remote = "/sdcard/Download/magisk_patched-30700_AbC12.tar"
        payload = b"patched"
        digest = MODULE.hashlib.sha256(payload).hexdigest()

        def extra(argv):
            if argv[-1] == MODULE.PATCHED_AP_DISCOVERY:
                return 0, f"{remote}\n".encode(), b""
            if "stat" in argv:
                return 0, f"{len(payload)}\n".encode(), b""
            if "sha256sum" in argv:
                return 0, f"{digest}  {remote}\n".encode(), b""
            if "pull" in argv:
                Path(argv[-1]).mkdir()
                return 1, b"", b"pull failed\n"
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE, "PATCHED_AP_MIN_SIZE", 1
        ), mock.patch.object(MODULE, "PATCHED_AP_MAX_SIZE", 1024), mock.patch.object(
            MODULE, "PATCHED_AP_HOST_RESERVE", 0
        ):
            root = Path(temporary)
            run_dir = MODULE.allocate_run_dir(root, MODULE.PATCHED_AP_ACTION, None)
            MODULE.acquire_guard(root, run_dir, MODULE.PATCHED_AP_ACTION, None)
            recorder = MODULE.Recorder(
                self.common_command(calls, extra)
            )
            with self.assertRaisesRegex(MODULE.RoutineActionError, "pull failed"):
                MODULE.run_action(
                    MODULE.PATCHED_AP_ACTION,
                    root=root,
                    recorder=recorder,
                )
            self.assertFalse(recorder.retrieval_cleanup_confirmed)
            self.assertEqual(
                len(list((root / MODULE.PATCHED_AP_DEST_REL).glob(".*.partial-*"))),
                1,
            )
            self.assertFalse(
                MODULE.close_guard_after_failure(
                    root,
                    run_dir=run_dir,
                    action=MODULE.PATCHED_AP_ACTION,
                    effect_command_count=recorder.effect_command_count,
                    retrieval_cleanup_confirmed=recorder.retrieval_cleanup_confirmed,
                )
            )
            self.assertTrue(MODULE.guard_path(root).is_file())

    def test_stage_rejects_low_space_before_transfer(self):
        calls: list[list[str]] = []

        def extra(argv):
            if "df" in argv:
                return 0, b"Filesystem 1K-blocks Used Available Use% Mounted on\n/data 10 1 2 1% /data\n", b""
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.fake_artifact(root, MODULE.AP_REL, MODULE.AP_SIZE, MODULE.AP_SHA256):
                with self.assertRaisesRegex(MODULE.RoutineActionError, "insufficient"):
                    MODULE.run_action(
                        "stage-ap",
                        root=root,
                        command=self.common_command(calls, extra),
                    )
        self.assertFalse(any("push" in call for call in calls))

    def test_remote_hash_parser_and_df_fail_closed(self):
        self.assertEqual(
            MODULE.parse_remote_sha256(f"{MODULE.AP_SHA256}  {MODULE.AP_REMOTE}", MODULE.AP_REMOTE),
            MODULE.AP_SHA256,
        )
        for malformed in ("", "bad", f"{MODULE.AP_SHA256}  /wrong"):
            with self.subTest(malformed=malformed), self.assertRaises(MODULE.RoutineActionError):
                MODULE.parse_remote_sha256(malformed, MODULE.AP_REMOTE)
        with self.assertRaises(MODULE.RoutineActionError):
            MODULE.parse_available_bytes("bad")

    def test_artifact_binding_rejects_size_hash_and_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "artifact"
            path.write_bytes(b"abc")
            digest = MODULE.hashlib.sha256(b"abc").hexdigest()
            self.assertEqual(MODULE.require_artifact(root, Path("artifact"), 3, digest)["sha256"], digest)
            with self.assertRaises(MODULE.RoutineActionError):
                MODULE.require_artifact(root, Path("artifact"), 4, digest)
            with self.assertRaises(MODULE.RoutineActionError):
                MODULE.require_artifact(root, Path("artifact"), 3, "0" * 64)
            link = root / "link"
            link.symlink_to(path)
            with self.assertRaises(MODULE.RoutineActionError):
                MODULE.require_artifact(root, Path("link"), 3, digest)

    def test_bad_artifact_stops_before_any_device_command(self):
        calls: list[list[str]] = []
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(MODULE.RoutineActionError, "unavailable"):
                MODULE.run_action(
                    "install-magisk",
                    root=Path(temporary),
                    command=lambda argv, _timeout, _maximum: (
                        calls.append(argv) or (0, b"", b"")
                    ),
                )
        self.assertEqual(calls, [])

    def test_stage_hash_mismatch_closes_before_publish(self):
        calls: list[list[str]] = []

        def extra(argv):
            if "df" in argv:
                return 0, b"Filesystem 1K-blocks Used Available Use% Mounted on\n/data 100000000 1 50000000 1% /data\n", b""
            if "mkdir" in argv:
                return 0, b"", b""
            if "push" in argv:
                return 0, b"1 file pushed\n", b""
            if "sha256sum" in argv:
                return 0, f"{'0' * 64}  {argv[-1]}\n".encode(), b""
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.fake_artifact(root, MODULE.AP_REL, MODULE.AP_SIZE, MODULE.AP_SHA256):
                with self.assertRaisesRegex(MODULE.RoutineActionError, "staged AP SHA-256"):
                    MODULE.run_action(
                        "stage-ap",
                        root=root,
                        command=self.common_command(calls, extra),
                    )
        self.assertEqual(sum("push" in call for call in calls), 1)
        self.assertFalse(any("mv" in call for call in calls))

    def test_atomic_stage_directory_claim_failure_prevents_push(self):
        calls: list[list[str]] = []

        def extra(argv):
            if "df" in argv:
                return 0, b"Filesystem 1K-blocks Used Available Use% Mounted on\n/data 100000000 1 50000000 1% /data\n", b""
            if "mkdir" in argv:
                return 1, b"", b"already exists\n"
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.fake_artifact(root, MODULE.AP_REL, MODULE.AP_SIZE, MODULE.AP_SHA256):
                with self.assertRaisesRegex(MODULE.RoutineActionError, "claim failed"):
                    MODULE.run_action(
                        "stage-ap",
                        root=root,
                        command=self.common_command(calls, extra),
                    )
        self.assertEqual(sum("mkdir" in call for call in calls), 1)
        self.assertFalse(any("push" in call for call in calls))

    def test_private_intent_result_helpers_are_no_clobber(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = MODULE.allocate_run_dir(root, "install-magisk", None)
            intent = run_dir / "intent.json"
            MODULE.base.durable_write(intent, {"action": "install-magisk"})
            self.assertEqual(intent.stat().st_mode & 0o777, 0o400)
            with self.assertRaises(FileExistsError):
                MODULE.base.durable_write(intent, {"action": "again"})

    def test_retrieval_destination_rejects_parent_symlink_and_publish_race(self):
        basename = "magisk_patched-30700_AbC12.tar"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "private").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(MODULE.RoutineActionError, "tree is not exact"):
                MODULE.prepare_retrieval_destination(root, basename)
            self.assertEqual(list(outside.iterdir()), [])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partial, final = MODULE.prepare_retrieval_destination(root, basename)
            partial.write_bytes(b"candidate")
            final.write_bytes(b"racer")
            with self.assertRaisesRegex(MODULE.RoutineActionError, "clobber"):
                MODULE.publish_retrieved_artifact(partial, final)
            self.assertEqual(final.read_bytes(), b"racer")

    def test_failure_receipt_preserves_possible_effect_without_raw_error(self):
        recorder = MODULE.Recorder(lambda _argv, _timeout, _maximum: (0, b"", b""))
        recorder.run(
            ["adb", "-s", "PRIVATE", "push", "fixed", "fixed"],
            1,
            1,
            label="stage-ap-bytes",
            effect=True,
        )
        failure = MODULE.failure_result(
            "stage-ap", recorder, MODULE.RoutineActionError("PRIVATE failure")
        )
        encoded = json.dumps(failure, sort_keys=True)
        self.assertTrue(failure["possible_effect"])
        self.assertTrue(failure["possible_user_storage_stage"])
        self.assertFalse(failure["automatic_retry_permitted"])
        self.assertNotIn("PRIVATE", encoded)

    def test_active_guard_blocks_concurrency_and_effect_failure_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = MODULE.allocate_run_dir(root, "reboot-system", None)
            MODULE.acquire_guard(root, first, "reboot-system", None)
            second = MODULE.allocate_run_dir(root, "reboot-system", None)
            with self.assertRaisesRegex(MODULE.RoutineActionError, "unresolved"):
                MODULE.acquire_guard(root, second, "reboot-system", None)
            self.assertFalse(
                MODULE.close_guard_after_failure(
                    root,
                    run_dir=first,
                    action="reboot-system",
                    effect_command_count=1,
                )
            )
            self.assertTrue(MODULE.guard_path(root).is_file())
            with self.assertRaises(MODULE.RoutineActionError):
                MODULE.acquire_guard(root, second, "install-magisk", None)

    def test_effect_free_failure_and_setup_success_release_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            failed = MODULE.allocate_run_dir(root, "install-magisk", None)
            artifact = {
                "path": "/fixed",
                "size": MODULE.MAGISK_APK_SIZE,
                "sha256": MODULE.MAGISK_APK_SHA256,
            }
            MODULE.acquire_guard(root, failed, "install-magisk", artifact)
            self.assertTrue(
                MODULE.close_guard_after_failure(
                    root,
                    run_dir=failed,
                    action="install-magisk",
                    effect_command_count=0,
                )
            )
            self.assertFalse(MODULE.guard_path(root).exists())
            succeeded = MODULE.allocate_run_dir(root, "stage-ap", None)
            ap_artifact = {
                "path": "/fixed-ap",
                "size": MODULE.AP_SIZE,
                "sha256": MODULE.AP_SHA256,
            }
            MODULE.acquire_guard(root, succeeded, "stage-ap", ap_artifact)
            self.assertTrue(
                MODULE.close_guard_after_result(
                    root, run_dir=succeeded, action="stage-ap"
                )
            )
            self.assertFalse(MODULE.guard_path(root).exists())

    def test_control_dispatch_guard_requires_matching_durable_resolution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = MODULE.allocate_run_dir(root, "enter-download", None)
            MODULE.acquire_guard(root, run_dir, "enter-download", None)
            MODULE.base.durable_write(
                run_dir / "effect-01.json",
                {
                    "schema": "s20plus_g986n_routine_effect_intent_v1",
                    "version": MODULE.VERSION,
                    "action": "enter-download",
                    "label": "enter-download",
                    "ordinal": 1,
                },
            )
            MODULE.base.durable_write(
                run_dir / "result.json",
                {
                    "schema": "s20plus_g986n_routine_action_result_v1",
                    "version": MODULE.VERSION,
                    "action": "enter-download",
                    "verdict": MODULE.CONTROL_VERDICTS["enter-download"],
                    "effect_command_count": 1,
                    "verification": {
                        "terminal_health_pending": True,
                        "replay_permitted": False,
                    },
                },
            )
            self.assertFalse(
                MODULE.close_guard_after_result(
                    root, run_dir=run_dir, action="enter-download"
                )
            )
            with self.assertRaisesRegex(MODULE.RoutineActionError, "does not match"):
                MODULE.resolve_control(root, "recovery-observed")
            resolution = MODULE.resolve_control(root, "download-observed")
            self.assertTrue(resolution.is_file())
            self.assertFalse(MODULE.guard_path(root).exists())

    def test_control_resolution_rejects_forged_or_extra_effect_evidence(self):
        forged_effects = (
            {
                "schema": "wrong",
                "version": MODULE.VERSION,
                "action": "enter-download",
                "label": "enter-download",
                "ordinal": 1,
            },
            {
                "schema": "s20plus_g986n_routine_effect_intent_v1",
                "version": MODULE.VERSION,
                "action": "install-magisk",
                "label": "stage-ap",
                "ordinal": 99,
            },
        )
        for forged in forged_effects:
            with self.subTest(forged=forged), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_dir = MODULE.allocate_run_dir(root, "enter-download", None)
                MODULE.acquire_guard(root, run_dir, "enter-download", None)
                MODULE.base.durable_write(run_dir / "effect-01.json", forged)
                MODULE.base.durable_write(
                    run_dir / "result.json",
                    {
                        "schema": "s20plus_g986n_routine_action_result_v1",
                        "version": MODULE.VERSION,
                        "action": "enter-download",
                        "verdict": MODULE.CONTROL_VERDICTS["enter-download"],
                        "effect_command_count": 1,
                        "verification": {
                            "terminal_health_pending": True,
                            "replay_permitted": False,
                        },
                    },
                )
                with self.assertRaisesRegex(MODULE.RoutineActionError, "not exact"):
                    MODULE.resolve_control(root, "download-observed")
                self.assertTrue(MODULE.guard_path(root).is_file())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = MODULE.allocate_run_dir(root, "enter-download", None)
            MODULE.acquire_guard(root, run_dir, "enter-download", None)
            for ordinal in (1, 2):
                MODULE.base.durable_write(
                    run_dir / f"effect-{ordinal:02d}.json",
                    {
                        "schema": "s20plus_g986n_routine_effect_intent_v1",
                        "version": MODULE.VERSION,
                        "action": "enter-download",
                        "label": "enter-download",
                        "ordinal": ordinal,
                    },
                )
            MODULE.base.durable_write(
                run_dir / "result.json",
                {
                    "schema": "s20plus_g986n_routine_action_result_v1",
                    "version": MODULE.VERSION,
                    "action": "enter-download",
                    "verdict": MODULE.CONTROL_VERDICTS["enter-download"],
                    "effect_command_count": 1,
                    "verification": {
                        "terminal_health_pending": True,
                        "replay_permitted": False,
                    },
                },
            )
            with self.assertRaisesRegex(MODULE.RoutineActionError, "no durable"):
                MODULE.resolve_control(root, "download-observed")
            self.assertTrue(MODULE.guard_path(root).is_file())

    def test_source_excludes_partition_flash_and_arbitrary_command_surfaces(self):
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for forbidden in (
            "odin4",
            "fastboot",
            "/dev/block",
            "su -c",
            "setprop ",
            "settings put",
            "disable-verity",
            "reboot bootloader",
        ):
            self.assertNotIn(forbidden, source)

    def test_documents_bind_exactly_one_active_s20_routine_row_and_preserve_other_targets(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        tiers = (ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md").read_text(
            encoding="utf-8"
        )
        common = (ROOT / "docs/operations/ROUTINE_CONNECTED_ACTIONS.md").read_text(
            encoding="utf-8"
        )
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        report = (
            ROOT
            / "docs/reports/S20PLUS_G986N_ROUTINE_CONNECTED_ACTIONS_H0_2026-08-13.md"
        ).read_text(encoding="utf-8")
        retrieval_report = (
            ROOT
            / "docs/reports/S20PLUS_G986N_PATCHED_AP_RETRIEVAL_H0_2026-08-13.md"
        ).read_text(encoding="utf-8")
        goal = (ROOT / "GOAL_S20PLUS.md").read_text(encoding="utf-8")
        s22_contract = (
            ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        a90_contract = (
            ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Status: **BINDING - TARGET-CONTRACT ACTIVATION REQUIRED**", common)
        self.assertIn("Status: **BINDING - ROUTINE D1 SETUP/CONTROL ACTIVE**", contract)
        self.assertIn("Status: **BINDING - ROUTINE D0 PATCHED-AP RETRIEVAL ACTIVE**", contract)
        self.assertIn("PASS_GO - ROUTINE D1 ACTIVATED", report)
        self.assertIn("PASS_GO - ROUTINE D0 RETRIEVAL ACTIVATED", retrieval_report)
        self.assertIn(MODULE.sha256_file(SCRIPT), contract)
        self.assertIn("ROUTINE_CONNECTED_ACTIONS.md", agents)
        self.assertIn("ROUTINE_CONNECTED_ACTIONS.md", tiers)
        row = (
            "| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) "
            "| `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` "
            "| Active exact-target routine D0 reads, closed patched-AP D0 retrieval, and reviewed D1 setup/control; no F1 process |"
        )
        self.assertEqual(agents.count(row), 1)
        self.assertNotIn("s20plus_g986n_routine_actions.py", s22_contract)
        self.assertNotIn("s20plus_g986n_routine_actions.py", a90_contract)
        for text in (agents, tiers, common, contract):
            self.assertIn("partition", text.lower())
        self.assertIn("F1 and all partition actions\nremain undefined", contract)
        for text in (contract, retrieval_report, goal):
            self.assertNotIn("DRAFT - NOT ACTIVE", text)
            self.assertNotIn("H0 REVIEW PENDING", text)


if __name__ == "__main__":
    unittest.main()
