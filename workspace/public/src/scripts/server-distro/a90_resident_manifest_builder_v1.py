#!/usr/bin/env python3
"""Build one validated A90 resident-promotion manifest without device access.

The builder reuses an exact resident manifest only as a structural template.
Every run-dependent path, hash, size, and execution-source binding is reopened
from the selected private run.  It validates a temporary manifest through the
production resident loader and local closure before publishing one absent-only
final file.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_resident_fast_handoff_v1 as qualification  # noqa: E402
import a90_resident_promotion_v1 as promotion  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


SCHEMA = "a90_resident_manifest_builder_v1"
PASS_DECISION = "A90_RESIDENT_MANIFEST_VALIDATED_HOST_PASS"
RUN_ID_RE = re.compile(
    r"^a90-v3406-debian-display-f1-[0-9]{8}-[0-9]{2}$"
)
OUTPUT_NAME_RE = re.compile(r"^resident-prepared-manifest(?:-[a-z0-9-]+)?\.json$")
KEYED_SUMMARY_NAME = "keyed-rootfs-summary.json"
CANDIDATE_NAME = "candidate-boot-phase2-display-v1.img"
ROLLBACK_NAME = "rollback-boot-v2321.img"
HOST_PREPARATION_NAME = "host-preparation.json"
CANDIDATE_SIZE = 66379776
CANDIDATE_SHA256 = (
    "3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb"
)
CANDIDATE_VERSION = "0.11.161"
CANDIDATE_BUILD = "phase2-display-v1-native-handoff"
ROLLBACK_SIZE = 60882944
ROLLBACK_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_BUILD = "v2321-usb-clean-identity-rodata"


class ContractError(RuntimeError):
    """Raised when resident manifest preparation is not exact."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or staging.HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not an exact sha256")
    return value


def validate_canonical_boot_template(
    candidate: dict[str, Any],
    rollback: dict[str, Any],
) -> None:
    for label, value, name, size, digest, version, build in (
        (
            "candidate",
            candidate,
            CANDIDATE_NAME,
            CANDIDATE_SIZE,
            CANDIDATE_SHA256,
            CANDIDATE_VERSION,
            CANDIDATE_BUILD,
        ),
        (
            "rollback",
            rollback,
            ROLLBACK_NAME,
            ROLLBACK_SIZE,
            ROLLBACK_SHA256,
            ROLLBACK_VERSION,
            ROLLBACK_BUILD,
        ),
    ):
        path = value.get("path")
        if (
            not isinstance(path, str)
            or Path(path).name != name
            or value.get("partition") != "boot"
            or value.get("size") != size
            or value.get("sha256") != digest
            or value.get("expected_version") != version
            or value.get("expected_build") != build
        ):
            raise ContractError(f"template {label} boot binding is not canonical")


