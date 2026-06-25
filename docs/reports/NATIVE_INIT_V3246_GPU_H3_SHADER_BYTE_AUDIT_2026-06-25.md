# Native Init V3246 GPU H3 Shader Byte Audit

Date: 2026-06-25

## Scope

Host-only audit of the current H3 hand-assembled ir3 shader words in
`workspace/public/src/native-init/v319/80_shell_dispatch.inc.c`.

No native-init source behavior changed, no boot image was built, and no flash was run.

## Tooling

- Mesa checkout: `/tmp/a90-mesa-h3-sparse` (`origin=https://gitlab.freedesktop.org/mesa/mesa.git`)
- Built tool: `/tmp/a90-mesa-h3-build-ir3/src/freedreno/isa/ir3-disasm`
- Build note: the local Mesa build was restricted to `-Dtools=freedreno` with Gallium/Vulkan/OpenGL disabled. The host
  lacks `zlib.h`, so `/tmp` Mesa `freedreno_common` was locally narrowed to omit RD-output objects that are not needed by
  `ir3-disasm`.

## Result

`native_gpu_h3_shader_byte_audit_v3246.py --require-ir3-disasm` passed. The exact H3 shader words decode as:

VS:

```text
20044000_00000000 => mov.f32f32 r0.x, r0.x
20044001_00000001 => mov.f32f32 r0.y, r0.y
20444002_00000000 => mov.f32f32 r0.z, (0.0)
20444003_3f800000 => mov.f32f32 r0.w, (1.0)
03000000_00000000 => end
00000000_00000000 => nop
```

FS:

```text
20444000_3f800000 => mov.f32f32 r0.x, (1.0)
03000000_00000000 => end
00000000_00000000 => nop
00000000_00000000 => nop
```

All instructions decode without `(ss)` or `(sy)` flags, matching the current plain hand encoding.

## Targeted Checks

- FS precision: FS writes full `r0.x` via `mov.f32f32`; `SP_PS_OUTPUT_REG0` is regid `0` with `HALF_PRECISION=0`.
  This does not support a half/full mismatch as the current no-pixel root cause.
- MRT metadata: current `SP_PS_MRT_REG0` color format is `0x4a` (`FMT6_32_FLOAT`) and `COLOR_UINT=0`; Mesa's current
  A6xx XML does not define a half-precision bit in `SP_PS_MRT_REG0`.
- Position linkage: `SP_VS_OUTPUT_REG0` is regid `0`, compmask `0xf`; `SP_VS_VPC_DEST_REG0.OUTLOC0=0`;
  `VPC_VS_CNTL=0x00ff0004` decodes to stride `4`, `POSITIONLOC=0`, `PSIZELOC=0xff`.
- SIV linkage: `VPC_VS_SIV_CNTL=0x0000ffff` and `_V2=0x0000ffff` are layer/view sentinels. Position is selected by
  `VPC_VS_CNTL.positionloc`, not by SIV.

## Validation

```text
python3 workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py \
  --require-ir3-disasm \
  --ir3-disasm /tmp/a90-mesa-h3-build-ir3/src/freedreno/isa/ir3-disasm \
  --pretty
```

Result: `passed=true`, `mismatches=[]`, `external_ir3_disasm_used=true`.

```text
PYTHONPATH=tests python3 -m unittest tests/test_native_gpu_h3_shader_byte_audit_v3246.py
```

Result: `Ran 3 tests ... OK`.

```text
python3 - <<'PY'
import py_compile
from pathlib import Path
files = [
    Path('workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py'),
    Path('tests/test_native_gpu_h3_shader_byte_audit_v3246.py'),
]
for i, path in enumerate(files):
    py_compile.compile(str(path), cfile=f'/tmp/a90_v3246_pycompile_{i}.pyc', doraise=True)
    print(f'compiled {path}')
PY
```

Result: both files compiled. The explicit `/tmp` cfile is used because
`workspace/public/src/scripts/revalidation/__pycache__` is root-owned in this checkout.

## Decision

The current H3 no-pixel symptom should not be attributed to invalid ir3 word encoding, a simple FS half/full mismatch,
or a position-SIV misunderstanding. The next bounded unit should compare the remaining first-draw packet/linkage delta
outside the verified shader bytes, especially render-target/RB linkage or compiler-emitted minimal-shader state that is
still absent from the KGSL-direct envelope.
