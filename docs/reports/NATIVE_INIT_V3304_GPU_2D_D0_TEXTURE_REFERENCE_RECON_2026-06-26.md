# Native Init V3304 GPU 2D D0 Texture Reference Recon

Date: 2026-06-26

## Scope

Host-only D0 recon for the active GPU-accelerated 2D ladder.

No native-init source behavior changed, no boot artifact was built, and no flash was run.

## Result

`native_gpu_2d_d0_texture_reference_v3304.py --json` passed the D0 texture reference recon.

Confirmed from the freshly pre-staged Mesa freedreno reference under `/tmp/a90-mesa-gpu-src/`:

- Mesa source: `https://gitlab.freedesktop.org/mesa/mesa.git`
- Mesa commit: `6adb0d5e01dca952fcb04b7773ad92b0ab2e132d`
- Local reference summary: `/tmp/a90-mesa-gpu-src/a6xx_texture_blit_reference_v3304.txt`
- FS texture state enters the draw stream through `FD6_GROUP_FS_TEX` and `fd6_texture_state(ctx, MESA_SHADER_FRAGMENT)`.
- FS sampler descriptors are 4 dwords each.
- FS texture/TEXMEMOBJ descriptors are 16 dwords each.
- FS sampler descriptor load:
  `SP_PS_SAMPLER_BASE` + `CP_LOAD_STATE6_FRAG` + `ST6_SHADER` + `SS6_INDIRECT` + `SB6_FS_TEX`.
- FS texture/TEXMEMOBJ descriptor load:
  `SP_PS_TEXMEMOBJ_BASE` + `SP_PS_TSIZE` + `CP_LOAD_STATE6_FRAG` + `ST6_CONSTANTS` + `SS6_INDIRECT` + `SB6_FS_TEX`.
- FS program config must set `SP_PS_CONFIG` with `NTEX/NSAMP` through Mesa's `sp_xs_config(state->fs)` path.
- TPL1 draw baseline registers are source-pinned: `TPL1_MODE_CNTL`, `TPL1_GFX_BORDER_COLOR_BASE`, and
  `TPL1_WINDOW_OFFSET`.
- Non-bindless ir3 cat5 `sam` is source-confirmed with both sampler and texture fields; D1 should use `s#0/t#0` for the
  static checkerboard texture.

## Source Identity

```text
a6xx_texture_blit_reference_v3304.txt 05948dae9f4b1ce1e80e9aa21dc9af8e98c1ee2b65871a74a046f0113a31a328
fd6_texture.cc                        39eb196dc43dc17dc649cb2a7b11058c2d87a40f856e25755dfcbea3d158d73a
fd6_texture.h                         2fbd2cf9a5609bf8b92a6702a7d8dc124e5c48b3db9c0d27e7d4c8d4db8eb53b
fd6_emit.cc                           eda14dd95168c97675b45574e3bed1fe026d30e5b02523cd590a9b8e4143f184
fd6_emit.h                            9ef105a064b718a466885a2aa4d00e7587739b02553d1ad835d2bd691481da7a
fd6_program.cc                        88d91ce9fba30ca1d5cf7c478eb44ea4ef11735037985ec361140b3f0020c26a
a6xx.xml                              142f225bc4ae56a910c910f1d233cc7890587c74fbdec8c390466ffbdf5e0faa
adreno_pm4.xml                        f8137e5d31a3cfce27cba0a8bc269e460067dca9ccb95e620404b7fc752913fb
ir3-cat5.xml                          9f00c1ca77a92e2e24baa715811974289a8f33dc1110a954007accd6f18c3a65
```

## Key A640 Offsets

```text
SP_PS_CONFIG                  0xab04
SP_PS_INSTR_SIZE              0xab05
SP_PS_INITIAL_TEX_LOAD_CNTL   0xa99e
SP_PS_INITIAL_TEX_LOAD        0xa99f
SP_PS_INITIAL_TEX_INDEX       0xa9a3
SP_PS_TSIZE                   0xa9a7
SP_PS_SAMPLER_BASE            0xa9e0
SP_PS_TEXMEMOBJ_BASE          0xa9e4
SP_UPDATE_CNTL                0xbb08
TPL1_GFX_BORDER_COLOR_BASE    0xb302
TPL1_MSAA_SAMPLE_POS_CNTL     0xb304
TPL1_WINDOW_OFFSET            0xb307
TPL1_MODE_CNTL                0xb309
```

## Key PM4 / State Values

```text
CP_LOAD_STATE6_FRAG  0x34
CP_SET_DRAW_STATE    0x43
CP_DRAW_INDX_OFFSET  0x38
CP_WAIT_FOR_IDLE     0x26
SB6_FS_TEX           0x04
SB6_FS_SHADER        0x0c
ST6_SHADER           0x00
ST6_CONSTANTS        0x01
SS6_INDIRECT         0x02
```

## Ordered D1 Envelope

```text
H triangle draw baseline
  -> FS program config (SP_UPDATE_CNTL, SP_PS_CONFIG, SP_PS_INSTR_SIZE)
  -> FD6_GROUP_FS_TEX / fd6_texture_state(MESA_SHADER_FRAGMENT)
  -> sampler descriptor: 4 dwords, SP_PS_SAMPLER_BASE, CP_LOAD_STATE6_FRAG/ST6_SHADER/SB6_FS_TEX
  -> texture descriptor: 16 dwords, SP_PS_TEXMEMOBJ_BASE, SP_PS_TSIZE, CP_LOAD_STATE6_FRAG/ST6_CONSTANTS/SB6_FS_TEX
  -> TPL1 baseline
  -> textured FS shader contract: cat5 sam, CAT5_UNIFORM, s#0/t#0
  -> static checkerboard readback proof
```

## D1 Gate

D0 did not build or flash a boot image. The next bounded unit is D1 shader-byte materialization:

- Materialize a minimal FD640 textured FS that samples `s#0/t#0` from interpolated UVs.
- Verify the generated shader words with `ir3-disasm`.
- Only then wire the shader bytes and a static checkerboard texture into a V3305 D1 boot artifact.

## Validation

```text
PYTHONPYCACHEPREFIX=tmp/pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_gpu_2d_d0_texture_reference_v3304.py \
  tests/test_native_gpu_2d_d0_texture_reference_v3304.py
```

Result: pass.

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_native_gpu_2d_d0_texture_reference_v3304.py'
```

Result: `Ran 7 tests ... OK`.

```text
python3 workspace/public/src/scripts/revalidation/native_gpu_2d_d0_texture_reference_v3304.py --json
```

Result: `passed=true`, `d0_texture_reference_recon_passed=true`, `offset_mismatches={}`,
`pm4_mismatches={}`, `cat5_sam_contract_valid=true`, `d1_gate.ready_for_d1_live=false`.
