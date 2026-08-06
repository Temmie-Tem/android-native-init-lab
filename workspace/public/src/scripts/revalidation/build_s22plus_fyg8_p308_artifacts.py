#!/usr/bin/env python3
"""Run the P3.08 candidate builder with the exact 61-module stock closure."""

from __future__ import annotations

import json
import subprocess

import build_s22plus_fyg8_p286_candidate as build_base
import build_s22plus_fyg8_p308_candidate as candidate
import s22plus_fyg8_p304_e2_stock_closure as closure


def main(argv: list[str] | None = None) -> int:
    candidate._configure()
    args = build_base.parse_args(argv)
    build_base.p286_closure = closure
    try:
        result = build_base.build_candidate(args)
    except (
        build_base.BuildError,
        build_base.candidate_contract.ContractError,
        build_base.candidate_contract.intent.IntentError,
        build_base.e2_closure.ClosureError,
        build_base.carrier.BuildError,
        build_base.boot_slice.BootSliceError,
        build_base.boot_verify.BootVerifyError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": candidate.SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({
        "schema": candidate.SCHEMA,
        "verdict": result["verdict"],
        "boot_sha256": result["outputs"]["boot_img"]["sha256"],
        "ap_sha256": result["outputs"]["ap_tar_md5"]["sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
