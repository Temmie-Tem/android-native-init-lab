# Goal: autonomous native-init forward loop (Codex)

Drive the A90 native-init project forward one **bounded V-iteration at a time** using
the proven cycle below. This file says WHAT to pursue; **`AGENTS.md` says HOW — its
safety invariants and flash gates are binding and override any sub-goal.**

> Running mode note: this loop runs unattended (incl. Codex bypass) and is **OPERATOR-PRE-AUTHORIZED
> BY PRINCIPLE (2026-06-15)**, not by an enumerated mechanism list. **The rule: the loop MAY
> self-authorize ANY device action that stays inside the "recoverable envelope" — it MUST NOT stop
> merely to ask for human approval, and MUST NOT treat a *new* mechanism as needing fresh approval as
> long as that mechanism stays inside the envelope.** Proceed.
>
> **Recoverable envelope (self-authorize freely):** an action whose only persistent writes are to the
> **boot partition** (via the checked flash helper) or to **runtime / ephemeral / temporary state**,
> AND which is **fully recoverable to `v2321` native init without manual partition repair**. This
> explicitly includes — but is **not limited to** — native-init flashes, ADSP activation,
> `tinymix`/PCM/`tinyplay`, USB-gadget reconfigure (control-channel preserved), booting a pinned
> stock-Android image, **temporary systemless Magisk measurement capsules** (auto-cleaned before
> rollback; writes confined to the Magisk module dir under `/data`; never format/wipe `/data`), and
> all reads/observation. Any future mechanism that meets the envelope test is likewise pre-authorized.
>
> **Bright line — NEVER self-authorize; STOP and report:** (1) any write to a **forbidden partition**
> (efs/sec_efs/modem/RPMB/keymaster/vbmeta/bootloader/dsp/keydata) = permanent brick; (2) raw
> `dd`/fastboot to any non-boot partition; (3) any **PMIC/regulator/GDSC/GPIO power write** (e.g. GPU
> GX-GDSC) — hardware-damage / hard-hang risk; (4) **destructive `/data`** (format/wipe userdata);
> (5) anything **not recoverable to `v2321`** (no known-good rollback image present).
>
> This relaxes only the *human-approval* gate; it does **not** relax the flash-safety machinery —
> every device step still obeys the `AGENTS.md` flash gates (rollback precondition, pinned + readback
> SHA, post-flash health check, **auto-rollback to `v2321`**, no cascading bad flashes); these stay ON
> because they are what makes unattended progress safe (a bad boot self-recovers and the loop
> continues; a disabled rollback would strand the device until morning). Audio writes keep to
> **observed/known-good routes and bounded/low amplitude — no blind smart-amp gain/boost poking**. The
> **"fails twice → stop" and anti-churn guards stay in force** (broad pre-auth removes *parking*, not
> the duty to stop grinding low-information plumbing). The operator accepts that a boot failure may
> need a manual TWRP/download-mode recovery in the morning — **that acceptance covers the boot
> partition ONLY.** When an action would cross the bright line or leave the recoverable envelope, STOP
> and report — never guess.

## North star — priority-ordered tracks (T1 → T2 → T3)

Pursue the **highest tier that still has a meaningful, safely-actionable next step**.
Drop to the next tier only when the current one is *saturated* or *meaningless* (criteria
below). Re-evaluate each iteration; you may climb back up if new work appears.

### Audio (ADSP/Q6) speaker — DONE ✅ (CORE device-proven + promoted `0.10.0`, 2026-06-19) — now BACKGROUND/optional

Internal-speaker playback works on-device as a self-contained native-init command: `audio play --execute`
runs the integrated worker (adsp boot → `/dev/snd` materialize → global **App Type Config** write → native
ACDB SET replay into `/dev/msm_audio_cal` → route apply → PCM write → cleanup), promoted to init `0.10.0`
(V2811/V2814 audible, V2812 build → V2815 promote). The unlock was the missing global App Type Config write
(numid 3122/3123 → kernel `app_type_cfg[]`, fixing `adm_open bit_width:0→16`); residual `q6asm` ENEEDMORE
(audstrm cal_type 15) is source-confirmed non-fatal. Boot chime, bounded `audio stop`, status/selftest/
screenapp surfaces, and a bundled chime preset all landed across the `0.10.x` line.

**AUDIO IS NO LONGER THE ACTIVE FRONTIER.** Safety still in force: amp ≤ 0.2, no WSA gain/boost / SP-bypass
writes; `v2321` stays the flash-gate rollback target. Magisk remains an Android-side *measurement* capsule
only, never a native-init runtime dependency. Full history (AUD-0 → AUD-5, V2324 → V2815): `CLAUDE.md` +
`docs/reports/` + `docs/operations/VERSIONING_POLICY.md`. Reopen only for an explicit audio polish/feature ask.

### ⚡ ACTIVE EPIC (operator-chartered 2026-06-19; re-scoped 2026-06-19) — Video PLAYBACK (frame streaming on the EXISTING KMS display)

