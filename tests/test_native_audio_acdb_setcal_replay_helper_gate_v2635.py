"""Tests for V2635 exact SET-cal replay helper gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2635 = load_revalidation("native_audio_acdb_setcal_replay_helper_gate_v2635")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fake_record(sequence: int, cal_type: int, payload: bool = False) -> dict:
    return {
        "sequence": sequence,
        "cal_type": cal_type,
        "role": f"CAL_{cal_type}",
        "dmabuf_expected": payload,
        "arg": {
            "path_private": f"workspace/private/fake/set-arg-{sequence}-{cal_type}.bin",
            "sha256": f"{cal_type:064x}"[-64:],
        },
        "dmabuf": {
            "path_private": f"workspace/private/fake/payload-{sequence}-{cal_type}.bin" if payload else None,
            "sha256": f"{sequence:064x}"[-64:] if payload else None,
        },
    }


def fake_v2634_manifest(root: Path) -> Path:
    records = [
        fake_record(1, 13),
        fake_record(2, 9),
        fake_record(3, 11, True),
        fake_record(4, 12),
        fake_record(5, 15, True),
        fake_record(6, 23),
        fake_record(7, 16, True),
        fake_record(8, 21),
    ]
    path = root / "v2634.json"
    write_json(path, {
        "ok": True,
        "inputs_ok": True,
        "operator_gate2_accepted": False,
        "native_replay_ready": False,
        "safe_to_run_native_replay": False,
        "captured_set_order": [13, 9, 11, 12, 15, 23, 16, 21],
        "topology": {
            "path_private": "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin",
            "sha256": "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89",
        },
        "set_records": records,
        "set_records_redacted": records,
        "replay_blockers": ["operator Gate-2 missing"],
    })
    return path


class NativeAudioAcdbSetcalReplayHelperGateV2635(unittest.TestCase):
    def test_source_state_has_exact_replay_tokens(self) -> None:
        state = v2635.helper_source_state()

        self.assertTrue(state["ready"], state)
        self.assertTrue(state["required_tokens"]["entry_cap_16"])
        self.assertTrue(state["required_tokens"]["exact_set_entry"])
        self.assertTrue(state["required_tokens"]["header_only_replay"])
        self.assertTrue(state["required_tokens"]["header_only_nonzero_cal_size"])
        self.assertTrue(state["required_tokens"]["header_only_marker"])
        self.assertTrue(state["required_tokens"]["header_mem_handle_neutralize"])
        self.assertTrue(state["required_tokens"]["header_zero_cal_mem_handle_policy"])
        self.assertTrue(state["required_tokens"]["ioctl_result_marker"])
        self.assertFalse(any(state["prohibited_tokens"].values()))

    def test_v2634_state_generates_mixed_future_args(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2635-"))
        state = v2635.v2634_state(fake_v2634_manifest(root))

        self.assertTrue(state["ready"])
        self.assertEqual(state["future_entry_count"], 9)
        self.assertEqual(state["future_private_args"][0], "--basic-payload")
        self.assertEqual(state["future_private_args"].count("--exact-set"), 8)
        self.assertTrue(any(":workspace/private/fake/payload-3-11.bin" in item for item in state["future_private_args"]))
        self.assertIn("--exact-set", state["future_private_args"])
        self.assertIn("workspace/private/fake/set-arg-8-21.bin", state["future_private_args"])
        self.assertFalse(any("set-arg-8-21.bin:" in item for item in state["future_private_args"]))

    def test_manifest_stays_host_only_and_replay_blocked_without_build(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2635-"))
        args = v2635.parse_args([
            "--v2634-manifest",
            str(fake_v2634_manifest(root)),
            "--build-root",
            str(root / "build"),
            "--manifest-path",
            str(root / "manifest.json"),
        ])

        manifest = v2635.build_manifest(args)

        self.assertFalse(manifest["ok"])
        self.assertTrue(manifest["v2634_manifest"]["ready"])
        self.assertFalse(manifest["safe_to_run_native_replay"])
        self.assertIn("operator Gate-2", manifest["replay_blockers"][0])
        self.assertTrue(manifest["helper_contract"]["supports_exact_set_arg_replay"])
        self.assertEqual(manifest["helper_contract"]["max_replay_entries"], 16)
        self.assertTrue(manifest["helper_contract"]["supports_header_only_nonzero_cal_size_exact_args"])
        self.assertTrue(manifest["helper_contract"]["neutralizes_header_only_zero_cal_size_positive_mem_handle"])
        self.assertTrue(manifest["helper_contract"]["logs_uniform_ioctl_results"])

    def test_report_states_no_live_replay_approval(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2635-"))
        args = v2635.parse_args([
            "--v2634-manifest",
            str(fake_v2634_manifest(root)),
            "--build-root",
            str(root / "build"),
            "--manifest-path",
            str(root / "manifest.json"),
        ])
        manifest = v2635.build_manifest(args)
        report = root / "report.md"

        v2635.write_report(report, manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("exact SET-cal replay helper gate", text)
        self.assertIn("No device action", text)
        self.assertIn("Native replay remains blocked", text)
        self.assertNotIn("workspace/private/fake", text)


if __name__ == "__main__":
    unittest.main()
