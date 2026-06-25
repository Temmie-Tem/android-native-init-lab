# Native Init V3267 GPU H3 CCU Magic Source Audit

Date: 2026-06-26

## Scope

- Audit the Mesa fd6 sysmem CCU hypothesis for the H3 no-pixel draw.
- Determine whether H3's `RB_CCU_CNTL=0x10000000` is a wrong hardcoded value on Adreno 640.
- Re-check the adjacent Mesa-grounded candidates: sysmem bin control and per-MRT component write enables.

## Evidence

- Mesa A640 device entry: `/tmp/a90-mesa-h3-sparse/src/freedreno/common/freedreno_devices.py`
  uses `GPUId(640)`, `a6xx_base + a6xx_gen2`, and `num_ccu=2`.
- Mesa `a6xx_base` sets sysmem CCU depth and color cache size to `64 * 1024` per CCU.
- Mesa `fd6_calc_gmem_cache_offsets()` sets sysmem `depth_ccu_offset=0` and
  `color_ccu_offset=depth_ccu_offset + num_ccu * sysmem_per_ccu_depth_cache_size`.
- For A640 this computes `color_ccu_offset = 2 * 64KiB = 0x20000`.
- Mesa A6xx `RB_CCU_CNTL.COLOR_OFFSET` is encoded as `(offset >> 12) << 23`, so
  `0x20000` becomes `(0x20 << 23) = 0x10000000`.
- Current H3 already has `GPU_H3_RB_CCU_CNTL=0x10000000`,
  `GPU_H3_RB_CCU_COLOR_OFFSET=0x00020000`, and `GPU_H3_RB_CCU_DEPTH_OFFSET=0`.

## Findings

- `RB_CCU_CNTL=0x10000000` is not a stale A5xx constant in this A640 sysmem path; it matches
  Mesa's A640 fd6 sysmem CCU calculation.
- V3255/V3256 already added Mesa `set_bin_size()` equivalents for sysmem rendering:
  `GRAS_SC_BIN_CNTL` and `RB_CNTL`.
- `RB_RENDER_COMPONENTS` and `SP_FS_RENDER_COMPONENTS` are not A6xx register names in the local
  A6xx XML. The A6xx color write-enable path is already represented in H3 by
  `RB_PS_OUTPUT_MASK`, `SP_PS_OUTPUT_MASK`, and `RB_MRT0_CONTROL.COMPONENT_ENABLE` for MRT0.

## Result

No boot-image delta was built for this audit because the proposed `RB_CCU_CNTL` replacement would
change a value that already matches Mesa's A640 sysmem calculation, and the other two proposed
register classes were already covered or do not map to A6xx register names.

The next bounded unit should be a definitive Mesa fd6 sysmem single-triangle `.rd` capture/cffdump
diff against H3. If a host Mesa Gallium+drm-shim reference cannot be built, continue a source-grounded
diff around remaining A6xx program/RB/static non-context state that is present in Mesa but absent from H3.
