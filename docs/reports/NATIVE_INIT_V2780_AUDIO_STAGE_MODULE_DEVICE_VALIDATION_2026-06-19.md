# Native Init V2780 Audio Stage Module Device Validation

## Summary

- Cycle: `V2780`
- Track: audio stage module device validation.
- Decision: `v2780-audio-stage-module-device-validation-aborted-candidate-selftest-text-desync-rollback-recovered`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2779_audio_stage_module.img`
- Candidate SHA256: `6bb5aa207e378ea6a98115085e2af3316acc16ccf71ab4d5974b6f4d76f734ca`
- Candidate version observed: `0.9.298 (v2779-audio-stage-module)`
- Rollback target: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Final recovery state: `0.9.285 (v2321-usb-clean-identity-rodata)`, `selftest fail=0`

## Result

- V2779 booted successfully and the checked flash helper verified the candidate image with protocol `selftest` before returning control.
- Candidate `version` and `status` commands returned successfully over the serial bridge.
- Candidate `selftest verbose` returned protocol `rc=0 status=ok`, but its text stream was corrupted/truncated and did not include the literal `fail=0` token.
- The V2780 runner treated the missing `fail=0` text token as a hard failure and aborted before running the read-only audio checks.
- Audio command smoke was therefore not executed: no `audio status`, `audio profiles`, `audio profile`, `audio stages`, `audio prereq`, or `audio play --dry-run` result exists for this run.

## Failure Mode

- Failure class: runner validation gap, not native-init stage-module failure.
- The protocol envelope for `candidate-selftest` was intact: `cmd=selftest`, `rc=0`, `errno=0`, `status=ok`.
- The human-readable payload was desynchronized: the saved tail begins mid-output and omits the summary line that normally contains `fail=0`.
- Because `selftest_ok()` only scanned the stdout text for `fail=0`, the runner raised `candidate selftest did not report fail=0` despite the protocol success.

## Rollback

- The runner attempted checked rollback to V2321 using `native_init_flash.py --from-native`.
- The native-to-recovery request timed out with a bridge reset while issuing `recovery`, but the device reached recovery mode.
- A manual checked V2321 flash was then run through `native_init_flash.py` from recovery.
- The manual rollback verified the boot readback SHA256, booted V2321, and completed protocol `selftest` with `fail=0`.
- Current post-incident proof: `version` reports `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)` and `selftest` reports `pass=11 warn=1 fail=0`.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was written.
- No forbidden partitions were touched.
- No audio route apply, ACDB SET, mixer write, PCM open, PCM write, or playback execute was performed.
- Full private transcripts remain under `workspace/private/runs/audio/v2780-audio-stage-module-device-validation-20260619-042432/`.

## Next Unit

- Do not rerun V2780 unchanged.
- V2781 should harden the device-validation runner before another live attempt:
  - Accept structured protocol success for `selftest` when the text stream is desynchronized, while still preserving a hard `fail=0` proof from checked flash verification and final rollback health.
  - Add rollback fallback: if `--from-native` recovery handoff times out but ADB shows the device in recovery, rerun `native_init_flash.py` without `--from-native` instead of leaving the run incomplete.
  - Record both rollback attempts in the result/report.
