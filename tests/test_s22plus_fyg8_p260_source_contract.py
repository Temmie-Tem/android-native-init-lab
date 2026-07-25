import argparse
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_candidate_intent as candidate_intent  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import s22plus_fyg8_p253_e2_stock_closure as closure_selector  # noqa: E402
import s22plus_fyg8_p258_source_contract as p258  # noqa: E402
import s22plus_fyg8_p260_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p260_e2_stock_closure as closure  # noqa: E402
import s22plus_fyg8_p260_linked_audit as linked  # noqa: E402
import s22plus_fyg8_p260_source_contract as p260  # noqa: E402
import s22plus_fyg8_source_contracts as contracts  # noqa: E402
import s22plus_fyg8_r4w1e_e1_candidate_static_checker as e1_static  # noqa: E402


class S22PlusFyg8P260SourceContractTest(unittest.TestCase):
    RUN_ID = bytes.fromhex("60" * 16)

    @classmethod
    def setUpClass(cls):
        cls.generated = p260.generate(ROOT)
        cls.historical = p258.generate(ROOT)
        cls.implementation = p260.implementation_result(ROOT)

    def test_descriptor_extends_exact_p258_prefix(self):
        self.assertEqual(len(spec.STEPS), 89)
        self.assertEqual(spec.STEPS[:80], p258.spec.STEPS[:80])
        self.assertEqual(
            tuple(step.stage for step in spec.STEPS[80:88]),
            tuple(range(0x88, 0x90)),
        )
        self.assertTrue(
            all(
                step.kind == spec.KIND_LOCAL and step.item_index == 0
                for step in spec.STEPS[80:88]
            )
        )
        self.assertEqual(spec.TERMINAL_ORDINAL, 88)
        self.assertEqual(spec.TERMINAL_STAGE, 0x90)
        self.assertEqual(
            spec.ordinal_for_stage(spec.CONFIGURED_STAGE) + 1, 88
        )

    def test_e3_local_failure_semantics_are_explicit(self):
        for stage in spec.E3_LOCAL_STAGES:
            step = spec.step_for_stage(stage)
            self.assertTrue(spec.failure_detail_allowed(step, 5))
            self.assertTrue(spec.failure_detail_allowed(step, 0x800))
            self.assertTrue(spec.failure_detail_allowed(step, 0x80B))
            self.assertTrue(spec.failure_detail_allowed(step, 0x900))
            self.assertTrue(spec.failure_detail_allowed(step, 0x90B))
            self.assertFalse(spec.failure_detail_allowed(step, 0x80C))
            self.assertFalse(spec.failure_detail_allowed(step, 0x90C))
            self.assertFalse(spec.failure_detail_allowed(step, 0xA00))
        old_terminal = p258.spec.STEPS[-1]
        self.assertFalse(
            spec.failure_detail_allowed(old_terminal, 0x80B)
        )

    def test_candidate_observer_is_run_id_derived(self):
        value = spec.candidate_observer(self.RUN_ID)
        self.assertEqual(set(value), {
            "kind",
            "usb_vendor_id",
            "usb_product_id",
            "usb_serial",
            "usb_driver",
            "usb_interface_number",
            "banner_hex",
        })
        self.assertEqual(value["usb_serial"], "S22E3" + self.RUN_ID.hex())
        self.assertEqual(
            bytes.fromhex(value["banner_hex"]),
            b"S22PLUS-FYG8-E3:" + self.RUN_ID.hex().encode("ascii") + b"\n",
        )
        self.assertEqual(len(value["usb_serial"]), spec.USB_SERIAL_SIZE)
        self.assertEqual(
            len(bytes.fromhex(value["banner_hex"])), spec.BANNER_SIZE
        )
        with self.assertRaises(spec.SpecError):
            spec.candidate_observer(bytes(16))

    def test_generation_preserves_plan_and_replaces_terminal_geometry(self):
        self.assertEqual(self.generated["plan"], self.historical["plan"])
        self.assertNotEqual(
            self.generated["runtime"], self.historical["runtime"]
        )
        self.assertNotEqual(
            self.generated["checkpoint"], self.historical["checkpoint"]
        )
        self.assertNotEqual(
            self.generated["patch"], self.historical["patch"]
        )
        tables = p260.linked_table_bytes()
        self.assertEqual(
            tables["s22_fyg8_e2_sequence"],
            bytes(step.stage for step in spec.STEPS),
        )
        self.assertEqual(tables["s22_fyg8_e2_items"][-9:], bytes(9))
        self.assertEqual(tables["s22_fyg8_e2_kinds"][-9:], bytes([0] * 8 + [2]))

    def test_generated_validators_allow_local_structured_details(self):
        checkpoint = self.generated["checkpoint"].decode("ascii")
        patch = self.generated["patch"].decode("ascii")
        self.assertIn("stage >= 0x88U && stage <= 0x8fU", checkpoint)
        self.assertIn("encoded_index >= 12U", checkpoint)
        self.assertIn("e3_local = ordinal >= 80 &&", patch)
        self.assertIn("ordinal < 88;", patch)
        self.assertIn("encoded_index >= 12", patch)
        self.assertNotIn("ordinal < 89;", patch)

    def test_runtime_is_one_shot_raw_and_no_flush(self):
        include = p260.source_bytes_for_runtime_include(ROOT)
        self.assertEqual(include.count(b"P260_TCGETS"), 3)
        self.assertEqual(include.count(b"P260_TCSETS"), 2)
        self.assertEqual(
            include.count(
                b'p260_write_value(p260_role_path, "peripheral")'
            ),
            1,
        )
        self.assertEqual(
            include.count(
                b'p260_write_and_verify(\n'
                b'        "/config/usb_gadget/g1/UDC"'
            ),
            1,
        )
        for forbidden in (
            b"TCIOFLUSH",
            b"soft_connect",
            b"ss_acm",
            b"sys_unlink",
        ):
            self.assertNotIn(forbidden, include)
        runtime = self.generated["runtime"]
        self.assertEqual(
            runtime.count(
                b'#include "s22plus_fyg8_p260_e3_runtime.inc.c"'
            ),
            1,
        )
        self.assertEqual(runtime.count(b"p260_e3_run();"), 1)

    def test_materialized_runtime_include_is_source_bound(self):
        source, receipts = p260.source_receipts(ROOT)
        self.assertEqual(
            source["e3_runtime_include"],
            p260.source_bytes_for_runtime_include(ROOT),
        )
        self.assertIn("e3_runtime_include", receipts)
        self.assertEqual(
            p260.MATERIALIZED_FILENAMES["e3_runtime_include"],
            "s22plus_fyg8_p260_e3_runtime.inc.c",
        )

    def test_selector_closure_and_linked_adapters_are_registered(self):
        selected = contracts.select(p260.CONTRACT_ID, "E2")
        self.assertIs(selected.module, p260)
        self.assertIs(selected.decoder, p260.decoder)
        self.assertIs(
            closure_selector.select(p260.CONTRACT_ID), closure
        )
        self.assertEqual(
            linked.EXPECTED_SOURCE_CONTRACT_ID, p260.CONTRACT_ID
        )
        self.assertEqual(
            linked.repro.LINKED_VALIDATOR_ADAPTERS[p260.CONTRACT_ID],
            "s22plus_fyg8_p260_linked_audit",
        )

    def test_no_lto_userspace_entrypoint_matches_closure(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=private_tmp, prefix="p260-entrypoint-"
        ) as name:
            parent = Path(name)
            intent_dir = parent / "intent"
            candidate_intent.create(
                argparse.Namespace(
                    source=candidate_intent.DEFAULT_SOURCE,
                    base_patch=candidate_intent.DEFAULT_BASE_PATCH,
                    out=intent_dir.relative_to(ROOT),
                    nonce_hex="60" * 16,
                    profile="E2",
                    source_contract_id=p260.CONTRACT_ID,
                )
            )
            output = parent / "userspace"
            result = userspace.build_userspace(
                argparse.Namespace(
                    source=candidate_intent.DEFAULT_SOURCE,
                    intent=intent_dir / "candidate-intent.json",
                    patch=intent_dir / "candidate.patch",
                    out=output,
                )
            )
            observed = {
                "init": e1_static.inspect_static_elf(
                    (output / "init").read_bytes(), "P2.60 test init"
                )["entrypoint"],
                "child": e1_static.inspect_static_elf(
                    (output / "s22-e1-child").read_bytes(),
                    "P2.60 test child",
                )["entrypoint"],
            }
        self.assertTrue(result["two_build_byte_identical"])
        self.assertEqual(observed, closure.EXPECTED_ELF_ENTRYPOINTS)

    def test_implementation_result_is_host_only(self):
        self.assertEqual(
            self.implementation["verdict"], p260.IMPLEMENTATION_VERDICT
        )
        self.assertTrue(
            self.implementation["linked_userspace"]["two_link_reproducible"]
        )
        self.assertEqual(
            self.implementation["safety"],
            {
                "host_only": True,
                "kernel_built": False,
                "image_built": False,
                "candidate_created": False,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "live_authorized": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
