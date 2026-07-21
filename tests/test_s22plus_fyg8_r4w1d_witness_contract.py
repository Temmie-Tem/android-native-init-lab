import copy
import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1d_witness_contract.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_r4w1d_witness_contract_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def circular_read(payload: bytes, index: int, size: int) -> bytes:
    start = index % len(payload)
    first = min(size, len(payload) - start)
    return payload[start : start + first] + payload[: size - first]


class S22PlusFyg8R4W1DWitnessContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        source = Path(
            os.environ.get(
                "S22PLUS_FYG8_TEST_SOURCE", str(cls.module.DEFAULT_SOURCE)
            )
        )
        cls.source = source if source.is_absolute() else ROOT / source
        cls.patch = ROOT / cls.module.DEFAULT_PATCH
        cls.inherited = ROOT / cls.module.DEFAULT_INHERITED_RESULT
        cls.patched = cls.module.apply_patch_to_minimal_tree(
            cls.source, cls.patch
        )

    def test_contract_passes_with_current_lineage_results(self):
        with mock.patch.object(
            self.module.shared,
            "check_dt_contract",
            return_value={"verified": True},
        ), mock.patch.object(
            self.module.shared,
            "check_vendor_abi",
            return_value={"verified": True},
        ):
            result = self.module.run_check(
                self.source, self.patch, self.inherited
            )
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertTrue(result["patched_contract"]["verified"])
        self.assertTrue(result["carrier_artifacts"]["verified"])
        self.assertTrue(result["current_source_layout_contract"]["verified"])
        self.assertFalse(result["safety"]["device_contact"])
        self.assertFalse(result["safety"]["live_authorized"])

    def test_compact_proof_is_derived(self):
        derived = hashlib.sha256(
            self.module.MARKER_PREIMAGE.encode("ascii")
        ).hexdigest()
        self.assertEqual(derived, self.module.MARKER_PREIMAGE_SHA256)
        self.assertEqual(self.module.MARKER_ID, derived[:32])
        self.assertEqual(len(self.module.PROOF.encode("ascii")), 45)

    def test_backfill_is_contiguous_on_both_sides_of_cursor(self):
        payload = bytes(256)
        proof = self.module.PROOF.encode("ascii")
        for position, expected in ((72, 27), (20, 211)):
            with self.subTest(position=position):
                updated, proof_position = self.module.backfill_proof(
                    payload, 512 + position, proof
                )
                self.assertEqual(proof_position, expected)
                self.assertEqual(
                    updated[proof_position : proof_position + len(proof)], proof
                )
                self.assertNotIn(proof, circular_read(updated, position, 100))

    def test_observed_99_byte_wrap_failure_is_not_repeated(self):
        payload_size = 256
        old = bytes(range(99))
        survived = 73  # Includes the leading newline; visible text is 72 bytes.
        wrapped_suffix = len(old) - survived
        old_start = payload_size - survived
        wrapped = bytearray(payload_size)
        wrapped[old_start:] = old[:survived]
        wrapped[:wrapped_suffix] = old[survived:]
        wrapped[:wrapped_suffix] = b"X" * wrapped_suffix
        self.assertNotIn(old, bytes(wrapped))

        proof = self.module.PROOF.encode("ascii")
        updated, proof_position = self.module.backfill_proof(
            bytes(payload_size), payload_size + old_start, proof
        )
        updated = bytearray(updated)
        updated[old_start:] = b"Y" * (payload_size - old_start)
        self.assertEqual(
            bytes(updated[proof_position : proof_position + len(proof)]), proof
        )

    def test_backfill_rejects_unsaturated_or_wrapped_small_index(self):
        proof = self.module.PROOF.encode("ascii")
        for index in (0, 255, 0x1_0000_0000):
            with self.subTest(index=index), self.assertRaises(
                self.module.CheckError
            ):
                self.module.backfill_proof(bytes(256), index, proof)
        updated, position = self.module.backfill_proof(
            bytes(256), 0xFFFFFFFF, proof
        )
        self.assertEqual(updated[position : position + len(proof)], proof)

    def test_contract_rejects_weakened_exec_guards(self):
        main_path = "kernel_platform/common/init/main.c"
        for token in (
            'strcmp(init_filename, "/init")',
            "task_pid_nr(current) != 1",
            "READ_ONCE(head->magic) != S22PLUS_FYG8_LOG_MAGIC",
        ):
            with self.subTest(token=token):
                patched = copy.deepcopy(self.patched)
                patched[main_path] = patched[main_path].replace(token, "false", 1)
                with self.assertRaises(self.module.CheckError):
                    self.module.check_patched_sources(patched)

    def test_contract_rejects_semantic_backfill_mutations(self):
        main_path = "kernel_platform/common/init/main.c"
        mutations = (
            (" || task_pid_nr", " && task_pid_nr"),
            ("idx = READ_ONCE(head->idx);", "idx = 0;"),
            (
                "memcpy(&head->buf[proof_pos], proof, proof_size);",
                "memset(&head->buf[proof_pos], 0, proof_size);",
            ),
            ("smp_wmb();", "if (false) smp_wmb();"),
            ("idx < payload_size", "idx <= payload_size"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                patched = copy.deepcopy(self.patched)
                patched[main_path] = patched[main_path].replace(old, new, 1)
                with self.assertRaises(self.module.CheckError):
                    self.module.check_patched_sources(patched)

    def test_artifact_binding_rejects_changed_init(self):
        source = ROOT / self.module.DEFAULT_CARRIER_INIT
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "init"
            changed.write_bytes(source.read_bytes()[:-1] + b"X")
            with self.assertRaises(self.module.CheckError):
                self.module.check_pinned_artifact(
                    changed,
                    expected_size=self.module.CARRIER_INIT_SIZE,
                    expected_sha256=self.module.CARRIER_INIT_SHA256,
                    label="carrier init",
                )

    def test_current_lineage_is_not_satisfied_by_inherited_json(self):
        with mock.patch.object(
            self.module.shared,
            "check_dt_contract",
            side_effect=self.module.shared.CheckError("missing current DT"),
        ):
            with self.assertRaises(self.module.CheckError):
                self.module.check_current_layout(self.source)

    def test_patch_policy_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "changed.patch"
            changed.write_bytes(self.patch.read_bytes() + b"\n")
            with self.assertRaises(self.module.CheckError):
                self.module.check_patch_policy(changed)


if __name__ == "__main__":
    unittest.main()
