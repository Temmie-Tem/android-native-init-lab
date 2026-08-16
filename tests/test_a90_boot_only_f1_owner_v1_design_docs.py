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
import json
import subprocess
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
BOOTSTRAP = REVALIDATION / "a90_boot_only_f1_helper_bootstrap.py"
ORCHESTRATOR = SERVER / "a90_v3403_f1_orchestrator.py"
GOAL = REPO / "GOAL_A90.md"
PROCESS = REPO / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
TARGET = REPO / "docs/operations/targets/A90_TARGET_CONTRACT.md"

FLASH_SHA = "366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53"
RUNTIME_CLOSURE_SHA = "ec8b55608d37028abf286061738edd54cbe7470165f7a40c42f1ff5821d62cbf"
RUNTIME_CLOSURE = {
    "_workspace_bootstrap.py": (
        1_255,
        "7a8322f9760c8aa3672e094b01df0231fb5b0a85ceaeb5ad73042fcd3f3a6ffe",
    ),
    "a90_observation_pipeline.py": (
        24_478,
        "6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb",
    ),
    "a90_boot_only_f1_helper_bootstrap.py": (
        2_801,
        "c1fadd1aa6b84707cdb813c96c681a0067c826a695fbf9ca4559fac8be7b8b9c",
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

SUCCESS_TERMINAL = "PASS_A90_RESIDENT_INSTALLED"
SUCCESS_SCHEMA = "resident-install-terminal-v1"
MANIFEST_KEYS = frozenset(
    {"candidateSha256", "expectedVersion", "expectedBuild", "hazards"}
)
SUCCESS_PAYLOAD_KEYS = frozenset(
    {
        "schema",
        "terminal",
        "targetEvidenceSha256",
        "runId",
        "journalNamespace",
        "manifestSha256",
        "candidateSha256",
        "expectedVersion",
        "expectedBuild",
        "observedVersion",
        "observedBuild",
        "ownerClosureSha256",
        "approvalBindingSha256",
        "observationResult",
        "acceptanceRuleSha256",
        "hazards",
        "finalHealth",
        "finalHealthReceiptSha256",
    }
)
ARTIFACT_IDENTITY_KEYS = frozenset(
    {
        "role",
        "path",
        "pathType",
        "fdType",
        "pathDev",
        "pathIno",
        "fdDev",
        "fdIno",
        "mode",
        "uid",
        "gid",
        "nlink",
        "size",
        "sha256",
    }
)
EXECUTABLE_IDENTITY_KEYS = ARTIFACT_IDENTITY_KEYS | {
    "versionReceiptSha256",
    "runtimeClosureSha256",
}
EXECUTABLE_ROLES = frozenset({"python-interpreter", "adb-transport"})


def artifact_identity(**overrides: object) -> dict[str, object]:
    identity: dict[str, object] = {
        "role": "candidate",
        "path": "/stable/a90/candidate.img",
        "pathType": "regular",
        "fdType": "regular",
        "pathDev": 10,
        "pathIno": 20,
        "fdDev": 10,
        "fdIno": 20,
        "mode": 0o100600,
        "uid": 1000,
        "gid": 1000,
        "nlink": 1,
        "size": 4096,
        "sha256": "d" * 64,
    }
    identity.update(overrides)
    return identity


def validate_artifact_checkpoint(
    bound: dict[str, object],
    current: dict[str, object],
) -> None:
    """Reference model for the held-FD plus pathname lifetime check."""
    if frozenset(bound) != ARTIFACT_IDENTITY_KEYS or frozenset(current) != ARTIFACT_IDENTITY_KEYS:
        raise ValueError("artifact identity schema mismatch")
    if current["pathType"] != "regular" or current["fdType"] != "regular":
        raise ValueError("artifact is not regular")
    if current["nlink"] != 1:
        raise ValueError("artifact link count drift")
    if bound["uid"] != 1000 or current["uid"] != 1000:
        raise ValueError("artifact owner mismatch")
    if type(current["mode"]) is not int or current["mode"] & 0o022:
        raise ValueError("artifact mode drift")
    if (current["pathDev"], current["pathIno"]) != (
        current["fdDev"],
        current["fdIno"],
    ):
        raise ValueError("pathname and held FD differ")
    if current != bound:
        raise ValueError("artifact identity or content drift")


def executable_identity(
    role: str,
    path: str,
    **overrides: object,
) -> dict[str, object]:
    identity = artifact_identity(role=role, path=path)
    identity.update(
        versionReceiptSha256="a" * 64,
        runtimeClosureSha256="b" * 64,
    )
    identity.update(overrides)
    return identity


def validate_executable_checkpoint(
    bound: dict[str, object],
    current: dict[str, object],
) -> None:
    """Reference model for the owner-fixed Python/ADB executable boundary."""
    if (
        frozenset(bound) != EXECUTABLE_IDENTITY_KEYS
        or frozenset(current) != EXECUTABLE_IDENTITY_KEYS
    ):
        raise ValueError("executable identity schema mismatch")
    if bound["role"] not in EXECUTABLE_ROLES or current["role"] != bound["role"]:
        raise ValueError("executable role mismatch")
    for value in (bound["path"], current["path"]):
        if type(value) is not str or not Path(value).is_absolute():
            raise ValueError("executable path is not absolute")
    for key in ("versionReceiptSha256", "runtimeClosureSha256"):
        for value in (bound[key], current[key]):
            if type(value) is not str or len(value) != 64:
                raise ValueError("executable digest malformed")
            if any(char not in "0123456789abcdef" for char in value):
                raise ValueError("executable digest malformed")
    artifact_keys = ARTIFACT_IDENTITY_KEYS
    validate_artifact_checkpoint(
        {key: bound[key] for key in artifact_keys},
        {key: current[key] for key in artifact_keys},
    )
    if current != bound:
        raise ValueError("executable identity or runtime closure drift")


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def canonical_manifest(**overrides: object) -> bytes:
    manifest: dict[str, object] = {
        "candidateSha256": "3" * 64,
        "expectedVersion": "0.11.194",
        "expectedBuild": "h27-build",
        "hazards": [
            {
                "id": "RKP_CFP_DISABLED_RESIDENT",
                "qualificationSha256": "7" * 64,
                "accepted": True,
            }
        ],
    }
    manifest.update(overrides)
    return canonical_json(manifest)


def strict_canonical_object(raw: bytes, keys: frozenset[str]) -> dict[str, object]:
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    value = json.loads(raw.decode("ascii"), object_pairs_hook=reject_duplicate_keys)
    if type(value) is not dict or frozenset(value) != keys:
        raise ValueError("schema mismatch")
    if raw != canonical_json(value):
        raise ValueError("non-canonical JSON")
    return value


def canonical_success_payload(
    manifest_raw: bytes | None = None,
    **overrides: object,
) -> bytes:
    """Reference fixture for the candidate-neutral terminal schema."""
    manifest_raw = manifest_raw if manifest_raw is not None else canonical_manifest()
    manifest = strict_canonical_object(manifest_raw, MANIFEST_KEYS)
    payload: dict[str, object] = {
        "schema": SUCCESS_SCHEMA,
        "terminal": SUCCESS_TERMINAL,
        "targetEvidenceSha256": "1" * 64,
        "runId": "run-01",
        "journalNamespace": "a90-boot-only-owner-v1",
        "manifestSha256": hashlib.sha256(manifest_raw).hexdigest(),
        "candidateSha256": manifest["candidateSha256"],
        "expectedVersion": manifest["expectedVersion"],
        "expectedBuild": manifest["expectedBuild"],
        "observedVersion": manifest["expectedVersion"],
        "observedBuild": manifest["expectedBuild"],
        "ownerClosureSha256": "4" * 64,
        "approvalBindingSha256": "5" * 64,
        "observationResult": "ACCEPTED",
        "acceptanceRuleSha256": "6" * 64,
        "hazards": manifest["hazards"],
        "finalHealth": "RESIDENT_HEALTHY",
        "finalHealthReceiptSha256": "8" * 64,
    }
    payload.update(overrides)
    return canonical_json(payload)


def validate_success_payload(
    terminal: str,
    raw: bytes,
    *,
    manifest_raw: bytes,
) -> dict[str, object]:
    """Minimal consumer model that prevents terminal/candidate substitution."""
    if terminal != SUCCESS_TERMINAL:
        raise ValueError("candidate-specific or unknown success terminal")

    manifest = strict_canonical_object(manifest_raw, MANIFEST_KEYS)
    payload = strict_canonical_object(raw, SUCCESS_PAYLOAD_KEYS)
    for key in SUCCESS_PAYLOAD_KEYS - {"hazards"}:
        if type(payload[key]) is not str:
            raise ValueError(f"terminal field type mismatch: {key}")
    if payload["schema"] != SUCCESS_SCHEMA or payload["terminal"] != terminal:
        raise ValueError("terminal vocabulary mismatch")
    if payload["manifestSha256"] != hashlib.sha256(manifest_raw).hexdigest():
        raise ValueError("cross-manifest terminal")
    if payload["candidateSha256"] != manifest["candidateSha256"]:
        raise ValueError("candidate digest substitution")
    if (payload["expectedVersion"], payload["expectedBuild"]) != (
        manifest["expectedVersion"],
        manifest["expectedBuild"],
    ):
        raise ValueError("manifest identity substitution")
    if (payload["observedVersion"], payload["observedBuild"]) != (
        manifest["expectedVersion"],
        manifest["expectedBuild"],
    ):
        raise ValueError("candidate identity mismatch")
    if payload["observationResult"] != "ACCEPTED":
        raise ValueError("observation not accepted")
    if payload["finalHealth"] != "RESIDENT_HEALTHY":
        raise ValueError("resident not healthy")
    hazards = payload["hazards"]
    if type(hazards) is not list or not hazards:
        raise ValueError("hazard binding missing")
    if hazards != manifest["hazards"]:
        raise ValueError("manifest hazard substitution")
    for hazard in hazards:
        if type(hazard) is not dict or set(hazard) != {
            "id",
            "qualificationSha256",
            "accepted",
        }:
            raise ValueError("hazard schema mismatch")
        if type(hazard["id"]) is not str or type(hazard["qualificationSha256"]) is not str:
            raise ValueError("hazard type mismatch")
        if hazard["accepted"] is not True:
            raise ValueError("hazard not accepted")
    return payload


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

    def test_artifact_lifetime_matches_process_v2(self) -> None:
        process = flatten(PROCESS.read_text(encoding="utf-8"))
        self.assertIn(
            "Recheck file descriptor identity and content after subprocess return",
            process,
        )
        for token in (
            "File lifetime and post-helper revalidation",
            "`O_RDONLY|O_CLOEXEC|O_NOFOLLOW`",
            "`artifact-identity-v1`",
            "st_dev",
            "st_ino",
            "st_nlink=1",
            "Every path ancestor below the configured artifact root",
            "real, non-symlink directory",
            "keeps each opened FD until the corresponding helper has exited",
            "signal, timeout, or lost return",
            "immediately before a candidate or rollback helper release",
            "after every normal or abnormal helper exit",
            "uses\nonly that sealed image for transfer",
            "before the owner interprets helper success",
            "After an owner crash, no vanished FD is reconstructed as proof",
            "requires the complete\ndurable `artifact-identity-v1` tuple",
        ):
            self.assertIn(token, self.raw, token)

    def test_artifact_checkpoint_rejects_path_content_and_link_drift(self) -> None:
        bound = artifact_identity()
        validate_artifact_checkpoint(bound, dict(bound))
        hostile = (
            {"pathType": "symlink"},
            {"pathIno": 21, "fdIno": 21},
            {"pathIno": 21},
            {"size": 2048},
            {"sha256": "e" * 64},
            {"mode": 0o100620},
            {"uid": 0},
            {"nlink": 2},
        )
        for mutation in hostile:
            with self.subTest(mutation=mutation):
                current = dict(bound)
                current.update(mutation)
                with self.assertRaisesRegex(ValueError, "artifact|pathname"):
                    validate_artifact_checkpoint(bound, current)
        wrong_owner = artifact_identity(uid=0)
        with self.assertRaisesRegex(ValueError, "owner"):
            validate_artifact_checkpoint(wrong_owner, dict(wrong_owner))

    def test_post_effect_drift_never_reopens_an_attempt(self) -> None:
        for token in (
            "mismatch after `CANDIDATE_INTENT` consumes the candidate attempt",
            "never\npermits candidate replay",
            "complete helper closure still\npass fresh exact checks",
            "parks as\n`RECOVERY_REQUIRED` without launching changed bytes",
            "mismatch after rollback\nrelease likewise never permits another rollback",
        ):
            self.assertIn(token, self.raw, token)

    def test_interpreter_and_transport_are_exact_executable_identities(self) -> None:
        for token in (
            "Interpreter and transport executable identity",
            "exactly one ordinary\nabsolute `PYTHON_EXECUTABLE` path",
            "one ordinary absolute `ADB_EXECUTABLE`\npath",
            "`executable-identity-v1`",
            "version-receipt\nSHA256",
            "exact runtime-closure SHA256",
            "python-runtime-closure-v1",
            "adb-runtime-closure-v1",
            "isolated-mode `-I`",
            "`shell=False`",
            "fake executable earlier in `PATH`",
            "never uses its\nbare `adb` default",
            "Python `-I` deliberately removes the script directory from `sys.path`",
            "does not execute `native_init_flash.py` directly",
            "installs only their fixed module names\nin `sys.modules`",
        ):
            self.assertIn(token, self.raw, token)

    def test_executable_checkpoint_rejects_path_byte_and_runtime_drift(self) -> None:
        for role, path in (
            ("python-interpreter", "/usr/bin/python3"),
            ("adb-transport", "/usr/bin/adb"),
        ):
            with self.subTest(role=role):
                bound = executable_identity(role, path)
                validate_executable_checkpoint(bound, dict(bound))
                for mutation in (
                    {"path": "adb"},
                    {"path": "relative/adb"},
                    {"pathIno": 21, "fdIno": 21},
                    {"sha256": "c" * 64},
                    {"versionReceiptSha256": "c" * 64},
                    {"runtimeClosureSha256": "c" * 64},
                ):
                    current = dict(bound)
                    current.update(mutation)
                    with self.assertRaisesRegex(ValueError, "executable|artifact"):
                        validate_executable_checkpoint(bound, current)

    def test_owner_launch_vector_cannot_use_path_or_caller_adb(self) -> None:
        flash_source = FLASH.read_text(encoding="utf-8")
        self.assertIn('default="adb"', flash_source)
        for token in (
            "Neither path may come from the manifest, an approval, a CLI argument",
            "`PATH`, `PYTHONPATH`, `shutil.which`, `/usr/bin/env`, a shell",
            "A bare or relative executable name is `NO_GO`",
            "[PYTHON_EXECUTABLE, -I, HELPER_BOOTSTRAP, fixed owner arguments, --adb,\nADB_EXECUTABLE]",
            "no\ncaller-supplied executable field",
            "same absolute ADB path to every candidate, rollback, observation,\nand recovery helper invocation",
        ):
            self.assertIn(token, self.raw, token)

    def test_real_isolated_bootstrap_launch_reaches_helper_cli(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", str(BOOTSTRAP), "--help"],
            cwd=REPO,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Flash a native init boot image", completed.stdout)

    def test_direct_isolated_helper_launch_remains_rejected(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", str(FLASH), "--help"],
            cwd=REPO,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("No module named 'a90ctl'", completed.stderr)

    def test_bootstrap_rejects_launch_without_isolated_mode(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(BOOTSTRAP), "--help"],
            cwd=REPO,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("requires Python isolated safe-path mode", completed.stderr)

    def test_bootstrap_is_exact_and_never_opens_sys_path(self) -> None:
        source = BOOTSTRAP.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(BOOTSTRAP))
        assigned = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "LOCAL_MODULE_ORDER"
                for target in node.targets
            )
        )
        order = tuple(name for name, _path in ast.literal_eval(assigned))
        expected = tuple(
            Path(name).stem
            for name in sorted(generated_runtime_closure(FLASH) - {FLASH.name})
        )
        self.assertEqual(set(order), set(expected))
        self.assertNotIn("sys.path.insert", source)
        self.assertNotIn("sys.path.append", source)
        self.assertIn("tuple(sys.path) != original_path", source)

    def test_the_hazard_is_bound_at_three_points(self) -> None:
        """A field nothing enforces is decoration; this session shipped two."""
        self.assertIn("RKP_CFP_DISABLED_RESIDENT", self.design)
        self.assertIn("binds it by digest", self.design)
        self.assertIn("inside the complete approval binding", self.design)
        self.assertIn("`accepted: true`", self.design)
        self.assertIn("unknown or unqualified hazard ID stops the owner", self.design)
        self.assertIn("empty invariant tuple", self.design)

    def test_approval_binding_is_exact_to_the_live_target_and_run(self) -> None:
        """Manifest equality must not transfer authority to another target/run."""
        for token in (
            "`approval-binding-v1`",
            "canonical typed JSON",
            "duplicate keys",
            "exact target profile",
            "live target evidence digest",
            "current boot ID",
            "run ID",
            "journal namespace",
            "manifest SHA256",
            "candidate SHA256",
            "rollback SHA256",
            "helper SHA256",
            "owner closure SHA256",
            "helper version",
            "exact Python/ADB executable identities",
            "both runtime-closure SHA256 values",
            "observation timeout and acceptance rule",
            "mandatory recovery plan",
            "hazard IDs and qualification digests",
            "expiry",
            "nonce",
            "immediately before `CANDIDATE_INTENT`",
            "atomically consumed",
            "same approval-binding SHA256",
        ):
            self.assertIn(token, self.design, token)

    def test_approval_binding_preserves_process_v2_inputs(self) -> None:
        process = flatten(PROCESS.read_text(encoding="utf-8"))
        target = flatten(TARGET.read_text(encoding="utf-8"))
        for token in (
            "exact target profile and live target evidence digest",
            "candidate and rollback AP SHA256",
            "manifest SHA256",
            "runner and Odin versions",
            "observation timeout and acceptance rule",
            "mandatory recovery plan",
        ):
            self.assertIn(token, process, token)
        self.assertIn("exact target, candidate, rollback, recovery evidence", target)
        self.assertIn("complete execution closure", target)

    def test_the_state_machine_has_three_terminals_and_no_refuted(self) -> None:
        for state in (
            "PREPARED",
            "APPROVED",
            "CANDIDATE_INTENT",
            "ROLLBACK_INTENT",
            "ROLLBACK_LAUNCHED",
            "ROLLBACK_RESULT",
            "ROLLBACK_RELEASE_UNCERTAIN",
            SUCCESS_TERMINAL,
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
       -> PASS_A90_RESIDENT_INSTALLED
       -> ROLLBACK_INTENT
            -> ROLLBACK_LAUNCHED
                 -> ROLLBACK_RESULT
                      -> NO_PROOF_ROLLED_BACK
                      -> RECOVERY_REQUIRED
                 -> ROLLBACK_RELEASE_UNCERTAIN
                      -> RECOVERY_REQUIRED""",
            self.raw,
        )

    def test_success_terminal_is_candidate_neutral_and_contract_aligned(self) -> None:
        target = flatten(TARGET.read_text(encoding="utf-8"))
        self.assertIn(f"successful install terminal is `{SUCCESS_TERMINAL}`", target)
        self.assertIn(f"`{SUCCESS_SCHEMA}`", self.design)
        self.assertNotIn("PASS_A90_H27_RESIDENT_INSTALLED", self.raw)
        self.assertIn("never infers a candidate generation from the terminal name", self.design)

    def test_h27_and_h28_share_owner_schema_but_not_candidate_payload(self) -> None:
        h27_manifest = canonical_manifest()
        h28_manifest = canonical_manifest(
            candidateSha256="a" * 64,
            expectedVersion="0.11.195",
            expectedBuild="h28-build",
            hazards=[
                {
                    "id": "RKP_CFP_DISABLED_RESIDENT",
                    "qualificationSha256": "b" * 64,
                    "accepted": True,
                },
                {
                    "id": "ANDROID_BINDERFS_ENABLED",
                    "qualificationSha256": "c" * 64,
                    "accepted": True,
                },
            ],
        )
        h27 = canonical_success_payload(h27_manifest)
        h28 = canonical_success_payload(h28_manifest)
        h27_result = validate_success_payload(
            SUCCESS_TERMINAL,
            h27,
            manifest_raw=h27_manifest,
        )
        h28_result = validate_success_payload(
            SUCCESS_TERMINAL,
            h28,
            manifest_raw=h28_manifest,
        )
        self.assertEqual(h27_result["ownerClosureSha256"], h28_result["ownerClosureSha256"])
        self.assertEqual(h27_result["schema"], h28_result["schema"])
        self.assertNotEqual(h27, h28)
        self.assertNotEqual(hashlib.sha256(h27).digest(), hashlib.sha256(h28).digest())

    def test_success_consumer_rejects_candidate_and_manifest_substitution(self) -> None:
        h27_manifest = canonical_manifest()
        h28_manifest = canonical_manifest(
            candidateSha256="a" * 64,
            expectedVersion="0.11.195",
            expectedBuild="h28-build",
        )
        h27 = canonical_success_payload(h27_manifest)
        with self.assertRaisesRegex(ValueError, "candidate-specific"):
            validate_success_payload(
                "PASS_A90_H27_RESIDENT_INSTALLED",
                h27,
                manifest_raw=h27_manifest,
            )
        with self.assertRaisesRegex(ValueError, "cross-manifest"):
            validate_success_payload(
                SUCCESS_TERMINAL,
                h27,
                manifest_raw=h28_manifest,
            )
        substituted_candidate = canonical_success_payload(
            h27_manifest,
            candidateSha256="a" * 64,
        )
        with self.assertRaisesRegex(ValueError, "candidate digest"):
            validate_success_payload(
                SUCCESS_TERMINAL,
                substituted_candidate,
                manifest_raw=h27_manifest,
            )
        mismatched_identity = canonical_success_payload(
            h27_manifest,
            observedBuild="different-build",
        )
        with self.assertRaisesRegex(ValueError, "candidate identity"):
            validate_success_payload(
                SUCCESS_TERMINAL,
                mismatched_identity,
                manifest_raw=h27_manifest,
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
        derived = generated_runtime_closure(FLASH) | {BOOTSTRAP.name}
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
            "hardlinked, group/world-writable, or wrong-owner artifact",
            "pathname `st_dev:st_ino` different from the held FD",
            "helper runs or after it returns",
            "transient different-byte substitution",
            "approval token that does not derive from the complete approval-binding",
            "missing the hazard ID",
            "approval from another A90 with the same resident",
            "approval from an earlier boot ID",
            "approval from another run or journal namespace",
            "changed observation rule or recovery plan",
            "changed owner closure, helper, Python/ADB executable identity",
            "bare or relative Python/ADB executable",
            "fake ADB earlier in `PATH`",
            "direct `python -I native_init_flash.py`",
            "bootstrap source directory added to `sys.path`",
            "same Python/ADB version string with different executable bytes",
            "crash after `CANDIDATE_INTENT`",
            "without\n  candidate replay",
            "post-candidate artifact drift followed by candidate retry",
            "rollback or helper-closure drift followed by rollback launch",
            "crash before `ROLLBACK_INTENT`",
            "crash after `ROLLBACK_INTENT` and before `ROLLBACK_LAUNCHED`",
            "crash after `ROLLBACK_LAUNCHED` and before release",
            "lost helper return after rollback dispatch",
            "crash while publishing `ROLLBACK_RESULT`",
            "duplicate or mismatched rollback intent or result",
            "candidate-specific success terminal name",
            "terminal payload from another manifest",
            "expected and observed candidate version/build mismatch",
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
