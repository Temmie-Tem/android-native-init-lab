import copy
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/device_action_d0_v2.py"
REVALIDATION = SCRIPT.parent
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
MANIFEST = (
    ROOT
    / "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1c_process_v2_draft.json"
)
P318_MANIFEST = (
    ROOT
    / "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p318_process_v2_ready_1.json"
)

sys.path.insert(0, str(REVALIDATION))
try:
    import prepare_s22plus_fyg8_p292_ready_manifest as p292_builder
    import s22plus_fyg8_p292_repair_decoder as p292_decoder
    import s22plus_fyg8_p292_repair_model as p292_model
finally:
    sys.path.remove(str(REVALIDATION))


def load_module():
    sys.path.insert(0, str(REVALIDATION))
    try:
        spec = importlib.util.spec_from_file_location("device_action_d0_v2", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(REVALIDATION))


class FakeClient:
    def __init__(self, profile, marker=b"clean retained log\n"):
        target = profile["target"]
        health = profile["start_health"]
        self.serials = ["fixture-serial", "fixture-serial"]
        self.topologies = ["usb:3-1", "usb:3-1"]
        self.property_values = {
            "model": target["model"],
            "device": target["device"],
            "bootloader": target["firmware_incremental"],
            "incremental": target["firmware_incremental"],
            "boot_completed": "1",
            "bootanim": "stopped",
            "verified_boot_state": health["verified_boot_state"],
            "boot_id": "12345678-1234-1234-1234-123456789abc",
            "kernel_release": "fixture-kernel",
        }
        self.property_sequence = None
        self.root_values = {
            "root": "uid=0(root) gid=0(root)",
            "boot": health["boot_sha256"],
            **health["supporting_partition_sha256"],
        }
        self.payload = marker
        self.calls = []

    def receipt(self):
        self.calls.append("receipt")
        return {
            "path": "/fixture/adb",
            "size": 1,
            "sha256": "a" * 64,
            "version_output_sha256": "b" * 64,
        }

    def one_serial(self):
        self.calls.append("one_serial")
        return self.serials.pop(0)

    def topology(self, _serial):
        self.calls.append("topology")
        return self.topologies.pop(0)

    def properties(self, _serial):
        self.calls.append("properties")
        if self.property_sequence is not None:
            return copy.deepcopy(self.property_sequence.pop(0))
        return copy.deepcopy(self.property_values)

    def root_health(self, _serial):
        self.calls.append("root_health")
        return copy.deepcopy(self.root_values)

    def capture(self, _serial, source, destination):
        self.calls.append(("capture", source))
        destination.write_bytes(self.payload)
        destination.with_suffix(destination.suffix + ".stderr").write_bytes(b"")
        return {
            "path": str(destination),
            "bytes": len(self.payload),
            "sha256": hashlib.sha256(self.payload).hexdigest(),
            "read_to_eof": True,
            "stderr_bytes": 0,
            "elapsed_sec": 0.01,
        }