> **This is now THE active frontier.** Audio CORE is device-proven + promoted (`0.10.0`); its Tier-C polish is optional background.
>
> **⚠️ KEY RE-SCOPE (operator, 2026-06-19): the DISPLAY IS ALREADY PROVEN — do NOT treat "can native init draw to the screen" as an
> open question.** `workspace/public/src/native-init/a90_kms.c` (682 lines) already does real **DRM/KMS**: opens `/dev/dri/card0`,
> `DRM_IOCTL_MODE_GETRESOURCES` → picks crtc/connector/mode, mmaps the active framebuffer (`kms_active_map`), and the HUD / menu /
> about screens render text+rects to the panel via `a90_kms_framebuffer()` + `a90_draw_text`/`a90_draw_rect`. So the framebuffer /
> cont-splash / "panel-init brick-caution" framing is MOOT — native init drives the panel today. **The video epic is therefore a
> PLAYBACK-PIPELINE problem on a proven display, not a display-feasibility problem.** Venus HW decode is NOT needed (demos use
> pre-rendered frames).
>
> **The real open questions (performance / pipeline, much lower risk than feasibility):**
> 1. **Full-frame blit throughput** — HUD draws occasional static text/rects; video needs full-screen bitmap blit at ~30 fps
>    (Bad Apple ≈ 6500 frames). Add a "blit a full framebuffer-sized bitmap into the mapped KMS fb" primitive (memcpy into the
>    existing map) and measure sustainable fps (downscale / lower color depth if needed). Page-flip vs direct-map is a tearing-polish detail.
> 2. **Frame streaming** — stream ~thousands of pre-rendered raw frames from storage (same pattern as audio PCM streaming).
> 3. **A/V sync** — time frame blits to the audio PCM position (audio engine already proven; needs the file/stream-PCM input path too).
>
> **VID-0 (host-only):** confirm the existing `a90_kms` fb is usable for full-frame blit (resolution/format/stride from `a90_kms.c`),
> design the host pre-processing (decode audio → 48k/stereo/16-bit PCM; render frames → raw bitmaps at fb format) + the on-device
> frame/PCM streaming + blit/sync loop. Deliverable: pipeline plan. **VID-1+ device steps:** add the blit primitive, measure fps with a
> test pattern, then wire pre-rendered Bad Apple frames + audio. Recoverable boot-partition flashes only; rollback `v2321`.
> **Bright lines still apply:** no backlight/PMIC/PWM/regulator/GDSC writes; forbidden partitions absolute. (Panel-init brick-caution is
> moot since `a90_kms` already drives the existing mode — do not regress into a from-scratch panel re-init either.)
>
> **⚡ IMPLEMENTATION RECIPE (web-validated, operator 2026-06-19) — build the playback path the DOCUMENTED standard way; do NOT re-derive or per-pixel-draw frames.**
> Our `a90_kms.c` already does the hard 80% (KMS modeset + a single DRM **dumb buffer** via `MODE_CREATE_DUMB`/`MAP_DUMB` + `mmap(MAP_SHARED)` + `SETCRTC`, format **XBGR8888**, stride-honored). The video upgrade is the textbook DRM-dumb-buffer playback pattern:
> 1. **Double-buffer + page-flip (kills tearing, gives vsync + the A/V-sync clock):** allocate a **2nd dumb buffer**, draw the next frame into the *back* buffer, then `drmModePageFlip()` (`DRM_IOCTL_MODE_PAGE_FLIP`) scheduled for the next **vblank**. The flip is async — a flip-complete **event arrives on the drm fd**; read it in the loop and use its vblank timestamp as the **frame cadence + audio-sync anchor**. (We currently have 1 buffer + one `SETCRTC`; add buffer #2 + the flip loop.)
> 2. **Frame update = bulk WC memcpy, NEVER per-pixel:** pre-render frames on the HOST to **linear XBGR8888 matching the fb stride**, then **`memcpy` the whole frame** into the mmap'd back buffer. Dumb-buffer maps are **write-combine** → *sequential* memcpy is fast (kernel docs: "fast WC memcpy"), but the existing per-pixel `a90_draw_rect`/font primitives are **slow on WC** and must NOT be used for full-frame video. Add a `a90_kms_blit_frame(fb, src, len)` bulk primitive.
> 3. **Constraints:** dumb buffers are **LINEAR-only** → frames must be linear + stride-aligned (downscale Bad Apple if full-res 30 fps is bandwidth-bound; measure real fps with a test pattern first).
> **Reference implementations to consult (fetch these — do not reinvent the ioctl sequence):** `serviceberry3/android_drm_dumb` (Android DRM dumb-buffer-to-screen, our exact platform); the dvdhrm drm-howto "modeset-double-buffered"/"modeset-vsync" + "Advanced DRM Mode-Setting API" (page-flip/vblank-event loop); FFmpeg's `kmsdrm` output device (same decode→memcpy-dumb→flip pattern; we do NOT run ffmpeg on-device — host pre-decodes to raw frames/PCM, device just streams+blits). We are software-only (no Mesa/GPU/Adreno) — this dumb-buffer+memcpy+page-flip path needs no GPU.
>
> **🎞️ SMOOTH-PLAYBACK STANDARDS (web-validated, operator REFERENCE 2026-06-20) — for the "frames feel choppy/judder" class.** The current stream play loop (`v319/30_status_hud.inc.c`) does **SD read → mono1 unpack → per-pixel upscale → blit → flip ALL serially per frame, with no prefetch** — so any per-frame variance (SD latency, the nested-loop scaler) makes frames late → judder, and with sync-drop on, dropped → stutter. The blit/double-buffer/page-flip skeleton is correct; what's missing maps to two industry standards:
> 1. **Frame pacing (AOSP/Android "Swappy" Frame Pacing library is the canonical impl).** Core rule: *"a consistent 30 Hz is smoother than a hybrid where some frames show for 16.6 ms and others 33.3 ms."* 30 fps content on the ~60 Hz panel must present **every source frame for a FIXED integer # of vblanks (here 2)**, scheduled to the display clock. We **already read page-flip completion events** (V2877) → use them as the vblank counter to hold each frame exactly 2 flips. Uneven hold = judder even at **zero** drops. Corollary: **a steady cadence beats chasing exact sync by dropping** — keep the V2927 direction of a *less* aggressive drop policy.
> 2. **Decode-ahead / render-ahead queue (producer-consumer ring buffer).** Standard streaming-player structure = a **compressed-frame queue + a decoded-frame queue**, with decode running *ahead* to keep the decoded queue full; presentation only does memcpy+flip off the decoded ring. This **decouples SD I/O + mono1 decode from the vblank deadline** (a 1–2 frame decode-ahead is enough to absorb our variance). Native init is largely single-threaded, so even a simple "decode the next 1–2 frames during slack" lookahead (not necessarily a full producer thread) gets most of the benefit.
> 3. **Push work to the host (extreme of "separate decode from the consumer").** Pre-render frames on the host at the **final on-screen resolution** so the device skips the per-frame upscale (the heaviest critical-path step), and/or pre-expanded format so it skips unpack — trading asset size (keep `mono1` at final res to stay compact). Device then ≈ read+memcpy only.
> **Refs:** Android Frame Pacing / Swappy (`developer.android.com/games/sdk/frame-pacing`, `source.android.com/docs/core/graphics/frame-pacing`), Raph Levien "Swapchains and frame pacing", render-ahead/decode-ahead queue (producer-consumer ring buffer). **This is REFERENCE/direction for the choppiness class — not a committed step; fold into the Bad Apple DoD #1 (presented ≥ 95 %) work.**

> **📍 STATUS (2026-06-20) — Bad Apple Player HUD demo DONE; pipeline proven end-to-end.** (Display proven; Venus not needed — the recon framing below is historical only.) Loop progress V2864→V2964:
> - DRM/KMS inventory (V2864), `video` command surface (V2865–V2867), animation scaffold (V2868–V2869).
> - **Q1 full-frame blit throughput** — blitbench live (V2871–V2872) ✅.
> - **Q2 frame streaming** — A90VSTR stream reader live (V2874–V2875) ✅.
> - **Q3 page-flip / vblank clock** — flipprobe 12/12 @ ~59.9 fps (V2876–V2877), stream page-flip mode (V2878–V2879) ✅ — the recipe's double-buffer + `drmModePageFlip` path is live.
> - **Audio file-PCM input** (V2880–V2881) ✅ — engine now plays arbitrary PCM, not only the 440 Hz tone.
> - **A/V co-run + sync** — AV PCM video co-run (V2882), AV sync telemetry + stream (V2884–V2886) ✅.
> - **Video cache** command + trusted cache + AV-sync + preset (V2904–V2912) ✅ — frames cached on SD for playback.
> - **Bad Apple asset** prepared host-side (V2903 wrapper) → seeded to SD cache → wired as `DEMO > Bad Apple` Player HUD.
> - **🎬 Bad Apple demo DONE ✅ (V2947 full-song / V2964 smooth)** — full 232 s / 6962 frames, **0 dropped**, even ~30 fps cadence, audio audible + A/V synced (operator-confirmed), BEAT FLASH + read-only dashboard live, `selftest fail=0`, init `0.10.49`. **All five Definition-of-Done criteria met** (see demo-targets). The journey validated the smooth-playback standards: uneven 16/50 ms pageflip cadence + full-HUD-repaint cost = visible stutter even at 0 drops → fixed via setcrtc default (V2960) + **incremental HUD repaint** (V2963/V2964).
> **🎬 Nyan Cat demo DONE ✅ (V2975/V2976, `A90VSTR2 pal8-rle` ~35× compression, 30 fps).** DOOM is now in progress
> (input solved via **serial doompad** over the command bridge — V3014/V3015 — no OTG keyboard / no touch needed; built-in
> touch is a concluded dead-end, see Touch block). **DOOM render scaffold (`doomgeneric`) is the active work.**
>
> **📌 Versioning / checkpoint plan (operator, 2026-06-21):**
> - **PATCH-level kept "demo checkpoint" DONE (V3021/V3022)** — built ONE image bundling the validated video pipeline +
>   **Bad Apple + Nyan** demos, then live-validated BOTH in that single image: Bad Apple full-song Player HUD and Nyan
>   Player HUD preview both passed, `selftest fail=0`, and rollback to v2321 passed. Kept milestone:
>   `A90 Linux init 0.10.72 (v3021-demo-checkpoint-badapple-nyan)`, boot SHA256
>   `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`.
>   This is NOT a MINOR roll and does NOT replace the v2321 rollback net — it locks in the known-good demo state before
>   further DOOM work can regress it.
> - **DOOM CORE DONE ✅ (V3032 visible frame / V3033–V3034 visible playable loop / V3035–V3041 dashboard, init `0.10.79`):**
>   doomgeneric runs the real shareware WAD, frames blit to the panel via KMS, serial-doompad input drives gameplay
>   (move/fire), DOOM dashboard/HUD added; device was left on the DOOM image for operator demo.
> - **0.11.0 (MINOR) RESERVED for video-epic close — GATED on a DOOM demo FINISHING/OPTIMIZATION pass first
>   (operator, 2026-06-22). Do NOT roll 0.11.0 on a rough DOOM.** Before promotion, do the polish round (same spirit as
>   Bad Apple's cadence/HUD-cost fixes): **frame pacing + sustained fps** (real-time → steadier matters more than for
>   Bad Apple), **640×400→1080×2400 upscale quality** (integer/aspect/letterbox), **dashboard incremental repaint**
>   (no full-HUD repaint per frame — reuse the V2963 lesson), **input responsiveness** (doompad→`DG_GetKey` latency,
>   simultaneous move+fire, key repeat), **DOOM audio** (music/SFX → PCM path, or explicitly defer per the "SFX optional"
>   ladder note), and **longer-session stability** (no hang over sustained play). THEN build the 0.11.0 promotion image
>   bundling Bad Apple + Nyan + the polished DOOM, live-validate all three, pin version+SHA+promotion report = video-epic
>   close. DOOM stays on the 0.10.x line through the finishing pass; v2321 remains the rollback net.
> - **0.11.0 VIDEO EPIC PROMOTION CLOSED ✅ (V3157, 2026-06-25):** `A90 Linux init 0.11.0
>   (v3157-video-epic-promotion)`, boot SHA256
>   `cc458455e64af62720eebe2f80d7f8b49ea8c8bd3a96368b8a5311b685c4ad33`. Same image live-validated
>   Bad Apple Player HUD 300 frames at `30065` fps_milli / 0 drops, Nyan Player HUD 300 frames at
>   `30053` fps_milli / 0 drops, DOOM WAD SHA match + 120-frame foreground loop (`rc=0`, 120 presented,
>   0 missed shared frames) + bounded background/SFX start (`audio_rc=0`, worker stopped cleanly). Reports:
>   `docs/reports/NATIVE_INIT_V3157_VIDEO_EPIC_PROMOTION_SOURCE_BUILD_2026-06-25.md` and
>   `docs/reports/NATIVE_INIT_V3157_VIDEO_EPIC_PROMOTION_LIVE_2026-06-25.md`. This closes the Video epic
>   and unlocks the reserved GPU G0 only under its bounded/bright-line rules.
> - **🎯 FRAME-PACING DIAGNOSIS CLOSED — next pass = SCALE optimization (operator, 2026-06-23).** The choppiness hunt
>   (V3061→V3101) is **done; stop telemetering.** By live measurement every infra stutter source was found and removed:
>   dashboard thermal-sysfs read (V3069/74), SETCRTC path → KMS pageflip (V3077), file handoff → `shared-mmap-seq` + pace
>   socket (V3079–88), and the **large 3:2 per-frame CPU scaler = confirmed stutter source (V3095, decision
>   `large-scaler-is-stutter-source`)**. At 1:1 the pageflip is flawless (`flip_delta ≈ 16.6 ms`, V3095/V3101); the only
>   residual is **DOOM-inherent 35 Hz logic on a 60 Hz panel with no interpolation** (V3101: half the visible frames repeat
>   the same `gametic`, `max_same_run=2`). That stepped motion is **DOOM being DOOM, NOT a bug and NOT a 0.11.0 blocker** —
>   frame interpolation is a separate quality backlog item, not part of this pass. **Do not add more tick/phase telemetry
>   units — the cause is proven.**
> - **SCALE optimization RESOLVED ✅ (V3124/V3128, 2026-06-23).** "Enlarge ⇒ slow" was an artifact of the presenter's
>   *per-frame CPU pixel scaling*, not of size. Fixed via **pre-scaled producer (1×) + `shared-mmap-direct-blit`**: the
>   engine pre-scales once into the large buffer it owns and the presenter does a direct shared-mmap blit (no second scale
>   copy, no full clear). V3128 audit confirmed **large per-frame scaling is off the critical path — the large DOOM frame
>   stays within the 16.6 ms vblank budget**. HW display-plane scaling was therefore not needed. Residual stepped motion is
>   the DOOM-inherent 35 Hz/60 Hz cadence (interpolation backlog, not a blocker). This fed directly into the V3157 promotion.
> - **DOOM host-only policy gate DONE (V3023)** — the WAD-backed `doomgeneric` frontier resumed after the V3020 host
>   probe; source provenance, WAD/runtime-private policy, boot-size caps, bounded command surface, and rollback-gated
>   live-validation requirements are now pinned without flashing or staging WAD data.
> - **DOOM private-source full-engine link DONE (V3024)** — the pinned private `doomgeneric` source now compiles 80
>   engine C files plus the A90 serial-doompad/runtime-WAD bridge into an AArch64 static private artifact; no WAD data,
>   ramdisk, boot image, or device action was produced.
> - **DOOM native-init command/boot bridge DONE (V3025)** — the V3024 private engine probe helper is now bundled into
>   the private V3025 boot candidate ramdisk as `/bin/a90_doomgeneric_private_engine_v3024`, and native-init exposes
>   `video demo doom engine-probe` plus `video.status.doomgeneric.*` / `video.demo.engine.active` status markers.
>   Input remains `serial-doompad-to-DG_GetKey`, sound remains `-nosound -nomusic`, WAD files in ramdisk are `0`, and
>   the generated private boot image SHA256 is `d028ece642793a7a6242295c86cd6caedbd533f733282120c0575116f012e95f`.
> - **DOOM command bridge live validation DONE (V3026)** — rollback-gated live validation flashed the exact V3025 image,
>   confirmed `version`/`status`/`selftest`, validated `video demo doom status` and `video demo doom engine-probe`
>   (`engine_probe.rc=0`, `timed_out=0`), then rolled back to V2321 with `selftest fail=0`. This proves the internal
>   serial-doompad-to-`DG_GetKey` bridge on-device; OTG keyboard is not required for this proof path.
> - **DOOM runtime-private WAD staging preflight DONE / CONTRACT READY (V3027)** — host-only preflight pinned the
>   runtime staging contract (`/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD`, max `67108864` bytes, SHA verify before
>   future command, cleanup after smoke, no public/ramdisk/boot WAD bytes) and confirmed public WAD count `0`.
>   Exactly one private IWAD/WAD candidate is now present and valid: `4196020` bytes, magic `IWAD`, SHA256
>   `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`.
> - **DOOM SD runtime WAD stage DONE (V3028)** — the selected V3027 WAD is now staged on the device SD runtime
>   path `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD` with device-side SHA256
>   `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`, size `4196020`, mode `0600`,
>   and post-stage `selftest fail=0`. No flash, boot image, ramdisk, public WAD, or forbidden partition path was touched.
> - **DOOM SD-WAD command implementation DONE (V3029)** — host-only source build produced the
>   `0.10.74` / `v3029-doomgeneric-sd-wad-command` private boot candidate
>   `boot_linux_v3029_doomgeneric_sd_wad_command.img` with SHA256
>   `9b45abb847ac64c9032f0e873038a3abf577e27f2dabc2ceccad8cd8e95cf804`. Native-init now has
>   `video demo doom verify --wad runtime-private --sha256 EXPECTED` and bounded
>   `video demo doom play [frames] --wad runtime-private --sha256 EXPECTED` handling around the SD-staged
>   WAD path `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`; the V3029 helper SHA256 is
>   `435dc0bda50dff6c27410ed727d4d513c02bfba89e876ff654a045cf00d26b44`. WAD files in ramdisk are
>   `0`, public WAD count remains `0`, and WAD bytes are not embedded in the boot image.
> - **DOOM SD-WAD command live validation DONE (V3030)** — rollback-gated live validation flashed the exact
>   V3029 candidate (`9b45abb847ac64c9032f0e873038a3abf577e27f2dabc2ceccad8cd8e95cf804`) through
>   `native_init_flash.py`, confirmed candidate `version`/`status`/`selftest fail=0`, validated
>   `video demo doom verify --wad runtime-private --sha256 EXPECTED` (`sha256_match=1`, `magic=IWAD`,
>   `ok=1`) and bounded `video demo doom play 4 --wad runtime-private --sha256 EXPECTED` (`rc=0`,
>   `timed_out=0`), then rolled back to V2321 with final `selftest fail=0`.
> - **DOOM WAD-backed visible frame/menu integration source build DONE (V3031)** — host-only source build
>   produced the `0.10.75` / `v3031-doomgeneric-visible-frame` private boot candidate
>   `boot_linux_v3031_doomgeneric_visible_frame.img` with SHA256
>   `1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`. The private helper now supports
>   `--wad-frame-dump ... --output /tmp/a90-doomgeneric-v3031-frame.xbgr8888`, and native-init exposes
>   `video demo doom frame [frames] --wad runtime-private --sha256 EXPECTED` to verify the SD WAD, request
>   one bounded raw `640x400` `xbgr8888` frame, blit it through the existing KMS dumb-buffer path, and restore
>   the DEMO > DOOM menu preview. WAD files in ramdisk are `0`, public WAD count remains `0`, and WAD bytes
>   are not embedded in the boot image.
> - **DOOM WAD-backed visible frame live validation DONE (V3032)** — rollback-gated live validation flashed
>   the exact V3031 candidate (`1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`)
>   through `native_init_flash.py`, confirmed candidate `version`/`status`/`selftest fail=0`, then ran
>   `video demo doom frame 8 --wad runtime-private --sha256 EXPECTED`: WAD SHA matched, `magic=IWAD`,
>   `render.ok=1`, `display.presented=1`, `display.rc=0`, and `doomframe` presented a 1080x2400 KMS
>   framebuffer. A bounded `video demo doom play 4 --wad runtime-private --sha256 EXPECTED` smoke also
>   passed (`rc=0`, `timed_out=0`). Rollback to V2321 passed with final `selftest fail=0`.
> - **DOOM WAD-backed visible playable loop source build DONE (V3033)** — host-only source build produced
>   the `0.10.76` / `v3033-doomgeneric-visible-loop` private boot candidate
>   `boot_linux_v3033_doomgeneric_visible_loop.img` with SHA256
>   `8fa375702a5023d9cc1f0811c310993a86f58154d658047b8edbe44eece30a97`. The private helper now supports
>   `--wad-frame-loop ... --input-state /tmp/a90-doomgeneric-v3033-input.state --frame-ms 50`; native-init
>   exposes foreground `video demo doom loop [frames] --wad runtime-private --sha256 EXPECTED`,
>   background `loop-start`/`loop-status`/`loop-stop`, and mirrors `doompad key` state into the helper input
>   file. Host keyboard control is via `host_doompad_keyboard_v3033.py` over the existing serial command bridge;
>   WAD files in ramdisk are `0`, public WAD count remains `0`, and WAD bytes are not embedded in boot.
> - **NEXT CHECKPOINT: V3034 rollback-gated visible playable DOOM loop live validation** — flash only the exact
>   V3033 boot image via `native_init_flash.py`, health-check, run foreground `video demo doom loop 8 --wad
>   runtime-private --sha256 EXPECTED`, then run `loop-start` with bounded host keyboard `doompad` transitions,
>   stop the loop, confirm presentation/input markers, and rollback to V2321.
> - Parallel optional polish: dashboard formatting, fonts/ASCII charset, beat-flash tuning.

**Historical recon framing (Venus HW-decode / cont-splash feasibility, VID-0/1/2):** SUPERSEDED — the display is
proven (see the re-scope + STATUS above) and Venus is **not** needed (demos use pre-rendered frames). The
original recon notes live in git history / `docs/reports/`. Do not regress into Venus PIL bring-up or a
from-scratch DSI panel init; bright lines (no backlight/PMIC/PWM/regulator/GDSC) still hold.

### Downstream demo targets (REFERENCE / direction only — NOT an active directive)

The payoff demos the audio + video tracks aim at. This is **direction, not a committed step list**
(refine the exact approach from recon results), and it is **gated**: do NOT start any item until its
prerequisites are actually proven. Until then this block is **orientation only** — e.g. it tells the
video recon to **optimize for a drawable display framebuffer (the demos need it), not Venus** (the
demos need no hardware video decode). Do not let it pull the loop off the one active frontier.

**Demo target ladder (operator direction, 2026-06-19): ① Bad Apple → ② Nyan Cat → ③ DOOM** —
increasing difficulty. Each builds on the same enablers (display framebuffer, audio, then input).

**Surface them under a `DEMO >` submenu in the native-init menu (operator direction, 2026-06-19).** Use the existing menu/app
pattern (`a90_menu.c` — same as `ABOUT >` / `CHANGELOG >` / the audio screens, rendered on the KMS framebuffer). Each demo = a
menu item whose handler launches the demo, and **each must be bounded + interruptible (key / duration / serial interrupt) and must
restore the menu+HUD on exit** (full-screen demos take over the framebuffer; redraw the menu when they end). Audio amplitude cap
(≤0.2) and best-effort/non-boot-blocking rules still apply. The `DEMO >` **scaffold can be built early** — wire `Audio` now (it just
delegates to the existing `audio play` / chime), and leave `Bad Apple` / `Nyan Cat` / `DOOM` as "coming soon" stubs that fill in as
each lands, so each demo becomes a simple "plug into the menu" task. **`Audio` and `Bad Apple` are DONE ✅** (Bad Apple = full-song
Player HUD, V2947/V2964 — see the Player HUD spec below); **`Nyan Cat` is the next rung**, with `DOOM` still a downstream stub. This `DEMO` corner lives in the **feature/test image**
(`0.10.x` audio-cmd / video line), not the `v2321` rollback baseline; promoting it is a separate later decision.

Enablers + demos, dependency-ordered (prereq in parens):
- **Boot chime = sound check** (prereq: audio — DONE) — PID-1 init plays a bundled bounded-amplitude
  chime at boot, **best-effort / non-fatal — never block boot on audio**. Minimal "audio integrated
  into the system" proof; a natural first use of the Tier-B `audio` command.
- **Display framebuffer** (prereq: none — this *is* the video recon's display sub-target) — a
  drawable inherited **cont-splash** surface (`/dev/dri/card0` or `/dev/fb0`) + region blit; **no
  from-scratch DSI panel init, no backlight/PMIC/regulator writes (brick-caution); if the splash
  surface is already torn down, STOP and report rather than re-lighting the panel**. This is the
  make-or-break probe for the whole demo ladder.
- **① Bad Apple** (prereq: audio [DONE] + display framebuffer) — B&W silhouette anim: pre-decoded raw
  frames + raw PCM + a sync loop (no codec, no Venus). The first AV-integration demo; audio half is
  already proven, so this is the strongest first target once the framebuffer lands.
  - **Presentation = "Player HUD" (operator direction, 2026-06-20).** Not a bare fullscreen playback — a
    composited player: **top region = the Bad Apple video** (source is 4:3; integer-upscale into the top of
    the 1080×2400 portrait fb), **bottom region = a live dashboard**. Each frame = render into the page-flip
    back buffer `[blit video region + draw dashboard]` → flip; the dashboard redraws at frame cadence.
  - **Dashboard telemetry — read-only `/proc`+`/sys` ONLY** (no writes; no PMIC/regulator/thermal-write —
    safety lines hold): CPU load (`/proc/stat` jiffies delta, `/proc/loadavg`), CPU temp
    (`/sys/class/thermal/thermal_zone*/temp`), GPU load (`/sys/class/kgsl/kgsl-3d0/gpubusy` —
    **expected ~idle: the blit is CPU memcpy, not GPU-accelerated; display the real value anyway, it is
    honest**), GPU temp (thermal zone), current frame `N/total`, and a **progress bar + `mm:ss`** position.
    Exact node paths to be confirmed by a read-only on-device probe on the feature image.
  - **A/V sync must be made *visible*, two layers:**
    - **(rigorous) drift readout + lamp** — show audio clock `A = PCM-consumed/48000` and video clock
      `V = frames-presented/fps` side by side with **`Δ = A−V` in ms** and a **sync lamp** (green `|Δ|<33ms`
      / yellow `<66ms` / red beyond). This is just surfacing the **already-built V2884/V2886 AV-sync
      telemetry** — no new infra. **Clock caveat:** PCM-bytes-written ≠ what is audibly playing (DSP
      buffering), so use the **DSP-consumed position** or subtract a **measured fixed latency**, else Δ shows
      a false constant drift.
    - **(intuitive) BEAT FLASH** (operator pick, 2026-06-20) — offline-extract onset/beat timestamps from the
      audio (ffmpeg, host-side, one-time) and **pulse a border/marker on those timestamps driven by the
      AUDIO clock**; when the flash visually coincides with Bad Apple's beat-synced motion accents, sync is
      self-evident on screen.
  - **Asset scope (current operator direction):** full song, downscaled. Bad Apple is **4:3 landscape**, so the
    video asset is **480×360** (≈21.6 KB/frame `mono1` × ~6960 frames ≈ **150 MB**; device-side integer-upscale
    ×2 → 960×720 into the top region). Full-res full-song ≈ 2.2 GB is too big for the SD cache — RLE format
    would fix that but is a later format-extension unit. Audio pre-rendered at **0.15 volume** (within
    the ≤0.2 cap). Host prep is **V2903** (`prepare_badapple_assets_v2903.py`) — source media stays private
    under `workspace/private/`, never committed.
  - **Generated asset (READY, 2026-06-20):** `workspace/private/demo-assets/video/v2903-badapple-480x360-full/`
    (private, uncommitted) — `video-stream/frames.a90vstr` (6962 frames, 480×360 `mono1`, 150,490,668 B,
    sha256 `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`) + `audio/audio.s16le`
    (48 kHz stereo S16LE, 0.15 vol, full 232 s, 44,561,952 B,
    sha256 `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`) + `video-stream/manifest.json`.
    **Next:** seed via the **V2900 chunked SD-cache uploader** (confirm the SD-cache size cap is ≥150 MB
    first), then wire the Player HUD handler. (`yt-dlp`+static `ffmpeg` live under `workspace/private/tools/bin/`
    for re-extraction / other demos.)
  - **🎯 DEFINITION OF DONE — Bad Apple demo (operator, 2026-06-20). Marker `pass=1` is NOT done; the run must
    also meet these. A run that passes its markers while dropping the picture is a FAIL, not a pass.**
    1. **Frames actually presented, not dropped to catch up** — over a *full-length* (not 300-frame slice) synced
       play, **`presented/total ≥ 0.95`** (drop rate < 5 %). **Explicit FAIL example: V2920 `presented=1
       dropped=299` (`first_presented_frame=299`, `initial_drop_late≈782 ms`)** — the audio anchor carried a
       fixed offset and the drop-policy threw away the whole picture. That is the bug to fix, not a pass.
    2. **Anchor-offset corrected** — the constant `initial_drop_late` (DSP/audio-start latency; the GOAL clock
       caveat above) must be **measured and subtracted** (or the anchor re-based / the initial catch-up capped)
       so video does not start "already late." Sync Δ within **±33 ms** after correction.
    3. **Audio audible + in sync** — the PCM track plays through the speaker (≤0.2 amp) time-aligned to the video,
       not merely "pcm_write_attempted".
    4. **Player HUD actually rendered** — bottom dashboard (CPU load/temp, GPU load/temp [honest ~idle], frame
       `N/total`, progress bar) **and the BEAT FLASH** are on screen, not just the layout split.
    5. **Full length** — the whole 232 s asset plays start→end (or an explicit operator-chosen clip), bounded +
       interruptible, restores menu+HUD on exit, rollback/health unaffected (`selftest fail=0`).
    Until all five hold, the Bad Apple demo is **in-progress**, not done. (This pins the *demo's* acceptance bar;
    it does **not** narrow the epic — Nyan Cat / DOOM remain the downstream ladder on the same pipeline.)
- **② Nyan Cat — 🎯 NEXT CHARTERED RUNG (operator, 2026-06-20)** (prereq: same as Bad Apple — all met). Color +
  looping animation + looping music; reuses the proven Player-HUD / page-flip / A-V-sync pipeline (still
  framebuffer-blit, still no Venus). **The format-efficiency Tier-1 work is folded in here as Nyan's *enabler*,
  NOT a standalone epic:** color frames raw blow up fast (mono1's 1-bit trick is gone → even a palette/RGB565 is
  several× bigger), so Nyan is the **concrete forcing function** that pulls in a **compact on-device-decodable
  format**. Design the format *from Nyan's actual needs* (palette-indexed and/or RLE / delta-frames for a short
  looping clip), with Bad Apple's `A90VSTR mono1` as the existing reference and the device staying light (cheap
  decode → bulk blit; no GPU/Venus). Deliverable = Nyan playing the Player-HUD demo *and* a small compact-format
  win proven on real content. (Do NOT build an abstract "format epic" with no consumer — bind every format unit
  to making Nyan playable/efficient.) Looping + short = also a good first test of seamless loop playback.
