# Native Init V3305 GPU 2D D1 Textured Shader Bytes

Date: 2026-06-26

## Scope

Host-only shader-byte gate for the active GPU-accelerated 2D D1 ladder.

No native-init source behavior changed, no boot artifact was built, and no flash was run.

## Result

`native_gpu_2d_d1_textured_shader_bytes_v3305.py --require-disasm --json` passed.

The minimal FD640 textured fragment shader is materialized and disassembly-verified:

```text
bary.f r0.x, 0, r0.x
bary.f r0.y, 1, r0.x
sam (f32)(xyzw)r0.z, r0.x, s#0, t#0
end
nop
```

The shader binary identity is:

```text
sha256      4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3
size        32 dwords / 128 bytes
gpu         FD640
chip_id     06040000
stage       fragment
instrlen    1
constlen    0
max_reg     1
max_hreg    -1
mergedregs  true
num_samp    1
num_tex     1
```

Materialized instruction pairs:

```text
47300000_00002000
47300001_00002001
a0c01f02_00000001
03000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
00000000_00000000
```

`ir3-disasm -c 06040000` decodes the binary as:

```text
0[47300000_00002000] bary.f r0.x, 0, r0.x
1[47300001_00002001] bary.f r0.y, 1, r0.x
2[a0c01f02_00000001] sam (f32)(xyzw)r0.z, r0.x, s#0, t#0
3[03000000_00000000] end
4[00000000_00000000] nop
```

## Toolchain

The host has no Freedreno GPU device, so `computerator` still cannot run as a live device-backed tool. A bounded local
libdrm-backed Mesa tool build was used only for offline IR3 materialization and disassembly.

```text
Mesa source root     /tmp/a90-mesa-gpu-src
Mesa build root      /tmp/a90-mesa-d1-texture-build-libdrm
libdrm prefix        /tmp/a90-libdrm-prefix
libdrm version       2.4.134
ir3-disasm           /tmp/a90-mesa-d1-texture-build-libdrm/src/freedreno/isa/ir3-disasm
ir3-disasm sha256    e4550ec20fb4caad778b45f4b81803000db27d187c69c7b6899e10af35afef1a
```

The materializer path used Mesa's `ir3_parse_asm` with `fd_dev_id gpu_id=640` and no device open:

```text
/tmp/a90-mesa-d1-texture-build-libdrm/src/freedreno/ir3/ir3_delay_test --dump \
  /tmp/a90-d1-textured-fs.asm 640 0
```

## H3 Output Contract

The sampled color lands in `r0.z`, which is scalar regid `2`. This matches the existing H3 color-output contract in
`workspace/public/src/native-init/v319/80_shell_dispatch.inc.c`:

```text
GPU_H3_PS_OUTPUT_REGID              2
GPU_H3_SP_PS_FULLREGFOOTPRINT       2
GPU_H3_IR3_INSTR_ALIGN              16
GPU_H3_FS_SHADER_DWORDS             GPU_H3_SHADER_ALIGNED_DWORDS
GPU_H3_SHADER_ALIGNED_DWORDS        GPU_H3_IR3_INSTR_ALIGN * 2
```

The V3305 checker also verified:

- `SP_PS_CNTL_0` mergedregs support is present.
- The FS shader slot covers the aligned 32-dword payload.
- The RGBA8 MRT contract is present.
- The D1 shader uses non-bindless `s#0/t#0`, matching the V3304 texture reference.

## D1 Live Readiness

The shader-byte gate is closed. The next bounded unit is the native-init D1 static checkerboard texture probe:

1. Embed the verified FS shader words.
2. Load one sampler descriptor and one TEXMEMOBJ descriptor.
3. Set `NTEX=1/NSAMP=1`.
4. Draw a fullscreen textured quad.
5. Require readback to contain the sampled checkerboard pattern, not the clear color.

If readback is unchanged, stay on the D1 texture/raster envelope and diff against the V3304 fd6 reference before adding
any new subsystem.

## Validation

```text
PYTHONPYCACHEPREFIX=tmp/pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_gpu_2d_d1_textured_shader_bytes_v3305.py \
  tests/test_native_gpu_2d_d1_textured_shader_bytes_v3305.py
```

Result: pass.

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_native_gpu_2d_d1_textured_shader_bytes_v3305.py'
```

Result: `Ran 5 tests ... OK`.

```text
python3 workspace/public/src/scripts/revalidation/native_gpu_2d_d1_textured_shader_bytes_v3305.py \
  --require-disasm --json
```

Result: `passed=true`, `ready_for_d1_source=true`, `h3_output_contract_valid=true`,
`ir3_disasm_contains_expected_ops=true`.
