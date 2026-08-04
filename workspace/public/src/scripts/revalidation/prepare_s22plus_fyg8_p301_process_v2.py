#!/usr/bin/env python3
"""Promote one independently checked P3.01 candidate into offline evidence."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

import prepare_s22plus_fyg8_p234_process_v2 as base
import s22plus_fyg8_p300_e2_stock_closure as e2_closure_selector
import s22plus_fyg8_p301_candidate_static_checker as static_checker


SCHEMA = "s22plus_fyg8_p301_process_v2_promotion_v1"
VERDICT = base.VERDICT
TARGET = static_checker.TARGET
DEFAULT_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p301/static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/outputs/s22plus_fyg8_p301/"
    "candidate-a/odin4/AP.tar.md5"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p301/process-v2"
)
_CONFIGURATION_FIELDS = (
    "static_checker",
    "e2_closure_selector",
    "SCHEMA",
    "VERDICT",
    "TARGET",
    "DEFAULT_STATIC",
    "DEFAULT_CANDIDATE_AP",
    "DEFAULT_OUT",
)
_INDIRECT_MODULE_NAMES = (
    "build_s22plus_fyg8_p286_candidate",
    "s22plus_fyg8_p286_boot_only_packager",
    "s22plus_fyg8_p286_build",
    "s22plus_fyg8_p286_build_repro_check",
    "s22plus_fyg8_p286_candidate_contract",
    "s22plus_fyg8_p286_candidate_static_checker",
    "s22plus_fyg8_p286_source_contracts",
    "s22plus_fyg8_p286_userspace_build",
    "s22plus_fyg8_p290_build_repro_check",
)


def _apply_configuration() -> None:
    static_checker._configure()
    base.static_checker = static_checker
    base.e2_closure_selector = e2_closure_selector
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.DEFAULT_STATIC = DEFAULT_STATIC
    base.DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_AP
    base.DEFAULT_OUT = DEFAULT_OUT


def _snapshot_indirect_modules() -> dict[ModuleType, dict[str, Any]]:
    return {
        module: dict(vars(module))
        for module in (
            importlib.import_module(name) for name in _INDIRECT_MODULE_NAMES
        )
    }


def _restore_indirect_modules(
    snapshots: dict[ModuleType, dict[str, Any]],
) -> None:
    for module, saved in snapshots.items():
        current = vars(module)
        for name in set(current) - set(saved):
            del current[name]
        current.update(saved)


@contextmanager
def _configuration_context() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _CONFIGURATION_FIELDS}
    indirect = _snapshot_indirect_modules()
    try:
        _apply_configuration()
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)
        _restore_indirect_modules(indirect)


def __getattr__(name: str):
    return getattr(base, name)


def parse_args(argv: list[str] | None = None):
    with _configuration_context():
        return base.parse_args(argv)


def validate_static(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configuration_context():
        return base.validate_static(*args, **kwargs)


def derive(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configuration_context():
        return base.derive(*args, **kwargs)


def main(argv: list[str] | None = None) -> int:
    with _configuration_context():
        return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
