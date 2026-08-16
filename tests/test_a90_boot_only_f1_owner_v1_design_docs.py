"""Pin the boot-only F1 owner design, especially the rule that breaks the loop.

Six reviews of the per-candidate runner each found real defects, and the cause
was structural: review findings were stored as code constants, so recording a
review changed the thing it reviewed. This design separates them. These tests
hold that separation, hold the hardcoded limits a manifest must never be able
to express, and hold the hazard binding at all three points -- because this
session twice shipped a field that nothing enforced.
"""

from __future__ import annotations

import ast
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


def flatten(text: str) -> str:
    """Collapse wrapping and blockquote markers, as the sibling docs tests do."""
    return " ".join(text.replace("> ", " ").split())


REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / "docs/plans/A90_BOOT_ONLY_F1_OWNER_V1_DESIGN_2026-08-17.md"
SERVER = REPO / "workspace/public/src/scripts/server-distro"
FLASH = REPO / "workspace/public/src/scripts/revalidation/native_init_flash.py"
REVALIDATION = FLASH.parent
ORCHESTRATOR = SERVER / "a90_v3403_f1_orchestrator.py"
GOAL = REPO / "GOAL_A90.md"
PROCESS = REPO / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
TARGET = REPO / "docs/operations/targets/A90_TARGET_CONTRACT.md"

FLASH_SHA = "366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53"
RUNTIME_CLOSURE_SHA = "4dd44f10cae4ebe872a047391fe7e1e81f4f8cff2e703df3085252f298ccbe13"
RUNTIME_CLOSURE = {
    "_workspace_bootstrap.py": (
        1_255,
        "7a8322f9760c8aa3672e094b01df0231fb5b0a85ceaeb5ad73042fcd3f3a6ffe",
    ),
    "a90_observation_pipeline.py": (
        24_478,
        "6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb",
    ),
    "a90_serial_lock.py": (
        2_860,
        "663dd16f5121e35fc1047d563bdbe55148695224cf0c6ca5ab59c0433b6191c7",
    ),
    "a90_transition_contract_v2.py": (
        13_734,
        "64e640dfb54d016f8e5548aea0da167e7f6917bf40c02fbc971773ef181b1c7e",
    ),
    "a90ctl.py": (
        16_380,
        "4d72b87b42ef49c5997ddcd24d0c6bb4fe94766c2c7fddaa21b07ff218009f8c",
    ),
    "native_init_flash.py": (43_118, FLASH_SHA),
}
RETIRED = (
    "a90_h15_ufs_f1_runner_v1.py",
    "a90_h15_ufs_d1_runner_v1.py",
    "a90_h16_ufs_f1_runner_v1.py",
    "a90_h16_ufs_d1_runner_v1.py",
    "a90_h17_ufs_f1_runner_v1.py",
    "a90_h17_ufs_d1_runner_v1.py",
    "a90_h18_ufs_f1_runner_v1.py",
    "a90_h18_ufs_d1_runner_v1.py",
    "a90_h24_ufs_f1_runner_v1.py",
    "a90_h24_ufs_d1_runner_v1.py",
    "a90_h27_ufs_f1_runner_v1.py",
)


def generated_runtime_closure(root: Path) -> set[str]:
    """Derive the exact same-directory non-stdlib import closure."""
    available = {path.stem: path for path in root.parent.glob("*.py")}
    pending = [root.stem]
    resolved: set[str] = set()
    while pending:
        module = pending.pop()
        if module in resolved:
            continue
        path = available.get(module)
        if path is None:
            raise AssertionError(f"unresolved local module: {module}")
        resolved.add(module)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                dynamic = (
                    isinstance(node.func, ast.Name) and node.func.id == "__import__"
                ) or (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "importlib"
                    and node.func.attr == "import_module"
                )
                if dynamic:
                    raise AssertionError(f"dynamic import is not admissible: {path}")
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [item.name.split(".", 1)[0] for item in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".", 1)[0]]
            for name in names:
                if name == "__future__" or name in sys.stdlib_module_names:
                    continue
                if name not in available:
                    raise AssertionError(
                        f"unresolved non-stdlib import {name!r} in {path.name}"
                    )
                if name not in resolved:
                    pending.append(name)
    return {f"{module}.py" for module in resolved}


