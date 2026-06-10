#!/usr/bin/env python3
"""Run a targeted local security rescan for the active workspace native-init tree.

This is a repository-local guardrail, not a replacement for the external Codex
Cloud security scanner. It checks the current promotion-relevant surfaces:
root-control exposure, flash artifact identity, Wi-Fi credential/staging
hygiene, and the accepted trusted-lab boundary.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
SRC_ROOT = Path("workspace/public/src/native-init")
SCRIPT_ROOT = Path("workspace/public/src/scripts/revalidation")
THIRD_PARTY_ROOT = Path("workspace/public/src/third_party")
DEFAULT_OUT = REPO_ROOT / "docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md"


@dataclass(frozen=True)
class Check:
    check_id: str
    title: str
    status: str
    evidence: str
    note: str


def read_rel(path: Path | str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")


def exists_rel(path: Path | str) -> bool:
    return (REPO_ROOT / path).exists()


def has_all(path: Path | str, needles: list[str]) -> bool:
    text = read_rel(path)
    return all(needle in text for needle in needles)


def has_none(paths: list[Path | str], pattern: str) -> bool:
    regex = re.compile(pattern)
    for path in paths:
        full = REPO_ROOT / path
        if not full.exists():
            continue
        if regex.search(full.read_text(encoding="utf-8", errors="replace")):
            return False
    return True


def status_from(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return result.stdout.strip() or "unknown"


def builders_do_not_define_wifi_test_boot() -> bool:
    for path in (REPO_ROOT / SCRIPT_ROOT).glob("build_native_init_boot_v*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "-DA90_WIFI_TEST_BOOT" in text or "A90_WIFI_TEST_BOOT=1" in text:
            return False
    return True


def active_boot_sha_map_has_v2189() -> bool:
    path = SCRIPT_ROOT / "native_wifi_connect_carrier_handoff_v2174.py"
    text = read_rel(path)
    return (
        '"boot_linux_v2189_security_p0_stage_fix.img": '
        '"f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51"'
    ) in text


def run_checks() -> list[Check]:
    config = SRC_ROOT / "a90_config.h"
    tcpctl = SRC_ROOT / "a90_tcpctl.c"
    netservice = SRC_ROOT / "a90_netservice.c"
    wifi = SRC_ROOT / "a90_wifi.c"
    wificfg = SRC_ROOT / "a90_wificfg.c"
    exposure = SRC_ROOT / "a90_exposure.c"
    flash = SCRIPT_ROOT / "native_init_flash.py"
    bridge = SCRIPT_ROOT / "a90_bridge.py"
    serial_bridge = SCRIPT_ROOT / "serial_tcp_bridge.py"
    profile_stage = SCRIPT_ROOT / "a90_wifi_profile_stage.py"
    connect_runner = SCRIPT_ROOT / "native_wifi_connect_carrier_handoff_v2174.py"
    certify = THIRD_PARTY_ROOT / "mkbootimg/gki/certify_bootimg.py"

    native_network_files = [
        config,
        tcpctl,
        netservice,
        SRC_ROOT / "a90_usbnet.c",
        SRC_ROOT / "a90_shell.c",
    ]

    checks: list[Check] = []

    checks.append(Check(
        "S001",
        "native root-control listeners stay bound to the USB-local device address",
        status_from(
            has_all(config, [
                "#define NETSERVICE_TCP_BIND_ADDR NETSERVICE_DEVICE_IP",
                "#define A90_RSHELL_BIND_ADDR NETSERVICE_DEVICE_IP",
                '#define NETSERVICE_DEVICE_IP "192.168.7.2"',
            ])
            and has_none(native_network_files, r"INADDR_ANY|\"0\.0\.0\.0\"")
        ),
        "`a90_config.h` binds tcpctl/rshell to `NETSERVICE_DEVICE_IP`; active native listener files have no broad bind literal.",
        "Keeps F001/F003/F005/F030-style root-control exposure below USB-local NCM.",
    ))

    checks.append(Check(
        "S002",
        "netservice-started tcpctl requires token authentication",
        status_from(
            has_all(tcpctl, [
                "config->require_auth",
                "ERR auth-required",
                "OK authenticated",
                "read_token_file(config->token_path",
            ])
            and has_all(netservice, [
                "NETSERVICE_TCP_TOKEN_PATH",
                "O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW",
                "fchmod(fd, 0600)",
                "auth=required",
            ])
        ),
        "`a90_tcpctl.c` gates privileged `run` behind auth; `a90_netservice.c` writes a private no-follow token and starts tcpctl with `auth=required`.",
        "Covers the historical unauthenticated tcpctl finding family for the active path.",
    ))

    checks.append(Check(
        "S003",
        "host serial bridge wrapper is localhost-default and pins Samsung ACM identity",
        status_from(
            has_all(bridge, [
                'DEFAULT_HOST = "127.0.0.1"',
                'DEFAULT_DEVICE_GLOB = "/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*"',
                "allow_multiple_auto_matches",
                "refusing start: ambiguous Samsung ACM candidates",
            ])
            and has_all(serial_bridge, [
                'DEFAULT_HOST = "127.0.0.1"',
                "DEFAULT_DEVICE_GLOB",
                "expected_serial_realpath",
                "pinned_serial_realpath",
                "refusing ambiguous auto serial match",
            ])
        ),
        "`a90_bridge.py` and `serial_tcp_bridge.py` default to localhost and require/pin the Samsung serial identity unless explicitly overridden.",
        "F021/F030 remain accepted trusted-lab boundaries; this check prevents accidental LAN exposure as the default.",
    ))

    checks.append(Check(
        "S004",
        "flash handoff requires a caller-pinned image hash and verifies readback",
        status_from(
            has_all(flash, [
                "refusing to flash without --expect-sha256",
                "sealed_local_image_copy",
                "O_NOFOLLOW",
                "stat.S_ISREG",
                "stat.S_IWGRP | stat.S_IWOTH",
                "boot block prefix sha256 mismatch after flash",
                "--expect-version",
            ])
            and active_boot_sha_map_has_v2189()
        ),
        "`native_init_flash.py` refuses unpinned images, seals a no-follow local copy, rejects group/world-writable boot images, checks boot-block readback, and the active Wi-Fi runner pins the V2189 SHA.",
        "Closes the pre-promotion flash identity P0 for `v2189-security-p0-stage-fix`.",
    ))

    checks.append(Check(
        "S005",
        "Wi-Fi runtime dirs and supplicant config have root-owned/private modes",
        status_from(
            has_all(wificfg, [
                '#define WIFICFG_RUNTIME_ROOT "/cache/a90-wifi"',
                "wificfg_prepare_dir_owned(WIFICFG_RUNTIME_ROOT, 0755, 0, 0)",
                "wificfg_prepare_dir_owned(WIFICFG_SUPPLICANT_CTRL_DIR",
                "0770",
                "WIFICFG_WIFI_UID",
                "WIFICFG_WIFI_GID",
                "O_WRONLY | O_CREAT | O_EXCL | O_TRUNC | O_CLOEXEC | O_NOFOLLOW",
                "fchown(fd, 0, 0)",
                "fchmod(fd, 0600)",
                "rename(WIFICFG_SUPPLICANT_TMP, A90_WIFICFG_SUPPLICANT_CONF)",
                "chmod(A90_WIFICFG_SUPPLICANT_CONF, 0600)",
                "secret_values_logged=0",
            ])
        ),
        "`a90_wificfg.c` keeps `/cache/a90-wifi` root-owned, exposes only the control socket dir to UID/GID 1010, and writes supplicant config by no-follow temp+rename with `0600`.",
        "Prevents the stale staged config/runtime ownership class from becoming a promoted baseline property.",
    ))

    checks.append(Check(
        "S006",
        "Wi-Fi root-executed artifacts are verified before exec",
        status_from(
            has_all(wifi, [
                "wifi_verify_root_exec_parents",
                "wifi_verify_root_exec_file",
                "open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW)",
                "!S_ISREG(st.st_mode)",
                "st.st_uid != 0",
                "S_IWGRP | S_IWOTH",
                "require_exec",
                "supplicant.root_exec_rc",
                "supplicant.root_exec_ok",
                "return supplicant_root_exec_rc",
            ])
        ),
        "`a90_wifi.c` verifies parent dirs and executable files with no-follow open, regular-file/root-owner/not group-or-world writable checks, and reports `supplicant.root_exec_*`.",
        "Closes the staged standalone supplicant root-exec P0 exposed by V2188 and fixed in V2189.",
    ))

    checks.append(Check(
        "S007",
        "host Wi-Fi profile staging hardens cache artifacts and redacts secrets",
        status_from(
            has_all(profile_stage, [
                '["chown", "-R", "0:0", "/cache/a90-wifi/wpa-standalone"]',
                '["chmod", "-R", "go-w", "/cache/a90-wifi/wpa-standalone"]',
                '["chmod", "755", "/cache/a90-wifi/wpa-standalone"]',
                '"secret_values_logged": 0',
                '"secret_values_logged=1" not in output',
            ])
            and has_all(connect_runner, [
                'WORKSPACE_ENV_FILE = REPO_ROOT / "workspace" / "private" / "secrets" / "a90-wifi-test.env"',
                "redact_wifi_evidence",
                "redaction_leaked_secret",
                '"secret_values_logged=1"',
                '("chown-standalone-wpa", [TOYBOX, "chown", "-R", "0:0", "/cache/a90-wifi/wpa-standalone"])',
                '("chmod-standalone-wpa", [TOYBOX, "chmod", "-R", "go-w", "/cache/a90-wifi/wpa-standalone"])',
            ])
        ),
        "`a90_wifi_profile_stage.py` and the active connect runner re-own standalone Wi-Fi artifacts as root, remove group/other write bits, and fail/flag evidence if secrets leak.",
        "Keeps profile staging compatible with the V2189 device-side root-exec checks.",
    ))

    checks.append(Check(
        "S008",
        "boot-image archive extraction keeps path traversal checks",
        status_from(
            has_all(certify, [
                "def _validate_archive_member_path",
                "Archive entry escapes extraction dir",
                "member.isfile() or member.isdir()",
                "safe_unpack_archive",
            ])
            and "shutil.unpack_archive" not in read_rel(certify)
        ),
        "`certify_bootimg.py` still validates archive members and avoids plain `shutil.unpack_archive`.",
        "Preserves the previous host archive-extraction mitigation in the current third-party workspace path.",
    ))

    checks.append(Check(
        "S009",
        "exposure guardrails remain wired and token values stay hidden",
        status_from(
            exists_rel(SRC_ROOT / "a90_exposure.h")
            and has_all(exposure, [
                "accepted_boundary=F021/F030",
                "no_token_values=yes",
            ])
            and has_all(SRC_ROOT / "a90_diag.c", [
                "token_value=hidden",
                "[exposure]",
            ])
        ),
        "`a90_exposure.*` labels F021/F030 as accepted boundaries and diagnostics hide token values.",
        "Makes the accepted local root-control boundary machine-visible instead of implicit.",
    ))

    checks.append(Check(
        "S010",
        "dead Wi-Fi test-boot scaffolding is not compiled by active builders",
        status_from(
            builders_do_not_define_wifi_test_boot()
            and has_all(SRC_ROOT / "v724/90_main.inc.c", [
                "#ifdef A90_WIFI_TEST_BOOT",
                "#endif",
            ])
        ),
        "Active `build_native_init_boot_v*.py` files do not define `-DA90_WIFI_TEST_BOOT`; the large research block in `v724/90_main.inc.c` remains source debt, not current binary behavior.",
        "Architecture cleanup remains important, but this specific block is not a V2189 promotion security blocker.",
    ))

    checks.append(Check(
        "S011",
        "accepted local root-control channels remain intentionally present",
        "WARN",
        "USB ACM root shell, localhost serial bridge, and USB-local NCM tcpctl are still intentional lab rescue/control channels.",
        "Do not expose bridge/tcpctl/rshell on LAN or Wi-Fi without a new authentication and threat model.",
    ))

    return checks


def render_report(checks: list[Check], *, baseline: str, title: str) -> str:
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1

    implementation_blockers = counts.get("FAIL", 0)
    lines = [
        f"# {title}",
        "",
        f"Date: {dt.date.today().isoformat()}",
        f"Baseline: `{baseline}`",
        f"Git HEAD: `{git_head()}`",
        "Scope: active workspace native-init source, active revalidation host tools, third-party boot tooling used by the current builder, V2189 security P0 guardrails, and accepted trusted-lab root-control boundaries.",
        "",
        "This is a local targeted rescan, not a Codex Cloud scanner replacement.",
        "",
        "## Summary",
        "",
        f"- PASS: {counts.get('PASS', 0)}",
        f"- WARN: {counts.get('WARN', 0)}",
        f"- FAIL: {counts.get('FAIL', 0)}",
        f"- New implementation blocker from this local scan: `{implementation_blockers}`",
        "",
        "## Results",
        "",
        "| id | status | check | evidence | note |",
        "|---|---|---|---|---|",
    ]
    for check in checks:
        lines.append(
            f"| {check.check_id} | {check.status} | {check.title} | {check.evidence} | {check.note} |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
    ])
    if implementation_blockers:
        lines.append(
            "The local targeted scan found one or more implementation blockers. Do not promote this baseline until the failed checks are resolved or explicitly re-scoped."
        )
    else:
        lines.append(
            "The local targeted scan found no new implementation blocker in the active V2189 promotion path. The remaining warning is the intentional trusted-lab local root-control boundary."
        )
    lines.extend([
        "",
        "Promotion remains conditioned on the separate live validation evidence and the architecture-debt disposition.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "python3 workspace/public/src/scripts/revalidation/local_security_rescan.py \\",
        "  --baseline 'A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)' \\",
        "  --out docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md",
        "git diff --check",
        "```",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--baseline", default="A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)")
    parser.add_argument("--title", default="V2189 Fresh Local Security Rescan")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks = run_checks()
    report = render_report(checks, baseline=args.baseline, title=args.title)
    out_path = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(out_path.relative_to(REPO_ROOT))
    return 1 if any(check.status == "FAIL" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
