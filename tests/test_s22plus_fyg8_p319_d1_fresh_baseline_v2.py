from __future__ import annotations

import copy
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v2.py"
)
BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v2.json"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_D1_FRESH_BASELINE_RAW_FIRST_V2_H0_2026-08-24.md"
)
REVIEW_REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_D1_FRESH_BASELINE_RAW_FIRST_V2_INDEPENDENT_REVIEW_"
    "2026-08-24.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ScriptedClient:
    def __init__(self, d0, raw, *, serial="FIXTURE_S22", topology="usb:1-1"):
        self.d0 = d0
        self.raw = raw
        self.adb = Path("/fixture/adb")
        self.serial = serial
        self.topology_value = topology
        self.capture_dir = None
        self.sequence = 0
        self.events = []
        self.rebooted = False
        self.poll_inventory = 0
        self.bind_error = None
        self.inventory_error = None
        self.inventory_text = None
        self.topology_error = None
        self.properties_error = None
        self.root_error = None
        self.bad_health = False
        self.disconnect_once = True
        self.poll_property_failures = 0

    def bind_raw_capture_dir(self, root):
        self.events.append("bind")
        if self.bind_error is not None:
            raise self.bind_error
        self.capture_dir = self.raw.prepare_capture_dir(root, "raw-adb")

    def _capture(self, label, payload=b"", *, returncode=0, stderr=b""):
        if self.capture_dir is None:
            raise self.d0.D0Error("ADB raw-first capture is not bound")
        name = f"{self.sequence:04d}-{label.replace(' ', '-')}"
        self.sequence += 1
        writer = self.raw.RawCaptureWriter(
            self.capture_dir,
            name,
            stdout_maximum=4 * 1024 * 1024,
            stderr_maximum=4 * 1024 * 1024,
            argv0_name="fixture-adb",
        )
        writer.write_stdout(payload)
        writer.write_stderr(stderr)
        handle = writer.finalize(returncode=returncode)
        self.events.append(("published", label))
        reopened = self.raw.load_handle(handle.receipt_path)
        self.raw.require_success(reopened)
        value = self.raw.read_stdout(reopened, maximum=4 * 1024 * 1024)
        if self.raw.read_stderr(reopened, maximum=4 * 1024 * 1024):
            raise self.d0.D0Error("fixture stderr")
        self.events.append(("parsed", label))
        return handle, value

    def _run(self, arguments, label, timeout=20):
        del arguments, timeout
        if self.inventory_error is not None:
            raise self.inventory_error
        if self.inventory_text is not None:
            text = self.inventory_text
        elif self.rebooted and self.disconnect_once and self.poll_inventory == 0:
            self.poll_inventory += 1
            text = "List of devices attached\n"
        else:
            text = (
                "List of devices attached\n"
                f"{self.serial} device model:SM_S906N device:g0q transport_id:1\n"
            )
        _handle, payload = self._capture(label, text.encode("utf-8"))
        return payload.decode("utf-8").strip()

    def topology(self, serial):
        if serial != self.serial:
            raise self.d0.D0Error("fixture serial differs")
        if self.topology_error is not None:
            raise self.topology_error
        _handle, payload = self._capture(
            "adb-get-devpath", self.topology_value.encode("ascii")
        )
        return payload.decode("ascii")

    def properties(self, serial):
        if serial != self.serial:
            raise self.d0.D0Error("fixture serial differs")
        if self.properties_error is not None:
            raise self.properties_error
        if self.rebooted and (
            self.poll_property_failures is None
            or self.poll_property_failures > 0
        ):
            if self.poll_property_failures is not None:
                self.poll_property_failures -= 1
            try:
                self._capture(
                    "adb-read-only-shell",
                    returncode=1,
                    stderr=b"fixture-not-ready",
                )
            except self.raw.RawCaptureError as exc:
                raise self.d0.D0Error("fixture properties raw failure") from exc
            raise AssertionError("failed raw fixture unexpectedly succeeded")
        boot_id = (
            "22222222-2222-2222-2222-222222222222"
            if self.rebooted
            else "11111111-1111-1111-1111-111111111111"
        )
        value = {
            "model": "SM-S906N",
            "device": "g0q",
            "incremental": "S906NKSS7FYG8",
            "boot_completed": "0" if self.bad_health else "1",
            "bootanim": "stopped",
            "verified_boot_state": "orange",
            "boot_id": boot_id,
            "kernel_release": "5.10.226-fixture",
        }
        self._capture("adb-read-only-shell", json.dumps(value).encode("ascii"))
        return value

    def root_health(self, serial):
        if serial != self.serial:
            raise self.d0.D0Error("fixture serial differs")
        if self.root_error is not None:
            raise self.root_error
        value = {
            "root": "uid=0(root) gid=0(root)",
            "boot": "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e",
            "vendor_boot": "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7",
            "dtbo": "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c",
            "recovery": "93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4",
        }
        self._capture("adb-read-only-shell", json.dumps(value).encode("ascii"))
        return value

    def capture_command(self, arguments, label, *, timeout, maximum):
        del arguments, timeout, maximum
        handle, _payload = self._capture(label)
        self.rebooted = True
        return handle


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class P319D1FreshBaselineV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load(SOURCE, "p319_d1_v2_test")

    def sandbox(self, *, pass_go=False):
        temporary = tempfile.TemporaryDirectory(prefix="p319-d1-v2-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        parent = root / "run-parent"
        run = parent / "p319-fresh-baseline-2"
        arm = parent / "p319-fresh-baseline-2.arm.json"
        raw_root = parent / "p319-fresh-baseline-2-raw"
        snapshot = root / "adb-snapshot"
        manifest = root / "binding.json"
        patcher = mock.patch.multiple(
            self.module,
            BINDING_MANIFEST=manifest,
            RUN_PARENT=parent,
            RUN_DIR=run,
            RUN_ARM=arm,
            RUN_STOP=run / "stop.json",
            RAW_ROOT=raw_root,
            RAW_ADB_DIR=raw_root / "raw-adb",
            ADB_SNAPSHOT=snapshot,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        payloads = self.module._input_payloads()
        review = (
            {"status": "pass-go", "verdict": self.module.REVIEW_VERDICT}
            if pass_go
            else {"status": "review-pending", "verdict": None}
        )
        manifest.write_bytes(
            self.module.canonical(self.module._expected_manifest(payloads, review))
        )
        return root

    def inputs(self, *, pass_go=False):
        self.sandbox(pass_go=pass_go)
        static = self.module._validated_static_inputs()
        return self.module._validated_execution_inputs(static)

    def arm(self, inputs, *, complete=True):
        if complete:
            inputs["v1"]._durable_create(
                self.module.RUN_ARM, self.module._arm_value(inputs)
            )
        else:
            self.module.RUN_PARENT.mkdir(mode=0o700)
            self.module.RUN_ARM.write_bytes(b'{"partial":')
            self.module.RUN_ARM.chmod(0o400)

    def raw_root(self, inputs):
        return inputs["raw"].prepare_capture_dir(
            self.module.RUN_PARENT, self.module.RAW_ROOT.name
        )

    def make_transport(self, inputs, client):
        module, _p318 = self.module._pinned_base(inputs)
        module.d0.usb_snapshot = lambda *_args, **_kwargs: {
            "download_endpoint_count": 0
        }
        binding = copy.deepcopy(inputs["v1_inputs"]["prior_binding"])
        binding["target"]["adb_serial_sha256"] = hashlib.sha256(
            client.serial.encode("ascii")
        ).hexdigest()
        transport = self.module._make_transport(
            module,
            inputs["raw"],
            binding,
            inputs["v1_inputs"]["profile"],
            self.module.RAW_ROOT,
            client_factory=lambda _d0, _raw: client,
        )
        transport.fixture_module = module
        return transport

    def complete_host_fixture(self, inputs, *, configure=None):
        self.arm(inputs)
        inputs["v1"]._load_p318(
            inputs["v1_inputs"]["p318_payload"]
        )._prepare_executable_snapshot(
            inputs["payloads"]["host_adb"], self.module.ADB_SNAPSHOT
        )
        self.raw_root(inputs)
        serial = "FIXTURE_S22"
        inputs["v1_inputs"]["prior_binding"]["target"]["adb_serial_sha256"] = (
            hashlib.sha256(serial.encode("ascii")).hexdigest()
        )
        holder = {}

        def factory(d0, raw):
            d0.usb_snapshot = lambda *_args, **_kwargs: {
                "download_endpoint_count": 0
            }
            client = ScriptedClient(d0, raw, serial=serial)
            if configure is not None:
                configure(client)
            holder["client"] = client
            return client

        self.module._execute_primitive(
            inputs, client_factory=factory, clock=FakeClock()
        )
        return self.module._post_validate(inputs), holder["client"]

    def test_v1_cause_is_mechanically_reproduced_without_device_contact(self):
        inputs = self.inputs()
        value = self.module.reproduce_v1_missing_bind(inputs)
        self.assertEqual(value["error_code"], "RAW_CAPTURE_UNBOUND")
        self.assertEqual(value["inherited_inventory_bounded_command_calls"], 1)
        self.assertEqual(value["inherited_inventory_raw_handles"], 0)
        self.assertEqual(value["topology_path_bounded_command_calls"], 0)
        self.assertFalse(value["device_contact"])

    def test_default_self_test_has_no_process_or_device_acquisition(self):
        with mock.patch(
            "subprocess.Popen", side_effect=AssertionError("device/process call")
        ):
            value = self.module.self_test()
        self.assertEqual(value["review_status"], "pass-go")
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_consumed_v1_evidence_is_exact_and_never_replayable(self):
        self.assertEqual(
            (self.module.V1_SOURCE.stat().st_size, hashlib.sha256(self.module.V1_SOURCE.read_bytes()).hexdigest()),
            self.module.EXPECTED["v1_source"],
        )
        self.assertEqual(
            (self.module.V1_BINDING.stat().st_size, hashlib.sha256(self.module.V1_BINDING.read_bytes()).hexdigest()),
            self.module.EXPECTED["v1_binding"],
        )
        self.assertEqual(
            (self.module.V1_ARM.stat().st_size, hashlib.sha256(self.module.V1_ARM.read_bytes()).hexdigest()),
            self.module.EXPECTED["v1_arm"],
        )
        self.assertEqual(
            (self.module.V1_STOP.stat().st_size, hashlib.sha256(self.module.V1_STOP.read_bytes()).hexdigest()),
            self.module.EXPECTED["v1_stop"],
        )

    def test_review_pending_wrong_and_old_approval_stop_before_execution(self):
        pending = {
            "manifest": {"independent_review": {"status": "review-pending", "verdict": None}},
            "authority": "new-authority",
        }
        with mock.patch.object(self.module, "_validated_static_inputs", return_value=pending), mock.patch.object(self.module, "_validated_execution_inputs") as execution:
            with self.assertRaises(self.module.SuccessorError):
                self.module.run_live("new-authority")
            execution.assert_not_called()
        passed = {
            "manifest": {"independent_review": {"status": "pass-go", "verdict": self.module.REVIEW_VERDICT}},
            "authority": "new-authority",
        }
        old = "DEVICE-ACTION-D1-P319-FRESH-BASELINE-V1-APPROVE:" + "0" * 64
        with mock.patch.object(self.module, "_validated_static_inputs", return_value=passed), mock.patch.object(self.module, "_validated_execution_inputs") as execution:
            with self.assertRaises(self.module.SuccessorError):
                self.module.run_live(old)
            execution.assert_not_called()

    def test_live_argv_has_no_path_or_old_ordinal_surface(self):
        for argv in (
            ["--live"],
            ["--live", "--approval", "x", "--run", "p319-fresh-baseline-1"],
            ["--adb", "/tmp/adb"],
        ):
            with self.subTest(argv=argv), mock.patch.object(
                self.module, "run_live"
            ) as live:
                self.assertEqual(self.module.main(argv), 2)
                live.assert_not_called()

    def test_missing_host_input_cli_is_traceback_free_and_redacted(self):
        missing = Path("/private-fixture-serial/missing-binding.json")
        output = io.StringIO()
        with mock.patch.object(
            self.module, "BINDING_MANIFEST", missing
        ), contextlib.redirect_stderr(output):
            self.assertEqual(self.module.main([]), 2)
        rendered = output.getvalue()
        self.assertIn("host input validation failed (FileNotFoundError)", rendered)
        self.assertNotIn(str(missing), rendered)
        self.assertNotIn("Traceback", rendered)

    def test_successor_binds_before_inventory_and_publishes_before_parse(self):
        inputs = self.inputs()
        self.arm(inputs)
        self.raw_root(inputs)
        module, _p318 = self.module._pinned_base(inputs)
        client = ScriptedClient(module.d0, inputs["raw"])
        transport = self.make_transport(inputs, client)
        _serial, selection = transport.select_exact()
        self.assertEqual(client.events[0], "bind")
        published = client.events.index(("published", "adb inventory"))
        parsed = client.events.index(("parsed", "adb inventory"))
        self.assertLess(published, parsed)
        self.assertEqual(selection["inventory_count"], 1)
        self.assertRegex(selection["inventory_sha256"], r"^[0-9a-f]{64}$")
        raw = self.module._raw_inventory(inputs["raw"])
        self.assertTrue(raw["complete"])
        self.assertEqual(len(raw["children"]), 6)
        self.assertEqual(len(raw["handles"]), 2)

    def test_inherited_direct_inventory_bypass_is_absent_from_successor(self):
        value = self.module._source_contract()
        self.assertEqual(value["direct_bounded_command_calls"], 0)
        self.assertTrue(value["bind_before_inventory"])

    def test_host_only_full_fixture_uses_one_reboot_and_closed_raw_evidence(self):
        inputs = self.inputs()
        result, client = self.complete_host_fixture(inputs)
        self.assertEqual(result["reboot_count"], 1)
        self.assertFalse(result["other_targets_commanded"])
        self.assertTrue(result["raw_evidence"]["complete"])
        self.assertEqual(len(result["raw_evidence"]["handles"]), 14)
        self.assertEqual(len(result["raw_evidence"]["children"]), 42)
        self.assertEqual(client.events[0], "bind")
        for event in {
            item[1] for item in client.events if isinstance(item, tuple)
        }:
            self.assertLess(
                client.events.index(("published", event)),
                client.events.index(("parsed", event)),
            )

    def test_transient_poll_properties_raw_failure_then_health_succeeds_once(self):
        inputs = self.inputs()

        def configure(client):
            client.disconnect_once = False
            client.poll_property_failures = 1

        result, client = self.complete_host_fixture(inputs, configure=configure)
        self.assertEqual(result["reboot_count"], 1)
        self.assertEqual(len(result["raw_evidence"]["handles"]), 15)
        self.assertEqual(
            sum(
                handle["returncode"] == 1
                for handle in result["raw_evidence"]["handles"]
            ),
            1,
        )
        self.assertEqual(
            client.events.count(("published", "adb normal reboot")), 1
        )

    def test_persistent_poll_properties_failures_terminalize_return_health(self):
        inputs = self.inputs()
        self.arm(inputs)
        inputs["v1"]._load_p318(
            inputs["v1_inputs"]["p318_payload"]
        )._prepare_executable_snapshot(
            inputs["payloads"]["host_adb"], self.module.ADB_SNAPSHOT
        )
        self.raw_root(inputs)
        serial = "FIXTURE_S22"
        inputs["v1_inputs"]["prior_binding"]["target"]["adb_serial_sha256"] = (
            hashlib.sha256(serial.encode("ascii")).hexdigest()
        )
        holder = {}

        def factory(d0, raw):
            d0.usb_snapshot = lambda *_args, **_kwargs: {
                "download_endpoint_count": 0
            }
            client = ScriptedClient(d0, raw, serial=serial)
            client.disconnect_once = False
            client.poll_property_failures = None
            holder["client"] = client
            return client

        with self.assertRaises(self.module.ClassifiedFailure) as caught:
            self.module._execute_primitive(
                inputs, client_factory=factory, clock=FakeClock()
            )
        self.assertEqual(
            (caught.exception.failure_site, caught.exception.failure_code),
            ("returned-health", "RETURN_HEALTH"),
        )
        self.module._publish_stop(inputs, caught.exception)
        stop = self.module.validate_stop_file()
        self.assertEqual(stop["failure_code"], "RETURN_HEALTH")
        self.assertTrue(stop["reboot_dispatch_possible"])
        self.assertTrue(stop["raw_evidence"]["complete"])
        self.assertGreater(
            sum(
                handle["returncode"] == 1
                for handle in stop["raw_evidence"]["handles"]
            ),
            1,
        )
        self.assertEqual(
            holder["client"].events.count(("published", "adb normal reboot")),
            1,
        )

    def test_inventory_failure_buckets_are_distinct(self):
        cases = (
            ("read", None, ("inventory-read", "INVENTORY_READ")),
            ("parse", "malformed", ("inventory-parse", "INVENTORY_FORMAT")),
            ("cardinality", "List of devices attached\n", ("inventory-select", "INVENTORY_CARDINALITY")),
            ("state", "List of devices attached\nFIXTURE_S22 offline model:SM_S906N device:g0q transport_id:1\n", ("inventory-select", "INVENTORY_STATE")),
        )
        for name, text, expected in cases:
            with self.subTest(case=name):
                inputs = self.inputs()
                self.arm(inputs)
                self.raw_root(inputs)
                module, _p318 = self.module._pinned_base(inputs)
                client = ScriptedClient(module.d0, inputs["raw"])
                if name == "read":
                    client.inventory_error = module.d0.D0Error("fixture")
                else:
                    client.inventory_text = text
                transport = self.make_transport(inputs, client)
                with self.assertRaises(self.module.ClassifiedFailure) as caught:
                    transport.select_exact()
                self.assertEqual(
                    (caught.exception.failure_site, caught.exception.failure_code),
                    expected,
                )

    def test_serial_and_topology_failure_buckets_are_distinct(self):
        inputs = self.inputs()
        self.arm(inputs)
        self.raw_root(inputs)
        module, _p318 = self.module._pinned_base(inputs)
        client = ScriptedClient(module.d0, inputs["raw"])
        transport = self.make_transport(inputs, client)
        transport.binding["target"]["adb_serial_sha256"] = "0" * 64
        with self.assertRaises(self.module.ClassifiedFailure) as serial:
            transport.select_exact()
        self.assertEqual(serial.exception.failure_code, "SERIAL_IDENTITY")

        inputs = self.inputs()
        self.arm(inputs)
        self.raw_root(inputs)
        module, _p318 = self.module._pinned_base(inputs)
        client = ScriptedClient(module.d0, inputs["raw"], topology="invalid")
        transport = self.make_transport(inputs, client)
        with self.assertRaises(self.module.ClassifiedFailure) as topology:
            transport.select_exact()
        self.assertEqual(topology.exception.failure_code, "TOPOLOGY_IDENTITY")

    def test_bind_topology_read_and_usb_failure_buckets_are_distinct(self):
        inputs = self.inputs()
        self.arm(inputs)
        self.raw_root(inputs)
        module, _p318 = self.module._pinned_base(inputs)
        client = ScriptedClient(module.d0, inputs["raw"])
        client.bind_error = module.d0.D0Error("fixture")
        with self.assertRaises(self.module.ClassifiedFailure) as bind:
            self.module._make_transport(
                module,
                inputs["raw"],
                inputs["v1_inputs"]["prior_binding"],
                inputs["v1_inputs"]["profile"],
                self.module.RAW_ROOT,
                client_factory=lambda _d0, _raw: client,
            )
        self.assertEqual(
            (bind.exception.failure_site, bind.exception.failure_code),
            ("raw-capture-bind", "RAW_CAPTURE_NAMESPACE"),
        )

        inputs = self.inputs()
        self.arm(inputs)
        self.raw_root(inputs)
        module, _p318 = self.module._pinned_base(inputs)
        client = ScriptedClient(module.d0, inputs["raw"])
        client.topology_error = module.d0.D0Error("fixture")
        transport = self.make_transport(inputs, client)
        with self.assertRaises(self.module.ClassifiedFailure) as topology:
            transport.select_exact()
        self.assertEqual(
            (topology.exception.failure_site, topology.exception.failure_code),
            ("topology-read", "TOPOLOGY_READ"),
        )

        inputs = self.inputs()
        self.arm(inputs)
        self.raw_root(inputs)
        module, _p318 = self.module._pinned_base(inputs)
        client = ScriptedClient(module.d0, inputs["raw"])
        transport = self.make_transport(inputs, client)
        serial, _selection = transport.select_exact()
        # The transport closure owns this exact pinned D0 module.
        transport.fixture_module.d0.usb_snapshot = lambda *_args, **_kwargs: {
            "download_endpoint_count": 1
        }
        with self.assertRaises(self.module.ClassifiedFailure) as usb:
            transport.snapshot(serial)
        self.assertEqual(
            (usb.exception.failure_site, usb.exception.failure_code),
            ("usb-snapshot", "USB_SNAPSHOT"),
        )

    def test_read_failure_buckets_are_distinct(self):
        for attribute, expected in (
            ("properties_error", ("properties-read", "HEALTH_PROPERTIES_READ")),
            ("root_error", ("root-health-read", "HEALTH_ROOT_READ")),
        ):
            with self.subTest(attribute=attribute):
                inputs = self.inputs()
                self.arm(inputs)
                self.raw_root(inputs)
                module, _p318 = self.module._pinned_base(inputs)
                client = ScriptedClient(module.d0, inputs["raw"])
                transport = self.make_transport(inputs, client)
                serial, _selection = transport.select_exact()
                setattr(client, attribute, module.d0.D0Error("private detail"))
                with self.assertRaises(self.module.ClassifiedFailure) as caught:
                    transport.snapshot(serial)
                self.assertEqual(
                    (caught.exception.failure_site, caught.exception.failure_code),
                    expected,
                )

    def test_health_and_start_publication_buckets_are_distinct(self):
        for case in ("health", "start"):
            with self.subTest(case=case):
                inputs = self.inputs()
                self.arm(inputs)
                inputs["v1"]._load_p318(
                    inputs["v1_inputs"]["p318_payload"]
                )._prepare_executable_snapshot(
                    inputs["payloads"]["host_adb"], self.module.ADB_SNAPSHOT
                )
                self.raw_root(inputs)
                serial = "FIXTURE_S22"
                inputs["v1_inputs"]["prior_binding"]["target"][
                    "adb_serial_sha256"
                ] = hashlib.sha256(serial.encode("ascii")).hexdigest()
                holder = {}

                def factory(d0, raw):
                    d0.usb_snapshot = lambda *_args, **_kwargs: {
                        "download_endpoint_count": 0
                    }
                    client = ScriptedClient(d0, raw, serial=serial)
                    client.bad_health = case == "health"
                    holder["client"] = client
                    return client

                patcher = (
                    mock.patch.object(
                        inputs["v1"], "_durable_create", side_effect=OSError("cut")
                    )
                    if case == "start"
                    else mock.patch.object(
                        inputs["v1"],
                        "_durable_create",
                        wraps=inputs["v1"]._durable_create,
                    )
                )
                with patcher, self.assertRaises(
                    self.module.ClassifiedFailure
                ) as caught:
                    self.module._execute_primitive(
                        inputs, client_factory=factory, clock=FakeClock()
                    )
                expected = (
                    ("health-validation", "HEALTH_INVALID")
                    if case == "health"
                    else ("start-publication", "START_PUBLICATION")
                )
                self.assertEqual(
                    (caught.exception.failure_site, caught.exception.failure_code),
                    expected,
                )

    def test_unknown_error_stop_does_not_leak_exception_text(self):
        inputs = self.inputs()
        self.arm(inputs)
        self.module._publish_stop(inputs, RuntimeError("PRIVATE-SERIAL-SECRET"))
        value = self.module.validate_stop_file()
        self.assertEqual((value["failure_site"], value["failure_code"]), ("internal", "UNCLASSIFIED"))
        self.assertNotIn("PRIVATE-SERIAL-SECRET", self.module.RUN_STOP.read_text())
        self.assertFalse(value["reboot_dispatch_possible"])
        self.assertFalse(value["replay_authorized"])

    def test_partial_arm_publishes_typed_consumed_stop(self):
        inputs = self.inputs()
        self.arm(inputs, complete=False)
        self.module._publish_stop(inputs, OSError("cut"))
        value = self.module.validate_stop_file()
        self.assertEqual(value["stage"], "during-arm-publication")
        self.assertTrue(value["arm_present"])
        self.assertTrue(value["arm_node_valid"])
        self.assertFalse(value["arm_bytes_complete"])
        self.assertFalse(value["reboot_dispatch_possible"])

    def test_run_live_arm_write_cut_is_consumed_and_stopped(self):
        self.sandbox(pass_go=True)
        static = self.module._validated_static_inputs()
        inputs = self.module._validated_execution_inputs(static)

        def partial_arm(path, _value):
            path.parent.mkdir(mode=0o700)
            path.write_bytes(b'{"partial":')
            path.chmod(0o400)
            raise OSError("fixture cut")

        p318 = types.SimpleNamespace(
            AdapterError=type("FixtureAdapterError", (RuntimeError,), {}),
            _durable_arm=partial_arm,
            _prepare_executable_snapshot=lambda *_args, **_kwargs: self.fail(
                "snapshot must not follow a partial arm"
            ),
        )
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ), mock.patch.object(inputs["v1"], "_load_p318", return_value=p318):
            with self.assertRaisesRegex(
                self.module.SuccessorError, "consumed without replay"
            ):
                self.module.run_live(static["authority"])
        stop = self.module.validate_stop_file()
        self.assertEqual(stop["stage"], "during-arm-publication")
        self.assertFalse(stop["reboot_dispatch_possible"])

    def test_preexisting_or_racing_arm_never_mutates_consumed_namespace(self):
        def snapshot(paths):
            values = {}
            for path in paths:
                if not path.exists() and not path.is_symlink():
                    continue
                if path.is_dir() and not path.is_symlink():
                    children = sorted(
                        item.relative_to(path).as_posix()
                        for item in path.rglob("*")
                    )
                    values[str(path)] = ("directory", children)
                    for item in path.rglob("*"):
                        if item.is_file() and not item.is_symlink():
                            values[str(item)] = (
                                item.stat().st_mode & 0o777,
                                item.stat().st_nlink,
                                hashlib.sha256(item.read_bytes()).hexdigest(),
                            )
                elif path.is_file() and not path.is_symlink():
                    values[str(path)] = (
                        path.stat().st_mode & 0o777,
                        path.stat().st_nlink,
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
            return values

        # Exact prior arm, no run: rejection must not manufacture stop/raw.
        inputs = self.inputs(pass_go=True)
        static = self.module._validated_static_inputs()
        self.arm(inputs)
        before = snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT])
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ):
            with self.assertRaisesRegex(self.module.SuccessorError, "replay is forbidden"):
                self.module.run_live(static["authority"])
        self.assertEqual(snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT]), before)
        self.assertFalse(self.module.RUN_DIR.exists())
        self.assertFalse(self.module.RAW_ROOT.exists())

        # A complete prior success namespace is equally immutable: no stop may
        # be appended to its start/result/raw evidence.
        inputs = self.inputs(pass_go=True)
        static = self.module._validated_static_inputs()
        self.complete_host_fixture(inputs)
        before = snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT])
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ):
            with self.assertRaisesRegex(self.module.SuccessorError, "replay is forbidden"):
                self.module.run_live(static["authority"])
        self.assertEqual(snapshot([self.module.RUN_PARENT, self.module.ADB_SNAPSHOT]), before)
        self.assertFalse(self.module.RUN_STOP.exists())

        # A concurrent O_EXCL loser returns the exact P3.18 duplicate error and
        # owns no path, even if the preflight raced with another invocation.
        inputs = self.inputs(pass_go=True)
        static = self.module._validated_static_inputs()
        p318 = inputs["v1"]._load_p318(inputs["v1_inputs"]["p318_payload"])
        with mock.patch.object(
            self.module, "_validated_static_inputs", return_value=static
        ), mock.patch.object(
            self.module, "_validated_execution_inputs", return_value=inputs
        ), mock.patch.object(
            self.module, "_preflight_new_run_namespace", return_value=None
        ), mock.patch.object(
            inputs["v1"], "_load_p318", return_value=p318
        ), mock.patch.object(
            p318,
            "_durable_arm",
            side_effect=p318.AdapterError("D1 approval arm already exists"),
        ):
            with self.assertRaisesRegex(self.module.SuccessorError, "replay is forbidden"):
                self.module.run_live(static["authority"])
        self.assertFalse(self.module.RUN_ARM.exists())
        self.assertFalse(self.module.RUN_DIR.exists())
        self.assertFalse(self.module.RAW_ROOT.exists())
        self.assertFalse(self.module.ADB_SNAPSHOT.exists())

    def test_stop_is_no_clobber(self):
        inputs = self.inputs()
        self.arm(inputs)
        self.module._publish_stop(inputs, RuntimeError("one"))
        first = self.module.RUN_STOP.read_bytes()
        with self.assertRaises(Exception):
            self.module._publish_stop(inputs, RuntimeError("two"))
        self.assertEqual(self.module.RUN_STOP.read_bytes(), first)

    def test_namespace_attacks_fail_closed(self):
        inputs = self.inputs()
        self.arm(inputs)
        (self.module.RUN_PARENT / "extra").write_bytes(b"x")
        with self.assertRaises(self.module.SuccessorError):
            self.module._publish_stop(inputs, RuntimeError("x"))
        self.assertFalse(self.module.RUN_STOP.exists())

    def test_symlink_and_hardlink_namespace_attacks_fail_closed(self):
        inputs = self.inputs()
        self.arm(inputs)
        os.link(self.module.RUN_ARM, Path(self.module.RUN_PARENT).parent / "arm-link")
        with self.assertRaises(self.module.SuccessorError):
            self.module._publish_stop(inputs, RuntimeError("x"))
        self.assertFalse(self.module.RUN_STOP.exists())

        inputs = self.inputs()
        self.arm(inputs)
        foreign = Path(self.module.RUN_PARENT).parent / "foreign-run"
        foreign.mkdir(mode=0o700)
        self.module.RUN_DIR.symlink_to(foreign, target_is_directory=True)
        with self.assertRaises(self.module.SuccessorError):
            self.module._publish_stop(inputs, RuntimeError("x"))
        self.assertFalse(self.module.RUN_STOP.exists())

    def test_raw_receipt_replacement_is_rejected(self):
        inputs = self.inputs()
        self.arm(inputs)
        self.raw_root(inputs)
        module, _p318 = self.module._pinned_base(inputs)
        client = ScriptedClient(module.d0, inputs["raw"])
        transport = self.make_transport(inputs, client)
        transport.select_exact()
        stdout = next(self.module.RAW_ADB_DIR.glob("*.stdout.bin"))
        stdout.chmod(0o600)
        with self.assertRaises((self.module.SuccessorError, Exception)):
            self.module._raw_inventory(inputs["raw"])

    def test_bool_int_and_unallowlisted_stop_mutations_reject(self):
        inputs = self.inputs()
        self.arm(inputs)
        self.module._publish_stop(inputs, RuntimeError("x"))
        value = self.module.validate_stop_file()
        for mutate in (
            lambda item: item.__setitem__("replay_authorized", 0),
            lambda item: item.__setitem__("failure_code", "PRIVATE_ERROR"),
        ):
            changed = copy.deepcopy(value)
            mutate(changed)
            with self.assertRaises(self.module.SuccessorError):
                self.module.validate_stop(changed, inputs=inputs)

    def test_duplicate_json_keys_and_bool_int_binding_are_rejected(self):
        with self.assertRaises(self.module.SuccessorError):
            self.module._strict(b'{"a":1,"a":2}\n', "fixture")
        self.sandbox()
        value = json.loads(self.module.BINDING_MANIFEST.read_text())
        value["bounds"]["reboot_count"] = True
        self.module.BINDING_MANIFEST.write_bytes(self.module.canonical(value))
        with self.assertRaises(self.module.SuccessorError):
            self.module._validated_static_inputs()

    def test_tracked_binding_is_canonical_pass_go_and_self_bound(self):
        payload = BINDING.read_bytes()
        value = json.loads(payload)
        self.assertEqual(payload, self.module.canonical(value))
        self.assertEqual(
            value["independent_review"],
            {"status": "pass-go", "verdict": self.module.REVIEW_VERDICT},
        )
        self.assertEqual(value["run"]["ordinal"], "d1-fresh-baseline-2")
        self.assertEqual(value["successor"]["size"], SOURCE.stat().st_size)
        self.assertEqual(
            value["successor"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        )
        self.assertEqual(len(payload), 5351)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9",
        )

    def test_report_ledger_and_goal_preserve_v1_and_resolve_only_topic_42(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "PASS_GO_P319_D1_FRESH_BASELINE_RAW_FIRST_V2_H0_CAPABILITY_V1",
            "does not rewrite the incident receipt",
            "d1-fresh-baseline-2",
            "5,300-byte",
            "review-pending execution binding",
            "5,351-byte canonical binding",
            "14-handle/42-child",
            "prior successful start/result/raw",
            "connected-but-not-ready",
            "FRESH_BASELINE_MISSING",
            "no token was issued",
            "remains pinned to the V1",
        ):
            self.assertIn(token, report)
        review = REVIEW_REPORT.read_text(encoding="utf-8")
        for token in (
            "694ad3ad53",
            "917daa0257fda4b6bd784bf303ef9226b744ba0ce458e1bbfc4b7a48721cef8f",
            "65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9",
            "capability data only",
            "D0 consumer remains",
            "FRESH_BASELINE_MISSING",
        ):
            self.assertIn(token, review)
        ledger = LEDGER.read_text(encoding="utf-8")
        ordinal = "h0-d1-fresh-baseline-raw-first-successor-42"
        rows = [line for line in ledger.splitlines() if f" | {ordinal} | " in line]
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "P319_D1_FRESH_BASELINE_RAW_FIRST_V2_IMPLEMENTED_REVIEW_PENDING",
            rows[0],
        )
        self.assertNotIn("PASS_GO", rows[0])
        review_ordinal = "h0-d1-fresh-baseline-raw-first-successor-review-42"
        review_rows = [
            line for line in ledger.splitlines() if f" | {review_ordinal} | " in line
        ]
        self.assertEqual(len(review_rows), 1)
        self.assertIn(self.module.REVIEW_VERDICT, review_rows[0])
        self.assertIn("60/43/17", review_rows[0])
        goal = GOAL.read_text(encoding="utf-8")
        self.assertEqual(len(goal.splitlines()), 900)
        self.assertIn("independently reviewed V2 H0 capability", goal)
        self.assertIn("5351B/65e2953e", goal)
        self.assertIn("12394B/2d5fc042", goal)


if __name__ == "__main__":
    unittest.main()
