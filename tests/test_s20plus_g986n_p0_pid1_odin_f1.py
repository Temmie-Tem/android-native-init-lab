from __future__ import annotations

import contextlib
import contextvars
import hashlib
import importlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s20plus_g986n_p0_pid1_odin_f1.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module():
    name = "s20plus_g986n_p0_pid1_odin_f1_tested"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusG986NP0Pid1OdinF1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def endpoint(
        self,
        node: str = "1-2",
        device: str = "/dev/bus/usb/001/007",
        identity: list[int] | None = None,
    ) -> dict[str, object]:
        return {
            "device": device,
            "endpoint_identity": identity or [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(device.encode()).hexdigest(),
            "topology_sha256": hashlib.sha256(
                f"usb:{node}".encode("ascii")
            ).hexdigest(),
            "usb": {**self.module.engine.DOWNLOAD_USB, "serial_absent": True},
        }

    def baseline(self, binding: str = "1" * 64, node: str = "1-2"):
        endpoint = self.endpoint(node)
        observer_baseline = self.module.observer.baseline_value(node)
        return self.module._baseline_value(
            binding, endpoint, node, observer_baseline
        )

    def write_raw_banner(self, run_dir: Path):
        path = run_dir / self.module.P0_RAW_BANNER_NAME
        path.write_bytes(self.module.observer.BANNER)
        path.chmod(0o400)
        return {
            "name": self.module.P0_RAW_BANNER_NAME,
            "size": len(self.module.observer.BANNER),
            "sha256": hashlib.sha256(self.module.observer.BANNER).hexdigest(),
            "mode": "0400",
        }

    def p0_receipt(self, baseline, raw_receipt, endpoint_identity="2" * 64):
        rdev = self.module.observer.digest({"major": 166, "minor": 7})
        return {
            "schema": self.module.P0_RECEIPT_SCHEMA,
            "observer_schema": self.module.observer.SCHEMA,
            "baseline_sha256": self.module.observer.digest(
                baseline["observer_baseline"]
            ),
            "expected_topology_sha256": baseline["observer_baseline"][
                "expected_topology_sha256"
            ],
            "endpoint_identity_sha256": endpoint_identity,
            "descriptor_rdev_sha256": rdev,
            "endpoint_binding_sha256": self.module.observer.digest(
                {
                    "endpoint_identity_sha256": endpoint_identity,
                    "descriptor_rdev_sha256": rdev,
                }
            ),
            "raw_banner": raw_receipt,
            "pid1_exact": True,
            "tty_number_stable": False,
            "exact": True,
            "accepted": True,
        }

    @contextlib.contextmanager
    def live_transaction(self, run_dir: Path | None = None):
        transaction = {
            "entrypoint": "fixture",
            "run_dir": None if run_dir is None else str(run_dir),
        }
        with mock.patch.object(
            self.module, "_require_live_transaction", return_value=transaction
        ):
            yield

    def durable_fixture(self, path: Path, value: dict) -> None:
        path.write_bytes(self.module.engine.canonical_bytes(value))
        path.chmod(0o400)

    @contextlib.contextmanager
    def real_session_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "target-session.lock"
            lock.write_bytes(self.module.registry.SESSION_LOCK_PAYLOAD)
            lock.chmod(0o600)
            with mock.patch.object(
                self.module, "_session_lock_path", return_value=lock
            ):
                yield lock

    def test_plan_is_dormant_and_exactly_boot_only(self):
        with mock.patch.object(
            self.module, "P0_F1_ACTIVE", False
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", False
        ):
            plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["activation_mismatch"])
        self.assertEqual(
            plan["status"], "H0_IMPLEMENTED_REVIEW_PENDING_NOT_ACTIVE"
        )
        self.assertEqual(plan["candidate"]["partition"], "boot")
        self.assertEqual(
            plan["candidate"]["ap_sha256"], self.module.CANDIDATE_AP_SHA256
        )
        self.assertEqual(plan["candidate"]["first_runtime_syscall"], "getpid")
        self.assertEqual(plan["candidate"]["accepted_pid"], 1)
        self.assertTrue(plan["rollback"]["mandatory_after_candidate_intent"])
        self.assertTrue(plan["forbidden"]["candidate_replay"])
        self.assertTrue(plan["forbidden"]["recovery_partition_transfer"])
        self.assertIn("local_recovery_projection", plan)
        self.assertNotIn("global_candidate_claim", plan)
        self.assertEqual(
            plan["target_session_lease"], self.module.registry.SESSION_LOCK_NAME
        )

    def test_host_closure_pins_engine_profile_observer_and_artifacts(self):
        with mock.patch.object(
            self.module, "_validate_live_activation", return_value={}
        ):
            closure = self.module.validate_host_closure()
        self.assertEqual(
            closure["candidate"]["ap"]["sha256"],
            self.module.CANDIDATE_AP_SHA256,
        )
        self.assertEqual(
            closure["rollback"]["ap"]["sha256"],
            self.module.ROLLBACK_AP_SHA256,
        )
        self.assertEqual(
            closure["manifest"]["sha256"], self.module.MANIFEST_SHA256
        )
        self.assertEqual(
            closure["p0_profile"]["p0_observer"]["sha256"],
            self.module.OBSERVER_SHA256,
        )
        self.assertEqual(
            closure["p0_profile"]["p0_owner"]["normalized_sha256"],
            self.module.EXPECTED_REVIEWED_NORMALIZED_SHA256,
        )
        self.assertTrue(
            closure["p0_profile"]["p0_global_registry"][
                "validated_append_only_hash_chain"
            ]
        )
        self.assertTrue(
            closure["p0_profile"]["p0_global_registry"][
                "p0_candidate_absent_from_pinned_legacy_activation"
            ]
        )

    def test_observer_activation_pair_has_one_normalized_identity(self):
        payload = self.module.OBSERVER_PATH.read_bytes()
        atoms = re.findall(
            rb"^OBSERVER_ACTIVE = (False|True)$", payload, flags=re.MULTILINE
        )
        self.assertEqual(len(atoms), 1)
        current_active = atoms[0] == b"True"
        dormant, dormant_count = re.subn(
            rb"^OBSERVER_ACTIVE = (?:False|True)$",
            b"OBSERVER_ACTIVE = False",
            payload,
            flags=re.MULTILINE,
        )
        active, active_count = re.subn(
            rb"^OBSERVER_ACTIVE = (?:False|True)$",
            b"OBSERVER_ACTIVE = True",
            payload,
            flags=re.MULTILINE,
        )
        self.assertEqual((dormant_count, active_count), (1, 1))
        normalized, normalized_count = re.subn(
            rb"^OBSERVER_ACTIVE = (?:False|True)$",
            b"OBSERVER_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
            payload,
            flags=re.MULTILINE,
        )
        active_normalized, active_normalized_count = re.subn(
            rb"^OBSERVER_ACTIVE = (?:False|True)$",
            b"OBSERVER_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
            active,
            flags=re.MULTILINE,
        )
        self.assertEqual((normalized_count, active_normalized_count), (1, 1))
        self.assertEqual(normalized, active_normalized)
        self.assertEqual(
            hashlib.sha256(dormant).hexdigest(),
            self.module.OBSERVER_DORMANT_SHA256,
        )
        self.assertEqual(len(dormant), self.module.OBSERVER_DORMANT_SIZE)
        self.assertEqual(
            hashlib.sha256(active).hexdigest(), self.module.OBSERVER_ACTIVE_SHA256
        )
        self.assertEqual(len(active), self.module.OBSERVER_ACTIVE_SIZE)
        self.assertEqual(
            hashlib.sha256(normalized).hexdigest(),
            self.module.OBSERVER_NORMALIZED_SHA256,
        )
        receipt, observed_active = self.module._activation_normalized_observer_receipt()
        self.assertEqual(observed_active, current_active)
        self.assertEqual(receipt["normalized_sha256"], self.module.OBSERVER_NORMALIZED_SHA256)
        with tempfile.TemporaryDirectory() as temporary:
            active_path = Path(temporary) / self.module.OBSERVER_PATH.name
            active_path.write_bytes(active)
            module_name = "_s20plus_p0_active_observer_pair_test"
            try:
                with mock.patch.object(self.module, "OBSERVER_PATH", active_path):
                    active_receipt, active_atom = (
                        self.module._activation_normalized_observer_receipt()
                    )
                    loaded = self.module._load_activation_normalized_observer(
                        module_name
                    )
                self.assertTrue(active_atom)
                self.assertEqual(
                    active_receipt["sha256"], self.module.OBSERVER_ACTIVE_SHA256
                )
                self.assertTrue(loaded.OBSERVER_ACTIVE)
            finally:
                sys.modules.pop(module_name, None)

    def test_adb_environment_ignores_caller_redirect_and_loader_poison(self):
        socket_spec = self.module.P0_ADB_SERVER_SOCKET
        poison = {
            "ADB_SERVER_SOCKET": "tcp:attacker.invalid:5037",
            "ANDROID_ADB_SERVER_ADDRESS": "attacker.invalid",
            "ANDROID_ADB_SERVER_PORT": "9",
            "ANDROID_SERIAL": "foreign",
            "ADB_VENDOR_KEYS": "/tmp/foreign-key",
            "LD_PRELOAD": "/tmp/foreign.so",
            "LD_LIBRARY_PATH": "/tmp/foreign-libs",
        }
        with mock.patch.dict(os.environ, poison, clear=False):
            environment = self.module._closed_adb_environment(socket_spec)
        self.assertEqual(
            set(environment), {"ADB_SERVER_SOCKET", "HOME", "LANG", "LC_ALL", "PATH"}
        )
        self.assertEqual(environment["ADB_SERVER_SOCKET"], socket_spec)
        self.assertEqual(environment["LANG"], "C")
        self.assertEqual(environment["LC_ALL"], "C")
        self.assertEqual(environment["PATH"], "/usr/bin:/bin")
        self.assertTrue(Path(environment["HOME"]).is_absolute())
        with self.assertRaisesRegex(self.module.P0F1Error, "socket is not fixed"):
            self.module._closed_adb_environment("localabstract:foreign")
        source = SCRIPT.read_text("utf-8")
        self.assertIn("kwargs[\"env\"] = adb_client_environment()", source)
        self.assertNotIn('"server",\n                    "nodaemon"', source)
        self.assertNotIn("stop_adb_server", source)

    def test_adb_client_and_raw_paths_share_one_fixed_server_environment(self):
        calls = []

        class FakeProcess:
            def __init__(self):
                self.pid = 4243
                self.returncode = 0

            def poll(self):
                return self.returncode

            def terminate(self):
                self.returncode = -15

            def kill(self):
                self.returncode = -9

            def wait(self, timeout=None):
                del timeout
                return self.returncode

        def popen(argv, **kwargs):
            calls.append((list(argv), dict(kwargs)))
            if kwargs.get("stdout") is self.module.subprocess.PIPE:
                raise OSError("host-only raw capture probe")
            kwargs["stdout"].write(inventory)
            kwargs["stdout"].flush()
            return FakeProcess()

        serial = "S20SERIAL"
        inventory = (
            "List of devices attached\n"
            f"{serial} device usb:1-2 product:y2qksx model:SM_G986N "
            "device:y2q transport_id:1\n"
        ).encode("ascii")

        def guard_probe(_run_dir):
            rows = self.module.engine.adb_inventory()
            self.assertEqual(rows[0]["serial"], serial)
            handle = self.module.engine.raw_capture.acquire_command(
                [
                    str(self.module.engine.ADB),
                    "-s",
                    serial,
                    "shell",
                    "su",
                    "-c",
                    self.module.engine.shlex.quote(
                        self.module.engine.ROOT_READ_SCRIPT
                    ),
                ],
                run_dir,
                "environment-probe",
                timeout=30,
                stdout_maximum=4096,
                stderr_maximum=4096,
                stdout_name="environment-probe.stdout",
                stderr_name="environment-probe.stderr",
            )
            self.assertEqual(handle.producer_error_type, "OSError")
            raise self.module.P0F1Error("fixed-server-environment-probe-stop")

        poison = {
            "ADB_SERVER_SOCKET": "tcp:attacker.invalid:5037",
            "ANDROID_ADB_SERVER_ADDRESS": "attacker.invalid",
            "LD_PRELOAD": "/tmp/foreign.so",
        }
        with tempfile.TemporaryDirectory(
            dir=self.module.RUN_ROOT, prefix="run-adb-owner-test-"
        ) as temporary, self.real_session_lock(), mock.patch.object(
            self.module, "P0_F1_ACTIVE", True
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", True
        ), mock.patch.object(
            self.module, "_assert_profile_installed"
        ), mock.patch.object(
            self.module, "_validate_live_activation", return_value={}
        ), mock.patch.object(
            self.module.engine, "validate_run_dir", side_effect=lambda path: path
        ), mock.patch.object(
            self.module.engine, "require_guard", side_effect=guard_probe
        ), mock.patch.object(
            self.module.subprocess, "Popen", side_effect=popen
        ), mock.patch.dict(
            os.environ, poison, clear=False
        ):
            run_dir = Path(temporary)
            with self.assertRaisesRegex(
                self.module.P0F1Error, "fixed-server-environment-probe-stop"
            ):
                self.module._read_prepared_for_output(run_dir)
        self.assertEqual(len(calls), 2)
        environments = [kwargs["env"] for _argv, kwargs in calls]
        self.assertEqual(environments[0], environments[1])
        for environment in environments:
            self.assertEqual(
                set(environment),
                {"ADB_SERVER_SOCKET", "HOME", "LANG", "LC_ALL", "PATH"},
            )
            self.assertEqual(
                environment["ADB_SERVER_SOCKET"],
                self.module.P0_ADB_SERVER_SOCKET,
            )

    def test_wrapper_does_not_mutate_the_ordinary_imported_b0_module(self):
        ordinary = importlib.import_module(
            "s20plus_g986n_boot_recovery_canary_b0_f1"
        )
        self.assertIsNot(ordinary, self.module.engine)
        self.assertEqual(
            ordinary.CANDIDATE_AP_SHA256,
            "a8ed52d314e3b0cf5820e99ecd55e97cacdbc8a943d2181886d52d42a1c177fa",
        )
        self.assertEqual(
            ordinary.RUN_ROOT.name,
            "s20plus-g986n-boot-recovery-canary-b0-f1",
        )
        self.assertIsNot(ordinary.raw_capture, self.module.engine.raw_capture)
        self.assertIsNot(ordinary.base, self.module.engine.base)
        self.assertIsNot(ordinary.transport, self.module.engine.transport)
        self.assertEqual(
            ordinary.raw_capture.acquire_command.__name__, "acquire_command"
        )
        self.assertEqual(ordinary.base.bounded_command.__name__, "bounded_command")

    def test_live_cli_stops_before_engine_or_observer_while_dormant(self):
        with mock.patch.object(
            self.module, "P0_F1_ACTIVE", False
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", False
        ), mock.patch.object(
            self.module.engine,
            "prepare",
            side_effect=AssertionError("connected engine reached"),
        ), mock.patch.object(
            self.module.observer,
            "scan_inventory",
            side_effect=AssertionError("live USB observer reached"),
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            rc = self.module.main(["--prepare"])
        self.assertEqual(rc, 3)
        self.assertIn("NOT_ACTIVE", output.getvalue())

    def test_download_node_is_bound_by_bus_dev_and_topology_hash(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction():
            root = Path(temporary)
            node = root / "1-2"
            node.mkdir()
            (node / "busnum").write_text("1\n", encoding="ascii")
            (node / "devnum").write_text("7\n", encoding="ascii")
            self.assertEqual(
                self.module._download_usb_node(self.endpoint(), root), "1-2"
            )
            forged = {**self.endpoint(), "topology_sha256": "0" * 64}
            with self.assertRaisesRegex(
                self.module.P0F1Error, "topology hash"
            ):
                self.module._download_usb_node(forged, root)

    def test_usb_baseline_is_durable_before_global_candidate_claim(self):
        prepared = {
            "binding_sha256": "1" * 64,
            "binding": {"endpoint": self.endpoint()},
        }
        events: list[str] = []
        with mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(Path("/fixture")), mock.patch.object(
            self.module, "_actual_registry_identity",
            return_value={"candidate_key": "2" * 64},
        ), mock.patch.object(
            self.module.engine, "read_json", return_value=prepared
        ), mock.patch.object(
            self.module,
            "_capture_p0_baseline",
            side_effect=lambda *_args: events.append("baseline"),
        ), mock.patch.object(
            self.module,
            "_stage_candidate_transfer_preflight",
            side_effect=lambda *_args: events.append("transfer-preflight"),
        ), mock.patch.object(
            self.module,
            "_claim_global_registry",
            side_effect=lambda *_args: events.append("global-claim"),
        ), mock.patch.object(
            self.module,
            "_ENGINE_CONSUME_CANDIDATE",
            side_effect=lambda *_args: events.append("local-claim") or {"ok": True},
        ), mock.patch.object(
            self.module,
            "_ENGINE_REQUIRE_CANDIDATE_CLAIM",
            side_effect=lambda *_args: events.append("local-validate"),
        ):
            result = self.module.consume_candidate_globally(
                Path("/fixture"), "1" * 64
            )
        self.assertEqual(
            events,
            [
                "baseline",
                "transfer-preflight",
                "global-claim",
                "local-claim",
                "local-validate",
            ],
        )
        self.assertEqual(result, {"ok": True})

    def test_candidate_preflight_accepts_ctime_drift_only_within_same_session(self):
        binding = "1" * 64
        prepared_endpoint = self.endpoint()
        prepared_endpoint["endpoint_identity"] = [1, 2, 3, 100]
        current_endpoint = self.endpoint()
        current_endpoint["endpoint_identity"] = [1, 2, 3, 200]
        dispatch_endpoint = self.endpoint()
        dispatch_endpoint["endpoint_identity"] = [1, 2, 3, 300]
        prepared = {
            "binding_sha256": binding,
            "binding": {"endpoint": prepared_endpoint},
        }
        preflight = {
            "schema": self.module.P0_CANDIDATE_PREFLIGHT_SCHEMA,
            "version": self.module.VERSION,
            "binding_sha256": binding,
            "candidate_ap": {
                "path": str(self.module.CANDIDATE_AP),
                "size": self.module.CANDIDATE_AP_SIZE,
                "sha256": self.module.CANDIDATE_AP_SHA256,
                "member_name": "boot.img.lz4",
                "member_size": self.module.CANDIDATE_MEMBER_SIZE,
                "member_sha256": self.module.CANDIDATE_MEMBER_SHA256,
            },
            "prepared_endpoint_sha256": self.module.engine.digest(
                prepared_endpoint
            ),
            "current_endpoint": current_endpoint,
            "process_cage": {
                "binding_sha256": binding,
                "kind": "candidate",
            },
            "complete_before_global_claim": True,
            "backend_invoked": False,
            "at": "2026-09-02T00:00:00+00:00",
        }

        def read_record(path, _label):
            return prepared if path.name == "prepared.json" else preflight

        with mock.patch.object(
            self.module.engine, "read_json", side_effect=read_record
        ), mock.patch.object(
            self.module, "_candidate_preflight_bound", return_value=(1, {})
        ):
            self.assertEqual(
                self.module._validate_candidate_transfer_preflight(
                    Path("/fixture"), binding, dispatch_endpoint
                ),
                preflight,
            )
            changed_session = json.loads(json.dumps(dispatch_endpoint))
            changed_session["endpoint_identity"][2] = 99
            with self.assertRaisesRegex(
                self.module.P0F1Error, "candidate transfer preflight differs"
            ):
                self.module._validate_candidate_transfer_preflight(
                    Path("/fixture"), binding, changed_session
                )

        fresh_endpoint = self.endpoint()
        fresh_endpoint["endpoint_identity"] = [1, 2, 3, 400]

        def present(path):
            return Path(path).name in {
                "candidate-claim-intent.json",
                self.module.P0_REGISTRY_RECEIPT_NAME,
            }

        with mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(Path("/fixture")), mock.patch.object(
            self.module.os.path, "lexists", side_effect=present
        ), mock.patch.object(
            self.module,
            "_validate_candidate_transfer_preflight",
            return_value=preflight,
        ), mock.patch.object(
            self.module.engine, "identify_download", return_value=fresh_endpoint
        ):
            returned, cage = self.module._P0_PREFLIGHT_ODIN_DISPATCH(
                Path("/fixture"),
                "candidate",
                self.module.CANDIDATE_AP,
                self.module.CANDIDATE_AP_SIZE,
                self.module.CANDIDATE_AP_SHA256,
                dispatch_endpoint,
                binding,
            )
        self.assertEqual(returned, fresh_endpoint)
        self.assertEqual(cage, preflight["process_cage"])

    def test_positive_observation_is_strictly_bound_to_exact_p0_receipt(self):
        binding = "1" * 64
        endpoint = self.endpoint()
        baseline = self.baseline(binding)
        prepared = {"binding_sha256": binding, "binding": {"endpoint": endpoint}}
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            receipt = self.p0_receipt(
                baseline, self.write_raw_banner(run_dir)
            )
            value = {
                "schema": "s20plus_g986n_b0_candidate_observation_v1",
                "version": self.module.VERSION,
                "binding_sha256": binding,
                "environment": self.module.P0_SUCCESS_ENVIRONMENT,
                "transport_authorized": True,
                "claim_verdict": "PROVED",
                "p0_receipt": receipt,
                "at": "2026-09-01T00:00:00+00:00",
                "candidate_replay_permitted": False,
            }
            with mock.patch.object(
                self.module.engine,
                "read_json",
                side_effect=lambda path, _label: prepared
                if path.name == "prepared.json"
                else baseline,
            ):
                self.module.validate_candidate_observation(
                    run_dir, value, binding, "3" * 64
                )
                forged = json.loads(json.dumps(value))
                forged["p0_receipt"]["pid1_exact"] = False
                with self.assertRaises(self.module.P0F1Error):
                    self.module.validate_candidate_observation(
                        run_dir, forged, binding, "3" * 64
                    )
                forged_binding = json.loads(json.dumps(value))
                forged_binding["p0_receipt"]["descriptor_rdev_sha256"] = "9" * 64
                with self.assertRaises(self.module.P0F1Error):
                    self.module.validate_candidate_observation(
                        run_dir, forged_binding, binding, "3" * 64
                    )
                (run_dir / self.module.P0_RAW_BANNER_NAME).chmod(0o600)
                with self.assertRaises(self.module.P0F1Error):
                    self.module.validate_candidate_observation(
                        run_dir, value, binding, "3" * 64
                    )

    def test_raw_banner_publication_is_durable_no_clobber_and_reopened(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction():
            run_dir = Path(temporary)
            receipt = self.module._publish_raw_banner(
                run_dir, self.module.observer.BANNER
            )
            raw, reopened = self.module._read_raw_banner(run_dir)
            self.assertEqual(raw, self.module.observer.BANNER)
            self.assertEqual(reopened, receipt)
            with self.assertRaisesRegex(self.module.P0F1Error, "not fresh"):
                self.module._publish_raw_banner(
                    run_dir, self.module.observer.BANNER
                )

    def test_live_observer_join_accepts_only_same_topology_exact_banner(self):
        binding = "1" * 64
        baseline = self.baseline(binding)
        prepared = {
            "binding_sha256": binding,
            "binding": {"endpoint": self.endpoint()},
        }
        candidate = SimpleNamespace(
            usb_node="1-2", identity_sha256="2" * 64, major=166, minor=7
        )
        inventory = SimpleNamespace(
            exact=(candidate,),
            pending_identity_sha256=(),
            conflicting_identity_sha256=(),
        )
        raw_receipt = {
            "name": self.module.P0_RAW_BANNER_NAME,
            "size": len(self.module.observer.BANNER),
            "sha256": hashlib.sha256(self.module.observer.BANNER).hexdigest(),
            "mode": "0400",
        }
        with mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(Path("/fixture")), mock.patch.object(
            self.module.engine, "read_json", return_value=baseline
        ), mock.patch.object(
            self.module.observer, "scan_inventory", return_value=inventory
        ), mock.patch.object(
            self.module, "_expected_node_from_hashes", return_value="1-2"
        ), mock.patch.object(
            self.module.observer, "select_arrival", return_value=candidate
        ), mock.patch.object(
            self.module.observer, "open_live", return_value=99
        ), mock.patch.object(
            self.module.observer, "verify_descriptor"
        ) as verify, mock.patch.object(
            self.module.observer,
            "read_exact_banner",
            return_value=self.module.observer.BANNER,
        ), mock.patch.object(
            self.module, "_publish_raw_banner", return_value=raw_receipt
        ), mock.patch.object(self.module.os, "close") as close:
            result = self.module._observe_p0(Path("/fixture"), prepared)
        self.assertEqual(result["environment"], self.module.P0_SUCCESS_ENVIRONMENT)
        self.assertEqual(result["claim_verdict"], "PROVED")
        self.assertTrue(result["transport_authorized"])
        self.assertEqual(result["p0_receipt"]["raw_banner"], raw_receipt)
        self.assertEqual(verify.call_count, 2)
        close.assert_called_once_with(99)

    def test_no_proof_observation_cannot_gain_transport_authority(self):
        binding = "1" * 64
        baseline = self.baseline(binding)
        prepared = {
            "binding_sha256": binding,
            "binding": {"endpoint": self.endpoint()},
        }
        value = {
            "schema": "s20plus_g986n_b0_candidate_observation_v1",
            "version": self.module.VERSION,
            "binding_sha256": binding,
            "environment": self.module.P0_NO_PROOF_ENVIRONMENT,
            "transport_authorized": False,
            "claim_verdict": "NO_PROOF",
            "reason_sha256": "4" * 64,
            "at": "2026-09-01T00:00:00+00:00",
            "candidate_replay_permitted": False,
        }
        with mock.patch.object(
            self.module.engine,
            "read_json",
            side_effect=lambda path, _label: prepared
            if path.name == "prepared.json"
            else baseline,
        ):
            self.module.validate_candidate_observation(
                Path("/fixture"), value, binding, "3" * 64
            )
            value["transport_authorized"] = True
            with self.assertRaises(self.module.P0F1Error):
                self.module.validate_candidate_observation(
                    Path("/fixture"), value, binding, "3" * 64
                )

    def test_every_live_facing_helper_is_dormant_before_contact(self):
        prepared = {
            "binding_sha256": "1" * 64,
            "binding": {"endpoint": self.endpoint()},
        }
        operations = (
            lambda: self.module._download_usb_node(self.endpoint()),
            lambda: self.module._capture_p0_baseline(
                Path("/fixture"), "1" * 64, self.endpoint()
            ),
            lambda: self.module.consume_candidate_globally(
                Path("/fixture"), "1" * 64
            ),
            lambda: self.module.candidate_claim_present(),
            lambda: self.module._registry_intent(
                Path("/fixture"), "1" * 64, {}
            ),
            lambda: self.module._registry_receipt(
                Path("/fixture"), "1" * 64, {}
            ),
            lambda: self.module._claim_global_registry(
                Path("/fixture"), "1" * 64, {}
            ),
            lambda: self.module._expected_node_from_hashes({}),
            lambda: self.module._observe_p0(Path("/fixture"), prepared),
            lambda: self.module.observe_candidate(Path("/fixture"), prepared),
            lambda: self.module._publish_raw_banner(
                Path("/fixture"), self.module.observer.BANNER
            ),
            lambda: self.module.engine.adb_inventory(),
            lambda: self.module.engine.transfer_boot(
                Path("/fixture"), "candidate", self.endpoint(), "1" * 64
            ),
            lambda: self.module.engine.payload_free_return(
                Path("/fixture"), self.endpoint()
            ),
            lambda: self.module.engine.prepare_process_cage(
                Path("/fixture"), "candidate", "1" * 64
            ),
            lambda: self.module.observer.scan_inventory(),
            lambda: self.module.observer.open_live(None),
            lambda: self.module._ENGINE_OBSERVE_CANDIDATE(
                Path("/fixture"), prepared
            ),
            lambda: self.module._ENGINE_CONSUME_CANDIDATE(
                Path("/fixture"), "1" * 64
            ),
            lambda: self.module.registry.claim(self.module.ROOT, {}),
            lambda: self.module.engine.prepare(None),
        )
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "P0_F1_ACTIVE", False
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", False
        ), mock.patch.object(
            self.module.observer, "USB_ROOT", Path(temporary)
        ), mock.patch.object(
            self.module.observer, "TTY_ROOT", Path(temporary)
        ), mock.patch.object(
            self.module.observer, "DEV_ROOT", Path(temporary)
        ), mock.patch.object(
            self.module.engine.raw_capture,
            "acquire_command",
            side_effect=AssertionError("raw command reached"),
        ) as raw_command, mock.patch.object(
            self.module.engine.base,
            "bounded_command",
            side_effect=AssertionError("ADB inventory reached"),
        ) as adb_command:
            for operation in operations:
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(self.module.P0F1Error, "not active"):
                        operation()
        raw_command.assert_not_called()
        adb_command.assert_not_called()

    def test_dormant_private_root_owner_cannot_create_or_validate_roots(self):
        with mock.patch.object(
            self.module, "P0_F1_ACTIVE", False
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", False
        ), mock.patch.object(
            self.module,
            "_registry_authority",
            side_effect=AssertionError("registry reached while dormant"),
        ) as registry_check, mock.patch.object(
            Path,
            "mkdir",
            side_effect=AssertionError("private root creation reached"),
        ) as mkdir:
            with self.assertRaisesRegex(self.module.P0F1Error, "not active"):
                self.module.ensure_private_roots()
        registry_check.assert_not_called()
        mkdir.assert_not_called()

    def test_global_registry_duplicate_is_the_prepare_no_replay_boundary(self):
        with mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(), mock.patch.object(
            self.module, "_registry_authority", return_value={"valid": True}
        ), mock.patch.object(
            self.module,
            "_registry_identity",
            return_value={"candidate_key": "2" * 64},
        ), mock.patch.object(
            self.module.registry,
            "active_claim",
            return_value={"candidate_key": "2" * 64},
        ):
            self.assertTrue(self.module.candidate_claim_present())

        ordinary_registry = importlib.import_module(
            "consumed_candidate_registry_v1"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "workspace/private").mkdir(parents=True)
            ordinary_registry.initialize(root)

            def registry_snapshot():
                registry_root = ordinary_registry.registry_root(root)
                return {
                    str(path.relative_to(registry_root)): (
                        path.lstat().st_mode,
                        path.lstat().st_nlink,
                        path.lstat().st_size,
                        path.read_bytes() if path.is_file() else None,
                    )
                    for path in [registry_root, *sorted(registry_root.rglob("*"))]
                }

            before = registry_snapshot()
            with mock.patch.object(
                self.module, "ROOT", root
            ), mock.patch.object(
                self.module, "P0_F1_ACTIVE", True
            ), mock.patch.object(
                self.module.observer, "OBSERVER_ACTIVE", True
            ), mock.patch.object(
                self.module, "_assert_profile_installed"
            ), mock.patch.object(
                self.module, "_validate_live_activation", return_value={}
            ), mock.patch.object(
                self.module, "_registry_authority", return_value={"valid": True}
            ), mock.patch.object(
                self.module.engine,
                "validate_host_closure",
                side_effect=self.module.P0F1Error("post-preflight-stop"),
            ):
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "post-preflight-stop"
                ):
                    self.module.engine.prepare(None)
            self.assertEqual(registry_snapshot(), before)

            staging = ordinary_registry.registry_root(root) / ".head.json.next-1-1"
            staging.write_bytes(b"incomplete-head\n")
            staging.chmod(0o400)
            before_staging_stop = registry_snapshot()
            with mock.patch.object(
                self.module, "ROOT", root
            ), mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(), mock.patch.object(
                self.module, "_registry_authority", return_value={"valid": True}
            ):
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "preflight failed closed"
                ):
                    self.module.candidate_claim_present()
            self.assertEqual(registry_snapshot(), before_staging_stop)

    def test_global_registry_key_binds_target_ap_and_member_across_runs(self):
        first = self.module._registry_identity("run-first", "1" * 64)
        second = self.module._registry_identity("run-second", "2" * 64)
        self.assertEqual(first["candidate_key"], second["candidate_key"])
        self.assertEqual(first["target_key"], second["target_key"])
        self.assertEqual(
            first["candidate_ap_sha256"], self.module.CANDIDATE_AP_SHA256
        )
        self.assertEqual(
            first["boot_member_sha256"], self.module.CANDIDATE_MEMBER_SHA256
        )
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertNotEqual(
            first["approval_binding_sha256"],
            second["approval_binding_sha256"],
        )

    def test_global_claim_cut_recovers_only_local_journal_without_reclaim(self):
        identity = {"candidate_key": "2" * 64}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(Path(temporary)), mock.patch.object(
            self.module, "_actual_registry_identity", return_value=identity
        ), mock.patch.object(
            self.module, "_registry_intent"
        ) as intent, mock.patch.object(
            self.module, "_registry_receipt"
        ) as receipt, mock.patch.object(
            self.module.engine, "claim_path", return_value=Path(temporary) / "missing"
        ), mock.patch.object(
            self.module, "_ENGINE_CONSUME_CANDIDATE", return_value={"local": True}
        ) as local, mock.patch.object(
            self.module,
            "_ENGINE_REQUIRE_CANDIDATE_CLAIM",
            return_value={"validated": True},
        ) as validate:
            result = self.module.require_candidate_claim(
                Path(temporary), "1" * 64
            )
        self.assertEqual(result, {"validated": True})
        intent.assert_called_once()
        receipt.assert_called_once()
        local.assert_called_once()
        validate.assert_called_once()

    def test_existing_baseline_is_freshly_revalidated_before_claim(self):
        binding = "1" * 64
        endpoint = self.endpoint()
        baseline = self.baseline(binding)
        with mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(Path("/fixture")), mock.patch.object(
            self.module.engine, "read_json", return_value=baseline
        ), mock.patch.object(
            self.module.engine, "identify_download", return_value=endpoint
        ) as identify, mock.patch.object(
            self.module.engine, "same_download_session", return_value=True
        ), mock.patch.object(
            self.module, "_download_usb_node", return_value="1-2"
        ), mock.patch.object(
            self.module.observer,
            "capture_baseline",
            return_value=baseline["observer_baseline"],
        ) as capture, mock.patch.object(self.module.os.path, "lexists", return_value=True):
            self.assertEqual(
                self.module._capture_p0_baseline(
                    Path("/fixture"), binding, endpoint
                ),
                baseline,
            )
        identify.assert_called_once_with()
        capture.assert_called_once_with("1-2")

    def test_candidate_dispatch_refuses_missing_or_ambiguous_global_claim(self):
        run_dir = Path("/fixture")

        def present(path):
            return Path(path).name == "candidate-claim-intent.json"

        with mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(run_dir), mock.patch.object(
            self.module.os.path, "lexists", side_effect=present
        ):
            with self.assertRaisesRegex(
                self.module.P0F1Error, "one global claim state"
            ):
                self.module._P0_PREFLIGHT_ODIN_DISPATCH(
                    run_dir,
                    "candidate",
                    self.module.CANDIDATE_AP,
                    self.module.CANDIDATE_AP_SIZE,
                    self.module.CANDIDATE_AP_SHA256,
                    self.endpoint(),
                    "1" * 64,
                )

    def test_active_low_level_surface_still_requires_leased_dispatch(self):
        with mock.patch.object(
            self.module, "require_active"
        ), mock.patch.object(
            self.module.engine.base,
            "bounded_command",
            side_effect=AssertionError("ADB command escaped lease gate"),
        ) as command:
            with self.assertRaisesRegex(self.module.P0F1Error, "lease"):
                self.module.engine.adb_inventory()
            with self.assertRaisesRegex(self.module.P0F1Error, "lease"):
                self.module.observer.open_live(None)
            with self.assertRaisesRegex(self.module.P0F1Error, "lease"):
                self.module._ENGINE_OBSERVE_CANDIDATE(Path("/fixture"), {})
        command.assert_not_called()

    def test_exposed_fake_context_and_valid_descriptor_cannot_forge_lease(self):
        self.assertFalse(hasattr(self.module, "_LIVE_CAPABILITY_TOKEN"))
        self.assertFalse(hasattr(self.module, "_LIVE_TRANSACTION"))
        with self.real_session_lock() as lock:
            descriptor = os.open(lock, os.O_RDWR | os.O_CLOEXEC)
            self.module.fcntl.flock(
                descriptor, self.module.fcntl.LOCK_EX | self.module.fcntl.LOCK_NB
            )
            forged_state = contextvars.ContextVar("forged", default=None)
            forged_capability = object()
            setattr(self.module, "_LIVE_TRANSACTION", forged_state)
            setattr(self.module, "_LIVE_CAPABILITY_TOKEN", forged_capability)
            state_token = forged_state.set(
                {
                    "capability": forged_capability,
                    "lease_fd": descriptor,
                    "lease_identity": self.module._session_lock_identity(descriptor),
                    "run_dir": "/fixture",
                }
            )
            try:
                with self.assertRaisesRegex(self.module.P0F1Error, "lease"):
                    self.module._require_live_transaction()
            finally:
                forged_state.reset(state_token)
                delattr(self.module, "_LIVE_TRANSACTION")
                delattr(self.module, "_LIVE_CAPABILITY_TOKEN")
                self.module.fcntl.flock(descriptor, self.module.fcntl.LOCK_UN)
                os.close(descriptor)

    def test_direct_dependency_effect_primitives_require_real_lease(self):
        operations = (
            lambda: self.module.engine.base.bounded_command(),
            lambda: self.module.engine.base.collect(),
            lambda: self.module.engine.base.allocate_run_dir(),
            lambda: self.module.engine.base.durable_write(),
            lambda: self.module.engine.base.arm_intent(),
            lambda: self.module.engine.base._fsync_dir(),
            lambda: self.module.engine.base.main(),
            lambda: self.module.engine.raw_capture.acquire_command(
                [], Path("/fixture"), "fixture"
            ),
            lambda: self.module.engine.raw_capture.RawCaptureWriter(),
            lambda: self.module.engine.raw_capture.publish_captured_bytes(),
            lambda: self.module.engine.raw_capture.prepare_capture_dir(),
            lambda: self.module.engine.raw_capture._direct_directory(
                Path("/fixture"), create=True
            ),
            lambda: self.module.engine.raw_capture._open_stream(),
            lambda: self.module.engine.raw_capture._write_all(),
            lambda: self.module.engine.raw_capture._durable_create(),
            lambda: self.module.engine.raw_capture._fsync_dir(),
            lambda: self.module.engine.durable_json(),
            lambda: self.module.engine._atomic_publish_at(),
            lambda: self.module.engine.transport.execute_odin_boot_only(),
            lambda: self.module.registry._append(),
            lambda: self.module.registry._write_no_replace(),
            lambda: self.module.registry._write_head(),
            lambda: self.module.observer.read_attr(),
            lambda: self.module.observer.optional_attr(),
            lambda: self.module.engine._write_host_control(),
            lambda: self.module.engine.guard_present(),
            lambda: self.module.engine.require_guard(),
            lambda: self.module.engine._read_guard_at(),
            lambda: self.module.engine._candidate_claim_intent(),
            lambda: self.module.engine._read_small(),
            lambda: self.module.engine._read_bounded_host_file(),
            lambda: self.module.engine._host_boot_id(),
            lambda: self.module.engine._current_cgroup_parent(),
            lambda: self.module.engine._cgroup_identity(),
            lambda: self.module.engine._cgroup_populated(),
        )
        with mock.patch.object(self.module, "require_active"):
            for operation in operations:
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(
                        self.module.P0F1Error,
                        "lease|acquisition capability|forbids raw fixture",
                    ):
                        operation()

    def test_real_session_lease_does_not_grant_direct_registry_mutation(self):
        def guard_probe(received):
            current = self.module._require_live_transaction()
            self.assertEqual(current["entrypoint"], "prepare-output")
            self.assertEqual(current["run_dir"], str(received))
            for operation in (
                lambda: self.module.registry._append(),
                lambda: self.module.registry._write_no_replace(),
                lambda: self.module.registry._write_head(),
            ):
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(
                        self.module.P0F1Error, "internal capability"
                    ):
                        operation()
            with self.assertRaisesRegex(
                self.module.P0F1Error, "writer lock lacks"
            ):
                with self.module.registry._writer(self.module.ROOT):
                    pass
            with self.assertRaisesRegex(
                self.module.P0F1Error, "raw writer lacks"
            ):
                self.module.engine.raw_capture.RawCaptureWriter()
            for operation in (
                lambda: self.module.engine.base.collect(),
                lambda: self.module.engine.transport.execute_odin_boot_only(),
                lambda: self.module.engine.base.bounded_command(
                    ["/bin/true"], 1, 1
                ),
                lambda: self.module.engine.raw_capture.acquire_command(
                    ["/bin/true"],
                    received,
                    "foreign-command",
                    timeout=1,
                    stdout_maximum=1,
                    stderr_maximum=1,
                ),
            ):
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(
                        self.module.P0F1Error, "forbids|outside"
                    ):
                        operation()
            raise self.module.P0F1Error("capability-probe-stop")

        with tempfile.TemporaryDirectory(
            dir=self.module.RUN_ROOT, prefix="run-capability-test-"
        ) as temporary, self.real_session_lock(), mock.patch.object(
            self.module, "P0_F1_ACTIVE", True
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", True
        ), mock.patch.object(
            self.module, "_assert_profile_installed"
        ), mock.patch.object(
            self.module, "_validate_live_activation", return_value={}
        ), mock.patch.object(
            self.module.engine, "require_guard", side_effect=guard_probe
        ):
            with self.assertRaisesRegex(
                self.module.P0F1Error, "capability-probe-stop"
            ):
                self.module._read_prepared_for_output(Path(temporary))
        with self.assertRaisesRegex(self.module.P0F1Error, "lease"):
            self.module._require_live_transaction()

    def test_raw_writer_proxy_closes_and_cannot_outlive_acquisition(self):
        captured = []

        def reject_process(*_args, **_kwargs):
            frame = inspect.currentframe()
            try:
                frame = None if frame is None else frame.f_back
                while frame is not None and "writer" not in frame.f_locals:
                    frame = frame.f_back
                if frame is not None:
                    captured.append(frame.f_locals["writer"])
            finally:
                del frame
            raise OSError("host-only raw-writer lifetime probe")

        with mock.patch.object(
            self.module.engine.raw_capture.subprocess,
            "Popen",
            side_effect=reject_process,
        ), mock.patch.object(
            self.module, "_registry_authority", return_value={}
        ):
            with self.assertRaises(Exception):
                self.module.validate_host_closure()
        self.assertEqual(len(captured), 1)
        writer = captured[0]
        with self.assertRaisesRegex(
            self.module.P0F1Error, "acquisition capability|lifetime|target-session lease"
        ):
            writer.current_sizes()
        for descriptor in (writer._writer.stdout_fd, writer._writer.stderr_fd):
            with self.assertRaises(OSError):
                os.fstat(descriptor)

    def test_capability_issuers_are_not_module_accessible(self):
        for name in (
            "_target_session_transaction",
            "_make_entrypoint_replacement",
            "_registry_mutation",
            "_require_registry_mutation",
            "_REGISTRY_MUTATION_TOKEN",
            "_REGISTRY_MUTATION",
            "_RAW_CAPABILITY_REPLACEMENTS",
        ):
            self.assertFalse(hasattr(self.module, name), name)

    def test_prepare_output_reacquires_lease_and_validates_same_run(self):
        events: list[str] = []
        def validate_run(value):
            current = self.module._require_live_transaction()
            events.append(f"lease:{current['entrypoint']}:{current['run_dir']}")
            events.append(f"validate:{value.name}")
            raise self.module.P0F1Error("prepare-output-probe-stop")

        with tempfile.TemporaryDirectory(
            dir=self.module.RUN_ROOT, prefix="run-prepare-output-test-"
        ) as temporary, self.real_session_lock(), mock.patch.object(
            self.module, "P0_F1_ACTIVE", True
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", True
        ), mock.patch.object(
            self.module, "_assert_profile_installed"
        ), mock.patch.object(
            self.module, "_validate_live_activation", return_value={}
        ), mock.patch.object(
            self.module.engine, "require_guard"
        ), mock.patch.object(
            self.module.engine, "validate_run_dir", side_effect=validate_run
        ):
            run_dir = Path(temporary)
            with self.assertRaisesRegex(
                self.module.P0F1Error, "prepare-output-probe-stop"
            ):
                self.module._read_prepared_for_output(run_dir)
        self.assertEqual(events[0], f"lease:prepare-output:{run_dir}")
        self.assertEqual(events[1], f"validate:{run_dir.name}")
        with self.assertRaisesRegex(self.module.P0F1Error, "lease"):
            self.module._require_live_transaction()

    def test_registry_failure_is_allowed_only_inside_same_run_recovery(self):
        run_dir = self.module.RUN_ROOT / "run-degraded-fixture"
        with mock.patch.object(
            self.module, "P0_F1_ACTIVE", False
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", False
        ), mock.patch.object(
            self.module,
            "_registry_authority",
            side_effect=self.module.P0F1Error("registry unavailable"),
        ), mock.patch.object(
            self.module, "_allow_degraded_registry_recovery"
        ) as degraded, mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(run_dir):
            self.module.ensure_private_roots()
        degraded.assert_called_once_with(run_dir)
        with mock.patch.object(
            self.module, "P0_F1_ACTIVE", False
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", False
        ), mock.patch.object(
            self.module,
            "_registry_authority",
            side_effect=self.module.P0F1Error("registry unavailable"),
        ), mock.patch.object(
            self.module, "_allow_degraded_registry_recovery"
        ) as degraded:
            with self.assertRaisesRegex(self.module.P0F1Error, "not active"):
                self.module.ensure_private_roots()
        degraded.assert_not_called()

    def test_local_claim_boundary_precedes_registry_reopen_on_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / self.module.P0_REGISTRY_INTENT_NAME).write_text(
                "{}\n", encoding="utf-8"
            )
            with mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module, "_allow_degraded_registry_recovery"
            ) as degraded, mock.patch.object(
                self.module,
                "_registry_authority",
                side_effect=AssertionError("registry reopened before local recovery"),
            ):
                self.assertTrue(self.module.candidate_claim_present())
            degraded.assert_called_once_with(run_dir)

    def test_registry_receipt_and_uncertain_state_are_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            for name in (
                self.module.P0_REGISTRY_RECEIPT_NAME,
                self.module.P0_REGISTRY_UNCERTAIN_NAME,
            ):
                (run_dir / name).write_text("{}\n", encoding="utf-8")
            with mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module, "_actual_registry_identity", return_value={}
            ), mock.patch.object(
                self.module, "_registry_intent"
            ), mock.patch.object(
                self.module, "_local_parse_result", return_value=None
            ):
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "contradictory"
                ):
                    self.module.require_candidate_claim(run_dir, "1" * 64)

    def test_degraded_recovery_requires_preexisting_claim_intent(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "runs"
            run_dir = run_root / "run-degraded"
            run_dir.mkdir(parents=True)
            binding = {
                "run_dir": str(run_dir),
                "target": dict(self.module.engine.TARGET),
            }
            binding_sha256 = self.module.engine.digest(binding)
            self.durable_fixture(
                run_dir / "prepared.json",
                {
                    "binding": binding,
                    "binding_sha256": binding_sha256,
                },
            )
            with mock.patch.object(
                self.module, "RUN_ROOT", run_root
            ), mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module.engine, "require_guard"
            ):
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "before the candidate-claim boundary"
                ):
                    self.module._allow_degraded_registry_recovery(run_dir)
                identity = self.module._registry_identity(
                    run_dir.name, binding_sha256
                )
                self.module._registry_intent(run_dir, binding_sha256, identity)
                self.module._allow_degraded_registry_recovery(run_dir)
            uncertain = json.loads(
                (run_dir / self.module.P0_REGISTRY_UNCERTAIN_NAME).read_text()
            )
            self.assertTrue(uncertain["consumed_uncertain"])
            self.assertFalse(uncertain["candidate_replay_permitted"])

    def test_registry_loss_after_local_claim_receipt_keeps_recovery_reachable(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "runs"
            run_dir = run_root / "run-receipt-cut"
            run_dir.mkdir(parents=True)
            binding = {
                "run_dir": str(run_dir),
                "target": dict(self.module.engine.TARGET),
            }
            binding_sha256 = self.module.engine.digest(binding)
            self.durable_fixture(
                run_dir / "prepared.json",
                {"binding": binding, "binding_sha256": binding_sha256},
            )
            (run_dir / self.module.P0_REGISTRY_INTENT_NAME).write_text(
                "{}\n", encoding="utf-8"
            )
            (run_dir / self.module.P0_REGISTRY_RECEIPT_NAME).write_text(
                "{}\n", encoding="utf-8"
            )
            with mock.patch.object(
                self.module, "RUN_ROOT", run_root
            ), mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module.engine, "require_guard"
            ), mock.patch.object(
                self.module,
                "_registry_intent",
                return_value={"durable": True},
            ), mock.patch.object(
                self.module, "_validate_local_registry_receipt"
            ) as validate, mock.patch.object(
                self.module, "_registry_uncertain"
            ) as uncertain:
                self.module._allow_degraded_registry_recovery(run_dir)
            validate.assert_called_once()
            uncertain.assert_not_called()

    def test_local_parse_release_is_append_only_and_cleans_only_projection(self):
        ordinary_registry = importlib.import_module(
            "consumed_candidate_registry_v1"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "workspace/private").mkdir(parents=True)
            ordinary_registry.initialize(root)
            run_root = root / "workspace/private/runs/p0"
            run_dir = run_root / "run-release"
            claim_root = run_root / "consumed-candidates"
            claim_root.mkdir(parents=True)
            run_dir.mkdir()
            binding = "1" * 64
            identity = self.module._registry_identity(run_dir.name, binding)
            global_claim = ordinary_registry.claim(root, identity)
            patches = (
                mock.patch.object(self.module, "ROOT", root),
                mock.patch.object(self.module, "RUN_ROOT", run_root),
                mock.patch.object(self.module, "CLAIM_ROOT", claim_root),
                mock.patch.object(self.module.engine, "RUN_ROOT", run_root),
                mock.patch.object(self.module.engine, "CLAIM_ROOT", claim_root),
                mock.patch.object(self.module, "require_active"),
                mock.patch.object(
                    self.module, "_local_parse_result", return_value={"raw": True}
                ),
                mock.patch.object(
                    self.module,
                    "_minimal_prepared_identity",
                    return_value=(binding, identity),
                ),
                mock.patch.object(
                    self.module.registry, "release", ordinary_registry.release
                ),
            )
            with contextlib.ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                with self.live_transaction(run_dir):
                    self.module._registry_intent(run_dir, binding, identity)
                    self.durable_fixture(
                        run_dir / self.module.P0_REGISTRY_RECEIPT_NAME,
                        {
                            "schema": self.module.P0_REGISTRY_RECEIPT_SCHEMA,
                            "version": self.module.VERSION,
                            "binding_sha256": binding,
                            "candidate_identity": identity,
                            "active_record": global_claim["record"],
                            "candidate_replay_permitted": False,
                        },
                    )
                    _intent, local_claim = self.module._ENGINE_CANDIDATE_CLAIM_INTENT(
                        run_dir, binding
                    )
                    claim_path = self.module.engine.claim_path()
                    claim_path.write_bytes(self.module.engine.canonical_bytes(local_claim))
                    claim_path.chmod(0o400)
                    self.assertTrue(
                        self.module._release_global_claim_after_local_parse(
                            run_dir, binding, identity
                        )
                    )
            self.assertIsNone(
                ordinary_registry.active_claim(root, identity["candidate_key"])
            )
            self.assertEqual(ordinary_registry.history(root)[-1]["event"], "release")
            self.assertFalse(claim_path.exists())
            cleanup = json.loads(
                (run_dir / self.module.P0_LOCAL_PROJECTION_RELEASE_NAME).read_text()
            )
            self.assertTrue(cleanup["projection_absent"])
            self.assertFalse(cleanup["candidate_replay_permitted_for_this_run"])

    def test_unavailable_release_retains_claim_but_does_not_block_recovery(self):
        identity = {name: "2" * 64 for name in self.module._REGISTRY_IDENTITY_FIELDS}
        identity.update(
            {
                "candidate_ap_size": 1,
                "boot_member_size": 1,
                "boot_member_name": "boot.img.lz4",
                "manifest_id": "manifest",
                "run_id": "run",
            }
        )
        claim = {"claim_id": "3" * 64, "record_sha256": "4" * 64}
        with mock.patch.object(
            self.module, "require_active"
        ), self.live_transaction(Path("/fixture")), mock.patch.object(
            self.module, "_local_parse_result", return_value={"raw": True}
        ), mock.patch.object(
            self.module,
            "_validate_local_registry_receipt",
            return_value={"active_record": claim},
        ), mock.patch.object(
            self.module, "_registry_release_intent"
        ), mock.patch.object(
            self.module.os.path, "lexists", return_value=False
        ), mock.patch.object(
            self.module.registry,
            "release",
            side_effect=self.module.registry.RegistryUnavailable("offline"),
        ), mock.patch.object(
            self.module, "_remove_local_recovery_projection"
        ) as cleanup:
            self.assertFalse(
                self.module._release_global_claim_after_local_parse(
                    Path("/fixture"), "1" * 64, identity
                )
            )
        cleanup.assert_not_called()

    def test_local_parse_release_requires_reopened_raw_transfer_result(self):
        value = {
            "classification": "odin_local_parse_failure",
            "receipt": {},
            "host_process_quiescence_proved": True,
        }
        with mock.patch.object(
            self.module.engine, "read_json", return_value=value
        ), mock.patch.object(
            self.module, "_ENGINE_VALIDATE_TRANSFER_OUTCOME"
        ) as validate, mock.patch.object(
            self.module.os.path, "lexists", return_value=True
        ):
            self.assertIs(
                self.module._local_parse_result(Path("/fixture"), "1" * 64),
                value,
            )
        validate.assert_called_once_with(
            Path("/fixture"), value, "candidate", "1" * 64
        )
        forged = {**value, "host_process_quiescence_proved": False}
        with mock.patch.object(
            self.module.engine, "read_json", return_value=forged
        ), mock.patch.object(
            self.module, "_ENGINE_VALIDATE_TRANSFER_OUTCOME"
        ), mock.patch.object(
            self.module.os.path, "lexists", return_value=True
        ):
            with self.assertRaisesRegex(self.module.P0F1Error, "raw quiescent"):
                self.module._local_parse_result(Path("/fixture"), "1" * 64)

    def test_cage_prepare_intent_precedes_allocation_and_bound_receipt(self):
        events: list[str] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            parent = root / "sys/fs/cgroup/p0-fixture"
            run_dir.mkdir()
            parent.mkdir(parents=True)
            cage = parent / f"s20plus-p0-candidate-{'1' * 12}-g0001"
            original_durable = self.module.engine.durable_json

            def durable(path, value):
                if path.name.endswith("-bound.json"):
                    self.assertTrue(cage.is_dir())
                    events.append("allocated")
                events.append(f"durable:{path.name}")
                return original_durable(path, value)

            def identity(path):
                return [1, 2, 3, 4, 5] if path == parent else [6, 7, 8, 9, 10]

            with mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module.engine, "_current_cgroup_parent", return_value=parent
            ), mock.patch.object(
                self.module.engine, "_cgroup_identity", side_effect=identity
            ), mock.patch.object(
                self.module.engine, "_cgroup_populated", return_value=False
            ), mock.patch.object(
                self.module.engine, "_host_boot_id", return_value="boot"
            ), mock.patch.object(
                self.module.engine, "durable_json", side_effect=durable
            ), mock.patch.object(
                self.module, "_validate_cage_bound", return_value={}
            ):
                actual_cage, bound = self.module._prepare_p0_process_cage(
                    run_dir, "candidate", "1" * 64
                )
            self.assertEqual(actual_cage, cage)
            self.assertEqual(bound["cage_identity"], [6, 7, 8, 9, 10])
        self.assertEqual(
            events,
            [
                "durable:p0-candidate-cage-0001-prepare.json",
                "allocated",
                "durable:p0-candidate-cage-0001-bound.json",
            ],
        )

    def test_orphan_cage_is_removed_from_intent_without_backend_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "runs"
            run_dir = run_root / "run-cage"
            parent = Path(temporary) / "cgroup-parent"
            cage = parent / f"s20plus-p0-candidate-{'1' * 12}-g0001"
            cage.mkdir(parents=True)
            run_dir.mkdir(parents=True)
            (run_dir / "prepared.json").write_text("{}", encoding="utf-8")
            (run_dir / "p0-candidate-cage-0001-prepare.json").write_text(
                "{}", encoding="utf-8"
            )
            prepare = {
                "schema": self.module.P0_CAGE_PREPARE_SCHEMA,
                "version": self.module.VERSION,
                "kind": "candidate",
                "generation": 1,
                "binding_sha256": "1" * 64,
                "parent": str(parent),
                "parent_identity": [1, 2, 3, 4, 5],
                "cage": str(cage),
                "host_boot_id_sha256": hashlib.sha256(b"boot").hexdigest(),
                "backend_invoked": False,
                "candidate_replay_permitted": False,
                "at": "now",
            }
            with mock.patch.object(
                self.module, "RUN_ROOT", run_root
            ), mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module.engine, "require_guard"
            ), mock.patch.object(
                self.module,
                "_minimal_prepared_identity",
                return_value=("1" * 64, {}),
            ), mock.patch.object(
                self.module, "_validate_cage_prepare", return_value=prepare
            ), mock.patch.object(
                self.module.engine, "_host_boot_id", return_value="boot"
            ), mock.patch.object(
                self.module.engine,
                "_cgroup_identity",
                return_value=[1, 2, 3, 4, 5],
            ), mock.patch.object(
                self.module.engine, "_cgroup_populated", return_value=False
            ):
                self.module._reconcile_orphan_process_cages(run_dir)
            self.assertFalse(cage.exists())
            result = json.loads(
                (run_dir / "p0-candidate-cage-0001-reconciled.json").read_text()
            )
            self.assertTrue(result["cage_removed"])
            self.assertFalse(result["backend_replayed"])

    def test_reconciled_preintent_cage_allows_next_host_only_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            parent = root / "sys/fs/cgroup/p0"
            run_dir.mkdir()
            parent.mkdir(parents=True)
            first_prepare = {
                "binding_sha256": "1" * 64,
                "parent": str(parent),
            }
            with mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module,
                "_cage_generations",
                side_effect=[
                    {1: {"prepare", "bound", "reconciled"}},
                    {1: {"prepare", "bound", "reconciled"}},
                ],
            ), mock.patch.object(
                self.module,
                "_validate_cage_prepare",
                return_value=first_prepare,
            ), mock.patch.object(
                self.module, "_validate_cage_reconciled"
            ), mock.patch.object(
                self.module.engine, "_current_cgroup_parent", return_value=parent
            ), mock.patch.object(
                self.module.engine,
                "_cgroup_identity",
                side_effect=lambda path: [1, 2, 3, 4, 5]
                if path == parent
                else [6, 7, 8, 9, 10],
            ), mock.patch.object(
                self.module.engine, "_cgroup_populated", return_value=False
            ), mock.patch.object(
                self.module.engine, "_host_boot_id", return_value="boot"
            ), mock.patch.object(
                self.module, "_validate_cage_bound", return_value={}
            ):
                cage, _bound = self.module._prepare_p0_process_cage(
                    run_dir, "rollback", "1" * 64
                )
            self.assertTrue(cage.name.endswith("-g0002"))
            self.assertTrue(
                (run_dir / "p0-rollback-cage-0002-prepare.json").exists()
            )
            self.assertTrue(
                (run_dir / "p0-rollback-cage-0002-bound.json").exists()
            )

    def test_abort_return_cage_uses_its_own_endpoint_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            binding = "a" * 64
            parent = Path("/sys/fs/cgroup/p0-abort-fixture")
            prepare = {
                "schema": self.module.P0_CAGE_PREPARE_SCHEMA,
                "version": self.module.VERSION,
                "kind": "abort-return",
                "generation": 1,
                "binding_sha256": binding,
                "parent": str(parent),
                "parent_identity": [1, 2, 3, 4, 5],
                "cage": str(
                    parent / f"s20plus-p0-abort-return-{binding[:12]}-g0001"
                ),
                "host_boot_id_sha256": "b" * 64,
                "backend_invoked": False,
                "candidate_replay_permitted": False,
                "at": "now",
            }
            self.durable_fixture(
                run_dir / "p0-abort-return-cage-0001-prepare.json", prepare
            )
            self.assertEqual(
                self.module._validate_cage_prepare(
                    run_dir, "abort-return", 1, None
                ),
                prepare,
            )
            with self.assertRaisesRegex(self.module.P0F1Error, "differs"):
                self.module._validate_cage_prepare(
                    run_dir, "abort-return", 1, "c" * 64
                )

    def test_cage_prepare_rejects_parent_traversal_and_incomplete_bound_identity(self):
        binding = "a" * 64
        parent = Path("/sys/fs/cgroup/p0/../foreign")
        prepare = {
            "schema": self.module.P0_CAGE_PREPARE_SCHEMA,
            "version": self.module.VERSION,
            "kind": "candidate",
            "generation": 1,
            "binding_sha256": binding,
            "parent": str(parent),
            "parent_identity": [1, 2, 3, 4, 5],
            "cage": str(parent / f"s20plus-p0-candidate-{binding[:12]}-g0001"),
            "host_boot_id_sha256": "b" * 64,
            "backend_invoked": False,
            "candidate_replay_permitted": False,
            "at": "now",
        }
        with mock.patch.object(
            self.module.engine, "read_json", return_value=prepare
        ):
            with self.assertRaisesRegex(self.module.P0F1Error, "prepare intent"):
                self.module._validate_cage_prepare(
                    Path("/fixture"), "candidate", 1, binding
                )

        canonical_parent = Path("/sys/fs/cgroup/p0")
        canonical_prepare = {
            **prepare,
            "parent": str(canonical_parent),
            "cage": str(
                canonical_parent
                / f"s20plus-p0-candidate-{binding[:12]}-g0001"
            ),
        }
        incomplete = {
            "schema": self.module.P0_CAGE_BOUND_SCHEMA,
            "version": self.module.VERSION,
            "kind": "candidate",
            "generation": 1,
            "binding_sha256": binding,
            "prepare_sha256": self.module.engine.digest(canonical_prepare),
            "process_cage": {
                "schema": "s20plus_g986n_b0_process_cage_binding_v1",
                "version": self.module.VERSION,
                "kind": "candidate",
                "binding_sha256": binding,
                "parent": str(canonical_parent),
                "parent_identity": [1, 2, 3, 4, 5],
                "cage": canonical_prepare["cage"],
                "host_boot_id_sha256": "b" * 64,
                "empty_before_backend": True,
                "at": "now",
            },
            "backend_invoked": False,
            "candidate_replay_permitted": False,
        }
        with mock.patch.object(
            self.module.engine, "read_json", return_value=incomplete
        ):
            with self.assertRaisesRegex(self.module.P0F1Error, "bound receipt"):
                self.module._validate_cage_bound(
                    Path("/fixture"), "candidate", 1, canonical_prepare
                )

    def test_inherited_b0_validation_accepts_exact_p0_cage_generations(self):
        for kind in ("candidate", "rollback", "abort-return"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                run_dir = Path(temporary)
                binding = hashlib.sha256(kind.encode()).hexdigest()
                parent = Path("/sys/fs/cgroup/p0-validation")
                cage = parent / (
                    f"s20plus-p0-{kind}-{binding[:12]}-g0001"
                )
                prepare = {
                    "schema": self.module.P0_CAGE_PREPARE_SCHEMA,
                    "version": self.module.VERSION,
                    "kind": kind,
                    "generation": 1,
                    "binding_sha256": binding,
                    "parent": str(parent),
                    "parent_identity": [1, 2, 3, 4, 5],
                    "cage": str(cage),
                    "host_boot_id_sha256": "a" * 64,
                    "backend_invoked": False,
                    "candidate_replay_permitted": False,
                    "at": "now",
                }
                process_cage = {
                    "schema": "s20plus_g986n_b0_process_cage_binding_v1",
                    "version": self.module.VERSION,
                    "kind": kind,
                    "binding_sha256": binding,
                    "parent": str(parent),
                    "parent_identity": [1, 2, 3, 4, 5],
                    "cage": str(cage),
                    "host_boot_id_sha256": "a" * 64,
                    "cage_identity": [6, 7, 8, 9, 10],
                    "empty_before_backend": True,
                    "at": "now",
                }
                bound = {
                    "schema": self.module.P0_CAGE_BOUND_SCHEMA,
                    "version": self.module.VERSION,
                    "kind": kind,
                    "generation": 1,
                    "binding_sha256": binding,
                    "prepare_sha256": self.module.engine.digest(prepare),
                    "process_cage": process_cage,
                    "backend_invoked": False,
                    "candidate_replay_permitted": False,
                }
                quiescence = {
                    "schema": "s20plus_g986n_b0_process_cage_quiescent_v1",
                    "version": self.module.VERSION,
                    "kind": kind,
                    "binding_sha256": binding,
                    "cage_binding_sha256": self.module.engine.digest(process_cage),
                    "kill_requested": False,
                    "cage_absent_before_check": False,
                    "empty_and_removed": True,
                    "at": "now",
                }
                self.durable_fixture(
                    run_dir / f"p0-{kind}-cage-0001-prepare.json", prepare
                )
                self.durable_fixture(
                    run_dir / f"p0-{kind}-cage-0001-bound.json", bound
                )
                self.durable_fixture(
                    run_dir / f"{kind}-cage-quiescent.json", quiescence
                )
                self.assertEqual(
                    self.module.engine._validate_process_cage_binding(
                        process_cage, kind, binding
                    ),
                    process_cage,
                )
                self.assertEqual(
                    self.module.engine._validate_process_cage_quiescence(
                        run_dir,
                        {entry.name for entry in run_dir.iterdir()},
                        kind,
                        binding,
                        process_cage,
                    ),
                    quiescence,
                )

    def test_reconciled_generation_cannot_hide_effect_cage_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "runs"
            run_dir = run_root / "run-mismatch"
            run_dir.mkdir(parents=True)
            (run_dir / "candidate-intent.json").write_text("{}\n", encoding="utf-8")
            prepare = {
                "binding_sha256": "1" * 64,
                "cage": "/sys/fs/cgroup/p0/exact",
            }
            exact_bound = {
                "binding_sha256": "1" * 64,
                "kind": "candidate",
                "cage": "/sys/fs/cgroup/p0/exact",
            }
            effect = {
                "binding_sha256": "1" * 64,
                "process_cage": {**exact_bound, "cage": "/sys/fs/cgroup/p0/foreign"},
                "backend_invoked": True,
            }
            with mock.patch.object(
                self.module, "RUN_ROOT", run_root
            ), mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module.engine, "require_guard"
            ), mock.patch.object(
                self.module, "_cage_generations", return_value={1: {"prepare", "bound", "reconciled"}}
            ), mock.patch.object(
                self.module, "_validate_cage_prepare", return_value=prepare
            ), mock.patch.object(
                self.module,
                "_validate_cage_bound",
                return_value={"process_cage": exact_bound},
            ), mock.patch.object(
                self.module, "_validate_cage_reconciled"
            ), mock.patch.object(
                self.module.engine, "read_json", return_value=effect
            ):
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "exactly one cage generation"
                ):
                    self.module._reconcile_orphan_process_cages(run_dir)

    def test_listing_cage_cut_is_quiesced_and_reconciled_without_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "runs"
            run_dir = run_root / "run-list"
            parent = Path(temporary) / "cgroup"
            cage = parent / "s20plus-p0-odin-listing-aaaaaaaaaaaa-g0001"
            cage.mkdir(parents=True)
            run_dir.mkdir(parents=True)
            for name in (
                "p0-odin-listing-cage-0001-prepare.json",
                "p0-odin-listing-cage-0001-bound.json",
                "p0-odin-listing-0001-intent.json",
            ):
                (run_dir / name).write_text("{}\n", encoding="utf-8")
            prepare = {
                "binding_sha256": "a" * 64,
                "parent": str(parent),
                "parent_identity": [1, 2, 3, 4, 5],
                "cage": str(cage),
                "host_boot_id_sha256": hashlib.sha256(b"boot").hexdigest(),
            }
            bound = {
                "binding_sha256": "a" * 64,
                "kind": "odin-listing",
                "cage": str(cage),
                "cage_identity": [6, 7, 8, 9, 10],
            }
            effect = {
                "binding_sha256": "a" * 64,
                "process_cage": bound,
            }
            with mock.patch.object(
                self.module, "RUN_ROOT", run_root
            ), mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module.engine, "require_guard"
            ), mock.patch.object(
                self.module, "_validate_cage_prepare", return_value=prepare
            ), mock.patch.object(
                self.module,
                "_validate_cage_bound",
                return_value={"process_cage": bound},
            ), mock.patch.object(
                self.module, "_validate_odin_listing_intent", return_value=effect
            ), mock.patch.object(
                self.module.engine,
                "read_json",
                side_effect=lambda path, _label: effect
                if path.name.endswith("-intent.json")
                else {},
            ), mock.patch.object(
                self.module.engine, "_host_boot_id", return_value="boot"
            ), mock.patch.object(
                self.module.engine,
                "_cgroup_identity",
                side_effect=lambda path: [1, 2, 3, 4, 5]
                if path == parent
                else [6, 7, 8, 9, 10],
            ), mock.patch.object(
                self.module.engine,
                "_cgroup_populated",
                side_effect=[True, False],
            ), mock.patch.object(
                self.module.engine, "_write_host_control"
            ) as kill:
                self.module._reconcile_orphan_process_cages(run_dir)
            kill.assert_called_once()
            self.assertFalse(cage.exists())
            self.assertTrue(
                (run_dir / "p0-odin-listing-cage-0001-reconciled.json").exists()
            )

    def test_reconciled_listing_intent_without_result_remains_cage_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary) / "runs"
            run_dir = run_root / "run-list-reconciled"
            run_dir.mkdir(parents=True)
            for name in (
                "p0-odin-listing-cage-0001-prepare.json",
                "p0-odin-listing-cage-0001-bound.json",
                "p0-odin-listing-cage-0001-reconciled.json",
                "p0-odin-listing-0001-intent.json",
            ):
                (run_dir / name).write_text("{}\n", encoding="utf-8")
            prepare = {
                "binding_sha256": "a" * 64,
                "cage": "/sys/fs/cgroup/p0/list-exact",
            }
            bound = {
                "binding_sha256": "a" * 64,
                "kind": "odin-listing",
                "cage": "/sys/fs/cgroup/p0/list-exact",
            }
            effect = {
                "binding_sha256": "a" * 64,
                "process_cage": {**bound, "cage": "/sys/fs/cgroup/p0/list-foreign"},
            }
            with mock.patch.object(
                self.module, "RUN_ROOT", run_root
            ), mock.patch.object(
                self.module, "require_active"
            ), self.live_transaction(run_dir), mock.patch.object(
                self.module.engine, "require_guard"
            ), mock.patch.object(
                self.module,
                "_cage_generations",
                side_effect=lambda _run, kind: {1: {"prepare", "bound", "reconciled"}}
                if kind == "odin-listing"
                else {},
            ), mock.patch.object(
                self.module, "_validate_cage_prepare", return_value=prepare
            ), mock.patch.object(
                self.module,
                "_validate_cage_bound",
                return_value={"process_cage": bound},
            ), mock.patch.object(
                self.module, "_validate_cage_reconciled"
            ), mock.patch.object(
                self.module.engine, "read_json", return_value=effect
            ):
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "reconciled Odin-listing intent"
                ):
                    self.module._reconcile_orphan_process_cages(run_dir)

    def test_inherited_b0_environment_cannot_prove_p0(self):
        forged = {
            "environment": "resident-android",
            "claim_verdict": "PROVED",
        }
        with mock.patch.object(
            self.module, "_ENGINE_VALIDATE_CANDIDATE_OBSERVATION"
        ) as inherited:
            with self.assertRaisesRegex(self.module.P0F1Error, "only exact P0"):
                self.module.validate_candidate_observation(
                    Path("/fixture"), forged, "1" * 64, "2" * 64
                )
        inherited.assert_called_once()

    def test_profile_lineage_rejects_b0_recovery_predecessors(self):
        self.assertEqual(
            self.module.engine.RECOVERY_PREDECESSOR_NORMALIZED_SHA256,
            frozenset(),
        )
        self.assertEqual(self.module.engine.RUN_NODE_NAMES, self.module.P0_RUN_NODE_NAMES)

    def test_partial_activation_is_reported_inactive(self):
        with mock.patch.object(
            self.module, "P0_F1_ACTIVE", True
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", False
        ):
            plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertTrue(plan["activation_mismatch"])
        self.assertEqual(plan["status"], "ACTIVATION_MISMATCH_NOT_ACTIVE")

    def test_boolean_activation_without_exact_record_is_not_live(self):
        with mock.patch.object(
            self.module, "P0_F1_ACTIVE", True
        ), mock.patch.object(
            self.module.engine, "B0_F1_ACTIVE", True
        ), mock.patch.object(
            self.module.observer, "OBSERVER_ACTIVE", True
        ), mock.patch.object(
            self.module,
            "_validate_live_activation",
            side_effect=self.module.P0F1Error("activation absent"),
        ):
            plan = self.module.render_plan()
            self.assertFalse(plan["active"])
            self.assertFalse(plan["live_authority"])
            self.assertEqual(
                plan["status"], "ACTIVATION_RECORD_INVALID_NOT_ACTIVE"
            )
            with self.assertRaisesRegex(self.module.P0F1Error, "activation"):
                self.module.require_active()

    def test_live_activation_requires_dedicated_zero_finding_record(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module,
            "P0_ZERO_FINDING_REVIEW",
            Path(temporary) / "missing-zero-review.json",
        ):
            with self.assertRaisesRegex(self.module.P0F1Error, "zero-finding"):
                self.module._live_activation_expected()

    def test_dormant_documents_cannot_satisfy_active_semantics(self):
        with mock.patch.object(
            self.module,
            "_current_document_semantics",
            return_value=self.module.P0_DORMANT_DOCUMENT_SEMANTICS,
        ):
            with self.assertRaisesRegex(
                self.module.P0F1Error, "active document semantics"
            ):
                self.module._active_document_semantics()

    def test_active_semantics_are_anchored_to_authoritative_status_fields(self):
        paths = self.module.P0_POLICY_FILES
        active = {
            paths["repository_contract"]: (
                "# AGENTS\n\n| Target | Current state | Binding target contract | Binding live process |\n"
                "|---|---|---|---|\n| "
                + self.module.P0_REGISTRY_TARGET_CELL
                + " | "
                + self.module.P0_REGISTRY_GOAL_CELL
                + " | "
                + self.module.P0_REGISTRY_CONTRACT_CELL
                + " | "
                + self.module.P0_ACTIVE_REGISTRY_PROCESS_CELL
                + " |\n"
            ),
            paths["target_contract"]: (
                "# Contract\n\n## P0 PID1 ACM Odin boot-only F1\n\n"
                + self.module.P0_ACTIVE_CONTRACT_MARKER
                + "\n\nBody\n"
            ),
            paths["current_goal"]: (
                "# Goal\n\n## Current P0 PID1 Odin F1 state\n\n"
                + self.module.P0_ACTIVE_GOAL_MARKER
                + "\n\nBody\n"
            ),
            paths["qualification_report"]: (
                "# S20+ G986N P0 PID1 Odin F1 owner H0 implementation\n\n"
                "Date: 2026-09-01\n\n"
                "Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`\n\n"
                "Tier: H0 only\n\n"
                + self.module.P0_ACTIVE_REPORT_MARKER
                + "\n\n## Outcome\n"
            ),
        }

        def read_active(path, *_args, **_kwargs):
            return active[path]

        with mock.patch.object(
            Path, "read_text", autospec=True, side_effect=read_active
        ):
            self.assertEqual(
                self.module._active_document_semantics(),
                {
                    "repository_contract": self.module.P0_ACTIVE_REGISTRY_PROCESS_CELL,
                    "target_contract": self.module.P0_ACTIVE_CONTRACT_MARKER,
                    "current_goal": self.module.P0_ACTIVE_GOAL_MARKER,
                    "qualification_report": self.module.P0_ACTIVE_REPORT_MARKER,
                },
            )

        misplaced = dict(active)
        misplaced[paths["repository_contract"]] = (
            active[paths["repository_contract"]].replace(
                self.module.P0_ACTIVE_REGISTRY_PROCESS_CELL,
                self.module.P0_DORMANT_REGISTRY_PROCESS_CELL,
            )
            + "\n<!-- "
            + self.module.P0_ACTIVE_REGISTRY_MARKER
            + " -->\n"
        )
        misplaced[paths["target_contract"]] = (
            active[paths["target_contract"]].replace(
                self.module.P0_ACTIVE_CONTRACT_MARKER,
                self.module.P0_DORMANT_CONTRACT_MARKER,
            )
            + "\n## History\n"
            + self.module.P0_ACTIVE_CONTRACT_MARKER
            + "\n"
        )
        misplaced[paths["current_goal"]] = (
            active[paths["current_goal"]].replace(
                self.module.P0_ACTIVE_GOAL_MARKER,
                self.module.P0_DORMANT_GOAL_MARKER,
            )
            + "\n<!-- "
            + self.module.P0_ACTIVE_GOAL_MARKER
            + " -->\n"
        )
        misplaced[paths["qualification_report"]] = (
            active[paths["qualification_report"]].replace(
                self.module.P0_ACTIVE_REPORT_MARKER,
                self.module.P0_DORMANT_REPORT_MARKER,
            )
            + "\n## History\n"
            + self.module.P0_ACTIVE_REPORT_MARKER
            + "\n"
        )

        def read_misplaced(path, *_args, **_kwargs):
            return misplaced[path]

        with mock.patch.object(
            Path, "read_text", autospec=True, side_effect=read_misplaced
        ):
            with self.assertRaisesRegex(
                self.module.P0F1Error, "active document semantics"
            ):
                self.module._active_document_semantics()

        hidden_variants = []
        hidden = dict(active)
        hidden[paths["target_contract"]] = (
            "# Contract\n\n<!--\n## P0 PID1 ACM Odin boot-only F1\n\n"
            + self.module.P0_ACTIVE_CONTRACT_MARKER
            + "\n-->\n\n## Other\n"
        )
        hidden_variants.append(hidden)
        hidden = dict(active)
        hidden[paths["current_goal"]] = (
            "# Goal\n\n```text\n## Current P0 PID1 Odin F1 state\n\n"
            + self.module.P0_ACTIVE_GOAL_MARKER
            + "\n```\n\n## Other\n"
        )
        hidden_variants.append(hidden)
        hidden = dict(active)
        hidden[paths["qualification_report"]] = (
            "# S20+ G986N P0 PID1 Odin F1 owner H0 implementation\n\n"
            "Date: 2026-09-01\n\n"
            "Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`\n\n"
            "Tier: H0 only\n\n<!-- "
            + self.module.P0_ACTIVE_REPORT_MARKER
            + " -->\n\n## Outcome\n"
        )
        hidden_variants.append(hidden)
        hidden = dict(active)
        hidden[paths["repository_contract"]] = (
            "# AGENTS\n\n| Target | Current state | Binding target contract | Binding live process |\n"
            "|---|---|---|---|\n```text\n"
            + active[paths["repository_contract"]].splitlines()[4]
            + "\n```\n"
        )
        hidden_variants.append(hidden)
        for hidden_documents in hidden_variants:
            with self.subTest(hidden_document=hidden_documents), mock.patch.object(
                Path,
                "read_text",
                autospec=True,
                side_effect=lambda path, *_args, **_kwargs: hidden_documents[path],
            ):
                with self.assertRaises(self.module.P0F1Error):
                    self.module._active_document_semantics()

    def test_activation_document_normalization_allows_only_exact_status_changes(self):
        paths = self.module.P0_POLICY_FILES
        current = {
            paths[name]: paths[name].read_text("utf-8")
            for name in self.module.P0_DORMANT_DOCUMENT_SEMANTICS
        }
        semantics = self.module._current_document_semantics(
            {
                name: current[paths[name]]
                for name in self.module.P0_DORMANT_DOCUMENT_SEMANTICS
            }
        )
        dormant = dict(current)
        active = dict(current)
        for name in self.module.P0_DORMANT_DOCUMENT_SEMANTICS:
            path = paths[name]
            before = self.module.P0_DORMANT_DOCUMENT_SEMANTICS[name]
            after = self.module.P0_ACTIVE_DOCUMENT_SEMANTICS[name]
            actual = semantics[name]
            self.assertIn(actual, {before, after})

            def marker(status: str) -> str:
                if name == "repository_contract":
                    return (
                        f"| {self.module.P0_REGISTRY_TARGET_CELL} | "
                        f"{self.module.P0_REGISTRY_GOAL_CELL} | "
                        f"{self.module.P0_REGISTRY_CONTRACT_CELL} | {status} |"
                    )
                if name == "target_contract":
                    return f"\n## P0 PID1 ACM Odin boot-only F1\n\n{status}\n"
                if name == "current_goal":
                    return f"\n## Current P0 PID1 Odin F1 state\n\n{status}\n"
                return f"\nTier: H0 only\n\n{status}\n\n## Outcome\n"

            actual_marker = marker(actual)
            self.assertEqual(current[path].count(actual_marker), 1)
            dormant[path] = current[path].replace(actual_marker, marker(before), 1)
            active[path] = current[path].replace(actual_marker, marker(after), 1)

        def normalized(documents):
            with mock.patch.object(
                Path,
                "read_text",
                autospec=True,
                side_effect=lambda path, *_args, **_kwargs: documents[path],
            ):
                return self.module._activation_document_normalized_receipts()

        self.assertEqual(normalized(dormant), normalized(active))
        changed = dict(active)
        changed[paths["target_contract"]] += "\nUnreviewed activation text.\n"
        self.assertNotEqual(normalized(dormant), normalized(changed))

    def test_zero_finding_review_rejects_every_normalized_or_unchanged_policy_drift(self):
        current = self.module._reviewed_closure_current()
        reviewed = json.loads(json.dumps(current))
        value = {
            "schema": self.module.P0_ZERO_FINDING_REVIEW_SCHEMA,
            "version": self.module.VERSION,
            "target": dict(self.module.engine.TARGET),
            "reviewed_closure": reviewed,
            "reviewed_closure_sha256": self.module.engine.digest(reviewed),
            "independent_review": {
                "verdict": "PASS_GO",
                "high": 0,
                "medium": 0,
                "low": 0,
            },
            "reviewer_device_contacts": 0,
            "reviewer_writes": 0,
            "tests_run": {"focused": 1},
            "at": "fixture",
        }
        receipt = {"path": "fixture", "size": 1, "sha256": "1" * 64}
        mutations = []
        for name in self.module.P0_DORMANT_DOCUMENT_SEMANTICS:
            changed = json.loads(json.dumps(current))
            changed["activation_documents_normalized"][name][
                "normalized_sha256"
            ] = "f" * 64
            mutations.append((f"normalized-{name}", changed))
        for name in self.module.P0_UNCHANGED_POLICY_NAMES:
            changed = json.loads(json.dumps(current))
            changed["policy"][name]["sha256"] = "e" * 64
            mutations.append((f"unchanged-{name}", changed))
        for label, changed in mutations:
            with self.subTest(policy=label), mock.patch.object(
                self.module,
                "_read_private_activation_record",
                return_value=(value, receipt),
            ), mock.patch.object(
                self.module, "_reviewed_closure_current", return_value=changed
            ), mock.patch.object(
                self.module, "_validate_review_test_results"
            ):
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "reviewed dormant closure drifted"
                ):
                    self.module._validate_zero_finding_review()

    def test_zero_finding_review_requires_exact_raw_test_results(self):
        reviewed_sha256 = "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            log_root = Path(temporary) / "review-tests-v1"
            log_root.mkdir(mode=0o700)
            log_root.chmod(0o700)
            with mock.patch.object(
                self.module, "P0_REVIEW_TEST_LOG_ROOT", log_root
            ):
                suites = {}
                for name, requirement in sorted(
                    self.module.P0_REVIEW_TEST_REQUIREMENTS.items()
                ):
                    terminal = (
                        "OK"
                        if requirement["skipped"] == 0
                        else f"OK (skipped={requirement['skipped']})"
                    )
                    path = log_root / requirement["log_name"]
                    path.write_text(
                        f"Ran {requirement['tests']} tests in 0.001s\n\n{terminal}\n",
                        encoding="utf-8",
                    )
                    path.chmod(0o400)
                    os.utime(path, ns=(1, path.stat().st_mtime_ns))
                    receipt, _text = self.module._read_review_test_log(
                        log_root, path, name
                    )
                    suites[name] = {
                        "runner": "python3 -m unittest",
                        "modules": requirement["modules"],
                        "tests": requirement["tests"],
                        "skipped": requirement["skipped"],
                        "failures": 0,
                        "errors": 0,
                        "result": "OK",
                        "raw_receipt": receipt,
                    }
                value = {
                    "schema": self.module.P0_REVIEW_TEST_RESULTS_SCHEMA,
                    "reviewed_closure_sha256": reviewed_sha256,
                    "suites": suites,
                }
                self.module._validate_review_test_results(
                    value, reviewed_sha256, log_root
                )
                broken = json.loads(json.dumps(value))
                broken["suites"]["focused_owner"]["tests"] = 1
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "review test suite differs"
                ):
                    self.module._validate_review_test_results(
                        broken, reviewed_sha256, log_root
                    )
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "review test results shape differs"
                ):
                    self.module._validate_review_test_results(
                        {"focused": 1}, reviewed_sha256, log_root
                    )

    def test_mechanical_activation_requires_allowlist_and_normalized_closure(self):
        reviewed = self.module._reviewed_closure_current()
        zero_value = {"reviewed_closure": reviewed}
        zero_receipt = {"path": "zero", "size": 1, "sha256": "1" * 64}
        after = {
            name: {
                "path": str(path),
                "size": index + 1,
                "sha256": f"{index + 1:064x}",
            }
            for index, (name, path) in enumerate(
                sorted(self.module.P0_ACTIVATION_CHANGE_FILES.items())
            )
        }
        before = {
            "owner": reviewed["owner"],
            "observer": reviewed["observer"],
            **{
                name: reviewed["policy"][name]
                for name in self.module.P0_DORMANT_DOCUMENT_SEMANTICS
            },
        }
        activation_diff = {
            name: {"before": before[name], "after": after[name]}
            for name in sorted(self.module.P0_ACTIVATION_CHANGE_FILES)
        }
        normalized = {
            "owner": reviewed["owner_normalized_sha256"],
            "observer": reviewed["observer_normalized_sha256"],
            "documents": reviewed["activation_documents_normalized"],
        }
        active_test_closure = self.module._active_test_closure(
            reviewed, activation_diff, normalized
        )
        active_tests_run = {"active": True}
        transitions = {
            "owner_active": [False, True],
            "observer_active": [False, True],
            "repository_registry": [
                self.module.P0_DORMANT_REGISTRY_PROCESS_CELL,
                self.module.P0_ACTIVE_REGISTRY_PROCESS_CELL,
            ],
            "target_contract": [
                self.module.P0_DORMANT_CONTRACT_MARKER,
                self.module.P0_ACTIVE_CONTRACT_MARKER,
            ],
            "current_goal": [
                self.module.P0_DORMANT_GOAL_MARKER,
                self.module.P0_ACTIVE_GOAL_MARKER,
            ],
            "qualification_report": [
                self.module.P0_DORMANT_REPORT_MARKER,
                self.module.P0_ACTIVE_REPORT_MARKER,
            ],
        }
        value = {
            "schema": self.module.P0_MECHANICAL_ACTIVATION_SCHEMA,
            "version": self.module.VERSION,
            "target": dict(self.module.engine.TARGET),
            "zero_finding_review": zero_receipt,
            "activation_diff": activation_diff,
            "activation_diff_sha256": self.module.engine.digest(activation_diff),
            "allowlisted_changes": self.module.P0_ACTIVATION_CHANGE_RULES,
            "normalized_closure": normalized,
            "normalized_closure_sha256": self.module.engine.digest(normalized),
            "active_test_closure": active_test_closure,
            "active_test_closure_sha256": self.module.engine.digest(
                active_test_closure
            ),
            "active_tests_run": active_tests_run,
            "semantic_transitions": transitions,
            "independent_review": {
                "verdict": "PASS_GO",
                "high": 0,
                "medium": 0,
                "low": 0,
            },
            "reviewer_device_contacts": 0,
            "reviewer_writes": 0,
            "at": "fixture",
        }
        receipt = {"path": "mechanical", "size": 1, "sha256": "2" * 64}

        def receipt_for(path, _label):
            for name, expected_path in self.module.P0_ACTIVATION_CHANGE_FILES.items():
                if path == expected_path:
                    return after[name]
            raise AssertionError(path)

        patches = (
            mock.patch.object(
                self.module,
                "_read_private_activation_record",
                return_value=(value, receipt),
            ),
            mock.patch.object(
                self.module, "_current_file_receipt", side_effect=receipt_for
            ),
            mock.patch.object(
                self.module,
                "_active_document_semantics",
                return_value=self.module.P0_ACTIVE_DOCUMENT_SEMANTICS,
            ),
        )
        with patches[0], patches[1], patches[2], mock.patch.object(
            self.module, "_validate_review_test_results"
        ) as validate_active_tests:
            self.assertEqual(
                self.module._validate_mechanical_activation(zero_value, zero_receipt)[1],
                receipt,
            )
        validate_active_tests.assert_called_once_with(
            active_tests_run,
            self.module.engine.digest(active_test_closure),
            self.module.P0_ACTIVE_REVIEW_TEST_LOG_ROOT,
        )
        broken = dict(value)
        broken["allowlisted_changes"] = {}
        with mock.patch.object(
            self.module,
            "_read_private_activation_record",
            return_value=(broken, receipt),
        ), mock.patch.object(
            self.module, "_current_file_receipt", side_effect=receipt_for
        ), mock.patch.object(
            self.module,
            "_active_document_semantics",
            return_value=self.module.P0_ACTIVE_DOCUMENT_SEMANTICS,
        ):
            with self.assertRaisesRegex(
                self.module.P0F1Error, "mechanical activation record differs"
            ):
                self.module._validate_mechanical_activation(zero_value, zero_receipt)

    def test_live_activation_expected_binds_goal_review_and_mechanical_record(self):
        zero_value = {"reviewed_closure": {}}
        zero_receipt = {
            "path": str(self.module.P0_ZERO_FINDING_REVIEW),
            "size": 1,
            "sha256": "1" * 64,
        }
        mechanical_receipt = {
            "path": str(self.module.P0_MECHANICAL_ACTIVATION),
            "size": 1,
            "sha256": "2" * 64,
        }
        with mock.patch.object(
            self.module,
            "_validate_zero_finding_review",
            return_value=(zero_value, zero_receipt),
        ), mock.patch.object(
            self.module,
            "_validate_mechanical_activation",
            return_value=({}, mechanical_receipt),
        ) as mechanical:
            expected = self.module._live_activation_expected()
        self.assertEqual(expected["independent_review"], {
            "verdict": "PASS_GO",
            "high": 0,
            "medium": 0,
            "low": 0,
        })
        self.assertEqual(
            set(expected["closure"]["policy"]), set(self.module.P0_POLICY_FILES)
        )
        self.assertIn("current_goal", expected["closure"]["policy"])
        self.assertEqual(
            set(expected["closure"]["tests"]), set(self.module.P0_TEST_FILES)
        )
        self.assertEqual(
            expected["closure"]["zero_finding_review"], zero_receipt
        )
        self.assertEqual(
            expected["closure"]["mechanical_activation"], mechanical_receipt
        )
        self.assertTrue(expected["mechanical_activation_reviewed"])
        mechanical.assert_called_once_with(zero_value, zero_receipt)

    def test_candidate_claim_and_observation_require_p0_baseline_node(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "_ENGINE_VALIDATE_NAMESPACE", return_value=None
        ):
            run_dir = Path(temporary)
            (run_dir / "candidate-claim-intent.json").write_text(
                "{}\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(self.module.P0F1Error, "lacks"):
                self.module.validate_namespace(run_dir)

    def test_physical_rebind_accepts_only_address_drift_on_same_topology(self):
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        self.assertTrue(
            self.module._physical_rebind_continuity(prior, current)
        )
        same = dict(prior)
        self.assertFalse(self.module._physical_rebind_continuity(prior, same))
        wrong_bus = self.endpoint(
            "2-2", "/dev/bus/usb/003/034", [7, 1987, 48545, 20]
        )
        self.assertFalse(
            self.module._physical_rebind_continuity(prior, wrong_bus)
        )
        wrong_profile = dict(current)
        wrong_profile["usb"] = {**current["usb"], "product": "foreign"}
        self.assertFalse(
            self.module._physical_rebind_continuity(prior, wrong_profile)
        )

    def test_existing_confirmation_requires_separate_rebind_arm_mode(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module,
                "_ENGINE_ARM_PHYSICAL_ROLLBACK",
            ) as original_arm, mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(
                self.module.engine, "rollback_from_arrival"
            ) as rollback:
                result = self.module._arm_physical_rollback_with_rebind(run_dir)
            self.assertEqual(
                result["verdict"],
                "PHYSICAL_DOWNLOAD_REENUM_BOUND_AWAITING_CONFIRMATION",
            )
            self.assertTrue(
                result["confirmation"].startswith(
                    self.module.PHYSICAL_REBIND_CONFIRM_PREFIX
                )
            )
            self.assertTrue(
                (run_dir / self.module.P0_PHYSICAL_REBIND_ARM_NAME).exists()
            )
            rollback.assert_not_called()
            original_arm.assert_not_called()

    def test_rebind_confirmation_accepts_ctime_drift_and_dispatches_rollback(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        confirmed = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 30]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ):
                armed = self.module._arm_physical_rollback_rebind(
                    run_dir, prepared
                )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine,
                "identify_download",
                return_value=confirmed,
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(
                self.module.engine,
                "rollback_from_arrival",
                return_value={"verdict": "rollback-dispatched"},
            ) as rollback:
                result = self.module._confirm_physical_rollback_with_rebind(
                    run_dir, armed["confirmation"]
                )
            self.assertEqual(result["verdict"], "rollback-dispatched")
            self.assertTrue(
                (run_dir / self.module.P0_PHYSICAL_REBIND_CONFIRM_NAME).exists()
            )
            self.assertTrue(
                (run_dir / self.module.P0_PHYSICAL_REBIND_ARRIVAL_NAME).exists()
            )
            arrival = self.module._validate_physical_rebind_arrival(
                run_dir,
                prepared,
                self.module._validate_physical_rebind_arm(run_dir, prepared),
                self.module._validate_physical_rebind_confirmation(
                    run_dir,
                    prepared,
                    self.module._validate_physical_rebind_arm(run_dir, prepared),
                ),
            )
            self.assertEqual(arrival["endpoint"], confirmed)
            rollback.assert_called_once_with(run_dir, prepared, confirmed)

    def test_rebind_wrong_confirmation_cannot_reach_rollback(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ):
                self.module._arm_physical_rollback_rebind(run_dir, prepared)
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine, "identify_download"
            ) as identify, mock.patch.object(
                self.module.engine, "rollback_from_arrival"
            ) as rollback:
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "confirmation differs"
                ):
                    self.module._confirm_physical_rollback_with_rebind(
                        run_dir, "wrong"
                    )
            identify.assert_not_called()
            rollback.assert_not_called()
            self.assertFalse(
                (run_dir / self.module.P0_PHYSICAL_REBIND_CONFIRM_NAME).exists()
            )

    def test_expired_rebind_confirmation_stops_before_endpoint_read(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(self.module.time, "time", return_value=100):
                armed = self.module._arm_physical_rollback_rebind(
                    run_dir, prepared
                )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine, "identify_download"
            ) as identify, mock.patch.object(
                self.module.engine, "rollback_from_arrival"
            ) as rollback, mock.patch.object(
                self.module.time,
                "time",
                return_value=100
                + self.module.engine.PHYSICAL_ARRIVAL_LIFETIME_SECONDS
                + 1,
            ):
                with self.assertRaisesRegex(self.module.P0F1Error, "expired"):
                    self.module._confirm_physical_rollback_with_rebind(
                        run_dir, armed["confirmation"]
                    )
            identify.assert_not_called()
            rollback.assert_not_called()

    def test_rebound_endpoint_drift_stops_before_confirmation_intent(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        later = self.endpoint(
            "2-2", "/dev/bus/usb/002/035", [7, 1990, 48546, 30]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ):
                armed = self.module._arm_physical_rollback_rebind(
                    run_dir, prepared
                )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine, "identify_download", return_value=later
            ), mock.patch.object(
                self.module.engine, "rollback_from_arrival"
            ) as rollback:
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "rebound Download endpoint changed"
                ):
                    self.module._confirm_physical_rollback_with_rebind(
                        run_dir, armed["confirmation"]
                    )
            rollback.assert_not_called()
            self.assertFalse(
                (run_dir / self.module.P0_PHYSICAL_REBIND_CONFIRM_NAME).exists()
            )

    def test_confirmed_rebind_reporting_cut_remains_recoverable_after_expiry(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(self.module.time, "time", return_value=100):
                armed = self.module._arm_physical_rollback_rebind(
                    run_dir, prepared
                )
            arm = self.module._validate_physical_rebind_arm(run_dir, prepared)
            self.durable_fixture(
                run_dir / self.module.P0_PHYSICAL_REBIND_CONFIRM_NAME,
                {
                    "schema": self.module.P0_PHYSICAL_REBIND_CONFIRM_SCHEMA,
                    "version": self.module.VERSION,
                    "binding_sha256": prepared["binding_sha256"],
                    "arm_sha256": self.module.engine.digest(arm),
                    "confirmation_token_sha256": hashlib.sha256(
                        armed["confirmation"].encode()
                    ).hexdigest(),
                    "confirmed_unix": 101,
                    "no_replay": True,
                    "at": "fixture",
                },
            )
            after_expiry = (
                100 + self.module.engine.PHYSICAL_ARRIVAL_LIFETIME_SECONDS + 1
            )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine,
                "identify_download",
                side_effect=[current, current],
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(
                self.module.engine,
                "rollback_from_arrival",
                return_value={"verdict": "reporting-cut-resumed"},
            ) as rollback, mock.patch.object(
                self.module.time, "time", return_value=after_expiry
            ):
                result = self.module._confirm_physical_rollback_with_rebind(
                    run_dir, armed["confirmation"]
                )
            self.assertEqual(result["verdict"], "reporting-cut-resumed")
            rollback.assert_called_once_with(run_dir, prepared, current)

    def test_rebind_arm_reemits_same_token_without_refreshing_expiry(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(self.module.time, "time", return_value=100):
                first = self.module._arm_physical_rollback_rebind(
                    run_dir, prepared
                )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module, "_ENGINE_ARM_PHYSICAL_ROLLBACK"
            ) as original_arm, mock.patch.object(
                self.module.engine, "identify_download"
            ) as identify, mock.patch.object(
                self.module.time, "time", return_value=101
            ):
                repeated = self.module._arm_physical_rollback_with_rebind(run_dir)
            self.assertEqual(repeated["confirmation"], first["confirmation"])
            original_arm.assert_not_called()
            identify.assert_not_called()
            expired = 100 + self.module.engine.PHYSICAL_ARRIVAL_LIFETIME_SECONDS + 1
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.time, "time", return_value=expired
            ):
                with self.assertRaisesRegex(self.module.P0F1Error, "arm expired"):
                    self.module._arm_physical_rollback_with_rebind(run_dir)

    def test_consumed_original_confirmation_cannot_bypass_rebind_arm(self):
        prepared = {"binding_sha256": "1" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module, "_ENGINE_CONFIRM_PHYSICAL_ROLLBACK"
            ) as original_confirm, mock.patch.object(
                self.module.engine, "identify_download"
            ) as identify:
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "must be armed"
                ):
                    self.module._confirm_physical_rollback_with_rebind(
                        run_dir, "consumed-original-confirmation"
                    )
            original_confirm.assert_not_called()
            identify.assert_not_called()

    def test_detected_post_confirmation_drift_is_durably_invalidated(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        later = self.endpoint(
            "2-2", "/dev/bus/usb/002/035", [7, 1990, 48546, 30]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ):
                armed = self.module._arm_physical_rollback_rebind(
                    run_dir, prepared
                )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine,
                "identify_download",
                side_effect=[current, later],
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(
                self.module.engine, "rollback_from_arrival"
            ) as rollback:
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "changed after confirmation"
                ):
                    self.module._confirm_physical_rollback_with_rebind(
                        run_dir, armed["confirmation"]
                    )
            rollback.assert_not_called()
            miss = self.module._validate_physical_rebind_miss(
                run_dir,
                prepared,
                self.module._validate_physical_rebind_arm(run_dir, prepared),
                self.module._validate_physical_rebind_confirmation(
                    run_dir,
                    prepared,
                    self.module._validate_physical_rebind_arm(run_dir, prepared),
                ),
            )
            self.assertEqual(miss["reason"], "endpoint-changed-after-confirmation")
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine, "identify_download"
            ) as identify, mock.patch.object(
                self.module.engine, "rollback_from_arrival"
            ) as rollback:
                with self.assertRaisesRegex(self.module.P0F1Error, "invalidated"):
                    self.module._confirm_physical_rollback_with_rebind(
                        run_dir, armed["confirmation"]
                    )
            identify.assert_not_called()
            rollback.assert_not_called()

    def test_all_rollback_preintent_identity_failures_are_durably_invalidated(self):
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        for message in sorted(self.module.ROLLBACK_PREINTENT_IDENTITY_ERRORS):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                run_dir = Path(temporary)
                self.durable_fixture(
                    run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
                )
                self.durable_fixture(
                    run_dir / "physical-confirmation-intent.json",
                    {"consumed": True},
                )
                with mock.patch.object(
                    self.module.engine, "identify_download", return_value=current
                ), mock.patch.object(
                    self.module.engine,
                    "durable_json",
                    side_effect=self.durable_fixture,
                ):
                    armed = self.module._arm_physical_rollback_rebind(
                        run_dir, prepared
                    )
                with mock.patch.object(
                    self.module, "require_active"
                ), mock.patch.object(
                    self.module.engine, "read_prepared", return_value=prepared
                ), mock.patch.object(
                    self.module.engine, "require_all_transfer_processes_quiescent"
                ), mock.patch.object(
                    self.module.engine, "identify_download", return_value=current
                ), mock.patch.object(
                    self.module.engine,
                    "durable_json",
                    side_effect=self.durable_fixture,
                ), mock.patch.object(
                    self.module.engine,
                    "rollback_from_arrival",
                    side_effect=self.module.engine.B0F1Error(message),
                ):
                    with self.assertRaisesRegex(
                        self.module.engine.B0F1Error, re.escape(message)
                    ):
                        self.module._confirm_physical_rollback_with_rebind(
                            run_dir, armed["confirmation"]
                        )
                arm = self.module._validate_physical_rebind_arm(run_dir, prepared)
                confirmation = self.module._validate_physical_rebind_confirmation(
                    run_dir, prepared, arm
                )
                miss = self.module._validate_physical_rebind_miss(
                    run_dir, prepared, arm, confirmation
                )
                self.assertEqual(
                    miss["reason"], "identity-unproved-before-rollback-intent"
                )
                self.assertFalse((run_dir / "rollback-intent.json").exists())
                with mock.patch.object(
                    self.module, "require_active"
                ), mock.patch.object(
                    self.module.engine, "read_prepared", return_value=prepared
                ), mock.patch.object(
                    self.module.engine, "require_all_transfer_processes_quiescent"
                ), mock.patch.object(
                    self.module.engine, "identify_download"
                ) as identify, mock.patch.object(
                    self.module.engine, "rollback_from_arrival"
                ) as rollback:
                    with self.assertRaisesRegex(
                        self.module.P0F1Error, "invalidated"
                    ):
                        self.module._confirm_physical_rollback_with_rebind(
                            run_dir, armed["confirmation"]
                        )
                identify.assert_not_called()
                rollback.assert_not_called()

    def test_final_exact_identity_oserror_is_durably_invalidated(self):
        guarded_reads = (
            (
                self.module._guarded_identify_download(
                    mock.Mock(side_effect=FileNotFoundError("gone"))
                ),
                (),
            ),
            (
                self.module._guarded_endpoint_stat(
                    mock.Mock(side_effect=FileNotFoundError("gone"))
                ),
                ("/dev/bus/usb/002/034",),
            ),
        )
        for guarded_read, arguments in guarded_reads:
            with self.subTest(read=guarded_read.__name__), mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(self.module, "_require_live_transaction"):
                with self.assertRaisesRegex(
                    self.module.engine.B0F1Error, "identity is unproved"
                ):
                    guarded_read(*arguments)
        prepared = {"binding_sha256": "1" * 64}
        prior = self.endpoint(
            "2-2", "/dev/bus/usb/002/032", [7, 1963, 48543, 10]
        )
        current = self.endpoint(
            "2-2", "/dev/bus/usb/002/034", [7, 1987, 48545, 20]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(
                run_dir / "physical-rollback-arrival.json", {"endpoint": prior}
            )
            self.durable_fixture(
                run_dir / "physical-confirmation-intent.json", {"consumed": True}
            )
            with mock.patch.object(
                self.module.engine, "identify_download", return_value=current
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ):
                armed = self.module._arm_physical_rollback_rebind(
                    run_dir, prepared
                )
            with mock.patch.object(
                self.module, "require_active"
            ), mock.patch.object(
                self.module.engine, "read_prepared", return_value=prepared
            ), mock.patch.object(
                self.module.engine, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                self.module.engine,
                "identify_download",
                side_effect=[current, current, FileNotFoundError("gone")],
            ), mock.patch.object(
                self.module.engine,
                "durable_json",
                side_effect=self.durable_fixture,
            ), mock.patch.object(
                self.module.engine, "rollback_from_arrival"
            ) as rollback:
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "unproved before rollback intent"
                ):
                    self.module._confirm_physical_rollback_with_rebind(
                        run_dir, armed["confirmation"]
                    )
            rollback.assert_not_called()
            arm = self.module._validate_physical_rebind_arm(run_dir, prepared)
            confirmation = self.module._validate_physical_rebind_confirmation(
                run_dir, prepared, arm
            )
            miss = self.module._validate_physical_rebind_miss(
                run_dir, prepared, arm, confirmation
            )
            self.assertEqual(
                miss["reason"], "identity-unproved-before-rollback-intent"
            )

    def test_rebind_arm_refuses_an_existing_rollback_intent(self):
        prepared = {"binding_sha256": "1" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            self.durable_fixture(run_dir / "rollback-intent.json", {"attempt": 1})
            with mock.patch.object(
                self.module.engine, "identify_download"
            ) as identify:
                with self.assertRaisesRegex(
                    self.module.P0F1Error, "already attempted"
                ):
                    self.module._arm_physical_rollback_rebind(run_dir, prepared)
            identify.assert_not_called()

    def test_terminal_pass_requires_transfer_pid1_and_rollback_together(self):
        self.assertEqual(
            self.module.derive_terminal_verdict(
                "odin_transfer_completed", "PROVED", True
            ),
            ("PROVED_P0_PID1_ACM_RETURNED_RESIDENT_HEALTHY", True),
        )
        for candidate, claim, rollback in (
            ("odin_transfer_completed", "NO_PROOF", True),
            ("odin_device_session_failure_or_unknown", "PROVED", True),
            ("odin_transfer_completed", "PROVED", False),
        ):
            verdict, passed = self.module.derive_terminal_verdict(
                candidate, claim, rollback
            )
            self.assertEqual(verdict, "NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY")
            self.assertFalse(passed)

    def test_wrapper_has_no_direct_device_command_or_transfer_primitive(self):
        source = SCRIPT.read_text("utf-8")
        self.assertEqual(source.count("subprocess.Popen("), 1)
        self.assertIn("env=dict(environment)", source)
        self.assertIn("adb_client_environment()", source)
        self.assertNotIn("server nodaemon", source)
        self.assertNotIn("/usr/bin/adb", source)
        self.assertNotIn("/usr/bin/odin4", source)
        self.assertNotIn("dd if=", source)
        self.assertNotIn("/dev/block/", source)

    def test_repository_policy_matches_p0_odin_activation_state(self):
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text("utf-8")
        goal = (ROOT / "GOAL_S20PLUS.md").read_text("utf-8")
        agents = (ROOT / "AGENTS.md").read_text("utf-8")
        self.assertIn("## P0 PID1 ACM Odin boot-only F1", contract)
        if self.module.P0_F1_ACTIVE:
            self.assertIn(self.module.P0_ACTIVE_CONTRACT_MARKER, contract)
            self.assertIn(self.module.P0_ACTIVE_GOAL_MARKER, goal)
            self.assertIn(self.module.P0_ACTIVE_REGISTRY_PROCESS_CELL, agents)
            self.assertTrue(self.module.observer.OBSERVER_ACTIVE)
        else:
            self.assertIn(self.module.P0_DORMANT_CONTRACT_MARKER, contract)
            self.assertIn(self.module.P0_DORMANT_GOAL_MARKER, goal)
            self.assertIn(self.module.P0_DORMANT_REGISTRY_PROCESS_CELL, agents)
            self.assertFalse(self.module.observer.OBSERVER_ACTIVE)


if __name__ == "__main__":
    unittest.main()