class DeviceActionD0V2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.p318_manifest = json.loads(P318_MANIFEST.read_text(encoding="utf-8"))

    def bundle(self, profile=None, manifest=None):
        return self.module.f1.Bundle(
            profile or copy.deepcopy(self.profile),
            manifest or copy.deepcopy(self.manifest),
            {},
            "b" * 64,
        )

    def p292_manifest(self):
        run_manifest = {
            "profile": "E2",
            "run_id": "12" * 16,
            "source_contract_id": p292_builder.SOURCE_CONTRACT_ID,
            "decoder": p292_decoder.DECODER_ID,
            "policy_id": p292_decoder.POLICY_ID,
            "records": {
                "long_family_hex": p292_model.LONG_FAMILY.hex(),
                "unsat_family_hex": p292_model.UNSAT_FAMILY.hex(),
                "terminal_stage": self.module.f1.typed_evidence._latest_stage_terminal(
                    p292_decoder, "E2"
                ),
            },
            "observation_contract": {
                "minimum_success_count": 1,
                "clean_baseline_required": True,
            },
        }
        paths = {
            "candidate_static": ROOT / "workspace/private/p292-candidate-static.json",
            "run_manifest": ROOT / "workspace/private/p292-run-manifest.json",
            "static_check": ROOT / "workspace/private/p292-static-check.json",
        }
        receipts = {
            name: {"size": index + 1, "sha256": f"{index + 1:064x}"}
            for index, name in enumerate(paths)
        }
        return p292_builder.derive_manifest(
            root=ROOT,
            run_manifest=run_manifest,
            evidence_paths=paths,
            evidence_receipts=receipts,
            candidate_ap={
                "path": "workspace/private/p292-candidate/AP.tar.md5",
                "size": 10,
                "sha256": "a" * 64,
            },
            rollback_ap=copy.deepcopy(self.profile["rollback"]["ap"]),
            target_profile=PROFILE,
            manifest_id="s22plus-fyg8-p292-d0-fixture",
            live_run_id="s22plus-fyg8-p292-d0-fixture",
            timeout_sec=300,
        )

    def usb_root(self, root: Path, *, download=False):
        usb = root / "usb"
        entry = usb / "3-1"
        entry.mkdir(parents=True)
        (entry / "idVendor").write_text("04e8\n", encoding="utf-8")
        (entry / "idProduct").write_text(
            "685d\n" if download else "6860\n", encoding="utf-8"
        )
        (entry / "product").write_text(
            "SAMSUNG USB\n" if download else "Android\n", encoding="utf-8"
        )
        (entry / "manufacturer").write_text("Samsung\n", encoding="utf-8")
        return usb

    def run_connected(self, client=None, *, download=False, bundle=None):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        run_dir = root / "run"
        run_dir.mkdir()
        usb = self.usb_root(root, download=download)
        client = client or FakeClient(self.profile)
        result = self.module.collect_connected(
            bundle or self.bundle(), run_dir, client, usb
        )
        return temporary, result, client

    def test_connected_pass_is_read_only_and_redacts_target_identifiers(self):
        temporary, result, client = self.run_connected()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["verdict"], self.module.D0_VERDICT)
        self.assertTrue(result["device_contact"])
        for key in (
            "device_writes",
            "reboot_requested",
            "download_transition_requested",
            "odin_invoked",
            "partition_transfer",
            "f1_authorized",
            "live_authorized",
        ):
            self.assertFalse(result[key])
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn("fixture-serial", encoded)
        self.assertNotIn("usb:3-1", encoded)
        self.assertTrue((Path(temporary.name) / "run/result.json").is_file())
        self.assertEqual(client.calls.count("root_health"), 1)
        self.assertEqual(client.calls.count("properties"), 2)

    def test_connected_p292_fixture_passes_same_parser_and_validator(self):
        manifest = self.p292_manifest()
        temporary, result, client = self.run_connected(
            bundle=self.bundle(manifest=manifest)
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["verdict"], self.module.D0_VERDICT)
        self.assertTrue(result["observer"]["baseline_clean"])
        self.assertEqual(
            manifest["observation"]["acceptance"]["source_contract_id"],
            p292_builder.SOURCE_CONTRACT_ID,
        )
        self.module.validate_result(
            result,
            self.bundle(manifest=manifest),
            Path(temporary.name) / "run",
        )
        self.assertEqual(client.calls.count("root_health"), 1)

    def test_target_evidence_binds_profile_and_topology_digests(self):
        temporary, result, _client = self.run_connected()
        self.addCleanup(temporary.cleanup)
        evidence = result["target_evidence"]
        self.module.f1.validate_target_evidence(self.profile, evidence)
        target = evidence["targets"][0]
        self.assertEqual(
            target["adb_serial_sha256"], hashlib.sha256(b"fixture-serial").hexdigest()
        )
        self.assertEqual(
            target["usb_topology_sha256"], hashlib.sha256(b"usb:3-1").hexdigest()
        )

    def test_same_ring_baseline_checks_both_families_and_edge_partials(self):
        evidence = self.module.f1.typed_evidence
        decoder = evidence.same_ring
        manifest = copy.deepcopy(self.manifest)
        manifest["observation"]["acceptance"] = {
            "kind": evidence.SAME_RING_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": evidence.SAME_RING_DECODER,
            "contract_id": evidence.SAME_RING_CONTRACT_ID,
            "records": {
                "entry_hex": decoder.ENTRY_PROOF.hex(),
                "userspace_hex": decoder.USERSPACE_PROOF.hex(),
                "unsat_hex": decoder.UNSAT_PROOF.hex(),
            },
            "families": {
                "long_hex": decoder.ENTRY_FAMILY.hex(),
                "unsat_hex": decoder.UNSAT_FAMILY.hex(),
            },
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "exact_count": 1,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/run.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
                "static_check": {
                    "path": "workspace/private/static.json",
                    "size": 1,
                    "sha256": "2" * 64,
                },
            },
        }
        bundle = self.bundle(manifest=manifest)
        temporary, result, _client = self.run_connected(bundle=bundle)
        self.addCleanup(temporary.cleanup)
        self.assertTrue(result["observer"]["baseline_clean"])

        for payload in (
            decoder.ENTRY_PROOF,
            decoder.UNSAT_PROOF,
            b"prefix" + decoder.UNSAT_PROOF[:12],
        ):
            with self.subTest(payload=payload.hex()):
                with tempfile.TemporaryDirectory() as temporary_name:
                    root = Path(temporary_name)
                    run_dir = root / "run"
                    run_dir.mkdir()
                    usb = self.usb_root(root)
                    client = FakeClient(self.profile, marker=payload)
                    with self.assertRaisesRegex(
                        self.module.D0Error, "durable D0 stop result"
                    ):
                        self.module.collect_connected(
                            bundle, run_dir, client, usb
                        )
                    stop = json.loads((run_dir / "result.json").read_bytes())
                    self.assertEqual(
                        stop["stop"]["reason"], "retained-evidence-present"
                    )
                    self.assertFalse(stop["stop"]["final_health_observed"])
                    self.module.validate_stop_result(stop, bundle, run_dir)

    def test_p318_decoder_rejection_is_normalized_into_durable_stop_result(self):
        acceptance = self.p318_manifest["observation"]["acceptance"]
        model = self.module.f1.typed_evidence.p318_max77705_decoder.model
        payload = model.initialize_record(
            acceptance["profile"], bytes.fromhex(acceptance["run_id"])
        )
        bundle = self.bundle(manifest=copy.deepcopy(self.p318_manifest))
        client = FakeClient(self.profile, marker=payload)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaisesRegex(
                self.module.D0Error, "durable D0 stop result"
            ):
                self.module.collect_connected(
                    bundle, run_dir, client, self.usb_root(root)
                )
            stop_path = run_dir / "result.json"
            self.assertEqual(stop_path.stat().st_mode & 0o777, 0o400)
            stop = json.loads(stop_path.read_bytes())
            self.assertEqual(stop["schema"], self.module.D0_STOP_RESULT_SCHEMA)
            self.assertEqual(stop["version"], self.module.D0_STOP_VERSION)
            self.assertEqual(stop["verdict"], self.module.D0_STOP_VERDICT)
            self.assertEqual(stop["stop"]["reason"], "baseline-decoder-rejected")
            self.assertFalse(stop["usb"]["final_observed"])
            self.assertFalse(stop["stop"]["final_target_continuity_observed"])
            self.assertFalse(stop["stop"]["final_health_observed"])
            self.assertFalse(stop["stop"]["result_reusable"])
            self.assertEqual(stop["observer"]["bytes"], len(payload))
            self.assertEqual(
                stop["observer"]["sha256"], hashlib.sha256(payload).hexdigest()
            )
            self.module.validate_stop_result(stop, bundle, run_dir)
            self.assertEqual(client.calls.count("one_serial"), 1)
            self.assertEqual(client.calls.count("properties"), 1)

            changed = copy.deepcopy(stop)
            changed["stop"]["reason"] = "retained-evidence-present"
            with self.assertRaises(self.module.D0Error):
                self.module.validate_stop_result(changed, bundle, run_dir)
            changed = copy.deepcopy(stop)
            changed["stop"]["final_health_observed"] = True
            with self.assertRaises(self.module.D0Error):
                self.module.validate_stop_result(changed, bundle, run_dir)
            for section, key, value in (
                ("observer", "stderr_bytes", False),
                ("observer", "path", 1),
                ("initial_usb", "download_endpoint_count", False),
            ):
                with self.subTest(section=section, key=key):
                    changed = copy.deepcopy(stop)
                    if section == "initial_usb":
                        changed["usb"]["initial"][key] = value
                    else:
                        changed[section][key] = value
                    with self.assertRaises(self.module.D0Error):
                        self.module.validate_stop_result(changed, bundle, run_dir)
            (run_dir / "baseline-observer.bin").write_bytes(b"changed")
            with self.assertRaises(self.module.D0Error):
                self.module.validate_stop_result(stop, bundle, run_dir)

    def test_durable_result_publication_forces_exact_mode_under_hostile_umask(self):
        with tempfile.TemporaryDirectory() as temporary:
            result_path = Path(temporary) / "result.json"
            previous = os.umask(0o777)
            try:
                self.module.durable_create(result_path, {"fixture": "readable"})
            finally:
                os.umask(previous)
            metadata = result_path.stat()
            self.assertTrue(stat.S_ISREG(metadata.st_mode))
            self.assertEqual(metadata.st_mode & 0o777, 0o400)
            self.assertEqual(metadata.st_nlink, 1)
            self.assertEqual(
                json.loads(result_path.read_bytes()), {"fixture": "readable"}
            )

    def test_connected_cli_returns_clean_error_after_publishing_stop_result(self):
        acceptance = self.p318_manifest["observation"]["acceptance"]
        model = self.module.f1.typed_evidence.p318_max77705_decoder.model
        payload = model.initialize_record(
            acceptance["profile"], bytes.fromhex(acceptance["run_id"])
        )
        bundle = self.bundle(manifest=copy.deepcopy(self.p318_manifest))
        client = FakeClient(self.profile, marker=payload)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            adb = root / "adb"
            adb.write_bytes(b"fixture-adb")
            adb.chmod(0o700)
            usb_root = self.usb_root(root)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch.object(
                    self.module.f1, "verify_bundle", return_value=bundle
                ),
                mock.patch.object(
                    self.module, "allocate_run_dir", return_value=run_dir
                ),
                mock.patch.object(
                    self.module, "adb_client_for_bundle", return_value=client
                ),
                mock.patch.object(self.module, "DEFAULT_USB_ROOT", usb_root),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                rc = self.module.main(
                    [
                        "--connected-read-only",
                        "--manifest",
                        str(root / "manifest.json"),
                        "--adb",
                        str(adb),
                    ]
                )
            self.assertEqual(rc, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("durable D0 stop result was preserved", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
            stop = json.loads((run_dir / "result.json").read_bytes())
            self.module.validate_stop_result(stop, bundle, run_dir)

    def test_result_validator_rejects_authority_and_evidence_tamper(self):
        temporary, result, _client = self.run_connected()
        self.addCleanup(temporary.cleanup)
        run_dir = Path(temporary.name) / "run"
        self.module.validate_result(result, self.bundle(), run_dir)
        for key, value in (
            ("odin_invoked", True),
            ("bundle_sha256", "0" * 64),
        ):
            changed = copy.deepcopy(result)
            changed[key] = value
            with self.assertRaises(self.module.D0Error):
                self.module.validate_result(changed, self.bundle(), run_dir)
        changed = copy.deepcopy(result)
        changed["observer"]["marker_family_count"] = 1
        with self.assertRaises(self.module.D0Error):
            self.module.validate_result(changed, self.bundle(), run_dir)
        for section, key, value in (
            ("observer", "elapsed_sec", 0),
            ("initial", "enumerated_devices", 0),
        ):
            changed = copy.deepcopy(result)
            if section == "observer":
                changed[section][key] = value
            else:
                changed["usb"][section][key] = value
            with self.assertRaises(self.module.D0Error):
                self.module.validate_result(changed, self.bundle(), run_dir)
        changed = copy.deepcopy(result)
        changed["host_tool"]["raw_serial"] = "must-not-be-accepted"
        with self.assertRaises(self.module.D0Error):
            self.module.validate_result(changed, self.bundle(), run_dir)
        stderr_path = run_dir / "baseline-observer.bin.stderr"
        stderr_path.write_bytes(b"unexpected stderr")
        with self.assertRaises(self.module.D0Error):
            self.module.validate_result(result, self.bundle(), run_dir)
        stderr_path.write_bytes(b"")
        (run_dir / "baseline-observer.bin").write_bytes(b"changed")
        with self.assertRaises(self.module.D0Error):
            self.module.validate_result(result, self.bundle(), run_dir)

    def test_wrong_target_or_partition_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            usb = self.usb_root(root)
            for fault in ("model", "boot"):
                run_dir = root / f"run-{fault}"
                run_dir.mkdir()
                client = FakeClient(self.profile)
                if fault == "model":
                    client.property_values["model"] = "SM-S908N"
                else:
                    client.root_values["boot"] = "0" * 64
                with self.assertRaises(self.module.D0Error):
                    self.module.collect_connected(self.bundle(), run_dir, client, usb)
                self.assertFalse((run_dir / "result.json").exists())

    def test_unprofiled_bootloader_value_is_observed_but_not_misbound(self):
        client = FakeClient(self.profile)
        client.property_values["bootloader"] = "separate-bootloader-identity"
        temporary, result, _client = self.run_connected(client)
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["verdict"], self.module.D0_VERDICT)

    def test_health_validator_selects_final_profile_explicitly(self):
        bundle = self.bundle()
        client = FakeClient(self.profile)
        result = self.module.validate_health(
            bundle,
            client.property_values,
            client.root_values,
            True,
            "final_health",
        )
        self.assertTrue(result["root_verified"])
        with self.assertRaises(self.module.D0Error):
            self.module.validate_health(
                bundle,
                client.property_values,
                client.root_values,
                True,
                "unknown",
            )

    def test_marker_contamination_fails_closed(self):
        marker = self.manifest["observation"]["acceptance"]["marker"].encode()
        client = FakeClient(self.profile, b"prefix\n" + marker + b"\n")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaises(self.module.D0Error):
                self.module.collect_connected(
                    self.bundle(), run_dir, client, self.usb_root(root)
                )

    def test_target_change_during_collection_fails_closed(self):
        client = FakeClient(self.profile)
        changed = copy.deepcopy(client.property_values)
        changed["boot_id"] = "abcdefab-cdef-abcd-efab-cdefabcdefab"
        client.property_sequence = [client.property_values, changed]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaises(self.module.D0Error):
                self.module.collect_connected(
                    self.bundle(), run_dir, client, self.usb_root(root)
                )

    def test_download_endpoint_presence_fails_before_adb(self):
        client = FakeClient(self.profile)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaises(self.module.D0Error):
                self.module.collect_connected(
                    self.bundle(), run_dir, client, self.usb_root(root, download=True)
                )
            self.assertEqual(client.calls, ["receipt"])

    def test_empty_usb_inventory_fails_before_adb(self):
        client = FakeClient(self.profile)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            usb = root / "usb"
            usb.mkdir()
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaises(self.module.D0Error):
                self.module.collect_connected(self.bundle(), run_dir, client, usb)
            self.assertEqual(client.calls, ["receipt"])

    def test_unsafe_observer_source_is_rejected_before_capture(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["observation"]["acceptance"]["source"] = "/proc/../data/local/tmp/x"
        client = FakeClient(self.profile)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaises(self.module.D0Error):
                self.module.collect_connected(
                    self.bundle(manifest=manifest),
                    run_dir,
                    client,
                    self.usb_root(root),
                )
            self.assertFalse(any(isinstance(call, tuple) for call in client.calls))

    def test_symlinked_observer_output_is_rejected(self):
        class SymlinkClient(FakeClient):
            def capture(self, _serial, _source, destination):
                target = destination.with_name("target")
                target.write_bytes(b"clean")
                destination.symlink_to(target)
                return {"path": str(destination), "bytes": 5, "sha256": "0" * 64}

        client = SymlinkClient(self.profile)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaises(self.module.D0Error):
                self.module.collect_connected(
                    self.bundle(), run_dir, client, self.usb_root(root)
                )

    def test_adb_shell_uses_one_quoted_remote_argument(self):
        with tempfile.TemporaryDirectory() as temporary:
            adb = Path(temporary) / "adb"
            adb.write_bytes(b"adb")
            adb.chmod(0o700)
            seen = []

            def fake_run(argv, **_kwargs):
                seen.append(argv)
                remote = argv[-1]
                if remote.startswith("sh -c "):
                    values = FakeClient(self.profile).property_values
                    payload = "".join(f"{key}={value}\n" for key, value in values.items())
                else:
                    values = FakeClient(self.profile).root_values
                    payload = "".join(f"{key}={value}\n" for key, value in values.items())
                return self.module.CommandResult(0, payload.encode(), b"")

            client = self.module.AdbReadOnlyClient(adb)
            with mock.patch.object(self.module, "bounded_command", side_effect=fake_run):
                client.properties("fixture-serial")
                client.root_health("fixture-serial")
            self.assertEqual(seen[0][1:4], ["-s", "fixture-serial", "shell"])
            self.assertEqual(seen[1][1:4], ["-s", "fixture-serial", "shell"])
            self.assertEqual(len(seen[0]), 5)
            self.assertEqual(len(seen[1]), 5)
            self.assertTrue(seen[0][4].startswith("sh -c "))
            self.assertTrue(seen[1][4].startswith("su -c "))

    def test_adb_client_selects_exact_s22_without_commanding_other_target(self):
        inventory = (
            "List of devices attached\n"
            "A90SERIAL device product:a90 model:SM_A908N device:a90q transport_id:1\n"
            "S22SERIAL device product:g0qksx model:SM_S906N device:g0q transport_id:2\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            adb = Path(temporary) / "adb"
            adb.write_bytes(b"adb")
            adb.chmod(0o700)
            seen = []

            def fake_run(argv, **_kwargs):
                seen.append(argv)
                return self.module.CommandResult(0, inventory.encode(), b"")

            client = self.module.AdbReadOnlyClient(
                adb, expected_model="SM-S906N", expected_device="g0q"
            )
            with mock.patch.object(
                self.module, "bounded_command", side_effect=fake_run
            ):
                self.assertEqual(client.one_serial(), "S22SERIAL")
                self.assertEqual(client.one_serial(), "S22SERIAL")
            self.assertTrue(all(argv[1:] == ["devices", "-l"] for argv in seen))

    def test_adb_client_rejects_duplicate_or_replacement_s22_before_target_read(self):
        initial = (
            "List of devices attached\n"
            "A90SERIAL device model:SM_A908N device:a90q transport_id:1\n"
            "S22SERIAL device model:SM_S906N device:g0q transport_id:2\n"
        )
        replaced = initial.replace("S22SERIAL", "S22OTHER")
        duplicate = initial + (
            "S22OTHER device model:SM_S906N device:g0q transport_id:3\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            adb = Path(temporary) / "adb"
            adb.write_bytes(b"adb")
            adb.chmod(0o700)
            client = self.module.AdbReadOnlyClient(
                adb, expected_model="SM-S906N", expected_device="g0q"
            )
            inventories = iter((initial, replaced))
            with mock.patch.object(
                self.module,
                "bounded_command",
                side_effect=lambda _argv, **_kwargs: self.module.CommandResult(
                    0, next(inventories).encode(), b""
                ),
            ):
                self.assertEqual(client.one_serial(), "S22SERIAL")
                with self.assertRaisesRegex(
                    self.module.D0Error, "target or inventory changed"
                ):
                    client.one_serial()

            duplicate_client = self.module.AdbReadOnlyClient(
                adb, expected_model="SM-S906N", expected_device="g0q"
            )
            with mock.patch.object(
                self.module,
                "bounded_command",
                return_value=self.module.CommandResult(0, duplicate.encode(), b""),
            ), self.assertRaisesRegex(
                self.module.D0Error, "matching ADB target, found 2"
            ):
                duplicate_client.one_serial()

    def test_run_directory_cannot_escape_private_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            escaped = root / self.module.DEFAULT_RUN_ROOT / "../../../../escape"
            with self.assertRaises(self.module.D0Error):
                self.module.allocate_run_dir(root, escaped)

    def test_cli_exposes_no_control_or_transfer_mode(self):
        options = self.module.build_parser()._option_string_actions
        for forbidden in ("--live", "--flash", "--reboot", "--download", "--odin"):
            self.assertNotIn(forbidden, options)
        self.assertNotIn("--usb-sysfs-root", options)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("execute_odin_boot_only(", source)
        self.assertNotIn("sysrq", source.lower())
        self.assertNotIn("reboot download", source.lower())


if __name__ == "__main__":
    unittest.main()
