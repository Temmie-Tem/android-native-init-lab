"""Drift guards between S20+ runners and the policy documents they pin.

Several S20+ capabilities pin policy text verbatim as an activation atom: a
contract section header, its status line, its `Runner-Normalized-SHA256` and
`Root-Script-SHA256`, and for the P0 F1 owner the AGENTS registry table's
header, separator and live-process cell.

A documentation edit that changes any of that without re-pinning breaks the
runner. While the runner is dormant nothing exercises it, so the breakage is
silent until someone tries to activate - and then it fails closed at the
activation gate rather than at review time.

That happened. A docs commit trimmed the registry header from "Binding live
process" to "Live process" and reformatted the separator to spaced pipes,
updating several affected tests but not the P0 F1 owner. Later registry row
edits drifted the live-process cell away from both reviewed values. The lane sat
broken until it was noticed by hand.

These tests are the mechanical version of noticing. They run unconditionally and
depend on no private artifact, so a docs edit that desynchronizes a runner fails
here, in the same change that caused it.
"""
import hashlib
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
CONTRACT = ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
AGENTS = ROOT / "AGENTS.md"

# Every S20+ runner that pins a contract section by name. Each must still find
# its section, and each pinned digest must equal what the runner computes now.
SECTION_PINNED_RUNNERS = (
    "s20plus_g986n_pstore_readiness_d0",
    "s20plus_g986n_last_kmsg_observation_d0",
    "s20plus_g986n_pmsg_warm_reboot_d1",
)
P0_OWNER = "s20plus_g986n_p0_pid1_odin_f1"


def load(name):
    path = REVALIDATION / (name + ".py")
    spec = importlib.util.spec_from_file_location("_drift_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_of(module):
    """The runner's own normalized digest, under either accessor it exposes."""
    if hasattr(module, "source_receipt"):
        return module.source_receipt()["normalized_sha256"]
    return module.normalized_source()


def section_of(module):
    """The contract section a runner pins, by whichever constant it uses."""
    header = getattr(module, "CONTRACT_SECTION", None) or getattr(module, "SECTION")
    text = CONTRACT.read_text()
    if text.count(header + "\n") != 1:
        raise AssertionError(f"{header!r} is absent or duplicated in the contract")
    return text.split(header + "\n", 1)[1].split("\n## ", 1)[0]


class ContractSectionPinTests(unittest.TestCase):
    def test_every_pinned_section_exists_exactly_once(self):
        for name in SECTION_PINNED_RUNNERS:
            with self.subTest(runner=name):
                self.assertTrue(section_of(load(name)).strip())

    def test_pinned_normalized_digest_matches_the_runner(self):
        # The exact line the runner's require_active looks for. A source edit
        # that does not re-pin the section fails here rather than at activation.
        for name in SECTION_PINNED_RUNNERS:
            with self.subTest(runner=name):
                module = load(name)
                expected = "Runner-Normalized-SHA256: `" + normalized_of(module) + "`"
                self.assertEqual(section_of(module).splitlines().count(expected), 1)

    def test_pinned_root_script_digest_matches_the_runner(self):
        for name in SECTION_PINNED_RUNNERS:
            module = load(name)
            script = getattr(module, "ROOT_SCRIPT", None)
            if script is None:
                continue
            with self.subTest(runner=name):
                expected = "Root-Script-SHA256: `" + hashlib.sha256(script.encode()).hexdigest() + "`"
                self.assertEqual(section_of(module).splitlines().count(expected), 1)

    def test_dormant_runners_do_not_carry_their_active_status_line(self):
        # Both activation atoms must be unset together. A section left saying
        # ACTIVE beside a False boolean is a half-armed capability.
        for name in SECTION_PINNED_RUNNERS:
            module = load(name)
            active = getattr(module, "ACTIVE", None)
            if active is not False:
                continue
            with self.subTest(runner=name):
                for line in section_of(module).splitlines():
                    self.assertNotRegex(
                        line, r"^Status: \*\*BINDING - .* ACTIVE\*\*$",
                        f"{name} is dormant but its section claims ACTIVE",
                    )


class P0ActivationDocumentTests(unittest.TestCase):
    """The exact class of drift that broke this lane, checked mechanically."""

    def setUp(self):
        self.module = load(P0_OWNER)

    def test_registry_header_and_separator_are_present_verbatim(self):
        text = AGENTS.read_text()
        source = (REVALIDATION / (P0_OWNER + ".py")).read_text()
        header = re.search(r'\n    header = "([^"]+)"', source)[1]
        separator = re.search(r'\n    separator = "([^"]+)"', source)[1]
        self.assertEqual(text.count(header), 1, "registry header drifted from the owner")
        self.assertIn(separator, text, "registry separator drifted from the owner")

    def test_current_documents_match_a_reviewed_activation_state(self):
        # This is the check that silently failed: every pinned document cell must
        # equal either the reviewed dormant value or the reviewed active one.
        current = self.module._current_document_semantics()
        dormant = self.module.P0_DORMANT_DOCUMENT_SEMANTICS
        active = self.module.P0_ACTIVE_DOCUMENT_SEMANTICS
        for name in dormant:
            with self.subTest(document=name):
                self.assertIn(
                    current[name], (dormant[name], active[name]),
                    f"{name} matches neither the reviewed dormant nor active value",
                )

    def test_dormant_owner_sees_the_dormant_documents(self):
        if self.module.P0_F1_ACTIVE:
            self.skipTest("owner is active")
        self.assertEqual(
            self.module._current_document_semantics(),
            self.module.P0_DORMANT_DOCUMENT_SEMANTICS,
        )

    def test_owner_self_identity_is_pinned_to_its_own_bytes(self):
        # The owner refuses to run unless its normalized digest matches; a rebind
        # that forgets to re-pin fails here instead of at the first gate.
        self.assertEqual(
            self.module.normalized_self_sha256(),
            self.module.EXPECTED_REVIEWED_NORMALIZED_SHA256,
        )

    def test_registry_row_is_addressed_by_the_owner_and_unambiguous(self):
        cell = self.module._registry_process_cell(AGENTS.read_text())
        self.assertIn(
            cell,
            (
                self.module.P0_DORMANT_REGISTRY_PROCESS_CELL,
                self.module.P0_ACTIVE_REGISTRY_PROCESS_CELL,
            ),
            "the S20+ registry live-process cell drifted from both reviewed values",
        )


if __name__ == "__main__":
    unittest.main()