def runtime_closure_digest(names: set[str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(names):
        path = REVALIDATION / name
        data = path.read_bytes()
        file_sha = hashlib.sha256(data).hexdigest()
        digest.update(f"{name}\0{len(data)}\0{file_sha}\n".encode("ascii"))
    return digest.hexdigest()


class BootOnlyF1OwnerDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = DESIGN.read_text(encoding="utf-8")
        self.design = flatten(self.raw)

    def test_it_is_a_structural_draft_that_authorizes_nothing(self) -> None:
        head = flatten(self.raw[: self.raw.index("## The loop being removed")])
        self.assertIn("DRAFT", head)
        self.assertIn("grants no authority", head)
        self.assertIn("implements nothing", head)
        self.assertIn("Device or live effect of this document: none", head)

    def test_the_cycle_breaking_rule_is_stated_as_a_rule(self) -> None:
        """This is the whole point; it must not read as a nice-to-have."""
        self.assertIn(
            "**Review artifacts sign the owner closure. The owner closure never contains\nreview artifacts.**",
            self.raw,
        )
        self.assertIn("producing it cannot change what it signed", self.design)
        self.assertIn("There is no fixed point", self.design)

    def test_both_causes_of_the_loop_are_named(self) -> None:
        self.assertIn("Self-reference", self.design)
        self.assertIn("Lineage drag", self.design)
        self.assertIn("32 places", self.design)
        self.assertIn("colliding journal namespaces", self.design)

    def test_the_two_review_layers_separate_code_from_data(self) -> None:
        self.assertIn("only when owner code changes", self.design)
        self.assertIn("every candidate", self.design)
        self.assertIn("they do not re-open the owner capability review", self.design)

    def test_the_manifest_cannot_express_authority(self) -> None:
        for token in (
            "the `boot` partition as the only writable target",
            "exactly one candidate attempt",
            "exactly one rollback attempt",
            "cannot name a command, a partition, or a retry count",
        ):
            self.assertIn(token, self.design, token)
        self.assertIn("`--boot-block` and `--remote-image` at their defaults", self.design)

    def test_preflight_separates_healthy_from_expected(self) -> None:
        """Conflating them is how an H18 predecessor survived in an H27 runner."""
        self.assertIn("the device is healthy", self.design)
        self.assertIn("is the resident this manifest expects", self.design)
        self.assertIn("stops before any effect", self.design)

    def test_runtime_rehash_replaces_delegated_verification(self) -> None:
        self.assertIn("at execution time", self.design)
        self.assertIn("That is the authoritative check", self.design)
        self.assertIn("No reviewer reads private bytes", self.design)
        self.assertIn("no receipt needs binding", self.design)

    def test_the_hazard_is_bound_at_three_points(self) -> None:
        """A field nothing enforces is decoration; this session shipped two."""
        self.assertIn("RKP_CFP_DISABLED_RESIDENT", self.design)
        self.assertIn("binds it by digest", self.design)
        self.assertIn("over the manifest SHA **and** the hazard ID", self.design)
        self.assertIn("`accepted: true`", self.design)
        self.assertIn("unknown or unqualified hazard ID stops the owner", self.design)
        self.assertIn("empty invariant tuple", self.design)

    def test_the_state_machine_has_three_terminals_and_no_refuted(self) -> None:
        for state in (
            "PREPARED",
            "APPROVED",
            "CANDIDATE_INTENT",
            "ROLLBACK_INTENT",
            "ROLLBACK_LAUNCHED",
            "ROLLBACK_RESULT",
            "ROLLBACK_RELEASE_UNCERTAIN",
            "PASS_A90_H27_RESIDENT_INSTALLED",
            "NO_PROOF_ROLLED_BACK",
            "RECOVERY_REQUIRED",
        ):
            self.assertIn(state, self.raw, state)
        self.assertIn("There is no `REFUTED`", self.design)
        self.assertIn("does not adjudicate why a kernel failed to boot", self.design)
        self.assertIn(
            """PREPARED
  -> APPROVED
  -> CANDIDATE_INTENT
       -> PASS_A90_H27_RESIDENT_INSTALLED
       -> ROLLBACK_INTENT
            -> ROLLBACK_LAUNCHED
                 -> ROLLBACK_RESULT
                      -> NO_PROOF_ROLLED_BACK
                      -> RECOVERY_REQUIRED
                 -> ROLLBACK_RELEASE_UNCERTAIN
                      -> RECOVERY_REQUIRED""",
            self.raw,
        )

    def test_rollback_has_durable_one_shot_crash_prefixes(self) -> None:
        """Only intent-without-launch may resume; release uncertainty never replays."""
        for token in (
            "file and directory `fsync`",
            "target identity",
            "run ID",
            "rollback SHA256",
            "helper SHA256",
            "process-group identity",
            "release-gate identity",
            "log identity",
            "transport generation",
            "attempt `1`",
            "cannot exec the flash helper or open the transport",
            "EOF or any byte other than the exact release byte",
            "one release write",
            "intent exists without `ROLLBACK_LAUNCHED`",
            "same bound rollback",
            "observation and health reconciliation only",
            "must never start a second helper",
        ):
            self.assertIn(token, self.design, token)
        self.assertIn(
            "`ROLLBACK_LAUNCHED` is the one-shot consumption point",
            self.design,
        )
        self.assertIn(
            "`ROLLBACK_RESULT` never reconstructs a missing helper return",
            self.design,
        )

    def test_rollback_prefixes_preserve_the_binding_contract(self) -> None:
        target = flatten(TARGET.read_text(encoding="utf-8"))
        process = flatten(PROCESS.read_text(encoding="utf-8"))
        self.assertIn(
            "A rollback intent without a launch resumes only that same bound rollback",
            target,
        )
        self.assertIn(
            "An uncertain released rollback is never replayed",
            target,
        )
        self.assertIn("`rollback_transfer_started`", process)
        self.assertIn("`rollback_transfer_completed`", process)
        self.assertIn("intent-only prefix may still launch its same bound attempt", self.design)
        self.assertIn("launched prefix with no complete result permits observation", self.design)

    def test_the_closure_excludes_the_orchestrator(self) -> None:
        self.assertIn("must not import `a90_v3403_f1_orchestrator.py`", self.design)
        self.assertIn("closure constraint, not a\nstyle preference", self.raw)
        self.assertTrue(ORCHESTRATOR.is_file(), str(ORCHESTRATOR))

    def test_the_pinned_flash_helper_digest_is_real(self) -> None:
        self.assertIn(FLASH_SHA, self.raw)
        self.assertTrue(FLASH.is_file(), str(FLASH))
        self.assertEqual(hashlib.sha256(FLASH.read_bytes()).hexdigest(), FLASH_SHA)

    def test_flash_helper_runtime_closure_is_generated_and_exact(self) -> None:
        derived = generated_runtime_closure(FLASH)
        self.assertEqual(derived, set(RUNTIME_CLOSURE))
        self.assertEqual(runtime_closure_digest(derived), RUNTIME_CLOSURE_SHA)
        self.assertIn("generated exact non-stdlib import closure", self.design)
        self.assertIn("dynamic import is `NO_GO`", self.design)

    def test_every_runtime_closure_member_is_pinned_by_size_and_hash(self) -> None:
        for name, (expected_size, expected_sha) in RUNTIME_CLOSURE.items():
            path = REVALIDATION / name
            data = path.read_bytes()
            self.assertEqual(len(data), expected_size, name)
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected_sha, name)
            self.assertIn(f"`{name}`", self.raw, name)
            self.assertIn(expected_sha, self.raw, name)
        self.assertIn(RUNTIME_CLOSURE_SHA, self.raw)

    def test_runtime_closure_rejects_unresolved_and_dynamic_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "root.py"
            root.write_text("import not_in_stdlib_or_closure\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "unresolved non-stdlib"):
                generated_runtime_closure(root)
            root.write_text("__import__('json')\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "dynamic import"):
                generated_runtime_closure(root)

    def test_every_named_retired_runner_exists_and_is_listed(self) -> None:
        for name in RETIRED:
            self.assertIn(name, self.raw, name)
            self.assertTrue((SERVER / name).is_file(), name)
        self.assertIn("must not execute a new candidate", self.design)
        self.assertIn("A90-H15-F1-APPROVE:", self.design)
        self.assertIn("`h15-f1-live`", self.design)

    def test_the_hostile_corpus_covers_the_defects_reviews_found(self) -> None:
        """Each entry here maps to a real failure, not a hypothetical."""
        for token in (
            "non-`boot` partition",
            "more than one candidate or rollback attempt",
            "resident other than `expected_start`",
            "runtime hash differs from the manifest",
            "approval token that does not derive from this manifest SHA",
            "missing the hazard ID",
            "crash after `CANDIDATE_INTENT`",
            "without\n  candidate replay",
            "crash before `ROLLBACK_INTENT`",
            "crash after `ROLLBACK_INTENT` and before `ROLLBACK_LAUNCHED`",
            "crash after `ROLLBACK_LAUNCHED` and before release",
            "lost helper return after rollback dispatch",
            "crash while publishing `ROLLBACK_RESULT`",
            "duplicate or mismatched rollback intent or result",
            "colliding with a retired runner's namespace",
        ):
            self.assertIn(token, self.raw, token)

    def test_it_does_not_overclaim_what_it_saves(self) -> None:
        self.assertIn("does not remove the one-time cost", self.design)
        self.assertIn("needs a full capability review before first use", self.design)
        self.assertIn("It does not implement the owner", self.design)
        self.assertIn("It does not authorize an F1", self.design)

    def test_the_goal_still_forbids_a_successor(self) -> None:
        quoted = "No successor candidate, approval, transfer, reboot, or D1 effect"
        self.assertIn(quoted, flatten(GOAL.read_text(encoding="utf-8")))
        self.assertIn("no successor candidate, transfer, or reboot is authorized", self.design)

    def test_the_h27_work_is_declared_carried_forward(self) -> None:
        self.assertIn("retired before ever executing", self.design)
        self.assertIn("phase3-minimal-h27", self.design)
        self.assertIn("are unaffected and carry forward", self.design)


if __name__ == "__main__":
    unittest.main()
