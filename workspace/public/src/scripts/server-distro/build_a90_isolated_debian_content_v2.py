#!/usr/bin/env python3
"""Build the H0 A90 isolated-Debian content set into private host output.

This is a content-only builder.  It never opens a device, enumerates USB, uses
ADB/Odin/fastboot, mounts UFS, configures a network, or installs anything.  It
uses a private SHA-pinned Dropbear source input, creates only the manifest
allowlist, builds the three tracked static-PIE components with the pinned
cross-compiler, and emits a deterministic private tarball plus receipt.

The Dropbear source input is intentionally not vendored.  Until it is present,
the materialization command fails closed and the tracked manifest remains an
H0 specification with the exact Dropbear hash deferred.  After every binary
is materialized, the intended trace method is qemu-aarch64 user-mode tracing
with binfmt_misc.  That trace is a candidate syscall superset and must later
be followed by on-device negative testing; this script never runs that trace.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
COMPONENT_DIR = SCRIPT_DIR / "a90_isolated_debian_content_v2"
MANIFEST_PATH = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    / "isolated-debian-minimal-content-v2/userdata-content-manifest.json"
)
PRIVATE_ROOT = (REPO_ROOT / "workspace/private").resolve()
DEFAULT_DROPBEAR_SOURCE = PRIVATE_ROOT / "inputs/a90-isolated-debian/dropbear-source"
DEFAULT_OUTPUT = PRIVATE_ROOT / "outputs/a90-isolated-debian-content-v2"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "a90-isolated-debian-ufs-content-manifest-v2"
SERVICE_UID = 3301
SERVICE_GID = 3301
KEY_DAEMON_UID = 3302
KEY_DAEMON_GID = 3302

COMPONENTS = {
    "/usr/local/libexec/a90-pid1": ("pid1", COMPONENT_DIR / "a90_pid1.c"),
    "/usr/local/libexec/a90-probe": ("probe", COMPONENT_DIR / "a90_probe.c"),
    "/usr/local/libexec/a90-workload": (
        "workload",
        COMPONENT_DIR / "a90_workload.c",
    ),
}

STATIC_TEXT = {
    "/etc/a90-appliance-stage": (
        "schema=a90-isolated-debian-content-v2\n"
        "root=read-only-ufs\n"
        "pid1=/usr/local/libexec/a90-pid1\n"
        "ssh=/usr/sbin/dropbear\n"
        "workload=/usr/local/libexec/a90-workload\n"
        "authority=host-only-specification\n"
    ).encode("utf-8"),
    "/etc/a90-server-distro-stage": (
        "stage=isolated-debian-content-h0\n"
        "network=native-bootstrap-veth-only\n"
        "wifi=native-owner\n"
        "firstboot=absent\n"
        "hud=absent\n"
        "smoke-http=absent\n"
    ).encode("utf-8"),
    "/etc/group": b"root:x:0:\na90svc:x:3301:\na90key:x:3302:\n",
    "/etc/nsswitch.conf": (
        b"passwd: files\ngroup: files\nshadow: files\nhosts: files\n"
    ),
    "/etc/passwd": (
        b"root:x:0:0:root:/nonexistent:/usr/sbin/nologin\n"
        b"a90svc:x:3301:3301:A90 service:/srv/a90-service:/usr/local/libexec/a90-probe\n"
        b"a90key:x:3302:3302:A90 SSH key daemon:/var/empty:/usr/sbin/nologin\n"
    ),
    "/etc/shadow": (
        b"root:!*:0:0:99999:7:::\n"
        b"a90svc:!*:0:0:99999:7:::\n"
        b"a90key:!*:0:0:99999:7:::\n"
    ),
    "/etc/shells": b"/usr/local/libexec/a90-probe\n",
}

FILE_MODES = {
    "/etc/a90-appliance-stage": 0o644,
    "/etc/a90-server-distro-stage": 0o644,
    "/etc/group": 0o644,
    "/etc/nsswitch.conf": 0o644,
    "/etc/passwd": 0o644,
    "/etc/shadow": 0o600,
    "/etc/shells": 0o644,
    "/usr/local/libexec/a90-pid1": 0o755,
    "/usr/local/libexec/a90-probe": 0o755,
    "/usr/local/libexec/a90-workload": 0o755,
    "/usr/sbin/dropbear": 0o755,
}

SOURCE_DATE_EPOCH = 0
COMPILER_FLAGS = (
    "-std=c11",
    "-O2",
    "-pipe",
    "-fPIE",
    "-fno-ident",
    "-ffunction-sections",
    "-fdata-sections",
    "-D_FORTIFY_SOURCE=2",
    "-fstack-protector-strong",
    "-static-pie",
    "-Wl,--gc-sections",
    "-Wl,--build-id=none",
    "-Wl,--strip-all",
)


class DeferredInput(RuntimeError):
    """A required private input is unavailable; this is not a build failure."""


class ContentError(RuntimeError):
    """The content contract is malformed or a pinned input drifted."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentError("content manifest is not exact JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ContentError("content manifest schema is not the isolated-Debian v2 schema")
    return value


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContentError(f"{label} is not a nonempty string")
    return value