- **Touch bring-up** (prereq: none; parallel-able) — read the touch panel via evdev `/dev/input/event*`. The input
  track for DOOM. **Progress (2026-06-20): device FOUND, event-read NOT yet proven.** `inputscan` (V2977/78) enumerated
  9 input nodes incl. **`event6 sec_touchscreen`** + `event8 sec_touchpad`; `readinput event6` (V2979) timed out with
  **0 events** (`readinput-touch-sample-not-proven`).
  - **🔎 TWRP-validated recipe (operator host-side RE, 2026-06-20 — `workspace/private/inputs/firmware/twrp/recovery.img`):**
    TWRP's ramdisk has **NO touch enable / firmware-load / sysfs / chmod on input nodes** — it just **opens
    `/dev/input/event*` and reads**. So the panel is brought up by the **kernel built-in driver at boot; no userspace
    power/enable is needed** (bright lines safe — do NOT add PMIC/regulator/backlight writes for touch). Cross-check:
    native init **already reads input today** — `a90_input.c` opens `event0`/`event3` and reads **EV_KEY** (the menu
    nav buttons work), proving the input subsystem is live under native init. **Touch = the same subsystem, just
    `event6` with `EV_ABS`/`ABS_MT` instead of `EV_KEY`.**
  - **Recipe:** open `/dev/input/event6` `O_RDONLY|O_NONBLOCK` + poll (reuse the existing `a90_input.c` poll loop),
    and **add the multitouch-protocol-B parse**: `ABS_MT_SLOT` / `ABS_MT_TRACKING_ID` / `ABS_MT_POSITION_X` /
    `ABS_MT_POSITION_Y` / `BTN_TOUCH` / `SYN_REPORT`. The only gap vs today is the `EV_ABS/ABS_MT` parse path (current
    code parses `EV_KEY` only). **Live validation REQUIRES an operator finger-touch during the read window.** If a
    *real* touch still yields 0 events, only THEN suspect driver runtime-PM/suspend → else pivot DOOM input to the
    USB-keyboard fallback. So `0 events` so far ≈ "nobody touched in the window," not a hardware/power wall.
  - **🛑 CONCLUDED (2026-06-20, V2982–V2993): built-in touch is a DEAD END under native init.** With the operator
    physically touching during bounded windows, BOTH `event6 sec_touchscreen` and `event8 sec_touchpad` emitted
    **0 events** (V2982; reconfirmed V2989–V2991 dual-touch). The panel registers as a touch device but does not
    *deliver* events under native init (runtime-PM/suspend or panel-power coupling never resumed — not crackable
    within bright lines). **Decision `v2993-doom-input-frontier-pivot-keyboard-fallback`: DOOM input → USB keyboard
    over OTG** (the GOAL-anticipated fallback). The loop built an input MUX (touch/keyboard/button proxy, V2994–V2998)
    + DOOM keyboard gate (V3004–V3013).
  - **✅ SUPERSEDED (V3014–V3017): no OTG hardware wait for the next DOOM step.** The OTG keyboard path remains a
    fallback diagnostic, but V3014 added a serial `doompad` controller, V3015 validated its state live, V3016 wired
    that state into a bounded foreground KMS `doomplay` loop, and V3017 live-validated `video demo doom play 8`
    consuming `forward+fire` (`player.y 1200→1128`) with rollback to V2321 and `selftest fail=0`. The current input
    surface for DOOM iteration is therefore `serial-doompad-consumed`, not `external-hardware-stimulus-required`.
