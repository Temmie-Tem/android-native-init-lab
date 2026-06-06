#!/usr/bin/env python3
"""V464 execns helper v31 deploy/preflight wrapper.

Deploy is limited to `/cache/bin/a90_android_execns_probe` and requires the
exact V464 deploy approval phrase. It does not start service-manager,
hwservicemanager, Wi-Fi HAL, CNSS, scan/connect, or Wi-Fi bring-up.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v464-execns-helper-v31-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v464-a90_android_execns_probe-v31/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "96179d75ee81586cf8f46edb7354eeb8c57569e56a047a2c55e678c794a514e9"
deploy.HELPER_MARKER = "a90_android_execns_probe v31"
deploy.SERVICE_MODE_TOKEN = "wifi-surface-composite-start-only"
deploy.DEPLOY_LABEL = "v31"
deploy.DEPLOY_NAME = "execns-helper-v31"
deploy.DEPLOY_PLAN_VERSION = "V464"
deploy.DEPLOY_LOG_PREFIX = "v464"
deploy.SUMMARY_TITLE = "v464 Execns Helper v31 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v464 deploy execns helper v31 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/native_wifi_surface_composite_v464.py")

SURFACE_TOKENS = (
    "wifi-surface-composite-start-only",
    "wifi_surface_composite.before",
    "wifi_surface_composite.during",
    "wifi_surface_composite.after_cleanup",
    "--allow-cnss-start-only",
)

_BASE_LOCAL_HELPER_INFO = deploy.local_helper_info
_BASE_BUILD_CHECKS = deploy.build_checks


def local_helper_info(args: deploy.argparse.Namespace) -> dict[str, object]:
    info = _BASE_LOCAL_HELPER_INFO(args)
    info["strings_surface_tokens"] = False
    if not info.get("exists"):
        return info
    rc, strings_output = deploy.run_host(["strings", str(deploy.repo_path(args.local_helper))], timeout=10)
    if rc == 0:
        info["strings_surface_tokens"] = all(token in strings_output for token in SURFACE_TOKENS)
    return info


def build_checks(args: deploy.argparse.Namespace, store: deploy.EvidenceStore,
                 steps: list[deploy.StepResult], local: dict[str, object],
                 ping: dict[str, object] | None) -> list[deploy.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, local, ping)
    local_surface_ok = bool(local.get("strings_surface_tokens"))
    deploy.add_check(
        checks,
        "local-helper-v31-surface-guards",
        "pass" if local_surface_ok else "blocked",
        "blocker",
        f"surface_tokens={local_surface_ok}",
        [str(local.get("path", ""))],
        "rebuild helper v31 with surface-composite mode before deploy",
    )
    if args.command == "plan":
        return checks
    helper_usage = deploy.capture_text(store, steps, "helper-usage")
    helper_sha = deploy.capture_text(store, steps, "sha-helper")
    remote_surface_ok = (
        args.helper_sha256 in helper_sha
        and deploy.HELPER_MARKER in helper_usage
        and deploy.SERVICE_MODE_TOKEN in helper_usage
        and "--allow-cnss-start-only" in helper_usage
    )
    deploy.add_check(
        checks,
        "remote-helper-v31-surface-guards",
        "pass" if remote_surface_ok else "needs-deploy",
        "deploy",
        f"surface_guard={remote_surface_ok}",
        [line for line in helper_usage.splitlines() if deploy.SERVICE_MODE_TOKEN in line or "--allow-cnss-start-only" in line][:4],
        "approved V464 deploy installs helper v31 with surface-composite support if needed",
    )
    return checks


def run_v464_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v464-surface-composite-preflight")
    command = [
        sys.executable,
        str(deploy.repo_path(deploy.V373_SCRIPT)),
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.remote_helper,
        "--helper-sha256",
        args.helper_sha256,
        "preflight",
    ]
    rc, output = deploy.run_host(command, timeout=180)
    store.write_text("host/v464-surface-composite-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v464-surface-composite-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v464_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v31-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return "execns-helper-v31-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(check.name == "remote-helper-v31" and check.status != "pass" for check in checks)
    if args.command == "preflight":
        if deploy_needed:
            return "execns-helper-v31-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v31 deploy still requires exact approval", "operator may approve V464 deploy"
        return "execns-helper-v31-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V464 deploy"
    if not deploy.approved(args):
        return "execns-helper-v31-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v31-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v464_result and v464_result["decision"] not in {
        "v464-native-wlan-surface-preflight-ready",
        "v464-native-wlan-surface-blocked",
    }:
        return "execns-helper-v31-deploy-postflight-review", False, f"V464 preflight decision={v464_result['decision']}", "inspect V464 preflight output"
    return "execns-helper-v31-deploy-pass", True, "helper v31 deployed or already current; V464 preflight was rerun", "next requires separate V464 live surface-composite approval"


deploy.run_v373_preflight = run_v464_preflight
deploy.decide = decide
deploy.local_helper_info = local_helper_info
deploy.build_checks = build_checks


if __name__ == "__main__":
    raise SystemExit(deploy.main())
