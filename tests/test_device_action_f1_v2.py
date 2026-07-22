import copy
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/device_action_f1_v2.py"
REVALIDATION = SCRIPT.parent


def load_module():
    sys.path.insert(0, str(REVALIDATION))
    try:
        spec = importlib.util.spec_from_file_location("device_action_f1_v2", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(REVALIDATION))


def write_ap(path: Path, members=("boot.img.lz4",)) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w") as archive:
        for member in members:
            payload = f"payload:{path.name}:{member}".encode()
            info = tarfile.TarInfo(member)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    payload = path.read_bytes()
    return {
        "path": str(path.absolute()),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


class DeviceActionF1V2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def fixture(self, root: Path, candidate_members=("boot.img.lz4",)):
        artifacts = root / "artifacts"
        candidate = write_ap(artifacts / "candidate.tar.md5", candidate_members)
        rollback = write_ap(artifacts / "rollback.tar.md5")
        odin_path = artifacts / "odin4"
        odin_path.write_bytes(b"fixture-odin4")
        odin_path.chmod(0o700)
        odin_payload = odin_path.read_bytes()
        odin = {
            "path": "artifacts/odin4",
            "size": len(odin_payload),
            "sha256": hashlib.sha256(odin_payload).hexdigest(),
        }
        health = {
            "android_boot_completed": True,
            "boot_animation_stopped": True,
            "verified_boot_state": "orange",
            "root_required": True,
            "boot_sha256": "1" * 64,
            "supporting_partition_sha256": {
                "vendor_boot": "2" * 64,
                "dtbo": "3" * 64,
                "recovery": "4" * 64,
            },
            "odin_endpoint_absent": True,
        }
        profile = {
            "schema": self.module.PROFILE_SCHEMA,
            "profile_id": "fixture.s22plus.fyg8",
            "health_profile_id": "fixture.s22plus.fyg8.health",
            "target": {
                "model": "SM-S906N",
                "device": "g0q",
                "firmware_incremental": "S906NKSS7FYG8",
                "android_transport": "adb",
                "download": {
                    "usb_vendor_id": "04e8",
                    "usb_product_id": "685d",
                    "product": "SAMSUNG USB",
                    "manufacturer": "Samsung",
                    "serial_policy": "absent",
                },
            },
            "transport": {
                "kind": "odin4_boot_only",
                "allowed_partition": "boot",
                "allowed_member": "boot.img.lz4",
                "odin": odin,
            },
            "rollback": {"kind": "magisk_boot_only", "ap": rollback},
            "start_health": copy.deepcopy(health),
            "final_health": copy.deepcopy(health),
            "recovery": {
                "operator_attended": True,
                "physical_download_required": True,
                "rollback_preapproved": True,
            },
        }
        profile_path = root / "profiles/profile.json"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        manifest = {
            "schema": self.module.MANIFEST_SCHEMA,
            "manifest_id": "fixture.s22plus.fyg8.run",
            "run_id": "fixture-run",
            "status": "draft-host-only",
            "target_profile": "profiles/profile.json",
            "candidate_ap": candidate,
            "rollback_ap": rollback,
            "allowed_member": "boot.img.lz4",
            "observation": {
                "timeout_sec": 300,
                "acceptance": {
                    "kind": "retained_marker_after_rollback",
                    "source": "/proc/last_kmsg",
                    "marker": "[[FIXTURE|pid=1]]",
                    "family": "[[FIXTURE|",
                    "exact_count": 1,
                },
            },
            "final_health_profile": profile["health_profile_id"],
            "runner_version": self.module.RUNNER_VERSION,
        }
        manifest_path = root / "manifests/manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return profile, manifest, profile_path, manifest_path

    def evidence(self, profile, targets=1):
        target = {
            "model": profile["target"]["model"],
            "device": profile["target"]["device"],
            "firmware_incremental": profile["target"]["firmware_incremental"],
            "android_transport": "adb",
            "adb_serial_sha256": "5" * 64,
            "usb_topology_sha256": "6" * 64,
        }
        return {
            "schema": self.module.TARGET_EVIDENCE_SCHEMA,
            "targets": [copy.deepcopy(target) for _ in range(targets)],
            "odin_endpoint_absent": True,
        }

    def test_bundle_validation_and_rendered_plan_are_host_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, _, manifest_path = self.fixture(root)
            bundle = self.module.verify_bundle(root, manifest_path)
            plan = self.module.render_plan(bundle)
            self.assertEqual(plan["status"], "draft-host-only")
            self.assertFalse(plan["device_contact"])
            self.assertFalse(plan["odin_invoked"])
            self.assertFalse(plan["live_authorized"])

    def test_p233_source_only_evidence_is_rejected_by_full_bundle_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, manifest, _, manifest_path = self.fixture(root)
            contracts = root / "contracts"
            contracts.mkdir()

            artifacts = {}
            for name in ("candidate_static", "run_manifest", "static_check"):
                path = contracts / f"{name}.json"
                payload = b"{}"
                path.write_bytes(payload)
                artifacts[name] = {
                    "path": str(path.relative_to(root)),
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }

            decoder = self.module.typed_evidence.e1_latest_stage
            model = decoder.model
            run_id = hashlib.sha256(b"P233-BUNDLE-BLOCK-TEST").digest()[:16]
            self.assertNotEqual(run_id, model.model_run_id("E1A"))
            manifest["observation"]["acceptance"] = {
                "kind": self.module.typed_evidence.E1_LATEST_STAGE_KIND,
                "source": self.module.typed_evidence.CHECKPOINT_SOURCE,
                "decoder": decoder.DECODER_ID,
                "policy_id": decoder.POLICY_ID,
                "profile": "E1A",
                "run_id": run_id.hex(),
                "long_family_hex": model.LONG_FAMILY.hex(),
                "unsat_family_hex": model.UNSAT_FAMILY.hex(),
                "terminal_stage": model.PROFILE_TERMINALS["E1A"],
                "minimum_success_count": 1,
                "clean_baseline_required": True,
                "contract": artifacts,
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(
                self.module.F1V2Error, "no candidate-bound offline contract"
            ):
                self.module.verify_bundle(root, manifest_path)

    def test_manifest_readiness_state_is_explicit_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, manifest, _, manifest_path = self.fixture(root)
            ready = copy.deepcopy(manifest)
            ready["status"] = "ready-for-f1-approval"
            manifest_path.write_text(json.dumps(ready), encoding="utf-8")
            self.assertEqual(
                self.module.verify_bundle(root, manifest_path).manifest["status"],
                "ready-for-f1-approval",
            )
            ready["status"] = "active"
            manifest_path.write_text(json.dumps(ready), encoding="utf-8")
            with self.assertRaises(self.module.F1V2Error):
                self.module.verify_bundle(root, manifest_path)

    def test_candidate_ap_rejects_extra_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, _, _, manifest_path = self.fixture(
                root, ("boot.img.lz4", "recovery.img.lz4")
            )
            with self.assertRaises(self.module.F1TransportError):
                self.module.verify_bundle(root, manifest_path)

    def test_profile_rejects_non_boot_partition_and_wrong_download_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile, _, profile_path, manifest_path = self.fixture(root)
            for mutation in ("partition", "product"):
                changed = copy.deepcopy(profile)
                if mutation == "partition":
                    changed["transport"]["allowed_partition"] = "recovery"
                else:
                    changed["target"]["download"]["product"] = "unknown"
                profile_path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(self.module.F1V2Error):
                    self.module.verify_bundle(root, manifest_path)

    def test_changed_or_missing_rollback_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, manifest, _, manifest_path = self.fixture(root)
            changed = copy.deepcopy(manifest)
            changed["rollback_ap"]["sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(self.module.F1V2Error):
                self.module.verify_bundle(root, manifest_path)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / manifest["rollback_ap"]["path"]).unlink()
            with self.assertRaises(self.module.F1TransportError):
                self.module.verify_bundle(root, manifest_path)

    def test_target_evidence_rejects_wrong_or_ambiguous_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile, _, _, _ = self.fixture(root)
            wrong = self.evidence(profile)
            wrong["targets"][0]["model"] = "SM-S908N"
            with self.assertRaises(self.module.F1V2Error):
                self.module.validate_target_evidence(profile, wrong)
            with self.assertRaises(self.module.F1V2Error):
                self.module.validate_target_evidence(profile, self.evidence(profile, 2))

    def test_approval_binds_target_candidate_observation_and_rollback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile, _, _, manifest_path = self.fixture(root)
            bundle = self.module.verify_bundle(root, manifest_path)
            binding, digest = self.module.approval_binding(bundle, self.evidence(profile))
            self.assertTrue(binding["rollback_preapproved"])
            self.assertEqual(binding["candidate_ap_sha256"], bundle.manifest["candidate_ap"]["sha256"])
            self.assertEqual(binding["rollback_ap_sha256"], bundle.manifest["rollback_ap"]["sha256"])
            changed = self.evidence(profile)
            changed["targets"][0]["usb_topology_sha256"] = "7" * 64
            self.assertNotEqual(digest, self.module.approval_binding(bundle, changed)[1])

    def test_odin_local_parse_failure_is_pre_session(self):
        classify = self.module.classify_odin_output
        self.assertEqual(classify(1, b"Fail parse AP.tar.md5", b""), "odin_local_parse_failure")
        self.assertEqual(
            classify(1, b"unrecognized failure", b""),
            "odin_device_session_failure_or_unknown",
        )
        transcript = (
            b"Setup Connection\nUpload Binaries\nboot.img.lz4\n100%\n"
            b"Close Connection\n"
        )
        self.assertEqual(classify(0, transcript, b""), "odin_transfer_completed")

    def test_journal_rejects_invalid_transition_and_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            journal = self.module.Journal.create(run_dir, "8" * 64)
            with self.assertRaises(self.module.F1V2Error):
                journal.transition("CANDIDATE_FLASHED", "bad", {})
            first = sorted(journal.directory.glob("*.json"))[0]
            first.chmod(0o600)
            value = json.loads(first.read_text())
            value["outcome"] = "tampered"
            first.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(self.module.F1V2Error):
                self.module.Journal.reopen(run_dir, "8" * 64)

    def test_live_journal_preflight_details_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            journal = self.module.Journal.create(
                run_dir,
                "a" * 64,
                {
                    "host_only": False,
                    "device_contact": True,
                    "device_writes": False,
                },
            )
            first = journal.records()[0]
            self.assertEqual(
                first["details"],
                {
                    "host_only": False,
                    "device_contact": True,
                    "device_writes": False,
                },
            )

    def test_journal_checkpoint_is_state_bound_and_not_a_timeline_event(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            journal = self.module.Journal.create(
                root / "run", "b" * 64
            )
            journal.transition("APPROVED", "approved", {})
            journal.transition("DOWNLOAD_IDENTIFIED", "identified", {})
            for attempt in (1, 2):
                start = root / f"candidate-attempt-{attempt:02d}.start.json"
                start.write_text(f"attempt={attempt}\n", encoding="ascii")
                payload = start.read_bytes()
                journal.checkpoint(
                    "candidate_transfer_attempt",
                    "attempt_started",
                    {
                        "attempt": attempt,
                        "start": {
                            "path": str(start.absolute()),
                            "size": len(payload),
                            "sha256": hashlib.sha256(payload).hexdigest(),
                        },
                    },
                )
            self.assertEqual(journal.state(), "DOWNLOAD_IDENTIFIED")
            self.assertEqual(self.module.timeline(journal.records()), {"events": []})
            with self.assertRaises(self.module.F1V2Error):
                journal.checkpoint(
                    "candidate_transfer_attempt",
                    "attempt_started",
                    {
                        "attempt": 3,
                        "start": {
                            "path": str((root / "unused").absolute()),
                            "size": 1,
                            "sha256": "1" * 64,
                        },
                    },
                )
            with self.assertRaises(self.module.F1V2Error):
                journal.checkpoint(
                    "rollback_transfer_attempt",
                    "wrong_state",
                    {
                        "attempt": 1,
                        "start": {
                            "path": str((root / "unused").absolute()),
                            "size": 1,
                            "sha256": "1" * 64,
                        },
                    },
                )

    def test_journal_head_detects_tail_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            journal = self.module.Journal.create(run_dir, "9" * 64)
            journal.event("live_session_start")
            sorted(journal.directory.glob("*.json"))[-1].unlink()
            with self.assertRaises(self.module.F1V2Error):
                self.module.Journal.reopen(run_dir, "9" * 64)

    def test_run_directory_cannot_escape_private_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            escaped = root / self.module.DEFAULT_RUN_ROOT / "../../../../escape"
            with self.assertRaises(self.module.F1V2Error):
                self.module.allocate_run_dir(root, escaped)

    def run_scenario(self, scenario):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        _, _, _, manifest_path = self.fixture(root)
        bundle = self.module.verify_bundle(root, manifest_path)
        result = self.module.simulate(bundle, scenario, root / "runs/run")
        return temporary, result

    def test_happy_simulation_closes_with_canonical_timeline(self):
        temporary, result = self.run_scenario("happy-path")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["current_state"], "CLOSED")
        self.assertEqual(
            [event["name"] for event in result["timeline"]["events"]],
            list(self.module.TIMELINE),
        )
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["partition_transfer"])

    def test_candidate_timeout_still_rolls_back_without_claiming_proof(self):
        temporary, result = self.run_scenario("candidate-timeout")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["current_state"], "CLOSED")
        self.assertTrue(result["verdict"].startswith("NO_PROOF"))
        self.assertEqual(len(result["timeline"]["events"]), 8)

    def test_interrupted_result_resumes_without_replaying_events(self):
        temporary, result = self.run_scenario("interrupted-result")
        self.addCleanup(temporary.cleanup)
        names = [event["name"] for event in result["timeline"]["events"]]
        self.assertTrue(result["resumed"])
        self.assertEqual(names, list(self.module.TIMELINE))
        self.assertEqual(len(names), len(set(names)))

    def test_local_parse_failure_aborts_before_device_session(self):
        temporary, result = self.run_scenario("local-parse-failure")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result["current_state"], "ABORTED")
        self.assertEqual(result["outcome_class"], "odin_local_parse_failure")
        self.assertFalse(result["odin_invoked"])
        self.assertEqual(
            [event["name"] for event in result["timeline"]["events"]],
            ["live_session_start", "candidate_flash_start"],
        )

    def test_cli_has_no_live_or_connected_mode(self):
        options = self.module.build_parser()._option_string_actions
        self.assertNotIn("--live", options)
        self.assertNotIn("--connected", options)
        self.assertFalse(hasattr(self.module, "transport"))
        self.assertFalse(hasattr(self.module, "execute_odin_boot_only"))
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("execute_odin_boot_only(", source)


if __name__ == "__main__":
    unittest.main()
