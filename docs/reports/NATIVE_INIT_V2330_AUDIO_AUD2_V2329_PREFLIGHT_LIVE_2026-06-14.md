# Native Init V2330 Audio AUD-2 V2329 Preflight Live

## Summary

- Cycle: `V2330`
- Track: audio AUD-2 live preflight validation.
- Decision: `adsp-preflight-effective-fwclass-path-incomplete`
- Result: BLOCKED BEFORE ADSP ACTIVATION
- Operator gate: AUD-2 live approval received in chat.
- Candidate flashed: `A90 Linux init 0.9.290 (v2329-audio-adsp-fw-preflight)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v2329_audio_adsp_fw_preflight.img`
- Candidate SHA256: `8ab5ae3bbd750ee871c52b040905652683894f9816e7c4e29bfae2b2695638d8`
- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence directory: `workspace/private/runs/audio/v2330-aud2-v2329-preflight-20260614-213818`

## Live Flow

1. Confirmed rollback images by SHA256:
   - V2321 clean USB identity rollback image matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
   - V2237 Wi-Fi-proven fallback matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
   - V48 final fallback existed and hashed to `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
2. Confirmed pre-flash resident native init was healthy: V2321 `selftest fail=0`.
3. Flashed V2329 through `workspace/public/src/scripts/revalidation/native_init_flash.py` only, with pinned `--expect-sha256`.
4. V2329 booted and passed `version`/`status` verification.
5. Ran V2329 `selftest verbose`; result remained `fail=0`.
6. Ran `audio adsp-status` before the gated write attempt.
7. Ran `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT`.
8. The first token command was rejected by the UI busy guard before reaching the audio handler; activation remained `0`.
9. Re-ran the token command once with `--hide-on-busy`; the audio handler refused before any ADSP boot write.
10. Ran `audio adsp-status` and `selftest verbose` after refusal.
11. Rolled back to V2321 through `native_init_flash.py` with pinned `--expect-sha256`.
12. Confirmed V2321 restored with `status` and `selftest fail=0`.

## Key Evidence

V2329 health:

```text
A90 Linux init 0.9.290 (v2329-audio-adsp-fw-preflight)
selftest: pass=11 warn=1 fail=0
```

Corrected ADSP segment model under the mounted APNHLOS firmware path:

```text
audio.firmware_class_path=/mnt/vendor/firmware
audio.firmware_dir=/vendor/firmware_mnt/image exists=yes
audio.firmware.adsp_mdt=yes
audio.firmware.adsp_segments_model=stock-sparse-b00-b11-b13-b16
audio.firmware.adsp_segments_present=16 expected=16
audio.firmware.adsp_segments_missing=none
audio.firmware.adspr_jsn=yes
audio.firmware.adspua_jsn=yes
```

Effective `firmware_class.path` lacks ADSP:

```text
audio.firmware_class_dir=/mnt/vendor/firmware exists=yes
audio.firmware_class.adsp_mdt=no
audio.firmware_class.adsp_segments_present=0 expected=16
audio.firmware_class.adsp_complete=no
```

Gated boot command refusal:

```text
audio.adsp_boot_once.version=1
audio.adsp_boot_once.scope=AUD-2-liveness-only
audio.status.audio_playback_attempted=0
audio.adsp_boot_once.refused=firmware-class-path-incomplete path=/mnt/vendor/firmware mdt=no present=0 expected=16 model=stock-sparse-b00-b11-b13-b16 missing=adsp.b00,adsp.b01,adsp.b02,adsp.b03,adsp.b04,adsp.b05,adsp.b06,adsp.b07,adsp.b08,adsp.b09,adsp.b10,adsp.b11,adsp.b13,adsp.b14,adsp.b15,adsp.b16
audio.status.activation_write_attempted=0
```

Rollback health:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Classification

`adsp-preflight-effective-fwclass-path-incomplete`

V2329 fixed the false `adsp.b12` blocker: the stock sparse ADSP set is complete under `/vendor/firmware_mnt/image`. The remaining AUD-2 blocker is the effective firmware loader path. PID1/Wi-Fi setup changes `firmware_class.path` to `/mnt/vendor/firmware`, and that path does not expose `adsp.mdt` or any expected ADSP split segment.

Because V2329 gates on the effective path, it refused before the `/sys/kernel/boot_adsp/boot` write.

## Safety Result

- Actual ADSP boot write: not attempted.
- `audio.status.activation_write_attempted`: remained `0`.
- Audio playback/mixer/HAL/tinyalsa: not attempted.
- `/dev/subsys_adsp` open: not attempted.
- adsprpc invoke/ioctl: not attempted.
- Boot partition only was flashed.
- Rollback to V2321 completed and selftest remained `fail=0`.

## Next Step

Do not proceed to AUD-3.

The next safe unit is a new AUD-2 serve-path design/build step:

- keep the sparse ADSP segment model from V2329;
- design a bounded way to make the effective `firmware_class.path` expose the same ADSP files visible under `/vendor/firmware_mnt/image`;
- do not write `/sys/kernel/boot_adsp/boot` until the effective path reports `audio.firmware_class.adsp_complete=yes`;
- keep any firmware path change explicit, logged, and rollbackable in rootfs/runtime state only; no partition writes.
