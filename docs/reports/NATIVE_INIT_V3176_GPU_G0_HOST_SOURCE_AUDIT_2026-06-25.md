# Native Init V3176 GPU G0 Host Source Audit

## Summary

- Cycle: `V3176`
- Track: GPU G0 KGSL open-hang diagnosis.
- Result: HOST-SIDE SOURCE AUDIT PASS; live bounded probe still pending.
- Device flash: `no`.
- Device action: `no`.
- Safety scope: freedreno/KGSL-direct only, no proprietary Adreno blob/EGL/Bionic path, no exploit work, no ioctl/mmap ladder rung, no GDSC/regulator/PMIC/GPIO/power-rail writes.

## Prerequisite

- Video 0.11.0 promotion is closed in `GOAL.md` as V3157, so the GPU G0 epic is active.
- G0 remains the only active GPU rung. G1-G5 are still gated on G0 proving a non-hanging bright-line-safe path.

## Current Native-Init Probe Surface

- Native command surface exposes `gpu g0-status` and `gpu g0-open-probe`.
- `gpu g0-status` is read-only: KGSL sysfs/devnode/firmware visibility only.
- `gpu g0-open-probe` forks a child for `open("/dev/kgsl-3d0")`; the parent never enters open, enforces a timeout, kills the child on timeout, and reports metadata.
- The probe reports `ioctl_attempted=0`, `mmap_attempted=0`, and `power_write_attempted=0`.
- Optional `--materialize-devnode` creates `/dev/kgsl-3d0` only from the read-only `/sys/class/kgsl/kgsl-3d0/dev` major/minor.

## Kernel Open Path Evidence

- `workspace/private/tmp/gpu-g0-kernel-src/drivers/gpu/msm/kgsl.c:4982-4990` wires `.open = kgsl_open`.
- `kgsl.c:1413-1445` shows `kgsl_open()` performs `pm_runtime_get_sync()`, creates device-private state, and then calls `kgsl_open_device()`.
- `kgsl.c:1372-1399` shows first open (`open_count == 0`) calls `device->ftbl->init(device)` and then `device->ftbl->start(device, 0)` before completing `hwaccess_gate`.
- `kgsl.c:5090-5097` shows platform probe initializes KGSL power control before registration can be useful.

## Adreno/GMU Start Evidence

- `workspace/private/tmp/gpu-g0-kernel-src/drivers/gpu/msm/adreno.c:1689-1719` shows `adreno_init()` transitions to `KGSL_STATE_INIT` and calls `gpudev->microcode_read()`.
- `adreno_a6xx.c:1123-1143` shows GMU firmware is requested through `request_firmware(gpucore->gpmufw_name)`; A640 uses `a640_gmu.bin`.
- `adreno_a6xx.c:1328-1348` shows SQE firmware is also loaded through `request_firmware()`.
- `adreno.c:1926-2020` shows `_adreno_start()` transitions power state, starts MMU, sends GMU OOB GPU request, and sends the HFI start message before regular GPU command use.
- `adreno_a6xx_gmu.c:346-363` shows GMU boot waits for `A6XX_GMU_CM3_FW_INIT_RESULT == 0xBABEFACE` with a timeout.
- `adreno_a6xx_gmu.c:372-385` shows HFI init waits for `A6XX_GMU_HFI_CTRL_STATUS`.
- `adreno_a6xx_gmu.c:574-620` shows OOB GPU handoff waits for a GMU interrupt bit and can time out.
- `adreno_a6xx_gmu.c:681-691` shows A640/A680 send `H2F_MSG_START`.
- `adreno_a6xx_gmu.c:1008-1116` shows cold boot loads RPMh ucode, loads GMU firmware, configures CM3/HFI/fence registers, starts GMU, may turn on the GFX rail, and starts HFI.

## DTS/Power Evidence

- `workspace/private/tmp/gpu-g0-kernel-src/arch/arm64/boot/dts/qcom/sm8150-gpu.dtsi:66-83` identifies `kgsl-3d0`, chipid `0x06040000`, and `qcom,gpu-quirk-cx-gdsc`.
- `sm8150-gpu.dtsi:105-114` binds GPU clocks to GPUCC/GCC/L3 vote clocks.
- `sm8150-gpu.dtsi:141-145` binds GPU `vddcx` and `vdd` to `gpu_cx_gdsc` and `gpu_gx_gdsc`.
- `sm8150-gpu.dtsi:350-385` defines the GMU node with HFI/GMU IRQs, `vddcx`/`vdd`, GPUCC clocks, and AOP mailbox.

## Diagnosis

The unbounded native-init `open("/dev/kgsl-3d0")` hang is explained by the KGSL first-open path. It is not a passive devnode open: the first opener synchronously enters runtime PM, Adreno init, firmware request, GMU cold boot, GDSC/clock/RPMh/HFI setup, OOB GPU handoff, and ringbuffer startup before returning a file descriptor.

The most likely hang classes are:

1. Firmware path/readiness: `a630_sqe.fw`, `a640_gmu.bin`, or `a640_zap` visibility/loading while native-init has a different root/firmware search path.
2. GMU boot/HFI/OOB wait: CM3 FW init, HFI init, HFI start, or OOB GPU handoff timeout.
3. Power-domain transition: `gpu_cx_gdsc`/`gpu_gx_gdsc`, GPUCC clocks, AOP/RPMh GPU power sequencing, or GMU CX/GX rail state.

## Bright-Line Determination

There is no clean standalone sysfs bring-up hook analogous to the audio `adsp-boot` path in the audited KGSL/GMU source. The only bright-line-clean path is to let the existing kernel KGSL runtime-PM/open path perform the work, with firmware visibility fixed if `gpu g0-status` proves that is the issue.

If a bounded live probe shows immediate return or a firmware `ENOENT`/similar failure, G0 can continue by fixing firmware visibility without power writes. If the bounded live probe times out after firmware/devnode visibility is correct, the remaining root cause is inside GMU/GDSC/RPMh/HFI startup and the epic must be shelved as BLOCKED unless a kernel-owned, non-writing status/configuration gap is found. Direct GDSC/regulator/PMIC/GPIO/power-rail writes remain forbidden.

## Next Safe Live Step

When the A90 is reachable again:

1. Flash only through `workspace/public/src/scripts/revalidation/native_init_flash.py` after rollback gates.
2. Run `gpu g0-status`.
3. Run `gpu g0-open-probe --timeout-ms 2000 --materialize-devnode`.
4. If it times out, do not retry-loop and do not run unbounded open. Capture the single bounded result and decide whether the evidence points to firmware visibility or a forbidden power-domain dependency.