- **③ DOOM = capstone** (prereq: display + input [touch *or* USB-keyboard fallback]; audio SFX
  optional) — `doomgeneric`: `DG_DrawFrame` → framebuffer region, `DG_GetKey` → the proven input surface
  (`doompad` now; touch/USB keyboard remain fallback diagnostics). Combines display + input + audio; biggest jump
  (real-time render loop + interactive input). **Next safe unit after V3017:** host-only `doomgeneric`/WAD feasibility
  and asset-policy work. Do not flash a WAD-backed engine until source provenance, boot-size impact, IWAD/shareware
  asset policy, bounded runtime controls, and rollback validation are pinned in a source-build report.

**Venus (HW video decode) is NOT on this demo path** — it stays an optional, separate track for
real-video / headless-media, only if explicitly chartered later.

**T1 (now SATURATED) — analyzer / harness regression test suite (host-only, NO flash).**
As of 2026-06-13 the 12 `workspace/public/src/harness/a90harness/` modules and all 124 revalidation
scripts have accept + reject/edge tests (**964 tests green**). **This tier is covered — do NOT grind
it.** The overnight run already over-extended here onto frozen one-shot build wrappers and
closed-phase analysis scripts (low marginal value, an anti-churn violation in spirit). Only touch T1
to add a regression test for a **real bug you actually hit**, batched into a single commit — never
resume per-script coverage sweeps.