def _manifest_files(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ContentError("files is not a nonempty list")
    result: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict):
            raise ContentError("file record is not an object")
        path = item.get("path")
        if (
            not isinstance(path, str)
            or not path.startswith("/")
            or "//" in path
            or "." in Path(path).parts
            or ".." in Path(path).parts
            or path in result
        ):
            raise ContentError(f"file path is not unique and canonical: {path!r}")
        if item.get("kind") != "file" or item.get("mode") not in {
            "0600",
            "0644",
            "0755",
        }:
            raise ContentError(f"file record has an invalid kind/mode: {path}")
        mode = int(item["mode"], 8)
        if mode & (stat.S_ISUID | stat.S_ISGID):
            raise ContentError(f"setuid/setgid executable in content: {path}")
        if item.get("uid") not in {0, SERVICE_UID} or item.get("gid") not in {
            0,
            SERVICE_GID,
        }:
            raise ContentError(f"file ownership is outside the content contract: {path}")
        digest = item.get("sha256")
        deferred = item.get("artifact_state") == "deferred"
        if digest is not None and (
            not isinstance(digest, str) or HEX64_RE.fullmatch(digest) is None
        ):
            raise ContentError(f"file hash is malformed: {path}")
        if digest is None and not deferred:
            raise ContentError(f"file hash is absent without deferred state: {path}")
        result[path] = item
    return result


def validate_accounts(manifest: dict[str, Any]) -> None:
    accounts = manifest.get("accounts")
    if not isinstance(accounts, dict):
        raise ContentError("account contract is absent")
    service = accounts.get("service")
    key_daemon = accounts.get("ssh_key_daemon")
    root = accounts.get("root")
    if not all(isinstance(item, dict) for item in (service, key_daemon, root)):
        raise ContentError("account identities are incomplete")
    if (
        service.get("name") != "a90svc"
        or service.get("uid") != SERVICE_UID
        or service.get("gid") != SERVICE_GID
        or service.get("login_eligible") is not True
        or service.get("home") != "/srv/a90-service"
        or service.get("shell") != "/usr/local/libexec/a90-probe"
        or key_daemon.get("name") != "a90key"
        or key_daemon.get("uid") != KEY_DAEMON_UID
        or key_daemon.get("gid") != KEY_DAEMON_GID
        or key_daemon.get("home") != "/var/empty"
        or key_daemon.get("shell") != "/usr/sbin/nologin"
        or key_daemon.get("login_eligible") is not False
        or root.get("name") != "root"
        or root.get("uid") != 0
        or root.get("gid") != 0
        or root.get("shell") != "/usr/sbin/nologin"
        or root.get("login_eligible") is not False
        or accounts.get("exact_identity_count") != 2
        or accounts.get("duplicate_names_or_ids") is not False
        or accounts.get("supplementary_groups") != []
        or accounts.get("service_shell_is_general_shell") is not False
    ):
        raise ContentError("account identity or login boundary is widened")
    nss = accounts.get("nss")
    if (
        not isinstance(nss, dict)
        or nss.get("account_sources") != ["files"]
        or nss.get("network_lookup") is not False
        or nss.get("pam") is not False
        or nss.get("source_lookup") is not False
        or accounts.get("database_files")
        != ["/etc/passwd", "/etc/group", "/etc/shadow", "/etc/nsswitch.conf", "/etc/shells"]
    ):
        raise ContentError("NSS/PAM/network account lookup is not closed")
    expected_account_files = {
        "/etc/passwd": (
            b"root:x:0:0:root:/nonexistent:/usr/sbin/nologin\n"
            b"a90svc:x:3301:3301:A90 service:/srv/a90-service:/usr/local/libexec/a90-probe\n"
            b"a90key:x:3302:3302:A90 SSH key daemon:/var/empty:/usr/sbin/nologin\n"
        ),
        "/etc/group": b"root:x:0:\na90svc:x:3301:\na90key:x:3302:\n",
        "/etc/shadow": (
            b"root:!*:0:0:99999:7:::\n"
            b"a90svc:!*:0:0:99999:7:::\n"
            b"a90key:!*:0:0:99999:7:::\n"
        ),
        "/etc/nsswitch.conf": b"passwd: files\ngroup: files\nshadow: files\nhosts: files\n",
        "/etc/shells": b"/usr/local/libexec/a90-probe\n",
    }
    if any(STATIC_TEXT[path] != data for path, data in expected_account_files.items()):
        raise ContentError("recipe account database bytes are not the exact closed set")


