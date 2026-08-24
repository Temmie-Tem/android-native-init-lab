from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
D1_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_d1_fresh_baseline.py"
)
REDUCER_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_fresh_baseline_capability.py"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def arm_worker(path: str, value: dict, queue) -> None:
    module = load(
        ROOT / (
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_baseline_rotation_d1.py"
        ),
        f"p318_arm_worker_{multiprocessing.current_process().pid}",
    )
    try:
        module._durable_arm(Path(path), value)
    except Exception as exc:  # pragma: no cover - child reports the type
        queue.put(type(exc).__name__)
    else:
        queue.put("winner")


class FixtureTransport:
    def __init__(self, module, binding):
        self.module = module
        self.binding = binding
        self.serial = "FIXTURE-S22"
        self.reboot_count = 0
        self.poll_count = 0
        self.other_target_commands = 0

    def selection(self):
        return {
            "inventory_count": 2,
            "inventory_models": ["FOREIGN", "SM_S906N"],
            "inventory_sha256": hashlib.sha256(b"fixture inventory").hexdigest(),
            "selected_serial_sha256": self.binding["target"]["adb_serial_sha256"],
            "selected_topology_sha256": hashlib.sha256(b"usb:fixture").hexdigest(),
            "other_targets_commanded": False,
        }

    def select_exact(self):
        return self.serial, self.selection()

    def snapshot(self, serial):
        if serial != self.serial:
            self.other_target_commands += 1
            raise self.module.RotationError("fixture selected another target")
        health = self.binding["health"]
        return {
            "properties": {
                "model": "SM-S906N",
                "device": "g0q",
                "incremental": "S906NKSS7FYG8",
                "boot_completed": "1",
                "bootanim": "stopped",
                "verified_boot_state": health["verified_boot_state"],
                "boot_id": (
                    "22222222-2222-2222-2222-222222222222"
                    if self.reboot_count else
                    "11111111-1111-1111-1111-111111111111"
                ),
                "kernel_release": health["kernel_release"],
            },
            "root_health": {
                "root": "uid=0(root) gid=0(root)",
                "boot": health["boot_sha256"],
                **health["supporting_partition_sha256"],
            },
            "topology": "usb:fixture",
            "no_odin": True,
        }

    def reboot_once(self, serial):
        if serial != self.serial or self.reboot_count:
            raise self.module.RotationError("fixture reboot count differs")
        self.reboot_count += 1

    def poll(self, serial):
        if serial != self.serial:
            self.other_target_commands += 1
            raise self.module.RotationError("fixture polled another target")
        self.poll_count += 1
        if self.poll_count == 1:
            return {"connected": False}
        return {
            "connected": True,
            "ready": True,
            "boot_id": "22222222-2222-2222-2222-222222222222",
        }