**T2 (fallback) — native-init / WLAN baseline improvement (device; flash authorized).**
Do not enter T2 from this closed-loop file without a fresh operator direction. If selected later,
advance the native-init baseline from the current V2312 test baseline with DESIGN → IMPLEMENT →
STATIC VALIDATE host-side, then DEVICE validation through the `AGENTS.md` flash gates. Wi-Fi
credentials may be available under `workspace/private/secrets/`; never log their values.

**T3 (fallback) — self-directed (host-only preferred).**
Build reproducibility / tooling hardening (e.g. mkbootimg round-trip verification,
build-script robustness), or another concrete frontier unit from the state docs. Prefer
host-only, safe units.

**Drop-tier criteria** — leave a tier when its meaningful units are genuinely covered/done,
it needs hardware/data not available (e.g. creds for full Wi-Fi validation), it is blocked
with no safe next step, or it would only re-confirm established facts (diminishing returns).
**When you change tier, record the trigger** in that iteration's report.

## Audio frontier history — CLOSED

The detailed V2428 → V2815 ACDB / App-Type / Magisk investigation log lived here; it is closed (audio DONE — see
the Audio section above). Full detail: `CLAUDE.md` + `docs/reports/`. No active audio directive remains.

## Read at the START of every iteration

- **this `GOAL.md`** — re-read it every iteration; the contract may be updated mid-run,
  so never rely on a cached copy from session start,