def validate_authorized_keys(manifest: dict[str, Any]) -> None:
    value = manifest.get("authorized_keys")
    if not isinstance(value, dict):
        raise ContentError("authorized_keys contract is absent")
    grammar = value.get("grammar")
    owner = value.get("owner")
    if not isinstance(grammar, dict) or not isinstance(owner, dict):
        raise ContentError("authorized_keys grammar/owner is incomplete")
    if (
        value.get("path") != "/srv/a90-service/.ssh/authorized_keys"
        or value.get("content") != "redacted-unbound"
        or value.get("root_authorization_path") is not False
        or value.get("key_bytes_tracked") is not False
        or grammar.get("canonical_one_line") is not True
        or grammar.get("line_count") != 1
        or grammar.get("algorithm") != "ssh-ed25519"
        or grammar.get("key_material") != "redacted-unbound"
        or grammar.get("comment") is not False
        or grammar.get("alternate_key_sources") is not False
        or grammar.get("extra_lines") is not False
        or grammar.get("shell_or_command_override") is not False
        or owner != {"uid": SERVICE_UID, "gid": SERVICE_GID, "mode": "0600"}
        or value.get("parent")
        != {"path": "/srv/a90-service/.ssh", "uid": SERVICE_UID, "gid": SERVICE_GID, "mode": "0700"}
        or value.get("home")
        != {
            "path": "/srv/a90-service",
            "uid": SERVICE_UID,
            "gid": SERVICE_GID,
            "mode": "0750",
            "read_only_before_exec": True,
        }
    ):
        raise ContentError("authorized_keys is not the canonical redacted one-line contract")
    options = grammar.get("options")
    if options != [
        'command="/usr/local/libexec/a90-probe --request=readiness"',
        "no-agent-forwarding",
        "no-port-forwarding",
        "no-X11-forwarding",
        "no-pty",
    ]:
        raise ContentError("authorized_keys restrictions changed")
    template = grammar.get("line_template")
    expected_template = ",".join(options) + " ssh-ed25519 <redacted-unbound>\n"
    if template != expected_template:
        raise ContentError("authorized_keys template is not one redacted line")


def validate_dropbear(manifest: dict[str, Any]) -> None:
    value = manifest.get("dropbear")
    if not isinstance(value, dict):
        raise ContentError("Dropbear contract is absent")
    build = value.get("build")
    launch = value.get("launch_contract")
    if (
        not isinstance(build, dict)
        or not isinstance(launch, dict)
        or value.get("path") != "/usr/sbin/dropbear"
        or value.get("binary_sha256") is not None
        and HEX64_RE.fullmatch(value["binary_sha256"]) is None
        or value.get("binary_state")
        not in {"deferred-missing-private-source", "materialized-private-not-authorized"}
    ):
        raise ContentError("Dropbear build/launch contract is incomplete")
    macros = build.get("feature_macros")
    if not isinstance(macros, dict):
        raise ContentError("Dropbear feature matrix is absent")
    required_false = {
        "DROPBEAR_SVR_PASSWORD_AUTH",
        "DROPBEAR_SVR_PAM_AUTH",
        "DROPBEAR_SVR_ROOTLOGIN",
        "DROPBEAR_SVR_AGENTFWD",
        "DROPBEAR_SVR_X11FWD",
        "DROPBEAR_SVR_LOCALTCPFWD",
        "DROPBEAR_SVR_REMOTETCPFWD",
        "DROPBEAR_SVR_PTY",
        "DROPBEAR_SVR_SUBSYSTEM",
        "DROPBEAR_SVR_HOSTKEYGEN",
    }
    if any(macros.get(name) is not False for name in required_false):
        raise ContentError("Dropbear prohibited feature is enabled in the matrix")
    if macros.get("DROPBEAR_SVR_PUBKEY_AUTH") is not True:
        raise ContentError("Dropbear public-key authentication is not enabled")
    required_matrix = {
        "password_auth": False,
        "empty_password_auth": False,
        "none_authentication": False,
        "keyboard_interactive_auth": False,
        "pam_auth": False,
        "public_key_auth": True,
        "root_login": False,
        "alternate_accounts": False,
        "alternate_authorized_key_sources": False,
        "general_shell": False,
        "arbitrary_command": False,
        "subsystem": False,
        "pty": False,
        "local_forwarding": False,
        "remote_forwarding": False,
        "agent_forwarding": False,
        "x11_forwarding": False,
        "host_key_generation": False,
    }
    if build.get("feature_matrix") != required_matrix:
        raise ContentError("Dropbear normalized feature matrix changed")
    if build.get("static") is not True or build.get("pam") is not False:
        raise ContentError("Dropbear static/PAM build binding changed")
    if (
        launch.get("foreground") is not True
        or launch.get("stderr_only_logging") is not True
        or any(
            launch.get(name) is not False
            for name in (
                "password",
                "empty_password",
                "none_authentication",
                "keyboard_interactive",
                "pam",
                "root_login",
                "alternate_accounts",
                "alternate_authorized_key_sources",
                "general_shell",
                "arbitrary_command",
                "subsystem",
                "pty",
                "local_forwarding",
                "remote_forwarding",
                "agent_forwarding",
                "x11_forwarding",
                "host_key_generation",
            )
        )
    ):
        raise ContentError("Dropbear launch feature matrix is widened")
    if build.get("source_path") != "workspace/private/inputs/a90-isolated-debian/dropbear-source":
        raise ContentError("Dropbear source path changed")
    if build.get("enforcement") != (
        "compile-time-feature-removal-required; runtime-only-disablement-is-not-accepted"
    ):
        raise ContentError("Dropbear feature-removal enforcement changed")
    configuration_hash = build.get("configuration_semantics_sha256")
    if configuration_hash is not None and HEX64_RE.fullmatch(configuration_hash) is None:
        raise ContentError("Dropbear configuration semantics hash is malformed")
    source_hash = build.get("source_sha256")
    if source_hash is not None and HEX64_RE.fullmatch(source_hash) is None:
        raise ContentError("Dropbear source hash is malformed")
    if (value.get("binary_sha256") is None) != (source_hash is None):
        raise ContentError("Dropbear binary/source materialization state is inconsistent")
    prohibited = (
        "password",
        "empty_password",
        "none_authentication",
        "keyboard_interactive",
        "pam",
        "root_login",
        "alternate_accounts",
        "alternate_authorized_key_sources",
        "general_shell",
        "arbitrary_command",
        "subsystem",
        "pty",
        "local_forwarding",
        "remote_forwarding",
        "agent_forwarding",
        "x11_forwarding",
        "host_key_generation",
    )
    if any(launch.get(name) is not False for name in prohibited):
        raise ContentError("Dropbear prohibited launch feature is enabled")
    if (
        value.get("non_privileged_port") != 2222
        or value.get("argv")
        != [
            "/usr/sbin/dropbear",
            "-F",
            "-E",
            "-s",
            "-w",
            "-j",
            "-k",
            "-a",
            "-p",
            "2222",
            "-r",
            "/etc/dropbear/dropbear_ed25519_host_key",
        ]
    ):
        raise ContentError("Dropbear argv or port changed")
    if value.get("session_contract") != {
        "account": "a90svc",
        "forced_dispatcher": "/usr/local/libexec/a90-probe",
        "accepted_client_key": "boot-private-ed25519-only",
        "non_pty": True,
        "max_sessions": 1,
        "max_request_bytes": 128,
        "max_output_bytes": 256,
    }:
        raise ContentError("Dropbear session contract changed")


