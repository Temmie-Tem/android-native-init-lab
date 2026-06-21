# Native Init V3022 Demo Checkpoint Bad Apple + Nyan Live Validation

## Summary

- Cycle: `V3022`
- Track: active Video playback / kept demo checkpoint before further DOOM integration.
- Decision: `v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback`
- Result before rollback: `1`
- Candidate: `v3021-demo-checkpoint-badapple-nyan` / `0.10.72` / `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3021_demo_checkpoint_badapple_nyan.img`
- Same-image validation: Bad Apple pass=`1` Nyan pass=`1`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Candidate Health

- Version OK: `1`
- Status OK: `1`
- Selftest before demos fail=0: `1`
- Video status markers: demo_surface=`1` badapple=`1` nyan=`1` incremental_hud=`1`
- Audio status OK: `1`

## Demo Results

### Bad Apple Full-Song Player HUD

- Pass: `1`
- Video cache source: `hit` hit=`1` uploaded=`0`
- Audio remote SHA matched: `1`
- Status/verify/play rc: `0` / `0` / `0`
- Frames: presented=`6962` dropped=`0` expected=`6962` fps_milli=`29980`
- Present/layout/path: `1` / `1` / `1`
- Sync pass: `1`
- Audio worker done/pass: `1` / `1`
- Play stdout: `workspace/private/runs/video/v3022-demo-checkpoint-badapple-nyan-live-20260621-164538/23_candidate-video-demo-badapple-fullsong-player-hud-av-play.txt`

### Nyan Cat Player HUD Preview

- Pass: `1`
- Video cache source: `hit` hit=`1` uploaded=`0`
- Audio remote SHA matched: `1`
- Status/verify/play rc: `0` / `0` / `0`
- Frames: presented=`300` dropped=`0` expected=`300` fps_milli=`27913`
- Present/layout/path: `1` / `1` / `1`
- Sync pass: `1`
- Audio worker done/pass: `1` / `1`
- Play stdout: `workspace/private/runs/video/v3022-demo-checkpoint-badapple-nyan-live-20260621-164538/40_candidate-video-demo-nyan-player-hud-av-play.txt`

## Evidence

- Result JSON: `workspace/private/runs/video/v3022-demo-checkpoint-badapple-nyan-live-20260621-164538/result.json`
- Output dir: `workspace/private/runs/video/v3022-demo-checkpoint-badapple-nyan-live-20260621-164538`

## Safety

- Only the boot partition was flashed, through `native_init_flash.py`.
- The exact V3021 SHA256 was checked before flash and requested as readback identity.
- Rollback target remained `v2321`; deeper fallbacks `v2237` and `v48` plus TWRP were preflighted.
- Raw media, generated boot images, and command transcripts remained private/untracked.
- No Wi-Fi connect/DHCP/ping, forbidden partition, Venus, GPU, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.
