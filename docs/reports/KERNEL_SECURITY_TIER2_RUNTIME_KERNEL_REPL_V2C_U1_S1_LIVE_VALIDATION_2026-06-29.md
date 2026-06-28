# Kernel Security Tier-2 Runtime Kernel REPL v2c U1/S1 - Live Validation

- Date: 2026-06-29
- Unit: `v2c U1 live` + `v2c S1 live gate`
- Decision: `a90-repl-v2c-u1-s1-live-pass-rollback-clean`
- Device action: yes
- Boot partition only: yes
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`

## Objective

Live-validate the v2c host-side REPL productization work on the already-proven
v1-repl image, then roll back to the clean v2321 baseline. This closes the live
gate for:

- U1 `read`, `call`, and owned-buffer-only `poke` CLI commands.
- S1A safe-op retry / serial-fragment hardening on the live op path.

## Flash Gate

Preflight:

- Rollback images present and SHA-checked:
  - v2321: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - v2237 fallback: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - v48 fallback: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Baseline v2321 before flash:
  - `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - `status`: rc `0`, status `ok`
  - `selftest verbose`: `pass=11 warn=1 fail=0`
- Bridge: running on `127.0.0.1:54321`, selected serial `/dev/ttyACM0`.

Candidate flash:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --expect-readback-sha256 b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65 \
  --bridge-timeout 240 \
  --recovery-timeout 180 \
  workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img
```

Result:

- Recovery/TWRP ADB reached.
- Remote pushed image SHA matched the candidate SHA.
- Boot partition prefix readback SHA matched the candidate SHA.
- Post-flash `version/status` verification passed.
- Post-flash `selftest verbose`: `pass=11 warn=1 fail=0`.

The version string still reports v2321 because the v1-repl image is a patch of
the v2321 base image; artifact identity is the helper-pinned boot-prefix SHA.

## Live REPL Validation

Private evidence was written under `workspace/private/runs/kernel/v2c-u1-live/`
and is not committed.

### v2a1 selftest over v2c driver

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/a90_repl.py selftest \
  --map workspace/private/runs/kernel/v2a1-repl-driver/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 35 \
  --safe-op-retries 3 \
  --retry-delay-sec 0.2 \
  --evidence-dir workspace/private/runs/kernel/v2c-u1-live/selftest
```

Result: `decision=a90-repl-v2a1-selftest-pass`, `ok=true`.

- Named peek `kgsl_pwrctrl_force_no_nap_store`: static qword match.
- Named peek `__kmalloc`: static qword match.
- Named call `printk(format, sentinel)`: verified resolution and sentinel echo.

### U1 read

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/a90_repl.py read \
  --map workspace/private/runs/kernel/v2a1-repl-driver/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 35 \
  --safe-op-retries 3 \
  --retry-delay-sec 0.2 \
  --evidence-dir workspace/private/runs/kernel/v2c-u1-live/read \
  --len 20 \
  kgsl_pwrctrl_force_no_nap_store
```

Result:

- `decision=a90-repl-v2c-u1-read-pass`
- `chunk_count=3`, `chunk_size=8`
- `static_image_match=true`
- `data_sha256=5642494b8364c16a197612eba47d416916d4059ae03f5a46a8aeeb285f5184c9`
- Raw data and runtime values redacted from public output.

### U1 call

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/a90_repl.py call \
  --map workspace/private/runs/kernel/v2a1-repl-driver/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 35 \
  --safe-op-retries 3 \
  --retry-delay-sec 0.2 \
  --evidence-dir workspace/private/runs/kernel/v2c-u1-live/call \
  --replay-safe \
  printk @repl_format 0xa90ca11
```

Result:

- `decision=a90-repl-v2c-u1-call-pass`
- `resolution.verified=true`, method `disasm-signature+xref+map`
- Argument and return values redacted from public output.
- Private evidence check, without printing raw values here: sentinel echo `true`,
  stub return seen `true`.

The call summary reported `return_value_count=3`; the extra line is consistent
with residual `A90R` ring content. The proof condition is the private sentinel
echo plus stub return, both present.

### U1 owned-buffer poke

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/a90_repl.py poke \
  --map workspace/private/runs/kernel/v2a1-repl-driver/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --timeout 35 \
  --safe-op-retries 3 \
  --retry-delay-sec 0.2 \
  --evidence-dir workspace/private/runs/kernel/v2c-u1-live/poke \
  --width 8 \
  0xaabbccddeeff0011
```

Result:

- `decision=a90-repl-v2c-u1-owned-poke-pass`
- `__kmalloc` and `kfree`: verified via export recovery.
- Checks passed: `kmalloc-owned-buffer`, `owned-buffer-poke-peek`, and
  `kfree-owned-buffer`.
- Raw pointer and value details redacted from public output.

Post-validation health before rollback:

- `status`: rc `0`, status `ok`
- `selftest verbose`: `pass=11 warn=1 fail=0`

## Rollback

Rollback command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --from-native \
  --expect-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --expect-readback-sha256 ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb \
  --bridge-timeout 240 \
  --recovery-timeout 180 \
  workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img
```

Result:

- Recovery/TWRP ADB reached.
- Remote pushed image SHA matched v2321 SHA.
- Boot partition prefix readback SHA matched v2321 SHA.
- Post-rollback `version/status` helper verification passed.
- Final sequential checks:
  - `version`: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - `selftest verbose`: `pass=11 warn=1 fail=0`

An attempted parallel final `version`/`selftest` pair produced the expected
host-side serial-lock / `ATAT` fragment noise. A sequential retry immediately
passed, so this is recorded as host concurrency noise, not a device health
failure. Continue to run live bridge validation commands sequentially unless a
future transport layer explicitly supports concurrency.

## Conclusion

v2c U1 is live-proven on the existing v1-repl image and the device is back on
clean v2321 with `selftest fail=0`. S1A's bounded retry path was sufficient for
the sequential REPL live flow; host-side parallel bridge users can still create
lock/noise and should be avoided or serialized by the caller.