class P319D1FreshBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d1 = load(D1_SOURCE, "p319_d1_test")
        cls.reducer = load(REDUCER_SOURCE, "p319_d1_reducer_test")
        cls.p318 = cls.d1._load_p318(cls.d1.P318_WRAPPER.read_bytes())

    @staticmethod
    def write0400(path: Path, payload: bytes) -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o400)

    def fixture_paths(self):
        root = Path(tempfile.mkdtemp(prefix="p319-d1-producer-"))
        run = root / "p319-fresh-baseline-1"
        arm = Path(str(run) + ".arm.json")
        stop = run / "stop.json"
        snapshot = root / "adb-snapshot"
        manifest = root / "binding.json"
        return root, run, arm, stop, snapshot, manifest

    def patched_paths(self, run, arm, stop, snapshot, manifest):
        return (
            mock.patch.multiple(
                self.d1, RUN_DIR=run, RUN_ARM=arm, RUN_STOP=stop,
                ADB_SNAPSHOT=snapshot, BINDING_MANIFEST=manifest,
            ),
            mock.patch.multiple(
                self.reducer, RUN_DIR=run, RUN_ARM=arm,
                D1_EXECUTION_MANIFEST=manifest, D1_ADB_SNAPSHOT=snapshot,
            ),
        )

    def write_manifest(self, manifest: Path, *, pass_go: bool) -> dict:
        d1 = self.d1
        reducer = d1._load_reducer()
        review = (
            {
                "status": "pass-go",
                "verdict": "PASS_GO_P319_D1_FRESH_BASELINE_H0_CAPABILITY_V1",
            }
            if pass_go else {"status": "review-pending", "verdict": None}
        )
        value = d1._expected_manifest(
            script_payload=d1.SCRIPT.read_bytes(),
            reducer_payload=d1.REDUCER.read_bytes(),
            p318_payload=d1.P318_WRAPPER.read_bytes(),
            p296_payload=d1.P296_PRIMITIVE.read_bytes(),
            d0_payload=d1.D0_RUNTIME.read_bytes(),
            reference_payload=d1.REFERENCE_D0.read_bytes(),
            profile_payload=d1.PROFILE.read_bytes(),
            adb_payload=d1.ADB.read_bytes(),
            current_candidate=d1._candidate_binding(reducer),
            review=review,
        )
        manifest.write_bytes(d1.canonical(value))
        return value

    def prepare_inputs(self, *, pass_go: bool = True):
        root, run, arm, stop, snapshot, manifest = self.fixture_paths()
        d1_patch, reducer_patch = self.patched_paths(run, arm, stop, snapshot, manifest)
        d1_patch.start()
        reducer_patch.start()
        self.addCleanup(d1_patch.stop)
        self.addCleanup(reducer_patch.stop)
        self.write_manifest(manifest, pass_go=pass_go)
        snapshot.write_bytes(self.d1.ADB.read_bytes())
        snapshot.chmod(0o500)
        return root, run, arm, stop, snapshot, manifest, self.d1._validated_inputs()

    def test_default_host_fixture_reuses_one_reboot_primitive(self):
        result = self.d1.self_test()
        self.assertEqual(result["reboot_count"], 1)
        self.assertEqual(result["other_target_commands"], 0)
        self.assertFalse(result["device_contact"])
        self.assertEqual(result["review_status"], "pass-go")

    def test_review_pending_and_wrong_approval_stop_before_arm_or_contact(self):
        pending = {
            "manifest": {"independent_review": {"status": "review-pending", "verdict": None}},
            "authority": "expected",
        }
        with mock.patch.object(self.d1, "_validated_inputs", return_value=pending), mock.patch.object(self.d1, "_load_p318") as load_p318:
            with self.assertRaises(self.d1.D1FreshBaselineError):
                self.d1.run_live("expected")
            load_p318.assert_not_called()
        passed = {
            "manifest": {"independent_review": {"status": "pass-go", "verdict": "PASS_GO_P319_D1_FRESH_BASELINE_H0_CAPABILITY_V1"}},
            "authority": "expected",
        }
        with mock.patch.object(self.d1, "_validated_inputs", return_value=passed), mock.patch.object(self.d1, "_load_p318") as load_p318:
            with self.assertRaises(self.d1.D1FreshBaselineError):
                self.d1.run_live("wrong")
            load_p318.assert_not_called()

    def test_live_argv_is_closed(self):
        for argv in (["--live"], ["--live", "--approval", "x", "extra"], ["--adb", "/tmp/adb"]):
            with self.subTest(argv=argv):
                self.assertEqual(self.d1.main(list(argv)), 2)

    def test_arm_precedes_snapshot_and_transport(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        events = []
        fake_p318 = types.SimpleNamespace(
            _durable_arm=lambda path, value: events.append(("arm", path, value)),
            _prepare_executable_snapshot=lambda payload, path: events.append(("snapshot", path)),
        )

        def execute(_inputs, _p318):
            events.append(("execute",))
            self.write0400(run / "result.json", self.d1.canonical({"fixture": True}))

        fake_reducer = types.SimpleNamespace(
            _profile=lambda: {}, _validate_d1=lambda *args: events.append(("validate",))
        )
        inputs["reducer"] = fake_reducer
        with mock.patch.object(self.d1, "_validated_inputs", return_value=inputs), mock.patch.object(self.d1, "_load_p318", return_value=fake_p318), mock.patch.object(self.d1, "_execute_primitive", side_effect=execute), mock.patch.object(self.d1, "_load_reducer", side_effect=AssertionError("second reducer import")):
            self.d1.run_live(inputs["authority"])
        self.assertEqual([item[0] for item in events], ["arm", "snapshot", "execute", "validate"])

    def test_arm_cut_is_typed_only_when_an_arm_file_was_created(self):
        for partial in (False, True):
            with self.subTest(partial=partial):
                root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()

                class FakeAdapterError(RuntimeError):
                    pass

                def cut(path, _value):
                    if partial:
                        self.write0400(path, b'{"partial":true}\n')
                        raise KeyboardInterrupt("fixture post-create arm cut")
                    raise RuntimeError("fixture pre-create arm cut")

                fake_p318 = types.SimpleNamespace(
                    AdapterError=FakeAdapterError,
                    _durable_arm=cut,
                    _prepare_executable_snapshot=mock.Mock(),
                )
                with mock.patch.object(self.d1, "_validated_inputs", return_value=inputs), mock.patch.object(self.d1, "_load_p318", return_value=fake_p318):
                    with self.assertRaises(self.d1.D1FreshBaselineError):
                        self.d1.run_live(inputs["authority"])
                fake_p318._prepare_executable_snapshot.assert_not_called()
                if partial:
                    value = json.loads(stop.read_text())
                    self.assertTrue(value["arm_present"])
                    self.assertFalse(value["arm_bytes_complete"])
                    self.assertFalse(value["replay_authorized"])
                    self.d1.validate_stop(value, inputs=inputs)
                else:
                    self.assertFalse(stop.exists())
                    self.assertFalse(run.exists())

    def test_atomic_arm_has_one_winner_sequential_and_concurrent(self):
        root = Path(tempfile.mkdtemp(prefix="p319-arm-"))
        value = {"schema": "fixture", "consumed": True}
        first = root / "sequential.arm.json"
        self.p318._durable_arm(first, value)
        with self.assertRaises(self.p318.AdapterError):
            self.p318._durable_arm(first, value)
        second = root / "concurrent.arm.json"
        ctx = multiprocessing.get_context("fork")
        queue = ctx.Queue()
        children = [ctx.Process(target=arm_worker, args=(str(second), value, queue)) for _ in range(2)]
        for child in children:
            child.start()
        for child in children:
            child.join(10)
            self.assertEqual(child.exitcode, 0)
        outcomes = sorted(queue.get(timeout=2) for _ in children)
        self.assertEqual(outcomes.count("winner"), 1)
        self.assertEqual(len(outcomes), 2)

    def test_exact_fixture_output_is_accepted_by_reducer(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        self.p318._durable_arm(arm, self.d1._arm_value(inputs))
        transport = {}

        def factory(module, binding):
            value = FixtureTransport(module, binding)
            transport["value"] = value
            return value

        self.d1._execute_primitive(
            inputs, self.p318, transport_factory=factory,
            clock_factory=lambda module: module.FakeClock(),
        )
        result = json.loads((run / "result.json").read_text())
        validated = self.reducer._validate_d1(
            result, inputs["baseline_design"], inputs["candidate"],
            self.reducer._profile(), run / "result.json",
        )
        self.assertEqual(validated["result"]["reboot_count"], 1)
        self.assertEqual(transport["value"].other_target_commands, 0)

    def test_adb_snapshot_mutation_and_replacement_are_rejected(self):
        for mutation in ("content", "hardlink"):
            with self.subTest(mutation=mutation):
                root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
                self.p318._durable_arm(arm, self.d1._arm_value(inputs))
                self.d1._execute_primitive(
                    inputs, self.p318,
                    transport_factory=lambda module, binding: FixtureTransport(module, binding),
                    clock_factory=lambda module: module.FakeClock(),
                )
                result = json.loads((run / "result.json").read_text())
                if mutation == "content":
                    payload = bytearray(snapshot.read_bytes())
                    payload[0] ^= 1
                    snapshot.chmod(0o700)
                    snapshot.write_bytes(payload)
                    snapshot.chmod(0o500)
                else:
                    original = snapshot.read_bytes()
                    snapshot.unlink()
                    foreign = root / "foreign-adb"
                    foreign.write_bytes(original)
                    foreign.chmod(0o500)
                    snapshot.hardlink_to(foreign)
                with self.assertRaises(self.d1.D1FreshBaselineError):
                    self.d1._validate_adb_snapshot(inputs)
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.reducer._validate_d1(
                        result, inputs["baseline_design"], inputs["candidate"],
                        self.reducer._profile(), run / "result.json",
                    )

    def test_profile_is_pinned_for_transport_and_drift_rejects_post_run(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        profile = root / "profile.json"
        original = self.d1.PROFILE.read_bytes()
        profile.write_bytes(original)
        fake_module = types.SimpleNamespace(
            PROFILE=profile,
            RotationError=RuntimeError,
        )
        loader = self.d1._pinned_profile_loader(fake_module, inputs["profile"])
        profile.write_text('{"tampered":true}\n', encoding="utf-8")
        self.assertEqual(loader(profile, "S22+ target profile"), inputs["profile"])
        local = {**inputs, "manifest": copy.deepcopy(inputs["manifest"])}
        local["manifest"]["target_profile"] = {
            "path": self.d1._relative(profile),
            "size": len(original),
            "sha256": hashlib.sha256(original).hexdigest(),
        }
        with mock.patch.object(self.d1, "PROFILE", profile):
            with self.assertRaises(self.d1.D1FreshBaselineError):
                self.d1._validate_profile_post(local)

    def test_post_run_reducer_drift_does_not_import_changed_source(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        reducer = root / "reducer.py"
        original = self.d1.REDUCER.read_bytes()
        reducer.write_bytes(original)
        local = {**inputs, "manifest": copy.deepcopy(inputs["manifest"])}
        local["manifest"]["inputs"]["fresh_baseline_reducer"] = {
            "path": self.d1._relative(reducer),
            "size": len(original),
            "sha256": hashlib.sha256(original).hexdigest(),
        }
        marker = root / "post-run-imported"
        reducer.write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed')\n",
            encoding="utf-8",
        )
        with mock.patch.object(self.d1, "REDUCER", reducer):
            with self.assertRaises(self.d1.D1FreshBaselineError):
                self.d1._validate_reducer_post(local)
        self.assertFalse(marker.exists())
        self.assertIs(local["reducer"], inputs["reducer"])

    def test_tampered_reducer_is_rejected_before_import_side_effect(self):
        root, run, arm, stop, snapshot, manifest = self.fixture_paths()
        candidate = self.d1._candidate_binding(self.d1._load_reducer())
        reducer = root / "reducer.py"
        marker = root / "imported"
        reducer.write_text(
            "def _current_candidate_identity():\n"
            f"    return {candidate!r}\n",
            encoding="utf-8",
        )
        d1_patch, reducer_patch = self.patched_paths(
            run, arm, stop, snapshot, manifest
        )
        with d1_patch, reducer_patch, mock.patch.object(self.d1, "REDUCER", reducer):
            self.write_manifest(manifest, pass_go=True)
            reducer.write_text(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('executed')\n"
                "raise RuntimeError('import side effect')\n",
                encoding="utf-8",
            )
            with self.assertRaises(self.d1.D1FreshBaselineError):
                self.d1._validated_inputs()
        self.assertFalse(marker.exists())

    def test_p318_import_and_post_run_validation_use_only_pinned_bytes(self):
        root = Path(tempfile.mkdtemp(prefix="p319-p318-import-pin-"))
        wrapper = root / "a/b/c/d/e/p318_wrapper.py"
        wrapper.parent.mkdir(parents=True)
        original = self.d1.P318_WRAPPER.read_bytes()
        wrapper.write_bytes(original)
        marker = root / "import-marker"
        marker_source = (
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed')\n"
        ).encode("utf-8")

        with mock.patch.object(self.d1, "P318_WRAPPER", wrapper):
            pinned = self.d1._stable_read(
                wrapper, "fixture P3.18 wrapper",
                expected_size=self.d1.P318_WRAPPER_SIZE,
                expected_sha256=self.d1.P318_WRAPPER_SHA256,
                maximum=self.d1.P318_WRAPPER_SIZE,
            )
            wrapper.write_bytes(marker_source)
            with self.assertRaises(self.d1.D1FreshBaselineError):
                self.d1._load_p318(pinned)
            self.assertFalse(marker.exists())

            wrapper.write_bytes(original)
            self.d1._load_p318(pinned)
            inputs = {
                "p318_payload": pinned,
                "manifest": {
                    "inputs": {
                        "p318_reviewed_wrapper": self.d1._source_receipt(
                            wrapper, pinned
                        )
                    }
                },
            }
            wrapper.write_bytes(marker_source)
            with self.assertRaises(self.d1.D1FreshBaselineError):
                self.d1._validate_p318_post(inputs)
            self.assertFalse(marker.exists())

    def test_reducer_rejects_foreign_manifest_approval_and_journal_paths(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        self.p318._durable_arm(arm, self.d1._arm_value(inputs))
        self.d1._execute_primitive(
            inputs, self.p318,
            transport_factory=lambda module, binding: FixtureTransport(module, binding),
            clock_factory=lambda module: module.FakeClock(),
        )
        good = json.loads((run / "result.json").read_text())
        for mutation in ("manifest", "approval", "path"):
            with self.subTest(mutation=mutation):
                value = copy.deepcopy(good)
                if mutation == "manifest":
                    value["binding"]["execution_manifest"]["sha256"] = "0" * 64
                elif mutation == "approval":
                    value["binding"]["approval_sha256"] = "0" * 64
                else:
                    value["binding"]["journal"]["result"]["path"] = str(root / "foreign.json")
                    value["journal"] = copy.deepcopy(value["binding"]["journal"])
                with self.assertRaises(self.reducer.FreshBaselineError):
                    self.reducer._validate_d1(value, inputs["baseline_design"], inputs["candidate"], self.reducer._profile(), run / "result.json")

    def test_run_namespace_symlink_hardlink_and_extra_child_reject(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        self.p318._durable_arm(arm, self.d1._arm_value(inputs))
        self.d1._execute_primitive(inputs, self.p318, transport_factory=lambda module, binding: FixtureTransport(module, binding), clock_factory=lambda module: module.FakeClock())
        value = json.loads((run / "result.json").read_text())
        extra = run / "extra"
        self.write0400(extra, b"x")
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.reducer._validate_d1(value, inputs["baseline_design"], inputs["candidate"], self.reducer._profile(), run / "result.json")
        extra.unlink()
        start = run / "start.json"
        original = start.read_bytes()
        start.unlink()
        foreign = root / "foreign-start"
        self.write0400(foreign, original)
        start.symlink_to(foreign)
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.reducer._validate_d1(value, inputs["baseline_design"], inputs["candidate"], self.reducer._profile(), run / "result.json")
        start.unlink()
        start.hardlink_to(foreign)
        with self.assertRaises(self.reducer.FreshBaselineError):
            self.reducer._validate_d1(value, inputs["baseline_design"], inputs["candidate"], self.reducer._profile(), run / "result.json")

    def test_topology_selector_rejects_ambiguity_serial_and_drift(self):
        serial = "SERIAL"
        digest = hashlib.sha256(serial.encode()).hexdigest()
        rows = [(serial, "device", {"model:SM_S906N", "device:g0q", "transport_id:1"})]
        target = {"adb_serial_sha256": digest}
        selected = self.p318._select_current_topology(rows, target, "usb:1", None, None)
        self.assertEqual(selected[0], serial)
        with self.assertRaises(self.p318.AdapterError):
            self.p318._select_current_topology(rows + [("SECOND", "device", {"model:SM_S906N", "device:g0q", "transport_id:2"})], target, "usb:1", None, None)
        with self.assertRaises(self.p318.AdapterError):
            self.p318._select_current_topology(rows, {"adb_serial_sha256": "0" * 64}, "usb:1", None, None)
        with self.assertRaises(self.p318.AdapterError):
            self.p318._select_current_topology(rows, target, "usb:2", serial, hashlib.sha256(b"usb:1").hexdigest())

    def test_transport_id_drift_does_not_change_stable_inventory(self):
        serial = "SERIAL"
        target = {"adb_serial_sha256": hashlib.sha256(serial.encode()).hexdigest()}
        one = [(serial, "device", {"model:SM_S906N", "device:g0q", "transport_id:1"})]
        two = [(serial, "device", {"model:SM_S906N", "device:g0q", "transport_id:99"})]
        left = self.p318._select_current_topology(one, target, "usb:1", None, None)[2]
        right = self.p318._select_current_topology(two, target, "usb:1", serial, left["selected_topology_sha256"])[2]
        self.assertEqual(left, right)

    def test_health_rejects_boot_partition_download_and_boot_id(self):
        _root, _run, _arm, _stop, _snapshot, _manifest, inputs = self.prepare_inputs()
        module = self.d1._pinned_base(inputs, self.p318)
        binding = module.fixture_binding()
        transport = module.FixtureTransport(binding)
        snapshot = transport.snapshot(transport.serial)
        snapshot["properties"]["kernel_release"] = "5.10.226-fixture"
        original = module.validate_snapshot
        good = self.d1._health_from_snapshot(module, original, snapshot, binding, initial=True)
        self.assertEqual(good["kernel_release"], "5.10.226-fixture")
        for mutation in ("boot", "partition", "download", "boot_id"):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(snapshot)
                if mutation == "boot":
                    bad["root_health"]["boot"] = "0" * 64
                elif mutation == "partition":
                    bad["root_health"]["recovery"] = "0" * 64
                elif mutation == "download":
                    bad["no_odin"] = False
                else:
                    bad["properties"]["boot_id"] = ""
                with self.assertRaises(module.RotationError):
                    self.d1._health_from_snapshot(module, original, bad, binding, initial=True)

    def test_typed_consumed_stop_after_start(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        self.p318._durable_arm(arm, self.d1._arm_value(inputs))
        run.mkdir(mode=0o700)
        start_value = {
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_start_v1",
            "execution_manifest": inputs["manifest_receipt"],
            "approval_sha256": inputs["approval_sha256"],
            "before": {"fixture": True},
            "selection": {"fixture": True},
            "reboot_count": 1,
            "reboot_requested": True,
            "device_writes": False,
            "candidate_transfer": False,
            "partition_transfer": False,
            "odin_invoked": False,
            "download_transition_requested": False,
            "f1_authorized": False,
        }
        self.write0400(run / "start.json", self.d1.canonical(start_value))
        self.d1._publish_stop(inputs, RuntimeError("fixture"))
        value = json.loads(stop.read_text())
        self.assertTrue(value["reboot_dispatch_possible"])
        self.assertTrue(value["start_bytes_complete"])
        self.assertFalse(value["replay_authorized"])
        self.assertEqual(self.d1.validate_stop_file(), value)
        bad = copy.deepcopy(value)
        bad["reboot_dispatch_possible"] = 1
        with self.assertRaises(self.d1.D1FreshBaselineError):
            self.d1.validate_stop(bad)

    def test_stop_rejects_forged_presence_and_indirect_journal_nodes(self):
        for mutation in ("boolean", "arm_hardlink", "start_symlink"):
            with self.subTest(mutation=mutation):
                root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
                self.p318._durable_arm(arm, self.d1._arm_value(inputs))
                run.mkdir(mode=0o700)
                start = run / "start.json"
                start_value = {
                    "schema": "s22plus_fyg8_p319_d1_fresh_baseline_start_v1",
                    "execution_manifest": inputs["manifest_receipt"],
                    "approval_sha256": inputs["approval_sha256"],
                    "before": {"fixture": True},
                    "selection": {"fixture": True},
                    "reboot_count": 1,
                    "reboot_requested": True,
                    "device_writes": False,
                    "candidate_transfer": False,
                    "partition_transfer": False,
                    "odin_invoked": False,
                    "download_transition_requested": False,
                    "f1_authorized": False,
                }
                self.write0400(start, self.d1.canonical(start_value))
                self.d1._publish_stop(inputs, RuntimeError("fixture"))
                if mutation == "boolean":
                    value = json.loads(stop.read_text())
                    value["start_present"] = False
                    stop.chmod(0o600)
                    stop.write_bytes(self.d1.canonical(value))
                    stop.chmod(0o400)
                elif mutation == "arm_hardlink":
                    payload = arm.read_bytes()
                    arm.unlink()
                    foreign = root / "foreign-arm"
                    self.write0400(foreign, payload)
                    arm.hardlink_to(foreign)
                else:
                    payload = start.read_bytes()
                    start.unlink()
                    foreign = root / "foreign-start"
                    self.write0400(foreign, payload)
                    start.symlink_to(foreign)
                with self.assertRaises(self.d1.D1FreshBaselineError):
                    self.d1.validate_stop_file()

    def test_manifest_duplicate_keys_and_bool_integer_drift_reject(self):
        root, run, arm, stop, snapshot, manifest, inputs = self.prepare_inputs()
        payload = manifest.read_bytes()
        manifest.write_bytes(payload[:-2] + b',"command_count":true}\n')
        with self.assertRaises(self.d1.D1FreshBaselineError):
            self.d1._validated_inputs()
        manifest.write_bytes(b'{"schema":1,"schema":2}\n')
        with self.assertRaises(self.d1.D1FreshBaselineError):
            self.d1._validated_inputs()

    def test_public_manifest_contains_no_active_ap_or_live_run_pair(self):
        value = json.loads(self.d1.BINDING_MANIFEST.read_text())
        rendered = json.dumps(value, sort_keys=True)
        self.assertNotIn("fixed_image", rendered)
        self.assertNotIn("run_id", rendered)
        self.assertEqual(value["current_candidate"]["closure"]["source_keys"]["count"], 437)
        self.assertEqual(value["current_candidate"]["closure"]["module_plan"]["count"], 73)


if __name__ == "__main__":
    unittest.main()
