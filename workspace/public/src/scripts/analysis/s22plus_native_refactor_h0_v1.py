#!/usr/bin/env python3
"""Compile/package the direct native source against the consumed P383 oracle.

H0 only. The legacy generator is a comparison oracle and the existing compiler,
boot reader and packager remain the platform boundary. No live manifest is
created, changed, promoted or consumed by this command.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(Path(__file__).parent),
               str(ROOT / "workspace/public/src/scripts/revalidation")]
import s22plus_native_source_v1 as direct

REFERENCE = ROOT / "workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.1/candidate-build-verified"
REFERENCE_RESULT = {
    "size": 109545,
    "sha256": "50ba11b7114374bec18a4c0e2c11161ab2317d1805baba6c59e8762328b46597",
}
IDENTITY = direct.Identity("p383", "c383f1e0a90b5e6d7c8a9b0c0d2e3f0b", "v0.2.0-rc.1")


def identity(raw: bytes) -> dict:
    return {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def display_rows(plan: bytes) -> tuple[direct.DisplayModule, ...]:
    rows = tuple(direct.DisplayModule(name.decode(), int(size), flag == b"1")
                 for name, size, flag in re.findall(
                     rb'\{"/s22-display-modules/([A-Za-z0-9_.-]+\.ko)", ([0-9]+)ULL, ([01])\}',
                     plan))
    if direct.display_plan(rows) != plan:
        raise ValueError("reference display plan has an unsupported shape")
    return rows


def _private_output(output: Path) -> Path:
    output = output.absolute()
    private = (ROOT / "workspace/private").resolve(strict=True)
    if output.exists() or output.is_symlink():
        raise ValueError("new H0 output directory is required")
    if not output.resolve().is_relative_to(private):
        raise ValueError("materialized keyed source must stay under workspace/private")
    return output


def build(output: Path, *, reuse_components: Path | None = None) -> dict:
    # Imports below are restricted to this H0 comparison/packaging harness.
    # The production direct source module has no dependency on these oracles.
    import s22plus_fyg8_p383_stock_candidate_build as legacy
    import s22plus_fyg8_p383_research_shell_runtime as runtime
    import s22plus_fyg8_p383_display_renderer as renderer
    import s22plus_memory_manifest_v1 as memory
    import device_action_f1_evidence_v2 as evidence

    output = _private_output(output)
    reference = json.loads(legacy.stable(REFERENCE / "result.json", REFERENCE_RESULT))
    if reference["run_id_hex"] != IDENTITY.run_id_hex:
        raise ValueError("reference identity differs")
    for name, expected in reference["source_inputs"].items():
        legacy.stable(ROOT / name, expected)
    for name, expected in reference["toolchain_inputs"].items():
        legacy.stable(Path(name), expected)
    current_sources = direct.source_receipts()
    if reuse_components is not None:
        reuse_components = reuse_components.resolve(strict=True)
        if not reuse_components.is_relative_to((ROOT / "workspace/private").resolve()):
            raise ValueError("component evidence must remain under workspace/private")
        if json.loads(legacy.stable(reuse_components / "source-inputs.json")) != current_sources:
            raise ValueError("component source inputs changed")
    harness = identity(Path(__file__).read_bytes())
    observer_spec = identity(canonical(evidence._shell_observer_spec("p383")))
    plan_before = legacy.stable(REFERENCE / "inputs/s22plus_native_display_plan.h",
                                reference["module_plan"])
    plan = direct.display_plan(display_rows(plan_before))
    census = tuple(direct.MemoryModule(*row) for row in memory.manifest())
    display = direct.render_display(IDENTITY, census)
    if display != renderer.render() or display != legacy.stable(REFERENCE / "inputs/renderer.c"):
        raise ValueError("actual display sources differ")
    if direct.helper_template(IDENTITY) != runtime.build_helper():
        raise ValueError("production helper templates differ")

    source_dir = REFERENCE / "stock-sources"
    runtime_name = legacy.packager.RUNTIME_INCLUDE_NAME
    before = legacy.stable(source_dir / runtime_name, reference["source_closure"][runtime_name])
    key = runtime.predecessor._materialized_key(before)
    old_helper = runtime.materialize_helper(key)
    new_helper = direct.materialize_helper(IDENTITY, key)
    if old_helper != new_helper or before.count(old_helper) != 1:
        raise ValueError("actual keyed production helper differs")
    # The deeper source-matched platform envelope is outside this refactor.
    # Compile a fresh assembly that explicitly consumes the direct generator.
    assembled = before.replace(old_helper, new_helper, 1)
    if assembled != before:
        raise ValueError("platform source envelope changed")

    output.mkdir(parents=True, mode=0o700)
    legacy.write(output / "source-inputs.json", canonical(current_sources))
    legacy.write(output / "configuration.json", canonical({
        "identity": asdict(IDENTITY),
        "memory_modules": [asdict(row) for row in census],
        "display_modules": [asdict(row) for row in display_rows(plan)],
    }))
    for name, expected in reference["source_closure"].items():
        raw = legacy.stable(source_dir / name, expected)
        legacy.write(output / "stock-sources" / name, assembled if name == runtime_name else raw)
    child_source = legacy.stable(REFERENCE / "inputs/child-source.c",
                                legacy.packager.CHILD_SOURCE_IDENTITY)
    legacy.write(output / "inputs/child-source.c", child_source)
    legacy.write(output / "inputs/renderer.c", display)
    legacy.write(output / "inputs/s22plus_native_display_plan.h", plan)
    image = legacy.stable(REFERENCE / "inputs/fixed-Image", reference["image"])

    packager = legacy.packager
    if packager.TOOL_IDENTITIES != reference["tools"]:
        raise ValueError("compiler/packaging tool binding differs")
    packager.RUN_ID = bytes.fromhex(IDENTITY.run_id_hex)
    tools = packager._bind_tools()
    userspace = []
    for label in ("a", "b"):
        if reuse_components is None:
            built = packager._compile_userspace(output / "stock-sources",
                                               output / ("userspace-" + label), label="refactor-" + label)
        else:
            for name, expected in reference["source_closure"].items():
                legacy.stable(reuse_components / "stock-sources" / name, expected)
            for filename, kind in (("init", "init"), ("s22-e1-child", "child")):
                raw = legacy.stable(reuse_components / ("userspace-" + label) / filename,
                                    reference[kind])
                legacy.write(output / ("userspace-" + label) / filename, raw)
            built = {kind: reference[kind] for kind in ("init", "child")}
        if built["init"] != reference["init"] or built["child"] != reference["child"]:
            raise ValueError("static ARM64 userspace differs from reference")
        userspace.append(built)
    if userspace[0] != userspace[1]:
        raise ValueError("ARM64 userspace A/B differs")

    compiler = [tools["gcc"], *legacy.RENDERER_FLAGS, "-I", output / "inputs",
                "-I", legacy.HEADERS, "-I", legacy.NATIVE, output / "inputs/renderer.c"]
    for label in ("a", "b"):
        if reuse_components is None:
            legacy.run([*compiler, "-o", output / ("renderer-" + label)], output,
                       output / ("renderer-" + label + ".log"))
            (output / ("renderer-" + label)).chmod(0o400)
        else:
            if legacy.stable(reuse_components / "inputs/renderer.c") != display:
                raise ValueError("reused renderer source differs")
            legacy.stable(reuse_components / "inputs/s22plus_native_display_plan.h", reference["module_plan"])
            legacy.write(output / ("renderer-" + label),
                         legacy.stable(reuse_components / ("renderer-" + label), reference["renderer"]))
    renderer_a = legacy.stable(output / "renderer-a", reference["renderer"])
    legacy.stable(output / "renderer-b", reference["renderer"])
    for label, binary in (("init", output / "userspace-a/init"),
                          ("renderer", output / "renderer-a")):
        info = legacy.run([tools["file"], "-b", binary], output, output / (label + "-file.log"))
        headers = legacy.run([tools["readelf"], "-W", "-l", binary], output,
                             output / (label + "-readelf.log"))
        if b"ARM aarch64" not in info or b"statically linked" not in info or b"INTERP" in headers:
            raise ValueError("static ARM64 ELF inspection failed")

    modules = {name: legacy.stable(REFERENCE / "module-bytes" / name, expected)
               for name, expected in reference["module_bytes"].items()}
    base = json.loads(legacy.stable(legacy.BASE / "result.json", legacy.BASE_RESULT))
    base_boot = legacy.stable(legacy.BASE / "candidate-a/boot.img",
                             base["phase2"]["candidate"]["a"]["boot_img"])
    init = legacy.stable(output / "userspace-a/init", reference["init"])
    candidates = {}
    for label in ("a", "b"):
        # Packaging scratch is private and temporary, like the existing compiler
        # scratch. Identical payloads already have an immutable retained oracle;
        # keep command logs and receipts rather than duplicate large firmware.
        scratch = Path(tempfile.mkdtemp(prefix="s22plus-native-refactor-pack-"))
        try:
            candidate = legacy.build_package(scratch, label, base_boot, image, init, renderer_a, modules, tools)
            if candidate != reference["candidate"][label]:
                raise ValueError("boot/AP/inventory differs from reference")
            candidates[label] = candidate
            for log in sorted((scratch / ("pack-" + label)).glob("*.log")):
                legacy.write(output / "packaging-logs" / label / log.name, legacy.stable(log))
        except BaseException:
            # Do not remove partial host-failure evidence. The marker identifies
            # the private scratch even if ordinary result publication fails.
            (scratch / "FAILED_H0.json").write_bytes(canonical({"output": str(output), "role": label}))
            raise
        else:
            shutil.rmtree(scratch)

    if direct.source_receipts() != current_sources or identity(Path(__file__).read_bytes()) != harness:
        raise ValueError("direct source or comparison harness changed during build")
    for name, expected in reference["source_inputs"].items():
        legacy.stable(ROOT / name, expected)
    for name, expected in reference["toolchain_inputs"].items():
        legacy.stable(Path(name), expected)
    packager._bind_tools()
    if observer_spec != identity(canonical(evidence._shell_observer_spec("p383"))):
        raise ValueError("observation specification changed")
    result = {
        "schema": "s22plus-native-refactor-h0-v1",
        "verdict": "PASS_H0_NATIVE_SOURCE_EQUIVALENCE",
        "reference_result": REFERENCE_RESULT,
        "configuration": identity((output / "configuration.json").read_bytes()),
        "harness": harness,
        "source_inputs": current_sources,
        "source_closure": reference["source_closure"],
        "helper": identity(new_helper),
        "renderer_source": identity(display),
        "module_plan": identity(plan),
        "observer_spec": observer_spec,
        "init": reference["init"], "renderer": reference["renderer"],
        "image": identity(image),
        "module_bytes": reference["module_bytes"],
        "candidate": candidates,
        "byte_identical": True, "production_helper_used": True,
        "components_reused_from": str(reuse_components) if reuse_components is not None else None,
        "identical_package_bytes_retained_at": str(REFERENCE),
        "deeper_platform_envelope_preserved": True,
        "scope": {"tier": "H0", "device_contact": False, "live_authorized": False,
                  "candidate_transfers": 0, "rollback_transfers": 0,
                  "historical_consumption_unchanged": True},
    }
    legacy.write(output / "result.json", canonical(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--reuse-components", type=Path)
    args = parser.parse_args()
    result = build(args.out, reuse_components=args.reuse_components)
    print(json.dumps({"verdict": result["verdict"], "byte_identical": result["byte_identical"],
                      "ap": result["candidate"]["a"]["ap_tar_md5"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
