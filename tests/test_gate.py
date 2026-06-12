"""Regression tests for a90harness.gate safety decisions.

Pins fail-closed flag evaluation for validation modules without constructing a
real device client, evidence store, or module context.
"""

import sys
import types
import unittest

from _loader import load_harness

broker_stub = types.ModuleType("a90_broker")
broker_stub.PROTO = "A90B1"
broker_stub.connect_and_call = lambda *_args, **_kwargs: {}
sys.modules.setdefault("a90_broker", broker_stub)

gate = load_harness("gate")
module_contract = load_harness("module")


class SafeModule(module_contract.TestModule):
    description = "safe smoke"
    cycle_label = "vtest-safe"


class RiskyModule(module_contract.TestModule):
    description = "risky smoke"
    cycle_label = "vtest-risky"
    read_only = False
    destructive = True
    requires_ncm = True
    requires_usb_rebind = True
    operator_confirm_required = True
    external_bridge_client = True


class EvaluateGate(unittest.TestCase):
    def test_safe_module_is_allowed_by_default(self):
        result = gate.evaluate_gate(SafeModule(), gate.GateOptions())

        self.assertTrue(result.allowed)
        self.assertEqual(result.reasons, [])
        self.assertEqual(result.required_flags, [])
        self.assertEqual(
            result.metadata,
            {
                "description": "safe smoke",
                "cycle_label": "vtest-safe",
                "read_only": True,
                "destructive": False,
                "requires_ncm": False,
                "requires_usb_rebind": False,
                "operator_confirm_required": False,
                "external_bridge_client": False,
            },
        )

    def test_risky_module_is_blocked_with_all_required_flags_by_default(self):
        result = gate.evaluate_gate(RiskyModule(), gate.GateOptions())

        self.assertFalse(result.allowed)
        self.assertEqual(
            result.reasons,
            [
                "requires host USB NCM precondition",
                "may rebind/reset USB control channel",
                "declared destructive",
                "requires explicit operator confirmation",
            ],
        )
        self.assertEqual(
            result.required_flags,
            ["--allow-ncm", "--allow-usb-rebind", "--allow-destructive", "--assume-yes"],
        )
        self.assertTrue(result.metadata["external_bridge_client"])
        self.assertFalse(result.metadata["read_only"])

    def test_risky_module_allows_only_when_all_gate_options_are_set(self):
        partial = gate.evaluate_gate(RiskyModule(), gate.GateOptions(allow_ncm=True))
        self.assertFalse(partial.allowed)
        self.assertEqual(
            partial.required_flags,
            ["--allow-usb-rebind", "--allow-destructive", "--assume-yes"],
        )

        result = gate.evaluate_gate(
            RiskyModule(),
            gate.GateOptions(
                allow_ncm=True,
                allow_usb_rebind=True,
                allow_destructive=True,
                assume_yes=True,
            ),
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.reasons, [])
        self.assertEqual(result.required_flags, [])

    def test_gate_result_to_dict_serializes_full_decision(self):
        result = gate.GateResult(
            allowed=False,
            reasons=["reason"],
            required_flags=["--flag"],
            metadata={"k": "v"},
        )

        self.assertEqual(
            result.to_dict(),
            {
                "allowed": False,
                "reasons": ["reason"],
                "required_flags": ["--flag"],
                "metadata": {"k": "v"},
            },
        )


if __name__ == "__main__":
    unittest.main()
