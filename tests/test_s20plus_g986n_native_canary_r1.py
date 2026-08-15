from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT_DATA = load(
    "s20plus_g986n_native_canary_r1_tested",
    SCRIPTS / "s20plus_g986n_native_canary_r1.py",
)
STOCK = load(
    "s20plus_g986n_native_canary_stock_recovery_r1_tested",
    SCRIPTS / "s20plus_g986n_native_canary_stock_recovery_r1.py",
)


class S20PlusNativeCanaryR1Tests(unittest.TestCase):
    def base_binding(self) -> dict:
        return {
            "target": {
                "model": ROOT_DATA.bootstrap.EXPECTED_MODEL,
                "device": ROOT_DATA.bootstrap.EXPECTED_DEVICE,
                "product": ROOT_DATA.bootstrap.EXPECTED_PRODUCT,
                "incremental": ROOT_DATA.bootstrap.EXPECTED_INCREMENTAL,
                "serial_sha256": "1" * 64,
                "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
                "boot_id_sha256": "2" * 64,
            },
            "device_binding_sha256": "3" * 64,
            "run_nonce": "4" * 32,
        }

    def prepared(self) -> dict:
        value = {
            "binding_sha256": "5" * 64,
            "binding": {
                **self.base_binding(),
                "closure": {
                    "bootstrap": {"adb": {"path": "/usr/bin/adb"}},
                    "stock_recovery_runner": {
                        "path": str(STOCK.SCRIPT),
                        "size": STOCK.SCRIPT.stat().st_size,
                        "sha256": hashlib.sha256(STOCK.SCRIPT.read_bytes()).hexdigest(),
                        "normalized_sha256": STOCK.normalized_self_sha256(),
                    },
                },
                "artifacts": {
                    "stock_boot": {
                        "path": str(ROOT_DATA.bootstrap.ROLLBACK),
                        "size": ROOT_DATA.bootstrap.ROLLBACK_SIZE,
                        "sha256": ROOT_DATA.bootstrap.ROLLBACK_SHA256,
                        "member": {},
                    }
                },
                "magisk": {"test": "exact"},
            },
        }
        value["approval_token"] = ROOT_DATA.APPROVAL_PREFIX + value["binding_sha256"]
        return value

    def valid_result(self, binding: dict | None = None) -> bytes:
        binding = binding or self.base_binding()
        value = {
            "schema": "s20plus_native_canary_n1_result_v1",
            "binding_sha256": binding["device_binding_sha256"],
            "run_nonce": binding["run_nonce"],
            "target_model": "SM-G986N",
            "target_device": "y2q",
            "target_product": "y2qksx",
            "target_incremental": "G986NKSS8IYC2",
            "pid": 123,
            "ppid": 1,
            "uid": 0,
            "gid": 0,
            "selinux_context": "u:r:magisk:s0",
            "cap_eff": "0000000000000000",
            "cap_prm": "0000000000000000",
            "cap_bnd": "000001ffffffffff",
            "no_new_privs": "0",
            "monotonic_sec": 10,
            "monotonic_nsec": 20,
            "self_sha256": ROOT_DATA.BINARY_SHA256,
            "self_size": ROOT_DATA.BINARY_SIZE,
            "boot_id_sha256": "6" * 64,
            "pre_boot_id_changed": True,
            "mnt_ns": "mnt:[1]",
            "pid_ns": "pid:[2]",
            "uts_ns": "uts:[3]",
            "net_ns": "net:[4]",
            "replay_permitted": False,
        }
        self.assertEqual(list(value), ROOT_DATA.RESULT_KEYS)
        return (json.dumps(value, separators=(",", ":")) + "\n").encode()

    def valid_intent(self, binding: dict | None = None) -> bytes:
        binding = binding or self.base_binding()
        return (
            '{"schema":"s20plus_native_canary_n1_intent_v1",'
            f'"binding_sha256":"{binding["device_binding_sha256"]}",'
            f'"run_nonce":"{binding["run_nonce"]}",'
            '"replay_permitted":false}\n'
        ).encode()

    def seed_recovery_journal(self, run: Path, prepared: dict) -> dict:
        (run / "events").mkdir()
        for name in ("device-binding.txt", "module-inventory.txt", "prepared.json"):
            (run / name).write_text("x")
        event = {
            "schema": "s20plus_g986n_f1_event_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "ordinal": 0,
            "name": "native-canary-prepared",
            "at": "now",
            "binding_sha256": prepared["binding_sha256"],
        }
        (run / "events/00-native-canary-prepared.json").write_text(json.dumps(event))
        stage_intent = {
            "schema": "s20plus_g986n_native_canary_r1_stage_intent_v1",
            "version": ROOT_DATA.VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "module_zip_sha256": ROOT_DATA.MODULE_ZIP_SHA256,
            "device_binding_sha256": prepared["binding"]["device_binding_sha256"],
            "stage_dir": ROOT_DATA.STAGE_DIR,
            "attempt": 1,
            "replay_permitted": False,
            "at": "now",
        }
        (run / "stage-intent.json").write_text(json.dumps(stage_intent))
        (run / "events/01-native-canary-stage-intent.json").write_text(json.dumps({
            "schema": "s20plus_g986n_f1_event_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "ordinal": 1,
            "name": "native-canary-stage-intent",
            "at": "now",
            "binding_sha256": prepared["binding_sha256"],
        }))
        self.write_command_result(
            run,
            "stage-claim",
            b"PASS_N1_STAGE_CLAIMED\n",
        )
        self.write_command_result(run, "stage-zip", b"")
        self.write_command_result(run, "stage-binding", b"")
        self.write_command_result(
            run,
            "stage-verify",
            b"PASS_N1_STAGE_EXACT\n",
        )
        intent = self.seed_install_intent_only(run, prepared)
        (run / "events/02-native-canary-install-intent.json").write_text(json.dumps({
            "schema": "s20plus_g986n_f1_event_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "ordinal": 2,
            "name": "native-canary-install-intent",
            "at": "now",
            "binding_sha256": prepared["binding_sha256"],
        }))
        return intent

    def seed_prepared_only(self, run: Path, prepared: dict) -> None:
        (run / "events").mkdir()
        for name in ("device-binding.txt", "module-inventory.txt", "prepared.json"):
            (run / name).write_text("x")
        event = {
            "schema": "s20plus_g986n_f1_event_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "ordinal": 0,
            "name": "native-canary-prepared",
            "at": "now",
            "binding_sha256": prepared["binding_sha256"],
        }
        (run / "events/00-native-canary-prepared.json").write_text(json.dumps(event))

    def seed_install_intent_only(self, run: Path, prepared: dict) -> dict:
        intent = {
            "schema": "s20plus_g986n_native_canary_r1_install_intent_v1",
            "version": ROOT_DATA.VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "module_zip_sha256": ROOT_DATA.MODULE_ZIP_SHA256,
            "module_id": ROOT_DATA.MODULE_ID,
            "stage_dir": ROOT_DATA.STAGE_DIR,
            "attempt": 1,
            "replay_permitted": False,
            "at": "now",
        }
        (run / "install-intent.json").write_text(json.dumps(intent))
        return intent


    def write_command_result(
        self,
        run: Path,
        label: str,
        stdout: bytes,
        stderr: bytes = b"",
        returncode: int = 0,
    ) -> None:
        (run / f"{label}.stdout").write_bytes(stdout)
        (run / f"{label}.stderr").write_bytes(stderr)
        (run / f"{label}-result.json").write_text(json.dumps({
            "schema": "s20plus_g986n_native_canary_r1_command_result_v1",
            "version": ROOT_DATA.VERSION,
            "label": label,
            "returncode": returncode,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
            "replay_permitted": False,
        }))

    def test_capability_is_active_but_cli_surface_remains_closed(self) -> None:
        self.assertTrue(ROOT_DATA.NATIVE_CANARY_R1_ACTIVE)
        self.assertTrue(STOCK.NATIVE_CANARY_STOCK_RECOVERY_ACTIVE)
        self.assertTrue(ROOT_DATA.render_plan()["live_authority"])
        self.assertTrue(STOCK.render_plan()["live_authority"])
        rejected = subprocess.run(
            [sys.executable, str(ROOT_DATA.SCRIPT), "--shell", "id"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(b"unrecognized arguments", rejected.stderr)
        safe_mode_rejected = subprocess.run(
            [sys.executable, str(ROOT_DATA.SCRIPT), "--arm-safe-mode"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(safe_mode_rejected.returncode, 0)
        self.assertIn(b"unrecognized arguments", safe_mode_rejected.stderr)
        self.assertFalse(hasattr(ROOT_DATA, "arm_safe_mode"))
        self.assertFalse(hasattr(ROOT_DATA, "finalize_safe_mode"))
        path_rejected = subprocess.run(
            [sys.executable, str(ROOT_DATA.SCRIPT), "--execute", "--run-dir", "/tmp/no"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(path_rejected.returncode, 0)
        self.assertIn(b"unrecognized arguments", path_rejected.stderr)
        for invalid in ("..", "../run-123456789012345678", "/tmp/run-123456789012345678", "run-x"):
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.resolve_run_id(invalid)

        with mock.patch.object(
            sys,
            "argv",
            [
                str(ROOT_DATA.SCRIPT),
                "--create-stock-handoff",
                "--run-id",
                "run-123456789012345678",
                "--confirmation",
                ROOT_DATA.STOCK_HANDOFF_CONFIRM,
                "--approval",
                "ignored-credential",
            ],
        ), mock.patch.object(ROOT_DATA, "require_active"), mock.patch.object(
            ROOT_DATA, "resolve_run_id", return_value=Path("/tmp/not-used")
        ), mock.patch.object(ROOT_DATA, "create_stock_handoff") as handoff:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                ROOT_DATA.main()
        handoff.assert_not_called()

    def test_prepare_cli_emits_exact_run_and_approval_binding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-prepare-cli-") as temp:
            run = Path(temp) / "run-123456789012345678"
            run.mkdir()
            binding = {"exact": "prepared-binding"}
            binding_sha = ROOT_DATA.canonical_sha(binding)
            prepared = {
                "schema": "s20plus_g986n_native_canary_r1_prepared_v1",
                "version": ROOT_DATA.VERSION,
                "binding": binding,
                "binding_sha256": binding_sha,
                "approval_token": ROOT_DATA.APPROVAL_PREFIX + binding_sha,
                "prepared_at": ROOT_DATA.utc_now(),
            }
            (run / "prepared.json").write_text(json.dumps(prepared))
            output = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [str(ROOT_DATA.SCRIPT), "--prepare"],
            ), mock.patch.object(ROOT_DATA, "require_active"), mock.patch.object(
                ROOT_DATA, "prepare", return_value=run
            ), contextlib.redirect_stdout(output):
                self.assertEqual(ROOT_DATA.main(), 0)
            self.assertEqual(json.loads(output.getvalue()), {
                "schema": "s20plus_g986n_native_canary_r1_prepare_output_v1",
                "run_id": run.name,
                "approval_token": ROOT_DATA.APPROVAL_PREFIX + binding_sha,
            })

    def test_prepare_output_cut_reemits_exact_binding_without_device_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-prepare-output-cut-") as temp:
            private = Path(temp)
            run_root = private / "runs"
            run_root.mkdir()
            run = run_root / "run-123456789012345678"
            run.mkdir()
            events = run / "events"
            events.mkdir()
            binding = {"exact": "prepared-binding"}
            binding_sha = ROOT_DATA.canonical_sha(binding)
            prepared = {
                "schema": "s20plus_g986n_native_canary_r1_prepared_v1",
                "version": ROOT_DATA.VERSION,
                "binding": binding,
                "binding_sha256": binding_sha,
                "approval_token": ROOT_DATA.APPROVAL_PREFIX + binding_sha,
                "prepared_at": ROOT_DATA.utc_now(),
            }
            (run / "device-binding.txt").write_bytes(b"binding")
            (run / "module-inventory.txt").write_bytes(b"active_count=0\nupdate_count=0\n")
            (run / "prepared.json").write_text(json.dumps(prepared))
            (events / "00-native-canary-prepared.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_event_v1",
                "version": ROOT_DATA.bootstrap.VERSION,
                "ordinal": 0,
                "name": "native-canary-prepared",
                "at": ROOT_DATA.utc_now(),
                "binding_sha256": binding_sha,
            }))
            guard = private / "active-action.json"
            guard.write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_guard_v1",
                "version": ROOT_DATA.VERSION,
                "run_dir": str(run),
                "unresolved": True,
            }))
            prepare = mock.Mock(side_effect=AssertionError("prepare must not replay"))
            output = io.StringIO()
            with mock.patch.object(sys, "argv", [str(ROOT_DATA.SCRIPT), "--prepare"]), \
                 mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "RUN_ROOT", run_root), \
                 mock.patch.object(ROOT_DATA, "guard_path", return_value=guard), \
                 mock.patch.object(ROOT_DATA, "prepare", prepare), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(ROOT_DATA.main(), 0)
            prepare.assert_not_called()
            self.assertEqual(json.loads(output.getvalue()), {
                "schema": "s20plus_g986n_native_canary_r1_prepare_output_v1",
                "run_id": run.name,
                "approval_token": ROOT_DATA.APPROVAL_PREFIX + binding_sha,
            })
            (run / "stage-intent.json").write_text("{}")
            with mock.patch.object(ROOT_DATA, "RUN_ROOT", run_root), \
                 mock.patch.object(ROOT_DATA, "guard_path", return_value=guard):
                with self.assertRaises(ROOT_DATA.RootDataError):
                    ROOT_DATA.resume_prepared_cli_output()

    def test_root_and_cleanup_surfaces_are_fixed_and_have_no_generic_input(self) -> None:
        self.assertEqual(
            ROOT_DATA.root_argv("/usr/bin/adb", "SERIAL", "FIXED"),
            ["/usr/bin/adb", "-s", "SERIAL", "shell", "su", "-c", "FIXED"],
        )
        install = ROOT_DATA.install_script("a" * 64)
        self.assertIn(
            f"{ROOT_DATA.MAGISK_BINARY} --install-module {ROOT_DATA.STAGE_ZIP}",
            install,
        )
        self.assertTrue(ROOT_DATA.STAGE_DIR.startswith("/data/local/tmp/"))
        self.assertIn(
            f"chmod 0750 {ROOT_DATA.UPDATE_MODULE_DIR}/bin/s20plus_native_canary",
            install,
        )
        self.assertNotIn("rm -rf", install)
        self.assertNotIn("eval", install)
        self.assertNotIn("/dev/block", install)
        disable = ROOT_DATA.disable_script("a" * 64, "b" * 32)
        self.assertNotIn("--install-module", disable)
        self.assertNotIn("magisk --remove-modules", disable)
        self.assertEqual(STOCK.render_plan()["candidate_path"], False)

    def test_preflight_parser_binds_inventory_and_rejects_dirty_namespace(self) -> None:
        clean = (
            b"active=absent\nupdate=absent\nparent=absent\nstate=absent\nstage=absent\n"
            b"active_count=0\nupdate_count=0\n"
        )
        value = ROOT_DATA.parse_preflight(clean)
        self.assertEqual(value["active_count"], 0)
        self.assertEqual(value["update_count"], 0)
        for bad in (
            clean.replace(b"state=absent", b"state=present"),
            clean.replace(b"active_count=0", b"active_count=1"),
            clean.replace(b"update_count=0", b"update_count=1"),
            clean + b"unexpected\n",
        ):
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.parse_preflight(bad)

    def test_canary_intent_and_result_are_strict_and_bound(self) -> None:
        prepared = {"binding": self.base_binding()}
        valid = self.valid_result()
        parsed = ROOT_DATA.validate_canary_files(self.valid_intent(), valid, prepared)
        self.assertEqual(parsed["uid"], 0)
        mutations = (
            valid.replace(b'"uid":0', b'"uid":true'),
            valid.replace(b'"cap_eff":"0000000000000000"', b'"cap_eff":1111111111111111'),
            valid.replace(b'"boot_id_sha256":"' + b"6" * 64 + b'"', b'"boot_id_sha256":' + b"6" * 64),
            valid.replace(b'"replay_permitted":false', b'"replay_permitted":true'),
            valid.replace(b'"SM-G986N"', b'"SM-G999N"'),
            valid.replace(b'"binding_sha256":"' + b"3" * 64, b'"binding_sha256":"' + b"7" * 64),
            valid.replace(b'"selinux_context":"u:r:magisk:s0"', b'"selinux_context":"u:r:init:s0"'),
            valid.replace(b'"monotonic_nsec":20', b'"monotonic_nsec":1000000000'),
            valid.replace(b',"binding_sha256"', b', \n "binding_sha256"'),
            valid.replace(b'"schema"', b'"sch\\u0065ma"', 1),
            valid.replace(b'"target_device":"y2q"', b'"target_device":"y2\\u0071"'),
            valid.replace(b'"pid":123', b'"pid":2147483648'),
            valid.replace(b'"ppid":1', b'"ppid":2147483648'),
            valid.replace(b'"monotonic_sec":10', b'"monotonic_sec":9223372036854775808'),
            valid.replace(b'"mnt_ns":"mnt:[1]"', b'"mnt_ns":"mnt:[18446744073709551616]"'),
            valid[:-2] + b',"extra":0}\n',
            valid + b"trailing",
        )
        for mutated in mutations:
            with self.subTest(mutated=mutated[-40:]), self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_canary_files(self.valid_intent(), mutated, prepared)
        with self.assertRaises(ROOT_DATA.RootDataError):
            ROOT_DATA.validate_canary_files(self.valid_intent().replace(b"false", b"true"), valid, prepared)
        parsed = ROOT_DATA.validate_canary_files(self.valid_intent(), valid, prepared)
        ROOT_DATA.require_canary_boot(parsed, "6" * 64, "first boot")
        with self.assertRaisesRegex(ROOT_DATA.RootDataError, "observed source boot"):
            ROOT_DATA.require_canary_boot(parsed, "7" * 64, "first boot")

    def test_install_result_is_durable_before_error_and_never_replayed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-command-") as temp:
            run = Path(temp)
            calls: list[list[str]] = []

            def failing(argv, _timeout, _maximum):
                calls.append(argv)
                raise TimeoutError("transport uncertain")

            with self.assertRaises(TimeoutError):
                ROOT_DATA.durable_command_result(
                    run, "install", ["adb", "fixed"], failing, 1, 32
                )
            result = json.loads((run / "install-result.json").read_text())
            self.assertEqual(result["effect_outcome"], "uncertain")
            self.assertFalse(result["replay_permitted"])
            self.assertEqual(len(calls), 1)
            with self.assertRaises(FileExistsError):
                ROOT_DATA.durable_command_result(
                    run, "install", ["adb", "fixed"], failing, 1, 32
                )

    def test_atomic_publication_never_exposes_partial_final_bytes(self) -> None:
        value = {"schema": "atomic-publication-test-v1", "attempt": 1}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-publish-") as temp:
            root = Path(temp)
            write_cut = root / "write-cut.json"
            real_write = os.write
            writes = 0

            def fail_after_partial(descriptor, payload):
                nonlocal writes
                writes += 1
                if writes == 1:
                    return real_write(descriptor, payload[:7])
                raise OSError("injected write cut")

            with mock.patch.object(ROOT_DATA.os, "write", side_effect=fail_after_partial):
                with self.assertRaisesRegex(OSError, "injected write cut"):
                    ROOT_DATA.durable_create(write_cut, value)
            self.assertFalse(os.path.lexists(write_cut))

            fsync_cut = root / "fsync-cut.json"
            with mock.patch.object(
                ROOT_DATA.os,
                "fsync",
                side_effect=OSError("injected file fsync cut"),
            ):
                with self.assertRaisesRegex(OSError, "injected file fsync cut"):
                    ROOT_DATA.durable_create(fsync_cut, value)
            self.assertFalse(os.path.lexists(fsync_cut))

            directory_fsync_cut = root / "directory-fsync-cut.json"
            real_fsync = os.fsync

            def fail_directory_fsync(descriptor):
                if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                    raise OSError("injected directory fsync cut")
                return real_fsync(descriptor)

            with mock.patch.object(
                ROOT_DATA.os,
                "fsync",
                side_effect=fail_directory_fsync,
            ):
                with self.assertRaisesRegex(OSError, "injected directory fsync cut"):
                    ROOT_DATA.durable_create(directory_fsync_cut, value)
            self.assertEqual(
                ROOT_DATA.read_exact_json(directory_fsync_cut, "directory-fsync cut"),
                value,
            )

            close_cut = root / "close-cut.json"
            real_close = os.close
            failed_close = False

            def fail_regular_close(descriptor):
                nonlocal failed_close
                is_regular = stat.S_ISREG(os.fstat(descriptor).st_mode)
                real_close(descriptor)
                if is_regular and not failed_close:
                    failed_close = True
                    raise OSError("injected close cut")

            with mock.patch.object(ROOT_DATA.os, "close", side_effect=fail_regular_close):
                with self.assertRaisesRegex(OSError, "injected close cut"):
                    ROOT_DATA.durable_create(close_cut, value)
            self.assertEqual(
                ROOT_DATA.read_exact_json(close_cut, "close cut"),
                value,
            )

            original = close_cut.read_bytes()
            with self.assertRaises(OSError):
                ROOT_DATA.durable_create(close_cut, {"schema": "replacement"})
            self.assertEqual(close_cut.read_bytes(), original)

    def test_r1_events_use_the_atomic_local_publisher(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-event-publish-") as temp:
            run = Path(temp)
            with mock.patch.object(ROOT_DATA.bootstrap, "event") as legacy_event:
                ROOT_DATA.event(run, 2, "install-intent", {"binding_sha256": "5" * 64})
            legacy_event.assert_not_called()
            value = ROOT_DATA.read_exact_json(
                run / "events/02-native-canary-install-intent.json",
                "atomic R1 event",
            )
            self.assertEqual(value["ordinal"], 2)
            self.assertEqual(value["name"], "native-canary-install-intent")

    def test_prepare_claims_guard_only_after_complete_prepared_journal(self) -> None:
        inventory = b"active_count=0\nupdate_count=0\n"
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        preflight = {
            "_module_inventory": inventory,
            "inventory_sha256": hashlib.sha256(inventory).hexdigest(),
            "root_observation_sha256": "3" * 64,
            "magisk_version": ROOT_DATA.MAGISK_VERSION,
            "magisk_version_code": ROOT_DATA.MAGISK_VERSION_CODE,
            "install_closure": {},
            "active_count": 0,
            "update_count": 0,
        }
        artifacts = {
            "binary": {"sha256": ROOT_DATA.BINARY_SHA256, "size": ROOT_DATA.BINARY_SIZE},
            "module_zip": {
                "sha256": ROOT_DATA.MODULE_ZIP_SHA256,
                "size": ROOT_DATA.MODULE_ZIP_SIZE,
            },
            "stock_boot": {"sha256": "4" * 64, "size": 1},
        }
        closure = {"bootstrap": {"adb": {"path": "/usr/bin/adb"}}}
        fake_builder = mock.Mock()
        fake_builder.render_binding.return_value = b"exact-device-binding\n"
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-prepare-cut-") as temp:
            private = Path(temp)
            run_root = private / "runs"
            guard = private / "active-action.json"
            real_publish = ROOT_DATA.durable_create

            def publish_then_interrupt(path, value):
                real_publish(path, value)
                if path == guard:
                    raise KeyboardInterrupt("injected post-guard crash")

            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "RUN_ROOT", run_root), \
                 mock.patch.object(ROOT_DATA, "guard_path", return_value=guard), \
                 mock.patch.object(ROOT_DATA, "load_candidate_builder", return_value=fake_builder), \
                 mock.patch.object(ROOT_DATA, "validate_artifacts", return_value=artifacts), \
                 mock.patch.object(ROOT_DATA, "closure_receipts", return_value=closure), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "root_preflight", return_value=preflight), \
                 mock.patch.object(ROOT_DATA, "durable_create", side_effect=publish_then_interrupt):
                with self.assertRaisesRegex(KeyboardInterrupt, "post-guard crash"):
                    ROOT_DATA.prepare()

            guard_value = ROOT_DATA.read_exact_json(guard, "post-prepare guard")
            run = Path(guard_value["run_dir"])
            prepared = ROOT_DATA.read_exact_json(run / "prepared.json", "post-prepare binding")
            self.assertEqual(
                ROOT_DATA.validate_pre_install_cut(run, prepared),
                set(ROOT_DATA.PREPARED_FILES),
            )

    def test_magisk_install_output_uses_a_closed_terminal_grammar(self) -> None:
        valid = (
            b"****************************\n S20+ Native Canary \n"
            b" by android-native-init-lab \n****************************\n"
            b"*******************\n Powered by Magisk \n*******************\n"
            b"- Extracting module files\n- Done\n"
            b"PASS_N1_INSTALL_EXACT\n"
        )
        self.assertEqual(
            ROOT_DATA.validate_install_output((0, valid, b"")),
            hashlib.sha256(valid).hexdigest(),
        )
        for result in (
            (1, valid, b""),
            (0, valid, b"warning"),
            (0, valid.replace(b"- Done", b"- Failed"), b""),
            (0, valid + b"trailing\n", b""),
        ):
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_install_output(result)

    def test_reboot_intent_precedes_dispatch_and_failure_is_not_replayed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-reboot-") as temp:
            run = Path(temp)
            prepared = self.prepared()
            selected = {"serial": "SERIAL"}
            identity = {
                "serial_sha256": "1" * 64,
                "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
                "boot_id_sha256": "2" * 64,
            }
            calls = 0

            def command(_argv, _timeout, _maximum):
                nonlocal calls
                calls += 1
                self.assertTrue((run / "first-reboot-intent.json").exists())
                return 1, b"", b"offline"

            with mock.patch.object(
                ROOT_DATA,
                "revalidate_reboot_source",
                return_value=(selected, identity),
            ), self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.dispatch_reboot(run, "first", prepared, selected, identity, command)
            self.assertEqual(calls, 1)
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.dispatch_reboot(run, "first", prepared, selected, identity, command)
            self.assertEqual(calls, 1)

    def test_reboot_source_drift_stops_before_intent_or_dispatch(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        source_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        changed_identity = dict(source_identity, boot_id_sha256="6" * 64)
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-reboot-source-") as temp:
            run = Path(temp)
            effect = mock.Mock()
            with mock.patch.object(
                ROOT_DATA.bootstrap,
                "android_health_once",
                return_value=(selected, {}, changed_identity),
            ), mock.patch.object(
                ROOT_DATA,
                "recovery_magisk_preflight",
            ) as helper_check:
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "source boot changed"):
                    ROOT_DATA.dispatch_reboot(
                        run,
                        "first",
                        prepared,
                        selected,
                        source_identity,
                        effect,
                    )
            helper_check.assert_not_called()
            effect.assert_not_called()
            self.assertFalse((run / "first-reboot-intent.json").exists())

        with tempfile.TemporaryDirectory(prefix="s20plus-r1-reboot-helper-") as temp:
            run = Path(temp)
            effect = mock.Mock()
            with mock.patch.object(
                ROOT_DATA.bootstrap,
                "android_health_once",
                return_value=(selected, {}, source_identity),
            ), mock.patch.object(
                ROOT_DATA,
                "recovery_magisk_preflight",
                side_effect=ROOT_DATA.RootDataError("helper closure changed"),
            ):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "helper closure"):
                    ROOT_DATA.dispatch_reboot(
                        run,
                        "first",
                        prepared,
                        selected,
                        source_identity,
                        effect,
                    )
            effect.assert_not_called()
            self.assertFalse((run / "first-reboot-intent.json").exists())

    def test_recovery_reboot_source_state_cannot_regress_before_intent(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "6" * 64,
        }
        calls: list[list[str]] = []

        def command(argv, _timeout, _maximum):
            calls.append(argv)
            self.assertNotEqual(argv[-1], "reboot")
            return 0, b"PASS_N1_RECOVERY_DISABLED_binding-only\n", b""

        with tempfile.TemporaryDirectory(prefix="s20plus-r1-recovery-regress-") as temp:
            run = Path(temp)
            with mock.patch.object(
                ROOT_DATA.bootstrap,
                "android_health_once",
                return_value=(selected, {}, identity),
            ), mock.patch.object(
                ROOT_DATA,
                "recovery_magisk_preflight",
            ), mock.patch.object(
                ROOT_DATA,
                "require_module_inventory",
            ):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "regressed"):
                    ROOT_DATA.dispatch_reboot(
                        run,
                        "recovery-disabled",
                        prepared,
                        selected,
                        identity,
                        command,
                        minimum_recovery_state="completed",
                    )
            self.assertEqual(len(calls), 1)
            self.assertFalse(
                (run / "recovery-disabled-reboot-intent.json").exists()
            )

    def test_reboot_source_rejects_live_canary_byte_drift_before_intent(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "6" * 64,
        }
        stable_intent = self.valid_intent()
        stable_result = self.valid_result()
        changed_value = json.loads(stable_result)
        changed_value["boot_id_sha256"] = "7" * 64
        changed_result = (
            json.dumps(changed_value, separators=(",", ":")) + "\n"
        ).encode()
        for phase, label, audit_output in (
            ("replay", "first", b"PASS_N1_ACTIVE_AUDIT\n"),
            (
                "recovery-disabled",
                "recovery",
                b"PASS_N1_RECOVERY_DISABLED_completed\n",
            ),
        ):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory(
                prefix=f"s20plus-r1-{phase}-bytes-"
            ) as temp:
                run = Path(temp)
                (run / f"{label}-intent.raw").write_bytes(stable_intent)
                (run / f"{label}-result.raw").write_bytes(stable_result)
                reads = iter((audit_output, stable_intent, changed_result))

                def command(argv, _timeout, _maximum):
                    self.assertNotEqual(argv[-1], "reboot")
                    return 0, next(reads), b""

                with mock.patch.object(
                    ROOT_DATA.bootstrap,
                    "android_health_once",
                    return_value=(selected, {}, identity),
                ), mock.patch.object(
                    ROOT_DATA,
                    "recovery_magisk_preflight",
                ), mock.patch.object(
                    ROOT_DATA,
                    "require_module_inventory",
                ):
                    with self.assertRaisesRegex(
                        ROOT_DATA.RootDataError,
                        "canary bytes changed",
                    ):
                        ROOT_DATA.dispatch_reboot(
                            run,
                            phase,
                            prepared,
                            selected,
                            identity,
                            command,
                            minimum_recovery_state=(
                                "completed"
                                if phase == "recovery-disabled"
                                else None
                            ),
                        )
                self.assertFalse((run / f"{phase}-reboot-intent.json").exists())

    def test_wrong_duplicate_or_offline_preflight_has_zero_persistent_effects(self) -> None:
        for hazard in ("wrong-target", "duplicate-target", "offline-target"):
            with self.subTest(hazard=hazard), tempfile.TemporaryDirectory(
                prefix="s20plus-r1-preflight-reject-"
            ) as temp:
                run = Path(temp)
                with mock.patch.object(ROOT_DATA, "require_active"), \
                     mock.patch.object(
                         ROOT_DATA, "read_prepared", return_value=self.prepared()
                     ), \
                     mock.patch.object(ROOT_DATA, "require_exact_nodes"), \
                     mock.patch.object(
                         ROOT_DATA.bootstrap,
                         "android_health_once",
                         side_effect=ROOT_DATA.bootstrap.BootstrapError(hazard),
                     ):
                    with self.assertRaises(ROOT_DATA.bootstrap.BootstrapError):
                        ROOT_DATA.execute(run, self.prepared()["approval_token"])
                self.assertFalse((run / "install-intent.json").exists())
                self.assertFalse(any("install" in path.name for path in run.iterdir()))

    def test_cleanup_rejects_extra_or_indirect_nodes_in_device_script(self) -> None:
        script = ROOT_DATA.cleanup_script("a" * 64)
        self.assertIn("-mindepth 1 -maxdepth 1", script)
        self.assertIn('[ "$unexpected" = "0" ]', script)
        self.assertIn(f'-le "{ROOT_DATA.MODULE_ZIP_SIZE}"', script)
        self.assertIn(f'-le "{ROOT_DATA.DEVICE_BINDING_SIZE}"', script)
        self.assertIn('stat -c %u:%g:%h', script)
        self.assertNotIn("rm -rf", script)
        self.assertNotIn("find " + ROOT_DATA.STAGE_DIR + " -delete", script)

    def test_cleanup_consumes_bounded_partial_push_without_replaying_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-partial-stage-") as temp:
            stage = Path(temp) / "stage"
            stage.mkdir()
            stage.chmod(0o700)
            staged_zip = stage / f"{ROOT_DATA.MODULE_ID}.zip"
            staged_binding = stage / "binding.txt"
            staged_zip.write_bytes(b"partial-zip")
            staged_binding.write_bytes(b"partial-binding")
            # ADB sync propagates owner permission bits to group/other before
            # the post-push chmod: canonical 0600 ZIP -> 0666, 0400 binding -> 0444.
            staged_zip.chmod(0o666)
            staged_binding.chmod(0o444)
            script = ROOT_DATA.cleanup_script("a" * 64)
            script = script.replace(ROOT_DATA.STAGE_DIR, str(stage))
            script = script.replace(
                '"2000:2000:1"',
                f'"{os.getuid()}:{os.getgid()}:1"',
            )
            script = script.replace(
                '"2000:2000"',
                f'"{os.getuid()}:{os.getgid()}"',
            )
            script = script.replace("/system/bin/toybox", "/usr/bin/busybox")
            completed = subprocess.run(
                ["/bin/sh", "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, b"PASS_N1_STAGE_CLEANUP\n")
            self.assertFalse(stage.exists())

    def test_stage_source_modes_are_bound_before_any_device_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stage-mode-") as temp:
            path = Path(temp) / "module.zip"
            path.write_bytes(b"fixed-module")
            path.chmod(0o600)
            expected = {
                "path": str(path.resolve(strict=True)),
                "size": len(b"fixed-module"),
                "sha256": hashlib.sha256(b"fixed-module").hexdigest(),
                "mode": "0600",
            }
            self.assertEqual(
                ROOT_DATA.require_receipt(path, expected, "test module ZIP"),
                expected,
            )
            path.chmod(0o644)
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "mode changed"):
                ROOT_DATA.require_receipt(path, expected, "test module ZIP")

    def test_device_binding_mode_drift_stops_before_stage_claim(self) -> None:
        prepared = self.prepared()
        prepared["binding"]["device_binding_sha256"] = hashlib.sha256(
            b"binding"
        ).hexdigest()
        selected = {"serial": "SERIAL"}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-binding-mode-") as temp:
            run = Path(temp)
            module_zip = run / "module.zip"
            module_zip.write_bytes(b"module")
            module_zip.chmod(0o600)
            prepared["binding"]["artifacts"]["module_zip"] = {
                "path": str(module_zip.resolve(strict=True)),
                "size": len(b"module"),
                "sha256": hashlib.sha256(b"module").hexdigest(),
                "mode": "0600",
            }
            binding = run / "device-binding.txt"
            binding.write_bytes(b"binding")
            binding.chmod(0o600)
            command = mock.Mock()
            with mock.patch.object(ROOT_DATA, "MODULE_ZIP", module_zip), \
                 mock.patch.object(ROOT_DATA, "DEVICE_BINDING_SIZE", len(b"binding")):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "mode changed"):
                    ROOT_DATA.stage_inputs(run, prepared, selected, command)
            command.assert_not_called()

    def test_module_zip_mode_drift_stops_before_stage_claim(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-zip-mode-") as temp:
            run = Path(temp)
            module_zip = run / "module.zip"
            module_zip.write_bytes(b"module")
            module_zip.chmod(0o644)
            binding = run / "device-binding.txt"
            binding.write_bytes(b"binding")
            binding.chmod(0o400)
            prepared["binding"]["device_binding_sha256"] = hashlib.sha256(
                b"binding"
            ).hexdigest()
            prepared["binding"]["artifacts"]["module_zip"] = {
                "path": str(module_zip.resolve(strict=True)),
                "size": len(b"module"),
                "sha256": hashlib.sha256(b"module").hexdigest(),
                "mode": "0600",
            }
            command = mock.Mock()
            with mock.patch.object(ROOT_DATA, "MODULE_ZIP", module_zip), \
                 mock.patch.object(ROOT_DATA, "DEVICE_BINDING_SIZE", len(b"binding")):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "mode changed"):
                    ROOT_DATA.stage_inputs(run, prepared, selected, command)
            command.assert_not_called()

    def test_stage_source_drift_after_push_stops_before_next_command(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stage-post-push-") as temp:
            run = Path(temp)
            module_zip = run / "module.zip"
            module_zip.write_bytes(b"module")
            module_zip.chmod(0o600)
            binding = run / "device-binding.txt"
            binding.write_bytes(b"binding")
            binding.chmod(0o400)
            prepared["binding"]["device_binding_sha256"] = hashlib.sha256(
                b"binding"
            ).hexdigest()
            prepared["binding"]["artifacts"]["module_zip"] = {
                "path": str(module_zip.resolve(strict=True)),
                "size": len(b"module"),
                "sha256": hashlib.sha256(b"module").hexdigest(),
                "mode": "0600",
            }
            labels: list[str] = []

            def command_result(_run, label, *_args):
                labels.append(label)
                if label == "stage-zip":
                    module_zip.chmod(0o644)
                return 0, b"PASS_N1_STAGE_CLAIMED\n" if label == "stage-claim" else b"", b""

            with mock.patch.object(ROOT_DATA, "MODULE_ZIP", module_zip), \
                 mock.patch.object(ROOT_DATA, "DEVICE_BINDING_SIZE", len(b"binding")), \
                 mock.patch.object(ROOT_DATA, "durable_command_result", side_effect=command_result):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "mode changed"):
                    ROOT_DATA.stage_inputs(run, prepared, selected, mock.Mock())
            self.assertEqual(labels, ["stage-claim", "stage-zip"])

    def test_post_stage_identity_or_helper_drift_stops_before_install_intent(self) -> None:
        prepared = self.prepared()
        expected_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        changed_identity = {**expected_identity, "boot_id_sha256": "8" * 64}
        for second_identity, preflight_error in (
            (changed_identity, None),
            (expected_identity, ROOT_DATA.RootDataError("post-stage helper drift")),
        ):
            with self.subTest(
                identity_changed=second_identity != expected_identity
            ), tempfile.TemporaryDirectory(prefix="s20plus-r1-post-stage-drift-") as temp:
                run = Path(temp)
                health = iter((expected_identity, second_identity))
                post_stage = mock.Mock(
                    side_effect=preflight_error
                ) if preflight_error is not None else mock.Mock()
                with mock.patch.object(ROOT_DATA, "require_active"), \
                     mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                     mock.patch.object(ROOT_DATA, "require_exact_nodes"), \
                     mock.patch.object(
                         ROOT_DATA.bootstrap,
                         "android_health_once",
                         side_effect=lambda *_args, **_kwargs: (
                             {"serial": "SERIAL"},
                             {},
                             next(health),
                         ),
                     ), \
                     mock.patch.object(
                         ROOT_DATA,
                         "root_preflight",
                         return_value={
                             **prepared["binding"]["magisk"],
                             "_module_inventory": b"active_count=0\nupdate_count=0\n",
                         },
                     ), \
                     mock.patch.object(ROOT_DATA, "stage_inputs"), \
                     mock.patch.object(ROOT_DATA, "post_stage_preflight", post_stage), \
                     mock.patch.object(ROOT_DATA, "durable_command_result") as install:
                    expected_message = (
                        "target changed between staging and install"
                        if second_identity != expected_identity
                        else "post-stage helper drift"
                    )
                    with self.assertRaisesRegex(ROOT_DATA.RootDataError, expected_message):
                        ROOT_DATA.execute(run, prepared["approval_token"], mock.Mock())
                self.assertTrue((run / "stage-intent.json").is_file())
                self.assertFalse((run / "install-intent.json").exists())
                install.assert_not_called()
                if second_identity != expected_identity:
                    post_stage.assert_not_called()
                else:
                    post_stage.assert_called_once()

    def test_install_uses_exclusive_shell_private_stage_not_shared_storage(self) -> None:
        script = ROOT_DATA.install_script("a" * 64)
        self.assertTrue(ROOT_DATA.STAGE_DIR.startswith("/data/local/tmp/"))
        self.assertNotIn("/sdcard/", ROOT_DATA.STAGE_DIR)
        self.assertIn(f"stat -c %u:%g:%h {ROOT_DATA.STAGE_ZIP}", script)
        self.assertIn(f"sha256sum {ROOT_DATA.STAGE_ZIP}", script)
        self.assertIn(
            f"{ROOT_DATA.MAGISK_BINARY} --install-module {ROOT_DATA.STAGE_ZIP}",
            script,
        )
        self.assertLess(
            script.index(f"sha256sum {ROOT_DATA.STAGE_ZIP}"),
            script.index(f"--install-module {ROOT_DATA.STAGE_ZIP}"),
        )

    def test_stage_absence_requires_accessible_private_stage_parent(self) -> None:
        command = mock.Mock(return_value=(1, b"", b""))
        with self.assertRaisesRegex(ROOT_DATA.RootDataError, "absence is not exact"):
            ROOT_DATA.stage_absence_evidence(
                command,
                "/usr/bin/adb",
                {"serial": "SERIAL"},
            )
        argv = command.call_args.args[0]
        self.assertEqual(argv[3:6], ["exec-out", "sh", "-c"])
        self.assertIn(f"df -k {ROOT_DATA.STAGE_PARENT}", argv[-1])
        self.assertNotIn("su", argv)

    def test_recovery_state_scripts_cover_never_ran_intent_only_and_completed(self) -> None:
        binding = "a" * 64
        nonce = "b" * 32
        recovery = ROOT_DATA.recovery_disable_script(binding, nonce)
        audit = ROOT_DATA.recovery_disabled_audit_script(binding, nonce)
        for state_class, count in (
            ("binding-only", "1"),
            ("intent-only", "2"),
            ("completed", "3"),
        ):
            self.assertIn(f'{count})', recovery)
            self.assertIn(f"state_class={state_class}", recovery)
            self.assertIn(f"state_class={state_class}", audit)
        self.assertIn('= "644" ]', audit)
        self.assertEqual(
            ROOT_DATA.decode_recovery_state(
                (0, b"PASS_N1_RECOVERY_DISABLE_binding-only\n", b""),
                "recovery",
                ROOT_DATA.RECOVERY_STATE_OUTPUTS,
            ),
            "binding-only",
        )

    def test_exact_module_tree_and_zero_baseline_inventory_are_closed(self) -> None:
        self.assertIn("[ ! -e /data/adb/modules_update ]", ROOT_DATA.PREFLIGHT_SCRIPT)
        self.assertIn("active_count=%s", ROOT_DATA.PREFLIGHT_SCRIPT)
        self.assertIn("update_count=0", ROOT_DATA.PREFLIGHT_SCRIPT)
        self.assertIn("active_count=%s", ROOT_DATA.INVENTORY_SCRIPT)
        self.assertIn("update_count=0", ROOT_DATA.INVENTORY_SCRIPT)
        for script in (
            ROOT_DATA.POST_INSTALL_TESTS,
            ROOT_DATA.ACTIVE_MODULE_TREE_TESTS,
            ROOT_DATA.DISABLED_MODULE_TREE_TESTS,
        ):
            self.assertIn("stat -c %u:%g", script)
            self.assertIn('= "755" ]', script)
        self.assertIn(ROOT_DATA.EMPTY_SHA256, ROOT_DATA.DISABLED_MODULE_TREE_TESTS)
        self.assertIn(
            ROOT_DATA._dir_test("/data/adb/modules_update", "777"),
            ROOT_DATA.POST_INSTALL_TESTS,
        )
        self.assertIn(
            ROOT_DATA._dir_test(ROOT_DATA.ACTIVE_MODULE_DIR, "777"),
            ROOT_DATA.POST_INSTALL_TESTS,
        )

    def test_recovery_input_scope_does_not_depend_on_candidate_build_artifacts(self) -> None:
        prepared = self.prepared()
        root_receipt = {"path": "/reviewed/root.py", "size": 1, "sha256": "a" * 64, "normalized_sha256": "b" * 64}
        bootstrap_receipts = {"runner": {"sha256": "c" * 64}, "adb": {"sha256": "d" * 64}}
        prepared["binding"]["closure"] = {
            "root_data_runner": root_receipt,
            "stock_recovery_runner": prepared["binding"]["closure"]["stock_recovery_runner"],
            "bootstrap": bootstrap_receipts,
            "builder": {"missing_after_install": True},
            "canary_source": {"missing_after_install": True},
        }
        with mock.patch.object(ROOT_DATA, "self_receipt", return_value=root_receipt), \
             mock.patch.object(ROOT_DATA.bootstrap, "closure_receipts", return_value=bootstrap_receipts), \
             mock.patch.object(ROOT_DATA, "validate_artifacts") as candidate_artifacts, \
             mock.patch.object(ROOT_DATA, "validate_stock_artifact") as stock_artifact:
            ROOT_DATA.validate_recovery_inputs(prepared, "root-recovery")
        candidate_artifacts.assert_not_called()
        stock_artifact.assert_not_called()

    def test_stock_finalize_scope_does_not_reopen_the_transferred_stock_ap(self) -> None:
        prepared = self.prepared()
        root_receipt = {
            "path": "/reviewed/root.py", "size": 1,
            "sha256": "a" * 64, "normalized_sha256": "b" * 64,
        }
        stock_runner = prepared["binding"]["closure"]["stock_recovery_runner"]
        bootstrap_receipts = {"runner": {"sha256": "c" * 64}, "adb": {"sha256": "d" * 64}}
        prepared["binding"]["closure"] = {
            "root_data_runner": root_receipt,
            "stock_recovery_runner": stock_runner,
            "bootstrap": bootstrap_receipts,
            "builder": {"not_needed": True},
            "canary_source": {"not_needed": True},
        }
        prepared["binding"]["artifacts"] = {
            "module_zip": {"not_needed": True},
            "binary": {"not_needed": True},
            "stock_boot": prepared["binding"]["artifacts"]["stock_boot"],
        }
        with mock.patch.object(ROOT_DATA, "self_receipt", return_value=root_receipt), \
             mock.patch.object(ROOT_DATA, "recovery_runner_receipt", return_value=stock_runner), \
             mock.patch.object(ROOT_DATA.bootstrap, "closure_receipts", return_value=bootstrap_receipts), \
             mock.patch.object(ROOT_DATA, "validate_stock_artifact") as stock_artifact:
            ROOT_DATA.validate_recovery_inputs(prepared, "stock-finalize")
        stock_artifact.assert_not_called()

    def test_root_terminal_release_ignores_unused_stock_owner_and_device_tools(self) -> None:
        prepared = self.prepared()
        root_receipt = {
            "path": "/reviewed/root.py",
            "size": 1,
            "sha256": "a" * 64,
            "normalized_sha256": "b" * 64,
        }
        bootstrap_runner = {
            "path": "/reviewed/bootstrap.py",
            "size": 2,
            "sha256": "c" * 64,
            "normalized_sha256": "d" * 64,
        }
        prepared["binding"]["closure"] = {
            "root_data_runner": root_receipt,
            "stock_recovery_runner": {"unused_and_missing": True},
            "bootstrap": {
                "runner": bootstrap_runner,
                "adb": {"unused_and_changed": True},
            },
            "builder": {"unused_and_missing": True},
            "canary_source": {"unused_and_missing": True},
        }
        with mock.patch.object(ROOT_DATA, "self_receipt", return_value=root_receipt), \
             mock.patch.object(
                 ROOT_DATA,
                 "bootstrap_runner_receipt",
                 return_value=bootstrap_runner,
             ), \
             mock.patch.object(
                 ROOT_DATA,
                 "recovery_runner_receipt",
                 side_effect=AssertionError("unused stock owner must not be opened"),
             ), \
             mock.patch.object(
                 ROOT_DATA.bootstrap,
                 "closure_receipts",
                 side_effect=AssertionError("unused ADB closure must not be opened"),
             ):
            ROOT_DATA.validate_recovery_inputs(prepared, "root-terminal-release")

    def test_terminal_release_revalidates_real_bootstrap_parser_receipt(self) -> None:
        prepared = self.prepared()
        bootstrap_runner = ROOT_DATA.bootstrap_runner_receipt()
        prepared["binding"]["closure"] = {
            "root_data_runner": {"kind": "root"},
            "stock_recovery_runner": {"kind": "unused-stock"},
            "bootstrap": {"runner": bootstrap_runner},
            "builder": {"kind": "unused-builder"},
            "canary_source": {"kind": "unused-source"},
        }
        with mock.patch.object(
            ROOT_DATA,
            "self_receipt",
            return_value={"kind": "root"},
        ):
            ROOT_DATA.validate_recovery_inputs(
                prepared,
                "root-terminal-release",
            )

    def test_stock_terminal_release_revalidates_only_its_transfer_classifier(self) -> None:
        prepared = self.prepared()
        root_receipt = {"kind": "root"}
        stock_runner = {"kind": "stock"}
        bootstrap_runner = {"kind": "bootstrap"}
        f1_core = {"kind": "f1-core"}
        prepared["binding"]["closure"] = {
            "root_data_runner": root_receipt,
            "stock_recovery_runner": stock_runner,
            "bootstrap": {
                "runner": bootstrap_runner,
                "f1_core": f1_core,
                "adb": {"unused_and_missing": True},
            },
            "builder": {"unused_and_missing": True},
            "canary_source": {"unused_and_missing": True},
        }
        with mock.patch.object(ROOT_DATA, "self_receipt", return_value=root_receipt), \
             mock.patch.object(
                 ROOT_DATA,
                 "recovery_runner_receipt",
                 return_value=stock_runner,
             ), \
             mock.patch.object(
                 ROOT_DATA,
                 "bootstrap_runner_receipt",
                 return_value=bootstrap_runner,
             ), \
             mock.patch.object(
                 ROOT_DATA,
                 "bootstrap_f1_core_receipt",
                 return_value=f1_core,
             ), \
             mock.patch.object(
                 ROOT_DATA.bootstrap,
                 "closure_receipts",
                 side_effect=AssertionError("unused device closure must not be opened"),
             ):
            ROOT_DATA.validate_recovery_inputs(
                prepared,
                "stock-terminal-release",
            )

        with mock.patch.object(ROOT_DATA, "self_receipt", return_value=root_receipt), \
             mock.patch.object(
                 ROOT_DATA,
                 "recovery_runner_receipt",
                 return_value=stock_runner,
             ), \
             mock.patch.object(
                 ROOT_DATA,
                 "bootstrap_runner_receipt",
                 return_value=bootstrap_runner,
             ), \
             mock.patch.object(
                 ROOT_DATA,
                 "bootstrap_f1_core_receipt",
                 return_value={"kind": "changed-classifier"},
             ):
            with self.assertRaisesRegex(
                ROOT_DATA.RootDataError,
                "terminal-release parser closure changed",
            ):
                ROOT_DATA.validate_recovery_inputs(
                    prepared,
                    "stock-terminal-release",
                )

    def test_recovery_entrypoints_start_without_candidate_builder_source(self) -> None:
        probe = r'''
import builtins
import runpy
import sys

path = sys.argv[1]
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == "build_s20plus_g986n_native_canary_n1":
        raise ModuleNotFoundError("candidate builder intentionally absent")
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
sys.argv = [path, "--help"]
try:
    runpy.run_path(path, run_name="__main__")
except SystemExit as exc:
    raise SystemExit(exc.code)
'''
        environment = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(SCRIPTS),
        }
        for script in (ROOT_DATA.SCRIPT, STOCK.SCRIPT):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, "-c", probe, str(script)],
                    cwd=ROOT,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b"candidate builder", result.stderr)

    def test_pre_install_cut_has_cleanup_only_terminal_and_no_root_data_effect(self) -> None:
        prepared = self.prepared()
        same_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-pre-install-abort-") as temp:
            run = Path(temp)
            terminal = mock.Mock(return_value={"verdict": "ABORTED"})
            cleanup = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(
                     ROOT_DATA, "read_prepared", return_value=prepared
                 ) as read_prepared, \
                 mock.patch.object(ROOT_DATA, "validate_pre_install_cut"), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, same_identity),
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "root_observation",
                     return_value={"root_verified": True, "attempts": 1, "output_sha256": "e" * 64},
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "root_preflight",
                     return_value={**prepared["binding"]["magisk"], "_module_inventory": b""},
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input"), \
                 mock.patch.object(ROOT_DATA, "cleanup_stage", cleanup), \
                 mock.patch.object(
                     ROOT_DATA,
                     "stage_absence_evidence",
                     return_value={
                         "returncode": 0,
                         "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
                         "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                         "staged_input_absent": True,
                     },
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal", terminal):
                result = ROOT_DATA.abort_pre_install(run)
            self.assertEqual(result["verdict"], "ABORTED")
            cleanup.assert_not_called()
            self.assertFalse((run / "install-intent.json").exists())
            self.assertFalse((run / "recovery-disable-intent.json").exists())
            self.assertFalse(any("reboot" in path.name for path in run.iterdir()))
            self.assertEqual(terminal.call_args.kwargs["install_intent_count"], 0)
            self.assertFalse(terminal.call_args.kwargs["require_boot_change"])

    def test_pre_install_changed_boot_closes_only_after_exact_stage_cleanup(self) -> None:
        prepared = self.prepared()
        changed_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        staged_absence = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-preinstall-changed-boot-") as temp:
            run = Path(temp)
            (run / "stage-intent.json").write_text("{}")
            cleanup = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(ROOT_DATA, "validate_pre_install_cut"), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, changed_identity),
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "root_observation",
                     return_value={
                         "root_verified": True,
                         "attempts": 1,
                         "output_sha256": "e" * 64,
                     },
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input"), \
                 mock.patch.object(ROOT_DATA, "settle_cleanup_without_replay", cleanup), \
                 mock.patch.object(
                     ROOT_DATA,
                     "stage_absence_evidence",
                     return_value=staged_absence,
                 ), \
                 mock.patch.object(ROOT_DATA, "confirm_rooted_terminal_state"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "write_terminal",
                     return_value={"verdict": "ABORTED"},
                 ) as terminal:
                result = ROOT_DATA.abort_pre_install(run, mock.Mock())
            self.assertEqual(result["verdict"], "ABORTED")
            cleanup.assert_called_once()
            self.assertFalse((run / "install-intent.json").exists())
            self.assertTrue(terminal.call_args.kwargs["require_boot_change"])
            self.assertEqual(terminal.call_args.kwargs["install_intent_count"], 0)

    def test_pre_install_journal_rejects_any_install_boundary(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-pre-install-state-") as temp:
            run = Path(temp)
            self.seed_recovery_journal(run, prepared)
            (run / "install-intent.json").unlink()
            (run / "events/02-native-canary-install-intent.json").unlink()
            seen = ROOT_DATA.validate_pre_install_cut(run, prepared)
            self.assertIn("stage-intent.json", seen)
            self.assertNotIn("install-intent.json", seen)
            self.seed_install_intent_only(run, prepared)
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "after install intent"):
                ROOT_DATA.validate_pre_install_cut(run, prepared)

    def test_prepared_only_decline_is_an_exact_pre_install_cut(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-prepared-decline-") as temp:
            run = Path(temp)
            self.seed_prepared_only(run, prepared)
            self.assertEqual(ROOT_DATA.validate_pre_install_cut(run, prepared), ROOT_DATA.PREPARED_FILES)
            (run / "terminal-input.json").write_text("{}")
            (run / "terminal-result.json").write_text("{}")
            self.assertEqual(
                ROOT_DATA.validate_pre_install_cut(run, prepared),
                ROOT_DATA.PREPARED_FILES | {
                    "terminal-input.json", "terminal-result.json"
                },
            )
            (run / "unexpected").write_text("x")
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "missing, extra, or indirect"):
                ROOT_DATA.validate_pre_install_cut(run, prepared)

    def test_strict_host_json_rejects_duplicate_authority_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-duplicate-json-") as temp:
            path = Path(temp) / "intent.json"
            path.write_text('{"attempt":1,"attempt":2,"replay_permitted":false}')
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "duplicate key"):
                ROOT_DATA.read_exact_json(path, "duplicate intent")

    def test_host_journal_rejects_bool_integer_authority_substitution(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-typed-authority-") as temp:
            run = Path(temp) / "run"
            run.mkdir()
            guard = Path(temp) / "guard.json"
            guard_value = ROOT_DATA.guard_value(run)
            guard_value["unresolved"] = 1
            guard.write_text(json.dumps(guard_value))
            with mock.patch.object(ROOT_DATA, "guard_path", return_value=guard):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "does not match"):
                    ROOT_DATA.read_guard(run)

            stage = {
                "schema": "s20plus_g986n_native_canary_r1_stage_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "module_zip_sha256": ROOT_DATA.MODULE_ZIP_SHA256,
                "device_binding_sha256": prepared["binding"]["device_binding_sha256"],
                "stage_dir": ROOT_DATA.STAGE_DIR,
                "attempt": 1,
                "replay_permitted": 0,
                "at": "now",
            }
            (run / "stage-intent.json").write_text(json.dumps(stage))
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "stage intent"):
                ROOT_DATA.validate_stage_intent(run, prepared)

    def test_unobserved_recovery_intent_binds_canary_boot_to_disable_source(self) -> None:
        prepared = self.prepared()
        source_identity = {
            "serial_sha256": prepared["binding"]["target"]["serial_sha256"],
            "topology_sha256": prepared["binding"]["target"]["topology_sha256"],
            "boot_id_sha256": "8" * 64,
        }
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-unobserved-source-") as temp:
            run = Path(temp)
            path = run / "recovery-disable-intent.json"
            value = {
                "schema": "s20plus_g986n_native_canary_r1_recovery_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "source_identity": source_identity,
                "root_observation": root,
                "source_state_class": "completed",
                "source_canary_result_sha256": "a" * 64,
                "source_canary_boot_id_sha256": "7" * 64,
                "source_boot_observed": False,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(
                ROOT_DATA.RootDataError,
                "not the disable source boot",
            ):
                ROOT_DATA.validate_optional_effect_intents(run, prepared)

            value["source_canary_boot_id_sha256"] = source_identity[
                "boot_id_sha256"
            ]
            path.write_text(json.dumps(value))
            (run / "first-observation.json").write_text(json.dumps({
                "android_identity": {"boot_id_sha256": "6" * 64},
            }))
            with self.assertRaisesRegex(
                ROOT_DATA.RootDataError,
                "root observation is malformed",
            ):
                ROOT_DATA.validate_optional_effect_intents(run, prepared)

    def test_observed_recovery_source_requires_the_exact_first_canary_bytes(self) -> None:
        prepared = self.prepared()
        source_identity = {
            "serial_sha256": prepared["binding"]["target"]["serial_sha256"],
            "topology_sha256": prepared["binding"]["target"]["topology_sha256"],
            "boot_id_sha256": "7" * 64,
        }
        first_result = self.valid_result()
        changed = json.loads(first_result)
        changed["monotonic_nsec"] += 1
        changed_result = (
            json.dumps(changed, separators=(",", ":")) + "\n"
        ).encode()
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-observed-source-bytes-") as temp:
            run = Path(temp)
            (run / "first-observation.json").write_text(json.dumps({
                "android_identity": {
                    **source_identity,
                    "boot_id_sha256": "6" * 64,
                },
            }))
            for label, result in (("first", first_result), ("recovery", changed_result)):
                (run / f"{label}-intent.raw").write_bytes(self.valid_intent())
                (run / f"{label}-result.raw").write_bytes(result)
            (run / "recovery-disable-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_recovery_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "source_identity": source_identity,
                "root_observation": root,
                "source_state_class": "completed",
                "source_canary_result_sha256": hashlib.sha256(changed_result).hexdigest(),
                "source_canary_boot_id_sha256": "6" * 64,
                "source_boot_observed": True,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }))
            with self.assertRaisesRegex(
                ROOT_DATA.RootDataError,
                "differs from the first canary evidence",
            ):
                ROOT_DATA.validate_optional_effect_intents(run, prepared)

    def test_normal_disable_source_must_equal_the_replay_observation(self) -> None:
        prepared = self.prepared()
        replay_identity = {
            "serial_sha256": prepared["binding"]["target"]["serial_sha256"],
            "topology_sha256": prepared["binding"]["target"]["topology_sha256"],
            "boot_id_sha256": "7" * 64,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-disable-source-") as temp:
            run = Path(temp)
            (run / "replay-observation.json").write_text(json.dumps({
                "android_identity": replay_identity,
            }))
            (run / "disable-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "module_id": ROOT_DATA.MODULE_ID,
                "source_identity": {**replay_identity, "boot_id_sha256": "8" * 64},
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }))
            with self.assertRaisesRegex(
                ROOT_DATA.RootDataError,
                "not the replay observation",
            ):
                ROOT_DATA.validate_optional_effect_intents(run, prepared)


    def test_partial_command_receipts_are_consumed_only_for_recovery(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-partial-command-") as temp:
            run = Path(temp)
            (run / "install.stdout").write_bytes(b"partial")
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "incomplete"):
                ROOT_DATA.validate_command_evidence(run, "install")
            uncertain = ROOT_DATA.validate_command_evidence(
                run,
                "install",
                allow_uncertain_consumed=True,
            )
            self.assertEqual(
                uncertain["schema"],
                "s20plus_g986n_native_canary_r1_command_uncertain_consumed_v1",
            )
            self.assertFalse(uncertain["replay_permitted"])

            (run / "install.stdout").unlink()
            (run / "install.stderr").write_bytes(b"impossible")
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "publication order"):
                ROOT_DATA.validate_command_evidence(
                    run,
                    "install",
                    allow_uncertain_consumed=True,
                )

            (run / "install.stderr").unlink()
            stdout = b"published"
            (run / "install.stdout").write_bytes(stdout)
            (run / "install-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_command_result_v1",
                "version": ROOT_DATA.VERSION,
                "label": "install",
                "returncode": 0,
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                "stdout_bytes": len(stdout),
                "stderr_bytes": 0,
                "replay_permitted": False,
            }))
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "reachable publication cut"):
                ROOT_DATA.validate_command_evidence(
                    run,
                    "install",
                    allow_uncertain_consumed=True,
                )

            (run / "install-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_command_failure_v1",
                "version": ROOT_DATA.VERSION,
                "label": "install",
                "failure_class": "OSError",
                "effect_outcome": "uncertain",
                "replay_permitted": False,
            }))
            uncertain = ROOT_DATA.validate_command_evidence(
                run,
                "install",
                allow_uncertain_consumed=True,
            )
            self.assertEqual(uncertain["present"], ["result", "stdout"])

    def test_partial_canary_read_is_recovery_only_and_never_forged_complete(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-partial-canary-read-") as temp:
            run = Path(temp)
            self.seed_recovery_journal(run, prepared)
            (run / "recovery-intent.raw").write_bytes(self.valid_intent())
            seen = ROOT_DATA.validate_recovery_journal(
                run,
                prepared,
                allow_uncertain_commands=True,
            )
            self.assertIn("recovery-intent.raw", seen)
            self.assertFalse((run / "recovery-result.raw").exists())
            (run / "recovery-intent.raw").unlink()
            (run / "recovery-result.raw").write_bytes(self.valid_result())
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "incomplete"):
                ROOT_DATA.validate_recovery_journal(
                    run,
                    prepared,
                    allow_uncertain_commands=True,
                )

    def test_partial_canary_pair_reads_only_the_missing_result_without_replay(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        valid_intent = self.valid_intent()
        valid_result = self.valid_result()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-canary-pair-resume-") as temp:
            run = Path(temp)
            (run / "recovery-intent.raw").write_bytes(valid_intent)
            reads: list[str] = []

            def read_missing(argv, _timeout, _maximum):
                reads.append(argv[-1])
                self.assertEqual(argv[-1], ROOT_DATA.CAT_RESULT_SCRIPT)
                return 0, valid_result, b""

            intent, result, parsed = ROOT_DATA.read_or_collect_state_files(
                run,
                "recovery",
                prepared,
                selected,
                read_missing,
            )
            self.assertEqual((intent, result), (valid_intent, valid_result))
            self.assertEqual(parsed["target_model"], ROOT_DATA.bootstrap.EXPECTED_MODEL)
            self.assertEqual(reads, [ROOT_DATA.CAT_RESULT_SCRIPT])

            forbidden = mock.Mock(side_effect=AssertionError("read replay forbidden"))
            self.assertEqual(
                ROOT_DATA.read_or_collect_state_files(
                    run,
                    "recovery",
                    prepared,
                    selected,
                    forbidden,
                )[:2],
                (valid_intent, valid_result),
            )
            forbidden.assert_not_called()

            (run / "recovery-intent.raw").unlink()
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "no preceding intent"):
                ROOT_DATA.read_or_collect_state_files(
                    run,
                    "recovery",
                    prepared,
                    selected,
                    forbidden,
                )
            forbidden.assert_not_called()

    def test_partial_readonly_audit_uses_one_atomic_zero_effect_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-readonly-audit-resume-") as temp:
            run = Path(temp)
            (run / "disabled-audit.stdout").write_bytes(b"partial")
            command = mock.Mock(
                return_value=(0, b"PASS_N1_DISABLED_AUDIT\n", b"")
            )
            receipt = ROOT_DATA.complete_readonly_command(
                run,
                "disabled-audit",
                ["fixed-read-only-audit"],
                command,
                30,
                ROOT_DATA.MAX_OUTPUT,
            )
            self.assertEqual(receipt, (0, b"PASS_N1_DISABLED_AUDIT\n", b""))
            command.assert_called_once()
            snapshot = ROOT_DATA.read_exact_json(
                run / "disabled-audit-resume.json",
                "test read-only audit resume",
            )
            self.assertEqual(snapshot["source_evidence"], ["stdout"])
            self.assertEqual(snapshot["device_effect_count"], 0)
            forbidden = mock.Mock(side_effect=AssertionError("audit replay forbidden"))
            self.assertEqual(
                ROOT_DATA.complete_readonly_command(
                    run,
                    "disabled-audit",
                    ["fixed-read-only-audit"],
                    forbidden,
                    30,
                    ROOT_DATA.MAX_OUTPUT,
                ),
                receipt,
            )
            forbidden.assert_not_called()

            (run / "disabled-audit.stderr").write_bytes(b"")
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "read-only resume evidence"):
                ROOT_DATA.completed_readonly_command(run, "disabled-audit")

    def test_full_raw_failure_receipt_can_resume_only_as_a_readonly_audit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-readonly-full-failure-") as temp:
            run = Path(temp)
            (run / "disabled-audit.stdout").write_bytes(b"prior stdout")
            (run / "disabled-audit.stderr").write_bytes(b"")
            (run / "disabled-audit-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_command_failure_v1",
                "version": ROOT_DATA.VERSION,
                "label": "disabled-audit",
                "failure_class": "OSError",
                "effect_outcome": "uncertain",
                "replay_permitted": False,
            }))
            command = mock.Mock(
                return_value=(0, b"PASS_N1_DISABLED_AUDIT\n", b"")
            )
            expected = (0, b"PASS_N1_DISABLED_AUDIT\n", b"")
            self.assertEqual(
                ROOT_DATA.complete_readonly_command(
                    run,
                    "disabled-audit",
                    ["fixed-read-only-audit"],
                    command,
                    30,
                    ROOT_DATA.MAX_OUTPUT,
                ),
                expected,
            )
            command.assert_called_once()
            resume = ROOT_DATA.read_exact_json(
                run / "disabled-audit-resume.json",
                "test full-failure read-only resume",
            )
            self.assertEqual(
                resume["source_evidence"],
                ["result", "stderr", "stdout"],
            )
            self.assertEqual(resume["device_effect_count"], 0)
            self.assertEqual(
                ROOT_DATA.completed_readonly_command(run, "disabled-audit"),
                expected,
            )

    def test_reboot_chain_requires_each_prior_durable_boot(self) -> None:
        prepared = self.prepared()
        first = {"prior_boot_id_sha256": "2" * 64}
        first_observation = {"android_identity": {"boot_id_sha256": "6" * 64}}
        replay = {"prior_boot_id_sha256": "6" * 64}
        replay_observation = {"android_identity": {"boot_id_sha256": "7" * 64}}
        disabled = {"prior_boot_id_sha256": "7" * 64}
        disabled_observation = {"android_identity": {"boot_id_sha256": "8" * 64}}
        ROOT_DATA.validate_normal_reboot_chain(
            prepared,
            first,
            first_observation,
            replay,
            replay_observation,
            disabled,
            disabled_observation,
        )
        replay["prior_boot_id_sha256"] = "8" * 64
        with self.assertRaisesRegex(ROOT_DATA.RootDataError, "not contiguous"):
            ROOT_DATA.validate_normal_reboot_chain(
                prepared,
                first,
                first_observation,
                replay,
                replay_observation,
                disabled,
                disabled_observation,
            )
        replay["prior_boot_id_sha256"] = "6" * 64
        replay_observation["android_identity"]["boot_id_sha256"] = "2" * 64
        disabled["prior_boot_id_sha256"] = "2" * 64
        with self.assertRaisesRegex(ROOT_DATA.RootDataError, "reuses"):
            ROOT_DATA.validate_normal_reboot_chain(
                prepared,
                first,
                first_observation,
                replay,
                replay_observation,
                disabled,
                disabled_observation,
            )
        replay_observation["android_identity"]["boot_id_sha256"] = "7" * 64
        disabled["prior_boot_id_sha256"] = "7" * 64
        disabled_observation["android_identity"]["boot_id_sha256"] = "6" * 64
        with self.assertRaisesRegex(ROOT_DATA.RootDataError, "reuses"):
            ROOT_DATA.validate_normal_reboot_chain(
                prepared,
                first,
                first_observation,
                replay,
                replay_observation,
                disabled,
                disabled_observation,
            )
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-recovery-chain-") as temp:
            run = Path(temp)
            recovery_intent = {
                "source_identity": {"boot_id_sha256": "6" * 64},
            }
            recovery_reboot = {"prior_boot_id_sha256": "7" * 64}
            recovery_observation = {
                "android_identity": {"boot_id_sha256": "8" * 64},
            }
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "not contiguous"):
                ROOT_DATA.validate_recovery_reboot_chain(
                    run,
                    prepared,
                    recovery_intent,
                    recovery_reboot,
                    recovery_observation,
                )
            recovery_reboot["prior_boot_id_sha256"] = "6" * 64
            recovery_observation["android_identity"]["boot_id_sha256"] = "2" * 64
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "reuses"):
                ROOT_DATA.validate_recovery_reboot_chain(
                    run,
                    prepared,
                    recovery_intent,
                    recovery_reboot,
                    recovery_observation,
                )
            (run / "first-observation.json").write_text(json.dumps({
                "android_identity": {"boot_id_sha256": "7" * 64},
            }))
            recovery_observation["android_identity"]["boot_id_sha256"] = "7" * 64
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "reuses"):
                ROOT_DATA.validate_recovery_reboot_chain(
                    run,
                    prepared,
                    recovery_intent,
                    recovery_reboot,
                    recovery_observation,
                )

    def test_consumed_reboot_rejects_any_earlier_boot_id_reuse(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        source_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "7" * 64,
        }
        returned_identity = dict(source_identity, boot_id_sha256="6" * 64)
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-reboot-reuse-") as temp:
            run = Path(temp)
            for phase, boot_id in (("first", "6" * 64), ("replay", "7" * 64)):
                (run / f"{phase}-observation.json").write_text(json.dumps({
                    "android_identity": {"boot_id_sha256": boot_id},
                }))
            (run / "disabled-reboot-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_reboot_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "phase": "disabled",
                "prior_boot_id_sha256": source_identity["boot_id_sha256"],
                "attempt": 1,
                "replay_permitted": False,
                "at": "2026-08-15T00:00:00Z",
            }))
            root_probe = mock.Mock()
            with mock.patch.object(ROOT_DATA, "validate_reboot_evidence"), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=(selected, {}, returned_identity),
                 ), \
                 mock.patch.object(ROOT_DATA.bootstrap, "root_observation", root_probe):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "earlier boot"):
                    ROOT_DATA.resume_reboot_observation(
                        run,
                        "disabled",
                        prepared,
                        mock.Mock(),
                    )
            root_probe.assert_not_called()
            self.assertFalse((run / "disabled-observation.json").exists())

    def test_terminal_guard_release_resume_uses_no_device_command(self) -> None:
        prepared = self.prepared()
        terminal_input = {
            "target_identity": {
                "serial_sha256": "1" * 64,
                "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
                "boot_id_sha256": "9" * 64,
            }
        }
        derived = {
            "verdict": "PASS",
            "identity": terminal_input["target_identity"],
            "result_sha256": "a" * 64,
            "recovery": "normal",
            "state_class": "completed",
            "install_intent_count": 1,
            "require_boot_change": True,
        }
        staged = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-terminal-release-") as temp:
            run = Path(temp)
            (run / "terminal-input.json").write_text("{}")
            (run / "terminal-result.json").write_text("{}")
            device = mock.Mock(side_effect=AssertionError("device command forbidden"))
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(
                     ROOT_DATA, "read_prepared", return_value=prepared
                 ) as read_prepared, \
                 mock.patch.object(ROOT_DATA, "read_terminal_input", return_value=terminal_input), \
                 mock.patch.object(ROOT_DATA, "derived_terminal_fields", return_value=derived), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_exact_json",
                     return_value={"staged_input_absence_evidence": staged},
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal", return_value={"verdict": "PASS"}) as publish:
                result = ROOT_DATA.finalize_terminal(run, device)
            self.assertEqual(result["verdict"], "PASS")
            device.assert_not_called()
            publish.assert_called_once()
            read_prepared.assert_called_once_with(
                run,
                input_scope="root-terminal-release",
                allow_released_terminal=True,
            )

    def test_terminal_finalizer_rejects_foreign_target_before_root_probe(self) -> None:
        prepared = self.prepared()
        foreign_identity = {
            "serial_sha256": "f" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "9" * 64,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-terminal-foreign-") as temp:
            run = Path(temp)
            device = mock.Mock(side_effect=AssertionError("device command forbidden"))
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "FOREIGN"}, {}, foreign_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight") as root_probe, \
                 mock.patch.object(ROOT_DATA, "derived_terminal_fields") as derive:
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "prepared returned target"):
                    ROOT_DATA.finalize_terminal(run, device)
            device.assert_not_called()
            root_probe.assert_not_called()
            derive.assert_not_called()

    def test_existing_terminal_rejects_bool_for_integer_command_count(self) -> None:
        prepared = self.prepared()
        identity = {
            key: prepared["binding"]["target"][key]
            for key in ("serial_sha256", "topology_sha256", "boot_id_sha256")
        }
        staged = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-terminal-typed-") as temp:
            run = Path(temp)
            guard = run / "active-guard.json"
            ROOT_DATA.durable_create(guard, ROOT_DATA.guard_value(run))
            terminal_input = ROOT_DATA.terminal_input_value(
                prepared,
                "ABORTED_S20PLUS_G986N_NATIVE_CANARY_N1_BEFORE_INSTALL_HEALTHY",
                identity,
                None,
                "pre-install-abort",
                "absent",
                0,
                False,
                "now",
            )
            (run / "terminal-input.json").write_text(json.dumps(terminal_input))
            with mock.patch.object(ROOT_DATA, "guard_path", return_value=guard), \
                 mock.patch.object(ROOT_DATA, "release_guard"):
                ROOT_DATA.write_terminal(
                    run,
                    prepared,
                    terminal_input["verdict"],
                    identity,
                    None,
                    recovery="pre-install-abort",
                    canary_state_class="absent",
                    staged_input_absence=staged,
                    install_intent_count=0,
                    require_boot_change=False,
                )
                path = run / "terminal-result.json"
                forged = json.loads(path.read_text())
                forged["other_target_command_count"] = False
                path.unlink()
                path.write_text(json.dumps(forged))
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "existing terminal"):
                    ROOT_DATA.write_terminal(
                        run,
                        prepared,
                        terminal_input["verdict"],
                        identity,
                        None,
                        recovery="pre-install-abort",
                        canary_state_class="absent",
                        staged_input_absence=staged,
                        install_intent_count=0,
                        require_boot_change=False,
                    )

    def test_post_cleanup_identity_drift_blocks_terminal_state_proof(self) -> None:
        prepared = self.prepared()
        expected = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        changed = {**expected, "boot_id_sha256": "9" * 64}
        root_probe = mock.Mock()
        with mock.patch.object(
            ROOT_DATA.bootstrap,
            "android_health_once",
            return_value=({"serial": "SERIAL"}, {}, changed),
        ), mock.patch.object(ROOT_DATA.bootstrap, "root_observation", root_probe):
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "after staged-input cleanup"):
                ROOT_DATA.confirm_rooted_terminal_state(
                    Path("/tmp/not-used"),
                    prepared,
                    mock.Mock(),
                    expected,
                    "normal",
                    "completed",
                )
        root_probe.assert_not_called()

    def test_terminal_publish_then_guard_release_cut_resumes_without_rewriting(self) -> None:
        prepared = self.prepared()
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "9" * 64,
        }
        staged = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-terminal-cut-") as temp:
            run = Path(temp) / "run"
            run.mkdir()
            guard = Path(temp) / "active-guard.json"
            ROOT_DATA.bootstrap.durable_create(guard, ROOT_DATA.guard_value(run))
            ROOT_DATA.write_terminal_input(
                run,
                prepared,
                "PASS_TEST",
                identity,
                "a" * 64,
                recovery="normal",
                canary_state_class="completed",
            )
            arguments = dict(
                recovery="normal",
                canary_state_class="completed",
                staged_input_absence=staged,
            )
            with mock.patch.object(ROOT_DATA, "guard_path", return_value=guard), \
                 mock.patch.object(ROOT_DATA, "release_guard", side_effect=OSError("cut")):
                with self.assertRaisesRegex(OSError, "cut"):
                    ROOT_DATA.write_terminal(
                        run, prepared, "PASS_TEST", identity, "a" * 64, **arguments
                    )
            terminal = run / "terminal-result.json"
            first_bytes = terminal.read_bytes()
            self.assertTrue(guard.exists())
            with mock.patch.object(ROOT_DATA, "guard_path", return_value=guard):
                result = ROOT_DATA.write_terminal(
                    run, prepared, "PASS_TEST", identity, "a" * 64, **arguments
                )
            self.assertEqual(result["verdict"], "PASS_TEST")
            self.assertEqual(terminal.read_bytes(), first_bytes)
            self.assertFalse(guard.exists())
            with mock.patch.object(ROOT_DATA, "guard_path", return_value=guard), \
                 mock.patch.object(
                     ROOT_DATA,
                     "release_guard",
                     side_effect=AssertionError("released terminal must not release twice"),
                 ):
                released_result = ROOT_DATA.write_terminal(
                    run, prepared, "PASS_TEST", identity, "a" * 64, **arguments
                )
            self.assertEqual(released_result, result)
            self.assertEqual(terminal.read_bytes(), first_bytes)
            ROOT_DATA.durable_create(
                guard,
                ROOT_DATA.guard_value(run / "foreign-run"),
            )
            with mock.patch.object(ROOT_DATA, "guard_path", return_value=guard), \
                 mock.patch.object(ROOT_DATA, "validate_run_dir"):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "does not match"):
                    ROOT_DATA.read_prepared(
                        run,
                        input_scope="root-terminal-release",
                        allow_released_terminal=True,
                    )

    def test_terminal_finalizer_never_replays_partial_cleanup_intent(self) -> None:
        prepared = self.prepared()
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        derived = {
            "verdict": "ABORTED_TEST",
            "identity": identity,
            "result_sha256": None,
            "recovery": "pre-install-abort",
            "state_class": "absent",
            "install_intent_count": 0,
            "require_boot_change": False,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-cleanup-cut-") as temp:
            run = Path(temp)
            (run / "stage-intent.json").write_text("{}")
            ROOT_DATA.bootstrap.durable_create(run / "cleanup-intent.json", {
                "schema": "s20plus_g986n_native_canary_r1_cleanup_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "stage_dir": ROOT_DATA.STAGE_DIR,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            })
            (run / "cleanup.stdout").write_bytes(b"partial")
            ROOT_DATA.write_terminal_input(
                run,
                prepared,
                derived["verdict"],
                identity,
                None,
                recovery="pre-install-abort",
                canary_state_class="absent",
                install_intent_count=0,
                require_boot_change=False,
            )
            calls: list[list[str]] = []

            def read_only(argv, _timeout, _maximum):
                calls.append(argv)
                self.assertIn("PASS_N1_STAGE_ABSENT", argv[-1])
                return 0, b"PASS_N1_STAGE_ABSENT\n", b""

            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, identity),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "recovery_magisk_preflight",
                     return_value={"root_verified": True, "attempts": 1, "output_sha256": "e" * 64},
                 ), \
                 mock.patch.object(ROOT_DATA, "derived_terminal_fields", return_value=derived), \
                 mock.patch.object(
                     ROOT_DATA,
                     "root_preflight",
                     return_value={**prepared["binding"]["magisk"], "_module_inventory": b""},
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal", return_value={"verdict": "ABORTED_TEST"}):
                result = ROOT_DATA.finalize_terminal(run, read_only)
            self.assertEqual(result["verdict"], "ABORTED_TEST")
            self.assertEqual(len(calls), 1)

    def test_terminal_finalizer_rejects_complete_cleanup_semantic_failure(self) -> None:
        prepared = self.prepared()
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        derived = {
            "verdict": "ABORTED_TEST",
            "identity": identity,
            "result_sha256": None,
            "recovery": "pre-install-abort",
            "state_class": "absent",
            "install_intent_count": 0,
            "require_boot_change": False,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-cleanup-semantic-") as temp:
            run = Path(temp)
            (run / "stage-intent.json").write_text("{}")
            ROOT_DATA.bootstrap.durable_create(run / "cleanup-intent.json", {
                "schema": "s20plus_g986n_native_canary_r1_cleanup_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "stage_dir": ROOT_DATA.STAGE_DIR,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            })
            self.write_command_result(run, "cleanup", b"UNEXPECTED\n")
            ROOT_DATA.write_terminal_input(
                run,
                prepared,
                derived["verdict"],
                identity,
                None,
                recovery="pre-install-abort",
                canary_state_class="absent",
                install_intent_count=0,
                require_boot_change=False,
            )
            device = mock.Mock(side_effect=AssertionError("device command forbidden"))
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, identity),
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "root_observation",
                     return_value={"root_verified": True, "attempts": 1, "output_sha256": "e" * 64},
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight"), \
                 mock.patch.object(ROOT_DATA, "derived_terminal_fields", return_value=derived), \
                 mock.patch.object(ROOT_DATA, "validate_optional_effect_intents"), \
                 mock.patch.object(ROOT_DATA, "stage_absence_evidence") as absence, \
                 mock.patch.object(ROOT_DATA, "write_terminal") as terminal:
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "unexpected output"):
                    ROOT_DATA.finalize_terminal(run, device)
            device.assert_not_called()
            absence.assert_not_called()
            terminal.assert_not_called()

    def test_magisk_install_closure_binds_live_regular_bytes_without_claiming_provenance(self) -> None:
        payload = (
            b"magisk|755|0|0|1|1000|" + b"1" * 64 + b"\n"
            b"busybox|755|0|0|1|2000|" + b"2" * 64 + b"\n"
            b"util_functions|644|0|0|1|3000|" + b"3" * 64 + b"\n"
        )
        parsed = ROOT_DATA.parse_magisk_install_closure(payload)
        self.assertEqual(parsed["magisk"]["path"], ROOT_DATA.MAGISK_BINARY)
        self.assertEqual(ROOT_DATA.validate_magisk_install_closure(parsed), parsed)
        for field in ("uid", "gid", "nlink"):
            forged = json.loads(json.dumps(parsed))
            forged["magisk"][field] = field == "nlink"
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_magisk_install_closure(forged)
        for malformed in (
            payload.replace(b"magisk|755", b"magisk|777"),
            payload.replace(b"|0|0|1|1000|", b"|0|0|2|1000|", 1),
            payload + b"extra|600|0|0|1|1|" + b"4" * 64 + b"\n",
        ):
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.parse_magisk_install_closure(malformed)

    def test_magisk_install_closure_failure_is_finitely_classified_before_followup(self) -> None:
        payload = (
            b"magisk|755|0|0|1|1000|" + b"1" * 64 + b"\n"
            b"busybox|755|0|0|1|2000|" + b"2" * 64 + b"\n"
            b"util_functions|error|absent\n"
        )
        with self.assertRaisesRegex(
            ROOT_DATA.RootDataError,
            "install closure incompatible: util_functions=absent",
        ):
            ROOT_DATA.parse_magisk_install_closure(payload)
        unsafe = payload.replace(b"magisk|755", b"magisk|777").replace(
            b"util_functions|error|absent",
            b"util_functions|644|0|0|1|3000|" + b"3" * 64,
        )
        with self.assertRaisesRegex(
            ROOT_DATA.RootDataError,
            "install closure incompatible: magisk=unsafe-metadata",
        ):
            ROOT_DATA.parse_magisk_install_closure(unsafe)
        for malformed in (
            payload.replace(b"absent", b"caller-controlled"),
            payload.replace(b"util_functions|error", b"busybox|error"),
        ):
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "malformed"):
                ROOT_DATA.parse_magisk_install_closure(malformed)

        commands = []

        def classified(argv, _timeout, _maximum):
            commands.append(argv[-1])
            if argv[-1] == ROOT_DATA.MAGISK_CLOSURE_SCRIPT:
                return 0, payload, b""
            raise AssertionError("no command may follow a classified closure failure")

        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        with mock.patch.object(
            ROOT_DATA.bootstrap,
            "root_observation",
            return_value={"root_verified": True, "attempts": 1, "output_sha256": "3" * 64},
        ):
            with self.assertRaisesRegex(
                ROOT_DATA.RootDataError,
                "install closure incompatible: util_functions=absent",
            ):
                ROOT_DATA.root_preflight(
                    classified,
                    "/usr/bin/adb",
                    {"serial": "SERIAL"},
                    identity,
                )
        self.assertEqual(commands, [ROOT_DATA.MAGISK_CLOSURE_SCRIPT])
        commands.clear()
        with mock.patch.object(
            ROOT_DATA.bootstrap,
            "root_observation",
            return_value={"root_verified": True, "attempts": 1, "output_sha256": "3" * 64},
        ):
            with self.assertRaisesRegex(
                ROOT_DATA.RootDataError,
                "install closure incompatible: util_functions=absent",
            ):
                ROOT_DATA.recovery_magisk_preflight(
                    classified,
                    "/usr/bin/adb",
                    {"serial": "SERIAL"},
                    identity,
                    self.prepared(),
                )
        self.assertEqual(commands, [ROOT_DATA.MAGISK_CLOSURE_SCRIPT])
        self.assertIn("probe util_functions " + ROOT_DATA.MAGISK_UTIL_FUNCTIONS, ROOT_DATA.MAGISK_CLOSURE_SCRIPT)
        self.assertIn("2>/dev/null", ROOT_DATA.MAGISK_CLOSURE_SCRIPT)

    def test_magisk_closure_shell_classifier_covers_fixed_labels_and_tokens(self) -> None:
        labels = ("magisk", "busybox", "util_functions")
        read_failures = {
            "mode-read-failed": "%a",
            "uid-read-failed": "%u",
            "gid-read-failed": "%g",
            "nlink-read-failed": "%h",
            "size-read-failed": "%s",
            "hash-read-failed": "sha256sum",
        }

        def execute_case(states: dict[str, str]) -> tuple[int, bytes, bytes]:
            with tempfile.TemporaryDirectory(prefix="s20plus-r1-closure-shell-") as temp:
                root = Path(temp)
                paths = {
                    "magisk": root / "magisk",
                    "busybox": root / "busybox",
                    "util_functions": root / "util_functions.sh",
                }
                modes = {"magisk": 0o755, "busybox": 0o755, "util_functions": 0o644}
                for label, path in paths.items():
                    state = states.get(label, "ok")
                    if state == "absent":
                        continue
                    if state == "symlink":
                        path.symlink_to(root / "missing-target")
                    elif state == "not-regular":
                        path.mkdir()
                    else:
                        path.write_bytes((label + "-exact-bytes").encode("ascii"))
                        path.chmod(modes[label])
                toybox = root / "toybox"
                toybox.write_text(
                    "#!/usr/bin/env python3\n"
                    "import hashlib, os, stat, sys\n"
                    "command = sys.argv[1]\n"
                    "path = sys.argv[-1]\n"
                    "label = {'util_functions.sh': 'util_functions'}.get(os.path.basename(path), os.path.basename(path))\n"
                    "failure = os.environ.get('N1_TEST_FAILURE', '')\n"
                    "if failure.startswith(label + '='):\n"
                    "    wanted = failure.split('=', 1)[1]\n"
                    "    if (command == 'sha256sum' and wanted == 'sha256sum') or (command == 'stat' and sys.argv[3] == wanted):\n"
                    "        print('N1_TEST_STDOUT_SENTINEL')\n"
                    "        print('N1_TEST_STDERR_SENTINEL', file=sys.stderr)\n"
                    "        sys.exit(19)\n"
                    "if command == 'sha256sum':\n"
                    "    data = open(path, 'rb').read()\n"
                    "    print(hashlib.sha256(data).hexdigest() + '  ' + path)\n"
                    "elif command == 'stat':\n"
                    "    metadata = os.stat(path)\n"
                    "    values = {'%a': format(stat.S_IMODE(metadata.st_mode), 'o'), '%u': '0', '%g': '0', '%h': str(metadata.st_nlink), '%s': str(metadata.st_size)}\n"
                    "    print(values[sys.argv[3]])\n"
                    "else:\n"
                    "    sys.exit(17)\n"
                )
                toybox.chmod(0o700)
                script = ROOT_DATA.MAGISK_CLOSURE_SCRIPT.replace(
                    ROOT_DATA.MAGISK_UTIL_FUNCTIONS,
                    str(paths["util_functions"]),
                ).replace(
                    ROOT_DATA.MAGISK_BUSYBOX,
                    str(paths["busybox"]),
                ).replace(
                    ROOT_DATA.MAGISK_BINARY,
                    str(paths["magisk"]),
                ).replace(
                    "/system/bin/toybox",
                    str(toybox),
                )
                environment = dict(os.environ)
                environment.pop("N1_TEST_FAILURE", None)
                for label, state in states.items():
                    if state in read_failures:
                        environment["N1_TEST_FAILURE"] = f"{label}={read_failures[state]}"
                completed = subprocess.run(
                    ["/bin/sh", "-c", script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=environment,
                    check=False,
                )
                return completed.returncode, completed.stdout, completed.stderr

        success = execute_case({})
        self.assertEqual(success[0], 0)
        self.assertEqual(success[2], b"")
        self.assertEqual(tuple(ROOT_DATA.parse_magisk_install_closure(success[1])), labels)

        tokens = ("symlink", "absent", "not-regular", *read_failures)
        self.assertEqual(set(tokens), set(ROOT_DATA.MAGISK_CLOSURE_ERROR_TOKENS))
        for label in labels:
            for token in tokens:
                rc, stdout, stderr = execute_case({label: token})
                self.assertEqual(rc, 0, (label, token))
                self.assertEqual(stderr, b"", (label, token))
                lines = stdout.decode("ascii").splitlines()
                self.assertEqual([line.split("|", 1)[0] for line in lines], list(labels))
                self.assertEqual(lines[labels.index(label)], f"{label}|error|{token}")
                with self.assertRaisesRegex(
                    ROOT_DATA.RootDataError,
                    f"install closure incompatible: {label}={token}",
                ):
                    ROOT_DATA.parse_magisk_install_closure(stdout)

        rc, stdout, stderr = execute_case({
            "magisk": "absent",
            "busybox": "symlink",
            "util_functions": "nlink-read-failed",
        })
        self.assertEqual((rc, stderr), (0, b""))
        self.assertEqual(stdout, (
            b"magisk|error|absent\n"
            b"busybox|error|symlink\n"
            b"util_functions|error|nlink-read-failed\n"
        ))
        with self.assertRaisesRegex(
            ROOT_DATA.RootDataError,
            "magisk=absent,busybox=symlink,util_functions=nlink-read-failed",
        ):
            ROOT_DATA.parse_magisk_install_closure(stdout)

    def test_recovery_helper_drift_blocks_disable_before_effect_intent(self) -> None:
        prepared = self.prepared()
        expected_payload = (
            b"magisk|755|0|0|1|1000|" + b"1" * 64 + b"\n"
            b"busybox|755|0|0|1|2000|" + b"2" * 64 + b"\n"
            b"util_functions|644|0|0|1|3000|" + b"3" * 64 + b"\n"
        )
        prepared["binding"]["magisk"] = {
            "magisk_version": ROOT_DATA.MAGISK_VERSION,
            "magisk_version_code": ROOT_DATA.MAGISK_VERSION_CODE,
            "install_closure": ROOT_DATA.parse_magisk_install_closure(expected_payload),
        }
        current_payload = expected_payload.replace(b"2" * 64, b"9" * 64, 1)
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }

        def read_only(argv, _timeout, _maximum):
            script = argv[-1]
            self.assertNotIn("PASS_N1_RECOVERY_DISABLE", script)
            if script == ROOT_DATA.MAGISK_CLOSURE_SCRIPT:
                return 0, current_payload, b""
            if script == f"{ROOT_DATA.MAGISK_BINARY} -v":
                return 0, (ROOT_DATA.MAGISK_VERSION + "\n").encode(), b""
            if script == f"{ROOT_DATA.MAGISK_BINARY} -V":
                return 0, (ROOT_DATA.MAGISK_VERSION_CODE + "\n").encode(), b""
            raise AssertionError(f"unexpected recovery command: {script}")

        with tempfile.TemporaryDirectory(prefix="s20plus-r1-helper-drift-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            effect = mock.Mock()
            inventory = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA, "validate_recovery_journal", return_value={"install-intent.json"}
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, identity),
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "root_observation",
                     return_value={"root_verified": True, "attempts": 1, "output_sha256": "e" * 64},
                 ), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory", inventory), \
                 mock.patch.object(ROOT_DATA, "durable_command_result", effect):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "helper closure changed"):
                    ROOT_DATA.recover_android(run, read_only)
            inventory.assert_not_called()
            effect.assert_not_called()
            self.assertFalse((run / "recovery-disable-intent.json").exists())

    def test_recovery_validates_journal_and_prepared_serial_before_any_effect(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-recovery-gates-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            health = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     side_effect=ROOT_DATA.RootDataError("malformed journal"),
                 ), \
                 mock.patch.object(ROOT_DATA.bootstrap, "android_health_once", health):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "malformed journal"):
                    ROOT_DATA.recover_android(run)
            health.assert_not_called()
            self.assertFalse((run / "recovery-disable-intent.json").exists())

            wrong_identity = {
                "serial_sha256": "9" * 64,
                "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
                "boot_id_sha256": "8" * 64,
            }
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA, "validate_recovery_journal", return_value={"install-intent.json"}
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "FOREIGN"}, {}, wrong_identity),
                 ), \
                 mock.patch.object(ROOT_DATA.bootstrap, "root_observation") as root_probe:
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "prepared returned target"):
                    ROOT_DATA.recover_android(run)
            root_probe.assert_not_called()
            self.assertFalse((run / "recovery-disable-intent.json").exists())

    def test_safe_mode_evidence_blocks_android_recovery_before_any_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-safe-cross-branch-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            (run / "safe-mode-arm.json").write_text("{}")
            health = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=self.prepared()), \
                 mock.patch.object(ROOT_DATA.bootstrap, "android_health_once", health):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "extra or indirect"):
                    ROOT_DATA.recover_android(run)
            health.assert_not_called()
            self.assertFalse((run / "recovery-disable-intent.json").exists())

    def test_android_recovery_rejects_pre_promotion_boot_without_disable_effect(self) -> None:
        prepared = self.prepared()
        prepared_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-pre-promotion-recovery-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            root_probe = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     return_value={"install-intent.json"},
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, prepared_identity),
                 ), \
                 mock.patch.object(ROOT_DATA.bootstrap, "root_observation", root_probe):
                with self.assertRaisesRegex(
                    ROOT_DATA.RootDataError,
                    "pre-promotion uncertainty requires stock recovery only",
                ):
                    ROOT_DATA.recover_android(run)
            root_probe.assert_not_called()
            self.assertFalse((run / "recovery-disable-intent.json").exists())

    def test_malformed_prior_disable_journal_stops_before_device_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-disable-no-replay-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            (run / "disable-intent.json").write_text("{}")
            health = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=self.prepared()), \
                 mock.patch.object(ROOT_DATA.bootstrap, "android_health_once", health):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "missing its prepared"):
                    ROOT_DATA.recover_android(run)
            health.assert_not_called()
            self.assertFalse((run / "recovery-disable-intent.json").exists())

    def test_android_recovery_resumes_completed_disable_before_reboot_without_replay(self) -> None:
        prepared = self.prepared()
        source_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        final_identity = {**source_identity, "boot_id_sha256": "9" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-disable-resume-") as temp:
            run = Path(temp)
            self.seed_recovery_journal(run, prepared)
            (run / "recovery-disable-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_recovery_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "source_identity": source_identity,
                "root_observation": root,
                "source_state_class": "binding-only",
                "source_canary_result_sha256": None,
                "source_canary_boot_id_sha256": None,
                "source_boot_observed": False,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }))
            self.write_command_result(
                run,
                "recovery-disable",
                b"PASS_N1_RECOVERY_DISABLE_binding-only\n",
            )
            labels: list[str] = []

            def durable(_run, label, *_args):
                labels.append(label)
                self.assertEqual(label, "recovery-disabled-audit")
                return 0, b"PASS_N1_RECOVERY_DISABLED_binding-only\n", b""

            def command(_argv, _timeout, _maximum):
                return 0, b"PASS_N1_RECOVERY_SOURCE_binding-only\n", b""

            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, source_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight", return_value=root), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "dispatch_reboot",
                     return_value=({"serial": "SERIAL"}, final_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "durable_command_result", side_effect=durable), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input"), \
                 mock.patch.object(ROOT_DATA, "cleanup_stage"), \
                 mock.patch.object(ROOT_DATA, "stage_absence_evidence", return_value={
                     "returncode": 0,
                     "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
                     "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                     "staged_input_absent": True,
                 }), \
                 mock.patch.object(ROOT_DATA, "confirm_rooted_terminal_state"), \
                 mock.patch.object(ROOT_DATA, "write_terminal", return_value={"verdict": "RECOVERED"}):
                result = ROOT_DATA.recover_android(run, command=command)
            self.assertEqual(result["verdict"], "RECOVERED")
            self.assertEqual(labels, ["recovery-disabled-audit"])

    def test_android_recovery_rejects_canary_byte_drift_after_disabled_reboot(self) -> None:
        prepared = self.prepared()
        source_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        final_identity = {**source_identity, "boot_id_sha256": "9" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        stable_intent = self.valid_intent()
        stable_value = json.loads(self.valid_result())
        stable_value["boot_id_sha256"] = source_identity["boot_id_sha256"]
        stable_result = (
            json.dumps(stable_value, separators=(",", ":")) + "\n"
        ).encode()
        changed_value = json.loads(stable_result)
        changed_value["monotonic_nsec"] += 1
        changed_result = (
            json.dumps(changed_value, separators=(",", ":")) + "\n"
        ).encode()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-post-reboot-drift-") as temp:
            run = Path(temp)
            self.seed_recovery_journal(run, prepared)
            (run / "recovery-intent.raw").write_bytes(stable_intent)
            (run / "recovery-result.raw").write_bytes(stable_result)
            (run / "recovery-disable-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_recovery_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "source_identity": source_identity,
                "root_observation": root,
                "source_state_class": "completed",
                "source_canary_result_sha256": hashlib.sha256(stable_result).hexdigest(),
                "source_canary_boot_id_sha256": source_identity["boot_id_sha256"],
                "source_boot_observed": False,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }))
            self.write_command_result(
                run,
                "recovery-disable",
                b"PASS_N1_RECOVERY_DISABLE_completed\n",
            )
            terminal = mock.Mock()
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, source_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight", return_value=root), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "dispatch_reboot",
                     return_value=({"serial": "SERIAL"}, final_identity),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "durable_command_result",
                     return_value=(
                         0,
                         b"PASS_N1_RECOVERY_DISABLED_completed\n",
                         b"",
                     ),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_live_canary_pair",
                     return_value=(stable_intent, changed_result, changed_value),
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input", terminal):
                with self.assertRaisesRegex(
                    ROOT_DATA.RootDataError,
                    "changed after the disabled reboot",
                ):
                    ROOT_DATA.recover_android(run, command=mock.Mock())
            terminal.assert_not_called()

    def test_consumed_reboot_prefix_publishes_observation_without_dispatch_replay(self) -> None:
        prepared = self.prepared()
        prior = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        current = {**prior, "boot_id_sha256": "9" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-reboot-prefix-") as temp:
            run = Path(temp)
            (run / "recovery-disabled-reboot-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_reboot_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "phase": "recovery-disabled",
                "prior_boot_id_sha256": prior["boot_id_sha256"],
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }))
            # Reporting stopped after only one raw stream.  The reboot intent is
            # consumed and must never be dispatched again.
            (run / "recovery-disabled-reboot.stdout").write_bytes(b"")
            forbidden_dispatch = mock.Mock(
                side_effect=AssertionError("reboot dispatch must not replay")
            )
            with mock.patch.object(
                ROOT_DATA.bootstrap,
                "android_health_once",
                return_value=({"serial": "SERIAL"}, {}, current),
            ), mock.patch.object(
                ROOT_DATA.bootstrap,
                "root_observation",
                return_value=root,
            ), mock.patch.object(ROOT_DATA, "dispatch_reboot", forbidden_dispatch):
                selected, identity = ROOT_DATA.resume_reboot_observation(
                    run,
                    "recovery-disabled",
                    prepared,
                    mock.Mock(),
                )
            self.assertEqual(selected["serial"], "SERIAL")
            self.assertEqual(identity, current)
            observation = ROOT_DATA.read_exact_json(
                run / "recovery-disabled-observation.json",
                "test reboot observation",
            )
            self.assertEqual(observation["dispatch_evidence"], "consumed-unproved")
            self.assertFalse(observation["replay_permitted"])
            forbidden_dispatch.assert_not_called()

    def test_consumed_reboot_prefix_same_boot_stays_pending_without_replay(self) -> None:
        prepared = self.prepared()
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-reboot-same-boot-") as temp:
            run = Path(temp)
            (run / "disabled-reboot-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_reboot_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "phase": "disabled",
                "prior_boot_id_sha256": identity["boot_id_sha256"],
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }))
            root_probe = mock.Mock()
            with mock.patch.object(
                ROOT_DATA.bootstrap,
                "android_health_once",
                return_value=({"serial": "SERIAL"}, {}, identity),
            ), mock.patch.object(ROOT_DATA.bootstrap, "root_observation", root_probe):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "replay forbidden"):
                    ROOT_DATA.resume_reboot_observation(
                        run,
                        "disabled",
                        prepared,
                        mock.Mock(),
                    )
            root_probe.assert_not_called()
            self.assertFalse((run / "disabled-observation.json").exists())

    def test_normal_partial_disable_requires_read_only_proof_before_one_reboot(self) -> None:
        prepared = self.prepared()
        source = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        returned = {**source, "boot_id_sha256": "9" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-normal-disable-prefix-") as temp:
            run = Path(temp)
            (run / "disable-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "module_id": ROOT_DATA.MODULE_ID,
                "source_identity": source,
                "attempt": 1,
                "replay_permitted": False,
                "at": ROOT_DATA.utc_now(),
            }))
            (run / "disable.stdout").write_bytes(b"")
            effect_labels: list[str] = []

            def direct(command: list[str], *_args: object) -> tuple[int, bytes, bytes]:
                self.assertIn("PASS_N1_DISABLED_AUDIT", command[-1])
                return 0, b"PASS_N1_DISABLED_AUDIT\n", b""

            def durable(_run: Path, label: str, *_args: object) -> tuple[int, bytes, bytes]:
                effect_labels.append(label)
                self.assertEqual(label, "disabled-audit")
                return 0, b"PASS_N1_DISABLED_AUDIT\n", b""

            with mock.patch.object(ROOT_DATA, "validate_recovery_journal"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_command_evidence",
                     return_value={
                         "schema": "s20plus_g986n_native_canary_r1_command_uncertain_consumed_v1"
                     },
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, source),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight", return_value=root), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "dispatch_reboot",
                     return_value=({"serial": "SERIAL"}, returned),
                 ) as reboot, \
                 mock.patch.object(ROOT_DATA, "durable_command_result", side_effect=durable), \
                 mock.patch.object(ROOT_DATA, "read_or_collect_state_files"), \
                 mock.patch.object(
                     ROOT_DATA, "finalize_terminal", return_value={"verdict": "RECOVERED"}
                 ):
                result = ROOT_DATA.resume_normal_disable(run, prepared, direct)
            self.assertEqual(result["verdict"], "RECOVERED")
            self.assertTrue((run / "normal-disable-proof.json").is_file())
            self.assertEqual(effect_labels, ["disabled-audit"])
            reboot.assert_called_once()

    def test_complete_disable_cut_rejects_unrecorded_boot_before_reboot(self) -> None:
        prepared = self.prepared()
        source = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        changed = {**source, "boot_id_sha256": "9" * 64}
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-disable-boot-drift-") as temp:
            run = Path(temp)
            (run / "disable-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "module_id": ROOT_DATA.MODULE_ID,
                "source_identity": source,
                "attempt": 1,
                "replay_permitted": False,
                "at": ROOT_DATA.utc_now(),
            }))
            reboot = mock.Mock()
            with mock.patch.object(ROOT_DATA, "validate_recovery_journal"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_command_evidence",
                     return_value={
                         "schema": "s20plus_g986n_native_canary_r1_command_result_v1"
                     },
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "complete_command_tuple",
                     return_value=(0, b"PASS_N1_DISABLE_EXACT\n", b""),
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=({"serial": "SERIAL"}, {}, changed),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight"), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(ROOT_DATA, "dispatch_reboot", reboot):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "source boot changed"):
                    ROOT_DATA.resume_normal_disable(run, prepared, mock.Mock())
            reboot.assert_not_called()




    def test_android_recovery_accepts_only_monotonic_unobserved_completion(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        source_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        terminal_identity = {**source_identity, "boot_id_sha256": "9" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        valid_intent = self.valid_intent()
        parsed = json.loads(self.valid_result())
        parsed["boot_id_sha256"] = source_identity["boot_id_sha256"]
        valid_result = (json.dumps(parsed, separators=(",", ":")) + "\n").encode()
        staged_absence = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }

        with tempfile.TemporaryDirectory(prefix="s20plus-r1-recovery-monotonic-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            source_read = mock.Mock(
                return_value=(0, b"PASS_N1_RECOVERY_SOURCE_binding-only\n", b"")
            )
            disable = mock.Mock(
                return_value=(0, b"PASS_N1_RECOVERY_DISABLE_completed\n", b"")
            )
            reboot = mock.Mock(return_value=(selected, terminal_identity))
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     return_value={"install-intent.json"},
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=(selected, {}, source_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight", return_value=root), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(ROOT_DATA, "durable_command_result", disable), \
                 mock.patch.object(ROOT_DATA, "dispatch_reboot", reboot), \
                 mock.patch.object(
                     ROOT_DATA,
                     "complete_readonly_command",
                     return_value=(0, b"PASS_N1_RECOVERY_DISABLED_completed\n", b""),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_or_collect_state_files",
                     return_value=(valid_intent, valid_result, parsed),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_live_canary_pair",
                     return_value=(valid_intent, valid_result, parsed),
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input"), \
                 mock.patch.object(ROOT_DATA, "cleanup_stage"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "stage_absence_evidence",
                     return_value=staged_absence,
                 ), \
                 mock.patch.object(ROOT_DATA, "confirm_rooted_terminal_state"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "write_terminal",
                     return_value={"verdict": "RECOVERED"},
                 ) as terminal:
                result = ROOT_DATA.recover_android(run, source_read)
            self.assertEqual(result["verdict"], "RECOVERED")
            source_read.assert_called_once()
            disable.assert_called_once()
            reboot.assert_called_once()
            recovery_intent = ROOT_DATA.read_exact_json(
                run / "recovery-disable-intent.json",
                "test recovery-disable intent",
            )
            self.assertEqual(recovery_intent["source_state_class"], "binding-only")
            self.assertIsNone(recovery_intent["source_canary_result_sha256"])
            self.assertIsNone(recovery_intent["source_canary_boot_id_sha256"])
            self.assertFalse(recovery_intent["source_boot_observed"])
            self.assertEqual(
                terminal.call_args.kwargs["canary_state_class"],
                ROOT_DATA.COMPLETED_SOURCE_UNOBSERVED,
            )

        ROOT_DATA.require_monotonic_recovery_state(
            "binding-only", "completed", "test progression"
        )
        with self.assertRaisesRegex(ROOT_DATA.RootDataError, "regressed"):
            ROOT_DATA.require_monotonic_recovery_state(
                "completed", "intent-only", "test regression"
            )

    def test_android_recovery_resume_keeps_completion_bound_to_disable_source_boot(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        source_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        returned_identity = {**source_identity, "boot_id_sha256": "9" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        parsed = json.loads(self.valid_result())
        parsed["boot_id_sha256"] = source_identity["boot_id_sha256"]
        result_bytes = (json.dumps(parsed, separators=(",", ":")) + "\n").encode()
        intent_bytes = self.valid_intent()
        staged_absence = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-disable-completion-resume-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            (run / "recovery-disable-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_native_canary_r1_recovery_disable_intent_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "source_identity": source_identity,
                "root_observation": root,
                "source_state_class": "intent-only",
                "source_canary_result_sha256": None,
                "source_canary_boot_id_sha256": None,
                "source_boot_observed": False,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }))
            (run / "recovery-intent.raw").write_bytes(intent_bytes)
            (run / "recovery-result.raw").write_bytes(result_bytes)
            self.write_command_result(
                run,
                "recovery-disable",
                b"PASS_N1_RECOVERY_DISABLE_completed\n",
            )
            (run / "recovery-disabled-reboot-intent.json").write_text("{}")
            dispatch = mock.Mock(side_effect=AssertionError("reboot must not replay"))
            terminal = mock.Mock(return_value={"verdict": "RECOVERED"})
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     return_value={
                         "install-intent.json",
                         "recovery-disable-intent.json",
                         "recovery-disabled-reboot-intent.json",
                     },
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=(selected, {}, returned_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight", return_value=root), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "resume_reboot_observation",
                     return_value=(selected, returned_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "dispatch_reboot", dispatch), \
                 mock.patch.object(
                     ROOT_DATA,
                     "complete_readonly_command",
                     return_value=(0, b"PASS_N1_RECOVERY_DISABLED_completed\n", b""),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_live_canary_pair",
                     return_value=(intent_bytes, result_bytes, parsed),
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input"), \
                 mock.patch.object(ROOT_DATA, "cleanup_stage"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "stage_absence_evidence",
                     return_value=staged_absence,
                 ), \
                 mock.patch.object(ROOT_DATA, "confirm_rooted_terminal_state"), \
                 mock.patch.object(ROOT_DATA, "write_terminal", terminal):
                recovered = ROOT_DATA.recover_android(run, mock.Mock())
            self.assertEqual(recovered["verdict"], "RECOVERED")
            self.assertEqual(
                terminal.call_args.kwargs["canary_state_class"],
                ROOT_DATA.COMPLETED_SOURCE_UNOBSERVED,
            )
            dispatch.assert_not_called()

    def test_android_recovery_rejects_completed_result_from_another_source_boot(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        source_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        foreign_result = self.valid_result()
        foreign_parsed = json.loads(foreign_result)
        disable = mock.Mock()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-recovery-source-boot-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     return_value={"install-intent.json"},
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=(selected, {}, source_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight", return_value=root), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_or_collect_state_files",
                     return_value=(self.valid_intent(), foreign_result, foreign_parsed),
                 ), \
                 mock.patch.object(ROOT_DATA, "durable_command_result", disable):
                with self.assertRaisesRegex(
                    ROOT_DATA.RootDataError,
                    "observed source boot",
                ):
                    ROOT_DATA.recover_android(
                        run,
                        command=mock.Mock(
                            return_value=(
                                0,
                                b"PASS_N1_RECOVERY_SOURCE_completed\n",
                                b"",
                            )
                        ),
                    )
            disable.assert_not_called()
            self.assertFalse((run / "recovery-disable-intent.json").exists())

    def test_android_recovery_on_replay_boot_binds_the_first_canary_boot_separately(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        first_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "6" * 64,
        }
        replay_identity = {**first_identity, "boot_id_sha256": "7" * 64}
        disabled_identity = {**first_identity, "boot_id_sha256": "8" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "e" * 64}
        stable_intent = self.valid_intent()
        stable_result = self.valid_result()
        stable_parsed = json.loads(stable_result)
        staged_absence = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-replay-source-recovery-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            (run / "first-observation.json").write_text(json.dumps({
                "android_identity": first_identity,
            }))
            for label in ("first", "recovery"):
                (run / f"{label}-intent.raw").write_bytes(stable_intent)
                (run / f"{label}-result.raw").write_bytes(stable_result)
            source_audit = mock.Mock(
                return_value=(0, b"PASS_N1_RECOVERY_SOURCE_completed\n", b"")
            )
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     return_value={"install-intent.json", "first-observation.json"},
                 ), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     return_value=(selected, {}, replay_identity),
                 ), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight", return_value=root), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_or_collect_state_files",
                     return_value=(stable_intent, stable_result, stable_parsed),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "durable_command_result",
                     return_value=(0, b"PASS_N1_RECOVERY_DISABLE_completed\n", b""),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "dispatch_reboot",
                     return_value=(selected, disabled_identity),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "complete_readonly_command",
                     return_value=(0, b"PASS_N1_RECOVERY_DISABLED_completed\n", b""),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_live_canary_pair",
                     return_value=(stable_intent, stable_result, stable_parsed),
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input"), \
                 mock.patch.object(ROOT_DATA, "cleanup_stage"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "stage_absence_evidence",
                     return_value=staged_absence,
                 ), \
                 mock.patch.object(ROOT_DATA, "confirm_rooted_terminal_state"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "write_terminal",
                     return_value={"verdict": "RECOVERED"},
                 ):
                result = ROOT_DATA.recover_android(run, source_audit)
            self.assertEqual(result["verdict"], "RECOVERED")
            recovery_intent = ROOT_DATA.read_exact_json(
                run / "recovery-disable-intent.json",
                "test replay-source recovery intent",
            )
            self.assertEqual(recovery_intent["source_identity"], replay_identity)
            self.assertEqual(
                recovery_intent["source_canary_boot_id_sha256"],
                first_identity["boot_id_sha256"],
            )
            self.assertTrue(recovery_intent["source_boot_observed"])


    def test_execute_success_has_one_install_one_disable_and_three_reboots(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        identities = [
            {
                "serial_sha256": "1" * 64,
                "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
                "boot_id_sha256": value * 64,
            }
            for value in ("6", "7", "8")
        ]
        valid_result = self.valid_result()
        valid_intent = self.valid_intent()
        parsed = json.loads(valid_result)
        command_labels: list[str] = []
        reboot_phases: list[str] = []
        initial_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        health_results = iter((initial_identity, initial_identity, identities[1]))

        def durable(_run, label, _argv, _command, _timeout, _maximum):
            command_labels.append(label)
            if label == "install":
                stdout = (
                    b"****************************\n S20+ Native Canary \n"
                    b" by android-native-init-lab \n****************************\n"
                    b"*******************\n Powered by Magisk \n*******************\n"
                    b"- Extracting module files\n- Done\nPASS_N1_INSTALL_EXACT\n"
                )
                return 0, stdout, b""
            self.assertEqual(label, "disable")
            return 0, b"PASS_N1_DISABLE_EXACT\n", b""

        def reboot(_run, phase, _prepared, selected_value, _identity, _command):
            reboot_phases.append(phase)
            return selected_value, identities[len(reboot_phases) - 1]

        with tempfile.TemporaryDirectory(prefix="s20plus-r1-success-") as temp:
            run = Path(temp)
            def health(*_args, **_kwargs):
                return selected, {}, next(health_results)

            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(ROOT_DATA, "require_exact_nodes"), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     side_effect=health,
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "root_preflight",
                     return_value={
                         "test": "exact",
                         "_module_inventory": b"active_count=0\nupdate_count=0\n",
                     },
                 ), \
                 mock.patch.object(ROOT_DATA, "stage_inputs"), \
                 mock.patch.object(ROOT_DATA, "post_stage_preflight"), \
                 mock.patch.object(ROOT_DATA, "recovery_magisk_preflight"), \
                 mock.patch.object(ROOT_DATA, "durable_command_result", side_effect=durable), \
                 mock.patch.object(ROOT_DATA, "durable_root_exact"), \
                 mock.patch.object(ROOT_DATA, "dispatch_reboot", side_effect=reboot), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_state_files",
                     return_value=(valid_intent, valid_result, parsed),
                 ), \
                 mock.patch.object(ROOT_DATA, "write_terminal_input"), \
                 mock.patch.object(ROOT_DATA, "cleanup_stage"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "stage_absence_evidence",
                     return_value={
                         "returncode": 0,
                         "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
                         "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                         "staged_input_absent": True,
                     },
                 ), \
                 mock.patch.object(ROOT_DATA, "confirm_rooted_terminal_state"), \
                 mock.patch.object(ROOT_DATA, "write_terminal", return_value={"verdict": "PASS"}):
                result = ROOT_DATA.execute(run, prepared["approval_token"])
            self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(command_labels, ["install", "disable"])
        self.assertEqual(reboot_phases, ["first", "replay", "disabled"])

    def test_normal_disable_rebinds_helpers_before_persistent_marker(self) -> None:
        prepared = self.prepared()
        selected = {"serial": "SERIAL"}
        initial_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "2" * 64,
        }
        first_identity = {**initial_identity, "boot_id_sha256": "6" * 64}
        replay_identity = {**initial_identity, "boot_id_sha256": "7" * 64}
        valid_intent = self.valid_intent()
        valid_result = self.valid_result()
        parsed = json.loads(valid_result)
        health = iter((initial_identity, initial_identity, replay_identity))
        reboots = iter((first_identity, replay_identity))
        command_labels: list[str] = []

        def install_only(_run, label, *_args):
            command_labels.append(label)
            self.assertEqual(label, "install")
            return (
                0,
                b"****************************\n S20+ Native Canary \n"
                b" by android-native-init-lab \n****************************\n"
                b"*******************\n Powered by Magisk \n*******************\n"
                b"- Extracting module files\n- Done\nPASS_N1_INSTALL_EXACT\n",
                b"",
            )

        with tempfile.TemporaryDirectory(prefix="s20plus-r1-disable-helper-drift-") as temp:
            run = Path(temp)
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(ROOT_DATA, "require_exact_nodes"), \
                 mock.patch.object(
                     ROOT_DATA.bootstrap,
                     "android_health_once",
                     side_effect=lambda *_args, **_kwargs: (
                         selected,
                         {},
                         next(health),
                     ),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "root_preflight",
                     return_value={
                         **prepared["binding"]["magisk"],
                         "_module_inventory": b"active_count=0\nupdate_count=0\n",
                     },
                 ), \
                 mock.patch.object(ROOT_DATA, "stage_inputs"), \
                 mock.patch.object(ROOT_DATA, "post_stage_preflight"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "durable_command_result",
                     side_effect=install_only,
                 ), \
                 mock.patch.object(ROOT_DATA, "durable_root_exact"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "dispatch_reboot",
                     side_effect=lambda *_args, **_kwargs: (selected, next(reboots)),
                 ), \
                 mock.patch.object(ROOT_DATA, "require_module_inventory"), \
                 mock.patch.object(
                     ROOT_DATA,
                     "read_state_files",
                     return_value=(valid_intent, valid_result, parsed),
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "recovery_magisk_preflight",
                     side_effect=ROOT_DATA.RootDataError("disable helper closure drift"),
                 ) as pre_disable:
                with self.assertRaisesRegex(
                    ROOT_DATA.RootDataError,
                    "disable helper closure drift",
                ):
                    ROOT_DATA.execute(run, prepared["approval_token"], mock.Mock())
            self.assertEqual(command_labels, ["install"])
            pre_disable.assert_called_once()
            self.assertFalse((run / "disable-intent.json").exists())

    def test_stock_handoff_is_exact_and_cannot_be_forged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-handoff-") as temp:
            run = Path(temp)
            prepared = self.prepared()
            expected = {
                "schema": "s20plus_g986n_native_canary_r1_stock_handoff_v1",
                "version": ROOT_DATA.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "run_dir": str(run),
                "stock_boot": prepared["binding"]["artifacts"]["stock_boot"],
                "recovery_runner": prepared["binding"]["closure"]["stock_recovery_runner"],
                "operator_confirmed": True,
                "operator_asserted_rooted_recovery_unavailable": True,
                "confirmation": ROOT_DATA.STOCK_HANDOFF_CONFIRM,
                "attempt": 1,
                "replay_permitted": False,
                "at": "now",
            }
            (run / "stock-recovery-handoff.json").write_text(json.dumps(expected))
            with mock.patch.object(STOCK, "self_receipt", return_value={
                **prepared["binding"]["closure"]["stock_recovery_runner"],
            }):
                self.assertEqual(STOCK.read_handoff(run, prepared), expected)
                malformed = json.loads(json.dumps(expected))
                malformed["attempt"] = True
                (run / "stock-recovery-handoff.json").write_text(json.dumps(malformed))
                with self.assertRaises(STOCK.StockRecoveryError):
                    STOCK.read_handoff(run, prepared)
                malformed = json.loads(json.dumps(expected))
                malformed["operator_confirmed"] = 1
                malformed["replay_permitted"] = 0
                (run / "stock-recovery-handoff.json").write_text(json.dumps(malformed))
                with self.assertRaises(STOCK.StockRecoveryError):
                    STOCK.read_handoff(run, prepared)
                forged = json.loads(json.dumps(expected))
                forged["stock_boot"]["sha256"] = "0" * 64
                (run / "stock-recovery-handoff.json").write_text(json.dumps(forged))
                with self.assertRaises(STOCK.StockRecoveryError):
                    STOCK.read_handoff(run, prepared)

    def test_stock_handoff_rejects_completed_rooted_recovery_branch(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-handoff-closed-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            (run / "terminal-result.json").write_text("{}")
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "inconsistent"):
                    ROOT_DATA.create_stock_handoff(
                        run,
                        ROOT_DATA.STOCK_HANDOFF_CONFIRM,
                    )
            self.assertFalse((run / "stock-recovery-handoff.json").exists())
            (run / "terminal-result.json").unlink()
            recovery_tuple = {
                "recovery-disabled-audit.stdout",
                "recovery-disabled-audit.stderr",
                "recovery-disabled-audit-result.json",
            }
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     return_value={"install-intent.json", *recovery_tuple},
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "completed_readonly_command",
                     return_value=(0, b"PASS_N1_RECOVERY_DISABLED_binding-only\n", b""),
                 ):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "completed rooted"):
                    ROOT_DATA.create_stock_handoff(
                        run,
                        ROOT_DATA.STOCK_HANDOFF_CONFIRM,
                    )

    def test_stock_handoff_allows_only_semantically_failed_rooted_audit(self) -> None:
        prepared = self.prepared()
        recovery_tuple = {
            "recovery-disabled-audit.stdout",
            "recovery-disabled-audit.stderr",
            "recovery-disabled-audit-result.json",
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-handoff-semantic-failure-") as temp:
            run = Path(temp)
            (run / "install-intent.json").write_text("{}")
            with mock.patch.object(ROOT_DATA, "require_active"), \
                 mock.patch.object(ROOT_DATA, "read_prepared", return_value=prepared), \
                 mock.patch.object(
                     ROOT_DATA,
                     "validate_recovery_journal",
                     return_value={"install-intent.json", *recovery_tuple},
                 ), \
                 mock.patch.object(
                     ROOT_DATA,
                     "completed_readonly_command",
                     return_value=(0, b"WRONG_ROOTED_AUDIT_OUTPUT\n", b""),
                 ):
                path = ROOT_DATA.create_stock_handoff(
                    run,
                    ROOT_DATA.STOCK_HANDOFF_CONFIRM,
                )
            self.assertEqual(path, run / "stock-recovery-handoff.json")
            handoff = ROOT_DATA.read_exact_json(path, "test stock handoff")
            self.assertTrue(handoff["operator_asserted_rooted_recovery_unavailable"])
            self.assertFalse(handoff["replay_permitted"])

    def test_retired_safe_mode_journal_node_is_rejected(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-retired-safe-node-") as temp:
            run = Path(temp)
            self.seed_recovery_journal(run, prepared)
            (run / "safe-mode-arm.json").write_text("{}")
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "extra or indirect"):
                ROOT_DATA.validate_recovery_journal(
                    run,
                    prepared,
                    allow_uncertain_commands=True,
                )

    def test_recovery_journal_rejects_forged_intent_extra_and_symlink(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-journal-") as temp:
            run = Path(temp)
            intent = self.seed_recovery_journal(run, prepared)
            path = run / "install-intent.json"
            ROOT_DATA.validate_recovery_journal(run, prepared)
            forged = {**intent, "attempt": True}
            path.write_text(json.dumps(forged))
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_recovery_journal(run, prepared)
            path.write_text(json.dumps(intent))
            extra = run / "unexpected"
            extra.write_text("x")
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_recovery_journal(run, prepared)
            extra.unlink()
            target = run / "elsewhere"
            target.write_text("x")
            extra.symlink_to(target)
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_recovery_journal(run, prepared)

    def test_recovery_journal_rejects_forged_command_receipt(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-receipt-") as temp:
            run = Path(temp)
            self.seed_recovery_journal(run, prepared)
            stdout = b"****************************\n"
            stderr = b""
            (run / "install.stdout").write_bytes(stdout)
            (run / "install.stderr").write_bytes(stderr)
            result = {
                "schema": "s20plus_g986n_native_canary_r1_command_result_v1",
                "version": ROOT_DATA.VERSION,
                "label": "install",
                "returncode": False,
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                "stdout_bytes": len(stdout),
                "stderr_bytes": len(stderr),
                "replay_permitted": False,
            }
            (run / "install-result.json").write_text(json.dumps(result))
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_recovery_journal(run, prepared)

    def test_recovery_prefix_graph_rejects_impossible_or_mixed_branches(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-prefix-graph-") as temp:
            run = Path(temp)
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "stage chain"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {"install-intent.json"},
                )
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "mixes"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {"disable-intent.json", "recovery-disable-intent.json"},
                )
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "replay chain"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {"disable-intent.json"},
                )
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "no disable intent"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {"recovery-disabled-reboot-intent.json"},
                )
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "intent event"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {"stage-claim.stdout"},
                )
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "terminal input"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {"cleanup-intent.json"},
                )
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "cleanup prefix"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {
                        "stage-intent.json",
                        "terminal-result.json",
                        "terminal-input.json",
                    },
                )
            ROOT_DATA.validate_recovery_prefix_graph(
                run,
                prepared,
                {"terminal-result.json", "terminal-input.json"},
            )

    def test_recovery_prefix_graph_binds_reboot_sources_before_stock_handoff(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-prefix-sources-") as temp:
            run = Path(temp)
            (run / "first-reboot-intent.json").write_text(json.dumps({
                "prior_boot_id_sha256": "9" * 64,
            }))
            with mock.patch.object(
                ROOT_DATA,
                "require_complete_successful_command",
                return_value=(0, b"PASS_N1_POST_INSTALL_AUDIT\n", b""),
            ):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "wrong source"):
                    ROOT_DATA.validate_recovery_prefix_graph(
                        run,
                        prepared,
                        {"first-reboot-intent.json"},
                    )

            (run / "recovery-disable-intent.json").write_text(json.dumps({
                "source_identity": {"boot_id_sha256": "7" * 64},
            }))
            (run / "recovery-disabled-reboot-intent.json").write_text(json.dumps({
                "prior_boot_id_sha256": "8" * 64,
            }))
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "not contiguous"):
                ROOT_DATA.validate_recovery_prefix_graph(
                    run,
                    prepared,
                    {
                        "recovery-disable-intent.json",
                        "recovery-disabled-reboot-intent.json",
                    },
                )

    def test_state_read_prefixes_require_their_completed_phase_audits(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-state-prefix-") as temp:
            run = Path(temp)
            self.write_command_result(
                run,
                "post-install-audit",
                b"PASS_N1_POST_INSTALL_AUDIT\n",
            )
            first_reboot = {
                "prior_boot_id_sha256": prepared["binding"]["target"]["boot_id_sha256"],
            }
            first_observation = {
                "android_identity": {"boot_id_sha256": "6" * 64},
            }
            replay_reboot = {"prior_boot_id_sha256": "6" * 64}
            replay_observation = {
                "android_identity": {"boot_id_sha256": "7" * 64},
            }
            (run / "first-reboot-intent.json").write_text(json.dumps(first_reboot))
            (run / "first-observation.json").write_text(json.dumps(first_observation))
            (run / "replay-reboot-intent.json").write_text(json.dumps(replay_reboot))
            (run / "replay-observation.json").write_text(json.dumps(replay_observation))
            seen = {
                "post-install-audit.stdout",
                "post-install-audit.stderr",
                "post-install-audit-result.json",
                "first-reboot-intent.json",
                "first-observation.json",
                "first-intent.raw",
            }
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "complete command"):
                ROOT_DATA.validate_recovery_prefix_graph(run, prepared, seen)

            def predecessor(_run, label):
                if label == "post-install-audit":
                    return 0, b"PASS_N1_POST_INSTALL_AUDIT\n", b""
                if label == "first-active-audit":
                    return 0, b"PASS_N1_ACTIVE_AUDIT\n", b""
                if label == "replay-active-audit":
                    raise ROOT_DATA.RootDataError("missing replay audit complete command")
                raise AssertionError(label)

            replay_seen = {
                "first-reboot-intent.json",
                "first-observation.json",
                "first-active-audit-result.json",
                "first-active-audit.stdout",
                "first-active-audit.stderr",
                "first-intent.raw",
                "first-result.raw",
                "events/03-native-canary-first-observed.json",
                "replay-reboot-intent.json",
                "replay-observation.json",
                "replay-intent.raw",
            }
            with mock.patch.object(
                ROOT_DATA,
                "require_complete_successful_command",
                side_effect=predecessor,
            ), mock.patch.object(
                ROOT_DATA,
                "read_canary_pair",
                return_value=(b"intent", b"result", {}),
            ):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "replay audit"):
                    ROOT_DATA.validate_recovery_prefix_graph(
                        run,
                        prepared,
                        replay_seen,
                    )

            disabled_seen = {
                "disabled-observation.json",
                "disabled-intent.raw",
            }
            with mock.patch.object(
                ROOT_DATA,
                "completed_readonly_command",
                side_effect=ROOT_DATA.RootDataError("missing disabled audit"),
            ):
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "disabled audit"):
                    ROOT_DATA.validate_recovery_prefix_graph(
                        run,
                        prepared,
                        disabled_seen,
                    )

    def test_first_observed_event_binds_the_exact_canary_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-first-event-") as temp:
            run = Path(temp)
            (run / "events").mkdir()
            result = b"exact-result\n"
            (run / "first-result.raw").write_bytes(result)
            value = {
                "schema": "s20plus_g986n_f1_event_v1",
                "version": ROOT_DATA.bootstrap.VERSION,
                "ordinal": 3,
                "name": "native-canary-first-observed",
                "at": "now",
                "result_sha256": hashlib.sha256(result).hexdigest(),
            }
            path = run / "events/03-native-canary-first-observed.json"
            path.write_text(json.dumps(value))
            ROOT_DATA.validate_first_observed_event(run)
            value["result_sha256"] = "0" * 64
            path.write_text(json.dumps(value))
            with self.assertRaises(ROOT_DATA.RootDataError):
                ROOT_DATA.validate_first_observed_event(run)

    def test_stock_journal_requires_every_named_state_node(self) -> None:
        required = set(STOCK.STOCK_ARM_FILES)
        with mock.patch.object(
            STOCK.root_data,
            "validate_recovery_journal",
            return_value={"stock-recovery-handoff.json"},
        ):
            with self.assertRaises(STOCK.StockRecoveryError):
                STOCK.validate_stock_journal(
                    Path("/tmp/not-read"),
                    self.prepared(),
                    required,
                    required,
                )

    def test_stock_owner_rejects_a_handoff_superseding_completed_rooted_recovery(self) -> None:
        seen = {
            "stock-recovery-handoff.json",
            "recovery-disabled-audit.stdout",
            "recovery-disabled-audit.stderr",
            "recovery-disabled-audit-result.json",
        }
        with mock.patch.object(
            STOCK.root_data,
            "validate_recovery_journal",
            return_value=seen,
        ), mock.patch.object(
            STOCK.root_data,
            "completed_readonly_command",
            return_value=(0, b"PASS_N1_RECOVERY_DISABLED_binding-only\n", b""),
        ):
            with self.assertRaisesRegex(
                STOCK.root_data.RootDataError,
                "completed rooted",
            ):
                STOCK.validate_stock_journal(
                    Path("/tmp/not-read"),
                    self.prepared(),
                    {"stock-recovery-handoff.json"},
                    {"stock-recovery-handoff.json"},
                )

    def test_stock_event_is_strict_json_and_binds_the_rollback_intent(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-event-") as temp:
            run = Path(temp)
            events = run / "events"
            events.mkdir()
            event = {
                "schema": "s20plus_g986n_f1_event_v1",
                "version": ROOT_DATA.bootstrap.VERSION,
                "ordinal": 90,
                "name": "rollback-transfer-started",
                "at": "now",
                "ap_sha256": ROOT_DATA.bootstrap.ROLLBACK_SHA256,
            }
            path = events / "90-rollback-transfer-started.json"
            path.write_text(json.dumps(event))
            with mock.patch.object(STOCK, "validate_rollback_intent") as intent:
                self.assertEqual(STOCK.validate_rollback_event(run, prepared), event)
            intent.assert_called_once_with(run, prepared)
            path.write_bytes(b'{"schema":"s20plus_g986n_f1_event_v1"}\x00')
            with self.assertRaises(Exception):
                STOCK.validate_rollback_event(run, prepared)

    def test_stock_transfer_uses_atomic_r1_journal_and_exact_odin_core_once(self) -> None:
        prepared = self.prepared()
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
        }
        stdout = b"Setup Connection Upload Binaries boot.img.lz4 100% Close Connection"
        receipt = {
            "label": "rollback",
            "returncode": 0,
            "command_shape": ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"],
            "regular_path_inputs": True,
            "anonymous_proc_fd_inputs": False,
            "odin": {
                "path": str(ROOT_DATA.bootstrap.ODIN),
                "size": ROOT_DATA.bootstrap.ODIN_SIZE,
                "sha256": ROOT_DATA.bootstrap.ODIN_SHA256,
            },
            "ap": {
                "path": str(ROOT_DATA.bootstrap.ROLLBACK),
                "size": ROOT_DATA.bootstrap.ROLLBACK_SIZE,
                "sha256": ROOT_DATA.bootstrap.ROLLBACK_SHA256,
            },
            "endpoint_path_sha256": hashlib.sha256(endpoint["device"].encode()).hexdigest(),
            "endpoint_pre_identity": endpoint["endpoint_identity"],
            "endpoint_post_identity": endpoint["endpoint_identity"],
            "endpoint_post_state": "same",
            "stdout_bytes": len(stdout),
            "stderr_bytes": 0,
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-atomic-") as temp:
            run = Path(temp)
            (run / "events").mkdir()
            with mock.patch.object(
                STOCK.bootstrap,
                "execute_odin_exact",
                return_value=(receipt, stdout, b""),
            ) as execute, mock.patch.object(
                STOCK.bootstrap,
                "transfer_once",
            ) as legacy_transfer:
                classification = STOCK.transfer_stock_once(
                    run,
                    endpoint,
                    prepared["binding_sha256"],
                )
            self.assertEqual(classification, "odin_transfer_completed")
            execute.assert_called_once()
            legacy_transfer.assert_not_called()
            self.assertEqual(
                STOCK.validate_rollback_outcome(run, prepared, classification)["classification"],
                "odin_transfer_completed",
            )

    def test_stock_transfer_prefix_is_consumed_uncertain_and_never_replayed(self) -> None:
        prepared = self.prepared()
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(ROOT_DATA.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**ROOT_DATA.bootstrap.DOWNLOAD_USB, "serial_absent": True},
        }
        intent = {
            "schema": "s20plus_g986n_f1_transfer_intent_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "kind": "rollback",
            "binding_sha256": prepared["binding_sha256"],
            "ap_sha256": ROOT_DATA.bootstrap.ROLLBACK_SHA256,
            "endpoint": {"device": endpoint["device"], "identity": endpoint["endpoint_identity"]},
            "attempt": 1,
            "no_replay": True,
            "at": "now",
        }
        confirmation = {
            "schema": "s20plus_g986n_native_canary_stock_recovery_confirmation_v1",
            "version": STOCK.VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "endpoint": endpoint,
            "operator_confirmed": True,
            "confirmation": STOCK.PHYSICAL_CONFIRM,
            "attempt": 1,
            "replay_permitted": False,
            "at": "now",
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-prefix-") as temp:
            run = Path(temp)
            for name in STOCK.STOCK_ARM_FILES:
                (run / name).write_text("{}")
            (run / "stock-recovery-confirmation.json").write_text(json.dumps(confirmation))
            (run / "rollback-intent.json").write_text(json.dumps(intent))
            journal = lambda *_args, **_kwargs: {
                name
                for name in STOCK.STOCK_KNOWN_FILES
                if os.path.lexists(run / name)
            }
            common = (
                mock.patch.object(
                    STOCK.root_data,
                    "validate_recovery_journal",
                    side_effect=journal,
                ),
                mock.patch.object(
                    STOCK,
                    "validate_arm",
                    return_value={"arrival_endpoint": endpoint},
                ),
                mock.patch.object(STOCK, "validate_confirmation"),
                mock.patch.object(STOCK, "validate_rollback_event"),
            )
            with common[0], common[1], common[2], common[3]:
                classification, _files, complete = STOCK.validate_stock_transfer_state(
                    run, prepared
                )
            self.assertEqual(classification, "odin_effect_outcome_unproved_after_intent")
            self.assertFalse(complete)

            (run / "events").mkdir()
            (run / "events/90-rollback-transfer-started.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_event_v1",
                "version": ROOT_DATA.bootstrap.VERSION,
                "ordinal": 90,
                "name": "rollback-transfer-started",
                "at": "now",
                "ap_sha256": ROOT_DATA.bootstrap.ROLLBACK_SHA256,
            }))
            (run / "rollback.stdout").write_bytes(b"partial but bounded")
            with common[0], common[1], common[2], common[3]:
                classification, _files, complete = STOCK.validate_stock_transfer_state(
                    run, prepared
                )
            self.assertEqual(classification, "odin_effect_outcome_unproved_after_intent")
            self.assertFalse(complete)

            (run / "rollback.stdout").unlink()
            (run / "rollback.stderr").write_bytes(b"out of order")
            with common[0], common[1], common[2], common[3]:
                with self.assertRaisesRegex(STOCK.StockRecoveryError, "out of order"):
                    STOCK.validate_stock_transfer_state(run, prepared)

    def test_stock_finalize_parks_an_incomplete_transfer_prefix_without_odin(self) -> None:
        prepared = self.prepared()
        transfer_files = STOCK.STOCK_ARM_FILES | {
            "stock-recovery-confirmation.json",
            "rollback-intent.json",
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-prefix-finalize-") as temp:
            run = Path(temp)
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(
                     STOCK.root_data, "read_prepared", return_value=prepared
                 ) as read_prepared, \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(
                     STOCK,
                     "validate_stock_transfer_state",
                     return_value=(
                         "odin_effect_outcome_unproved_after_intent",
                         set(transfer_files),
                         False,
                     ),
                 ), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(
                     STOCK.bootstrap,
                     "final_stock_health",
                     return_value={"healthy": False, "reason": "android-not-returned"},
                 ), \
                 mock.patch.object(STOCK, "transfer_stock_once") as transfer:
                result = STOCK.finalize_stock(run)
            transfer.assert_not_called()
            self.assertEqual(
                result["verdict"],
                "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_STOCK_TRANSFER_UNCERTAIN",
            )
            self.assertEqual(
                result["stock_transfer"],
                "odin_effect_outcome_unproved_after_intent",
            )
            self.assertFalse(result["stock_recovery_replay_permitted"])

    def test_stock_same_boot_pending_receipt_round_trips_without_schema_stranding(self) -> None:
        prepared = self.prepared()
        observed = {
            "healthy": False,
            "root_absent": True,
            "boot_changed": False,
            "boot_id_sha256": "2" * 64,
            "confirmed_boot_id_sha256": "2" * 64,
            "root_probe_rc": 127,
            "root_probe_sha256": "a" * 64,
            "target": {
                "model": ROOT_DATA.bootstrap.EXPECTED_MODEL,
                "device": ROOT_DATA.bootstrap.EXPECTED_DEVICE,
                "product": ROOT_DATA.bootstrap.EXPECTED_PRODUCT,
                "incremental": ROOT_DATA.bootstrap.EXPECTED_INCREMENTAL,
            },
        }
        normalized = STOCK.normalize_pending_final_health(observed)
        self.assertEqual(normalized["reason"], "boot-identity-not-changed")
        verdict = STOCK.pending_verdict(normalized)
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-same-boot-") as temp:
            run = Path(temp)
            written = STOCK.pending_result(
                run,
                prepared,
                verdict,
                "odin_transfer_completed",
                normalized,
            )
            self.assertEqual(STOCK.validate_pending(run, prepared), written)
            forged = json.loads((run / "stock-recovery-result.json").read_text())
            forged["final_health"]["root_absent"] = 1
            (run / "stock-recovery-result.json").unlink()
            (run / "stock-recovery-result.json").write_text(json.dumps(forged))
            with self.assertRaises(STOCK.StockRecoveryError):
                STOCK.validate_pending(run, prepared)

    def test_stock_arm_resumes_complete_arm_without_reenumeration(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-arm-cut-") as temp:
            run = Path(temp)
            (run / "stock-recovery-arm.json").write_text("{}")
            (run / "stock-recovery-arrival.json").write_text("{}")
            baseline_read = mock.Mock(side_effect=AssertionError("baseline must not replay"))
            arrival_read = mock.Mock(side_effect=AssertionError("arrival must not replay"))
            enumerate_read = mock.Mock(side_effect=AssertionError("complete arm must not re-enumerate"))
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(STOCK, "validate_arm_intent", return_value={}), \
                 mock.patch.object(STOCK, "validate_arm"), \
                 mock.patch.object(STOCK.bootstrap, "download_baseline", baseline_read), \
                 mock.patch.object(STOCK.bootstrap, "wait_download_after_baseline", arrival_read), \
                 mock.patch.object(STOCK.bootstrap, "enumerate_download", enumerate_read):
                result = STOCK.arm(run, STOCK.PHYSICAL_ARM)
            self.assertIn("PHYSICAL_DOWNLOAD_CONFIRMATION", result["verdict"])
            baseline_read.assert_not_called()
            arrival_read.assert_not_called()
            enumerate_read.assert_not_called()
            self.assertTrue((run / "stock-recovery-arm.json").is_file())

    def test_stock_arm_records_intent_before_exact_arrival(self) -> None:
        prepared = self.prepared()
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(ROOT_DATA.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**ROOT_DATA.bootstrap.DOWNLOAD_USB, "serial_absent": True},
        }
        baseline = {
            "schema": "s20plus_g986n_f1_download_baseline_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "endpoint_count": 0,
            "listing_sha256": "a" * 64,
            "at": ROOT_DATA.utc_now(),
        }
        arrival = {
            "baseline_listing_sha256": baseline["listing_sha256"],
            "arrival_listing_sha256": "b" * 64,
            "arrival_endpoint": endpoint["device"],
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-arm-arrival-") as temp:
            run = Path(temp)
            baseline_read = mock.Mock(return_value=baseline)
            def observe_after_intent(*_args: object) -> tuple[dict[str, object], dict[str, str]]:
                self.assertTrue((run / "stock-recovery-arm.json").is_file())
                self.assertFalse((run / "stock-recovery-arrival.json").exists())
                return endpoint, arrival

            arrival_read = mock.Mock(side_effect=observe_after_intent)
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(STOCK.bootstrap, "download_baseline", baseline_read), \
                 mock.patch.object(
                     STOCK.bootstrap,
                     "wait_download_after_baseline",
                     arrival_read,
                 ):
                result = STOCK.arm(run, STOCK.PHYSICAL_ARM)
            self.assertIn("PHYSICAL_DOWNLOAD_CONFIRMATION", result["verdict"])
            baseline_read.assert_called_once()
            arrival_read.assert_called_once_with(
                mock.ANY,
                baseline,
                STOCK.ARM_ARRIVAL_WINDOW_SEC,
            )
            arm_record = STOCK.validate_arm(run, prepared)
            self.assertEqual(arm_record["arrival_endpoint"], endpoint)

    def test_host_journal_rejects_nonfinite_json_and_noncanonical_numbers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-nonfinite-") as temp:
            path = Path(temp) / "journal.json"
            path.write_bytes(b'{"value":Infinity}\n')
            with self.assertRaisesRegex(ROOT_DATA.RootDataError, "non-finite"):
                ROOT_DATA.read_exact_json(path, "hostile journal")
        with self.assertRaisesRegex(ROOT_DATA.RootDataError, "not finite"):
            ROOT_DATA.canonical_bytes({"value": float("inf")})

    def test_stock_baseline_and_endpoint_require_exact_local_types(self) -> None:
        baseline = {
            "schema": "s20plus_g986n_f1_download_baseline_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "endpoint_count": 0,
            "listing_sha256": "a" * 64,
            "at": ROOT_DATA.utc_now(),
        }
        self.assertEqual(STOCK.validate_stock_download_baseline(baseline), baseline)
        for key, hostile in (
            ("listing_sha256", int("1" * 64)),
            ("at", 1),
        ):
            forged = {**baseline, key: hostile}
            with self.assertRaises(STOCK.StockRecoveryError):
                STOCK.validate_stock_download_baseline(forged)
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(ROOT_DATA.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**ROOT_DATA.bootstrap.DOWNLOAD_USB, "serial_absent": 1},
        }
        with self.assertRaises(STOCK.StockRecoveryError):
            STOCK.validate_stock_download_endpoint(endpoint, "hostile endpoint")

    def test_stock_arm_only_cut_observes_current_endpoint_once_without_physical_replay(self) -> None:
        prepared = self.prepared()
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(ROOT_DATA.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**ROOT_DATA.bootstrap.DOWNLOAD_USB, "serial_absent": True},
        }
        baseline = {
            "schema": "s20plus_g986n_f1_download_baseline_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "endpoint_count": 0,
            "listing_sha256": "a" * 64,
            "at": ROOT_DATA.utc_now(),
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-arm-only-") as temp:
            run = Path(temp)
            armed_at = STOCK.datetime.now(STOCK.timezone.utc)
            arm = {
                "schema": "s20plus_g986n_native_canary_stock_recovery_arm_intent_v1",
                "version": STOCK.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "baseline": baseline,
                "baseline_sha256": ROOT_DATA.canonical_sha(baseline),
                "operator_confirmed": True,
                "physical_action": "operator-physical-download-entry",
                "arrival_deadline": (
                    armed_at + STOCK.timedelta(seconds=STOCK.ARM_ARRIVAL_WINDOW_SEC)
                ).isoformat(),
                "confirmation_required": STOCK.PHYSICAL_CONFIRM,
                "attempt": 1,
                "replay_permitted": False,
                "at": armed_at.isoformat(),
            }
            (run / "stock-recovery-arm.json").write_text(json.dumps(arm))
            wait = mock.Mock(side_effect=AssertionError("physical entry must not replay"))
            baseline_read = mock.Mock(side_effect=AssertionError("baseline must not replay"))
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(STOCK.bootstrap, "download_baseline", baseline_read), \
                 mock.patch.object(STOCK.bootstrap, "wait_download_after_baseline", wait), \
                 mock.patch.object(
                     STOCK.bootstrap,
                     "enumerate_download",
                     return_value=([endpoint["device"]], "b" * 64),
                 ) as enumerate_once, \
                 mock.patch.object(STOCK.bootstrap, "identify_download", return_value=endpoint):
                result = STOCK.arm(run, STOCK.PHYSICAL_ARM)
            self.assertIn("PHYSICAL_DOWNLOAD_CONFIRMATION", result["verdict"])
            enumerate_once.assert_called_once()
            baseline_read.assert_not_called()
            wait.assert_not_called()
            arrival = STOCK.validate_arm(run, prepared)
            self.assertEqual(arrival["arm_sha256"], ROOT_DATA.canonical_sha(arm))

            different_endpoint = {
                **endpoint,
                "endpoint_identity": [1, 2, 3, 5],
            }
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(
                     STOCK.bootstrap,
                     "identify_download",
                     return_value=different_endpoint,
                 ), \
                 mock.patch.object(STOCK, "transfer_stock_once") as transfer:
                with self.assertRaisesRegex(STOCK.StockRecoveryError, "armed arrival"):
                    STOCK.confirm(run, STOCK.PHYSICAL_CONFIRM)
            transfer.assert_not_called()

    def test_stock_arm_rejects_legacy_baseline_only_cut(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-legacy-baseline-") as temp:
            run = Path(temp)
            (run / "stock-recovery-baseline.json").write_text("{}")
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK.bootstrap, "download_baseline") as baseline:
                with self.assertRaisesRegex(STOCK.StockRecoveryError, "legacy baseline"):
                    STOCK.arm(run, STOCK.PHYSICAL_ARM)
            baseline.assert_not_called()

    def test_stock_arm_only_cut_never_replays_physical_action_after_time_passes(self) -> None:
        prepared = self.prepared()
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(ROOT_DATA.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**ROOT_DATA.bootstrap.DOWNLOAD_USB, "serial_absent": True},
        }
        armed_at = STOCK.datetime.now(STOCK.timezone.utc) - STOCK.timedelta(seconds=600)
        baseline = {
            "schema": "s20plus_g986n_f1_download_baseline_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "endpoint_count": 0,
            "listing_sha256": "a" * 64,
            "at": (armed_at - STOCK.timedelta(seconds=1)).isoformat(),
        }
        arm = {
            "schema": "s20plus_g986n_native_canary_stock_recovery_arm_intent_v1",
            "version": STOCK.VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "baseline": baseline,
            "baseline_sha256": ROOT_DATA.canonical_sha(baseline),
            "operator_confirmed": True,
            "physical_action": "operator-physical-download-entry",
            "arrival_deadline": (
                armed_at + STOCK.timedelta(seconds=STOCK.ARM_ARRIVAL_WINDOW_SEC)
            ).isoformat(),
            "confirmation_required": STOCK.PHYSICAL_CONFIRM,
            "attempt": 1,
            "replay_permitted": False,
            "at": armed_at.isoformat(),
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-expired-arm-") as temp:
            run = Path(temp)
            (run / "stock-recovery-arm.json").write_text(json.dumps(arm))
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(
                     STOCK.bootstrap,
                     "enumerate_download",
                     return_value=([endpoint["device"]], "b" * 64),
                 ) as enumerate_download, \
                 mock.patch.object(
                     STOCK.bootstrap,
                     "identify_download",
                     return_value=endpoint,
                 ), \
                 mock.patch.object(
                     STOCK.bootstrap,
                     "wait_download_after_baseline",
                     side_effect=AssertionError("physical action must not replay"),
                 ):
                result = STOCK.arm(run, STOCK.PHYSICAL_ARM)
            self.assertIn("PHYSICAL_DOWNLOAD_CONFIRMATION", result["verdict"])
            enumerate_download.assert_called_once()
            self.assertTrue((run / "stock-recovery-arrival.json").is_file())

    def test_stock_confirm_resumes_confirmation_only_cut_once(self) -> None:
        prepared = self.prepared()
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(ROOT_DATA.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**ROOT_DATA.bootstrap.DOWNLOAD_USB, "serial_absent": True},
        }
        confirmation = {
            "schema": "s20plus_g986n_native_canary_stock_recovery_confirmation_v1",
            "version": STOCK.VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "endpoint": endpoint,
            "operator_confirmed": True,
            "confirmation": STOCK.PHYSICAL_CONFIRM,
            "attempt": 1,
            "replay_permitted": False,
            "at": "now",
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-confirm-cut-") as temp:
            run = Path(temp)
            path = run / "stock-recovery-confirmation.json"
            path.write_text(json.dumps(confirmation))
            original = path.read_bytes()
            transfers: list[str] = []
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK, "validate_arm", return_value={"arrival_endpoint": endpoint}), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(STOCK.bootstrap, "identify_download", return_value=endpoint), \
                 mock.patch.object(
                     STOCK,
                     "transfer_stock_once",
                     side_effect=lambda *_args: transfers.append("rollback")
                     or "odin_device_session_failure_or_unknown",
                 ), \
                 mock.patch.object(
                     STOCK,
                     "validate_rollback_outcome",
                     return_value={"schema": "s20plus_g986n_f1_transfer_failure_v1"},
                 ):
                result = STOCK.confirm(run, STOCK.PHYSICAL_CONFIRM)
            self.assertEqual(transfers, ["rollback"])
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(result["stock_recovery_replay_permitted"])

    def test_stock_health_receipt_binds_serial_root_absence_and_boot(self) -> None:
        prepared = self.prepared()
        stderr = b"/system/bin/sh: su: not found\n"
        normalized = b"/system/bin/sh: su: not found"
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "9" * 64,
        }
        final = {
            "healthy": True,
            "root_absent": True,
            "boot_changed": True,
            "boot_id_sha256": "9" * 64,
            "confirmed_boot_id_sha256": "9" * 64,
            "root_probe_rc": 127,
            "root_probe_sha256": hashlib.sha256(normalized).hexdigest(),
            "target": {
                "model": ROOT_DATA.bootstrap.EXPECTED_MODEL,
                "device": ROOT_DATA.bootstrap.EXPECTED_DEVICE,
                "product": ROOT_DATA.bootstrap.EXPECTED_PRODUCT,
                "incremental": ROOT_DATA.bootstrap.EXPECTED_INCREMENTAL,
            },
        }
        evidence = {
            "schema": "s20plus_g986n_native_canary_stock_final_health_v1",
            "version": STOCK.VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "final_health": final,
            "android_identity": identity,
            "root_absence": {
                "returncode": 127,
                "stdout_bytes": 0,
                "stderr_bytes": len(stderr),
                "stdout_sha256": hashlib.sha256(b"").hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                "stdout_hex": "",
                "stderr_hex": stderr.hex(),
                "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
                "root_absent": True,
                "identity_confirmed": True,
            },
            "at": "now",
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-health-") as temp:
            run = Path(temp)
            path = run / STOCK.STOCK_HEALTH_FILE
            path.write_text(json.dumps(evidence))
            self.assertEqual(STOCK.validate_stock_health_evidence(run, prepared), evidence)
            (run / "first-observation.json").write_text(json.dumps({
                "android_identity": {"boot_id_sha256": "9" * 64},
            }))
            with self.assertRaisesRegex(Exception, "reuses an earlier boot"):
                STOCK.validate_stock_health_evidence(run, prepared)
            (run / "first-observation.json").unlink()
            (run / "recovery-disable-intent.json").write_text(json.dumps({
                "source_identity": {"boot_id_sha256": "9" * 64},
            }))
            with self.assertRaisesRegex(Exception, "reuses an earlier boot"):
                STOCK.validate_stock_health_evidence(run, prepared)
            (run / "recovery-disable-intent.json").unlink()
            evidence["android_identity"]["serial_sha256"] = "8" * 64
            path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(Exception, "prepared returned target"):
                STOCK.validate_stock_health_evidence(run, prepared)
            evidence["android_identity"]["serial_sha256"] = "1" * 64
            evidence["final_health"]["root_probe_sha256"] = "a" * 64
            path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(Exception, "identity is mismatched"):
                STOCK.validate_stock_health_evidence(run, prepared)

    def test_stock_root_absence_rejects_permission_denied(self) -> None:
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "9" * 64,
        }
        command = mock.Mock(
            return_value=(127, b"", b"/system/bin/sh: su: permission denied\n")
        )
        with self.assertRaisesRegex(STOCK.StockRecoveryError, "not exact"):
            STOCK.exact_root_absence_evidence(
                command,
                "/usr/bin/adb",
                {"serial": "SERIAL"},
                identity,
            )
        for hostile in (
            b"\n su: not found \t\n\n",
            b" su: not found\n",
            b"su: not found \n",
        ):
            with self.subTest(hostile=hostile), self.assertRaisesRegex(
                STOCK.StockRecoveryError, "raw transcript"
            ):
                STOCK.exact_root_absence_text(b"", hostile)

    def test_stock_rollback_intent_rejects_duplicate_authority_keys(self) -> None:
        prepared = self.prepared()
        endpoint_path = "/dev/bus/usb/003/007"
        payload = (
            '{"schema":"s20plus_g986n_f1_transfer_intent_v1",'
            f'"version":"{ROOT_DATA.bootstrap.VERSION}","kind":"rollback",'
            f'"binding_sha256":"{prepared["binding_sha256"]}",'
            f'"ap_sha256":"{ROOT_DATA.bootstrap.ROLLBACK_SHA256}",'
            f'"endpoint":{{"device":"{endpoint_path}","identity":[1,2,3,4]}},'
            '"attempt":0,"attempt":1,"no_replay":true,"at":"now"}'
        )
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-duplicate-") as temp:
            run = Path(temp)
            (run / "rollback-intent.json").write_text(payload)
            with self.assertRaisesRegex(Exception, "duplicate"):
                STOCK.validate_rollback_intent(run, prepared)

    def test_stock_rollback_result_rejects_duplicate_authority_keys(self) -> None:
        prepared = self.prepared()
        endpoint_path = "/dev/bus/usb/003/007"
        intent = {
            "schema": "s20plus_g986n_f1_transfer_intent_v1",
            "version": ROOT_DATA.bootstrap.VERSION,
            "kind": "rollback",
            "binding_sha256": prepared["binding_sha256"],
            "ap_sha256": ROOT_DATA.bootstrap.ROLLBACK_SHA256,
            "endpoint": {"device": endpoint_path, "identity": [1, 2, 3, 4]},
            "attempt": 1,
            "no_replay": True,
            "at": "now",
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-result-duplicate-") as temp:
            run = Path(temp)
            (run / "rollback-intent.json").write_text(json.dumps(intent))
            (run / "rollback-result.json").write_text(
                '{"schema":"wrong","schema":"s20plus_g986n_f1_transfer_v1"}'
            )
            with self.assertRaisesRegex(Exception, "duplicate"):
                STOCK.validate_rollback_outcome(
                    run,
                    prepared,
                    "odin_transfer_completed",
                )

    def test_finalize_stock_resumes_completed_transfer_without_replaying_odin(self) -> None:
        prepared = self.prepared()
        final = {
            "healthy": True,
            "root_absent": True,
            "boot_changed": True,
            "boot_id_sha256": "9" * 64,
            "confirmed_boot_id_sha256": "9" * 64,
            "root_probe_rc": 127,
            "root_probe_sha256": "a" * 64,
            "target": {
                "model": ROOT_DATA.bootstrap.EXPECTED_MODEL,
                "device": ROOT_DATA.bootstrap.EXPECTED_DEVICE,
                "product": ROOT_DATA.bootstrap.EXPECTED_PRODUCT,
                "incremental": ROOT_DATA.bootstrap.EXPECTED_INCREMENTAL,
            },
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-resume-") as temp:
            run = Path(temp)
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared) as read_prepared, \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(
                     STOCK,
                     "validate_stock_transfer_state",
                     return_value=(
                         "odin_transfer_completed",
                         set(STOCK.STOCK_COMPLETION_FILES),
                         True,
                     ),
                 ), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(STOCK.bootstrap, "final_stock_health", return_value=final), \
                 mock.patch.object(STOCK, "finish_healthy", return_value={"verdict": "RECOVERED"}) as finish, \
                 mock.patch.object(STOCK, "transfer_stock_once") as transfer:
                result = STOCK.finalize_stock(run)
            self.assertEqual(result["verdict"], "RECOVERED")
            read_prepared.assert_called_once_with(
                run,
                input_scope="stock-finalize",
                allow_released_terminal=False,
            )
            transfer.assert_not_called()
            finish.assert_called_once_with(
                run,
                prepared,
                mock.ANY,
                final,
                "odin_transfer_completed",
            )

    def test_stock_terminal_state_must_match_the_durable_odin_journal(self) -> None:
        prepared = self.prepared()
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-terminal-state-") as temp:
            run = Path(temp)
            for name in (
                STOCK.STOCK_HEALTH_FILE,
                "terminal-input.json",
                "terminal-result.json",
            ):
                (run / name).write_text("{}")
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(
                     STOCK.root_data, "read_prepared", return_value=prepared
                 ) as read_prepared, \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(
                     STOCK,
                     "validate_stock_transfer_state",
                     return_value=(
                         "odin_effect_outcome_unproved_after_intent",
                         set(),
                         False,
                     ),
                 ), \
                 mock.patch.object(STOCK, "validate_stock_health_evidence", return_value={}), \
                 mock.patch.object(STOCK.root_data, "read_stock_terminal_input", return_value={
                     "stock_transfer_state": "odin_transfer_completed",
                 }), \
                 mock.patch.object(STOCK, "validate_stock_journal"):
                with self.assertRaisesRegex(
                    STOCK.StockRecoveryError,
                    "contradicts the durable Odin journal",
                ):
                    STOCK.finalize_stock(run)

    def test_stock_terminal_identity_must_match_durable_final_health(self) -> None:
        prepared = self.prepared()
        health_identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "8" * 64,
        }
        terminal_identity = {**health_identity, "boot_id_sha256": "9" * 64}
        evidence = {
            "android_identity": health_identity,
            "root_absence": {"root_absent": True},
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-terminal-identity-") as temp:
            run = Path(temp)
            for name in (
                STOCK.STOCK_HEALTH_FILE,
                "terminal-input.json",
                "terminal-result.json",
            ):
                (run / name).write_text("{}")
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(
                     STOCK.root_data, "read_prepared", return_value=prepared
                 ) as read_prepared, \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(
                     STOCK,
                     "validate_stock_transfer_state",
                     return_value=("odin_transfer_completed", set(), True),
                 ), \
                 mock.patch.object(
                     STOCK,
                     "validate_stock_health_evidence",
                     return_value=evidence,
                 ), \
                 mock.patch.object(
                     STOCK.root_data,
                     "read_stock_terminal_input",
                     return_value={
                         "stock_transfer_state": "odin_transfer_completed",
                         "target_identity": terminal_identity,
                     },
                 ), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(
                     STOCK.root_data,
                     "read_exact_json",
                     return_value={"target_identity": terminal_identity},
                 ), \
                 mock.patch.object(STOCK.root_data, "write_terminal") as publish:
                with self.assertRaisesRegex(
                    STOCK.StockRecoveryError,
                    "differs from durable final health",
                ):
                    STOCK.finalize_stock(run)
            publish.assert_not_called()
            read_prepared.assert_called_once_with(
                run,
                input_scope="stock-terminal-release",
                allow_released_terminal=True,
            )

    def test_stock_terminal_after_released_guard_reemits_exact_result(self) -> None:
        prepared = self.prepared()
        identity = {
            "serial_sha256": prepared["binding"]["target"]["serial_sha256"],
            "topology_sha256": prepared["binding"]["target"]["topology_sha256"],
            "boot_id_sha256": "9" * 64,
        }
        staged = {
            "returncode": 0,
            "stdout_sha256": hashlib.sha256(b"PASS_N1_STAGE_ABSENT\n").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "staged_input_absent": True,
        }
        terminal_absence = {
            "root_absent": True,
            "identity_confirmed": True,
            "normalized_sha256": "c" * 64,
        }
        health_payload = b'{"exact":"stock-health"}\n'
        health_sha256 = hashlib.sha256(health_payload).hexdigest()
        root_absence_sha256 = "d" * 64
        semantics = ROOT_DATA.stock_terminal_semantics("odin_transfer_completed")
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-output-cut-") as temp:
            run = Path(temp) / "run"
            run.mkdir()
            guard = Path(temp) / "active-guard.json"
            ROOT_DATA.durable_create(guard, ROOT_DATA.guard_value(run))
            ROOT_DATA.write_stock_terminal_input(
                run,
                prepared,
                semantics["verdict"],
                identity,
                stock_transfer_state="odin_transfer_completed",
                stock_final_health_sha256=health_sha256,
                stock_root_absence_sha256=root_absence_sha256,
            )
            with mock.patch.object(ROOT_DATA, "guard_path", return_value=guard):
                ROOT_DATA.write_terminal(
                    run,
                    prepared,
                    semantics["verdict"],
                    identity,
                    None,
                    recovery=semantics["recovery"],
                    canary_state_class=semantics["canary_state_class"],
                    stock_final_health_sha256=health_sha256,
                    stock_transfer_state="odin_transfer_completed",
                    stock_precleanup_root_absence_sha256=root_absence_sha256,
                    stock_root_absent=True,
                    stock_terminal_root_absence=terminal_absence,
                    staged_input_absence=staged,
                )
            self.assertFalse(guard.exists())
            terminal_path = run / "terminal-result.json"
            exact_terminal = terminal_path.read_bytes()
            (run / STOCK.STOCK_HEALTH_FILE).write_bytes(health_payload)
            device = mock.Mock(side_effect=AssertionError("device command forbidden"))
            evidence = {
                "android_identity": identity,
                "root_absence": {"root_absent": True},
            }
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(
                     STOCK.root_data, "read_prepared", return_value=prepared
                 ) as read_prepared, \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(
                     STOCK,
                     "validate_stock_transfer_state",
                     return_value=("odin_transfer_completed", set(), True),
                 ), \
                 mock.patch.object(
                     STOCK, "validate_stock_health_evidence", return_value=evidence
                 ), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(
                     STOCK,
                     "validate_root_absence_record",
                     return_value=terminal_absence,
                 ), \
                 mock.patch.object(ROOT_DATA, "guard_path", return_value=guard):
                result = STOCK.finalize_stock(run, device)
            device.assert_not_called()
            self.assertEqual(result["verdict"], semantics["verdict"])
            self.assertEqual(terminal_path.read_bytes(), exact_terminal)
            read_prepared.assert_called_once_with(
                run,
                input_scope="stock-terminal-release",
                allow_released_terminal=True,
            )

    def test_stock_terminal_propagates_complete_cleanup_semantic_failure(self) -> None:
        prepared = self.prepared()
        identity = {
            "serial_sha256": "1" * 64,
            "topology_sha256": ROOT_DATA.bootstrap.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": "9" * 64,
        }
        final = {
            "healthy": True,
            "root_absent": True,
            "boot_changed": True,
            "boot_id_sha256": identity["boot_id_sha256"],
            "confirmed_boot_id_sha256": identity["boot_id_sha256"],
            "root_probe_rc": 127,
            "root_probe_sha256": "a" * 64,
            "target": {
                "model": ROOT_DATA.bootstrap.EXPECTED_MODEL,
                "device": ROOT_DATA.bootstrap.EXPECTED_DEVICE,
                "product": ROOT_DATA.bootstrap.EXPECTED_PRODUCT,
                "incremental": ROOT_DATA.bootstrap.EXPECTED_INCREMENTAL,
            },
        }
        evidence = {
            "android_identity": identity,
            "root_absence": {"root_absent": True},
            "final_health": final,
        }
        order: list[str] = []
        def fail_cleanup(*_args, **_kwargs):
            order.append("cleanup")
            raise ROOT_DATA.RootDataError("cleanup semantic failure")
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-cleanup-") as temp:
            run = Path(temp)
            (run / STOCK.STOCK_HEALTH_FILE).write_text("{}")
            with mock.patch.object(
                STOCK,
                "validate_stock_health_evidence",
                return_value=evidence,
            ), mock.patch.object(
                STOCK.bootstrap,
                "android_health_once",
                return_value=({"serial": "SERIAL"}, {}, identity),
            ), mock.patch.object(
                STOCK.root_data,
                "require_returned_target",
            ), mock.patch.object(
                STOCK,
                "exact_root_absence_evidence",
                return_value={
                    "root_absent": True,
                    "identity_confirmed": True,
                    "normalized_sha256": "d" * 64,
                },
            ), mock.patch.object(
                STOCK.root_data,
                "write_stock_terminal_input",
                side_effect=lambda *_args, **_kwargs: order.append("terminal-input"),
            ), mock.patch.object(
                STOCK.root_data,
                "settle_cleanup_without_replay",
                side_effect=fail_cleanup,
            ) as cleanup, mock.patch.object(
                STOCK.root_data,
                "stage_absence_evidence",
            ) as absence:
                with self.assertRaisesRegex(ROOT_DATA.RootDataError, "semantic failure"):
                    STOCK.finish_healthy(
                        run,
                        prepared,
                        mock.Mock(),
                        final,
                        "odin_transfer_completed",
                    )
            cleanup.assert_called_once()
            absence.assert_not_called()
            self.assertEqual(order, ["terminal-input", "cleanup"])

    def test_uncertain_stock_attempt_terminal_never_claims_stock_boot_provenance(self) -> None:
        uncertain = ROOT_DATA.stock_terminal_semantics(
            "odin_effect_outcome_unproved_after_intent"
        )
        self.assertEqual(uncertain["recovery"], "stock-attempt-unproved")
        self.assertEqual(
            uncertain["canary_state_class"],
            "unobserved-under-root-absent",
        )
        self.assertEqual(
            uncertain["module_terminal"],
            "inactive-under-root-absent-boot",
        )
        self.assertNotIn("TO_STOCK_HEALTHY", uncertain["verdict"])
        completed = ROOT_DATA.stock_terminal_semantics("odin_transfer_completed")
        self.assertEqual(completed["recovery"], "stock")
        self.assertEqual(completed["module_terminal"], "inactive-under-stock-boot")

    def test_policy_documents_activate_only_r1_and_keep_target_isolated(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text()
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text()
        report = (
            ROOT / "docs/reports/S20PLUS_G986N_NATIVE_CANARY_R1_H0_2026-08-15.md"
        ).read_text()
        self.assertIn("## Common R1 Invariants", agents)
        self.assertEqual(agents.count("| Samsung Galaxy S20+ 5G ("), 1)
        self.assertIn(
            "PASS_GO - BINDING - ACTIVE CAPABILITY - NO CURRENT RUN OR DEVICE AUTHORITY",
            contract,
        )
        self.assertIn("PASS_GO - ACTIVE CAPABILITY - NO CURRENT RUN", report)
        self.assertIn(ROOT_DATA.STAGE_DIR, contract)
        self.assertIn(ROOT_DATA.STAGE_DIR, report)
        self.assertIn(ROOT_DATA.STOCK_HANDOFF_CONFIRM, contract)
        self.assertIn(ROOT_DATA.STOCK_HANDOFF_CONFIRM, report)
        self.assertIn("android.googlesource.com/platform/packages/modules/adb", report)

    def test_stock_confirm_has_exactly_one_rollback_and_no_candidate_path(self) -> None:
        prepared = self.prepared()
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(ROOT_DATA.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**ROOT_DATA.bootstrap.DOWNLOAD_USB, "serial_absent": True},
        }
        with tempfile.TemporaryDirectory(prefix="s20plus-r1-stock-") as temp:
            run = Path(temp)
            calls: list[tuple[str, int]] = []
            with mock.patch.object(STOCK, "require_active"), \
                 mock.patch.object(STOCK.root_data, "read_prepared", return_value=prepared), \
                 mock.patch.object(STOCK.root_data, "read_guard"), \
                 mock.patch.object(STOCK, "read_handoff"), \
                 mock.patch.object(STOCK, "validate_arm", return_value={"arrival_endpoint": endpoint}), \
                 mock.patch.object(STOCK, "validate_stock_journal"), \
                 mock.patch.object(ROOT_DATA.bootstrap, "identify_download", return_value=endpoint), \
                 mock.patch.object(STOCK, "validate_confirmation"), \
                 mock.patch.object(STOCK, "transfer_stock_once", side_effect=lambda _r, _e, _b: calls.append(("rollback", 90)) or "odin_device_session_failure_or_unknown"), \
                 mock.patch.object(
                     STOCK,
                     "validate_rollback_outcome",
                     return_value={"schema": "s20plus_g986n_f1_transfer_failure_v1"},
                 ) as outcome_validate:
                result = STOCK.confirm(run, STOCK.PHYSICAL_CONFIRM, lambda *_: (0, b"", b""))
            self.assertEqual(calls, [("rollback", 90)])
            self.assertEqual(
                result["verdict"],
                "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_STOCK_TRANSFER_UNCERTAIN",
            )
            self.assertFalse(result["stock_recovery_replay_permitted"])
            self.assertFalse(any("candidate" in path.name for path in run.iterdir()))
            outcome_validate.assert_called_once_with(
                run,
                prepared,
                "odin_device_session_failure_or_unknown",
            )

    def test_runner_identities_and_policy_documents_are_frozen_after_review(self) -> None:
        self.assertEqual(
            ROOT_DATA.normalized_self_sha256(),
            "83ea1116e17ba1551633d9e4b73008f512b83764957f6bcc9bfd84f79e2479aa",
        )
        self.assertEqual(
            hashlib.sha256(ROOT_DATA.SCRIPT.read_bytes()).hexdigest(),
            "536cb88c67ddd378c511b3e6c659433009b68a5f2d9b767f7e41afdcf6a567a3",
        )
        self.assertEqual(
            STOCK.normalized_self_sha256(),
            "0bb7eab8a87d11758dac20103ede5ac16c5acbdf3cbc3b511cb30842c4f29f2d",
        )
        self.assertEqual(
            hashlib.sha256(STOCK.SCRIPT.read_bytes()).hexdigest(),
            "b029afc3d4a899e4d83304773f8405519bacdb02de742de015a52c97689cc2a6",
        )
        for relative in (
            "GOAL_S20PLUS.md",
            "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md",
            "docs/reports/S20PLUS_G986N_NATIVE_CANARY_R1_H0_2026-08-15.md",
        ):
            text = (ROOT / relative).read_text()
            self.assertIn(
                "536cb88c67ddd378c511b3e6c659433009b68a5f2d9b767f7e41afdcf6a567a3",
                text,
            )
            self.assertIn(
                "b029afc3d4a899e4d83304773f8405519bacdb02de742de015a52c97689cc2a6",
                text,
            )


if __name__ == "__main__":
    unittest.main()
