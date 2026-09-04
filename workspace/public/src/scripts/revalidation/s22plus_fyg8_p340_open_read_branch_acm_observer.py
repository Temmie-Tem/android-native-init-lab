"""P340 binds the existing rejected-header parser and initial collector.

The P339 parser is exact-loaded privately with the new run namespace. The
initial collector additionally retains its four failure diagnostic frames;
the protocol, successful session proof and authentication stay unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_open_failure_capture as capture
import s22plus_fyg8_p340_open_read_branch_runtime as runtime


SOURCE = Path(__file__).with_name("s22plus_fyg8_p339_open_read_branch_acm_observer.py")
SOURCE_IDENTITY = {
    "size": 11714,
    "sha256": "eef5a9c75a289716b254d418afd574f20b0bca1ca332ebbe6ee4bd667bd13e54",
}
SCHEMA = "s22plus-fyg8-p340-open-header-capture-acm-session-v1"
CONTRACT_ID = "s22plus-fyg8-p340-open-header-capture-acm-observer-v1"
P340_RUN_ID_HEX = runtime.P340_RUN_ID_HEX
P340_RUN_ID = runtime.P340_RUN_ID
DEVICE_BANNER = runtime.DEVICE_BANNER
DEFAULT_COMMANDS = tuple(runtime.DEFAULT_COMMANDS)


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


_payload = SOURCE.read_bytes()
if identity(_payload) != SOURCE_IDENTITY:
    raise ValueError("P340 predecessor parser source identity differs")
_parser = types.ModuleType("s22plus_fyg8_p339_parser_bound_for_p340")
_parser.__file__ = str(SOURCE)
exec(compile(_payload, str(SOURCE), "exec", dont_inherit=True), _parser.__dict__)
_parser.runtime = runtime
_parser.P339_RUN_ID_HEX = P340_RUN_ID_HEX
_parser.P339_RUN_ID = P340_RUN_ID
_parser.DEVICE_BANNER = DEVICE_BANNER
_parser.DEFAULT_COMMANDS = DEFAULT_COMMANDS
_parser.SCHEMA = SCHEMA
_parser.CONTRACT_ID = CONTRACT_ID
P340ObserverBindingError = _parser.P339ObserverBindingError
AuthObserverError = P340ObserverBindingError
install_initial_capture = capture.install


def audit_binding() -> dict[str, Any]:
    if identity(SOURCE.read_bytes()) != SOURCE_IDENTITY:
        raise P340ObserverBindingError("P340 predecessor parser source changed")
    return _parser.audit_binding() | {
        "parser_source": dict(SOURCE_IDENTITY),
        "initial_failure_suffix_capture": True,
        "maximum_failure_suffix_bytes": 96,
        "capture_source": identity(Path(capture.__file__).read_bytes()),
    }


def __getattr__(name: str) -> Any:
    return getattr(_parser, name)
