# Native Init V2976 Nyan Rung Completion Audit

## Summary

- Decision: `v2976-nyan-rung-completion-pass`
- Result: `1`
- Track: active Video playback / Nyan Cat compact color demo.
- Asset manifest: `workspace/private/demo-assets/video/v2973-nyancat-pal8-rle-preview/video-stream/manifest.json`
- Live result: `workspace/private/runs/video/v2975-nyan-real-preview-live-20260620-135253/result.json`
- Device action: `none` in this V2976 audit; it validates V2973/V2975 evidence only.

## Completion Criteria

- Real Nyan Player HUD playback: `1`
- Compact on-device format win: `1`
- Rollback proof: version_ok=`1` selftest_fail0=`1`

## Compact Format Evidence

- Format: `pal8-rle` / stream_version=`2` / palette_count=`128`
- Encoded payload bytes: `6552510`
- Raw pal8 bytes: `58320000` reduction_x100=`890`
- Raw XBGR bytes: `233280000` reduction_x100=`3560`
- Compression ratio milli vs pal8: `112` threshold=`<=200`
- Asset checks: `{'asset_id_ok': True, 'sha_ok': True, 'format_ok': True, 'stream_version_ok': True, 'geometry_ok': True, 'frames_ok': True, 'palette_bounded': True, 'rle_all_frames': True, 'compression_ratio_ok': True, 'raw_xbgr_reduction_ok': True, 'raw_pal8_reduction_ok': True, 'encoded_positive': True}`

## Playback Evidence

- Presented/dropped: `300` / `0`
- fps_milli: `30093` elapsed_ns=`9968905569` bytes=`6552510`
- Audio worker done: `1`
- Live checks: `{'decision_ok': True, 'result_pass': True, 'rollback_attempted': True, 'rollback_version_ok': True, 'rollback_selftest_fail0': True, 'video_cache_seeded': True, 'audio_sha_match': True, 'status_ok': True, 'verify_ok': True, 'play_pass': True, 'presented_all': True, 'dropped_zero': True, 'setcrtc_path': True, 'player_hud': True, 'pal8_pixel_format': True, 'sync_pass': True, 'audio_worker_done': True, 'audio_pass': True, 'audio_pcm_file_validated': True, 'audio_safety': True}`

## Interpretation

- V2975 proves the real Nyan `pal8-rle` stream plays in Player HUD with bounded PCM-file audio and clean rollback.
- V2973/V2976 prove the compact format requirement on real content: the encoded payload is several times smaller than raw pal8 and far smaller than raw XBGR8888.
- This closes the Nyan demo rung as a short real-content preview. Future work should be explicit polish or the next demo rung, not another Nyan bring-up retry.

## Safety

- V2976 performs no device action and reads only metadata/private JSON evidence.
- Raw media payloads and private run logs remain under `workspace/private/` and are not committed.
