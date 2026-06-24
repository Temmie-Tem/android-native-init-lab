# NATIVE_INIT_V3191 GPU G2 GPUOBJ probe live validation

- Date: 2026-06-25
- Track: GPU G2a KGSL GPU object alloc/free probe
- Source/build commit under test: `18c0ce38` (`Build V3190 GPU G2 gpuobj probe`)
- Boot artifact: `workspace/private/inputs/boot_images/boot_linux_v3190_gpu_g2_gpuobj_probe.img`
- Boot SHA256: `47f0ace56dc3bcf1a9739723cc945825136632274a7892a710f14dc44d0c2d1b`
- Native init: `0.11.23` / `v3190-gpu-g2-gpuobj-probe`

## Flash

`native_init_flash.py --from-native` passed the checked flash path:

- local image marker, size, and SHA matched
- recovery ADB gate passed
- remote pushed image SHA matched
- boot write/readback SHA matched
- rebooted to system and native-init verify passed
- no rollback needed

Rollback gate before flash:

- v2321 rollback SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- v2237 fallback SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- v48 fallback image present
- recovery/TWRP path exercised by the checked helper

## Health

Post-flash resident:

```text
A90 Linux init 0.11.23 (v3190-gpu-g2-gpuobj-probe)
selftest: pass=12 warn=1 fail=0
```

Post-probe health stayed clean:

```text
selftest: pass=12 warn=1 fail=0
```

## G0 Prepare

Before G2a, the required firmware-class step was re-run:

```text
gpu.g0.fwclass_prepare.verify_a630_sqe.size=32304
gpu.g0.fwclass_prepare.verify_a640_gmu.size=37680
gpu.g0.fwclass_prepare.fwpath.readback=/cache/a90-runtime/pkg/gpu-g0-fw
gpu.g0.fwclass_prepare.result=ok
```

## G1 Recheck

Command:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow \
  gpu g1-context-probe --timeout-ms 5000 --materialize-devnode
```

Result:

```text
gpu.g1.context.result=created-destroyed
gpu.g1.context.timed_out=0
gpu.g1.context.open_elapsed_ms=25
gpu.g1.context.create_rc=0
gpu.g1.context.context_id=1
gpu.g1.context.flags_in=0x140012
gpu.g1.context.flags_out=0x148052
gpu.g1.context.destroy_attempted=1
gpu.g1.context.destroy_rc=0
gpu.g1.context.total_elapsed_ms=26
```

The inherited G1 reporting still showed `child_reaped=0` because it uses the
older immediate nonblocking reap path. This is the same hygiene issue documented
in V3189 and did not affect the G2a run.

## G2a Probe

Command:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow \
  gpu g2-gpuobj-probe --timeout-ms 5000 --materialize-devnode
```

Result:

```text
gpu.g2.gpuobj.parent_enters_open=0
gpu.g2.gpuobj.parent_enters_ioctl=0
gpu.g2.gpuobj.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_free,drawctxt_destroy
gpu.g2.gpuobj.alloc_size=4096
gpu.g2.gpuobj.alloc_flags=0x0
gpu.g2.gpuobj.mmap_attempted=0
gpu.g2.gpuobj.submit_attempted=0
gpu.g2.gpuobj.power_write_attempted=0
gpu.g2.gpuobj.result=allocated-freed
gpu.g2.gpuobj.timed_out=0
gpu.g2.gpuobj.child_killed=0
gpu.g2.gpuobj.child_reaped=1
gpu.g2.gpuobj.open_elapsed_ms=7
gpu.g2.gpuobj.open_rc=0
gpu.g2.gpuobj.create_rc=0
gpu.g2.gpuobj.context_id=1
gpu.g2.gpuobj.context_flags_in=0x140012
gpu.g2.gpuobj.context_flags_out=0x148052
gpu.g2.gpuobj.alloc_rc=0
gpu.g2.gpuobj.alloc_size_in=4096
gpu.g2.gpuobj.alloc_size_out=4096
gpu.g2.gpuobj.alloc_flags_in=0x0
gpu.g2.gpuobj.alloc_flags_out=0xc0000
gpu.g2.gpuobj.alloc_va_len=0
gpu.g2.gpuobj.alloc_mmapsize=4096
gpu.g2.gpuobj.gpuobj_id=2
gpu.g2.gpuobj.free_attempted=1
gpu.g2.gpuobj.free_rc=0
gpu.g2.gpuobj.destroy_attempted=1
gpu.g2.gpuobj.destroy_rc=0
gpu.g2.gpuobj.close_rc=0
gpu.g2.gpuobj.total_elapsed_ms=9
```

The full command duration was 11 ms. The kernel returned extra allocation flags
`0xc0000` and an `mmapsize` of 4096 for the 4096-byte object; mmap was not
attempted in this rung.

## Kernel Log Filter

GPU-related dmesg filter after the probe showed normal boot-time KGSL/GMU/SMMU
inventory plus the G1-triggered ZAP load:

```text
[    0.374384] gpu_cc_gmu_clk_src: set OPP pair(...)
[    0.391336] arm-smmu 2ca0000.kgsl-smmu: non-coherent table walk
[    0.582774] iommu: Adding device 2c6a000.qcom,gmu:gmu_user to group ...
[    0.585352] iommu: Adding device 2ca0000.qcom,kgsl-iommu:gfx3d_user to group ...
[   71.085364] subsys-restart: __subsystem_get(): __subsystem_get: a640_zap count:0
[   71.086530] subsys-pil-tz soc:qcom,kgsl-hyp: a640_zap: loading from ...
[   71.100563] subsys-pil-tz soc:qcom,kgsl-hyp: a640_zap: Brought out of reset
```

No KGSL/Adreno/GMU fault, oops, timeout, or selftest regression was observed in
the bounded G2a validation.

## Conclusion

G2a is live-proven at the narrow allocation/free rung:

- G0 firmware-class prepare passed.
- G1 context create/destroy still passed.
- KGSL GPUOBJ allocation of 4096 bytes returned success.
- KGSL GPUOBJ free returned success.
- Context destroy and close returned success.
- No mmap, command submit, freedreno rendering, or power write was attempted.
- Post-probe health remained `pass=12 warn=1 fail=0`.

Next safe rung is G2b design only: confirm the KGSL mmap offset/semantics from
the kernel source, then add a bounded child-only mmap/munmap probe with GPUOBJ
free and context destroy cleanup still enforced before considering any submit.