def validate_manifest(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (
        manifest.get("supersedes") != "a90-h14-ufs-content-manifest-v1"
        or manifest.get("schema") != SCHEMA
        or manifest.get("candidate_eligible") is not False
        or manifest.get("device_install_authorized") is not False
        or manifest.get("selected_closure") != "NESTED_PID_NAMESPACE_ISOLATION"
        or manifest.get("status") not in {
            "h0-specification-deferred",
            "h0-materialized-private",
        }
    ):
        raise ContentError("content manifest carries candidate or installation authority")
    files = _manifest_files(manifest)
    if "/usr/sbin/dropbear" not in files:
        raise ContentError("Dropbear is missing from the content allowlist")
    absent = manifest.get("absent")
    if not isinstance(absent, list) or len(absent) != len(set(absent)):
        raise ContentError("absent list is not a unique list")
    if any(not isinstance(path, str) or not path.startswith("/") for path in absent):
        raise ContentError("absent list contains a non-canonical path")
    required_absent = {
        "/etc/a90-d3-firstboot",
        "/root/.ssh/authorized_keys",
        "/usr/bin/ip",
        "/usr/sbin/iw",
        "/usr/local/bin/a90-dpublic-smoke-httpd",
        "/usr/local/bin/a90-dpublic-hud-intent",
        "/usr/local/bin/a90-dpublic-hud-presenter",
        "/usr/local/bin/a90-dpublic-wifi-sta",
        "/usr/sbin/getty",
        "/usr/sbin/agetty",
        "/dev/console",
        "/dev/ttyGS0",
        "/dev/ptmx",
        "/dev/pts",
        "/dev/shm",
    }
    if not required_absent.issubset(absent):
        raise ContentError("forbidden content is missing from the absent list")
    if set(files) & set(absent):
        raise ContentError("a file is simultaneously present and absent")
    for path, data in STATIC_TEXT.items():
        record = files.get(path)
        if (
            record is None
            or record.get("sha256") != sha256_bytes(data)
            or record.get("size") != len(data)
        ):
            raise ContentError(f"static recipe source is not pinned exactly: {path}")
    forbidden = manifest.get("forbidden_content")
    if not isinstance(forbidden, dict) or any(value is not False for value in forbidden.values()):
        raise ContentError("forbidden-content assertions are not closed")
    validate_accounts(manifest)
    validate_authorized_keys(manifest)
    validate_dropbear(manifest)
    dropbear_record = files["/usr/sbin/dropbear"]
    dropbear_hash = manifest["dropbear"]["binary_sha256"]
    if dropbear_hash is None:
        if dropbear_record.get("sha256") is not None or dropbear_record.get("size") is not None:
            raise ContentError("deferred Dropbear record carries a partial binary pin")
    elif (
        dropbear_record.get("sha256") != dropbear_hash
        or not isinstance(dropbear_record.get("size"), int)
        or dropbear_record.get("artifact_state") is not None
    ):
        raise ContentError("materialized Dropbear record does not match its binary binding")
    bootstrap = manifest.get("bootstrap_owned")
    host_key_tree = bootstrap.get("server_host_key_tree") if isinstance(bootstrap, dict) else None
    auth_tmpfs = bootstrap.get("service_authorization_tmpfs") if isinstance(bootstrap, dict) else None
    veth_peer = bootstrap.get("veth_peer") if isinstance(bootstrap, dict) else None
    if (
        not isinstance(host_key_tree, dict)
        or host_key_tree.get("path") != "/etc/dropbear"
        or host_key_tree.get("uid") != KEY_DAEMON_UID
        or host_key_tree.get("gid") != KEY_DAEMON_GID
        or host_key_tree.get("mode") != "0700"
        or host_key_tree.get("private_key_mode") != "0400"
        or host_key_tree.get("per_boot_ed25519") is not True
        or host_key_tree.get("rootfs_creates_or_rotates") is not False
        or host_key_tree.get("rootfs_traverses_or_reads") is not False
        or host_key_tree.get("rootfs_inherits") is not False
        or host_key_tree.get("read_only_before_exec") is not True
        or auth_tmpfs
        != {
            "path": "/srv/a90-service/.ssh",
            "source": "trusted-bootstrap-boot-private-key",
            "rootfs_creates_or_rotates": False,
            "read_only_before_exec": True,
        }
        or veth_peer
        != {"source": "trusted-native-bootstrap", "rootfs_configures": False}
    ):
        raise ContentError("trusted-bootstrap ownership boundary changed")
    probe = manifest.get("probe_dispatcher")
    if (
        not isinstance(probe, dict)
        or probe.get("read_only") is not True
        or probe.get("general_shell") is not False
        or probe.get("arbitrary_command") is not False
        or probe.get("subsystem") is not False
        or probe.get("max_request_bytes") != 128
        or probe.get("max_output_bytes") != 256
    ):
        raise ContentError("probe dispatcher grammar or bounds are widened")
    writable = manifest.get("writable_tmpfs")
    if writable != [
        {
            "path": "/run/a90",
            "uid": SERVICE_UID,
            "gid": SERVICE_GID,
            "mode": "0755",
            "max_bytes": 4096,
            "max_inodes": 4,
            "allowed_paths": ["/run/a90/workload.ready"],
            "rootfs_creates_mount": False,
        }
    ]:
        raise ContentError("writable tmpfs set changed")
    return files


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _private_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PRIVATE_ROOT)
    except ValueError as exc:
        raise ContentError(f"{label} must stay below workspace/private") from exc
    return resolved