- `AGENTS.md` (binding safety/flash gates),
- `CLAUDE.md` (current state + safety),
- `tests/GOAL.md` (the host-only harness sub-goal detail) when on T1,
- the newest `docs/reports/NATIVE_INIT_*.md` (a few),
- `git log --oneline -15`.

## The cycle (repeat)

1. **STATE** — read the docs above; identify current baseline, last result, open thread.
2. **SELECT** — choose the single most appropriate next sub-goal: small, bounded, one
   V-iteration on the current frontier. Assign the next run/build identity per
   `docs/operations/VERSIONING_POLICY.md` (keep run ID / init version / build tag / SHA
   axes separate).
3. **DESIGN** — short plan; web research allowed when it helps; ground claims in source or
   docs.
4. **IMPLEMENT** — focused change in canonical `workspace/public/src/...` / `tests/` paths
   only.
5. **STATIC VALIDATE** — `py_compile` + `python3 -m unittest discover -s tests -p
   'test_*.py'` for touched Python; cross-compile touched C with `aarch64-linux-gnu-gcc`
   and verify with `file`; `git diff --check`.
6. **DEVICE** (only if the sub-goal needs a new boot artifact) — build via the checked
   build script, record SHA256, flash via `native_init_flash.py`, reboot, run the
   serial-bridge health check (`a90ctl version` / `status` / `selftest`), then the bounded
   non-creds validation this sub-goal calls for. On any failure → auto-rollback per
   `AGENTS.md`. T1 sub-goals skip this step entirely.
7. **REPORT** — write `docs/reports/NATIVE_INIT_VNNNN_<purpose>_<date>.md` (or a `tests/`
   coverage note for T1): redacted, metadata-only, no secrets/binaries.
8. **COMMIT** — one sub-goal per commit; scoped `git add` of the touched paths + the
   report; never `-A`. Message per project convention; end with the Co-Authored-By line.
9. **REPEAT** → back to STATE.

## 🟢 GPU epic — G0→G5 first-light DONE ✅, next rung = first triangle (overnight)

**Persistent HARD FRAMING (inherited by every GPU rung, do not deviate):**
- **freedreno / Mesa / KGSL-direct ONLY.** The proprietary Adreno blob path (libGLESv2/EGL/OpenCL via Bionic/Android
  userspace) is structurally impossible in static native-init and is **FORBIDDEN** — never write blob/EGL bring-up
  units (same HAL/blob wall that made audio a multi-hundred-cycle slog; chasing it = overnight churn, no device payoff).
- **Legitimate GPU driver bring-up, NOT exploitation.** Does NOT reopen the CLOSED kernel-security recon: no
  CVE-2023-33047 / UAF / memory-corruption / heap-spray / exploit-dev. KGSL is used only for normal command submission.
- **Bright lines absolute:** no GDSC / regulator / PMIC / GPIO / power-rail writes; bounded/timeout-guarded probes only
  (never an unbounded blocking `open()` as a loop unit). Recoverable boot-partition flashes only, rollback `v2321`.

**DONE — G0→G5 ladder complete + device-proven (V3174→V3206, init `0.11.30`, audit `v3206-gpu-epic-completion-audit-pass`).**
What was actually proven (first-light skeleton, *not* acceleration): G0 the `/dev/kgsl-3d0` open-hang root-cause = GPU
**firmware visibility / GMU cold-start blocking, NOT a power wall** → cleanly resolved by `firmware_class.path` prep
(pure sysfs, no power write), bounded open returns; G1 KGSL context create/destroy; G2 GPU buffer alloc + mmap; G3 noop
command stream submitted → fenced → retired (GPU executes submitted packets); G4 **A6xx A2D 2D solid-fill** rendered,
CPU-readback verified (`0xa5c3f00d`); G5 GPU-filled buffer CPU-copied into the KMS dumb framebuffer and presented
(`1080x2400`, `kms-blit-presented`). All with `proprietary_blob_attempted=0`, `power_write_attempted=0`, selftest
`fail=0`. **Honest boundaries (NOT done): no triangle/3D rasterization, no shader (no ir3 compiler ran), no compute, no
zero-copy/plane scanout (G5 is CPU-copy), and no demo is GPU-accelerated yet.** This is the control-path first-light,
the foundation — not graphics.

**NEXT GPU EPIC = first triangle (H0→H5, overnight deep target).** Threshold from fixed-function plumbing to *real GPU
graphics*: vertex buffer → vertex shader → rasterizer → fragment shader → a shaded triangle, readback-verified, blitted
to KMS. Reuses the proven G0-G3 core (context/buffer/submit/fence/readback) + G5 blit; swaps the 2D fill for a 3D draw.
- **H0** (host-only deep recon): study minimal A6xx 3D pipeline state (mesa fd6 + envytools regs); **hand-assemble the
  minimal ir3 shaders** (passthrough VS + constant-color FS) — do **NOT** bring up the full Mesa ir3 compiler (huge,
  not bounded); the freedreno "first triangle" tradition is hand-coded shaders.
- **H1** upload hand-assembled shaders + set SP (shader processor) state, verify no GPU fault → **H2** set 3D pipeline
  state (VFD/VPC/GRAS/RB) for one triangle into an offscreen buffer → **H3** bind a 3-vertex buffer, `CP_DRAW_INDX_OFFSET`,
  fence, readback → **H4** verify triangle pixels (interior = shaded, exterior = clear) via CPU readback = first-triangle
  proof → **H5** blit the triangle buffer to `/dev/dri/card0`. Each rung device-verifiable; GPU faults are recoverable.
