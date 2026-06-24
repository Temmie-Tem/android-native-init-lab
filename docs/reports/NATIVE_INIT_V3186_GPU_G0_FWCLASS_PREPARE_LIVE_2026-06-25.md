# NATIVE_INIT_V3186 GPU G0 firmware-class prepare live validation

- Date: 2026-06-25
- Track: GPU G0, KGSL first-open hang diagnosis
- Source/build commit under test: `b30edc05` (`Build V3185 GPU G0 firmware-class prepare`)
- Boot artifact: `workspace/private/inputs/boot_images/boot_linux_v3185_gpu_g0_fwclass_prepare.img`
- Boot SHA256: `1fbab0b8e68adb01b7f3c4d9e52311b817ff58e3f8b843521f234b2b28fbc32c`
- Native init: `0.11.21` / `v3185-gpu-g0-fwclass-prepare`
- Rollback gate:
  - v2321 rollback image SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - v2237 fallback image SHA matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - v48 fallback image present
  - TWRP/recovery path was exercised by `native_init_flash.py --from-native`

## Flash

Command:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v3185_gpu_g0_fwclass_prepare.img \
  --expect-sha256 1fbab0b8e68adb01b7f3c4d9e52311b817ff58e3f8b843521f234b2b28fbc32c \
  --expect-version "A90 Linux init 0.11.21 (v3185-gpu-g0-fwclass-prepare)" \
  --from-native
```

Result:

- Local image marker, size, and SHA matched.
- Recovery ADB gate passed.
- Remote pushed image SHA matched.
- Boot partition write/readback SHA matched.
- Rebooted to system and native-init verify passed.
- No rollback was needed.

## Health

Post-flash resident:

```text
A90 Linux init 0.11.21 (v3185-gpu-g0-fwclass-prepare)
selftest: pass=12 warn=1 fail=0
```

A first combined `selftest && gpu g0-status` command lost A90P1 framing after
the selftest response. A standalone `version` recovered cleanly; `gpu g0-status`
then reported `busy` because the auto menu was active. Sending `hide` cleared the
menu guard and GPU commands ran normally.

## GPU G0 firmware-class prepare

Initial `gpu g0-status` after hiding the menu showed:

- `fwclass_path=/vendor/firmware_mnt/image`
- cache SQE/GMU present under `/cache/a90-runtime/pkg/gpu-g0-fw`
- vendor-mounted ZAP files present under `/vendor/firmware_mnt/image`

`gpu g0-fwclass-prepare` result:

```text
gpu.g0.fwclass_prepare.verify_a630_sqe.size=32304
gpu.g0.fwclass_prepare.verify_a640_gmu.size=37680
gpu.g0.fwclass_prepare.copy_a640_zap_mdt.copy_rc=0
gpu.g0.fwclass_prepare.copy_a640_zap_b00.copy_rc=0
gpu.g0.fwclass_prepare.copy_a640_zap_b01.copy_rc=0
gpu.g0.fwclass_prepare.copy_a640_zap_b02.copy_rc=0
gpu.g0.fwclass_prepare.fwpath.readback=/cache/a90-runtime/pkg/gpu-g0-fw
gpu.g0.fwclass_prepare.result=ok
```

The command completed in 12 ms and kept the intended G0 boundaries:

- no private firmware payloads in ramdisk/source
- no power writes
- no ioctl
- no mmap

Follow-up `gpu g0-status` confirmed:

```text
gpu.g0.fwclass_path=/cache/a90-runtime/pkg/gpu-g0-fw
```

## Bounded open probe

Command:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py \
  gpu g0-open-probe --timeout-ms 5000 --materialize-devnode
```

Result:

```text
gpu.g0.open.result=returned
gpu.g0.open.timed_out=0
gpu.g0.open.child_elapsed_ms=24
gpu.g0.open.open_rc=0
gpu.g0.open.open_errno=0
gpu.g0.open.ioctl_attempted=0
gpu.g0.open.mmap_attempted=0
gpu.g0.open.power_write_attempted=0
```

The full command duration was 27 ms. Post-probe health remained:

```text
selftest: pass=12 warn=1 fail=0
```

## Kernel log correlation

The post-probe dmesg tail showed a modem firmware timeout shortly before the GPU
open probe's ZAP load:

```text
[   64.480118] firmware modem.mdt: _request_firmware_load: firmware state wait timeout: rc = -110
[   64.480198] subsys-pil-tz 4080000.qcom,mss: modem: Failed to locate modem.mdt(rc:-11)
[   64.965425] subsys-restart: __subsystem_get(): __subsystem_get: a640_zap count:0
[   64.966550] subsys-pil-tz soc:qcom,kgsl-hyp: a640_zap: loading from ...
[   64.979741] subsys-pil-tz soc:qcom,kgsl-hyp: a640_zap: Brought out of reset
```

The modem timeout preceded the GPU ZAP load by about 0.49 s and came from a
different process context. This keeps the modem event as a separate background
signal, not evidence that the bounded GPU open regressed health.

## Conclusion

V3185 converts the V3184 manual firmware-class workaround into a reproducible
source command. With SQE/GMU staged in `/cache`, `gpu g0-fwclass-prepare`
successfully verified/cached firmware, redirected firmware_class, and the bounded
KGSL open probe returned in 24 ms with no timeout and no health regression.

Next frontier remains G0/G1 gating: repeat from a fresher boot if needed to
separate the recurring modem firmware timeout from GPU first-open timing, then
only advance beyond G0 after the side-effect story is clean.
