# Native Init V3335 GPU Z3 Primary SETCRTC Live Validation

## Summary

- Cycle: `V3335`
- Track: GPU rung 4, Z3 zero-copy primary scanout.
- Result: PASS + OPERATOR EYE-CONFIRMED.
- Artifact flashed: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`
- Boot SHA256: `e7e0240e7894e9bd54a0a4fd5a3bf267b126097a5177ccd17686076528ea736b`
- Resident after flash: `A90 Linux init 0.11.103 (v3335-gpu-z3-primary-setcrtc)`
- Device identifiers, serial paths, network addresses, storage UUIDs, and raw logs are intentionally omitted.

## Flash Gate

- Rollback `v2321` image SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Fallback `v2237` image SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Fallback `v48` image SHA256 matched `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image SHA256 matched `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- Pre-flash resident was V3334 with selftest `pass=12 warn=1 fail=0`.
- Flash was performed only through `native_init_flash.py`; remote image SHA and boot readback SHA both matched the V3335 artifact.
- Post-flash native-init verify passed with version/status rc=0.
- Post-flash selftest stayed `pass=12 warn=1 fail=0`.

## Probe

Foreground setup:

```text
stophud
```

Command:

```text
gpu z3-imported-scanout-primary-probe --timeout-ms 60000 --hold-ms 12000 --materialize-devnode
```

The first host `a90ctl` invocation used its default timeout and disconnected before the 12 second hold completed. Device-side execution continued and completed; the full A90P1 telemetry was recovered from the managed bridge capture. `last` then reported `command=gpu code=0 duration=12243ms`.

Key telemetry:

- Result: `gpu.z3.scanout.result=z3-imported-scanout-primary-setcrtc-pass`
- Timeout/child state: `timed_out=0`, `child_killed=0`, `child_status=0x0`
- Buffer path: `kms-dumb-scanout-gem-prime-fd-kgsl-dmabuf-import`
- Display target: `1080x2400`, stride `4352`, bytes `10444800`, format `XBGR8888`
- KMS dumb: `dumb_create_rc=0`, `dumb_map_offset_rc=0`, `prime_export_rc=0`, `addfb2_rc=0`, `fb_id=30`
- KGSL import: `import_rc=0`, `info_rc=0`, size `10444800`, flags `0x140080`
- GPU render: `gpu_create_rc=0`, `render_rc=0`, `pm4_dwords=409`
- Semantic proof: `sample_count=64`, `match_count=64`, `exact_match_count=64`, `mismatch_count=0`, `output_other_count=0`
- Primary scanout: `base_present_rc=0`, `primary_setcrtc_attempted=1`, `present_rc=0`, `restore_rc=0`
- Copy removal: `kms_copy_attempted=0`, `primary_pageflip_attempted=0`
- Cleanup: `rmfb_rc=0`, `dumb_destroy_rc=0`, `close_prime_rc=0`, `close_drm_fd_rc=0`
- Timing: `texture_us=3506`, `gpu_wait_us=1657`, `sample_us=89977`, `present_us=10374`, command duration `12243ms`

## Health

- Follow-up selftest stayed `pass=12 warn=1 fail=0`.
- Follow-up version remained `A90 Linux init 0.11.103 (v3335-gpu-z3-primary-setcrtc)`.
- Operator visual confirmation: the held primary SETCRTC graph was visible and remained on-panel
  ("보인다 유지되는거 같다").

## Status

V3335 proves and eye-confirms the primary-CRTC zero-copy path: the GPU wrote directly into the
full-panel KMS scanout BO imported through KGSL, KMS presented that same framebuffer with primary
`SETCRTC`, the operator confirmed the held graph was visible and remained on-panel, and the base
framebuffer was restored before cleanup. This closes the overlay-plane blocker as an implementation
detour, not a zero-copy blocker, and closes GPU rung 4 / Z3.
