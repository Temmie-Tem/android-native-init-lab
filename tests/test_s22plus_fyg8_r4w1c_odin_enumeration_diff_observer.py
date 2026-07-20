import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.py"
)
TEST = Path("tests/test_s22plus_fyg8_r4w1c_odin_enumeration_diff_observer.py")
DRAFT = Path(
    "docs/operations/"
    "S22PLUS_FYG8_R4W1C_ODIN_ENUMERATION_DIFF_OBSERVER_EXCEPTION_DRAFT_2026-07-20.md"
)
USB = "/dev/bus/usb/002/019"


def load_module():
    spec = importlib.util.spec_from_file_location("r4w1c_enum_diff_observer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += max(seconds, 0.001)


def node(*, ctime=100, inode=19, mode=0o660, uid=0, gid=46):
    return {
        "path": USB,
        "st_dev": 7,
        "st_ino": inode,
        "st_rdev": os.makedev(189, 146),
        "st_nlink": 1,
        "st_mode": mode,
        "st_uid": uid,
        "st_gid": gid,
        "st_atime_ns": 90,
        "st_mtime_ns": 95,
        "st_ctime_ns": ctime,
        "birth_time_ns": 80,
        "device_major": 189,
        "device_minor": 146,
    }


def sysfs():
    return {
        "topology": "2-1.3",
        "vendor": "04e8",
        "product": "685d",
        "product_text": "SAMSUNG USB",
        "manufacturer": "Samsung",
        "busnum": "2",
        "devnum": "19",
        "devpath": "1.3",
        "serial_state": "absent",
        "serial_sha256": None,
    }


def bundle(current_node=None, extras=None):
    current_node = current_node or node()
    inventory = {USB: current_node}
    inventory.update(extras or {})
    return {
        "captured_at_utc": "2026-07-20T00:00:00.000000Z",
        "download_sysfs_before": {
            "entries": {"2-1.3": sysfs()},
            "races": [],
            "errors": [],
        },
        "usbfs": {"entries": inventory, "races": [], "errors": []},
        "download_sysfs_after": {
            "entries": {"2-1.3": sysfs()},
            "races": [],
            "errors": [],
        },
        "expected_path": USB,
        "expected_node": current_node,
        "capture_errors": [],
        "complete": True,
    }


def stabilization(current_node=None):
    sample = {"sysfs": sysfs(), "node": current_node or node()}
    return {
        "topology": "2-1.3",
        "samples": [sample, dict(sample), dict(sample)],
        "stable_sample": sample,
        "stable_count": 3,
        "elapsed_sec": 0.5,
    }


def odin_result(*, paths=None, returncode=0, timed_out=False):
    return {
        "argv": ["/usr/bin/odin4", "-l"],
        "returncode": returncode,
        "timed_out": timed_out,
        "output_truncated": False,
        "error": None,
        "reported_paths": [USB] if paths is None else paths,
        "reported_path_occurrences": [USB] if paths is None else paths,
        "output_parse_valid": True,
        "stderr_nonempty": False,
        "stdout": {},
        "stderr": {},
        "executable_path_changed": False,
    }


def prepare_consumed_recovery(module, root, authority, binding):
    run_dir = root / module.RUN_ROOT / "interrupted"
    run_dir.mkdir(parents=True)
    state_path = root / module.CONSUMED_STATE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "schema": module.CONSUMED_SCHEMA,
        "target": module.TARGET,
        "authority": authority,
        "android_serial_sha256": "c" * 64,
        "usb_binding": binding,
        "odin": {"sha256": module.EXPECTED_ODIN_SHA256},
        "run_dir": str(run_dir.relative_to(root)),
        "transfer_authorized": False,
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (run_dir / "timeline.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "name": "live_session_start",
                        "timestamp_utc": "2026-07-20T00:00:00.000000Z",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return state, run_dir


class EnumerationDiffObserverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_source_has_no_transfer_artifact_or_rollback_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            ".tar.md5",
            "boot.img.lz4",
            "flash_exact",
            "flash_ap",
            "candidate_ap",
            "magisk_ap",
            "stock_ap",
            "--rollback-from-download",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_source_has_one_exact_odin_listing_callsite(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(
            source.count("process = run_bounded(argv, 10.0, executable_fd=odin_fd)"),
            1,
        )

    def test_source_does_not_import_live_or_transfer_modules(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("import s22plus_", source)

    def test_parser_exposes_only_offline_observation_and_recovery_modes(self):
        parser = self.module.build_parser()
        offline = parser.parse_args(["--offline-check"])
        observe = parser.parse_args(["--observe-download-enumeration"])
        recovery = parser.parse_args(["--recover-consumed-observer"])
        self.assertTrue(offline.offline_check)
        self.assertTrue(observe.observe_download_enumeration)
        self.assertTrue(recovery.recover_consumed_observer)
        for forbidden in ("live", "rollback_from_download", "odin"):
            self.assertFalse(hasattr(observe, forbidden))

    def test_draft_is_inactive_and_contains_required_placeholders(self):
        text = DRAFT.read_text(encoding="utf-8")
        self.assertIn("DRAFT_INACTIVE", text)
        self.assertIn("{{HELPER_SHA256}}", text)
        self.assertIn("{{TEST_SHA256}}", text)
        self.assertIn(self.module.OBSERVE_ACK_TOKEN, text)
        self.assertIn(self.module.DOWNLOAD_CONFIRM_TOKEN, text)
        self.assertIn(self.module.RECOVERY_ACK_TOKEN, text)
        self.assertIn("{{POLICY_DRAFT_SHA256}}", text)
        self.assertIn("{{POLICY_CLAUSE_SHA256}}", text)

    def test_policy_active_returns_false_for_missing_clause(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("no observer clause\n", encoding="utf-8")
            self.assertFalse(self.module.policy_active(root))

    def test_policy_requires_exact_active_lines_and_rejects_retired(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative, payload in (
                (self.module.SCRIPT_RELATIVE, b"helper\n"),
                (self.module.TEST_RELATIVE, b"test\n"),
                (self.module.POLICY_DRAFT, b"draft\n"),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            agents = root / "AGENTS.md"
            agents.write_text(self.module.rendered_policy_clause(root), encoding="utf-8")
            self.assertTrue(self.module.policy_active(root))
            agents.write_text(
                self.module.rendered_policy_clause(root).replace(
                    self.module.POLICY_END,
                    "S22PLUS_FYG8_R4W1C_ENUM_DIFF_OBSERVER_POLICY_STATE=RETIRED\n"
                    + self.module.POLICY_END,
                ),
                encoding="utf-8",
            )
            self.assertFalse(self.module.policy_active(root))

    def test_policy_rejects_skeletal_marker_and_hash_clause(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                self.module.SCRIPT_RELATIVE,
                self.module.TEST_RELATIVE,
                self.module.POLICY_DRAFT,
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("pinned\n", encoding="ascii")
            (root / "AGENTS.md").write_text(
                "\n".join(
                    (
                        self.module.POLICY_BEGIN,
                        self.module.ACTIVE_SENTINEL,
                        self.module.POLICY_MARKER,
                        self.module.POLICY_END,
                        "",
                    )
                ),
                encoding="utf-8",
            )
            self.assertFalse(self.module.policy_active(root))

    def test_rendered_policy_contains_complete_load_bearing_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                self.module.SCRIPT_RELATIVE,
                self.module.TEST_RELATIVE,
                self.module.POLICY_DRAFT,
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("pinned\n", encoding="ascii")
            clause = self.module.rendered_policy_clause(root)
        for required in (
            "android_baseline=boot-complete",
            "stabilization=SIGINT+SIGTERM+SIGHUP-masked-from-each-sample-read-through-exclusive-create-fsync",
            "pre_odin_binding=first-complete-pre-listing-bundle",
            "partial-output-and-original-interruption-preserved-even-if-process-cleanup-fails",
            "immediate-open-no-follow-pin",
            "independently-attempt-after-bundle+command-outcome",
            "odin_output=raw-strict-utf8-path-only-stdout",
            "exclusive-intent-before-contact",
            "authority=whole-observation-or-recovery-session+single-writer",
            "after-non-PASS-preclosure-fsync",
            "result_closure=exclusive-non-PASS-preclosure",
            "timeline=only-events-name-timestamp_utc+canonical-eight-ordered-slots",
            "policy_digest_semantics=embedded-policy-clause-sha256",
            "forbidden=candidate-ap,odin-transfer,flash,partition-write",
        ):
            self.assertIn(required, clause)

    def test_authority_session_is_single_writer_and_detects_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                self.module.SCRIPT_RELATIVE,
                self.module.TEST_RELATIVE,
                self.module.POLICY_DRAFT,
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("pinned\n", encoding="ascii")
            (root / self.module.AUTHORITY_LOCK.parent).mkdir(parents=True, exist_ok=True)
            agents = root / "AGENTS.md"
            agents.write_text(self.module.rendered_policy_clause(root), encoding="utf-8")
            with self.module.authority_session(root) as lease:
                self.module.require_authority_lease(root, lease)
                with self.assertRaisesRegex(self.module.ObserverError, "active authority"):
                    with self.module.authority_session(root):
                        pass
                draft = root / self.module.POLICY_DRAFT
                draft.write_text("mutated\n", encoding="ascii")
                with self.assertRaisesRegex(self.module.ObserverError, "authority changed"):
                    self.module.require_authority_lease(root, lease)

    def test_authority_session_detects_lock_path_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                self.module.SCRIPT_RELATIVE,
                self.module.TEST_RELATIVE,
                self.module.POLICY_DRAFT,
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("pinned\n", encoding="ascii")
            (root / self.module.AUTHORITY_LOCK.parent).mkdir(parents=True, exist_ok=True)
            (root / "AGENTS.md").write_text(
                self.module.rendered_policy_clause(root), encoding="utf-8"
            )
            with self.module.authority_session(root) as lease:
                lock_path = root / self.module.AUTHORITY_LOCK
                lock_path.unlink()
                lock_path.write_text("replacement\n", encoding="ascii")
                with self.assertRaisesRegex(
                    self.module.ObserverError, "lock pathname changed"
                ):
                    self.module.require_authority_lease(root, lease)

    def test_json_bytes_rejects_nan(self):
        with self.assertRaises(ValueError):
            self.module.json_bytes({"value": float("nan")})

    def test_durable_create_is_exclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            receipt = self.module.durable_create_json(path, {"ok": True})
            self.assertEqual(receipt["sha256"], self.module.sha256_file(path))
            with self.assertRaises(FileExistsError):
                self.module.durable_create_json(path, {"ok": False})

    def test_durable_create_rejects_symlink_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            direct = root / "direct"
            direct.mkdir()
            link = root / "link"
            link.symlink_to(direct, target_is_directory=True)
            with self.assertRaises(self.module.ObserverError):
                self.module.durable_create_json(link / "record.json", {"ok": True})

    def test_timeline_is_single_schema_and_strict_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            self.module.append_timeline(path, events, "live_session_start")
            payload = json.loads(path.read_text())
            self.assertEqual(set(payload), {"events"})
            with self.assertRaises(self.module.ObserverError):
                self.module.append_timeline(path, events, "candidate_flash_done")

    def test_node_snapshot_records_complete_tuple(self):
        metadata = SimpleNamespace(
            st_mode=stat.S_IFCHR | 0o660,
            st_dev=7,
            st_ino=19,
            st_rdev=os.makedev(189, 146),
            st_nlink=1,
            st_uid=0,
            st_gid=46,
            st_atime_ns=90,
            st_mtime_ns=95,
            st_ctime_ns=100,
        )
        with mock.patch.object(self.module.os, "stat", return_value=metadata):
            result = self.module.node_snapshot(USB, birth_reader=lambda _path: 80)
        self.assertEqual(result, node())

    def test_node_snapshot_rejects_regular_file(self):
        metadata = SimpleNamespace(st_mode=stat.S_IFREG | 0o600)
        with mock.patch.object(self.module.os, "stat", return_value=metadata):
            with self.assertRaises(self.module.ObserverError):
                self.module.node_snapshot(USB, birth_reader=lambda _path: 80)

    def test_node_snapshot_rejects_mixed_time_tuple(self):
        first = SimpleNamespace(
            st_mode=stat.S_IFCHR | 0o660,
            st_dev=7,
            st_ino=19,
            st_rdev=os.makedev(189, 146),
            st_nlink=1,
            st_uid=0,
            st_gid=46,
            st_atime_ns=90,
            st_mtime_ns=95,
            st_ctime_ns=100,
        )
        second = SimpleNamespace(**{**vars(first), "st_ctime_ns": 101})
        with mock.patch.object(self.module.os, "stat", side_effect=[first, second]):
            with self.assertRaisesRegex(self.module.ObserverError, "birth-time"):
                self.module.node_snapshot(USB, birth_reader=lambda _path: 80)

    def test_usbfs_relation_checks_major_minor_and_path(self):
        self.module.require_usbfs_relation(node(), sysfs())
        bad = node()
        bad["device_minor"] = 147
        with self.assertRaises(self.module.ObserverError):
            self.module.require_usbfs_relation(bad, sysfs())

    def test_inventory_records_disappeared_node_race(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "002").mkdir()
            (root / "002" / "019").touch()
            result = self.module.usbfs_inventory_evidence(
                root=root,
                snapshotter=lambda _path: (_ for _ in ()).throw(FileNotFoundError()),
            )
            self.assertEqual(result["entries"], {})
            self.assertEqual(result["races"], [USB])

    def test_download_sysfs_absence_and_descriptor_race_are_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            absent = self.module.download_sysfs_inventory_evidence(root=missing)
            self.assertEqual(absent["entries"], {})
            self.assertTrue(absent["errors"])
            root = Path(temporary) / "sysfs"
            endpoint = root / "2-1.3"
            endpoint.mkdir(parents=True)
            raced = self.module.download_sysfs_inventory_evidence(root=root)
            self.assertEqual(raced["races"], ["2-1.3"])

    def test_birth_time_parser_preserves_nanoseconds(self):
        value = self.module.parse_birth_time_ns(
            "2026-07-20 16:10:24.751636416 +0900"
        )
        self.assertIsInstance(value, int)
        self.assertEqual(value % 1_000_000_000, 751636416)

    def test_stabilization_requires_three_identical_samples(self):
        clock = FakeClock()
        sample = {"sysfs": sysfs(), "node": node()}
        result = self.module.wait_for_stable_download(
            "2-1.3",
            2.0,
            sampler=lambda _topology: sample,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )
        self.assertEqual(result["stable_count"], 3)
        self.assertEqual(len(result["samples"]), 3)
        self.assertGreaterEqual(result["elapsed_sec"], 0.5)

    def test_stabilization_resets_on_ctime_change(self):
        clock = FakeClock()
        values = [100, 100, 101, 101, 101]

        def sampler(_topology):
            return {"sysfs": sysfs(), "node": node(ctime=values.pop(0))}

        result = self.module.wait_for_stable_download(
            "2-1.3",
            3.0,
            sampler=sampler,
            monotonic=clock.monotonic,
            sleep=clock.sleep,
        )
        self.assertEqual(len(result["samples"]), 5)
        self.assertEqual(result["stable_sample"]["node"]["st_ctime_ns"], 101)

    def test_stabilization_rejects_immutable_change(self):
        clock = FakeClock()
        values = [node(inode=19), node(inode=20)]
        with self.assertRaisesRegex(self.module.ObserverError, "immutable"):
            self.module.wait_for_stable_download(
                "2-1.3",
                2.0,
                sampler=lambda _topology: {
                    "sysfs": sysfs(),
                    "node": values.pop(0),
                },
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

    def test_stabilization_publishes_each_sample_before_failure(self):
        clock = FakeClock()
        values = [node(inode=19), node(inode=20)]
        published = []
        with self.assertRaisesRegex(self.module.ObserverError, "immutable"):
            self.module.wait_for_stable_download(
                "2-1.3",
                2.0,
                sampler=lambda _topology: {
                    "sysfs": sysfs(),
                    "node": values.pop(0),
                },
                monotonic=clock.monotonic,
                sleep=clock.sleep,
                on_sample=lambda index, sample: published.append((index, sample)),
            )
        self.assertEqual([index for index, _sample in published], [1, 2])
        self.assertEqual(published[1][1]["node"]["st_ino"], 20)

    def test_stabilization_defers_sigint_until_collected_sample_is_published(self):
        clock = FakeClock()
        published = []

        def sampler(_topology):
            os.kill(os.getpid(), self.module.signal.SIGINT)
            return {"sysfs": sysfs(), "node": node()}

        with self.assertRaises(KeyboardInterrupt):
            self.module.wait_for_stable_download(
                "2-1.3",
                2.0,
                sampler=sampler,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
                on_sample=lambda index, sample: published.append((index, sample)),
            )
        self.assertEqual([index for index, _sample in published], [1])

    def test_capture_bundle_brackets_sysfs_around_inventory(self):
        calls = []

        def read():
            calls.append("sysfs")
            return {
                "entries": {"2-1.3": sysfs()},
                "races": [],
                "errors": [],
            }

        def inventory():
            calls.append("inventory")
            return {"entries": {USB: node()}, "races": [], "errors": []}

        with mock.patch.object(
            self.module, "download_sysfs_inventory_evidence", side_effect=read
        ), mock.patch.object(
            self.module, "usbfs_inventory_evidence", side_effect=inventory
        ):
            result = self.module.capture_bundle("2-1.3")
        self.assertEqual(calls, ["sysfs", "inventory", "sysfs"])
        self.assertEqual(result["expected_node"], node())
        self.assertTrue(result["complete"])

    def test_capture_bundle_records_download_endpoint_ambiguity(self):
        second = {**sysfs(), "topology": "2-1.4", "devpath": "1.4", "devnum": "20"}
        sysfs_evidence = {
            "entries": {"2-1.3": sysfs(), "2-1.4": second},
            "races": [],
            "errors": [],
        }
        usbfs_evidence = {"entries": {USB: node()}, "races": [], "errors": []}
        with mock.patch.object(
            self.module,
            "download_sysfs_inventory_evidence",
            side_effect=[sysfs_evidence, sysfs_evidence],
        ), mock.patch.object(
            self.module, "usbfs_inventory_evidence", return_value=usbfs_evidence
        ):
            result = self.module.capture_bundle("2-1.3")
        self.assertFalse(result["complete"])
        self.assertIn("download-endpoint-ambiguity-or-absence", result["capture_errors"])

    def test_android_usb_binding_brackets_equal_sysfs_reads(self):
        commands = {
            ("adb", "-s", "TEST0000001", "get-devpath"): "usb:2-1.3",
            ("adb", "-s", "TEST0000001", "get-serialno"): "TEST0000001",
        }

        def command(argv, _timeout):
            return commands[tuple(argv)]

        identity = {
            "vendor": "04e8",
            "product": "6860",
            "serial": "TEST0000001",
            "busnum": "2",
            "devnum": "21",
            "devpath": "1.3",
        }
        with mock.patch.object(self.module, "require_command_text", side_effect=command), mock.patch.object(
            self.module, "android_sysfs_identity", side_effect=[identity, dict(identity)]
        ) as reader:
            binding = self.module.android_usb_binding("TEST0000001")
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(binding["topology"], "2-1.3")

    def test_download_endpoint_inventory_finds_only_exact_download_product(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            android = root / "2-1.2"
            download = root / "2-1.3"
            android.mkdir()
            download.mkdir()
            for directory, product in ((android, "6860"), (download, "685d")):
                values = {
                    "idVendor": "04e8",
                    "idProduct": product,
                    "product": "SAMSUNG USB",
                    "manufacturer": "Samsung",
                    "busnum": "2",
                    "devnum": "19",
                    "devpath": directory.name.split("-", 1)[1],
                }
                for name, value in values.items():
                    (directory / name).write_text(value + "\n", encoding="ascii")
            with mock.patch.object(self.module, "USB_SYSFS_ROOT", root):
                result = self.module.download_endpoint_inventory()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["topology"], "2-1.3")
        self.assertEqual(result[0]["serial_state"], "absent")

    def test_field_diff_reports_exact_nested_fields(self):
        result = self.module.field_diff({"a": {"b": 1}}, {"a": {"b": 2}})
        self.assertEqual(result, [{"field": "a.b", "before": 1, "after": 2}])

    def test_classifies_no_mutation(self):
        result = self.module.classify_observation(
            bundle(), bundle(), odin_result(), stabilization(), "2-1.3"
        )
        self.assertEqual(result["classification"], "OBSERVED_NO_NODE_MUTATION")
        self.assertFalse(result["acceptance_decision"])

    def test_classifies_ctime_only_mutation_without_accepting_it(self):
        result = self.module.classify_observation(
            bundle(node(ctime=100)),
            bundle(node(ctime=101)),
            odin_result(),
            stabilization(node(ctime=100)),
            "2-1.3",
        )
        self.assertEqual(result["classification"], "OBSERVED_CTIME_ONLY_MUTATION")
        self.assertEqual(result["metadata_changes"], ["st_ctime_ns"])
        self.assertFalse(result["acceptance_decision"])

    def test_classifies_other_metadata_mutation(self):
        result = self.module.classify_observation(
            bundle(node(mode=0o600)),
            bundle(node(mode=0o660)),
            odin_result(),
            stabilization(node(mode=0o600)),
            "2-1.3",
        )
        self.assertEqual(result["classification"], "OBSERVED_METADATA_ONLY_MUTATION")
        self.assertEqual(result["metadata_changes"], ["st_mode"])

    def test_classifies_inode_replacement_as_unsafe(self):
        result = self.module.classify_observation(
            bundle(node(inode=19)),
            bundle(node(inode=20)),
            odin_result(),
            stabilization(node(inode=19)),
            "2-1.3",
        )
        self.assertEqual(
            result["classification"],
            "OBSERVED_UNSAFE_OR_INCOMPLETE_ENUMERATION_TRANSITION",
        )
        self.assertIn("immutable-node-fields-changed", result["unsafe_reasons"])

    def test_classifies_inventory_membership_change_as_unsafe(self):
        extra = "/dev/bus/usb/002/020"
        result = self.module.classify_observation(
            bundle(),
            bundle(extras={extra: {**node(), "path": extra}}),
            odin_result(),
            stabilization(),
            "2-1.3",
        )
        self.assertIn("usbfs-inventory-membership-changed", result["unsafe_reasons"])

    def test_classifies_second_download_endpoint_as_unsafe(self):
        after = bundle()
        second = {**sysfs(), "topology": "2-1.4", "devpath": "1.4", "devnum": "20"}
        after["download_sysfs_before"]["entries"]["2-1.4"] = second
        after["download_sysfs_after"]["entries"]["2-1.4"] = second
        after["capture_errors"] = ["download-endpoint-ambiguity-or-absence"]
        after["complete"] = False
        result = self.module.classify_observation(
            bundle(), after, odin_result(), stabilization(), "2-1.3"
        )
        self.assertIn("after-capture-incomplete", result["unsafe_reasons"])

    def test_classifies_wrong_odin_path_as_unsafe(self):
        result = self.module.classify_observation(
            bundle(),
            bundle(),
            odin_result(paths=["/dev/bus/usb/002/020"]),
            stabilization(),
            "2-1.3",
        )
        self.assertIn("odin-output-not-one-expected-path", result["unsafe_reasons"])

    def test_classifies_duplicate_odin_path_as_unsafe(self):
        odin = odin_result()
        odin["reported_path_occurrences"] = [USB, USB]
        result = self.module.classify_observation(
            bundle(), bundle(), odin, stabilization(), "2-1.3"
        )
        self.assertIn("odin-output-not-one-expected-path", result["unsafe_reasons"])

    def test_classifies_stderr_or_unparsed_output_as_unsafe(self):
        odin = odin_result()
        odin["output_parse_valid"] = False
        odin["stderr_nonempty"] = True
        result = self.module.classify_observation(
            bundle(), bundle(), odin, stabilization(), "2-1.3"
        )
        self.assertIn("odin-output-not-strict-listing", result["unsafe_reasons"])
        self.assertIn("odin-stderr-nonempty", result["unsafe_reasons"])

    def test_parser_rejects_any_raw_whitespace_deviation(self):
        for stdout, stderr in (
            ((USB + "\n\n").encode(), b""),
            ((" " + USB).encode(), b""),
            ((USB + " ").encode(), b""),
            ((USB + "\r\n").encode(), b""),
            (USB.encode(), b"\n"),
            (USB.encode(), b" "),
        ):
            with self.subTest(stdout=stdout, stderr=stderr):
                parsed = self.module.parse_odin_listing_output(stdout, stderr)
                self.assertFalse(parsed["valid"])
                self.assertEqual(parsed["stderr_nonempty"], stderr != b"")

    def test_parser_accepts_only_literal_path_with_optional_final_lf(self):
        for stdout in (USB.encode(), (USB + "\n").encode()):
            with self.subTest(stdout=stdout):
                parsed = self.module.parse_odin_listing_output(stdout, b"")
                self.assertTrue(parsed["valid"])
                self.assertEqual(parsed["occurrences"], [USB])

    def test_stabilization_replacement_stops_before_odin(self):
        runner = mock.Mock()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(self.module.ObserverError, "after stabilization"):
                self.module.observe_odin_listing(
                    Path("/usr/bin/odin4"),
                    Path(temporary),
                    "2-1.3",
                    stabilization=stabilization(node(inode=19)),
                    capture=lambda _topology: bundle(node(inode=20)),
                    runner=runner,
                )
        runner.assert_not_called()

    def test_post_odin_capture_precedes_all_post_command_writes(self):
        order = []
        captures = [bundle(), bundle()]
        original_create = self.module.durable_create_bytes

        def capture(_topology):
            order.append(f"capture-{len(order)}")
            return captures.pop(0)

        def runner(_argv, _timeout):
            order.append("runner-return")
            return SimpleNamespace(returncode=0, stdout=(USB + "\n").encode(), stderr=b"")

        def create(path, payload):
            order.append(f"write-{path.name}")
            return original_create(path, payload)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "durable_create_bytes", side_effect=create
        ):
            self.module.observe_odin_listing(
                Path("/usr/bin/odin4"),
                Path(temporary),
                "2-1.3",
                stabilization=stabilization(),
                capture=capture,
                runner=runner,
            )
        runner_index = order.index("runner-return")
        post_capture_index = next(
            index for index in range(runner_index + 1, len(order)) if order[index].startswith("capture-")
        )
        self.assertEqual(post_capture_index, runner_index + 1)
        self.assertLess(post_capture_index, order.index("write-enumeration-after.json"))
        self.assertLess(
            order.index("write-enumeration-after.json"),
            order.index("write-odin-list.stdout"),
        )

    def test_observation_calls_exact_listing_once_and_persists_diff(self):
        captures = [bundle(node(ctime=100)), bundle(node(ctime=101))]
        calls = []

        def runner(argv, timeout):
            calls.append((argv, timeout))
            return SimpleNamespace(returncode=0, stdout=USB.encode(), stderr=b"")

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            result = self.module.observe_odin_listing(
                Path("/usr/bin/odin4"),
                run_dir,
                "2-1.3",
                stabilization=stabilization(node(ctime=100)),
                capture=lambda _topology: captures.pop(0),
                runner=runner,
            )
            self.assertEqual(calls, [(["/usr/bin/odin4", "-l"], 10.0)])
            self.assertTrue((run_dir / "enumeration-before.json").is_file())
            self.assertTrue((run_dir / "enumeration-after.json").is_file())
            self.assertTrue((run_dir / "odin-list.stdout").is_file())
            self.assertTrue((run_dir / "odin-list.stderr").is_file())
            self.assertTrue((run_dir / "enumeration-diff.json").is_file())
            self.assertEqual(
                result["classification"]["classification"],
                "OBSERVED_CTIME_ONLY_MUTATION",
            )

    def test_observation_persists_after_bundle_on_timeout(self):
        captures = [bundle(), bundle()]

        def runner(_argv, _timeout):
            raise self.module.BoundedCommandError(
                "timeout",
                stdout=b"partial",
                timed_out=True,
            )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            result = self.module.observe_odin_listing(
                Path("/usr/bin/odin4"),
                run_dir,
                "2-1.3",
                stabilization=stabilization(),
                capture=lambda _topology: captures.pop(0),
                runner=runner,
            )
            self.assertTrue((run_dir / "enumeration-after.json").is_file())
            self.assertTrue(result["odin"]["timed_out"])
            self.assertEqual((run_dir / "odin-list.stdout").read_bytes(), b"partial")
            self.assertIn(
                "odin-enumeration-failed",
                result["classification"]["unsafe_reasons"],
            )

    def test_observation_rejects_nonzero_truncated_and_empty_listing_results(self):
        cases = (
            (
                "nonzero",
                lambda _argv, _timeout: SimpleNamespace(
                    returncode=1, stdout=USB.encode(), stderr=b""
                ),
                "odin-enumeration-failed",
            ),
            (
                "truncated",
                mock.Mock(
                    side_effect=self.module.BoundedCommandError(
                        "output bound",
                        stdout=USB.encode(),
                        output_truncated=True,
                    )
                ),
                "odin-enumeration-failed",
            ),
            (
                "empty",
                lambda _argv, _timeout: SimpleNamespace(
                    returncode=0, stdout=b"", stderr=b""
                ),
                "odin-output-not-strict-listing",
            ),
        )
        for label, runner, expected_reason in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                result = self.module.observe_odin_listing(
                    Path("/usr/bin/odin4"),
                    Path(temporary),
                    "2-1.3",
                    stabilization=stabilization(),
                    capture=mock.Mock(side_effect=[bundle(), bundle()]),
                    runner=runner,
                )
                self.assertIn(
                    expected_reason, result["classification"]["unsafe_reasons"]
                )
                self.assertFalse(
                    result["classification"]["acceptance_decision"]
                )

    def test_observation_rejects_post_execution_odin_path_replacement(self):
        identity = {"sha256": self.module.EXPECTED_ODIN_SHA256}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "executable_fd_identity", return_value=identity
        ), mock.patch.object(
            self.module,
            "require_path_matches_fd",
            side_effect=self.module.ObserverError("synthetic pathname replacement"),
        ):
            result = self.module.observe_odin_listing(
                Path("/usr/bin/odin4"),
                Path(temporary),
                "2-1.3",
                stabilization=stabilization(),
                odin_fd=9,
                verified_odin=identity,
                capture=mock.Mock(side_effect=[bundle(), bundle()]),
                runner=lambda _argv, _timeout: SimpleNamespace(
                    returncode=0, stdout=USB.encode(), stderr=b""
                ),
            )
        self.assertTrue(result["odin"]["executable_path_changed"])
        self.assertIn(
            "odin-path-identity-changed",
            result["classification"]["unsafe_reasons"],
        )

    def test_observation_defers_interrupt_until_post_evidence_is_sealed(self):
        order = []
        captures = [bundle(), bundle()]
        original_create = self.module.durable_create_bytes

        def capture(_topology):
            order.append("capture")
            return captures.pop(0)

        def runner(_argv, _timeout):
            order.append("runner-interrupt")
            raise KeyboardInterrupt("operator interrupt")

        def create(path, payload):
            order.append(f"write-{path.name}")
            return original_create(path, payload)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "durable_create_bytes", side_effect=create
        ):
            run_dir = Path(temporary)
            with self.assertRaisesRegex(KeyboardInterrupt, "operator interrupt"):
                self.module.observe_odin_listing(
                    Path("/usr/bin/odin4"),
                    run_dir,
                    "2-1.3",
                    stabilization=stabilization(),
                    capture=capture,
                    runner=runner,
                )
            outcome = json.loads(
                (run_dir / "odin-list-command-outcome.json").read_text()
            )
            self.assertTrue((run_dir / "enumeration-after.json").is_file())
            self.assertTrue((run_dir / "odin-list.stdout").is_file())
            self.assertTrue((run_dir / "odin-list-result.json").is_file())
            self.assertTrue((run_dir / "enumeration-diff.json").is_file())
        interrupt_index = order.index("runner-interrupt")
        self.assertEqual(order[interrupt_index + 1], "capture")
        self.assertLess(
            order.index("write-enumeration-after.json"),
            order.index("write-odin-list-command-outcome.json"),
        )
        self.assertLess(
            order.index("write-odin-list-command-outcome.json"),
            order.index("write-odin-list.stdout"),
        )
        self.assertEqual(outcome["exception_type"], "KeyboardInterrupt")
        self.assertFalse(outcome["acceptance_decision"])

    def test_observation_preserves_partial_output_from_command_interruption(self):
        interruption = self.module.CommandInterruption(
            KeyboardInterrupt("operator interrupt"),
            stdout=b"partial-odin-output",
            stderr=b"partial-stderr",
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with self.assertRaisesRegex(KeyboardInterrupt, "operator interrupt"):
                self.module.observe_odin_listing(
                    Path("/usr/bin/odin4"),
                    run_dir,
                    "2-1.3",
                    stabilization=stabilization(),
                    capture=mock.Mock(side_effect=[bundle(), bundle()]),
                    runner=mock.Mock(side_effect=interruption),
                )
            outcome = json.loads(
                (run_dir / "odin-list-command-outcome.json").read_text()
            )
            self.assertEqual(
                (run_dir / "odin-list.stdout").read_bytes(), b"partial-odin-output"
            )
            self.assertEqual(
                (run_dir / "odin-list.stderr").read_bytes(), b"partial-stderr"
            )
        self.assertEqual(outcome["stdout_size"], len(b"partial-odin-output"))
        self.assertEqual(outcome["stderr_size"], len(b"partial-stderr"))

    def test_sigint_during_closure_is_delivered_only_after_evidence(self):
        original_create = self.module.durable_create_bytes
        signal_sent = False

        def create(path, payload):
            nonlocal signal_sent
            if path.name == "enumeration-after.json" and not signal_sent:
                signal_sent = True
                os.kill(os.getpid(), self.module.signal.SIGINT)
            return original_create(path, payload)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "durable_create_bytes", side_effect=create
        ):
            run_dir = Path(temporary)
            with self.assertRaises(KeyboardInterrupt):
                self.module.observe_odin_listing(
                    Path("/usr/bin/odin4"),
                    run_dir,
                    "2-1.3",
                    stabilization=stabilization(),
                    capture=mock.Mock(side_effect=[bundle(), bundle()]),
                    runner=lambda _argv, _timeout: SimpleNamespace(
                        returncode=0, stdout=USB.encode(), stderr=b""
                    ),
                )
            for name in (
                "enumeration-after.json",
                "odin-list-command-outcome.json",
                "odin-list.stdout",
                "odin-list.stderr",
                "odin-list-result.json",
                "enumeration-diff.json",
            ):
                self.assertTrue((run_dir / name).is_file(), name)

    def test_command_outcome_survives_later_raw_evidence_write_failure(self):
        original_create = self.module.durable_create_bytes

        def create(path, payload):
            if path.name == "odin-list.stdout":
                raise OSError("simulated raw evidence write failure")
            return original_create(path, payload)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "durable_create_bytes", side_effect=create
        ):
            run_dir = Path(temporary)
            with self.assertRaisesRegex(
                self.module.ObserverError, "raw evidence write failure"
            ):
                self.module.observe_odin_listing(
                    Path("/usr/bin/odin4"),
                    run_dir,
                    "2-1.3",
                    stabilization=stabilization(),
                    capture=mock.Mock(side_effect=[bundle(), bundle()]),
                    runner=lambda _argv, _timeout: SimpleNamespace(
                        returncode=0, stdout=USB.encode(), stderr=b""
                    ),
                )
            outcome = json.loads(
                (run_dir / "odin-list-command-outcome.json").read_text()
            )
            stderr = (run_dir / "odin-list.stderr").read_bytes()
        self.assertEqual(outcome["returncode"], 0)
        self.assertEqual(outcome["stdout_size"], len(USB.encode()))
        self.assertEqual(
            outcome["stdout_sha256"], self.module.sha256_bytes(USB.encode())
        )
        self.assertEqual(stderr, b"")

    def test_post_capture_persist_failure_still_seals_outcome_and_raw_streams(self):
        original_create = self.module.durable_create_json

        def create(path, payload):
            if path.name == "enumeration-after.json":
                raise OSError("simulated after evidence fsync failure")
            return original_create(path, payload)

        stdout = USB.encode()
        stderr = b"partial-stderr"
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "durable_create_json", side_effect=create
        ):
            run_dir = Path(temporary)
            with self.assertRaisesRegex(
                self.module.ObserverError, "after evidence fsync failure"
            ):
                self.module.observe_odin_listing(
                    Path("/usr/bin/odin4"),
                    run_dir,
                    "2-1.3",
                    stabilization=stabilization(),
                    capture=mock.Mock(side_effect=[bundle(), bundle()]),
                    runner=lambda _argv, _timeout: SimpleNamespace(
                        returncode=0, stdout=stdout, stderr=stderr
                    ),
                )
            outcome = json.loads(
                (run_dir / "odin-list-command-outcome.json").read_text()
            )
            sealed_stdout = (run_dir / "odin-list.stdout").read_bytes()
            sealed_stderr = (run_dir / "odin-list.stderr").read_bytes()
        self.assertIsNone(outcome["post_capture"])
        self.assertEqual(
            outcome["evidence_persist_errors"][0]["path"],
            "enumeration-after.json",
        )
        self.assertEqual(sealed_stdout, stdout)
        self.assertEqual(sealed_stderr, stderr)

    def test_observation_persists_disappearance_and_diff(self):
        after = bundle()
        after["usbfs"]["entries"] = {}
        after["expected_node"] = None
        after["capture_errors"] = ["expected-download-node-absent"]
        after["complete"] = False

        def runner(_argv, _timeout):
            return SimpleNamespace(returncode=0, stdout=USB.encode(), stderr=b"")

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            result = self.module.observe_odin_listing(
                Path("/usr/bin/odin4"),
                run_dir,
                "2-1.3",
                stabilization=stabilization(),
                capture=mock.Mock(side_effect=[bundle(), after]),
                runner=runner,
            )
            recorded = json.loads((run_dir / "enumeration-after.json").read_text())
            diff = json.loads((run_dir / "enumeration-diff.json").read_text())
        self.assertFalse(recorded["complete"])
        self.assertIn("after-capture-incomplete", diff["unsafe_reasons"])
        self.assertFalse(result["classification"]["acceptance_decision"])

    def test_real_runner_timeout_preserves_partial_output(self):
        command = [
            sys.executable,
            "-c",
            "import sys,time;sys.stdout.write('partial');sys.stdout.flush();time.sleep(2)",
        ]
        with self.assertRaises(self.module.BoundedCommandError) as caught:
            self.module.run_bounded(command, 0.2)
        self.assertTrue(caught.exception.timed_out)
        self.assertEqual(caught.exception.stdout, b"partial")

    def test_real_runner_output_bound_preserves_bounded_prefix(self):
        command = [sys.executable, "-c", "print('x' * 128, end='')"]
        with self.assertRaises(self.module.BoundedCommandError) as caught:
            self.module.run_bounded(command, 2.0, maximum=32)
        self.assertTrue(caught.exception.output_truncated)
        self.assertEqual(caught.exception.stdout, b"x" * 32)

    def test_real_runner_interruption_preserves_already_read_output(self):
        selector_factory = self.module.selectors.DefaultSelector

        class InterruptAfterReady:
            def __init__(self):
                self.inner = selector_factory()
                self.returned_ready = False

            def register(self, *args, **kwargs):
                return self.inner.register(*args, **kwargs)

            def unregister(self, *args, **kwargs):
                return self.inner.unregister(*args, **kwargs)

            def get_map(self):
                return self.inner.get_map()

            def select(self, timeout=None):
                if self.returned_ready:
                    raise KeyboardInterrupt("selector interruption")
                ready = self.inner.select(timeout)
                if ready:
                    self.returned_ready = True
                return ready

            def close(self):
                self.inner.close()

        command = [
            sys.executable,
            "-c",
            "import sys,time;sys.stdout.write('partial');sys.stdout.flush();time.sleep(60)",
        ]
        with mock.patch.object(
            self.module.selectors, "DefaultSelector", side_effect=InterruptAfterReady
        ):
            with self.assertRaises(self.module.CommandInterruption) as caught:
                self.module.run_bounded(command, 5.0)
        self.assertIsInstance(caught.exception.original, KeyboardInterrupt)
        self.assertEqual(caught.exception.stdout, b"partial")

    def test_runner_cleanup_failure_preserves_interruption_and_partial_output(self):
        selector_factory = self.module.selectors.DefaultSelector

        class InterruptAfterReady:
            def __init__(self):
                self.inner = selector_factory()
                self.returned_ready = False

            def register(self, *args, **kwargs):
                return self.inner.register(*args, **kwargs)

            def unregister(self, *args, **kwargs):
                return self.inner.unregister(*args, **kwargs)

            def get_map(self):
                return self.inner.get_map()

            def select(self, timeout=None):
                if self.returned_ready:
                    raise KeyboardInterrupt("selector interruption")
                ready = self.inner.select(timeout)
                if ready:
                    self.returned_ready = True
                return ready

            def close(self):
                self.inner.close()

        original_cleanup = self.module.terminate_process_group

        def cleanup_then_fail(process):
            original_cleanup(process)
            raise self.module.ObserverError("synthetic cleanup failure")

        command = [
            sys.executable,
            "-c",
            "import sys,time;sys.stdout.write('partial');sys.stdout.flush();time.sleep(60)",
        ]
        with mock.patch.object(
            self.module.selectors, "DefaultSelector", side_effect=InterruptAfterReady
        ), mock.patch.object(
            self.module, "terminate_process_group", side_effect=cleanup_then_fail
        ):
            with self.assertRaises(self.module.CommandInterruption) as caught:
                self.module.run_bounded(command, 5.0)
        self.assertIsInstance(caught.exception.original, KeyboardInterrupt)
        self.assertEqual(caught.exception.stdout, b"partial")
        self.assertIn("synthetic cleanup failure", caught.exception.cleanup_error)

    def test_real_runner_kills_descendant_pipe_holder_within_bound(self):
        command = [
            sys.executable,
            "-c",
            "import subprocess,sys; child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); print(child.pid, flush=True)",
        ]
        started = __import__("time").monotonic()
        with self.assertRaises(self.module.BoundedCommandError) as caught:
            self.module.run_bounded(command, 0.2)
        self.assertLess(__import__("time").monotonic() - started, 3.0)
        child_pid = int(caught.exception.stdout.strip())
        deadline = __import__("time").monotonic() + 1.0
        while True:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            if __import__("time").monotonic() >= deadline:
                self.fail("descendant process survived bounded group termination")
            __import__("time").sleep(0.01)

    def test_android_return_rejects_nonfinite_timeout_before_contact(self):
        with mock.patch.object(self.module, "android_state") as android:
            with self.assertRaisesRegex(self.module.ObserverError, "timeout is invalid"):
                self.module.wait_for_android_return(None, {}, float("inf"))
        android.assert_not_called()

    def test_fresh_confirmation_rejects_prebuffered_non_tty_input(self):
        with mock.patch.object(self.module.sys.stdin, "fileno", return_value=9), mock.patch.object(
            self.module.os, "isatty", return_value=False
        ), mock.patch.object(
            self.module, "select_with_timeout", return_value=([9], [], [])
        ):
            with self.assertRaisesRegex(self.module.ObserverError, "prebuffered"):
                self.module.fresh_confirmation(1.0)

    def test_wait_for_android_return_retries_until_download_endpoint_is_absent(self):
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "a" * 64,
            "download_serial_state": "absent",
        }
        state = {"model": "SM-S906N"}
        with mock.patch.object(
            self.module, "android_state", return_value=("TEST0000001", state)
        ), mock.patch.object(
            self.module, "android_usb_binding", return_value=binding
        ), mock.patch.object(
            self.module, "download_endpoint_inventory", side_effect=[[sysfs()], []]
        ), mock.patch.object(
            self.module.time, "monotonic", side_effect=[0.0, 0.0, 0.5]
        ), mock.patch.object(self.module.time, "sleep"):
            result = self.module.wait_for_android_return(
                "TEST0000001", binding, 2.0
            )
        self.assertEqual(result["serial"], "TEST0000001")

    def test_android_return_revalidates_continuity_between_contact_attempts(self):
        clock = FakeClock()
        checks = []

        def continuity_check():
            checks.append(len(checks) + 1)
            if len(checks) == 3:
                raise self.module.ObserverError("continuity changed")

        with mock.patch.object(
            self.module, "android_state", side_effect=self.module.ObserverError("not ready")
        ) as android, mock.patch.object(
            self.module.time, "monotonic", side_effect=clock.monotonic
        ), mock.patch.object(self.module.time, "sleep", side_effect=clock.sleep):
            with self.assertRaisesRegex(self.module.ObserverError, "continuity changed"):
                self.module.wait_for_android_return(
                    None,
                    {},
                    2.0,
                    continuity_check=continuity_check,
                )
        self.assertEqual(android.call_count, 1)
        self.assertEqual(checks, [1, 2, 3])

    def test_observe_live_success_has_only_zero_transfer_actions(self):
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "a" * 64,
            "download_serial_state": "absent",
        }
        returned = {
            "serial": "TEST0000001",
            "android": {"model": "SM-S906N"},
            "usb_binding": binding,
        }
        args = SimpleNamespace(
            ack=self.module.OBSERVE_ACK_TOKEN,
            run_dir=None,
            download_wait_sec=2.0,
            confirmation_wait_sec=2.0,
            android_wait_sec=2.0,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / self.module.CONSUMED_STATE.parent).mkdir(parents=True)
            run_dir = root / self.module.RUN_ROOT / "live-success"
            reboot_calls = []
            contact_order = []

            def allocate(*_args):
                run_dir.mkdir(parents=True)
                return run_dir

            def command(argv, timeout):
                reboot_calls.append((argv, timeout))
                contact_order.append("reboot")
                return (0, "", "")

            preclosure_authority_checks = []
            preclosure_consumed_checks = []
            original_consumed_check = self.module.require_consumed_state_pin

            def require_authority(*_args):
                contact_order.append("authority")
                if (run_dir / "result-preclosure.json").exists() and not (
                    run_dir / "result.json"
                ).exists():
                    preclosure_authority_checks.append(True)

            def require_consumed(pin):
                original_consumed_check(pin)
                if (run_dir / "result-preclosure.json").exists() and not (
                    run_dir / "result.json"
                ).exists():
                    preclosure_consumed_checks.append(True)

            def android():
                contact_order.append("android")
                return "TEST0000001", {"model": "SM-S906N"}

            def usb_binding(_serial):
                contact_order.append("binding")
                return binding

            observation = {
                "classification": {
                    "classification": "OBSERVED_CTIME_ONLY_MUTATION",
                    "acceptance_decision": False,
                    "unsafe_reasons": [],
                }
            }
            lease = SimpleNamespace(receipt={"helper_sha256": "a" * 64})
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(
                self.module, "require_authority_lease", side_effect=require_authority
            ), mock.patch.object(
                self.module,
                "open_verified_odin",
                return_value=nullcontext((9, {"sha256": self.module.EXPECTED_ODIN_SHA256})),
            ), mock.patch.object(
                self.module, "allocate_run_dir", side_effect=allocate
            ), mock.patch.object(
                self.module, "android_state", side_effect=android
            ), mock.patch.object(
                self.module, "android_usb_binding", side_effect=usb_binding
            ), mock.patch.object(
                self.module, "download_endpoint_inventory", return_value=[]
            ), mock.patch.object(
                self.module, "require_consumed_state_pin", side_effect=require_consumed
            ), mock.patch.object(
                self.module, "command_text", side_effect=command
            ), mock.patch.object(
                self.module, "wait_for_stable_download", return_value={"stable_count": 3}
            ), mock.patch.object(
                self.module, "fresh_confirmation", return_value=self.module.DOWNLOAD_CONFIRM_TOKEN
            ), mock.patch.object(
                self.module, "observe_odin_listing", return_value=observation
            ), mock.patch.object(
                self.module, "wait_for_android_return", return_value=returned
            ), mock.patch("builtins.print"):
                rc = self.module.observe_live(root, args)
            result = json.loads((run_dir / "result.json").read_text())
            preclosure = json.loads((run_dir / "result-preclosure.json").read_text())
            timeline = json.loads((run_dir / "timeline.json").read_text())
        self.assertEqual(rc, 0)
        self.assertEqual(
            reboot_calls,
            [(["adb", "-s", "TEST0000001", "reboot", "download"], 20.0)],
        )
        self.assertEqual([item["name"] for item in timeline["events"]], list(self.module.TIMELINE_NAMES))
        self.assertTrue(result["odin_enumeration"])
        self.assertFalse(result["odin_transfer"])
        self.assertFalse(result["flash"])
        self.assertFalse(result["acceptance_decision"])
        self.assertEqual(preclosure["verdict"], "PENDING_FINAL_AUTHORITY_VALIDATION")
        self.assertTrue(preclosure_authority_checks)
        self.assertTrue(preclosure_consumed_checks)
        self.assertEqual(
            result["consumed_state_sha256"], result["consumed_state_final_sha256"]
        )
        self.assertEqual(contact_order[:5], [
            "authority", "android", "authority", "binding", "authority"
        ])
        reboot_index = contact_order.index("reboot")
        self.assertEqual(contact_order[reboot_index - 1], "authority")
        self.assertEqual(contact_order[reboot_index + 1], "authority")
        self.assertTrue(
            all(status == "reached" for status in result["timeline_event_status"].values())
        )

    def test_observe_live_failure_after_download_attempts_exact_android_recovery(self):
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "a" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(
            ack=self.module.OBSERVE_ACK_TOKEN,
            run_dir=None,
            download_wait_sec=2.0,
            confirmation_wait_sec=2.0,
            android_wait_sec=2.0,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / self.module.CONSUMED_STATE.parent).mkdir(parents=True)
            run_dir = root / self.module.RUN_ROOT / "live-failure"

            def allocate(*_args):
                run_dir.mkdir(parents=True)
                return run_dir

            def fail_stabilization(_topology, _timeout, *, on_sample):
                on_sample(1, {"sysfs": sysfs(), "node": node()})
                raise self.module.ObserverError("stabilization failed")

            lease = SimpleNamespace(receipt={"helper_sha256": "a" * 64})
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(
                self.module, "require_authority_lease"
            ), mock.patch.object(
                self.module,
                "open_verified_odin",
                return_value=nullcontext((9, {"sha256": self.module.EXPECTED_ODIN_SHA256})),
            ), mock.patch.object(
                self.module, "allocate_run_dir", side_effect=allocate
            ), mock.patch.object(
                self.module, "android_state", return_value=("TEST0000001", {"model": "SM-S906N"})
            ), mock.patch.object(
                self.module, "android_usb_binding", return_value=binding
            ), mock.patch.object(
                self.module, "download_endpoint_inventory", return_value=[]
            ), mock.patch.object(
                self.module, "command_text", return_value=(0, "", "")
            ), mock.patch.object(
                self.module,
                "wait_for_stable_download",
                side_effect=fail_stabilization,
            ), mock.patch.object(
                self.module,
                "wait_for_android_return",
                return_value={"serial": "TEST0000001"},
            ) as recovery, mock.patch("builtins.print"):
                rc = self.module.observe_live(root, args)
            result = json.loads((run_dir / "result.json").read_text())
            timeline = json.loads((run_dir / "timeline.json").read_text())
            sample_exists = (
                run_dir / "download-stabilization-sample-0001.json"
            ).is_file()
        self.assertEqual(rc, 1)
        recovery.assert_called_once()
        self.assertEqual(recovery.call_args.args, ("TEST0000001", binding, 2.0))
        self.assertTrue(callable(recovery.call_args.kwargs["continuity_check"]))
        self.assertEqual(result["failure_recovery_android"]["serial"], "TEST0000001")
        self.assertFalse(result["odin_transfer"])
        self.assertFalse(result["flash"])
        self.assertTrue(sample_exists)
        self.assertEqual(
            [event["name"] for event in timeline["events"]],
            list(self.module.TIMELINE_NAMES),
        )
        self.assertEqual(
            result["timeline_event_status"]["candidate_boot_ready"],
            "not-reached-no-action-placeholder",
        )
        self.assertIn("not milestones", result["timeline_placeholder_semantics"])

    def test_live_consumed_path_replacement_blocks_preclosure_and_final_result(self):
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "a" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(
            ack=self.module.OBSERVE_ACK_TOKEN,
            run_dir=None,
            download_wait_sec=2.0,
            confirmation_wait_sec=2.0,
            android_wait_sec=2.0,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_path = root / self.module.CONSUMED_STATE
            state_path.parent.mkdir(parents=True)
            run_dir = root / self.module.RUN_ROOT / "live-consumed-replaced"

            def allocate(*_args):
                run_dir.mkdir(parents=True)
                return run_dir

            def replace_consumed(*_args):
                state_path.unlink()
                state_path.write_text("{}\n", encoding="ascii")
                return (0, "", "")

            lease = SimpleNamespace(receipt={"helper_sha256": "a" * 64})
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(
                self.module, "require_authority_lease"
            ), mock.patch.object(
                self.module,
                "open_verified_odin",
                return_value=nullcontext(
                    (9, {"sha256": self.module.EXPECTED_ODIN_SHA256})
                ),
            ), mock.patch.object(
                self.module, "allocate_run_dir", side_effect=allocate
            ), mock.patch.object(
                self.module,
                "android_state",
                return_value=("TEST0000001", {"model": "SM-S906N"}),
            ), mock.patch.object(
                self.module, "android_usb_binding", return_value=binding
            ), mock.patch.object(
                self.module, "download_endpoint_inventory", return_value=[]
            ), mock.patch.object(
                self.module, "command_text", side_effect=replace_consumed
            ), mock.patch("builtins.print"):
                with self.assertRaisesRegex(
                    self.module.ObserverError, "changed under active session"
                ):
                    self.module.observe_live(root, args)
            preclosure_exists = (run_dir / "result-preclosure.json").exists()
            result_exists = (run_dir / "result.json").exists()
        self.assertFalse(preclosure_exists)
        self.assertFalse(result_exists)

    def test_reboot_timeout_still_attempts_android_recovery(self):
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "a" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(
            ack=self.module.OBSERVE_ACK_TOKEN,
            run_dir=None,
            download_wait_sec=2.0,
            confirmation_wait_sec=2.0,
            android_wait_sec=2.0,
        )
        order = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / self.module.CONSUMED_STATE.parent).mkdir(parents=True)
            run_dir = root / self.module.RUN_ROOT / "reboot-timeout"

            def allocate(*_args):
                run_dir.mkdir(parents=True)
                return run_dir

            original_consume = self.module.consume_observer

            def consume(*_args):
                order.append("consume")
                return original_consume(*_args)

            def command(*_args):
                order.append("reboot")
                raise self.module.BoundedCommandError("adb timeout", timed_out=True)

            lease = SimpleNamespace(receipt={"helper_sha256": "a" * 64})
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(self.module, "require_authority_lease"), mock.patch.object(
                self.module,
                "open_verified_odin",
                return_value=nullcontext((9, {"sha256": self.module.EXPECTED_ODIN_SHA256})),
            ), mock.patch.object(self.module, "allocate_run_dir", side_effect=allocate), mock.patch.object(
                self.module, "android_state", return_value=("TEST0000001", {"model": "SM-S906N"})
            ), mock.patch.object(self.module, "android_usb_binding", return_value=binding), mock.patch.object(
                self.module, "download_endpoint_inventory", return_value=[]
            ), mock.patch.object(self.module, "consume_observer", side_effect=consume), mock.patch.object(
                self.module, "command_text", side_effect=command
            ), mock.patch.object(
                self.module,
                "wait_for_android_return",
                return_value={"serial": "TEST0000001"},
            ) as recovery, mock.patch("builtins.print"):
                rc = self.module.observe_live(root, args)
            result = json.loads((run_dir / "result.json").read_text())
        self.assertEqual(rc, 1)
        self.assertEqual(order, ["consume", "reboot"])
        recovery.assert_called_once()
        self.assertEqual(recovery.call_args.args, ("TEST0000001", binding, 2.0))
        self.assertTrue(callable(recovery.call_args.kwargs["continuity_check"]))
        self.assertTrue(result["reboot_request_attempted"])
        self.assertFalse(result["reboot_request_returned_cleanly"])

    def test_consumed_recovery_mode_reopens_exact_run_without_odin(self):
        authority = {"helper_sha256": "a" * 64}
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "b" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(
            ack=self.module.RECOVERY_ACK_TOKEN,
            android_wait_sec=2.0,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / self.module.RUN_ROOT / "interrupted"
            run_dir.mkdir(parents=True)
            state_path = root / self.module.CONSUMED_STATE
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "schema": self.module.CONSUMED_SCHEMA,
                "target": self.module.TARGET,
                "authority": authority,
                "android_serial_sha256": "c" * 64,
                "usb_binding": binding,
                "odin": {"sha256": self.module.EXPECTED_ODIN_SHA256},
                "run_dir": str(run_dir.relative_to(root)),
                "transfer_authorized": False,
            }
            state_path.write_text(json.dumps(state), encoding="utf-8")
            (run_dir / "timeline.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "name": "live_session_start",
                                "timestamp_utc": "2026-07-20T00:00:00.000000Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            returned = {"serial": "TEST0000001"}
            lease = SimpleNamespace(receipt=authority)
            preclosure_authority_checks = []
            preclosure_consumed_checks = []
            original_consumed_check = self.module.require_consumed_state_pin

            def require_authority(*_args):
                if (
                    (run_dir / "recovery-result-01-preclosure.json").exists()
                    and not (run_dir / "recovery-result-01.json").exists()
                ):
                    preclosure_authority_checks.append(True)

            def require_consumed(pin):
                original_consumed_check(pin)
                if (
                    (run_dir / "recovery-result-01-preclosure.json").exists()
                    and not (run_dir / "recovery-result-01.json").exists()
                ):
                    preclosure_consumed_checks.append(True)

            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(
                self.module, "require_authority_lease", side_effect=require_authority
            ), mock.patch.object(
                self.module, "require_consumed_state_pin", side_effect=require_consumed
            ), mock.patch.object(
                self.module, "wait_for_android_return", return_value=returned
            ) as waiter, mock.patch("builtins.print"):
                rc = self.module.recover_consumed_observer(root, args)
            result = json.loads((run_dir / "recovery-result-01.json").read_text())
            preclosure = json.loads(
                (run_dir / "recovery-result-01-preclosure.json").read_text()
            )
            timeline = json.loads((run_dir / "timeline.json").read_text())
            self.assertTrue((run_dir / "recovery-attempt-01-intent.json").is_file())
            self.assertTrue(
                (run_dir / "android-after-restarted-recovery-01.json").is_file()
            )
        self.assertEqual(rc, 0)
        waiter.assert_called_once()
        self.assertEqual(waiter.call_args.args, (None, binding, 2.0))
        self.assertEqual(
            waiter.call_args.kwargs["expected_serial_sha256"], "c" * 64
        )
        self.assertTrue(callable(waiter.call_args.kwargs["continuity_check"]))
        self.assertFalse(result["odin_enumeration"])
        self.assertFalse(result["odin_transfer"])
        self.assertEqual(len(timeline["events"]), 8)
        self.assertEqual(preclosure["verdict"], "PENDING_FINAL_AUTHORITY_VALIDATION")
        self.assertTrue(preclosure_authority_checks)
        self.assertTrue(preclosure_consumed_checks)

    def test_recovery_preserves_prior_placeholders_from_sealed_failed_result(self):
        authority = {"helper_sha256": "a" * 64}
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "b" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(ack=self.module.RECOVERY_ACK_TOKEN, android_wait_sec=2.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _state, run_dir = prepare_consumed_recovery(
                self.module, root, authority, binding
            )
            (run_dir / "timeline.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "name": name,
                                "timestamp_utc": "2026-07-20T00:00:00.000000Z",
                            }
                            for name in self.module.TIMELINE_NAMES
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "result.json").write_text(
                json.dumps(
                    {
                        "verdict": "FAIL_R4W1C_ENUM_DIFF_OBSERVER_INCOMPLETE",
                        "actual_timeline_events": [
                            "live_session_start",
                            "candidate_flash_start",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            lease = SimpleNamespace(receipt=authority)
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(
                self.module, "require_authority_lease"
            ), mock.patch.object(
                self.module,
                "wait_for_android_return",
                return_value={"serial": "TEST0000001"},
            ), mock.patch("builtins.print"):
                rc = self.module.recover_consumed_observer(root, args)
            result = json.loads((run_dir / "recovery-result-01.json").read_text())
        self.assertEqual(rc, 0)
        self.assertEqual(
            result["timeline_event_status"]["candidate_boot_ready"],
            "not-reached-no-action-placeholder",
        )
        for name in (
            "rollback_flash_start",
            "rollback_flash_done",
            "rollback_boot_ready",
        ):
            self.assertEqual(
                result["timeline_event_status"][name],
                "not-reached-no-action-placeholder",
            )
        self.assertEqual(result["timeline_event_status"]["live_session_end"], "reached")
        self.assertEqual(
            result["recovery_activity_events"],
            [
                "recovery-wait-start",
                "recovery-android-transport-returned",
                "recovery-exact-android-verified",
            ],
        )

    def test_recovery_rejects_completed_timeline_without_actual_event_semantics(self):
        authority = {"helper_sha256": "a" * 64}
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "b" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(ack=self.module.RECOVERY_ACK_TOKEN, android_wait_sec=2.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _state, run_dir = prepare_consumed_recovery(
                self.module, root, authority, binding
            )
            (run_dir / "timeline.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "name": name,
                                "timestamp_utc": "2026-07-20T00:00:00.000000Z",
                            }
                            for name in self.module.TIMELINE_NAMES
                        ]
                    }
                ),
                encoding="utf-8",
            )
            lease = SimpleNamespace(receipt=authority)
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(self.module, "wait_for_android_return") as waiter:
                with self.assertRaisesRegex(self.module.ObserverError, "lacks durable"):
                    self.module.recover_consumed_observer(root, args)
            intent_exists = (
                run_dir / "recovery-attempt-01-intent.json"
            ).exists()
        waiter.assert_not_called()
        self.assertFalse(intent_exists)

    def test_interrupted_recovery_intent_consumes_slot_and_uses_attempt_two(self):
        authority = {"helper_sha256": "a" * 64}
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "b" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(ack=self.module.RECOVERY_ACK_TOKEN, android_wait_sec=2.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, run_dir = prepare_consumed_recovery(
                self.module, root, authority, binding
            )
            with self.module.validated_consumed_observer(root, authority) as (
                pinned_state,
                pinned_run_dir,
                consumed_pin,
            ):
                attempt, _, _ = self.module.reserve_recovery_attempt(
                    root,
                    pinned_run_dir,
                    pinned_state,
                    authority,
                    consumed_pin,
                )
            self.assertEqual(attempt, 1)
            order = []

            def wait(*_args, **_kwargs):
                self.assertTrue(
                    (run_dir / "recovery-attempt-02-intent.json").is_file()
                )
                order.append("wait")
                return {"serial": "TEST0000001"}

            lease = SimpleNamespace(receipt=authority)
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(self.module, "require_authority_lease"), mock.patch.object(
                self.module, "wait_for_android_return", side_effect=wait
            ), mock.patch("builtins.print"):
                rc = self.module.recover_consumed_observer(root, args)
            result = json.loads((run_dir / "recovery-result-02.json").read_text())
            evidence_exists = (
                run_dir / "android-after-restarted-recovery-02.json"
            ).is_file()
        self.assertEqual(rc, 0)
        self.assertEqual(order, ["wait"])
        self.assertEqual(result["attempt"], 2)
        self.assertTrue(evidence_exists)

    def test_two_recovery_intents_stop_before_third_device_contact(self):
        authority = {"helper_sha256": "a" * 64}
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "b" * 64,
            "download_serial_state": "absent",
        }
        args = SimpleNamespace(ack=self.module.RECOVERY_ACK_TOKEN, android_wait_sec=2.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, run_dir = prepare_consumed_recovery(
                self.module, root, authority, binding
            )
            with self.module.validated_consumed_observer(root, authority) as (
                pinned_state,
                pinned_run_dir,
                consumed_pin,
            ):
                self.module.reserve_recovery_attempt(
                    root, pinned_run_dir, pinned_state, authority, consumed_pin
                )
                self.module.reserve_recovery_attempt(
                    root, pinned_run_dir, pinned_state, authority, consumed_pin
                )
            lease = SimpleNamespace(receipt=authority)
            with mock.patch.object(
                self.module, "authority_session", return_value=nullcontext(lease)
            ), mock.patch.object(self.module, "wait_for_android_return") as waiter:
                with self.assertRaisesRegex(self.module.ObserverError, "twice"):
                    self.module.recover_consumed_observer(root, args)
        waiter.assert_not_called()

    def test_consumed_state_pin_detects_path_replacement(self):
        authority = {"helper_sha256": "a" * 64}
        binding = {
            "topology": "2-1.3",
            "android_serial_sha256": "b" * 64,
            "download_serial_state": "absent",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _state, _run_dir = prepare_consumed_recovery(
                self.module, root, authority, binding
            )
            with self.module.validated_consumed_observer(root, authority) as (
                _pinned_state,
                _pinned_run_dir,
                consumed_pin,
            ):
                state_path = root / self.module.CONSUMED_STATE
                replacement = state_path.with_name("replacement.json")
                replacement.write_bytes(state_path.read_bytes())
                os.replace(replacement, state_path)
                with self.assertRaisesRegex(
                    self.module.ObserverError, "changed under active session"
                ):
                    self.module.require_consumed_state_pin(consumed_pin)

    def test_verify_odin_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "odin"
            target.write_bytes(b"x")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(self.module.ObserverError):
                self.module.verify_odin(link)

    def test_verified_executable_fd_survives_path_replacement(self):
        payload = Path("/bin/echo").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "odin4"
            path.write_bytes(payload)
            path.chmod(0o755)
            digest = self.module.sha256_bytes(payload)
            with mock.patch.object(self.module, "DEFAULT_ODIN", path), mock.patch.object(
                self.module, "EXPECTED_ODIN_SIZE", len(payload)
            ), mock.patch.object(self.module, "EXPECTED_ODIN_SHA256", digest):
                with self.module.open_verified_odin(path) as (descriptor, _identity):
                    path.unlink()
                    path.write_text("replacement\n", encoding="ascii")
                    result = self.module.run_bounded(
                        ["/bin/echo", "sealed"],
                        2.0,
                        executable_fd=descriptor,
                    )
                    with self.assertRaises(self.module.ObserverError):
                        self.module.require_path_matches_fd(path, descriptor)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"sealed\n")

    def test_run_directory_must_be_direct_private_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / self.module.RUN_ROOT).mkdir(parents=True)
            with self.assertRaisesRegex(self.module.ObserverError, "direct child"):
                self.module.allocate_run_dir(root, Path("outside/run"))

    def test_source_surface_audit_passes_current_source(self):
        result = self.module.source_surface_audit(Path.cwd())
        self.assertFalse(result["transfer_surface"])
        self.assertEqual(result["odin_listing_callsites"], 1)

    def test_offline_check_is_device_inert(self):
        args = SimpleNamespace()
        with mock.patch("builtins.print") as printer:
            rc = self.module.offline_check(Path.cwd(), args)
        self.assertEqual(rc, 0)
        payload = json.loads(printer.call_args.args[0])
        self.assertEqual(
            payload["verdict"],
            "PASS_R4W1C_ENUM_DIFF_OBSERVER_SOURCE_OFFLINE_CHECK",
        )
        for field in (
            "device_contact",
            "device_writes",
            "reboot",
            "download_transition",
            "odin_enumeration",
            "odin_transfer",
            "flash",
        ):
            self.assertFalse(payload[field])

    def test_live_mode_fails_before_contact_while_policy_inactive(self):
        args = SimpleNamespace(
            ack=self.module.OBSERVE_ACK_TOKEN,
            run_dir=None,
        )
        with mock.patch.object(self.module, "policy_active", return_value=False), mock.patch.object(
            self.module, "android_state"
        ) as android:
            with self.assertRaisesRegex(self.module.ObserverError, "inactive"):
                self.module.observe_live(Path.cwd(), args)
        android.assert_not_called()


if __name__ == "__main__":
    unittest.main()
