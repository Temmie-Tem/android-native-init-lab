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
#
# The canonical header each runner must pin, written out here rather than read
# from the runner. Taking the header from the module under test makes the guard
# circular: a runner re-bound to a freshly written section, with digests to
# match, would pass every check below while the section it is supposed to pin
# went stale. These literals are the independent anchor, so a rename has to be
# made here - in the same change, by hand - before any of it passes.
SECTION_PINNED_RUNNERS = {
    "s20plus_g986n_pstore_readiness_d0": "## S20+ Pstore/PMSG Readiness D0",
    "s20plus_g986n_last_kmsg_observation_d0": "## S20+ last_kmsg Record-Format D0",
    "s20plus_g986n_pmsg_warm_reboot_d1": "## S20+ PMSG Warm-Reboot Marker D1",
}
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


def header_of(module):
    """The header a runner pins, by whichever constant it uses."""
    return getattr(module, "CONTRACT_SECTION", None) or getattr(module, "SECTION")


def section_of(name):
    """The canonical contract section for a runner, addressed by literal.

    Deliberately keyed by runner *name* and not by the module: the header comes
    from the table above, so the section this returns is the one the repository
    says is canonical rather than whichever one the runner currently points at.
    """
    header = SECTION_PINNED_RUNNERS[name]
    text = CONTRACT.read_text()
    if text.count(header + "\n") != 1:
        raise AssertionError(f"{header!r} is absent or duplicated in the contract")
    return text.split(header + "\n", 1)[1].split("\n## ", 1)[0]


class ContractSectionPinTests(unittest.TestCase):
    def test_every_runner_pins_the_canonical_section_header(self):
        # The check that makes the rest of this class non-circular. A runner
        # re-bound to a section of its own making fails here first.
        for name, header in SECTION_PINNED_RUNNERS.items():
            with self.subTest(runner=name):
                self.assertEqual(header_of(load(name)), header)

    def test_every_pinned_section_exists_exactly_once(self):
        for name in SECTION_PINNED_RUNNERS:
            with self.subTest(runner=name):
                self.assertTrue(section_of(name).strip())

    def test_pinned_normalized_digest_matches_the_runner(self):
        # The exact line the runner's require_active looks for. A source edit
        # that does not re-pin the section fails here rather than at activation.
        for name in SECTION_PINNED_RUNNERS:
            with self.subTest(runner=name):
                module = load(name)
                expected = "Runner-Normalized-SHA256: `" + normalized_of(module) + "`"
                self.assertEqual(section_of(name).splitlines().count(expected), 1)

    def test_pinned_root_script_digest_matches_the_runner(self):
        for name in SECTION_PINNED_RUNNERS:
            module = load(name)
            script = getattr(module, "ROOT_SCRIPT", None)
            if script is None:
                continue
            with self.subTest(runner=name):
                expected = "Root-Script-SHA256: `" + hashlib.sha256(script.encode()).hexdigest() + "`"
                self.assertEqual(section_of(name).splitlines().count(expected), 1)

    def test_dormant_runners_do_not_carry_their_active_status_line(self):
        # Both activation atoms must be unset together. A section left saying
        # ACTIVE beside a False boolean is a half-armed capability.
        for name in SECTION_PINNED_RUNNERS:
            module = load(name)
            active = getattr(module, "ACTIVE", None)
            if active is not False:
                continue
            with self.subTest(runner=name):
                for line in section_of(name).splitlines():
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


class RecordedDeferralTests(unittest.TestCase):
    """Deferred defects must stay exactly as recorded, in number and in place.

    Two defects on this target are recorded rather than repaired, because
    repairing them would disturb the only active D0 and an active F1 to fix
    behaviour that is currently harmless here. A record is only worth deferring
    to if it stays true, so these enumerate the sites mechanically: a new copy,
    or a silent repair of one copy but not the others, fails here.
    """

    # `context=$(/system/bin/cat /proc/self/attr/current)` reports the exec'd
    # helper's SELinux context, not the shell's. The same files read
    # /proc/1/attr/current with an explicit pid, which is correct - the contrast
    # is inside a single script. On this target no domain transition occurs for a
    # system_file exec from the Magisk domain, so the value read is the value
    # intended and every identity predicate in the consumed trials passed.
    ATTR_SELF_SITES = {
        "s20plus_g986n_attended_root_health_d0.py",
        "s20plus_g986n_recovery_digest_profile_h0.py",
        "s20plus_g986n_boot_recovery_canary_b0_f1.py",
    }

    def sites(self, needle):
        found = {}
        for path in sorted(REVALIDATION.glob("s20plus_g986n_*.py")):
            hits = [
                line for line in path.read_text().splitlines()
                if needle in line and "/proc/1/attr" not in line
            ]
            if hits:
                found[path.name] = len(hits)
        return found

    def test_proc_self_attr_sites_are_exactly_the_recorded_three(self):
        found = self.sites("/proc/self/attr/current")
        self.assertEqual(set(found), self.ATTR_SELF_SITES)
        for name, count in found.items():
            with self.subTest(runner=name):
                self.assertEqual(count, 1, f"{name} grew a second copy")

    def test_each_site_still_reads_pid1_context_with_an_explicit_pid(self):
        # The contrast that makes this a defect rather than a style choice: the
        # same scripts get pid 1 right.
        for name in self.ATTR_SELF_SITES:
            with self.subTest(runner=name):
                text = (REVALIDATION / name).read_text()
                self.assertIn("/proc/1/attr/current", text)

    def test_the_deferral_is_recorded_for_every_site_not_just_one(self):
        body = CONTRACT.read_text()
        for name in self.ATTR_SELF_SITES:
            with self.subTest(runner=name):
                self.assertIn(name, body, "site is not named in the contract record")

    # The readiness D0 reads two watchdog attributes under an S22+-era node
    # address. Both recorded `absent` on this target, and the verdict logic
    # tolerates absent, so the two facts are vacuous rather than wrong. No S20+
    # evidence establishes the correct path, so they are recorded, not guessed.
    VACUOUS_WATCHDOG_PATHS = (
        "/sys/bus/platform/devices/17c10000.qcom,wdt/pet_time",
        "/sys/bus/platform/devices/17c10000.qcom,wdt/user_pet_enabled",
    )

    def test_vacuous_watchdog_paths_are_still_the_recorded_two(self):
        text = (REVALIDATION / "s20plus_g986n_pstore_readiness_d0.py").read_text()
        for path in self.VACUOUS_WATCHDOG_PATHS:
            with self.subTest(path=path):
                self.assertEqual(text.count(path), 1)
        self.assertIn("17c10000.qcom,wdt", CONTRACT.read_text())

if __name__ == "__main__":
    unittest.main()
