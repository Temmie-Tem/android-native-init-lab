#!/usr/bin/env python3
"""Run WSTA167: bounded seccomp gate live observation.

This live runner is intentionally no-load: it stages the WSTA164 launcher
contract plus the WSTA161 gated-apply helper into a Debian chroot, runs the
WSTA166 remote observation script, and verifies all scenarios fail closed
without ``A90WSTA161_SECCOMP_LOAD_ATTEMPT=1``.

The runner is inert unless every explicit live/no-load/cleanup acknowledgement
is supplied.  It never accepts or supplies the correct WSTA161 load token.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402
import run_wsta94_packet_filter_live_gate as wsta94  # noqa: E402
import run_wsta110_service_launcher_chroot_proof as wsta110  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta166_seccomp_live_observation_runner_source as wsta166  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA166_CONTRACT = (
    DEFAULT_RUN_BASE
    / "wsta166-seccomp-live-observation-runner-source-20260705T1344KST"
    / "wsta166_live_runner_contract.json"
)
DEFAULT_WSTA166_REMOTE_SCRIPT = (
    DEFAULT_RUN_BASE
    / "wsta166-seccomp-live-observation-runner-source-20260705T1344KST"
    / "wsta166_remote_seccomp_observation.sh"
)
DEFAULT_WSTA153_POLICY = wsta3.DEFAULT_SECCOMP_POLICY_SOURCE
DEFAULT_WSTA156_MANIFEST = wsta3.DEFAULT_SECCOMP_FILTER_MANIFEST
DEFAULT_WSTA156_OBJECT = wsta3.DEFAULT_SECCOMP_FILTER_OBJECT
DEFAULT_WSTA161_MANIFEST = (
    DEFAULT_RUN_BASE
    / "wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST"
    / "wsta161_seccomp_loader_helper_manifest.json"
)
DEFAULT_WSTA161_HELPER = (
    DEFAULT_RUN_BASE
    / "wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST"
    / "a90-seccomp-loader-gated-apply"
)
PASS_DECISION = "wsta167-seccomp-live-observation-pass"
RESULT_NAME = "wsta167_result.json"
REMOTE_OBSERVATION_SCRIPT = "/tmp/a90-wsta167-seccomp-observation.sh"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def finish_result(out_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def sha256_file(path: Path) -> str:
    return d1.sha256_file(path)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_seccomp_live_observation:
        return False, "wsta167-blocked-seccomp-live-observation-required"
    if not args.allow_seccomp_live_observation:
        return False, "wsta167-blocked-seccomp-live-observation-allow-required"
    if not args.ack_no_correct_wsta161_token:
        return False, "wsta167-blocked-no-correct-token-ack-required"
    if not args.ack_no_seccomp_load:
        return False, "wsta167-blocked-no-seccomp-load-ack-required"
    if not args.ack_cleanup_required:
        return False, "wsta167-blocked-cleanup-ack-required"
    return True, "ok"


def safety(gate_ok: bool) -> dict[str, Any]:
    return {
        "device_action": gate_ok,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "external_ping": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "rootfs_chroot_mutation": "explicit-live-gated-sd-work-image-only" if gate_ok else False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_supplied": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_contract(contract: dict[str, Any], script_text: str) -> dict[str, bool]:
    serialized = json.dumps(contract, sort_keys=True) + script_text
    return {
        "schema_ok": contract.get("schema") == "a90-wsta166-seccomp-live-observation-runner-source-v1",
        "source_only_state": contract.get("state") == "SOURCE_ONLY_REMOTE_SCRIPT_NOT_EXECUTED",
        "scenario_count_three": len(contract.get("scenario_names", [])) == 3,
        "expected_returncode_65": contract.get("expected_scenario_returncode") == 65,
        "correct_token_false": contract.get("correct_wsta161_token_included") is False,
        "load_expected_false": contract.get("seccomp_filter_load_expected") is False,
        "enforcement_expected_false": contract.get("seccomp_enforcement_expected") is False,
        "correct_token_literal_absent": wsta166.CORRECT_WSTA161_TOKEN not in serialized,
        "script_has_remote_done": "A90WSTA166_REMOTE_DONE" in script_text,
        "script_has_wrong_token_placeholder": "intentionally-wrong-token" in script_text,
        "script_no_external_network_inputs": (
            "cloudflared" not in script_text
            and "tunnel" not in script_text
            and "wifi" not in script_text.lower()
            and "dhcp" not in script_text.lower()
        ),
        "secret_values_logged_zero": contract.get("secret_values_logged") == 0,
    }


def stage_seccomp_observation_assets(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    policy_path = resolve_path(args.wsta153_seccomp_policy_json)
    policy = load_json(policy_path)
    records = {
        "launcher": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SERVICE_LAUNCHER),
            wsta3.launcher_script().encode("utf-8"),
            mode="0755",
            timeout=args.ssh_timeout,
        ),
        "policy": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_POLICY),
            (json.dumps(policy, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "map": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_LAUNCHER_MAP),
            wsta3.seccomp_launcher_map_text(policy).encode("utf-8"),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "filter_manifest": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_FILTER_MANIFEST),
            resolve_path(args.wsta156_filter_manifest_json).read_bytes(),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "filter_object": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_FILTER_OBJECT),
            resolve_path(args.wsta156_filter_object).read_bytes(),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "loader_manifest": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_LOADER_HELPER_MANIFEST),
            resolve_path(args.wsta161_loader_helper_manifest_json).read_bytes(),
            mode="0644",
            timeout=args.ssh_timeout,
        ),
        "loader_helper": wsta110.write_remote_bytes(
            args,
            run_dir,
            "/" + str(wsta3.TARGET_SECCOMP_LOADER_HELPER),
            resolve_path(args.wsta161_loader_helper).read_bytes(),
            mode="0755",
            timeout=args.ssh_timeout,
        ),
        "remote_observation_script": wsta110.write_remote_bytes(
            args,
            run_dir,
            REMOTE_OBSERVATION_SCRIPT,
            resolve_path(args.wsta166_remote_script).read_bytes(),
            mode="0755",
            timeout=args.ssh_timeout,
        ),
    }
    records["staged"] = all(bool(item.get("staged")) for item in records.values() if isinstance(item, dict))
    records["secret_values_logged"] = 0
    return records


def parse_observation(stdout: str, contract: dict[str, Any]) -> dict[str, bool]:
    scenario_names = [str(item) for item in contract.get("scenario_names", [])]
    expected_rc = str(contract.get("expected_scenario_returncode", 65))
    return {
        "remote_begin": "A90WSTA166_REMOTE_BEGIN" in stdout,
        "remote_done": "A90WSTA166_REMOTE_DONE" in stdout,
        "all_scenario_begin": all(f"A90WSTA166_SCENARIO_BEGIN name={name}" in stdout for name in scenario_names),
        "all_scenario_end": all(f"A90WSTA166_SCENARIO_END name={name}" in stdout for name in scenario_names),
        "all_scenario_rc_65": all(
            f"A90WSTA166_SCENARIO_RC name={name} rc={expected_rc}" in stdout for name in scenario_names
        ),
        "load_attempt_absent": "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1" not in stdout,
        "exec_absent": "a90_service_launcher_decision=exec" not in stdout and "fake_setpriv_args=" not in stdout,
        "loaded_absent": "a90_seccomp_loader_decision=loaded" not in stdout,
        "no_gate_block": "a90_seccomp_loader_decision=blocked-load-gate-required" in stdout,
        "missing_token_block": "a90_service_launcher_decision=blocked-seccomp-helper-load-token-required" in stdout,
        "wrong_token_block": "a90_seccomp_loader_decision=blocked-load-token-required" in stdout,
        "secret_values_logged": True,
    }


def run_remote_observation(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = wsta42.ssh_exec(args, run_dir, REMOTE_OBSERVATION_SCRIPT, timeout=args.observation_timeout)
    return record


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta167-blocked-explicit-live-gate"),
        ("contract_valid", "wsta167-blocked-contract-invalid"),
        ("local_inputs_present", "wsta167-blocked-local-inputs-missing"),
        ("baseline_selftest_fail_zero", "wsta167-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta167-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta167-blocked-remote-image"),
        ("chroot_mount_ready", "wsta167-blocked-chroot-mount"),
        ("dropbear_started", "wsta167-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta167-blocked-debian-ssh"),
        ("seccomp_assets_staged", "wsta167-blocked-seccomp-assets-stage"),
        ("observation_pass", "wsta167-blocked-observation"),
        ("chroot_cleanup_ok", "wsta167-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta167-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def local_inputs_present(args: argparse.Namespace) -> bool:
    paths = (
        args.local_image,
        args.wsta166_contract_json,
        args.wsta166_remote_script,
        args.wsta153_seccomp_policy_json,
        args.wsta156_filter_manifest_json,
        args.wsta156_filter_object,
        args.wsta161_loader_helper_manifest_json,
        args.wsta161_loader_helper,
    )
    return all(resolve_path(path).is_file() for path in paths)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta167-seccomp-live-observation-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    contract_path = resolve_path(args.wsta166_contract_json)
    script_path = resolve_path(args.wsta166_remote_script)
    contract = load_json(contract_path) if contract_path.is_file() else {}
    script_text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    contract_checks = validate_contract(contract, script_text) if contract and script_text else {}
    result: dict[str, Any] = {
        "scope": "WSTA167 bounded seccomp live observation",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "remote_image": args.remote_image,
        "remote_clean_image": args.remote_clean_image if wsta42.remote_clean_image_enabled(args) else None,
        "mountpoint": args.mountpoint,
        "contract": rel(contract_path),
        "remote_script": rel(script_path),
        "safety": safety(gate_ok),
        "contract_checks": contract_checks,
        "checks": {
            "explicit_live_gate": gate_ok,
            "contract_valid": bool(contract_checks) and all(contract_checks.values()),
            "local_inputs_present": local_inputs_present(args),
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = gate_decision
        return finish_result(out_path, result)
    if not result["checks"]["contract_valid"] or not result["checks"]["local_inputs_present"]:
        result["decision"] = classify(result)
        return finish_result(out_path, result)

    local_image = args.local_image
    local_sha = sha256_file(local_image)
    result["local_image"] = rel(local_image)
    result["local_image_sha256"] = local_sha
    if args.local_image_sha256 and args.local_image_sha256 != local_sha:
        result["local_image_expected_sha256"] = args.local_image_sha256
        result["checks"]["remote_image_ready"] = False
        result["decision"] = "wsta167-blocked-local-image-sha"
        return finish_result(out_path, result)

    mounted = False
    try:
        result["bridge_status"] = wsta2_run_host_bridge_status()
        result["version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["status"] = wsta19.try_cmdv1_retry(args, ["status"], timeout=args.timeout)
        result["baseline_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["baseline_selftest_fail_zero"] = wsta2_selftest_passed(result["baseline_selftest"])
        result["native_stale_cleanup"] = wsta94.native_stale_cleanup(args)
        result["checks"]["native_stale_cleanup_ok"] = bool(result["native_stale_cleanup"].get("cleaned"))
        write_json(out_path, result)
        if not result["checks"]["native_stale_cleanup_ok"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        image_ready = wsta42.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)
        result["checks"]["remote_image_ready"] = bool(image_ready)
        write_json(out_path, result)
        if not image_ready:
            result["decision"] = result.get("decision") or classify(result)
            return finish_result(out_path, result)

        result["keygen"] = d2.generate_ssh_key(run_dir, run_id)
        public_key = d2.read_public_key(run_dir)
        write_json(out_path, result)

        result["mount"] = wsta19.bridge_shell(
            args,
            wsta94.wsta94_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        mounted = True
        result["mount_parse"] = d2.parse_setup(str(result["mount"].get("text") or ""))
        result["checks"]["chroot_mount_ready"] = bool(
            result["mount_parse"].get("mount_ready") and result["mount_parse"].get("mounted")
        )
        write_json(out_path, result)
        if not result["checks"]["chroot_mount_ready"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["dropbear_start"] = wsta19.bridge_shell(
            args,
            wsta94.wsta94_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
            allow_error=True,
        )
        result["dropbear_parse"] = d2.parse_setup(str(result["dropbear_start"].get("text") or ""))
        result["checks"]["dropbear_started"] = bool(
            result["dropbear_parse"].get("started")
            and result["dropbear_parse"].get("authorized_keys")
            and result["dropbear_parse"].get("shadow_temp_key_only")
        )
        write_json(out_path, result)
        if not result["checks"]["dropbear_started"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["ssh"] = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh_parse"] = result["ssh"].get("marker", {})
        result["checks"]["debian_ssh_marker"] = bool(result["ssh_parse"].get("marker"))
        write_json(out_path, result)
        if not result["checks"]["debian_ssh_marker"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["seccomp_assets_stage"] = stage_seccomp_observation_assets(args, run_dir)
        result["checks"]["seccomp_assets_staged"] = bool(result["seccomp_assets_stage"].get("staged"))
        write_json(out_path, result)
        if not result["checks"]["seccomp_assets_staged"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["observation"] = run_remote_observation(args, run_dir)
        result["observation_parse"] = parse_observation(str(result["observation"].get("stdout") or ""), contract)
        result["checks"]["observation_pass"] = bool(
            result["observation"].get("returncode") == 0
            and all(result["observation_parse"].values())
        )
        write_json(out_path, result)
    finally:
        if mounted:
            result["cleanup"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["cleanup_parse"] = d2.parse_cleanup(str(result["cleanup"].get("text") or ""))
            result["postcheck"] = wsta19.bridge_shell(
                args,
                wsta94.wsta94_postcheck_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["postcheck_parse"] = d2.parse_postcheck(str(result["postcheck"].get("text") or ""))
        else:
            result["cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup_parse"] = {}
            result["postcheck"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["postcheck_parse"] = {}

        result["final_version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["final_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["chroot_cleanup_ok"] = bool(not mounted or wsta94.chroot_cleanup_ok(result))
        result["checks"]["final_selftest_fail_zero"] = wsta2_selftest_passed(result["final_selftest"])
        write_json(out_path, result)

    result["decision"] = classify(result)
    return finish_result(out_path, result)


def wsta2_run_host_bridge_status() -> dict[str, Any]:
    return wsta2.run_host([sys.executable, str(wsta2.BRIDGE), "status", "--json"], timeout=10.0)


def wsta2_selftest_passed(record: dict[str, Any]) -> bool:
    return wsta2.selftest_passed(record.get("text", ""))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=180.0)
    parser.add_argument("--cleanup-timeout", type=float, default=120.0)
    parser.add_argument("--ssh-timeout", type=float, default=45.0)
    parser.add_argument("--observation-timeout", type=float, default=45.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default=d1.EXPECTED_IMAGE_SHA256)
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--wsta166-contract-json", type=Path, default=DEFAULT_WSTA166_CONTRACT)
    parser.add_argument("--wsta166-remote-script", type=Path, default=DEFAULT_WSTA166_REMOTE_SCRIPT)
    parser.add_argument("--wsta153-seccomp-policy-json", type=Path, default=DEFAULT_WSTA153_POLICY)
    parser.add_argument("--wsta156-filter-manifest-json", type=Path, default=DEFAULT_WSTA156_MANIFEST)
    parser.add_argument("--wsta156-filter-object", type=Path, default=DEFAULT_WSTA156_OBJECT)
    parser.add_argument("--wsta161-loader-helper-manifest-json", type=Path, default=DEFAULT_WSTA161_MANIFEST)
    parser.add_argument("--wsta161-loader-helper", type=Path, default=DEFAULT_WSTA161_HELPER)
    parser.add_argument("--execute-seccomp-live-observation", action="store_true")
    parser.add_argument("--allow-seccomp-live-observation", action="store_true")
    parser.add_argument("--ack-no-correct-wsta161-token", action="store_true")
    parser.add_argument("--ack-no-seccomp-load", action="store_true")
    parser.add_argument("--ack-cleanup-required", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = utc_stamp()
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta167-seccomp-live-observation-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {"scope": "WSTA167 bounded seccomp live observation", "run_dir": rel(run_dir)}
        else:
            result = {"scope": "WSTA167 bounded seccomp live observation", "run_dir": rel(run_dir)}
        result["decision"] = "wsta167-runner-error"
        result["error"] = str(exc)
        finish_result(out_path, result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
