"""Unified evidence bundle helpers."""

from __future__ import annotations

import stat
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


@dataclass
class BundleFile:
    path: str
    size: int
    mode: str
    mtime: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_bundle_files(store: EvidenceStore) -> list[BundleFile]:
    files: list[BundleFile] = []
    for path in sorted(store.run_dir.rglob("*")):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink in evidence bundle: {path}")
        if not stat.S_ISREG(info.st_mode):
            continue
        files.append(
            BundleFile(
                path=str(path.relative_to(store.run_dir)),
                size=info.st_size,
                mode=oct(stat.S_IMODE(info.st_mode)),
                mtime=info.st_mtime,
            )
        )
    return files


def render_bundle_readme(manifest: dict[str, Any]) -> str:
    return "".join([
        "# A90 Native Init Evidence Bundle\n\n",
        f"- label: `{manifest.get('label')}`\n",
        f"- result: `{'PASS' if manifest.get('pass') else 'FAIL'}`\n",
        f"- created_utc: `{manifest.get('created_utc')}`\n",
        f"- expect_version: `{manifest.get('expect_version')}`\n",
        f"- policy: `{manifest.get('policy')}`\n\n",
        "## Layout\n\n",
        "- `manifest.json`: machine-readable run metadata\n",
        "- `summary.md`: human-readable run summary\n",
        "- `bundle-index.json`: file inventory for this bundle\n",
        "- `commands/`: direct command transcripts when present\n",
        "- `observer.jsonl`: read-only observer stream when present\n",
        "- `modules/<name>/`: module-owned evidence when present\n",
    ])


def finalize_bundle(store: EvidenceStore,
                    manifest: dict[str, Any],
                    summary_text: str) -> None:
    manifest = dict(manifest)
    manifest["bundle_schema"] = "a90-harness-v175"
    manifest["bundle_finalized_host_ts"] = time.time()
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary_text)
    store.write_text("README.md", render_bundle_readme(manifest))
    files = collect_bundle_files(store)
    index = {
        "schema": "a90-harness-v175",
        "run_dir": str(store.run_dir),
        "file_count": len(files),
        "files": [item.to_dict() for item in files],
        "policy": "private 0700 directories, 0600 files, symlink destinations refused",
    }
    store.write_json("bundle-index.json", index)