def regular_record(
    path: Path,
    *,
    private: bool,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    if path.is_symlink():
        raise ContractError(f"input must not be a symbolic link: {path}")
    resolved = path.resolve(strict=True)
    info = resolved.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
        raise ContractError(f"input is not an exact regular file: {resolved}")
    if private:
        staging.require_below(resolved, staging.PRIVATE_ROOT, "private input")
        if info.st_mode & 0o077:
            raise ContractError(f"private input permissions are excessive: {resolved}")
    actual_sha256 = sha256_file(resolved)
    if expected_size is not None and info.st_size != expected_size:
        raise ContractError(f"input size mismatch: {resolved}")
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ContractError(f"input sha256 mismatch: {resolved}")
    return {
        "path": str(resolved),
        "size": info.st_size,
        "sha256": actual_sha256,
    }


def load_exact_json(
    path: Path,
    *,
    expected_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = regular_record(
        path,
        private=True,
        expected_sha256=validate_sha256(expected_sha256, "JSON sha256"),
    )
    try:
        value = json.loads(Path(record["path"]).read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"input is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON input is not an object: {path}")
    return value, record


def current_record(path: Path) -> dict[str, Any]:
    return regular_record(path.resolve(), private=False)


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def update_execution_sources(manifest: dict[str, Any]) -> None:
    orchestrator = require_dict(manifest.get("f1_orchestrator"), "f1_orchestrator")
    orchestrator.update(current_record(Path(base.__file__).resolve()))

    rootfs_staging = require_dict(manifest.get("rootfs_staging"), "rootfs_staging")
    rootfs = require_dict(manifest.get("debian_rootfs"), "debian_rootfs")
    keyed_source = require_dict(
        rootfs.get("keyed_source"),
        "debian_rootfs.keyed_source",
    )
    rootfs_profile = keyed_source.get("profile", staging.PHASE2_PROFILE)
    adapter = require_dict(rootfs_staging.get("adapter"), "rootfs_staging.adapter")
    adapter.update(current_record(Path(staging.__file__).resolve()))
    transport = require_dict(
        rootfs_staging.get("transport"),
        "rootfs_staging.transport",
    )
    transport.update(current_record(REVAL_DIR / "tcpctl_host.py"))
    rootfs_staging["support_files"] = [
        current_record(path.resolve())
        for path in staging.required_support_files(rootfs_profile)
    ]

    resident = require_dict(manifest.get("resident_promotion"), "resident_promotion")
    runner = require_dict(resident.get("runner"), "resident_promotion.runner")
    runner.update(current_record(Path(promotion.__file__).resolve()))
    helper = require_dict(
        resident.get("qualification_helper"),
        "resident_promotion.qualification_helper",
    )
    helper.update(current_record(Path(qualification.__file__).resolve()))

    flash_runner = current_record(REVAL_DIR / "native_init_flash.py")
    manifest_transport = require_dict(manifest.get("transport"), "transport")
    manifest_transport.update(
        {
            "candidate_and_rollback_runner": flash_runner["path"],
            "runner_size": flash_runner["size"],
            "runner_sha256": flash_runner["sha256"],
        }
    )


def prepare_manifest(
    *,
    template: dict[str, Any],
    run_id: str,
    run_dir: Path,
    evidence_sequence: str,
    summary: dict[str, Any],
    summary_record: dict[str, Any],
    candidate_record: dict[str, Any],
    rollback_record: dict[str, Any],
    connected_value: dict[str, Any],
    connected_record: dict[str, Any],
    paths_value: dict[str, Any],
    paths_record: dict[str, Any],
    host_preparation_record: dict[str, Any],
    repository_commit: str,
    resident_install_v2: bool = False,
) -> dict[str, Any]:
    if template.get("schema") != staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA:
        raise ContractError("template is not a resident-promotion manifest")
    if template.get("status") != staging.FINAL_MANIFEST_STATUS:
        raise ContractError("template status is not final")
    template_run_id = template.get("run_id")
    if not isinstance(template_run_id, str) or RUN_ID_RE.fullmatch(template_run_id) is None:
        raise ContractError("template run_id is not exact")

    keyed = require_dict(summary.get("keyed_image"), "keyed summary image")
    observer = require_dict(summary.get("observer"), "keyed summary observer")
    source = require_dict(summary.get("source"), "keyed summary source")
    phase3 = (
        summary.get("schema")
        == "a90-phase3-network-ssh-keyed-rootfs-v1"
    )
    expected_decision = (
        "A90_PHASE3_NETWORK_SSH_KEYED_ROOTFS_HOST_PASS"
        if phase3
        else "A90_PHASE2D_KEYED_ROOTFS_HOST_PASS"
    )
    expected_image = run_dir / (
        "phase3-network-ssh-v1-keyed.img"
        if phase3
        else "phase2-display-v1-keyed.img"
    )
    if (
        summary.get("run_id") != run_id
        or summary.get("decision") != expected_decision
        or keyed.get("path") != str(expected_image)
    ):
        raise ContractError("keyed summary does not select the exact run")

    manifest = copy.deepcopy(template)
    if resident_install_v2:
        resident = require_dict(
            manifest.get("resident_promotion"),
            "resident_promotion",
        )
        if resident.get("mode") != promotion.MODE:
            raise ContractError("template resident mode is not legacy promotion v1")
        manifest["schema"] = staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        resident["mode"] = promotion.INSTALL_MODE
        resident.pop("resident_reboot_command", None)
        resident.pop("resident_reboot_timeout_sec", None)
        resident["candidate_health_checks"] = 1
        resident["success_terminal"] = promotion.INSTALL_STATUS
    manifest["run_id"] = run_id
    manifest["candidate_boot"].update(candidate_record)
    manifest["rollback_boot"].update(rollback_record)

    target = require_dict(manifest.get("target"), "target")
    connected_target = require_dict(connected_value.get("target"), "connected D0 target")
    target.update(
        {
            "bridge_device": connected_target.get("bridge_device"),
            "bridge_selected_realpath": connected_target.get("bridge_selected_realpath"),
            "bridge_selected_exact": True,
            "current_version": require_dict(
                connected_value.get("health"),
                "connected D0 health",
            ).get("version"),
            "current_build": require_dict(
                connected_value.get("health"),
                "connected D0 health",
            ).get("version_build"),
            "connected_d0_result": {
                **connected_record,
                "outcome": staging.D0_RESULT_OUTCOME,
            },
            "connected_path_preflight": {
                **paths_record,
                "keyed_source_path_absent": True,
                "handoff_work_path_absent": True,
                "run_stage_path_absent": True,
            },
        }
    )

    remote_final = str(staging.derive_remote_final(run_id))
    rootfs = require_dict(manifest.get("debian_rootfs"), "debian_rootfs")
    keyed_source = require_dict(rootfs.get("keyed_source"), "debian_rootfs.keyed_source")
    rootfs["kind"] = (
        "bookworm-arm64-phase3-network-ssh-v1-per-run-keyed"
        if phase3
        else "bookworm-arm64-phase2-display-v1-per-run-keyed"
    )
    keyed_source.update(
        {
            "local_path": keyed["path"],
            "size": keyed["size"],
            "sha256": keyed["sha256"],
            "profile": (
                staging.PHASE3_PROFILE if phase3 else staging.PHASE2_PROFILE
            ),
            "device_path": remote_final,
            "filesystem_label": (
                staging.PHASE3_FILESYSTEM_LABEL
                if phase3
                else staging.PHASE2_FILESYSTEM_LABEL
            ),
            "materialization": summary_record,
        }
    )
    rootfs["pristine_provenance"] = {
        "path": source.get("path"),
        "size": source.get("size"),
        "sha256": source.get("sha256"),
        "receipt_path": source.get("receipt_path"),
        "receipt_sha256": source.get("receipt_sha256"),
    }
    rootfs["handoff_command"] = [
        base.HANDOFF_COMMAND,
        base.HANDOFF_TOKEN,
        remote_final,
        keyed["sha256"],
    ]
    rootfs_observer = require_dict(rootfs.get("observer"), "debian_rootfs.observer")
    rootfs_observer.update(
        {
            "private_key_path": observer["private_key_path"],
            "public_key_sha256": observer["public_key_sha256"],
        }
    )

    manifest["host_preparation"] = host_preparation_record
    rootfs_staging = require_dict(
        manifest.get("rootfs_staging"),
        "rootfs_staging",
    )
    if phase3:
        rootfs_staging["review_verdict"] = "PASS_GO"
        approval_scope = manifest.get("approval_scope_template")
        if isinstance(approval_scope, dict):
            approval_scope.pop("bind_phase2_materialization_receipt", None)
            approval_scope["bind_phase3_materialization_receipt"] = True
    approval = require_dict(manifest.get("approval_preparation"), "approval_preparation")
    approval["path"] = str(run_dir / "approval-prepared.json")

    update_execution_sources(manifest)
    transport = require_dict(manifest.get("transport"), "transport")
    transport.update(
        {
            "repository_commit": repository_commit,
            "candidate_expected_arguments": [
                "--from-native",
                "--image",
                candidate_record["path"],
                "--expect-sha256",
                candidate_record["sha256"],
            ],
            "rollback_expected_arguments": [
                "--from-native|adb-recovery",
                "--image",
                rollback_record["path"],
                "--expect-sha256",
                rollback_record["sha256"],
            ],
        }
    )

    if connected_value.get("run_id") != f"{run_id}-connected-d0-{evidence_sequence}":
        raise ContractError("connected D0 run_id does not match the selected sequence")
    if paths_value.get("run_id") != run_id:
        raise ContractError("path preflight run_id does not match the selected run")

    serialized = json.dumps(manifest, sort_keys=True)
    template_remote = require_dict(
        require_dict(template.get("debian_rootfs"), "template debian_rootfs").get(
            "keyed_source"
        ),
        "template keyed_source",
    ).get("device_path")
    for stale in (template_run_id, template_remote):
        if isinstance(stale, str) and stale in serialized:
            raise ContractError(f"template run-specific value survived rebinding: {stale}")
    return manifest


def validate_local_paths(manifest: dict[str, Any], run_dir: Path) -> None:
    approval_path = str(run_dir / "approval-prepared.json")
    seen: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and value.startswith(str(REPO_ROOT)):
            seen.append(value)

    walk(manifest)
    if approval_path not in seen:
        raise ContractError("approval receipt path is not bound")
    if Path(approval_path).exists() or Path(approval_path).is_symlink():
        raise ContractError("approval receipt must remain absent before preparation")
    for value in sorted(set(seen) - {approval_path}):
        path = Path(value)
        if path.is_symlink() or not path.is_file():
            raise ContractError(f"manifest local path is absent or not regular: {path}")


def write_validate_publish(
    manifest: dict[str, Any],
    *,
    run_dir: Path,
    output_name: str,
) -> tuple[Path, str, dict[str, Any]]:
    if OUTPUT_NAME_RE.fullmatch(output_name) is None:
        raise ContractError("output name is not an exact resident manifest name")
    output = run_dir / output_name
    if output.exists() or output.is_symlink():
        raise ContractError("final manifest output must be absent")
    validate_local_paths(manifest, run_dir)

    fd, temporary_name = tempfile.mkstemp(
        dir=run_dir,
        prefix=".resident-manifest-",
        suffix=".json",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        manifest_sha256 = sha256_file(temporary)
        spec, promotion_value, issues = promotion.load_spec(
            temporary,
            manifest_sha256,
            allow_draft=False,
        )
        base.verify_local_closure(spec)
        if issues or not promotion_value:
            raise ContractError(f"resident manifest retained issues: {issues}")
        os.link(temporary, output, follow_symlinks=False)
        directory_fd = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if sha256_file(output) != manifest_sha256:
            raise ContractError("published manifest hash changed")
        return output, manifest_sha256, promotion_value
    finally:
        temporary.unlink(missing_ok=True)


def build(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(args.run_id) is None:
        raise ContractError("run_id is not the exact V3406 resident form")
    if re.fullmatch(r"[0-9]{2}", args.evidence_sequence) is None:
        raise ContractError("evidence sequence must be exactly two digits")
    run_dir = (staging.PRIVATE_RUN_BASE / args.run_id).resolve(strict=True)
    staging.require_below(run_dir, staging.PRIVATE_RUN_BASE, "run directory")

    template, _ = load_exact_json(
        args.template_manifest,
        expected_sha256=args.expect_template_sha256,
    )
    summary, summary_record = load_exact_json(
        run_dir / KEYED_SUMMARY_NAME,
        expected_sha256=args.expect_keyed_summary_sha256,
    )
    connected_path = run_dir / f"connected-d0-{args.evidence_sequence}.json"
    connected_value, connected_record = load_exact_json(
        connected_path,
        expected_sha256=args.expect_connected_d0_sha256,
    )
    paths_path = run_dir / f"connected-path-preflight-{args.evidence_sequence}.json"
    paths_value, paths_record = load_exact_json(
        paths_path,
        expected_sha256=args.expect_path_preflight_sha256,
    )

    template_candidate = require_dict(template.get("candidate_boot"), "candidate_boot")
    template_rollback = require_dict(template.get("rollback_boot"), "rollback_boot")
    validate_canonical_boot_template(template_candidate, template_rollback)
    candidate_record = regular_record(
        run_dir / CANDIDATE_NAME,
        private=True,
        expected_size=CANDIDATE_SIZE,
        expected_sha256=CANDIDATE_SHA256,
    )
    rollback_record = regular_record(
        run_dir / ROLLBACK_NAME,
        private=True,
        expected_size=ROLLBACK_SIZE,
        expected_sha256=ROLLBACK_SHA256,
    )
    host_preparation_record = regular_record(
        run_dir / HOST_PREPARATION_NAME,
        private=True,
        expected_sha256=args.expect_host_preparation_sha256,
    )
    repository_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30.0,
        check=True,
    ).stdout.strip()

    manifest = prepare_manifest(
        template=template,
        run_id=args.run_id,
        run_dir=run_dir,
        evidence_sequence=args.evidence_sequence,
        summary=summary,
        summary_record=summary_record,
        candidate_record=candidate_record,
        rollback_record=rollback_record,
        connected_value=connected_value,
        connected_record=connected_record,
        paths_value=paths_value,
        paths_record=paths_record,
        host_preparation_record=host_preparation_record,
        repository_commit=repository_commit,
        resident_install_v2=args.resident_install_v2,
    )
    output, manifest_sha256, promotion_value = write_validate_publish(
        manifest,
        run_dir=run_dir,
        output_name=args.output_name,
    )
    return {
        "schema": SCHEMA,
        "decision": PASS_DECISION,
        "run_id": args.run_id,
        "manifest": {
            "path": str(output),
            "size": output.stat().st_size,
            "sha256": manifest_sha256,
        },
        "promotion_mode": promotion_value.get("mode"),
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
        "flash": False,
        "reboot": False,
        "f1_authorized": False,
        "live_authority": False,
        "fresh_exact_f1_approval_required": True,
    }


def audit_payload() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": "host-only-audit",
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "contract": {
            "temporary_production_loader_validation": True,
            "absent_only_final_publication": True,
            "manual_string_replacement": False,
            "device_actions": False,
        },
        "device_contact": False,
        "device_write": False,
        "f1_authorized": False,
        "live_authority": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--build", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--evidence-sequence", default="01")
    parser.add_argument("--template-manifest", type=Path)
    parser.add_argument("--expect-template-sha256")
    parser.add_argument("--expect-keyed-summary-sha256")
    parser.add_argument("--expect-connected-d0-sha256")
    parser.add_argument("--expect-path-preflight-sha256")
    parser.add_argument("--expect-host-preparation-sha256")
    parser.add_argument("--output-name", default="resident-prepared-manifest.json")
    parser.add_argument("--resident-install-v2", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.audit_only:
        if args.resident_install_v2:
            raise ContractError("audit mode accepts no build profile")
        connected = (
            "run_id",
            "template_manifest",
            "expect_template_sha256",
            "expect_keyed_summary_sha256",
            "expect_connected_d0_sha256",
            "expect_path_preflight_sha256",
            "expect_host_preparation_sha256",
        )
        if any(getattr(args, name) is not None for name in connected):
            raise ContractError("audit mode accepts no build inputs")
        result = audit_payload()
    else:
        required = (
            "run_id",
            "template_manifest",
            "expect_template_sha256",
            "expect_keyed_summary_sha256",
            "expect_connected_d0_sha256",
            "expect_path_preflight_sha256",
            "expect_host_preparation_sha256",
        )
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise ContractError(f"builder inputs are missing: {missing}")
        result = build(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(
            f"a90-resident-manifest-builder-v1: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
