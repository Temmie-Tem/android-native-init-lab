# Native Init V3300 GPU Compute C1 Shader Bytes

Date: 2026-06-26

## Scope

Host-only C1 gate closure for the active visible GPU compute ladder.

No native-init source behavior changed, no boot artifact was built, and no flash was run.

## Result

`kern_invocationid.asm` is now materialized into verified A640 CS shader words.

- Source kernel: `/tmp/a90-mesa-gpu-src/kern_invocationid.asm`
- Kernel source SHA256: `1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a`
- Shader binary SHA256: `7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a`
- Size: `32` dwords / `128` bytes
- `instrlen=1`, `constlen=4`, `max_reg=0`, `max_half_reg=-1`
- Local size: `32,1,1`
- UAV contract: one 32-word buffer, expected readback `buf[i] == i`

The materialized dwords are:

```c
0x00000000, 0x200cc001, 0x00000000, 0x00000500,
0x01674000, 0xc0260000, 0x00000000, 0x03000000,
0x00000000, 0x00000000, 0x00000000, 0x00000000,
0x00000000, 0x00000000, 0x00000000, 0x00000000,
0x00000000, 0x00000000, 0x00000000, 0x00000000,
0x00000000, 0x00000000, 0x00000000, 0x00000000,
0x00000000, 0x00000000, 0x00000000, 0x00000000,
0x00000000, 0x00000000, 0x00000000, 0x00000000
```

Mesa `ir3-disasm -g FD640` decodes those words as:

```text
0[200cc001_00000000] mov.u32u32 r0.y, r0.x
1[00000500_00000000] (rpt5)nop
2[c0260000_01674000] stib.b.untyped.1d.u32.1.imm r0.x, r0.y, 0
3[03000000_00000000] end
```

## Toolchain

The original `/tmp/a90-mesa-h3-build-ir3` build had NIR stubbed out, so a bounded host-only full-NIR Mesa tool build was
created under `/tmp/a90-mesa-c1-fullnir-softpipe-v3300` with:

- `gallium-drivers=softpipe`
- `tools=freedreno`
- `opengl=true`
- no proprietary blob, EGL, OpenCL, Vulkan, or runtime driver path

The full `computerator` target still cannot be linked on this host because `libdrm` headers are absent, but the C1 gate
does not need the DRM backend. The IR3/NIR static libraries and `ir3-disasm` were sufficient to run the assembler path
offline and verify the resulting words.

Tool identities:

```text
ir3-disasm                             5fdf9cba93165bad98e9d2fe1ee92bb7cd06ef88e286454379e4943331498fc1
libnir.a                              42005745d187e2c34261b3a4c431fc205dc0a8155a3d23b5e6264d034c438b11
libfreedreno_ir3.a                    7f65ae1058d862037d7e70e1670e3b29256ea51d2d4ad126dcb09ffc6295a060
```

## C1 Live Readiness

The shader-byte gate is closed. The next bounded unit is native-init C1 live dispatch:

1. Embed the verified CS shader dwords.
2. Bind one 32-word UAV.
3. Dispatch one `32,1,1` workgroup through the C0 envelope.
4. Wait idle, sync/readback the UAV, and pass only if `buf[i] == i`.

If readback is unchanged, follow the GOAL-defined proof bisect immediately: CP_MEM_WRITE sentinel before `CP_EXEC_CS`,
drop `KGSL_CONTEXT_NO_SNAPSHOT`, then diff against `comp_a6xx.cc`.

## Validation

```text
PYTHONPYCACHEPREFIX=tmp/pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_gpu_compute_c1_shader_bytes_v3300.py \
  tests/test_native_gpu_compute_c1_shader_bytes_v3300.py
```

Result: pass.

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_native_gpu_compute_c1_shader_bytes_v3300.py'
```

Result: `Ran 4 tests ... OK`.

```text
python3 workspace/public/src/scripts/revalidation/native_gpu_compute_c1_shader_bytes_v3300.py \
  --require-disasm --json
```

Result: `passed=true`, `ready_for_c1_live=true`.
