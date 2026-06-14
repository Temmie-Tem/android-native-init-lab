# Native Init V2328 Audio AUD-2 Live Preflight

## Summary

- Cycle: `V2328`
- Track: audio AUD-2 live validation.
- Decision: `adsp-preflight-missing-firmware`
- Result: BLOCKED BEFORE ADSP ACTIVATION
- Operator gate: AUD-2 live approval received in chat.
- Candidate flashed: `A90 Linux init 0.9.289 (v2327-audio-adsp-boot-once)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v2327_audio_adsp_boot_once.img`
- Candidate SHA256: `6269f5689562268a2625da68385586d18d582a9c3ce8243c715485b6a703697f`
- Rollback target: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence directory: `workspace/private/runs/audio/v2328-aud2-live-20260614-212214`

## Live Flow

1. Confirmed rollback images by SHA256:
   - V2321 clean USB identity rollback image matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
   - V2237 Wi-Fi-proven fallback matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
   - V48 final fallback existed and hashed to `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
2. Confirmed pre-flash resident native init was healthy: `selftest fail=0`.
3. Flashed V2327 through `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
4. V2327 booted and passed `version`/`status` verification.
5. Ran `version`, `status`, `selftest verbose`, and `audio adsp-status`.
6. Because preflight failed, no ADSP activation write was accepted.
7. Ran `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` once to verify the token path refuses before write when preflight is missing.
8. Rolled back to V2321 through `native_init_flash.py`.
9. Confirmed V2321 restored with `version`, `status`, and `selftest fail=0`.

## Key Evidence

V2327 health:

```text
A90 Linux init 0.9.289 (v2327-audio-adsp-boot-once)
selftest: pass=11 warn=1 fail=0
```

AUD-2 preflight:

```text
audio.firmware_class_path=/mnt/vendor/firmware
audio.boot_adsp_boot.exists=yes mode=220 type=file
audio.firmware_dir=/vendor/firmware_mnt/image exists=yes
audio.firmware.adsp_mdt=yes
audio.firmware.adsp_segments_present=16 expected=17
audio.proc_asound_cards=--- no soundcards ---
audio.dev_snd.count=0 control_like=0 pcm_like=0
audio.status.activation_write_attempted=0
audio.status.audio_playback_attempted=0
```

Segment discriminator:

```text
stat /vendor/firmware_mnt/image/adsp.b12: No such file or directory
stat /mnt/vendor/firmware/adsp.mdt: No such file or directory
stat /mnt/vendor/firmware/adsp.b12: No such file or directory
```

Gated boot command refusal:

```text
audio.adsp_boot_once.refused=missing-adsp-segments present=16 expected=17
audio.status.activation_write_attempted=0
```

Rollback health:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Classification

`adsp-preflight-missing-firmware`

The boot attribute exists and the mounted firmware directory is visible, but the served ADSP segment set is incomplete from the native-init view. The missing observed segment is `adsp.b12`. The kernel `firmware_class.path` also reports `/mnt/vendor/firmware`, where the ADSP files checked in this run were not present.

## Safety Result

- Actual ADSP boot write: not accepted.
- `audio.status.activation_write_attempted`: remained `0`.
- Audio playback/mixer/HAL/tinyalsa: not attempted.
- `/dev/subsys_adsp` open: not attempted.
- adsprpc invoke/ioctl: not attempted.
- Boot partition only was flashed.
- Rollback to V2321 completed and selftest remained `fail=0`.

## Next Step

Do not proceed to AUD-3. The next safe unit is host/source-side correction of the ADSP firmware preflight and serve path:

- determine why `firmware_class.path` is `/mnt/vendor/firmware` while V2327 validates `/vendor/firmware_mnt/image`;
- verify whether the stock AP/NON-HLOS image truly lacks `ADSP.B12` or whether the native mount/materialization path is hiding it;
- update `audio adsp-status` / `audio adsp-boot-once` to validate the actual firmware_class path, not only the hard-coded firmware mount path;
- only after the full ADSP segment set is visible should AUD-2 be re-run.
