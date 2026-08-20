#!/usr/bin/env python3
"""Generate the single FD-executed A90 boot-only F1 helper package."""

from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "a90_boot_only_f1_source_package_v1.py"
MEMBERS = (
    "_workspace_bootstrap.py",
    "a90_transition_contract_v2.py",
    "a90_observation_pipeline.py",
    "a90_serial_lock.py",
    "a90ctl.py",
    "native_init_flash.py",
    "serial_tcp_bridge.py",
)


RUNTIME = r'''

LOCK_ROOT = Path("/home/temmie/.a90-boot-only-f1-owner-v1")
VIRTUAL_ROOT = "/a90-boot-only-f1-source-package-v1"
MODULE_ORDER = (
    ("_workspace_bootstrap", "_workspace_bootstrap.py"),
    ("a90_transition_contract_v2", "a90_transition_contract_v2.py"),
    ("a90_observation_pipeline", "a90_observation_pipeline.py"),
    ("a90_serial_lock", "a90_serial_lock.py"),
    ("a90ctl", "a90ctl.py"),
)
COMMANDS = {
    "version": ("version",),
    "selftest": ("selftest",),
    "status": ("status",),
    "boot-id": ("cat", "/proc/sys/kernel/random/boot_id"),
}
MAX_OUTPUT_BYTES = 1 << 20


def _member(name: str) -> bytes:
    try:
        expected_size, expected_sha256, encoded = MEMBERS[name]
    except KeyError as exc:
        raise RuntimeError("A90 source package member is unknown") from exc
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError("A90 source package member encoding is invalid") from exc
    if len(raw) != expected_size:
        raise RuntimeError("A90 source package member size mismatch")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise RuntimeError("A90 source package member digest mismatch")
    return raw


def _load_module(module_name: str, file_name: str) -> types.ModuleType:
    if module_name in sys.modules:
        raise RuntimeError(f"A90 source package module was preloaded: {module_name}")
    virtual_path = f"{VIRTUAL_ROOT}/{file_name}"
    module = types.ModuleType(module_name)
    module.__file__ = virtual_path
    module.__package__ = ""
    module.__cached__ = None
    sys.modules[module_name] = module
    try:
        exec(
            compile(_member(file_name), virtual_path, "exec", dont_inherit=True),
            module.__dict__,
        )
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


def _dependencies() -> dict[str, types.ModuleType]:
    original_path = tuple(sys.path)
    loaded: dict[str, types.ModuleType] = {}
    for module_name, file_name in MODULE_ORDER:
        module = _load_module(module_name, file_name)
        loaded[module_name] = module
        if module_name == "_workspace_bootstrap":
            module.repo_root = lambda: LOCK_ROOT
    if tuple(sys.path) != original_path:
        raise RuntimeError("A90 source package changed sys.path")
    loaded["a90_serial_lock"].repo_root = lambda: LOCK_ROOT
    loaded["a90_serial_lock"].DEFAULT_LOCK_REL = "a90-serial-bridge.lock"
    return loaded


def _exec_main(file_name: str, arguments: list[str]) -> None:
    virtual_path = f"{VIRTUAL_ROOT}/{file_name}"
    sys.argv = [virtual_path, *arguments]
    namespace = {
        "__name__": "__main__",
        "__file__": virtual_path,
        "__package__": None,
        "__cached__": None,
    }
    exec(
        compile(_member(file_name), virtual_path, "exec", dont_inherit=True),
        namespace,
    )


def _command(arguments: list[str]) -> int:
    if len(arguments) != 2 or arguments[0] not in COMMANDS:
        raise RuntimeError("A90 source package received an unknown command")
    try:
        timeout_sec = int(arguments[1], 10)
    except ValueError as exc:
        raise RuntimeError("A90 source package timeout is not an integer") from exc
    if not 1 <= timeout_sec <= 300:
        raise RuntimeError("A90 source package timeout is outside its bound")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    loaded = _dependencies()
    command = list(COMMANDS[arguments[0]])
    result = loaded["a90ctl"].run_cmdv1_command(
        "127.0.0.1",
        54321,
        float(timeout_sec),
        command,
        retry_unsafe=False,
        input_mode="normal",
        require_prompt_after_end=True,
    )
    print(
        json.dumps(
            {
                "command": command,
                "rc": result.rc,
                "status": result.status,
                "text": result.text,
            },
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )
    return 0 if result.rc == 0 and result.status == "ok" else 1


def main() -> int:
    if not sys.flags.isolated or not sys.flags.safe_path:
        raise RuntimeError("A90 source package requires isolated safe-path mode")
    if globals().get("__a90_bootstrap_fd_bound__") is not True:
        raise RuntimeError("A90 source package requires inherited-FD execution")
    if len(sys.argv) < 2:
        raise RuntimeError("A90 source package mode is absent")
    mode = sys.argv[1]
    arguments = sys.argv[2:]
    if mode == "bridge":
        _exec_main("serial_tcp_bridge.py", arguments)
        return 0
    if mode == "command":
        return _command(arguments)
    if mode == "flash":
        _dependencies()
        _exec_main("native_init_flash.py", arguments)
        return 0
    raise RuntimeError("A90 source package mode is unknown")


if __name__ == "__main__":
    raise SystemExit(main())
'''


def render() -> bytes:
    lines = [
        "#!/usr/bin/env python3",
        '"""Generated single-source runtime package for the A90 boot-only F1 owner.',
        "",
        "Regenerate with build_a90_boot_only_f1_source_package_v1.py.  The parent",
        "executes these exact bytes only through its inherited-FD loader.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import base64",
        "import binascii",
        "import hashlib",
        "import json",
        "import resource",
        "import sys",
        "import types",
        "from pathlib import Path",
        "",
        "",
        "MEMBERS = {",
    ]
    for name in MEMBERS:
        raw = (HERE / name).read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        lines.append(f"    {name!r}: (")
        lines.append(f"        {len(raw)},")
        lines.append(f"        {hashlib.sha256(raw).hexdigest()!r},")
        for offset in range(0, len(encoded), 88):
            lines.append(f"        {encoded[offset:offset + 88]!r}")
        lines.append("    ),")
    lines.append("}")
    lines.append(RUNTIME.strip("\n"))
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    expected = render()
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != expected:
            raise SystemExit("A90 source package is stale")
        return 0
    args.output.write_bytes(expected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
