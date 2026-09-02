from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p327_closed_result_finalizer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "p327_closed_finalizer_tested", SOURCE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P327ClosedResultFinalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_surface_is_exact_run_and_host_only(self):
        module = self.module
        self.assertEqual(module.EXPECTED_BINDING[:8], "c5a1c567")
        self.assertEqual(module.EXPECTED_PRE_STATE_SIZE, 30_308)
        self.assertEqual(module.EXPECTED_FINAL_STATE_SIZE, 30_381)
        self.assertEqual(module.EXPECTED_RESULT_SIZE, 34_047)
        self.assertEqual(module.CORE_MAX_RECORD, 32 * 1024)
        self.assertEqual(module.MAX_FINAL_RECORD, 64 * 1024)
        self.assertEqual(module.STATE_PATH, module.RUN_DIR / "live-state.json")
        self.assertEqual(module.RESULT_PATH, module.RUN_DIR / "live-result.json")
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "SamsungOdinBackend(",
            "subprocess.run(",
            "subprocess.Popen(",
            "adb_client_for_bundle(",
            "recover_prepared(",
            "execute_prepared(",
            "revalidate=True",
            "--execute",
            "--recover",
        ):
            self.assertNotIn(forbidden, source)

    def test_frozen_closure_hash_is_recomputed(self):
        module = self.module
        record = json.loads(
            (module.RUN_DIR / "prepared.json").read_text(encoding="utf-8")
        )
        closure = record["execution_closure"]
        self.assertEqual(closure["sha256"], module.EXPECTED_EXECUTION_CLOSURE)
        self.assertEqual(
            module._compact_json_sha256(
                {key: value for key, value in closure.items() if key != "sha256"}
            ),
            module.EXPECTED_EXECUTION_CLOSURE,
        )
        self.assertEqual(len(closure["sources"]), 30)

    def test_exact_closed_run_reconstructs_positive_framed_result(self):
        module = self.module
        value, payload, state, state_payload, phase, _prepared, _live = (
            module.reconstruct()
        )
        self.assertEqual(phase, "pre")
        self.assertEqual(value["current_state"], "CLOSED")
        self.assertEqual(value["verdict"], module.EXPECTED_RESULT_VERDICT)
        self.assertEqual(value["outcome_class"], module.EXPECTED_OUTCOME)
        proof = state["candidate_arrival_proof"]
        self.assertTrue(proof["proof"])
        self.assertTrue(proof["pid1_framed_exec_proof"])
        self.assertTrue(proof["busybox_ash_command_proof"])
        self.assertFalse(proof["interactive_pty_proof"])
        self.assertFalse(proof["caller_selected_command"])
        self.assertEqual(len(state_payload), module.EXPECTED_FINAL_STATE_SIZE)
        self.assertEqual(module._sha256(state_payload), module.EXPECTED_FINAL_STATE_SHA256)
        self.assertEqual(len(payload), module.EXPECTED_RESULT_SIZE)
        self.assertEqual(module._sha256(payload), module.EXPECTED_RESULT_SHA256)

    def test_old_projection_is_rejected_if_it_is_not_the_known_defect(self):
        module = self.module
        with self.assertRaises(module.FinalizerError):
            module._expected_old_state({"candidate_classification": "not-attempted"})

    def test_state_phase_accepts_only_pinned_pre_or_final(self):
        module = self.module
        pre = b"pre"
        final = b"final"
        with (
            mock.patch.object(module, "EXPECTED_PRE_STATE_SIZE", len(pre)),
            mock.patch.object(
                module, "EXPECTED_PRE_STATE_SHA256", module._sha256(pre)
            ),
            mock.patch.object(module, "EXPECTED_FINAL_STATE_SIZE", len(final)),
            mock.patch.object(
                module, "EXPECTED_FINAL_STATE_SHA256", module._sha256(final)
            ),
        ):
            self.assertEqual(module._state_phase(pre), "pre")
            self.assertEqual(module._state_phase(final), "final")
            with self.assertRaises(module.FinalizerError):
                module._state_phase(b"foreign")

    def test_publish_result_is_mode0400_single_link_and_no_clobber(self):
        module = self.module
        payload = b'{"closed":true}\n'
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with (
                mock.patch.object(module, "RESULT_PATH", result),
                mock.patch.object(module, "EXPECTED_RESULT_SIZE", len(payload)),
                mock.patch.object(
                    module, "EXPECTED_RESULT_SHA256", module._sha256(payload)
                ),
            ):
                module._publish_result(payload)
                info = result.lstat()
                self.assertEqual(result.read_bytes(), payload)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)
                with self.assertRaises(module.FinalizerError):
                    module._publish_result(payload)

    def test_arbitrary_or_oversized_result_is_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as name:
            result = Path(name) / "live-result.json"
            with mock.patch.object(module, "RESULT_PATH", result):
                with self.assertRaises(module.FinalizerError):
                    module._publish_result(b'{"arbitrary":true}\n')
                with self.assertRaises(module.FinalizerError):
                    module._publish_result(b"x" * (module.MAX_FINAL_RECORD + 1))
                self.assertFalse(result.exists())

    def test_two_link_result_publication_cut_is_repaired(self):
        module = self.module
        payload = b"complete"
        with tempfile.TemporaryDirectory() as name:
            parent = Path(name)
            result = parent / "live-result.json"
            temporary = parent / f".{result.name}.{os.getpid()}.123.tmp"
            temporary.write_bytes(payload)
            temporary.chmod(0o400)
            os.link(temporary, result)
            module._repair_publication_cut(result)
            self.assertFalse(temporary.exists())
            self.assertEqual(result.read_bytes(), payload)
            self.assertEqual(result.stat().st_nlink, 1)

    def test_publish_state_uses_dedicated_bound_and_restores_it(self):
        module = self.module
        old_state = {"schema": "device_action_f1_live_state_v2", "old": True}
        new_state = {"schema": "device_action_f1_live_state_v2", "old": False}
        old_payload = module._canonical(old_state)
        new_payload = module._canonical(new_state)
        with tempfile.TemporaryDirectory() as name:
            state_path = Path(name) / "live-state.json"
            state_path.write_bytes(old_payload)
            state_path.chmod(0o400)
            core = types.SimpleNamespace(MAX_RECORD=module.CORE_MAX_RECORD)
            live = types.SimpleNamespace(core=core)
            live._state = mock.Mock(return_value=old_state)

            def save(_prepared, value):
                self.assertEqual(core.MAX_RECORD, module.MAX_FINAL_RECORD)
                self.assertEqual(value, new_state)
                state_path.unlink()
                state_path.write_bytes(new_payload)
                state_path.chmod(0o400)

            live._save_state = mock.Mock(side_effect=save)
            with (
                mock.patch.object(module, "STATE_PATH", state_path),
                mock.patch.object(module, "EXPECTED_PRE_STATE_SIZE", len(old_payload)),
                mock.patch.object(
                    module, "EXPECTED_PRE_STATE_SHA256", module._sha256(old_payload)
                ),
                mock.patch.object(module, "EXPECTED_FINAL_STATE_SIZE", len(new_payload)),
                mock.patch.object(
                    module, "EXPECTED_FINAL_STATE_SHA256", module._sha256(new_payload)
                ),
            ):
                module._publish_state(live, object(), new_state, new_payload)
            self.assertEqual(core.MAX_RECORD, module.CORE_MAX_RECORD)
            self.assertEqual(state_path.read_bytes(), new_payload)

    def test_audit_flags_are_zero_effect(self):
        module = self.module
        value = {
            "verdict": module.EXPECTED_RESULT_VERDICT,
            "outcome_class": module.EXPECTED_OUTCOME,
            "current_state": "CLOSED",
            "recovery_required": False,
        }
        payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
        with (
            mock.patch.object(
                module,
                "reconstruct",
                return_value=(value, payload, {}, b"{}\n", "pre", object(), mock.Mock()),
            ),
            mock.patch.object(
                module,
                "RESULT_PATH",
                Path(f"/definitely/absent/{os.getpid()}-p327-live-result.json"),
            ),
        ):
            result = module.finalize(publish=False)
        for key in (
            "created",
            "device_contact",
            "adb_invoked",
            "usb_revalidated",
            "odin_invoked",
            "candidate_transfer",
            "rollback_transfer",
            "live_authorized",
        ):
            self.assertFalse(result[key])


if __name__ == "__main__":
    unittest.main()