- **Crux = the shader.** If hand-assembled ir3 proves too fiddly that is a real decision point — record it, do not
  escalate to the blob or to a full compiler port.

**STATUS (2026-06-25) — H1/H2 landed, H3 draw-envelope now retires but still draws no pixels.**
V3208 uploaded placeholder VS/FS shader objects and programmed SP shader state with no draw; V3210 programmed A6xx
GRAS/RB/VPC/PC/VFD/SP fixed-function 3D state into a private 128x128 offscreen target and retired cleanly with no draw.
V3212/V3213 added and flashed `gpu h3-draw-envelope-probe`: it binds command/color/event/VS/FS/3-vertex BOs, emits VFD
vertex-buffer/fetch/dest state plus direct non-indexed `CP_DRAW_INDX_OFFSET` (`packet=0x38`, `draw_initiator=0x84`,
`num_indices=3`), and stays inside the child-only KGSL timeout envelope. Live result: submit succeeded
(`submit_rc=0`, `pm4_dwords=170`) but the timestamp did not retire (`wait_rc=-1`, `errno=110`, `retired_timestamp=0`);
cleanup and post-probe selftest stayed clean. V3214/V3215 replaced the zero VS/FS payload with a hand-encoded ir3
`end + nop + nop + nop` stream (`0x0300000000000000`), added a boot-size gate after a rejected oversized image was
rolled back to V2321 cleanly, then flashed the corrected image. Live result: H3 now retires (`wait_rc=0`,
`retired_timestamp=1`, `fence_poll_rc=1`) with no GPU fault/hang signature, but the color readback remains unchanged
(`readback_changed_count=0`). This proves the previous H3 timeout was at least partly a non-terminating shader-stream
boundary, **not** H4 triangle proof. Next unit should replace the terminator-only payload with real minimal
hand-assembled ir3 VS/FS that writes clip-space position and a fragment color; do not claim triangle rendering until
readback changes with interior/exterior verification. V3216/V3217 made that first minimal shader-color attempt: VS uses
cat1 `mov.f32f32` to set `r0.z=0.0` and `r0.w=1.0` while VFD supplies `r0.xy`, FS writes `r0.x=1.0`, and H3 switches MRT0
to `FMT6_32_FLOAT` with output mask `0x1`. Live result still retired cleanly (`wait_rc=0`, `retired_timestamp=1`) but
readback stayed unchanged (`readback_changed_count=0`) and post-probe selftest stayed `fail=0`. This narrows the next
gap away from non-terminating shader streams and toward VS output/VPC destination, FS output/MRT linkage, or missing
draw/raster state required for pixels. V3218/V3219 then applied the concrete Mesa A6xx SP control gap: VS
`SP_VS_CNTL_0=0x00100080` (`FULLREGFOOTPRINT=1|MERGEDREGS`) and FS `SP_PS_CNTL_0=0x81000080`
(`FULLREGFOOTPRINT=1|INOUTREGOVERLAP|MERGEDREGS`). Live result again retired cleanly (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=454`) with no GPU fault/hang signature, but readback still
stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe
selftest stayed `fail=0`. That removes SP footprint/merged-reg control as the primary blocker; next bounded unit should
focus on FS output/MRT linkage, raster/depth/stencil/coverage enables, or a Mesa-diffed minimal draw-state packet gap.
V3220/V3221 then tested the narrow raster/coverage hypothesis by adding Mesa-derived GRAS defaults:
`GRAS_SC_RAS_MSAA_CNTL=0`, `GRAS_SC_DEST_MSAA_CNTL=0x4`, and `GRAS_SC_SCREEN_SCISSOR_CNTL=0`. Live result again
retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=455`) with
no GPU fault/hang signature, but readback still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`) and post-probe selftest stayed `fail=0`. That removes the tested GRAS raster coverage
defaults as the primary blocker; next bounded unit should focus on FS output/MRT linkage, VPC/RB output state, or a
Mesa-diffed minimal draw-state packet gap.
V3222/V3223 then tested the narrower VPC position/clip-cull linkage gap by changing `VPC_VS_CNTL` from stride-only
`0x00000004` to `0x00ff0004` (`PSIZELOC=0xff`) and adding `VPC_VS_CLIP_CULL_CNTL=0x00ffff00`,
`VPC_VS_CLIP_CULL_CNTL_V2=0x00ffff00`, plus `GRAS_CL_VS_CLIP_CULL_DISTANCE=0`. Live result again retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=30`) with no GPU fault/hang
signature, but readback still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`) and post-probe selftest stayed `fail=0`. That removes this tested VPC sentinel linkage
gap as the primary blocker; next bounded unit should focus on FS output/MRT or RB output linkage, or generate a
minimal Mesa-equivalent packet diff for the first draw.
V3224/V3225 then tested the bounded FS/MRT output component-mask hypothesis by changing `GPU_H3_COLOR_OUTPUT_MASK` from
`0x1` to Mesa's full RT0 mask `0xf`, which programs `RB_PS_OUTPUT_MASK=0x0000000f`,
`SP_PS_OUTPUT_MASK=0x0000000f`, and `RB_MRT0_CONTROL.COMPONENT_ENABLE=0x00000780`. Live result again retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=32`) with no GPU fault/hang
signature, but readback still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`) and post-probe selftest stayed `fail=0`. That removes the tested RT0 component-mask gap
as the primary blocker. The next bounded unit should generate a Mesa-equivalent first-draw packet diff, then test the
smallest resulting RB/CCU/FS-output or shader-output linkage delta before claiming H4.
V3226/V3227 then tested a concrete shader-mode gap from Mesa `fd6_program.cc::emit_shader_regs()` by adding
`SP_MODE_CNTL=0x00000005` and `TPL1_MODE_CNTL=0x000000a2` before the VS/FS program registers. Live result again retired
cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=186`,
`total_elapsed_ms=30`) with no GPU fault/hang signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe selftest stayed
`fail=0`. That removes this tested shader-mode setup gap as the primary blocker. Next bounded unit should continue the
Mesa-equivalent first-draw packet diff and test a small, draw-relevant missing static/init state group such as
`RB_INTERP_CNTL`/`RB_PS_INPUT_CNTL`/sample-position or the minimal `VPC_VARYING_LM_TRANSFER_CNTL`/SIV path.
V3228/V3229 then tested the narrow fragment-input default-state group from Mesa
`fd6_program.cc::emit_fs_inputs()` by adding explicit zero writes for `GRAS_CL_INTERP_CNTL`, `RB_INTERP_CNTL`,
`RB_PS_INPUT_CNTL`, `RB_PS_SAMPLEFREQ_CNTL`, `GRAS_LRZ_PS_INPUT_CNTL`, and `GRAS_LRZ_PS_SAMPLEFREQ_CNTL`. Live result
again retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=198`,
`state_reg_writes=74`, `total_elapsed_ms=30`) with no GPU fault/hang signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe selftest stayed
`fail=0`. That removes this tested fragment-input zero-state group as the primary blocker. Next bounded unit should
continue the Mesa-equivalent first-draw packet diff and test the minimal `VPC_VARYING_LM_TRANSFER_CNTL`/SIV path or
sample-position/static state group before claiming H4.
V3230/V3231 then tested the minimal VPC LM/SIV path from Mesa `fd6_program.cc::emit_vpc()` for the current
position-only linkage by adding `VPC_VARYING_LM_TRANSFER_CNTL[0..3]={0xfffffff0,0xffffffff,0xffffffff,0xffffffff}`,
`VPC_VS_SIV_CNTL=0x0000ffff`, `VPC_VS_SIV_CNTL_V2=0x0000ffff`, and `GRAS_SU_VS_SIV_CNTL=0`. Live result again retired
cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=209`,
`state_reg_writes=81`, `total_elapsed_ms=31`) with no GPU fault/hang signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe selftest stayed
`fail=0`. That removes this tested VPC LM/SIV group as the primary blocker. Next bounded unit should continue the
Mesa-equivalent first-draw packet diff and test a small sample-position/static state group or revisit the hand-assembled
shader output contract before claiming H4.
V3232/V3233 then tested a bounded Mesa `fd6_emit_static_context_regs()` group that was still absent from the hand-built
H3 stream by adding `GRAS_SU_CONSERVATIVE_RAS_CNTL=0`, `VPC_UNKNOWN_9210=0`, `VPC_SO_OVERRIDE=1`,
`VPC_RAST_STREAM_CNTL=0`, `PC_STEREO_RENDERING_CNTL=0`, `TPL1_PS_SWIZZLE_CNTL=0`, and
`SP_REG_PROG_ID_3=0x0000fcfc`. The flashed image booted as `0.11.43 (v3232-gpu-h3-static-context-probe)`, passed
post-flash and post-probe selftest (`pass=12 warn=1 fail=0`), and the H3 draw again retired cleanly (`submit_rc=0`,
`wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=223`, `state_reg_writes=88`,
`total_elapsed_ms=31`) with no GPU fault/hang signature. Readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still not reached. That
removes this tested static-context no-op/disable group as the primary blocker. Next bounded unit should revisit the
hand-assembled shader output contract or compare the remaining Mesa first-draw packet stream for a smaller
shader-output/RB linkage delta before claiming H4.
V3234/V3235 then tested the narrow shader-output/input-register overlap hypothesis by keeping VFD input in `r0.xy` but
moving VS clip-position output to `r1.xyzw`, moving FS color output to `r1.x`, and programming
`SP_VS_OUTPUT_REG0=0x00000f04` plus `SP_PS_OUTPUT_REG0=0x04` from Mesa `fd6_program.cc::emit_vpc()` /
`emit_fs_outputs()` output-regid mapping. The image built and flashed as `0.11.44
(v3234-gpu-h3-shader-output-probe)`, passed post-flash health (`selftest pass=12 warn=1 fail=0`), but the H3 draw
regressed to a child timeout (`result=timeout`, `timed_out=1`, `child_status=0x9`, `rc=-110`, duration about
`5004ms`) before any readback proof. A post-probe selftest still passed and a GPU fault/hang dmesg filter found no
match, but a follow-up `gpu g3-noop-submit-probe` also timed out, so the failed H3 can wedge the KGSL queue until
reboot. This removes r1 output split with the old `FULLREGFOOTPRINT=1` as a valid standalone fix. Next bounded unit
should keep the V3234 r1 split but bump VS/PS full register footprint to `2`; if that still times out, revert the r1
split and move to another Mesa packet delta before claiming H4.

