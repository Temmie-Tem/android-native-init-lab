#!/usr/bin/env python3
"""P345 host-only Image/AP joins; Image identity-only, userspace NOT unchanged.

Reuse the exact P344 Image and packaging validators, not its runtime claims.
The new read-only child, authenticated cancellation and drain implementation
must be independently built and supplied to the AP join as exact init bytes.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import types
from typing import Any

import s22plus_fyg8_p344_artifact_identity as predecessor

ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(predecessor.__file__).resolve()
SOURCE_IDENTITY = {"size": 17369, "sha256": "6578805fa29dd677eba383eb85ed1fcb05c3693a4ea4fbd1e89e5daf28a400a7"}
P344_IMAGE = ROOT / "workspace/private/outputs/s22plus_fyg8_p344/stock-candidate-build-v1-20260905-01/inputs/fixed-Image"
P344_IMAGE_IDENTITY = dict(predecessor.P344_IMAGE_IDENTITY)
P344_AP_IDENTITY = dict(predecessor.P344_AP_IDENTITY)
P344_PREDECESSOR_RUN_ID_HEX = predecessor.P344_RUN_ID_HEX
P344_PREDECESSOR_RUN_ID = predecessor.P344_RUN_ID
P345_RUN_ID_HEX = "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a"
P345_RUN_ID = bytes.fromhex(P345_RUN_ID_HEX)
P345_IMAGE_IDENTITY = {"size": 41490944, "sha256": "b937b2aeb9d1b70a7b1a2de891412a94415960b91de7494cffd51fa1d0897ccf"}
# AP identity is supplied by the fresh build result, never the consumed AP.
P345_AP_IDENTITY = None

_FUNCTIONS = frozenset(("identity", "stable_bytes", "_gzip_config", "_config_values",
    "_section_receipts", "_recompress_config", "_stale_counts", "validate_image",
    "transform_image", "_validate_init", "inspect_ap", "validate_rollback_ap"))
_source = predecessor.stable_bytes(SOURCE, "P344 artifact source", expected=SOURCE_IDENTITY, nlink=1)
_tree = ast.parse(_source, filename=str(SOURCE))
_selected = [node for node in _tree.body if isinstance(node, ast.FunctionDef) and node.name in _FUNCTIONS]
if {node.name for node in _selected} != _FUNCTIONS:
    raise ValueError("P344 artifact validator function set differs")
_bound = types.ModuleType("_p345_artifact_validators")
_bound.__dict__.update(vars(predecessor))
_bound.__dict__.update(globals())
_bound.predecessor = predecessor
_bound._INNER = predecessor._INNER
_bound.P345_UNSAT_TAG_HEX = predecessor.P344_UNSAT_TAG_HEX
_bound.STALE_AP_IDENTITIES = tuple(predecessor.STALE_AP_IDENTITIES) + (P344_AP_IDENTITY,)
_text = ast.unparse(ast.Module(body=_selected, type_ignores=[]))
# Simultaneous namespaced projection; no import or module-global mutation.
_text = _text.replace("P344", "__CURRENT__").replace("p344", "__current__")
_text = _text.replace("P343", "P344").replace("p343", "p344")
_text = _text.replace("__CURRENT__", "P345").replace("__current__", "p345")
exec(compile(_text, str(SOURCE) + "#p345-image-ap", "exec", dont_inherit=True), _bound.__dict__)
for _name in _FUNCTIONS:
    globals()[_name] = getattr(_bound, _name)
ArtifactIdentityError = predecessor.ArtifactIdentityError
STALE_AP_IDENTITIES = _bound.STALE_AP_IDENTITIES


def validate_p345_identity() -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p345_artifact_identity_v1",
        "run_id_hex": P345_RUN_ID_HEX,
        "predecessor_run_id_rejected": P344_PREDECESSOR_RUN_ID_HEX,
        "predecessor_ap_identity_rejected": dict(P344_AP_IDENTITY),
        "image_identity": dict(P345_IMAGE_IDENTITY),
        "ap_identity": None,
        "ap_identity_owner": "fresh build result and actual AP join",
        "boot_only": True, "ab_must_match": True,
        "image_delta_identity_only": True, "runtime_delta_identity_only": False,
        "runtime_behavior_unchanged": False, "catalog_unchanged": False,
        "read_only_child_required": True, "authenticated_cancel": True,
        "bounded_descendant_drain": True,
        "initial_session_count": 5, "same_fd_session_count": 5,
        "initial_reconnect_count": 0, "idle_seconds": 0,
        "later_action_lease_active": False, "mandatory_rollback": True,
        "device_contact": False, "live_authorized": False,
    }


def __getattr__(name: str) -> Any:
    return getattr(predecessor, name)
