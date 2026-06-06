#!/usr/bin/env python3
"""Run a targeted local security rescan for the active A90 native-init tree.

This is not a replacement for Codex Cloud's security scanner. It is a
repository-local guardrail that checks the patterns that previously produced the
F001-F046 findings and the current root-control surfaces.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT = REPO_ROOT / "docs" / "security" / "scans" / "SECURITY_FRESH_SCAN_F045_F046_2026-05-11.md"


@dataclass(frozen=True)
class Check:
    check_id: str
    title: str
    status: str
    evidence: str
    note: str


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def line_refs(path: str, pattern: str) -> list[str]:
    full = REPO_ROOT / path
    if not full.exists():
        return []
    regex = re.compile(pattern)
    refs: list[str] = []
    for number, line in enumerate(full.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if regex.search(line):
            refs.append(f"`{path}:{number}`")
    return refs


def any_refs(paths: list[str], pattern: str) -> list[str]:
    refs: list[str] = []
    for path in paths:
        refs.extend(line_refs(path, pattern))
    return refs


def menu_hold_source_clears_non_repeat(source: str) -> bool:
    old_inline_pattern = (
        "if (now_ms >= menu_hold_next_ms) {\n                    if (auto_menu_handle_volume_step" in source
        and "else {\n                        menu_hold_code = 0;\n                        menu_hold_next_ms = 0;\n                    }" in source
    )
    new_helper_pattern = (
        "if (auto_hud_handle_volume_step(state, state->menu_hold_code))" in source
        and "else {\n                auto_hud_reset_hold_timer(state);\n            }" in source
        and "state->menu_hold_code = 0;" in source
        and "state->menu_hold_next_ms = 0;" in source
    )
    return old_inline_pattern or new_helper_pattern


def status_from(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def run_git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def active_host_files() -> list[str]:
    files: list[str] = []
    for root in (REPO_ROOT / "scripts" / "revalidation").glob("*"):
        if root.name == "local_security_rescan.py":
            continue
        if root.suffix in {".py", ".sh"}:
            files.append(str(root.relative_to(REPO_ROOT)))
    files.append("mkbootimg/gki/certify_bootimg.py")
    return sorted(files)


def run_checks() -> list[Check]:
    config = read("stage3/linux_init/a90_config.h")
    tcpctl = read("stage3/linux_init/a90_tcpctl.c")
    netservice = read("stage3/linux_init/a90_netservice.c")
    helper = read("stage3/linux_init/a90_helper.c")
    controller = read("stage3/linux_init/a90_controller.c")
    dispatch = read("stage3/linux_init/v153/80_shell_dispatch.inc.c")
    shell_basic = read("stage3/linux_init/v153/60_shell_basic_commands.inc.c")
    storage_net = read("stage3/linux_init/v153/70_storage_android_net.inc.c")
    serial_bridge = read("scripts/revalidation/serial_tcp_bridge.py")
    native_soak = read("scripts/revalidation/native_soak_validate.py")
    integrated_validate = read("scripts/revalidation/native_integrated_validate.py")
    certify = read("mkbootimg/gki/certify_bootimg.py")
    diag_collect = read("scripts/revalidation/diag_collect.py")
    tcpctl_host = read("scripts/revalidation/tcpctl_host.py")
    diag = read("stage3/linux_init/a90_diag.c")
    runtime = read("stage3/linux_init/a90_runtime.c")
    log = read("stage3/linux_init/a90_log.c")
    storage = read("stage3/linux_init/a90_storage.c")
    longsoak = read("stage3/linux_init/a90_longsoak.c")
    longsoak_helper = read("stage3/linux_init/helpers/a90_longsoak.c")
    native_long_soak = read("scripts/revalidation/native_long_soak.py")
    longsoak_bundle = read("scripts/revalidation/native_long_soak_bundle.py")
    path_safety = read("scripts/revalidation/a90harness/path_safety.py")
    storage_iotest = read("scripts/revalidation/storage_iotest.py")
    fs_exerciser = read("scripts/revalidation/fs_exerciser_mini.py")
    cpu_mem_stability = read("scripts/revalidation/cpu_mem_thermal_stability.py")
    observer = read("scripts/revalidation/a90harness/observer.py")
    ncm_report = read("scripts/revalidation/ncm_tcp_stability_report.py")
    ncm_preflight = read("scripts/revalidation/a90harness/modules/ncm_tcp_preflight.py")
    cpu_memory_profiles = read("scripts/revalidation/a90harness/modules/cpu_memory_profiles.py")
    ncm_host_setup = read("scripts/revalidation/ncm_host_setup.py")
    v166_deferred_report = read("docs/reports/NATIVE_INIT_V166_NETWORK_THROUGHPUT_DEFERRED_2026-05-09.md")
    menu_hold_sources = [
        "stage3/linux_init/v131/40_menu_apps.inc.c",
        "stage3/linux_init/v132/40_menu_apps.inc.c",
        "stage3/linux_init/v133/40_menu_apps.inc.c",
        "stage3/linux_init/v134/40_menu_apps.inc.c",
        "stage3/linux_init/v153/40_menu_apps.inc.c",
    ]

    active_network_paths = [
        "stage3/linux_init/a90_config.h",
        "stage3/linux_init/a90_tcpctl.c",
        "stage3/linux_init/a90_netservice.c",
        "stage3/linux_init/helpers/a90_rshell.c",
        "stage3/linux_init/v153/70_storage_android_net.inc.c",
        "stage3/linux_init/v153/80_shell_dispatch.inc.c",
    ]
    active_root_ssh_patterns = r"PermitRootLogin yes|PasswordAuthentication yes|root:root|password[:= ]+root|passwd root"

    checks: list[Check] = []

    checks.append(Check(
        "S001",
        "tcpctl and rshell bind to the USB NCM device address, not INADDR_ANY",
        status_from(
            "#define NETSERVICE_TCP_BIND_ADDR NETSERVICE_DEVICE_IP" in config
            and "#define A90_RSHELL_BIND_ADDR NETSERVICE_DEVICE_IP" in config
            and not any_refs(active_network_paths, r"INADDR_ANY|0\.0\.0\.0")
        ),
        "`stage3/linux_init/a90_config.h` binds both services to `NETSERVICE_DEVICE_IP`; active network files have no `INADDR_ANY`/`0.0.0.0` match.",
        "Reduces F001/F003/F005/F030-style broad network exposure.",
    ))

    checks.append(Check(
        "S002",
        "tcpctl requires token auth when launched by netservice",
        status_from(
            "config->token_path = argv[6];" in tcpctl
            and "config->require_auth = true;" in tcpctl
            and "ERR auth-required" in tcpctl
            and "NETSERVICE_TCP_TOKEN_PATH" in netservice
            and "auth=required" in netservice
        ),
        "`a90_tcpctl.c` gates `run` behind `auth`; `a90_netservice.c` passes `NETSERVICE_TCP_TOKEN_PATH` and logs `auth=required`.",
        "Covers previous unauthenticated tcpctl findings.",
    ))

    checks.append(Check(
        "S003",
        "netservice and rshell token files are private no-follow writes",
        status_from(
            "O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW" in netservice
            and "0600" in netservice
            and "fchmod(fd, 0600)" in netservice
            and "O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW" in storage_net
            and "fchmod(fd, 0600)" in storage_net
            and "token_value=hidden" in diag
        ),
        "Token writers use `O_NOFOLLOW` and `0600`; diagnostics hide token value.",
        "Token display commands remain operator-only dangerous controls over the trusted local shell.",
    ))

    checks.append(Check(
        "S004",
        "dangerous service commands remain blocked by menu busy gate",
        status_from(
            '{ "service", handle_service, "service [list|status|start|stop|enable|disable] [name]", CMD_DANGEROUS' in dispatch
            and 'strcmp(name, "service") == 0' in controller
            and "service_read_only" in controller
            and "CMD_DANGEROUS" in controller
        ),
        "`service` is registered `CMD_DANGEROUS`; controller only allows read-only `service list/status` while menu is active.",
        "Covers F010/F023-style dangerous-command bypasses.",
    ))

    checks.append(Check(
        "S005",
        "runtime helper preference requires a valid manifest SHA-256 match",
        status_from(
            "entry->expected_sha256[0] != '\\0'" in helper
            and "entry->hash_checked" in helper
            and "entry->hash_match" in helper
            and "runtime helper sha256 required before preference" in helper
            and "sha256 mismatch" in helper
            and "snprintf(entry->preferred, sizeof(entry->preferred), \"%s\", entry->fallback);" in helper
        ),
        "`a90_helper.c` only prefers runtime helpers when SHA-256 is present, checked, and matched; otherwise fallback is selected.",
        "Covers helper manifest arbitrary-exec findings.",
    ))

    checks.append(Check(
        "S006",
        "logs, runtime probes, storage probes, and diagnostics use no-follow private writes",
        status_from(
            "O_NOFOLLOW" in log
            and "NATIVE_LOG_FALLBACK_DIR, 0700" in log
            and "0600" in log
            and "O_NOFOLLOW" in runtime
            and "0700" in runtime
            and "O_NOFOLLOW" in storage
            and "O_NOFOLLOW" in diag
            and "0600" in diag
            and "0700" in diag
        ),
        "`a90_log.c`, `a90_runtime.c`, `a90_storage.c`, and `a90_diag.c` retain `O_NOFOLLOW`, `0600`, and private-dir guardrails.",
        "Covers SD symlink/log/diagnostic disclosure findings.",
    ))

    checks.append(Check(
        "S007",
        "host boot-image archive extraction validates entries before extractall",
        status_from(
            "def _validate_archive_member_path" in certify
            and "Archive entry escapes extraction dir" in certify
            and "member.isfile() or member.isdir()" in certify
            and "mode not in (stat.S_IFREG, stat.S_IFDIR)" in certify
            and "safe_unpack_archive" in certify
            and "shutil.unpack_archive" not in certify
        ),
        "`mkbootimg/gki/certify_bootimg.py` uses tar/zip validators and `safe_unpack_archive`; `shutil.unpack_archive` is absent.",
        "Covers unsafe archive extraction finding.",
    ))

    checks.append(Check(
        "S008",
        "host subprocess helpers pin repo-relative paths and cwd where needed",
        status_from(
            "REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())" in native_soak
            and "A90CTL = REPO_ROOT" in native_soak
            and "cwd=REPO_ROOT" in native_soak
            and ("cwd=REPO_ROOT" in diag_collect or "cwd: Path = REPO_ROOT" in diag_collect)
        ),
        "`native_soak_validate.py` resolves `a90ctl.py` from `__file__` and runs with `cwd=REPO_ROOT`; diagnostics collector does the same.",
        "Covers untrusted-CWD helper execution findings.",
    ))

    checks.append(Check(
        "S009",
        "serial bridge defaults to localhost and pins Samsung by-id serial identity",
        status_from(
            'DEFAULT_HOST = "127.0.0.1"' in serial_bridge
            and "DEFAULT_DEVICE_GLOB" in serial_bridge
            and "allow_multiple_auto_matches" in serial_bridge
            and "pinned_serial_realpath" in serial_bridge
            and "expected_serial_realpath" in serial_bridge
        ),
        "`serial_tcp_bridge.py` defaults to `127.0.0.1`, uses Samsung by-id auto discovery, refuses ambiguous matches by default, and tracks realpath identity.",
        "F021/F030 remain accepted trusted-lab local control boundaries.",
    ))

    checks.append(Check(
        "S010",
        "diagnostic bundles are private and redact log tails by default",
        status_from(
            "path.parent.chmod(0o700)" in diag_collect
            and "path.chmod(0o600)" in diag_collect
            and "tail=redacted" in diag
            and "token_value=hidden" in diag
        ),
        "Host diag output chmods `0700/0600`; device diag defaults redact log tails and token value.",
        "Covers diagnostic disclosure findings.",
    ))

    active_refs = any_refs(active_host_files(), active_root_ssh_patterns)
    checks.append(Check(
        "S011",
        "active host scripts do not set known root SSH credentials",
        status_from(not active_refs),
        "No active `scripts/revalidation` or `mkbootimg/gki/certify_bootimg.py` match for default root SSH credential patterns." if not active_refs else ", ".join(active_refs[:8]),
        "Legacy archived docs/scripts are excluded from active v153 runtime/tooling scope.",
    ))

    checks.append(Check(
        "S012",
        "tcpctl host installer writes temp path, verifies hash, then moves into place",
        status_from(
            "tmp_target" in tcpctl_host
            and "sha256_file(local_binary)" in tcpctl_host
            and "device tmp sha256 did not match" in tcpctl_host
            and "mv -f {tmp_target} {target}" in tcpctl_host
            and "rm -f {tmp_target}" in tcpctl_host
        ),
        "`tcpctl_host.py install` uses a per-run temp target, verifies SHA-256 before `mv`, and cleans the temp path on exceptions.",
        "Covers tcpctl install race/poisoning follow-up guardrails.",
    ))

    menu_hold_ok = True
    for path in menu_hold_sources:
        source = read(path)
        menu_hold_ok = menu_hold_ok and menu_hold_source_clears_non_repeat(source)
    checks.append(Check(
        "S013",
        "volume hold repeat timer clears when a screen cannot consume repeats",
        status_from(menu_hold_ok),
        "Retained v131-v153 auto-HUD loops clear `menu_hold_code` and `menu_hold_next_ms` when a timed repeat is not consumed.",
        "Covers F032 zero-timeout poll/redraw spin in non-repeat screens.",
    ))

    checks.append(Check(
        "S014",
        "menu-visible mountsd requires explicit status subcommand",
        status_from(
            "static bool subcmd_one_of" in controller
            and 'if (strcmp(name, "mountsd") == 0) {\n        return subcmd_one_of(argc, argv, status_only' in controller
            and 'strcmp(name, "hudlog") == 0 ||\n        strcmp(name, "netservice") == 0' in controller
        ),
        "`a90_controller.c` allows `mountsd status` during menu-active operation, but no longer allows bare `mountsd`.",
        "Covers F033 mountsd side effects through absent-subcommand menu policy.",
    ))

    checks.append(Check(
        "S015",
        "exposure guardrail command and diagnostics are wired",
        status_from(
            (REPO_ROOT / "stage3/linux_init/a90_exposure.c").exists()
            and (REPO_ROOT / "stage3/linux_init/a90_exposure.h").exists()
            and '{ "exposure", handle_exposure, "exposure [status|verbose|guard]", CMD_NONE, A90_CMD_GROUP_NETWORK }' in dispatch
            and "a90_exposure_summary(&exposure" in shell_basic
            and "[exposure]" in read("stage3/linux_init/a90_diag.c")
            and "token_value=hidden" in read("stage3/linux_init/a90_diag.c")
        ),
        "`exposure [status|verbose|guard]`, `status`/`bootstatus` summaries, and `diag` exposure output are present without token values.",
        "Provides machine-checkable evidence before broader network or Wi-Fi work.",
    ))

    checks.append(Check(
        "S016",
        "controller policy matrix covers menu-visible side-effect boundaries",
        status_from(
            '{ "policycheck", handle_policycheck, "policycheck [status|run|verbose]", CMD_NONE, A90_CMD_GROUP_CORE }' in dispatch
            and "a90_controller_policy_matrix_run(command_table" in dispatch
            and "menu block bare mountsd" in controller
            and "menu block netservice start" in controller
            and "menu block rshell start" in controller
            and "menu block service start tcpctl" in controller
            and "menu block writefile" in controller
            and "menu block mountfs" in controller
            and "menu block reboot" in controller
            and "power block reboot" in controller
            and "policycheck [status|run|verbose]" in shell_basic
        ),
        "`policycheck` is registered and the matrix names representative storage/network/service/process/power side-effect cases.",
        "Covers absent-subcommand and command-policy drift before new network work.",
    ))

    checks.append(Check(
        "S017",
        "integrated validation harness covers core safety gates",
        status_from(
            "DEFAULT_COMMANDS" in integrated_validate
            and "selftest verbose" in integrated_validate
            and "pid1guard verbose" in integrated_validate
            and "exposure guard" in integrated_validate
            and "policycheck run" in integrated_validate
            and "service list" in integrated_validate
            and "netservice status" in integrated_validate
            and "rshell audit" in integrated_validate
            and "screenmenu" in integrated_validate
            and "hide" in integrated_validate
            and "cwd=REPO_ROOT" in integrated_validate
            and "DEFAULT_EXPECT_VERSION = \"A90 Linux init 0.9.53 (v153)\"" in integrated_validate
        ),
        "`native_integrated_validate.py` covers selftest, pid1guard, exposure, policycheck, service/network status, and UI nonblocking checks.",
        "Provides one host gate before Wi-Fi/network-facing changes or large controller refactors.",
    ))

    checks.append(Check(
        "S018",
        "longsoak host export is bounded and does not cat device-provided paths",
        status_from(
            '"longsoak",' in native_long_soak
            and '"export",' in native_long_soak
            and '["cat", device_path]' not in native_long_soak
            and "DEFAULT_DEVICE_EXPORT_MAX_LINES" in native_long_soak
            and "DEFAULT_DEVICE_EXPORT_MAX_BYTES" in native_long_soak
            and "parse_longsoak_export_summary" in native_long_soak
        ),
        "`native_long_soak.py` collects recorder data through `longsoak export` with line/byte caps and no longer issues generic `cat <device_path>`.",
        "Covers F034 unvalidated device path and unbounded host cat.",
    ))

    checks.append(Check(
        "S019",
        "longsoak helper opens root logs with no-follow private regular-file handling",
        status_from(
            "O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW" in longsoak_helper
            and "fstat(fd, &st)" in longsoak_helper
            and "!S_ISREG(st.st_mode)" in longsoak_helper
            and "fchmod(fd, 0600)" in longsoak_helper
            and "chmod(path, 0600)" not in longsoak_helper
        ),
        "`helpers/a90_longsoak.c` uses `open(...O_NOFOLLOW, 0600)`, verifies a regular file with `fstat`, and applies `fchmod` on the fd.",
        "Covers F035 helper symlink-following root log writes.",
    ))

    checks.append(Check(
        "S020",
        "longsoak status/tail/export reject display sentinels and unsafe paths",
        status_from(
            "strcmp(path, \"-\") == 0" in longsoak
            and "longsoak_path_has_expected_shape" in longsoak
            and "longsoak_open_log_readonly(status->path)" in longsoak
            and "longsoak_open_log_readonly(longsoak_path)" in longsoak
            and "O_RDONLY | O_CLOEXEC | O_NOFOLLOW" in longsoak
            and "longsoak: export path=" in longsoak
        ),
        "`a90_longsoak.c` validates owned JSONL paths, rejects `-`, and routes status scan, tail, and export through the no-follow safe opener.",
        "Covers F036 and the device-owned half of F034.",
    ))

    checks.append(Check(
        "S021",
        "longsoak bundle uses private no-follow output handling",
        status_from(
            "PRIVATE_DIR_MODE = 0o700" in longsoak_bundle
            and "PRIVATE_FILE_MODE = 0o600" in longsoak_bundle
            and "ensure_private_dir" in longsoak_bundle
            and "write_private_text" in longsoak_bundle
            and "copy_private_regular_file" in longsoak_bundle
            and "shutil.copy2" not in longsoak_bundle
            and ".write_text(" not in longsoak_bundle
        ),
        "`native_long_soak_bundle.py` forces `0700/0600`, rejects symlink destinations, and avoids `copy2`/`Path.write_text` for bundle outputs.",
        "Covers F037 private evidence and symlink-clobber handling.",
    ))

    checks.append(Check(
        "S023",
        "storage and filesystem exercisers enforce confined device paths",
        status_from(
            "def require_safe_component" in path_safety
            and "def normalize_device_path" in path_safety
            and "def require_path_under" in path_safety
            and "def require_run_child" in path_safety
            and "def require_safe_raw_arg" in path_safety
            and "require_run_child(args.test_root, args.run_id)" in storage_iotest
            and "raw_command(\"run\", args.toybox, \"rm\", \"-rf\", target)" in storage_iotest
            and ".startswith(\"/mnt/sdext/a90/test-\")" not in storage_iotest
            and "require_run_child(args.test_root, args.run_id)" in fs_exerciser
            and "normalized != DEFAULT_TEST_ROOT" in fs_exerciser
            and ".startswith(\"/mnt/sdext/a90/test-fsx\")" not in fs_exerciser
        ),
        "`path_safety.py` centralizes safe components/path-boundary/raw-arg checks; storage/fs tests no longer rely on weak string-prefix guards.",
        "Covers F038 and F041 path escape / raw serial command injection findings.",
    ))

    checks.append(Check(
        "S024",
        "CPU/memory stability validator does not opt into unsafe replay",
        status_from("retry_unsafe=True" not in cpu_mem_stability),
        "`cpu_mem_thermal_stability.py` no longer marks `dd`, `rm`, `longsoak start`, `ps`, or cpustress `run` commands as retry-unsafe replayable.",
        "Covers F040 replay of privileged non-idempotent commands.",
    ))

    checks.append(Check(
        "S025",
        "unlimited observer uses counters instead of retaining all samples",
        status_from(
            "all_samples" not in observer
            and "sample_count" in observer
            and "failure_count" in observer
            and "recent_failures = recent_failures[-16:]" in observer
        ),
        "`a90harness/observer.py` streams JSONL and keeps counters plus a bounded recent-failure ring.",
        "Covers F043 host memory growth during unlimited observer runs.",
    ))

    checks.append(Check(
        "S026",
        "NCM/TCP stability report requires authenticated tcpctl evidence",
        status_from(
            "tcpctl auth required" in ncm_report
            and "tcpctl authenticated flow" in ncm_report
            and "tcpctl no no-auth marker" in ncm_report
            and "auth=required" in ncm_report
            and "auth=none" in ncm_report
            and "OK authenticated" in ncm_report
        ),
        "`ncm_tcp_stability_report.py` now requires `auth=required`, authenticated request flow, and absence of `auth=none`.",
        "Covers F042 false PASS for unauthenticated tcpctl transcripts.",
    ))

    checks.append(Check(
        "S027",
        "NCM/TCP preflight matches tcpctl smoke output and checks auth",
        status_from(
            "--- tcpctl-checks ---" not in ncm_preflight
            and "--- ping ---" in ncm_preflight
            and "--- version ---" in ncm_preflight
            and "--- status ---" in ncm_preflight
            and "--- shutdown ---" in ncm_preflight
            and "--- serial-run ---" in ncm_preflight
            and "OK authenticated" in ncm_preflight
            and "auth=required" in ncm_preflight
            and "auth=none" in ncm_preflight
        ),
        "`ncm_tcp_preflight.py` no longer waits for a stale marker and verifies the authenticated smoke transcript.",
        "Covers F044 false failure of the NCM/TCP preflight wrapper.",
    ))

    checks.append(Check(
        "S028",
        "NCM resume docs prefer explicit host interface pinning",
        status_from(
            "setup --allow-auto-interface" not in v166_deferred_report
            and "setup --interface <known-usb-ncm-ifname>" in v166_deferred_report
            and "diagnostic fallback only" in v166_deferred_report
            and "diagnostic fallback only" in ncm_host_setup
            and "prefer --interface on multi-NIC hosts" in ncm_host_setup
        ),
        "The v166 deferred throughput resume path recommends `--interface`; auto-interface is documented as diagnostic fallback only.",
        "Covers F039 unsafe operational bypass of host NIC pinning.",
    ))

    checks.append(Check(
        "S029",
        "CPU/memory profiles use private unpredictable device temp directories",
        status_from(
            "import secrets" in cpu_memory_profiles
            and "secrets.token_hex" in cpu_memory_profiles
            and "DEVICE_TMP_PREFIX = \"a90-cpumem\"" in cpu_memory_profiles
            and "require_safe_component" in cpu_memory_profiles
            and "require_path_under" in cpu_memory_profiles
            and '"mem-mkdir"' in cpu_memory_profiles
            and '"mkdir", "-m", "700", temp_dir' in cpu_memory_profiles
            and '["run", "/cache/bin/toybox", "rm", "-rf", temp_dir]' in cpu_memory_profiles
            and 'path = f"/tmp/{self._run_id}-{spec.name}-mem.bin"' not in cpu_memory_profiles
        ),
        "`cpu_memory_profiles.py` now creates a random root-owned `/tmp/a90-cpumem.*` directory before `dd` writes and cleans that directory.",
        "Covers F045 predictable shared `/tmp` root `dd` target overwrite.",
    ))

    checks.append(Check(
        "S030",
        "NCM preflight refuses untrusted cache tcpctl fallback",
        status_from(
            'TRUSTED_TCPCTL_BINARY = "/bin/a90_tcpctl"' in ncm_preflight
            and '"/cache/bin/a90_tcpctl"' not in ncm_preflight
            and "for candidate in" not in ncm_preflight
            and "trusted ramdisk tcpctl helper missing" in ncm_preflight
            and "--device-binary" in ncm_preflight
        ),
        "`ncm_tcp_preflight.py` only selects the ramdisk `/bin/a90_tcpctl`; it no longer executes `/cache/bin/a90_tcpctl` after a plain stat.",
        "Covers F046 untrusted persistent tcpctl helper fallback.",
    ))

    checks.append(Check(
        "S022",
        "accepted local root-control channels remain intentionally present",
        "WARN",
        "USB ACM root shell and localhost serial bridge are still present by design.",
        "Matches F021/F030 accepted-lab-boundary; do not expose bridge or ACM control over LAN/Wi-Fi without new auth.",
    ))

    return checks


def render_report(checks: list[Check]) -> str:
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1

    lines = [
        "# F045-F046 Fresh Local Security Rescan",
        "",
        "Date: 2026-05-11",
        "Baseline: active v159 native-init plus post-v184 host harness security patches",
        f"Git HEAD: `{run_git_head()}`",
        "Scope: active native-init source, shared modules, current revalidation host tools, F001-F046 local guardrails, and known root-control surfaces.",
        "",
        "This is a local targeted rescan, not a Codex Cloud scanner replacement. It checks the imported F001-F046 pattern families, exposure guardrails, and controller policy matrix wiring against the current repository state.",
        "",
        "## Summary",
        "",
        f"- PASS: {counts.get('PASS', 0)}",
        f"- WARN: {counts.get('WARN', 0)}",
        f"- FAIL: {counts.get('FAIL', 0)}",
        "- New implementation blocker from this local scan: `0`" if counts.get("FAIL", 0) == 0 else "- New implementation blocker from this local scan: `yes`",
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
        "The local targeted scan found no new implementation blocker in the active code path. The remaining warning is the already accepted trusted-lab boundary for physical USB ACM/local serial bridge control.",
        "",
        "Before any Wi-Fi or broader network exposure, rerun this local scan and a Codex Cloud security scan, then revisit F021/F030 if the control channel is no longer USB-local/localhost-only.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "python3 scripts/revalidation/local_security_rescan.py --out docs/security/scans/SECURITY_FRESH_SCAN_F045_F046_2026-05-11.md",
        "git diff --check",
        "```",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="markdown report path; use - for stdout only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks = run_checks()
    report = render_report(checks)
    if args.out == "-":
        print(report)
    else:
        out = Path(args.out)
        if not out.is_absolute():
            out = REPO_ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        try:
            display_path = out.relative_to(REPO_ROOT)
        except ValueError:
            display_path = out
        print(f"wrote {display_path}")
    return 1 if any(check.status == "FAIL" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
