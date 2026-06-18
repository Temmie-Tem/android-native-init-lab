# Native Init V2785 Audio Route Core Apply Device Validation

## Summary

- Cycle: `V2785`
- Track: audio route core apply/reset device validation.
- Decision: `v2785-audio-route-core-apply-type-mismatch-blocked`
- Result directory: `workspace/private/runs/audio/v2785-audio-route-core-apply-device-validation-20260619-051634`
- Candidate image SHA256: `5ccea5238d5719ed43a015db2502a616be786a4245c502fb530cf4aed4b1eba2`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2785 flashed the V2783 route-API test image and reached the intended bounded write window: ADSP boot accepted, `/dev/snd` materialized, and `audio route internal-speaker-safe --dry-run --layer core` succeeded.
- The first live core apply stopped on the third selected control: `SLIMBUS_0_RX Audio Mixer MultiMedia1` returned `audio.route.bad_type ... expected=integer actual=1`.
- ALSA type `1` is `SNDRV_CTL_ELEM_TYPE_BOOLEAN`, so the route writer was too strict: numeric route values must support boolean mixer controls as well as integer controls.
- The failure happened before any feedback/endpoint/blocked smart-amp layer writes, ACDB SET, PCM open, PCM write, or playback.
- Auto-rollback to V2321 succeeded and final selftest reported `fail=0`.

## Follow-up

- V2786 fixes the source model by changing the route writer validation from integer-only to numeric INTEGER-or-BOOLEAN control acceptance.
- V2786 must build a new boot image and rerun the same core apply/reset validation; the old V2783 image must not be reused for the fix.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition was written.
- No forbidden partitions were touched.
- Public report contains metadata only; full command transcripts stay under `workspace/private/runs/audio/`.