def compile_components(build_dir: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    compiler = shutil.which("aarch64-linux-gnu-gcc")
    if compiler is None:
        raise DeferredInput("aarch64-linux-gnu-gcc is unavailable")
    build_dir.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update({"LC_ALL": "C", "SOURCE_DATE_EPOCH": str(SOURCE_DATE_EPOCH), "TZ": "UTC"})
    prefix_flags = (
        f"-ffile-prefix-map={REPO_ROOT}=/a90-source",
        f"-fdebug-prefix-map={REPO_ROOT}=/a90-source",
    )
    flags = [*COMPILER_FLAGS[:5], *prefix_flags, *COMPILER_FLAGS[5:]]
    result: dict[str, Path] = {}
    for path, (name, source) in COMPONENTS.items():
        source = source.resolve(strict=True)
        output = build_dir / name
        _run([compiler, *flags, str(source), "-o", str(output)], env=env)
        file_tool = shutil.which("file")
        if file_tool is None:
            raise DeferredInput("file is unavailable for ARM64 artifact verification")
        description = subprocess.check_output([file_tool, "-b", str(output)], text=True)
        if "ARM aarch64" not in description or "static-pie linked" not in description:
            raise ContentError(f"{path} did not produce a static ARM64 PIE: {description.strip()}")
        result[path] = output
    expected = _manifest_files(manifest)
    for path, output in result.items():
        record = expected[path]
        if record.get("sha256") != sha256_file(output) or record.get("size") != output.stat().st_size:
            raise ContentError(f"tracked component pin does not match the reproducible build: {path}")
    return result


def _safe_extract(source: Path, destination: Path) -> Path:
    if source.is_dir():
        return source
    if not source.is_file() or not tarfile.is_tarfile(source):
        raise ContentError("Dropbear source must be a directory or local tar archive")
    with tarfile.open(source, "r:*") as archive:
        members = archive.getmembers()
        for member in members:
            member_path = (destination / member.name).resolve()
            try:
                member_path.relative_to(destination.resolve())
            except ValueError as exc:
                raise ContentError("Dropbear source archive escapes its private staging directory") from exc
            if member.issym() or member.islnk():
                raise ContentError("Dropbear source archive may not contain links")
            if not member.isdir() and not member.isfile():
                raise ContentError("Dropbear source archive may not contain special files")
        archive.extractall(destination)
    roots = sorted(path for path in destination.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise ContentError("Dropbear source archive must contain one source directory")
    return roots[0]


def _source_tree_digest(root: Path) -> str:
    entries: list[str] = []
    for path in [root, *sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())]:
        relative = "." if path == root else path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            entries.append(f"D:{relative}:{stat.S_IMODE(info.st_mode):o}")
        elif stat.S_ISREG(info.st_mode):
            entries.append(
                f"F:{relative}:{stat.S_IMODE(info.st_mode):o}:{info.st_size}:{sha256_file(path)}"
            )
        else:
            raise ContentError("Dropbear source tree may not contain links or special files")
    return sha256_bytes("\n".join(entries).encode("utf-8"))


def build_dropbear(source: Path, build_dir: Path, manifest: dict[str, Any]) -> tuple[Path, str]:
    source = _private_path(source, "Dropbear source")
    if not source.exists():
        raise DeferredInput(
            "private pinned Dropbear source is absent; exact binary/configuration hashes remain deferred"
        )
    with tempfile.TemporaryDirectory(prefix="a90-dropbear-build-") as temporary:
        staging = Path(temporary) / "source"
        if source.is_dir():
            shutil.copytree(source, staging, symlinks=True)
            if any(path.is_symlink() for path in staging.rglob("*")):
                raise ContentError("Dropbear source tree may not contain links")
        else:
            staging.mkdir()
            staging = _safe_extract(source, staging)
        source_digest = _source_tree_digest(staging)
        configure = staging / "configure"
        makefile = staging / "Makefile"
        if not configure.is_file() and not makefile.is_file():
            raise ContentError("Dropbear source has no configure script or Makefile")
        config_header = Path(temporary) / "a90_dropbear_feature_config.h"
        config_header.write_text(
            "\n".join(
                [
                    "#define DROPBEAR_SVR_PASSWORD_AUTH 0",
                    "#define DROPBEAR_SVR_PAM_AUTH 0",
                    "#define DROPBEAR_SVR_PUBKEY_AUTH 1",
                    "#define DROPBEAR_SVR_ROOTLOGIN 0",
                    "#define DROPBEAR_SVR_AGENTFWD 0",
                    "#define DROPBEAR_SVR_X11FWD 0",
                    "#define DROPBEAR_SVR_LOCALTCPFWD 0",
                    "#define DROPBEAR_SVR_REMOTETCPFWD 0",
                    "#define DROPBEAR_SVR_PTY 0",
                    "#define DROPBEAR_SVR_SUBSYSTEM 0",
                    "#define DROPBEAR_SVR_HOSTKEYGEN 0",
                    "",
                ]
            ),
            encoding="ascii",
        )
        env = os.environ.copy()
        env.update(
            {
                "CC": "aarch64-linux-gnu-gcc",
                "AR": "aarch64-linux-gnu-ar",
                "RANLIB": "aarch64-linux-gnu-ranlib",
                "CFLAGS": "-O2 -fPIE -static-pie -fno-ident -ffile-prefix-map="
                f"{REPO_ROOT}=/a90-source",
                "CPPFLAGS": f"-include {config_header}",
                "LDFLAGS": "-static-pie -Wl,--build-id=none",
                "SOURCE_DATE_EPOCH": str(SOURCE_DATE_EPOCH),
                "LC_ALL": "C",
                "TZ": "UTC",
            }
        )
        if configure.is_file():
            _run(
                [
                    str(configure),
                    "--host=aarch64-linux-gnu",
                    "--disable-pam",
                    "--disable-zlib",
                ],
                cwd=staging,
                env=env,
            )
        _run(["make", "-j1", "dropbear"], cwd=staging, env=env)
        candidate = staging / "dropbear"
        if not candidate.is_file():
            raise ContentError("Dropbear build did not produce the bound server binary")
        output = build_dir / "dropbear"
        shutil.copyfile(candidate, output)
        output.chmod(0o755)
        return output, source_digest


def _mkdir(path: Path, mode: int = 0o755) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode)