**GPU backlog AFTER the triangle (do NOT pre-build; pull only when reached):**
- **2nd capability = a VISIBLE compute demo (e.g. Mandelbrot/particle → KMS).** Reuses the shader path minus the
  rasterizer; gives GPU compute a *screen consumer*. **Matrix/GPGPU math is absorbed here, NOT a standalone goal** —
  there is no module/library to load (OpenCL/BLAS = blob/Bionic wall; Mesa rusticl/turnip = full-stack port, unbounded),
  so any kernel is hand-assembled ir3, and an abstract matmul with no consumer is the forbidden "capability with no
  consumer" anti-pattern.
- **Modularization is NOT an epic — it is an extraction.** Do not design a `a90_gpu` API upfront. Once the triangle AND
  the compute demo are two real consumers pulling on the same G0-G3 core (rule of three), *extract* the common
  KGSL submit/fence/buffer layer into an internal helper as a bounded refactor. Keep the already-shared core clean
  meanwhile; formalize an API only after 2-3 real call sites reveal its shape.
- **zero-copy KMS/dmabuf scanout** (G5 CPU-copy → direct GPU-buffer scanout; crux = A6xx tiling/UBWC ↔ display modifier)
  — efficiency win, do *after* the triangle (premature on a solid fill).

## Stop conditions

- **CLOSED EPIC (operator-chartered 2026-06-19) = Video PLAYBACK pipeline on the EXISTING KMS display**
  (see the chartered Video section). Audio is DONE: CORE device-proven + promoted `0.10.0` + first demo
  (chime) passing; **audio Tier-C polish is now optional background, NOT the primary track — do not grind
  it.** **The display is ALREADY proven (`a90_kms.c` drives `/dev/dri/card0` for HUD/menu) — this is a
  playback-pipeline problem, NOT a display-feasibility probe.** **Pipeline + Bad Apple demo DONE ✅ (V2947 full-song
  / V2964 smooth, init `0.10.49`):** double-buffer/page-flip/blit, frame+PCM streaming, A/V sync, and the full-song
  Player HUD (0 dropped, ~30 fps, audible synced audio, BEAT FLASH + read-only dashboard). **Remaining is optional,
  non-blocking:** UI polish (dashboard/fonts/beat-flash). **Next chartered rung = 🎯 Nyan Cat (2026-06-20), with
  format-efficiency Tier-1 (compact on-device decode, e.g. palette/RLE) folded in as Nyan's enabler — bound to real
  content, not a standalone format epic.**
  Recoverable boot-partition flashes only, rollback `v2321`. **Bright lines:** no backlight/PMIC/PWM/regulator/GDSC
  writes; no from-scratch panel re-init; forbidden partitions absolute. Venus HW decode NOT needed (pre-rendered frames).
- **ACTIVE EPIC (overnight) = GPU first triangle (H0→H5)** — the GPU G0→G5 first-light ladder is DONE/device-proven
  (V3206, init `0.11.30`); the next rung is real GPU graphics (shaded triangle). See the "🟢 GPU epic" block for the
  H0-H5 ladder, the hand-assembled-ir3 crux, and the after-triangle backlog (visible compute demo → extracted
  modularization → zero-copy). Chosen deliberately as a *deep unattended overnight* target (not operator-ROI). Bluetooth /
  sensors / haptics / Wi-Fi SoftAP remain reference-only until separately chartered (attended daytime quick-wins).
- Device unreachable after an auto-rollback → STOP, leave an incident report.
- The same sub-goal fails twice → STOP or shelve it and move on; do NOT retry-loop.
- No sub-goal is safely actionable without the operator → STOP with a note (but T1 is
  almost always safely actionable, so this should be rare).

## Anti-churn guard (low-value *success* streaks)

The "fails twice → stop" rule does not catch *successful* but low-information work. Guard:

- If the last **3+ iterations** were host-only metadata / inventory / runner / cleanup /
  audit work with **no new tested behavior and no device validation**, treat that theme as
  **exhausted** and force a tier re-evaluation toward substantive work.
- A new test file that actually exercises previously-untested behavior is substantive (not
  churn). Mechanical sweeps with no new assertions are churn — **batch** them into one
  iteration, never one-V-per-item.
- Never let one theme justify its own next iteration ("previous left a backlog" is not a
  reason to continue past the streak limit).

## Out of scope / do not reopen

- **Kernel-security recon and kernel-observation phases are CLOSED.** See
  `docs/reports/NATIVE_INIT_KERNEL_SECURITY_RECON_PHASE_CLOSE_CHECKPOINT_2026-06-13.md`.
  Do NOT re-triage FastRPC/Binder/KGSL, build trigger/exploit/UAF helpers, attempt any
  memory-corruption trigger, do heap spray/reclaim, or flash `slub_debug`/debug-cmdline
  images. No exploit development.
- **KGSL `/dev/kgsl-3d0` open-block — RESOLVED (V3184, 2026-06-25).** The unbounded-`open()` hang was GPU
  **firmware visibility / GMU cold-start blocking**, fixed cleanly via `firmware_class.path` prep (pure sysfs,
  no power write); bounded open now returns. This unblocked the full G0→G5 GPU first-light ladder (DONE, V3206).
  Still **NEVER** run an unbounded blocking `open()` as a loop unit (use timeout-guarded bounded probes), and GPU
  work stays legitimate driver bring-up — it does **NOT** reopen kernel-security recon (no CVE/UAF/exploit-dev).
- **No doc / metadata / inventory cleanup as a track** (anti-churn trap).
- **Never reopen** external SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO paths for internal `wlan0`.
