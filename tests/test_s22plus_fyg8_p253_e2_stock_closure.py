import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p242_e2_stock_closure as legacy  # noqa: E402
import s22plus_fyg8_p245_e2_stock_closure as p245  # noqa: E402
import s22plus_fyg8_p245_source_contract as p245_contract  # noqa: E402
import s22plus_fyg8_p248_source_contract as p248_contract  # noqa: E402
import s22plus_fyg8_p252_source_contract as p252_contract  # noqa: E402
import s22plus_fyg8_p253_e2_stock_closure as p253  # noqa: E402


class S22PlusFyg8P253E2StockClosureTest(unittest.TestCase):
    def test_selector_is_explicit_and_preserves_historical_paths(self):
        self.assertIs(p253.select(None), legacy)
        self.assertIs(p253.select(p245_contract.CONTRACT_ID), p245)
        self.assertIs(p253.select(p248_contract.CONTRACT_ID), p245)
        with self.assertRaisesRegex(p253.ClosureError, "not proof-bound"):
            p253.select(p252_contract.CONTRACT_ID)
        self.assertIs(p253.select(p253.P254_CONTRACT_ID), p253)
        with self.assertRaisesRegex(p253.ClosureError, "unsupported"):
            p253.select("future-unreviewed-contract")

    def test_p252_entrypoints_are_isolated_from_historical_module(self):
        historical = legacy.EXPECTED_ELF_ENTRYPOINTS
        self.assertIs(legacy.EXPECTED_ELF_ENTRYPOINTS, historical)
        self.assertIsNot(p253.isolated_legacy, legacy)
        self.assertEqual(
            p253.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS,
            p253.EXPECTED_ELF_ENTRYPOINTS,
        )
        self.assertIs(legacy.EXPECTED_ELF_ENTRYPOINTS, historical)

    def test_isolated_failure_never_mutates_historical_entrypoints(self):
        historical = legacy.EXPECTED_ELF_ENTRYPOINTS
        with mock.patch.object(
            p253, "validate_module_closure", return_value={}
        ), mock.patch.object(
            p253.isolated_legacy,
            "validate_module_closure",
            side_effect=p253.ClosureError("expected failure"),
        ):
            with self.assertRaisesRegex(p253.ClosureError, "expected failure"):
                p253.validate_effective_rootfs(
                    {
                        "module_closure_sha256": p245.closure_sha256({})
                    },
                    expected_init={},
                    expected_child={},
                    module_closure={},
                )
        self.assertIs(legacy.EXPECTED_ELF_ENTRYPOINTS, historical)

    def test_p252_entrypoints_match_the_reproducible_userspace(self):
        self.assertEqual(
            p253.EXPECTED_ELF_ENTRYPOINTS,
            {"init": 0x4014F0, "child": 0x4000CC},
        )
        self.assertNotEqual(
            p253.EXPECTED_ELF_ENTRYPOINTS["init"],
            legacy.EXPECTED_ELF_ENTRYPOINTS["init"],
        )
        self.assertEqual(
            p253.EXPECTED_ELF_ENTRYPOINTS["child"],
            legacy.EXPECTED_ELF_ENTRYPOINTS["child"],
        )

    def test_historical_reader_never_observes_p254_entrypoints(self):
        historical = legacy.EXPECTED_ELF_ENTRYPOINTS
        observed = []
        entered = threading.Event()
        release = threading.Event()

        def isolated_audit(*_args, **_kwargs):
            entered.set()
            observed.append(legacy.EXPECTED_ELF_ENTRYPOINTS)
            release.wait(1)
            return {"verified": True}

        def historical_reader():
            while not release.is_set():
                observed.append(legacy.EXPECTED_ELF_ENTRYPOINTS)

        worker_error = []

        def p254_worker():
            try:
                p253.audit_candidate_generic_rootfs(
                    None,
                    (),
                    expected_init={},
                    expected_child={},
                    run_id=bytes(16),
                    module_closure={},
                )
            except BaseException as exc:
                worker_error.append(exc)

        reader = threading.Thread(target=historical_reader)
        reader.start()
        try:
            with mock.patch.object(
                p253, "validate_module_closure", return_value={}
            ), mock.patch.object(
                p253.isolated_legacy,
                "validate_module_closure",
                return_value={},
            ), mock.patch.object(
                p253.isolated_legacy,
                "audit_candidate_generic_rootfs",
                side_effect=isolated_audit,
            ):
                worker = threading.Thread(target=p254_worker)
                worker.start()
                self.assertTrue(entered.wait(1))
                time.sleep(0.01)
                release.set()
                worker.join(1)
        finally:
            release.set()
            reader.join(1)
        self.assertFalse(worker_error)
        self.assertTrue(observed)
        self.assertTrue(all(value is historical for value in observed))


if __name__ == "__main__":
    unittest.main()