def _write_file(path: Path, data: bytes, mode: int) -> None:
    _mkdir(path.parent)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)


def _copy_file(source: Path, destination: Path, mode: int) -> None:
    _mkdir(destination.parent)
    with source.open("rb") as input_stream, destination.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    destination.chmod(mode)


def _record_for(files: dict[str, dict[str, Any]], path: str) -> dict[str, Any]:
    try:
        return files[path]
    except KeyError as exc:
        raise ContentError(f"recipe source is not in the manifest allowlist: {path}") from exc


def materialize_tree(
    manifest: dict[str, Any],
    files: dict[str, dict[str, Any]],
    component_outputs: dict[str, Path],
    dropbear_output: Path,
    output: Path,
) -> Path:
    # The output root's absence is enforced once in build(), before it creates
    # the component and Dropbear build directories inside it. Re-checking the
    # root here can never pass on a real build; the tree this function owns is
    # the rootfs subdirectory, so that is what must be absent.
    rootfs = output / "rootfs"
    if rootfs.exists() or rootfs.is_symlink():
        raise ContentError(f"private output must be absent: {rootfs}")
    _mkdir(rootfs, 0o755)
    for path, data in STATIC_TEXT.items():
        record = _record_for(files, path)
        if sha256_bytes(data) != record.get("sha256") or len(data) != record.get("size"):
            raise ContentError(f"static text does not match its manifest pin: {path}")
        _write_file(rootfs / path.lstrip("/"), data, int(record["mode"], 8))
    for path, source in component_outputs.items():
        record = _record_for(files, path)
        _copy_file(source, rootfs / path.lstrip("/"), int(record["mode"], 8))
    dropbear_record = _record_for(files, "/usr/sbin/dropbear")
    if sha256_file(dropbear_output) != dropbear_record.get("sha256"):
        raise ContentError("Dropbear output does not match the refreshed manifest pin")
    _copy_file(dropbear_output, rootfs / "usr/sbin/dropbear", 0o755)

    for directory, mode in (
        ("etc", 0o755),
        ("usr", 0o755),
        ("usr/bin", 0o755),
        ("usr/lib", 0o755),
        ("usr/local", 0o755),
        ("usr/local/libexec", 0o755),
        ("usr/sbin", 0o755),
        ("srv", 0o755),
        ("srv/a90-service", 0o750),
        ("var", 0o755),
        ("var/empty", 0o700),
        ("dev", 0o755),
        ("run", 0o755),
    ):
        _mkdir(rootfs / directory, mode)
    for link, target in manifest["usrmerge_symlinks"].items():
        link_path = rootfs / link.lstrip("/")
        _mkdir(link_path.parent)
        link_path.symlink_to(target)

    absent = set(manifest["absent"])
    for path in absent:
        if os.path.lexists(rootfs / path.lstrip("/")):
            raise ContentError(f"forbidden path materialized: {path}")
    for path in ("/root/.ssh/authorized_keys", "/etc/dropbear/dropbear_ed25519_host_key"):
        if os.path.lexists(rootfs / path.lstrip("/")):
            raise ContentError(f"private authorization/key path materialized: {path}")
    validate_tree(rootfs, files, manifest)
    return rootfs


