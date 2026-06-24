# NATIVE_INIT_V3187 GPU G0 fresh-boot repeat

- Date: 2026-06-25
- Track: GPU G0, KGSL first-open hang diagnosis
- Resident under test: `A90 Linux init 0.11.21 (v3185-gpu-g0-fwclass-prepare)`
- Prior live report: `docs/reports/NATIVE_INIT_V3186_GPU_G0_FWCLASS_PREPARE_LIVE_2026-06-25.md`
- Device action: reboot only, no new flash

## Purpose

V3186 proved that `gpu g0-fwclass-prepare` plus a bounded KGSL open succeeds,
but the dmesg tail also showed a modem firmware timeout near the GPU first-open
window. This repeat reboots the same V3185 resident and runs G0 prepare/open
again before the modem timeout window to determine whether the modem event is
caused by the GPU open or is a separate boot background event.

## Procedure

1. Requested normal native-init reboot.
2. Waited for V3185 `version` over the bridge.
3. Re-ran `selftest verbose`.
4. Hid the auto menu guard.
5. Ran `gpu g0-fwclass-prepare`.
6. Ran `gpu g0-open-probe --timeout-ms 5000 --materialize-devnode`.
7. Captured dmesg tail immediately after open and again after passing the
   previous modem-timeout timestamp.
8. Re-ran `status` and `selftest verbose`.

A first post-reboot selftest attempt lost A90P1 framing; retrying with
`--input-mode slow` restored stable command framing. No device health regression
was associated with that host-side transport issue.

## Results

Fresh boot health:

```text
A90 Linux init 0.11.21 (v3185-gpu-g0-fwclass-prepare)
selftest: pass=12 warn=1 fail=0
```

G0 prepare:

```text
gpu.g0.fwclass_prepare.verify_a630_sqe.size=32304
gpu.g0.fwclass_prepare.verify_a640_gmu.size=37680
gpu.g0.fwclass_prepare.fwpath.readback=/cache/a90-runtime/pkg/gpu-g0-fw
gpu.g0.fwclass_prepare.result=ok
```

G0 bounded open:

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

Command duration for the bounded open was 29 ms. Post-open health remained:

```text
selftest: pass=12 warn=1 fail=0
```

## Dmesg timing

Immediate post-open tail showed GPU ZAP load success at about 52.83 s, with no
modem firmware timeout yet:

```text
[   52.833816] subsys-restart: __subsystem_get(): __subsystem_get: a640_zap count:0
[   52.834805] subsys-pil-tz soc:qcom,kgsl-hyp: a640_zap: loading from ...
[   52.848632] subsys-pil-tz soc:qcom,kgsl-hyp: a640_zap: Brought out of reset
```

After waiting beyond the previous timeout window, the modem firmware timeout
appeared at about 64.48 s:

```text
[   64.480106] firmware modem.mdt: _request_firmware_load: firmware state wait timeout: rc = -110
[   64.480202] subsys-pil-tz 4080000.qcom,mss: modem: Failed to locate modem.mdt(rc:-11)
[   64.480442] subsys-restart: __subsystem_get(): __subsystem_get: modem count:0
[   65.480738] subsys-restart: __subsystem_get(): __subsystem_get: modem count:1
```

## Conclusion

The fresh-boot repeat separates the two events:

- GPU G0 first-open succeeds at about 52.83 s after `g0-fwclass-prepare`.
- The modem firmware timeout occurs later at about 64.48 s.
- Health remains `pass=12 warn=1 fail=0`.

This makes the modem timeout a recurring boot-side background signal rather than
evidence that the bounded GPU G0 open is causing a regression. G0 now has two
successful bounded open observations on V3185 with no selftest regression.

Next bounded step is to keep G1 behind the same safety line: no GPU ioctl/mmap
or userspace rendering until a narrowly scoped G1 probe is designed with explicit
rollback and post-probe health checks.
