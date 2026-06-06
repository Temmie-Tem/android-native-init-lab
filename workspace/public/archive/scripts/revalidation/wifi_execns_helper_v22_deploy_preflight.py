#!/usr/bin/env python3
"""V402 execns helper v22 deploy/preflight wrapper.

Deploy is limited to /cache/bin/a90_android_execns_probe and requires the exact
V402 deploy approval phrase. It does not start service-manager and it does not
bring up Wi-Fi.
"""

from __future__ import annotations

import sys

import wifi_execns_helper_v12_deploy_preflight as deploy


deploy.__doc__ = __doc__
deploy.DEFAULT_OUT_DIR = deploy.Path("tmp/wifi/v402-execns-helper-v22-deploy-preflight")
deploy.DEFAULT_LOCAL_HELPER = deploy.Path("tmp/wifi/v402-a90_android_execns_probe-v22/a90_android_execns_probe")
deploy.DEFAULT_HELPER_SHA256 = "55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6"
deploy.HELPER_MARKER = "a90_android_execns_probe v22"
deploy.SERVICE_MODE_TOKEN = "private-selinux-proof"
deploy.DEPLOY_LABEL = "v22"
deploy.DEPLOY_NAME = "execns-helper-v22"
deploy.DEPLOY_PLAN_VERSION = "V402"
deploy.DEPLOY_LOG_PREFIX = "v402"
deploy.SUMMARY_TITLE = "v402 Execns Helper v22 Deploy Preflight"
deploy.APPROVAL_PHRASE = (
    "approve v402 deploy execns helper v22 only; "
    "no daemon start and no Wi-Fi bring-up"
)
deploy.V373_SCRIPT = deploy.Path("scripts/revalidation/wifi_private_selinux_surface_v402_live_runner.py")


def run_v402_preflight(args: deploy.argparse.Namespace, store: deploy.EvidenceStore) -> dict[str, object]:
    out_dir = store.path("v402-private-selinux-preflight")
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
    store.write_text("host/v402-private-selinux-preflight.txt", output)
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        manifest = deploy.json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "command": " ".join(command),
        "rc": rc,
        "ok": rc == 0,
        "file": "host/v402-private-selinux-preflight.txt",
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
    }


def decide(args: deploy.argparse.Namespace,
           checks: list[deploy.Check],
           deploy_result: dict[str, object] | None,
           v402_result: dict[str, object] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "execns-helper-v22-deploy-plan-ready", True, "plan-only; no live command executed", "run preflight"
    blockers = deploy.blocking_checks(checks, ignore_deploy=True)
    if blockers:
        return "execns-helper-v22-deploy-blocked", False, "blocked before deploy by " + ", ".join(blockers), "resolve blockers before deploy"
    deploy_needed = any(check.name == "remote-helper-v22" and check.status != "pass" for check in checks)
    if args.command == "preflight":
        if deploy_needed:
            return "execns-helper-v22-deploy-preflight-ready-needs-deploy", True, "preflight complete; helper v22 deploy still requires exact approval", "operator may approve V402 deploy"
        return "execns-helper-v22-deploy-preflight-ready", True, "preflight complete; deploy still requires exact approval", "operator may approve V402 deploy"
    if not deploy.approved(args):
        return "execns-helper-v22-deploy-approval-required", True, "exact approval phrase required; no mutation executed", "rerun with exact phrase if deploy is intended"
    if deploy_result and not deploy_result["ok"]:
        return "execns-helper-v22-deploy-failed", False, "install command failed", "inspect install transcript and retry after cleanup"
    if v402_result and v402_result["decision"] != "private-selinux-surface-proof-preflight-ready":
        return "execns-helper-v22-deploy-postflight-blocked", False, f"V402 preflight decision={v402_result['decision']}", "resolve V402 preflight blockers"
    return "execns-helper-v22-deploy-pass", True, "helper v22 deployed or already current; V402 private proof preflight is ready", "next requires separate V402 private proof approval"


deploy.run_v373_preflight = run_v402_preflight
deploy.decide = decide


if __name__ == "__main__":
    raise SystemExit(deploy.main())