def validate_tree(rootfs: Path, files: dict[str, dict[str, Any]], manifest: dict[str, Any]) -> None:
    expected = set(files)
    actual_regular: set[str] = set()
    actual_links: set[str] = set()
    allowed_dirs = {
        "/etc",
        "/usr",
        "/usr/bin",
        "/usr/lib",
        "/usr/local",
        "/usr/local/libexec",
        "/usr/sbin",
        "/srv",
        "/srv/a90-service",
        "/var",
        "/var/empty",
        "/dev",
        "/run",
    }
    structural_modes = {"/srv/a90-service": 0o750, "/var/empty": 0o700}
    for path in sorted(rootfs.rglob("*")):
        relative = "/" + path.relative_to(rootfs).as_posix()
        info = path.lstat()
        if stat.S_ISREG(info.st_mode):
            actual_regular.add(relative)
            if relative not in expected:
                raise ContentError(f"unlisted regular file in rootfs: {relative}")
            if info.st_mode & (stat.S_ISUID | stat.S_ISGID):
                raise ContentError(f"setuid/setgid file in rootfs: {relative}")
            record = files[relative]
            if stat.S_IMODE(info.st_mode) != int(record["mode"], 8):
                raise ContentError(f"rootfs file mode drift: {relative}")
            if record.get("sha256") is None or sha256_file(path) != record["sha256"]:
                raise ContentError(f"rootfs file hash drift: {relative}")
            if info.st_size != record["size"]:
                raise ContentError(f"rootfs file size drift: {relative}")
        elif stat.S_ISLNK(info.st_mode):
            actual_links.add(relative)
            expected_target = manifest["usrmerge_symlinks"].get(relative)
            if expected_target is None or os.readlink(path) != expected_target:
                raise ContentError(f"unlisted symlink in rootfs: {relative}")
        elif stat.S_ISDIR(info.st_mode):
            if relative not in allowed_dirs:
                raise ContentError(f"unlisted directory in rootfs: {relative}")
            expected_mode = structural_modes.get(relative, 0o755)
            if stat.S_IMODE(info.st_mode) != expected_mode:
                raise ContentError(f"rootfs directory mode drift: {relative}")
        else:
            raise ContentError(f"special file in rootfs: {relative}")
    if actual_regular != expected:
        raise ContentError(f"rootfs regular-file set mismatch: {sorted(actual_regular ^ expected)}")
    if actual_links != set(manifest["usrmerge_symlinks"]):
        raise ContentError(f"rootfs usrmerge link set mismatch: {sorted(actual_links)}")


