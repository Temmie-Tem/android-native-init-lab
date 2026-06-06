#!/usr/bin/env python3
"""V476 observed runtime property-context overlay dry-run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_property_runtime_overlay_v471 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v476-observed-runtime-property-context-overlay")

_BASE_BUILD_MANIFEST = base.build_manifest
_BASE_RENDER_SUMMARY = base.render_summary


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _BASE_BUILD_MANIFEST(args, store)
    manifest["decision"] = str(manifest["decision"]).replace(
        "v471-extended-private-property-runtime",
        "v476-observed-runtime-property-context",
    )
    manifest["next_step"] = (
        "deploy under an Android-readable private property root and rerun Samsung registration proof"
    )
    manifest["observed_runtime_key_count"] = len(base.RUNTIME_OBSERVED_KEYS)
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return _BASE_RENDER_SUMMARY(manifest).replace(
        "# V471 Extended Private Property Runtime Overlay Dry-run",
        "# V476 Observed Runtime Property-Context Overlay Dry-run",
        1,
    )


base.build_manifest = build_manifest
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
