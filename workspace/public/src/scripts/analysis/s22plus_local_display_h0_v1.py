#!/usr/bin/env python3
"""H0 source join and static ARM64 builds for local-display-v1; no AP or run."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / "workspace/public/src/scripts/revalidation")]
import s22plus_native_source_v1 as direct
import s22plus_native_refactor_h0_v1 as oracle


def build(output: Path) -> dict:
    import s22plus_fyg8_p383_stock_candidate_build as platform
    import s22plus_fyg8_p383_research_shell_runtime as historical
    import s22plus_memory_manifest_v1 as memory

    support = {str(Path(oracle.__file__).relative_to(ROOT)):
               oracle.identity(platform.stable(Path(oracle.__file__)))}
    output = oracle._private_output(output)
    reference = json.loads(platform.stable(oracle.REFERENCE / "result.json", oracle.REFERENCE_RESULT))
    for path, receipt in reference["source_inputs"].items():
        platform.stable(ROOT / path, receipt)
    for path, receipt in reference["toolchain_inputs"].items():
        platform.stable(Path(path), receipt)
    inputs = direct.source_receipts()
    harness = oracle.identity(Path(__file__).read_bytes())
    name = platform.packager.RUNTIME_INCLUDE_NAME
    before = platform.stable(oracle.REFERENCE / "stock-sources" / name,
                             reference["source_closure"][name])
    key = historical.predecessor._materialized_key(before)
    if direct.join_platform(before, oracle.IDENTITY, key, profile=direct.CONSOLE_PROFILE) != before:
        raise ValueError("default platform sources changed")
    joined = direct.join_platform(before, oracle.IDENTITY, key, profile=direct.LOCAL_PROFILE)
    publisher = joined[joined.index(b"static __attribute__((noreturn)) void p319_stock_publish("):]
    publisher = publisher[:publisher.index(b"\n}\n") + 3]
    if not (publisher.index(b"local_begin()") < publisher.index(b"p335_getrandom_boot_id(") <
            publisher.index(b"p345_framed_console(")):
        raise ValueError("local publication order differs")
    census = tuple(direct.MemoryModule(*row) for row in memory.manifest())
    renderer = direct.render_display(oracle.IDENTITY, census, profile=direct.LOCAL_PROFILE)
    plan = platform.stable(oracle.REFERENCE / "inputs/s22plus_native_display_plan.h", reference["module_plan"])
    output.mkdir(parents=True, mode=0o700)
    platform.write(output / "source-inputs.json", oracle.canonical(inputs))
    platform.write(output / "profile.json", oracle.canonical(direct.profile_contract(direct.LOCAL_PROFILE)))
    for path, receipt in reference["source_closure"].items():
        raw = platform.stable(oracle.REFERENCE / "stock-sources" / path, receipt)
        platform.write(output / "stock-sources" / path, joined if path == name else raw)
    platform.write(output / "inputs/renderer.c", renderer)
    platform.write(output / "inputs/s22plus_native_display_plan.h", plan)
    platform.write(output / "inputs/child-source.c", platform.stable(
        oracle.REFERENCE / "inputs/child-source.c", platform.packager.CHILD_SOURCE_IDENTITY))
    tools = platform.packager._bind_tools()
    platform.packager.RUN_ID = bytes.fromhex(oracle.IDENTITY.run_id_hex)
    components = []
    renderers = []
    for label in ("a", "b"):
        components.append(platform.packager._compile_userspace(
            output / "stock-sources", output / ("userspace-" + label), label="local-display-" + label))
        binary = output / ("renderer-" + label)
        platform.run([tools["gcc"], *platform.RENDERER_FLAGS, "-I", output / "inputs",
                      "-I", platform.HEADERS, "-I", platform.NATIVE,
                      output / "inputs/renderer.c", "-o", binary], output,
                     output / ("renderer-" + label + ".log"))
        platform.run(["file", binary], output, output / ("renderer-" + label + ".file.log"))
        renderers.append(oracle.identity(platform.stable(binary)))
    if components[0] != components[1] or renderers[0] != renderers[1]:
        raise ValueError("A/B compiled component identities differ")
    if direct.source_receipts() != inputs or oracle.identity(Path(__file__).read_bytes()) != harness:
        raise ValueError("local source changed during build")
    for path, receipt in support.items():
        platform.stable(ROOT / path, receipt)
    for path, receipt in reference["source_inputs"].items():
        platform.stable(ROOT / path, receipt)
    for path, receipt in reference["toolchain_inputs"].items():
        platform.stable(Path(path), receipt)
    result = {"schema": "s22plus-local-display-h0-v1", "status": "PASS_H0_COMPONENT_BUILD",
              "live_activation": False, "profile": direct.profile_contract(direct.LOCAL_PROFILE),
              "identity": asdict(oracle.IDENTITY), "reference_result": oracle.REFERENCE_RESULT,
              "source_inputs": inputs, "harness": harness, "supporting_sources": support,
              "platform_runtime": oracle.identity(joined),
              "helper": oracle.identity(direct.materialize_helper(oracle.IDENTITY, key, profile=direct.LOCAL_PROFILE)),
              "renderer_source": oracle.identity(renderer), "components": components[0],
              "renderer": renderers[0], "default_platform_unchanged": True,
              "publication_start_before_boot_id_and_auth": True,
              "historical_source_input_count": len(reference["source_inputs"]),
              "toolchain_input_count": len(reference["toolchain_inputs"]),
              "device_effect": False, "ap_or_manifest_created": False}
    platform.write(output / "result.json", oracle.canonical(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.out), sort_keys=True, indent=2))
