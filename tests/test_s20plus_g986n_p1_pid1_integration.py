"""Offline integration of the P1 profile with the existing F1 shell.

Only hardware/process boundaries and activation records are replaced in lifecycle
fixtures. The real installed engine state machine, session lock, evidence
producer/consumer and durable file helpers are exercised. No test invokes ADB.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tests import test_s20plus_g986n_p1_pid1_witness_v1 as witness

P = witness.OWNER
R = P._runtime
E = P.engine
O = witness.OBSERVER
C = witness.EVIDENCE
ROOT = witness.ROOT
SCRIPTS = witness.REVALIDATION


def load_raw():
    path = SCRIPTS / "device_action_raw_capture_v1.py"
    spec = importlib.util.spec_from_file_location("_p1_offline_raw", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RAW = load_raw()
SERIAL = "S20_FIXTURE_ONLY"
SERIAL_HASH = hashlib.sha256(SERIAL.encode()).hexdigest()
TOPOLOGY = "usb:1-2"
TOPOLOGY_HASH = hashlib.sha256(TOPOLOGY.encode()).hexdigest()
BOOT = witness.BOOT_ID
BOOT_HASH = hashlib.sha256(BOOT.encode()).hexdigest()
INITIAL_HASH = hashlib.sha256(b"earlier fixture boot").hexdigest()


def write_json(path, value):
    O.publish_raw(path, E.canonical_bytes(value))


class ProcessFixture:
    """Substitute the process boundary; run the real bounded raw acquisition."""
    def __init__(self, payload=b"", *, returncode=137, delay=0, stderr=b""):
        self.calls = []
        self.payload, self.returncode, self.delay, self.stderr = payload, returncode, delay, stderr
        self.snapshots = 0
        self.boots = [BOOT, BOOT]
        self.extra_after = False
        self.extra_target = False
        self.row_serial = SERIAL
        self.actual_pid = None
        self.raw_capture = SimpleNamespace(acquire_command=self.command,
            load_handle=RAW.load_handle, read_stdout=RAW.read_stdout, read_stderr=RAW.read_stderr)
        self.base = SimpleNamespace(bounded_command=self.public)
        self.ADB = Path("/fixture-only/no-adb")
        self.TARGET = E.TARGET
        self.PUBLIC_SNAPSHOT_SCRIPT = E.PUBLIC_SNAPSHOT_SCRIPT
        self.MAX_ADB_BYTES = E.MAX_ADB_BYTES
        self.shlex = shlex
        self.exact_adb_row = E.exact_adb_row
        self.parse_public_snapshot = E.parse_public_snapshot
        self.sanitized_inventory = E.sanitized_inventory
        self.digest = E.digest
        self.durable_json = write_json

    def command(self, argv, directory, name, **kwargs):
        expected = [str(self.ADB), "-s", SERIAL, "shell", "su", "-c", shlex.quote(O.READ_SCRIPT)]
        if argv != expected or name != O.CAPTURE_LABEL or kwargs != O.CAPTURE_KWARGS:
            raise AssertionError("non-fixed command or bounds reached process fixture")
        self.calls.append(argv)
        script = (f"import os,time;os.write(1,{self.payload!r});os.write(2,{self.stderr!r});"
                  f"time.sleep({self.delay!r});raise SystemExit({self.returncode})")
        # A short host timeout exercises the same raw helper's termination path.
        return RAW.acquire_command([sys.executable, "-c", script], directory, name,
            timeout=0.15 if self.delay else 2, stdout_maximum=kwargs["stdout_maximum"],
            stderr_maximum=kwargs["stderr_maximum"], stdout_name=kwargs["stdout_name"],
            stderr_name=kwargs["stderr_name"])

    def adb_inventory(self, **kwargs):
        row = {"serial": self.row_serial, "state": "device", "metadata": E.EXPECTED_ADB_METADATA}
        rows = [row]
        if self.extra_target:
            rows.append({**row, "serial": "SECOND_S20_FIXTURE"})
        if self.extra_after and self.snapshots:
            rows.append({"serial": "UNRELATED_FIXTURE", "state": "device",
                         "metadata": frozenset({"model:other"})})
        return tuple(rows)

    def adb_devpath(self, serial):
        if serial != SERIAL:
            raise AssertionError("foreign serial was addressed")
        return TOPOLOGY

    def public(self, argv, timeout, maximum):
        if argv != [str(self.ADB), "-s", SERIAL, "exec-out", "sh", "-c", E.PUBLIC_SNAPSHOT_SCRIPT]:
            raise AssertionError("non-fixed snapshot command")
        self.snapshots += 1
        values = {"model": E.TARGET["model"], "device": E.TARGET["device"],
                  "product_name": E.TARGET["product"], "incremental": E.TARGET["incremental"],
                  "boot_completed": "1", "bootanim": "stopped", "selinux": "Enforcing",
                  "boot_id": self.boots[min(self.snapshots - 1, len(self.boots) - 1)]}
        return 0, "".join(f"{key}={values[key]}\n" for key in E.PUBLIC_SNAPSHOT_KEYS).encode(), b""


def acquisition(engine, directory):
    return O.run_acquisition(engine, out_dir=directory,
        expected={"serial_sha256": SERIAL_HASH, "topology_sha256": TOPOLOGY_HASH,
                  "boot_id_sha256": INITIAL_HASH},
        candidate_id=C.CANDIDATE_ID, candidate_boot_sha256=P.CANDIDATE_BOOT_SHA256,
        candidate_ap_sha256=P.CANDIDATE_AP_SHA256, candidate_boot_id_sha256=BOOT_HASH)


class PublicationTests(unittest.TestCase):
    def test_short_writes_are_completed_and_receipt_matches_disk(self):
        actual = os.write
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture"
            with mock.patch.object(O.os, "write", side_effect=lambda fd, data: actual(fd, data[:3])):
                receipt = O.publish_raw(path, b"0123456789abcdef")
            self.assertEqual(path.read_bytes(), b"0123456789abcdef")
            self.assertEqual(receipt["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(receipt["size"], 16)

    def test_interrupted_write_retries_same_bytes(self):
        actual = os.write
        calls = 0
        def interrupted(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise InterruptedError()
            return actual(fd, data)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(O.os, "write", side_effect=interrupted):
            path = Path(tmp) / "capture"
            O.publish_raw(path, b"retained")
            self.assertEqual(path.read_bytes(), b"retained")

    def test_zero_progress_and_partial_failure_never_publish_success(self):
        actual = os.write
        for failure in (0, OSError("fixture write failure")):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "capture"
                calls = 0
                def interrupted(fd, data):
                    nonlocal calls
                    calls += 1
                    if calls == 1:
                        return actual(fd, data[:3])
                    if isinstance(failure, Exception):
                        raise failure
                    return failure
                with mock.patch.object(O.os, "write", side_effect=interrupted), self.assertRaises(O.PublishError):
                    O.publish_raw(path, b"original bytes")
                self.assertFalse(path.exists())
                self.assertEqual(path.with_name("capture.incomplete").read_bytes(), b"ori")

    def test_existing_capture_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture"
            O.publish_raw(path, b"first")
            with self.assertRaises(O.PublishError):
                O.publish_raw(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")


class AcquisitionTests(unittest.TestCase):
    def test_real_raw_backend_to_consumer_positive(self):
        payload = witness.capture(witness=witness.witness_body())
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fixture = ProcessFixture(payload)
            value = acquisition(fixture, directory)
            self.assertEqual(C.validate(value["capture_path"], value["attestation_path"])["verdict"], "PROVED")
            self.assertEqual((directory / O.CAPTURE_NAME).read_bytes(), payload)
            self.assertEqual(value["acquisition"]["status"], O.STATUS_DEADLINE)
            self.assertEqual(len(fixture.calls), 1)

    def test_partial_tail_is_retained_and_prefix_is_raw_derived(self):
        payload = witness.capture(witness=witness.witness_body()) + b"6,99,123,-;partial"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            value = acquisition(ProcessFixture(payload), directory)
            self.assertEqual((directory / O.CAPTURE_NAME).read_bytes(), payload)
            result = C.validate(value["capture_path"], value["attestation_path"])
            self.assertEqual(result["verdict"], "PROVED", result)
            self.assertEqual(value["attestation"]["parse_status"], O.PARSE_TRAILING_PARTIAL)
            self.assertGreater(value["attestation"]["trailing_partial_bytes"], 0)

    def test_malformed_framing_preserves_raw_before_failure(self):
        payload = b"not a kmsg header\npartial"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            value = acquisition(ProcessFixture(payload), directory)
            self.assertEqual((directory / O.CAPTURE_NAME).read_bytes(), payload)
            self.assertEqual(C.validate(value["capture_path"], value["attestation_path"])["verdict"], "NO_PROOF")
            self.assertEqual(value["attestation"]["parse_status"], O.PARSE_UNPARSABLE)

    def test_acquisition_error_timeout_and_stderr_never_prove(self):
        payload = witness.capture(witness=witness.witness_body())
        for options in ({"returncode": 1}, {"delay": 1}, {"stderr": b"fixture error"}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                value = acquisition(ProcessFixture(payload, **options), directory)
                self.assertEqual((directory / O.CAPTURE_NAME).read_bytes(), payload)
                self.assertEqual(value["acquisition"]["status"], O.STATUS_FAILED)
                self.assertEqual(C.validate(value["capture_path"], value["attestation_path"])["verdict"], "NO_PROOF")

    def test_source_change_is_refused_after_raw_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ProcessFixture(b"6,0,0,-;fixture\n")
            fixture.boots = [BOOT, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]
            with self.assertRaisesRegex(O.ObserverError, "changed"):
                acquisition(fixture, Path(tmp))
            self.assertTrue((Path(tmp) / O.CAPTURE_NAME).exists())
            self.assertFalse((Path(tmp) / O.ATTESTATION_NAME).exists())

    def test_wrong_serial_and_ambiguous_target_never_start_capture(self):
        for kind in ("serial", "duplicate"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                fixture = ProcessFixture()
                if kind == "serial":
                    fixture.row_serial = "OTHER_S20_FIXTURE"
                else:
                    fixture.extra_target = True
                with self.assertRaises(Exception):
                    acquisition(fixture, Path(tmp))
                self.assertEqual(fixture.calls, [])

    def test_other_target_arrival_does_not_change_s20_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ProcessFixture(witness.capture(witness=witness.witness_body()))
            fixture.extra_after = True
            self.assertEqual(acquisition(fixture, Path(tmp))["serial"], SERIAL)

    def test_raw_handle_cannot_name_other_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fixture = ProcessFixture()
            RAW.publish_captured_bytes(directory, O.CAPTURE_LABEL, stdout=b"6,0,0,-;fixture\n", stderr=b"",
                stdout_name="foreign.raw", stderr_name=O.STDERR_NAME)
            with self.assertRaisesRegex(O.ObserverError, "fixed capture"):
                O.read_acquisition(fixture, directory)

    def test_changed_raw_digest_is_rejected_even_if_prefix_hash_matches(self):
        payload = witness.capture(witness=witness.witness_body())
        framed = O.frame(payload)
        att = O.build_attestation(framed=framed, acquisition_status=O.STATUS_DEADLINE,
            target=C.TARGET, candidate_id=C.CANDIDATE_ID,
            candidate_boot_sha256=P.CANDIDATE_BOOT_SHA256,
            candidate_ap_sha256=P.CANDIDATE_AP_SHA256, boot_id=BOOT)
        att["raw_sha256"] = "0" * 64
        with self.assertRaisesRegex(C.EvidenceError, "raw bytes"):
            C.evaluate(payload, C.parse_attestation(json.dumps(att).encode()))

    def test_duplicate_attestation_keys_are_refused(self):
        with self.assertRaisesRegex(C.EvidenceError, "duplicate"):
            C.parse_attestation(b'{"schema":"a","schema":"b"}')


class ProfileTests(unittest.TestCase):
    def test_p1_installs_the_full_existing_shell(self):
        R._assert_profile_installed()
        for name in ("consume_candidate_globally", "require_candidate_claim", "prepare_process_cage",
                     "transfer_boot", "validate_namespace", "validate_rollback_closure", "validate_health_closure"):
            self.assertIs(getattr(E, name), R._profile_function_replacements()[name])
        self.assertIn("p1-kmsg-capture.raw", E.RUN_NODE_NAMES)
        self.assertIn(R.P0_REGISTRY_INTENT_NAME, E.RUN_NODE_NAMES)
        self.assertEqual(P.P1_F1_ACTIVE, R.P0_F1_ACTIVE)

    def test_p0_and_p1_have_isolated_dependencies_and_candidates(self):
        path = SCRIPTS / "s20plus_g986n_p0_pid1_odin_f1.py"
        spec = importlib.util.spec_from_file_location("_p1_test_ordinary_p0", path)
        p0 = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = p0
        spec.loader.exec_module(p0)
        p0._assert_profile_installed()
        R._assert_profile_installed()
        self.assertNotEqual(p0.CANDIDATE_AP_SHA256, P.CANDIDATE_AP_SHA256)
        for left, right in ((p0.engine, E), (p0.engine.base, E.base),
                            (p0.engine.raw_capture, E.raw_capture), (p0.registry, R.registry)):
            self.assertIsNot(left, right)
        self.assertFalse(p0.P0_F1_ACTIVE)

    def test_dormant_entrypoints_refuse_before_lease_or_process(self):
        with mock.patch.object(P, "P1_F1_ACTIVE", False), \
             mock.patch.object(O, "OBSERVER_ACTIVE", False), \
             mock.patch.object(R, "_session_lock_path", side_effect=AssertionError("lease reached")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("process reached")):
            for name in ("prepare", "execute", "resume_run", "arm_physical_rollback", "finalize_resident"):
                with self.subTest(name=name), self.assertRaises(P.P1F1Error):
                    getattr(E, name)(Path("/fixture/run"))
            with self.assertRaises(O.ObserverError):
                O.observe(SimpleNamespace())

    def test_reader_and_consumer_rebinding_is_rejected(self):
        for loader, name in ((P._load_reader, "frame"), (P._load_consumer, "evaluate")):
            module = loader()
            with mock.patch.object(module, name, return_value={"verdict": "PROVED"}):
                with self.assertRaisesRegex(P.P1F1Error, "rebound"):
                    loader()

    def test_owner_closure_has_actual_engine_shape(self):
        with mock.patch.object(R, "_validate_live_activation", return_value={}):
            closure = P.validate_host_closure()
        for key in ("runner", "sources", "physical_recovery", "process_cage_capability",
                    "candidate", "rollback", "manifest", "builder", "p1_profile"):
            self.assertIn(key, closure)
        self.assertEqual(closure["candidate"]["ap"]["sha256"], E.CANDIDATE_AP_SHA256)
        self.assertEqual(closure["manifest"]["sha256"], E.MANIFEST_SHA256)
        self.assertEqual(closure["builder"]["sha256"], E.BUILDER_SHA256)

    def test_recovery_closure_does_not_need_candidate_payload_or_builder(self):
        with mock.patch.object(E, "CANDIDATE_AP", Path("/absent/candidate")), \
             mock.patch.object(E, "BUILDER", Path("/absent/builder")), \
             mock.patch.object(R, "_assert_profile_installed"):
            self.assertIn("rollback", P.validate_rollback_closure())
            self.assertIn("sources", P.validate_health_closure())

    def test_cli_recovery_does_not_consult_observer_activation(self):
        for option, entry in (("--resume", "resume_run"), ("--arm-physical-rollback", "arm_physical_rollback"),
                              ("--finalize-resident", "finalize_resident")):
            with self.subTest(option=option), mock.patch.object(P, "require_active"), \
                 mock.patch.object(P, "_candidate_require_active", side_effect=AssertionError("reader gate")), \
                 mock.patch.object(E, entry, return_value={"fixture": True}) as called, \
                 mock.patch("builtins.print"):
                self.assertEqual(P.main([option, "--run-dir", "/fixture/run"]), 0)
                called.assert_called_once()

    def test_unexpected_recovery_claim_is_not_relabelled_as_pid1(self):
        for claim in ("REFUTED", "PROVED"):
            with self.subTest(claim=claim), tempfile.TemporaryDirectory() as tmp, \
                 mock.patch.object(P, "require_active"), mock.patch.object(R, "_require_live_transaction"), \
                 mock.patch.object(R, "_ENGINE_OBSERVE_CANDIDATE", return_value=(
                     {"environment": "recovery-adb", "claim_verdict": claim, "transport_authorized": True}, SERIAL)):
                result, serial = P.observe_candidate(Path(tmp), {})
                self.assertEqual(result["environment"], "observer-reporting-cut")
                self.assertEqual(result["claim_verdict"], "NO_PROOF")
                self.assertIsNone(serial)

    def test_reporting_cut_observation_is_valid_for_recovery(self):
        value = {"schema": P.OBSERVATION_SCHEMA, "version": P.VERSION,
                 "binding_sha256": "1" * 64, "candidate_replay_permitted": False,
                 **P._failed_observation("fixture-cut")}
        with tempfile.TemporaryDirectory() as tmp:
            P.validate_candidate_observation(Path(tmp), value, "1" * 64, INITIAL_HASH)




class EngineLifecycleTests(unittest.TestCase):
    """Actual installed engine dispatch with qualified hardware receipts replaced.

    Artifact closure is real. Session flock, JSON publication, owner observation,
    leased raw-command dispatch and consumer are real. Hardware health, cgroup
    qualification and Odin transfer are fixture boundaries, not device proofs.
    """
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(R, "_validate_live_activation", return_value={}):
            cls.closure = P.validate_host_closure()

    @contextlib.contextmanager
    def scenario(self, *, capture_returncode=137, publication_failure=False):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir(mode=0o700)
            lock = root / "target-session.lock"
            lock.write_bytes(R.registry.SESSION_LOCK_PAYLOAD)
            lock.chmod(0o600)
            health = {"target": E.TARGET, "serial_sha256": SERIAL_HASH,
                      "topology_sha256": TOPOLOGY_HASH, "boot_id_sha256": BOOT_HASH}
            preflight = {**health, "boot_id_sha256": INITIAL_HASH}
            endpoint = {"fixture": "download"}
            binding = E.prepared_binding(run_dir, preflight, endpoint, self.closure)
            prepared = {"schema": "s20plus_g986n_b0_prepared_v1", "version": P.VERSION,
                        "binding": binding, "binding_sha256": E.digest(binding),
                        "approval_token": P.APPROVAL_PREFIX + E.digest(binding), "at": "fixture"}
            write_json(run_dir / "prepared.json", prepared)
            observed = {"environment": "resident-android", "transport_authorized": True,
                        "claim_verdict": "NO_PROOF", "resident_health": health, "at": "fixture"}
            reader = P._load_reader()
            calls = []
            fixture = ProcessFixture()
            fixture.ADB = E.ADB
            fixed_command = [str(E.ADB), "-s", SERIAL, "shell", "su", "-c", shlex.quote(reader.READ_SCRIPT)]
            payload = witness.capture(witness=witness.witness_body())
            real_popen = subprocess.Popen

            def popen(argv, *args, **kwargs):
                self.assertEqual(argv, fixed_command)
                self.assertEqual(R._require_live_transaction()["run_dir"], str(run_dir))
                calls.append("capture")
                command = [sys.executable, "-c", f"import os;os.write(1,{payload!r});raise SystemExit({capture_returncode})"]
                return real_popen(command, *args, **kwargs)

            def bounded(argv, timeout, maximum):
                if argv == [str(E.ADB), "devices", "-l"]:
                    target = ""
                    if (run_dir / "candidate-intent.json").exists():
                        target = SERIAL + "\tdevice " + " ".join(sorted(E.EXPECTED_ADB_METADATA)) + "\n"
                    return 0, ("List of devices attached\n" + target).encode(), b""
                if argv == [str(E.ADB), "-s", SERIAL, "get-devpath"]:
                    return 0, (TOPOLOGY + "\n").encode(), b""
                return fixture.public(argv, timeout, maximum)

            def consume(directory, digest):
                self.assertEqual(R._require_live_transaction()["run_dir"], str(directory))
                calls.append("consume")

            def transfer(directory, kind, endpoint, digest):
                self.assertEqual(kind, "candidate")
                calls.append("transfer")
                write_json(directory / "candidate-intent.json", {"fixture": True})
                write_json(directory / "candidate-result.json", {"classification": "odin_transfer_completed"})

            def transfer_receipt(directory, stored):
                self.assertTrue((directory / "candidate-intent.json").exists())
                self.assertEqual(stored["binding_sha256"], prepared["binding_sha256"])
                return {"candidate_result_sha256": "2" * 64,
                        "binding_sha256": prepared["binding_sha256"],
                        "candidate_ap_sha256": P.CANDIDATE_AP_SHA256,
                        "candidate_boot_sha256": P.CANDIDATE_BOOT_SHA256}

            def rollback_entry(directory, stored, observation, serial):
                self.assertEqual(serial, SERIAL)
                self.assertEqual(R._require_live_transaction()["run_dir"], str(directory))
                calls.append("rollback-entry")
                return {"endpoint": endpoint}

            def durable(path, value):
                if publication_failure and path.name == reader.ATTESTATION_NAME:
                    raise OSError("fixture publication failure")
                write_json(path, value)

            patches = [
                mock.patch.object(P, "P1_F1_ACTIVE", True),
                mock.patch.object(R, "P0_F1_ACTIVE", True),
                mock.patch.object(E, "B0_F1_ACTIVE", True),
                mock.patch.object(E, "EXPECTED_ANDROID_TOPOLOGY_SHA256", TOPOLOGY_HASH),
                mock.patch.object(reader, "OBSERVER_ACTIVE", True),
                mock.patch.object(R, "RUN_ROOT", root),
                mock.patch.object(E, "RUN_ROOT", root),
                mock.patch.object(R, "_session_lock_path", return_value=lock),
                mock.patch.object(R, "_assert_profile_installed"),
                mock.patch.object(R, "_validate_live_activation", return_value={}),
                mock.patch.object(E, "require_guard"),
                mock.patch.object(E, "validate_run_dir", side_effect=lambda p: p),
                mock.patch.object(E, "_validate_resident_health_receipt"),
                mock.patch.object(E, "_validate_endpoint"),
                mock.patch.object(E, "validate_prepared_history"),
                mock.patch.object(E, "validate_host_closure", return_value=self.closure),
                mock.patch.object(E, "validate_health_closure", return_value={}),
                mock.patch.object(E, "candidate_claim_present", return_value=False),
                mock.patch.object(E, "consume_candidate_globally", side_effect=consume),
                mock.patch.object(E, "require_candidate_claim"),
                mock.patch.object(E, "identify_download", return_value=endpoint),
                mock.patch.object(E, "same_download_session", return_value=True),
                mock.patch.object(E, "transfer_boot", side_effect=transfer),
                mock.patch.object(E, "require_transfer_process_quiescence"),
                mock.patch.object(E, "require_all_transfer_processes_quiescent"),
                mock.patch.object(E, "source_closure_receipts", return_value={}),
                mock.patch.object(E, "health_source_closure_receipts", return_value={}),
                mock.patch.object(E.base, "bounded_command", side_effect=bounded),
                mock.patch.object(E, "durable_json", side_effect=durable),
                mock.patch.object(R, "_ENGINE_OBSERVE_CANDIDATE", return_value=(dict(observed), SERIAL)),
                mock.patch.object(P, "_candidate_transfer", side_effect=transfer_receipt),
                mock.patch.object(E, "enter_rollback_download", side_effect=rollback_entry),
                mock.patch.object(E, "rollback_from_arrival", side_effect=lambda *args: {"fixture_rollback": True}),
                mock.patch("subprocess.Popen", side_effect=popen),
                # Cgroup hardware qualification is represented by an already
                # reconciled generation; legacy P0 tests cover its validator.
                mock.patch.object(R, "_cage_generations", side_effect=lambda directory, kind:
                    {1: {"prepare", "bound", "reconciled"}} if kind == "candidate"
                    and (directory / "candidate-intent.json").exists() else {}),
                mock.patch.object(R, "_validate_cage_prepare", return_value={"cage": "/fixture/cage"}),
                mock.patch.object(R, "_validate_cage_bound", return_value={"process_cage": {}}),
                mock.patch.object(R, "_effect_matches_cage", return_value=True),
                mock.patch.object(R, "_validate_cage_reconciled"),
            ]
            for item in patches:
                stack.enter_context(item)
            yield run_dir, prepared, calls

    def test_prepared_closure_round_trip_uses_actual_engine_consumer(self):
        with self.scenario() as (run_dir, prepared, calls):
            result = R._read_prepared_for_output(run_dir)
            self.assertEqual(result, prepared)
            self.assertEqual(calls, [])
            bad = json.loads(json.dumps(prepared))
            bad["binding"]["closure"]["manifest"]["sha256"] = "0" * 64
            bad["binding_sha256"] = E.digest(bad["binding"])
            bad["approval_token"] = P.APPROVAL_PREFIX + bad["binding_sha256"]
            (run_dir / "prepared.json").unlink()
            write_json(run_dir / "prepared.json", bad)
            with self.assertRaisesRegex(E.B0F1Error, "closure"):
                R._read_prepared_for_output(run_dir)

    def test_actual_execute_joins_acquisition_to_mandatory_rollback(self):
        with self.scenario() as (run_dir, prepared, calls):
            result = E.execute(run_dir, prepared["approval_token"])
            self.assertEqual(result, {"fixture_rollback": True})
            self.assertEqual(calls, ["consume", "transfer", "capture", "rollback-entry"])
            observation = json.loads((run_dir / "candidate-observation.json").read_bytes())
            self.assertEqual(observation["claim_verdict"], "PROVED", observation)
            with self.assertRaisesRegex(E.B0F1Error, "consumed"):
                E.execute(run_dir, prepared["approval_token"])
            self.assertEqual(calls.count("transfer"), 1)

    def test_acquisition_failure_preserves_raw_and_resumes_recovery_only(self):
        with self.scenario(capture_returncode=1) as (run_dir, prepared, calls):
            result = E.execute(run_dir, prepared["approval_token"])
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_PHYSICAL_DOWNLOAD")
            self.assertEqual(calls, ["consume", "transfer", "capture"])
            self.assertTrue((run_dir / "p1-kmsg-capture.raw").exists())
            before = (run_dir / "p1-kmsg-capture.raw").read_bytes()
            resumed = E.resume_run(run_dir)
            self.assertFalse(resumed["candidate_replay_permitted"])
            self.assertEqual(calls, ["consume", "transfer", "capture"])
            self.assertEqual(before, (run_dir / "p1-kmsg-capture.raw").read_bytes())

    def test_publication_failure_keeps_raw_and_does_not_retry_observation(self):
        with self.scenario(publication_failure=True) as (run_dir, prepared, calls):
            result = E.execute(run_dir, prepared["approval_token"])
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_PHYSICAL_DOWNLOAD")
            self.assertTrue((run_dir / "p1-kmsg-capture.raw").exists())
            resumed = E.resume_run(run_dir)
            self.assertFalse(resumed["candidate_replay_permitted"])
            self.assertEqual(calls.count("capture"), 1)

    def test_reporting_cut_recovers_without_a_second_acquisition(self):
        with self.scenario(capture_returncode=1) as (run_dir, prepared, calls):
            E.execute(run_dir, prepared["approval_token"])
            # Fixture simulates process loss after durable raw/intent and before
            # observation publication; no actual journal is modified by tests.
            (run_dir / "candidate-observation.json").unlink()
            E.resume_run(run_dir)
            value = json.loads((run_dir / "candidate-observation.json").read_bytes())
            self.assertEqual(value["environment"], "observer-reporting-cut")
            self.assertEqual(value["claim_verdict"], "NO_PROOF")
            self.assertEqual(calls.count("capture"), 1)
            self.assertEqual(calls.count("transfer"), 1)


if __name__ == "__main__":
    unittest.main()
