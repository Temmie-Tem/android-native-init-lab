# Native Init V3179 GPU G0 Firmware Visibility Audit

## Summary

- Cycle: `V3179`
- Track: GPU G0 KGSL open-hang diagnosis.
- Decision: `v3179-gpu-g0-firmware-visibility-host-audit`
- Result: HOST-SIDE AUDIT PASS; live runtime visibility still pending.
- Device flash: `no`.
- Device action: `no`.
- Candidate still awaiting live validation: `boot_linux_v3177_gpu_g0_bounded_probe.img`
- Candidate SHA256: `6aea73ef99a05fbc86336597a7631d9de80a57b162e74d95b20217c3d7a11fee`

## Artifact Evidence

The private factory firmware artifacts do contain the known A640 KGSL/GMU firmware payloads:

- AP `vendor.img.ext4.lz4` -> vendor ext4 `/firmware/a630_sqe.fw`
  - size: `32304`
  - SHA256: `a0e1b583f620fabe32729ce367959d1960638663244d7d0cfc21b9a5215a018b`
- AP `vendor.img.ext4.lz4` -> vendor ext4 `/firmware/a640_gmu.bin`
  - size: `37680`
  - SHA256: `3ff0c02708bbe78641db887fa62f3a7f9337934d0c2ce0b961ef7c43172591d2`
- BL `NON-HLOS.bin.lz4` FAT image contains the PIL/TZ ZAP set:
  - `image/a640_zap.b00`, size `148`
  - `image/a640_zap.b01`, size `6712`
  - `image/a640_zap.b02`, size `1968`
  - `image/a640_zap.mdt`, size `6860`

## Source/Runtime Link

- `sm8150-gpu.dtsi` names the secure GPU PIL firmware as `a640_zap`.
- The KGSL first-open path still requests SQE/GMU firmware through kernel `request_firmware()` before regular GPU use.
- V3177 `gpu g0-status` already checks the relevant runtime paths:
  - `/sys/module/firmware_class/parameters/path`
  - `/vendor/firmware/a630_sqe.fw`
  - `/vendor/firmware/a640_gmu.bin`
  - `/firmware/a630_sqe.fw`
  - `/firmware/a640_gmu.bin`
  - `/vendor/firmware/a640_zap.mdt`
  - `/firmware_mnt/image/a640_zap.mdt`

## Diagnosis Update

This weakens the host-side "firmware missing from available artifacts" explanation: the factory images do carry the
expected SQE, GMU, and ZAP payloads. The remaining firmware-class question is runtime visibility under native-init:
whether the mounted paths and `firmware_class.path` seen by the kernel first-open path expose those payloads.

The next live discriminator remains:

1. `gpu g0-status`
2. `gpu g0-open-probe --timeout-ms 2000 --materialize-devnode`

If `g0-status` shows SQE/GMU/ZAP missing at runtime, G0 should route only to a firmware visibility fix or mount/path
correction. If `g0-status` shows the firmware visible and the bounded open still times out, the remaining hang class is
inside GMU/GDSC/RPMh/HFI/OOB startup, and no audited bright-line standalone bring-up hook exists. Direct GDSC,
regulator, PMIC, GPIO, or power-rail writes remain forbidden.

## Safety

- No device contact, flash, reboot, KGSL open, ioctl, mmap, freedreno submit, or power write was performed.
- Private firmware images were read only on the host.
- No raw firmware blobs or generated private images are committed by this report.