def deterministic_tar(rootfs: Path, destination: Path, manifest: dict[str, Any]) -> None:
    with tarfile.open(destination, "w", format=tarfile.USTAR_FORMAT) as archive:
        entries = [rootfs]
        entries.extend(sorted(rootfs.rglob("*"), key=lambda item: item.relative_to(rootfs).as_posix()))
        for path in entries:
            relative = "." if path == rootfs else path.relative_to(rootfs).as_posix()
            info = path.lstat()
            tar_info = tarfile.TarInfo(relative)
            tar_info.mode = stat.S_IMODE(info.st_mode)
            tar_info.uid = 0
            tar_info.gid = 0
            if relative == "srv/a90-service":
                tar_info.uid = SERVICE_UID
                tar_info.gid = SERVICE_GID
                tar_info.mode = 0o750
            elif relative == "var/empty":
                tar_info.uid = KEY_DAEMON_UID
                tar_info.gid = KEY_DAEMON_GID
                tar_info.mode = 0o700
            tar_info.mtime = SOURCE_DATE_EPOCH
            if stat.S_ISDIR(info.st_mode):
                tar_info.type = tarfile.DIRTYPE
                archive.addfile(tar_info)
            elif stat.S_ISLNK(info.st_mode):
                tar_info.type = tarfile.SYMTYPE
                tar_info.linkname = os.readlink(path)
                tar_info.mode = 0o777
                archive.addfile(tar_info)
            else:
                tar_info.type = tarfile.REGTYPE
                tar_info.size = info.st_size
                with path.open("rb") as stream:
                    archive.addfile(tar_info, stream)


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def refreshed_manifest(
    manifest: dict[str, Any],
    dropbear_output: Path,
    dropbear_source_sha256: str,
) -> dict[str, Any]:
    value = copy.deepcopy(manifest)
    value["status"] = "h0-materialized-private"
    value["dropbear"]["binary_sha256"] = sha256_file(dropbear_output)
    value["dropbear"]["binary_state"] = "materialized-private-not-authorized"
    value["dropbear"]["build"]["source_sha256"] = dropbear_source_sha256
    # The digest covers the configuration, so it must exclude the field that
    # carries the digest itself. Hashing the whole build dict fed each build's
    # result into the next one, so the manifest never reached a fixed point and
    # every rebuild produced a spurious diff against the reviewed value.
    configuration_semantics = {
        key: item
        for key, item in value["dropbear"]["build"].items()
        if key != "configuration_semantics_sha256"
    }
    value["dropbear"]["build"]["configuration_semantics_sha256"] = sha256_bytes(
        json.dumps(configuration_semantics, sort_keys=True, separators=(",", ":")).encode()
    )
    value["source_inputs"]["dropbear"]["sha256"] = dropbear_source_sha256
    value["source_inputs"]["dropbear"]["state"] = "materialized-private"
    for item in value["files"]:
        if item.get("path") == "/usr/sbin/dropbear":
            item["sha256"] = sha256_file(dropbear_output)
            item["size"] = dropbear_output.stat().st_size
            item.pop("artifact_state", None)
    value["deferred"] = [
        item for item in value["deferred"] if item.get("item") != "dropbear-feature-removed-binary"
    ]
    return value


def build(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_manifest(args.manifest)
    files = validate_manifest(manifest)
    dropbear_source = _private_path(args.dropbear_source, "Dropbear source")
    if not dropbear_source.exists():
        raise DeferredInput(
            "private pinned Dropbear source is absent; exact binary/configuration hashes remain deferred"
        )
    output = _private_path(args.output, "output")
    if output.exists() or output.is_symlink():
        raise ContentError(f"private output must be absent: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    build_dir = output / "component-build"
    components = compile_components(build_dir, manifest)
    dropbear_dir = output / "dropbear-build"
    dropbear_dir.mkdir()
    dropbear_output, source_sha256 = build_dropbear(
        dropbear_source,
        dropbear_dir,
        manifest,
    )
    if manifest["dropbear"]["binary_sha256"] is None and not args.write_manifest:
        raise ContentError(
            "Dropbear was built but the tracked manifest is still deferred; rerun with --write-manifest"
        )
    if args.write_manifest:
        manifest = refreshed_manifest(manifest, dropbear_output, source_sha256)
        write_json(args.manifest, manifest)
        files = validate_manifest(manifest)
    rootfs = materialize_tree(manifest, files, components, dropbear_output, output)
    tar_path = output / "content.tar"
    deterministic_tar(rootfs, tar_path, manifest)
    receipt = {
        "schema": "a90-isolated-debian-content-build-receipt-v2",
        "manifest": str(args.manifest.resolve().relative_to(REPO_ROOT)),
        "manifest_sha256": sha256_file(args.manifest.resolve()),
        "manifest_semantic_sha256": sha256_bytes(canonical_json(manifest)),
        "content_tar": str(tar_path.relative_to(REPO_ROOT)),
        "content_tar_sha256": sha256_file(tar_path),
        "files": {
            path: {
                "size": (rootfs / path.lstrip("/")).stat().st_size,
                "sha256": sha256_file(rootfs / path.lstrip("/")),
            }
            for path in sorted(files)
        },
        "candidate_authority": False,
        "device_contact": False,
        "device_write": False,
        "installation_authorized": False,
        "trace": manifest["toolchain"]["trace"],
        "deferred": manifest["deferred"],
    }
    write_json(output / "receipt.json", receipt)
    return receipt


def audit(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_manifest(args.manifest)
    files = validate_manifest(manifest)
    return {
        "schema": manifest["schema"],
        "status": manifest["status"],
        "file_count": len(files),
        "deferred_count": len(manifest["deferred"]),
        "candidate_eligible": manifest["candidate_eligible"],
        "device_install_authorized": manifest["device_install_authorized"],
        "dropbear_hash_bound": manifest["dropbear"]["binary_sha256"] is not None,
        "trace_attempted": False,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--dropbear-source", type=Path, default=DEFAULT_DROPBEAR_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", action="store_true", help="validate only; write nothing")
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="after a successful private Dropbear build, refresh its exact public hash binding",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.audit:
            print(json.dumps(audit(args), sort_keys=True))
        else:
            print(json.dumps(build(args), sort_keys=True))
    except DeferredInput as exc:
        print(f"DEFERRED: {exc}", file=sys.stderr)
        return 2
    except (ContentError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
