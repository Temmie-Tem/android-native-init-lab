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

### ✅ SUPERSEDED — Video PLAYBACK / Bad Apple / GPU demo ladder — DONE (kept below for history)

> **POINTER (operator, 2026-06-28): Video/GPU AND SoftAP are both CLOSED. The single active epic is now
> `## 🟣 ACTIVE NOW — DELEGATED: Tier-2 Runtime Kernel REPL (v1-repl → v2a)` further down this file.**
> Bad Apple full-song demo, GPU first-light/triangle/compute/accel-2D/monitor/zero-copy rungs, and DOOM
> are all DONE and eye-confirmed; the loop pivoted GPU→SoftAP at V3336; SoftAP S0→S4 is DONE at V3344.
> Do NOT resume Video/Nyan/GPU/SoftAP work — go to the **Runtime Kernel REPL** delegated block. v2a is
> LIVE-PROVEN end-to-end (v1-slide, v1-repl slide/peek/poke/call, kallsyms extractor v2a0, named host
> driver v2a1, recovered-export allocator-backed poke round-trip v2a2). **The ACTIVE NEXT EPIC is now v2c —
> Tier-2 Kernel REPL PRODUCTIZATION (correctness + stability + usability)**; see the `▶ ACTIVE NEXT EPIC =
> v2c` block. v2c's centerpiece is fail-closed resolution (the kallsyms map silently mislabels regions —
> this bit v2a2). v2b "show-buf" bulk peek is superseded by v2c U1's host-side looped `read`. The text below
> is retained as reference history only.

> **(history)** Audio CORE is device-proven + promoted (`0.10.0`); its Tier-C polish is optional background.
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

## 🟢 GPU epic — first-light G0→G5 ✅, triangle H0→H5 ✅, compute C0→C3 ✅, accel-2D D0→D3 ✅, monitor M0→M3 ✅, zero-copy scanout Z0→Z3 ✅ (all eye-confirmed; GPU epic CLOSED), next = SoftAP server-endgame pivot

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

**FIRST TRIANGLE H0→H5 = DONE + EYE-CONFIRMED (2026-06-26, init `0.11.73`).** Operator visually confirmed a GREEN
RIGHT-TRIANGLE on the panel. The long no-pixel wall's root cause was the **blend/output register group**
(`RB_BLEND_CNTL=0xffff0100`, `RB_MRT0.BLEND_CONTROL=0x08040804`, `SP_BLEND_CNTL=0x100`) — found via a built
**cffdump-diff tool** (`native_gpu_h3_cffdump_diff_v3286.py`) against a local A640 cffdump reference: V3286 diff →
V3290 first pixels (`readback_changed_count=672`) → V3292 KMS present → V3295/V3296 strict linear-triangle proof
(`strict_linear_triangle_sample_proof=1`) → V3298 visual hold. Operator nudges that landed: FS-output `0xfc` invalid
regids, A640 device-DB magic regs (`freedreno_devices.py`, necessary-not-sufficient); ruled out HLSQ-rename and the
CCU-flush hypothesis. The H0→H5 detail below is retained as the done record. **The first triangle proves "GPU draws the
screen."**

**VISIBLE COMPUTE demo C0→C3 = DONE + EYE-CONFIRMED (2026-06-26, init `0.11.77`).** Proves "GPU does
real WORK" (the multipurpose-server motivation), not just display. The ladder mirrored H0→H5, reused the proven
G0-G3 KGSL submit/fence/buffer core + the H5 KMS present path, and swapped the 3D draw for a hand-assembled ir3
COMPUTE dispatch. Same HARD FRAMING and bright lines were preserved (freedreno/KGSL-direct, NO blob/EGL/OpenCL/BLAS,
NO power writes, NO panel re-init, recoverable, rollback `v2321`).
**Operator PRE-STAGED the compute reference (2026-06-26) so C0 starts warm and does NOT repeat the triangle's 40-probe
stall** — staged at `/tmp/a90-mesa-gpu-src/a6xx_compute_dispatch_reference.txt` (+ `comp_a6xx.cc` = Mesa computerator
hand-built a6xx compute cmdstream, `comp_fd6_compute.cc`, and `kern_*.asm` = known-good ir3 compute kernels). It pins
the ordered CS dispatch envelope, CS register offsets (from local a6xx.xml), the UAV output-buffer binding, and the
ir3 `stib`/`ldib` buffer ops.
- **C0** (host-only recon): confirm/encode the CS dispatch envelope from the staged reference — `cs_restore`→`SP_CS_*`
  program (CONFIG.enabled+nuav, CNTL_0/1, WGE_CNTL, BASE, INSTR_SIZE) + `CP_LOAD_STATE6 ST6_SHADER`; UAV bind
  (`SP_CS_UAV_BASE`/`USIZE` + `CP_LOAD_STATE6 ST6_UAV`); `CP_SET_MARKER RM6_COMPUTE`; `SP_CS_NDRANGE_0..6` + KERNEL_GROUP;
  `CP_EXEC_CS(ngroups)`; WFI. **Hand-assemble the kernel from `kern_invocationid.asm`** (do NOT port the Mesa compiler);
  reuse the V3246 ir3-disasm to verify bytes.
- **C1** dispatch the trivial kernel = `kern_invocationid.asm` (writes per-invocation id to the UAV buffer). **PASS
  criterion: readback `buf[i] == i` for grid 32 (or `changed_count>0` with the per-invocation pattern).** If unchanged,
  do NOT churn "what's missing" — immediately run the execution-proof bisect (CP_MEM_WRITE sentinel to `buf[0]` before
  `CP_EXEC_CS`; drop `KGSL_CONTEXT_NO_SNAPSHOT` and read GPU fault state), then register-diff against `comp_a6xx.cc`.
- **C2** Mandelbrot-or-pattern kernel: each invocation = one pixel → `z=z²+c` bounded escape loop (float `mul.f`/`add.f`/`cmps.f`
  + predicate/branch from `kern_branch.asm`) → color buffer. **Crux.** If ir3 float+loop too fiddly, FALL BACK to a
  simpler per-pixel kernel (gradient/xy-pattern) — still proves "GPU computes per pixel and shows it" — and record it.
  **V3302 used the fallback: a 128x128 workgroup-id UAV pattern, live readback-proven.**
- **C3** blit the compute output to `/dev/dri/card0` via the proven H5 present path (reuse tile→linear if needed);
  operator visually confirmed the rainbow gradient / square-grid fractal-like pattern on the panel = compute-demo close.
  **Matrix/GPGPU math is ABSORBED here** (no standalone matmul, no blob/BLAS). Modularization stays an extraction
  (rule-of-three) after the chain's consumers exist.

**② GPU-ACCELERATED 2D = texturing + frame blit/scale (D0→D3) = DONE + EYE-CONFIRMED.** The real acceleration payoff: the demo
player (Bad Apple/DOOM) blits frames via CPU `memcpy` today; make the GPU sample + scale + composite them. Brings up
the A6xx texture pipe (TPL1 sampler + texture/IBO descriptor) and a textured fullscreen quad — reuses the proven H
triangle pipeline (VS/raster/RB) + H5 present; the new pieces are the sampler state and an ir3 FS that does `sam`
(texture sample). Same HARD FRAMING / bright lines. **Apply the proven method: PRE-STAGE the reference first** (fetch
`fd6_texture.cc` + the fd6 tex-const/IBO emit + a6xx TPL1 regs, the same way compute used computerator) so D0 starts
warm and does not repeat a stall; carry the execution-proof bisect + register-diff-against-fd6 discipline.
- **D0** (host-only recon): A6xx texture/sampler state — TPL1 sampler descriptor + texture (IBO) descriptor + how the
  FS binds them (`CP_LOAD_STATE6 ST6_TEX`/`ST6_SHADER`), and the ir3 `sam` op. Hand-assemble a textured FS (sample tex
  at interpolated UV → output); reuse the triangle's VS/raster/RB. Verify bytes with the V3246 ir3-disasm.
  **V3304 landed the Mesa fd6 texture/TPL1 reference recon; V3305 landed the D1 textured FS shader-byte gate.**
- **D1** render a fullscreen quad sampling a STATIC test texture (e.g. an uploaded checkerboard) → readback proof that
  the FS sampled it (output matches the texture pattern). PASS = sampled pattern present, not clear. Same bisect if not.
- **D2** feed a REAL frame (a demo/SD-cache frame) as the texture; GPU scales/blits it to the output buffer → readback.
  PASS = scaled frame content in the buffer.
- **D3** wire the GPU textured-quad blit into the demo player's present path (replace the CPU `memcpy` blit); present +
  measure (fps / CPU freed); operator confirms the demo still renders correctly via the GPU blit = ② close. This makes
  the GPU a real CONSUMER of existing work and is the third call site for the ③ rule-of-three extraction.

**③ on-panel GPU-accelerated SYSTEM MONITOR (M0→M3) — DONE + EYE-CONFIRMED; this visible/useful consumer DELIVERED the
rule-of-three extraction.** Rather than a bare refactor, build a glanceable on-panel system dashboard (per-core/cluster
CPU, freq, thermals, GPU, battery) as a 4th real GPU consumer; building it forces a clean reuse of the G0-G3 KGSL core +
H draw + ②D texture/blit, so the ③ extraction falls out organically (GOAL discipline: formalize the API only after the
call sites reveal its shape). Useful for the server/appliance endgame, eye-confirmable, and **bright-line-trivially safe
— ALL reads (`/proc`,`/sys`) + KMS present, NO power writes.** Same HARD FRAMING.
- **M0** (data layer, host+device, read-only): build the sampler + history ring buffers from real sysfs/proc — per-core
  `/proc/stat`; **cluster auto-detect** (`cpufreq/related_cpus` + `cpuinfo_max_freq` + `cpu_capacity` + `/proc/cpuinfo`
  MIDR `0xd0b`=A76 / `0xd05`=A55) to label cores Prime/Gold/Silver (SD855 = 1×A76@2.84 + 3×A76@2.42 + 4×A55@1.78);
  `/sys/class/thermal/*` zones; KGSL `/sys/class/kgsl/kgsl-3d0/{gpu_busy_percentage,devfreq/cur_freq,temp}`; battery
  `power_supply/battery/{current_now,voltage_now,capacity,temp}` (device-total power; per-core power NOT cleanly
  available — model-estimate only, label as such). Enumerate the actual nodes on-device first; do not hardcode.
- **M1** render a static dashboard with the EXISTING draw primitives (text + filled rects from the G4/HUD path): per-core
  usage bars labeled by cluster, freq/temp/GPU/battery readouts. Eye-confirm the layout is correct.
- **M2** GPU-accelerated LIVE graphs: scrolling history line/area graphs via the ②D textured-quad/blit path, smooth
  real-time redraw (the continuous-repaint workload that genuinely exercises the GPU 2D path = the 4th consumer).
- **M3** polish + the **③ EXTRACTION**: with H-draw + compute + ②D-blit + monitor all pulling on the same core, extract
  the shared KGSL submit/fence/buffer/texture/present layer into a clean internal helper (bounded refactor; demos +
  monitor both call it); selftest stays green, all consumers still work. Operator eye-confirm the live monitor = ③ close.
  Then ④ zero-copy, or pivot to the server-endgame (SoftAP).

**STATUS (2026-06-27) — C0 host-only recon landed as V3299; C1 shader-byte gate landed as V3300; C1 native-init source/build + live UAV readback proof landed as V3301; C2 128x128 compute pattern source/build + live readback proof landed as V3302; C3 source/build + device-presented-held proof landed as V3303 and is now operator eye-confirmed; D0 texture reference recon landed as V3304; D1 textured FS shader-byte gate landed as V3305 and closed live as V3310; D2 real SD-cache Bad Apple frame texture readback closed live as V3311; D3 source/build first landed as V3312, live exposed a fork/protocol bug, and fork-fixed V3313 passed telemetry live validation plus a no-flash 60 s eye-confirm replay hold. V3314 added high-contrast `--start-frame 515` plus a stricter final-frame semantic gate; live presentation, hold, KMS, and health were clean, but exact source-pixel validation missed one scaled-edge sample (`semantic_match_count=63`, `semantic_mismatch_count=1`). V3315 fixed that validation-design gap with a bounded 3x3 source-neighborhood tolerance and passed live: `semantic_sample_count=64`, `match_count=64`, `exact_match_count=63`, `edge_tolerant_match_count=1`, `mismatch_count=0`, `output_other_count=0`, post-probe `selftest fail=0`, no GPU fault-filter match. The operator then visually confirmed the held GPU-blit output: "배드애플 보였다 프레임은 정상적으로 나오는거 같았다". Rung ② is DONE + EYE-CONFIRMED. NEXT = ③ modularization/extraction backlog.**

**STATUS (2026-06-27 M0 kickoff) — V3316 completed the required read-only node enumeration for the on-panel system
monitor. The device exposes CPU topology/frequency, `/proc/stat`, memory/load, KGSL GPU busy/frequency/temp, thermal
zones, and battery/power-supply nodes without writes. SD855 clusters are discoverable from `cpufreq/related_cpus` plus
max frequency as Silver `0-3` @ 1.7856 GHz, Gold `4-6` @ 2.4192 GHz, and Prime `7` @ 2.8416 GHz; implementation must derive
those labels dynamically and tolerate absent/empty thermal nodes. No boot artifact was built and no flash was run. NEXT =
M0 sampler + history ring probe telemetry (`gpu.m0.monitor.*`).**

**STATUS (2026-06-27 M0 live) — V3317 implemented `a90_monitor.c/.h` plus `gpu m0-monitor-sampler-probe`, built
`boot_linux_v3317_gpu_m0_monitor_sampler.img` (SHA256
`47dcc28d9a9de86a56258bfd066839d5d3e3c93f9c5b55e6de266d3ffb5ba813`), flashed through `native_init_flash.py`, and passed
live validation. Probe telemetry reported `cpu.count=8`, `cluster.count=3`, `history.count=3`, derived labels Silver
`0-3`, Gold `4-6`, Prime `7`, KGSL model `Adreno640v2`, GPU freq/temp, thermal zone summary, battery readouts, and
`power_write_attempted=0` / `kms_present_attempted=0`; post-probe selftest stayed `pass=12 warn=1 fail=0`. M0 is DONE.
NEXT = M1 static dashboard with existing draw primitives.**

**STATUS (2026-06-27 M1 live) — V3318 implemented `gpu m1-monitor-dashboard-probe` using the M0 sampler plus existing
draw/KMS primitives, built `boot_linux_v3318_gpu_m1_monitor_dashboard.img` (SHA256
`e5a3905e94f65d8a8a071955cea92ddd3e0037c0c3839946f9c5c2357fdd6858`), flashed through `native_init_flash.py`, and passed
live validation. Probe telemetry reported `cpu.count=8`, `cluster.count=3`, `history.count=3`, KGSL model
`Adreno640v2`, framebuffer `1080x2400` stride `4352`, `kgsl_submit_attempted=0`, `kms_present_attempted=1`,
`present_rc=0`, `hold_elapsed_ms=5000`, and `result=dashboard-presented`; post-probe selftest stayed
`pass=12 warn=1 fail=0`. M1 is DONE. NEXT = M2 GPU-accelerated live graphs via the 2D textured-quad/blit path.**

**STATUS (2026-06-27 M2 live) — V3319 implemented `gpu m2-monitor-live-graph-probe`, built
`boot_linux_v3319_gpu_m2_monitor_live_graphs.img` (SHA256
`4b78660fa1721006ec57f1295a02e65f32546638823f2c537a01dddc30b99fee`), flashed through `native_init_flash.py`, and passed
live validation. Probe telemetry reported the live monitor mono1 graph source (`480x360` stride `60`) scaled through the
proven D3 KGSL textured-quad path to a `960x720` target, `kgsl_submit_attempted=1`, `kms_present_attempted=1`,
`presented=12`, `present_rc=0`, `graph_points=13`, `graph_pixels_set=2724`, `cpu.count=8`, `cluster.count=3`, KGSL model
`Adreno640v2`, `pm4_dwords=409`, `semantic.sample_count=64`, `semantic.match_count=64`, `semantic.mismatch_count=0`,
`semantic.output_other_count=0`, and `result=monitor-live-graph-pass`; post-probe selftest stayed
`pass=12 warn=1 fail=0`. M2 is DONE. NEXT = M3 polish + shared KGSL submit/fence/buffer/texture/present extraction.**

**STATUS (2026-06-27 M3 live telemetry) — V3320 extracted the D3-named 2D present path into the shared
`gpu_2d_present_*` layer and routed both D3 video texture present plus M2 live monitor graphs through
`gpu_2d_present_create_session` / `gpu_2d_present_render_frame_to_kms`. Built
`boot_linux_v3320_gpu_m3_monitor_extraction.img` (SHA256
`dd2f4fa31b81340ad35477cb0d23655b9b837887272a4224926311e04ef43ea2`), flashed through
`native_init_flash.py`, and passed telemetry live validation. `gpu m3-monitor-extraction-probe --frames 12
--interval-ms 200 --timeout-ms 60000 --hold-ms 5000 --materialize-devnode` reported
`gpu.m3.extract.layer=gpu_2d_present_v1`, shared core `bo-map,sync-to-gpu,submit-wait,linear-readback,kms-copy`,
M2 delegate `result=monitor-live-graph-pass`, `presented=12`, `present_rc=0`, `semantic.match_count=64`,
`semantic.mismatch_count=0`, `semantic.output_other_count=0`, and
`result=shared-2d-present-monitor-pass`. Focused D3 regression with Bad Apple frame 515 for 3 frames also passed:
`extraction_layer=gpu_2d_present_v1`, `result=video-texture-present-pass`, `presented=3`, `present_rc=0`,
`semantic.match_count=64`, `semantic.output_other_count=0`; the operator confirmed the Bad Apple path was visible
and frames looked normal. Post-probe selftest stayed `pass=12 warn=1 fail=0`. M3 telemetry is DONE; explicit operator
eye-confirmation of the held live monitor panel remains if the ③ rung is to be marked eye-confirmed/closed.**

**STATUS (2026-06-27 M3 held replay) — No-flash V3320 live monitor replay was run for eye-confirmation. A 60 s hold
attempt intentionally hit the same `--timeout-ms 60000` budget and killed the child at timeout; follow-up selftest
remained `pass=12 warn=1 fail=0`. A second replay with `--hold-ms 45000` completed cleanly in `47454ms`:
`gpu.m3.extract.layer=gpu_2d_present_v1`, M2 delegate `result=monitor-live-graph-pass`, `presented=12`,
`graph_pixels_set=2732`, `cpu.count=8`, `cluster.count=3`, `semantic.match_count=64`, `semantic.mismatch_count=0`,
`semantic.output_other_count=0`, and `result=shared-2d-present-monitor-pass`; post-replay selftest again stayed
`pass=12 warn=1 fail=0`. A third replay with `--hold-ms 50000` also completed cleanly in `53661ms` with
`presented=12`, `graph_pixels_set=2722`, `semantic.match_count=64`, `semantic.output_other_count=0`, and post-replay
selftest `pass=12 warn=1 fail=0`. Operator eye-confirmation of the held live monitor panel is still pending before
marking the ③ monitor rung eye-confirmed/closed.**

**STATUS (2026-06-27 M3 60s hold budget fix) — V3321 fixed the V3320 visual-hold rough edge by splitting the monitor
parent watchdog into render timeout + visual hold budget + 5 s margin. Built
`boot_linux_v3321_gpu_m3_hold_timeout_budget.img` (SHA256
`48050046e743694d6e74ed6123b49f87d5d2dd0f87a44bd14e3d548431ca9a49`), flashed through `native_init_flash.py`, and
passed live validation. After hiding the auto menu, `gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200
--timeout-ms 60000 --hold-ms 60000 --materialize-devnode` reported `parent_timeout_ms=125000`,
`timeout_split=render-plus-visual-hold`, `timed_out=0`, `child_killed=0`, M2 delegate
`result=monitor-live-graph-pass`, `presented=12`, `present_rc=0`, `graph_pixels_set=2733`, `cpu.count=8`,
`cluster.count=3`, `semantic.match_count=64`, `semantic.mismatch_count=0`, `semantic.output_other_count=0`, and
`result=shared-2d-present-monitor-pass`; duration was `62502ms`. Focused D3 Bad Apple regression also stayed green
(`result=video-texture-present-pass`, `presented=3`, `present_rc=0`, `semantic.match_count=64`,
`semantic.output_other_count=0`) and post-probe selftest stayed `pass=12 warn=1 fail=0`. A no-flash operator replay then
confirmed the human-facing close: the first `hide` run showed the monitor graph but had possible auto-HUD interference;
the second run stopped auto-HUD with `stophud` first and again passed (`presented=12`, `timed_out=0`, `child_killed=0`,
`graph_pixels_set=2720`, `semantic.match_count=64`, `semantic.mismatch_count=0`, `semantic.output_other_count=0`,
duration `63588ms`, follow-up selftest `pass=12 warn=1 fail=0`). The operator confirmed: "보인다 유지되는거 같다".
The ③ monitor rung is DONE + EYE-CONFIRMED.**

**CLOSED RUNG HISTORY = ④ zero-copy KMS/dmabuf scanout (Z0→Z3).** This rung made the GPU-rendered
buffer the scanout buffer directly, with no CPU copy on the present path. The final solution is V3335:
full-panel KMS dumb scanout buffer imported into KGSL, rendered by the GPU, presented through primary
`SETCRTC`, then restored to the previous base framebuffer. Bright lines stayed unchanged: KMS present +
GPU only, NO backlight/PMIC/PWM/regulator/GDSC writes, NO panel re-init, recoverable boot-partition
flash, rollback `v2321`.
- **Z0 (host-only recon).** From the staged Mesa/freedreno sources in `/tmp/a90-mesa-gpu-src/` (fd6_gmem/resolve, the
  `fdl6_*` layout helpers, `a6xx.xml` RB/scanout regs) + the existing `a90_kms.c` modeset path, pin: what tiling/UBWC
  modifier the GPU writes for the demo/monitor color buffer, what DRM format-modifier the A90 display plane accepts on
  `/dev/dri/card0` (enumerate `drmModeGetPlane`/IN_FORMATS read-only), and whether a shared linear buffer or a tiled
  buffer with a matching modifier is the feasible zero-copy path. Enumerate the actual on-device plane formats — do not
  hardcode. Output: a written zero-copy feasibility decision + the exact buffer allocation/modifier recipe.
- **Z1 (allocator bridge proof).** Prove one shared scanout-linear allocation path before any present: a buffer that KMS
  can accept as an `XBGR8888` framebuffer and that can plausibly become the GPU render target. Keep the CPU-copy present
  path as the live fallback.
- **Z2 (shared GPU target + live present).** Make that shared buffer the actual GPU output target, then page-flip the
  GPU-rendered buffer directly to scan-out for one of the existing consumers
  (monitor graph or Bad Apple blit) with the CPU copy removed; measure CPU/fps/latency delta vs the copy path; confirm
  no GPU fault, `selftest fail=0`, rollback to `v2321` clean.
- **Z3 (eye-confirm + close).** Operator visually confirms the zero-copy consumer renders correctly on-panel and holds;
  record the measured efficiency win. Eye-confirm = ④ closed = **GPU epic closed**. Then re-charter to SoftAP.**

**STATUS (2026-06-27 Z0 modifier recon) — V3322 completed the no-flash display-side zero-copy feasibility pass.**
Read-only helper `a90_drm_modifier_probe_z0` was built as a static AArch64 binary
(`sha256=4e79afa9d7bdb470f8038876e4973dbcf60ae6f47a6f980036709549e6bb937a`), installed temporarily via
NCM/bridge-nc, and queried `/dev/dri/card0` only. Live result on resident `0.11.92`:
`plane_count=16`, `compatible_active_crtc=16`, `rect_props=16`, `DRM_CAP_ADDFB2_MODIFIERS=1`,
`DRM_CAP_PRIME=0x3 import=1 export=1`, all 16 planes expose `XBGR8888`, but no plane exposes an
`IN_FORMATS` modifier blob (`rc=-61`, modifier counts all zero). Therefore the explicit
`QCOM_TILED3`/UBWC modifier route is NOT evidenced on this display stack. The only safe Z1 route is
**implicit/legacy linear scanout**: keep `DRM_FORMAT_XBGR8888`, 960x720, stride 3840, and first prove
one shared scanout-linear allocation path (`msm` DRM GEM `MSM_BO_SCANOUT | MSM_BO_WC` and GEM/iova or
dmabuf bridge) before removing the current KGSL-linear → KMS CPU copy. If the existing KGSL path cannot
target/import that shared GEM/dma-buf, pivot the submit path to DRM `msm` for this rung or close
zero-copy as infeasible on KGSL-only. Report:
`docs/reports/NATIVE_INIT_V3322_GPU_Z0_ZERO_COPY_MODIFIER_RECON_2026-06-27.md`.**

**STATUS (2026-06-27 Z1 shared-linear allocator preflight) — V3323 completed the no-flash DRM msm
shared-linear preflight.** Helper `a90_drm_msm_shared_linear_probe_z1` was built static
(`sha256=d5e86d6b2ab180374977c14817867894d42538bf26ffe8817f41ba422950a4d2`), installed temporarily via
NCM/bridge-nc, and ran on resident `0.11.92` with pre/post `selftest fail=0`. Live result:
`DRM_CAP_DUMB_BUFFER=1`, `DRM_CAP_ADDFB2_MODIFIERS=1`, `DRM_CAP_PRIME=0x3 import=1 export=1`;
`DRM_IOCTL_MSM_GEM_NEW` with `MSM_BO_SCANOUT | MSM_BO_WC` succeeded for `960x720`, stride `3840`,
bytes `2764800`; `MSM_INFO_GET_OFFSET` succeeded; mmap/writeback samples succeeded; PRIME
export/import succeeded; `DRM_IOCTL_MODE_ADDFB2` accepted the GEM as `XBGR8888`; cleanup `RMFB` and
GEM close succeeded. `MSM_INFO_GET_IOVA` and `MSM_INFO_GET_FLAGS` returned `-22`, so Z1 proves the
display-side shared-linear scanout allocation path but **does not yet prove current KGSL submit can
directly target that memory**. Active next: find/prove a KGSL dma-buf/import-or-target route for this
GEM, or pivot the zero-copy source unit to DRM `msm` submit; do not remove the current KGSL→KMS CPU
copy fallback until a shared GPU target is proven. Report:
`docs/reports/NATIVE_INIT_V3323_GPU_Z1_SHARED_LINEAR_PREFLIGHT_2026-06-27.md`.**

**STATUS (2026-06-27 Z2 KGSL dma-buf import preflight) — V3324 proved the shared buffer reaches
both KMS and KGSL.** Helper `a90_kgsl_dmabuf_import_probe_z2` was built static
(`sha256=02ab83482f3f86231e65015a8cfe963b4fc7deebd5e12d888d7ab209da719d15`), installed temporarily
via NCM/bridge-nc, and ran no-flash/no-present/no-submit on resident `0.11.92` with pre/post
`selftest fail=0`. Live result: DRM msm `MSM_BO_SCANOUT | MSM_BO_WC` GEM for `960x720`, stride
`3840`, bytes `2764800` created and mmap-sampled; PRIME export succeeded; `ADDFB2` accepted it as an
`XBGR8888` KMS framebuffer; KGSL opened `/dev/kgsl-3d0`; `IOCTL_KGSL_GPUOBJ_IMPORT` with
`KGSL_USER_MEM_TYPE_DMABUF` imported the same PRIME fd (`id=1`, flags `0x140080`); `GPUOBJ_INFO`
returned `gpuaddr=0x500000000`, `size=2764800`, `va_len=2764800`; KGSL free, `RMFB`, and DRM handle
close all succeeded. This proves the allocator/import bridge needed for zero-copy. Next source unit:
replace the current `session->linear` KGSL allocation with the imported scanout GEM for the guarded
render target, then page-flip it only after readback/telemetry proves the imported BO was written
correctly; keep CPU-copy fallback. Report:
`docs/reports/NATIVE_INIT_V3324_GPU_Z2_KGSL_DMABUF_IMPORT_PREFLIGHT_2026-06-27.md`.**

**STATUS (2026-06-27 Z2 imported scanout render-target source build) — V3325 built the first guarded
native-init path that renders into a KMS-acceptable scanout GEM imported into KGSL.** Source adds
`gpu z2-imported-scanout-target-probe [--timeout-ms N] [--materialize-devnode]`. The child probe
creates a DRM msm `MSM_BO_SCANOUT | MSM_BO_WC` `960x720`/stride `3840` linear GEM, mmap-clears it,
exports PRIME, attaches it as an `XBGR8888` framebuffer with `ADDFB2`, imports the same fd through
KGSL `GPUOBJ_IMPORT` with `KGSL_USER_MEM_TYPE_DMABUF`, replaces the M3 shared `session->linear`
target with that imported object, submits the existing textured monitor graph PM4 into the imported
target, then validates readback semantics without a KMS copy or present. Static validation passed:
`py_compile`, focused V3325 unittest, V3321 M3 regression unittest, `git diff --check`, AArch64
compile smoke, and full boot build. Boot artifact:
`workspace/private/inputs/boot_images/boot_linux_v3325_gpu_z2_imported_scanout_target.img`
(`sha256=3c0d2180627c6fd35f8997e5a720931bb44c3793e83929a5ad66f8b6dd341112`, size `63778816`
bytes). Live flash/health passed on `0.11.93`; the first run was correctly blocked by a busy menu
(`rc=-16`) until `hide`, then the probe showed the functional proof: `drm.open_rc=0`,
`drm.msm_gem_new_rc=0`, `drm.prime_export_rc=0`, `drm.addfb2_rc=0`, KGSL import/info `0`,
`gpuaddr=0x500300000`, `render_rc=0`, `pm4_dwords=409`, `changed_count=691200`, semantic exact match
`64/64`, output-other `0`, no KMS copy/present, cleanup `0`, and post-probe `selftest fail=0`.
The only failing field was the pass-gate self-reference (`summary.result_rc` checked before the child
assigned final `result_rc`), so V3325 is a live functional PASS with a reportable gate false negative.
Reports: `docs/reports/NATIVE_INIT_V3325_GPU_Z2_IMPORTED_SCANOUT_TARGET_SOURCE_BUILD_2026-06-27.md`
and `docs/reports/NATIVE_INIT_V3325_GPU_Z2_IMPORTED_SCANOUT_TARGET_LIVE_FALSE_NEGATIVE_2026-06-27.md`.**

**STATUS (2026-06-27 Z2 imported scanout render-target pass gate live) — V3326 fixed the
V3325 pass predicate and closed the shared GPU target proof.** Source removes the premature
`summary.result_rc == 0` predicate from `gpu_z2_imported_target_summary_passed()` while leaving the
render path unchanged. Static validation passed (`py_compile`, V3326 focused unittest, V3325 source
contract, V3321 M3 regression, `git diff --check`, full boot build). Boot artifact:
`workspace/private/inputs/boot_images/boot_linux_v3326_gpu_z2_imported_scanout_pass_gate.img`
(`sha256=9a63d1f1c8c2ad8aac6cdf63232d71466b2bcf97b5bec5ad7fb62f45601d39d4`, size `64978944`
bytes). Rollback images were re-confirmed, flash used only `native_init_flash.py`, and live health
passed on `A90 Linux init 0.11.94 (v3326-gpu-z2-imported-scanout-pass-gate)` with `selftest fail=0`.
Live command `gpu z2-imported-scanout-target-probe --timeout-ms 60000 --materialize-devnode` returned
`gpu.z2.import.result=z2-imported-scanout-render-target-pass`, `result_rc=0`, DRM msm scanout GEM
create/export/`ADDFB2` all `0`, KGSL dma-buf import/info `0`, `gpuaddr=0x500300000`,
`render_rc=0`, `pm4_dwords=409`, `graph_pixels_set=2178`, `changed_count=691200`, semantic exact
match `64/64`, output-other `0`, `kms_copy_attempted=0`, `kms_present_attempted=0`, elapsed
`39525781ns`, and post-probe `selftest fail=0`. **Z2 shared scanout-linear GPU target is proven.**
Active next: Z3 page-flip/present the same imported FB directly, hold it for operator eye-confirm,
and record the CPU-copy removal/latency delta before closing the GPU epic. Reports:
`docs/reports/NATIVE_INIT_V3326_GPU_Z2_IMPORTED_SCANOUT_PASS_GATE_SOURCE_BUILD_2026-06-27.md` and
`docs/reports/NATIVE_INIT_V3326_GPU_Z2_IMPORTED_SCANOUT_PASS_GATE_LIVE_2026-06-27.md`.**

**OPERATOR REDIRECT (2026-06-27, Z3 present wall) — STOP iterating overlay-plane present variants;
present the imported scanout FB on the PRIMARY crtc via the already-proven SETCRTC path.** V3327–V3332
all failed the same step: presenting the imported MSM_BO_SCANOUT FB on a DPU **overlay** plane returned
`EACCES` then `SETPLANE/atomic EINVAL` (`-13` → `-22`). GPU render/import/semantic were all clean
(`64/64`); the failure is the DPU SSPP overlay-plane format/zpos/rect constraint, **not** a zero-copy
problem. Do NOT keep cycling legacy-setplane / master-fd / atomic / overlay-filter / overlay-state
variants — that is the overlay rabbit hole. Instead reuse the working full-screen present:
`a90_kms.c` `kms_present()` already does `DRM_IOCTL_MODE_SETCRTC` on the **primary** crtc with the
full panel mode (`mode.hdisplay × mode.vdisplay`) and gives `base_present_rc=0`. For Z3, allocate the
imported scanout GEM at **full panel size** (not 960×720 at an overlay offset), GPU-render the monitor
graph into it, `ADDFB2` (already `rc=0`), then present via that same base path with
`setcrtc.fb_id = imported_fb_id` — i.e. swap the dumb `fb_id` for the imported scanout `fb_id` in the
existing primary SETCRTC. That IS zero-copy (GPU output BO == scanout BO, no `memcpy`) and avoids the
overlay SSPP entirely. Keep the CPU-copy dumb base as live fallback. Then hold for operator eye-confirm
and record the CPU-copy-removal/latency delta = ④ close = GPU epic closed. If primary SETCRTC with an
imported PRIME/dmabuf FB itself fails, THAT is the real new datum to report — not another overlay variant.**

**STATUS (2026-06-27 Z3 primary SETCRTC pass + eye-confirmed) — V3335 implemented, live-validated,
and operator-confirmed the primary-CRTC zero-copy route after the overlay wall.** Source adds
`gpu z3-imported-scanout-primary-probe`, an `a90_kms_present_external_fb()` helper, dynamic full-panel
target overrides for the shared GPU 2D presenter, and stride-aware semantic/readback sampling for KMS
dumb pitch padding. Built `boot_linux_v3335_gpu_z3_primary_setcrtc.img`
(`sha256=e7e0240e7894e9bd54a0a4fd5a3bf267b126097a5177ccd17686076528ea736b`), flashed only through
`native_init_flash.py`, and booted `A90 Linux init 0.11.103 (v3335-gpu-z3-primary-setcrtc)` with
post-flash selftest `pass=12 warn=1 fail=0`. After `stophud`, live command
`gpu z3-imported-scanout-primary-probe --timeout-ms 60000 --hold-ms 12000 --materialize-devnode`
completed device-side in `12243ms` with `result=z3-imported-scanout-primary-setcrtc-pass`: full-panel
KMS dumb scanout target `1080x2400`, stride `4352`, bytes `10444800`; PRIME export `0`; KGSL dma-buf
import/info `0`; `render_rc=0`; semantic `64/64` exact; `kms_copy_attempted=0`; primary
`SETCRTC present_rc=0`; base FB `restore_rc=0`; cleanup `RMFB/dumb_destroy/close_prime/close_drm_fd`
all `0`; follow-up selftest stayed `pass=12 warn=1 fail=0`. The first host `a90ctl` read timed out
before the 12 s hold finished, but the bridge capture and `last` confirmed command rc `0`. The
operator then confirmed the held primary SETCRTC graph was visible and remained on-panel:
"보인다 유지되는거 같다". **Z3 is PASS + EYE-CONFIRMED; ④ zero-copy scanout is CLOSED, and the GPU
epic is DONE.** Reports:
`docs/reports/NATIVE_INIT_V3335_GPU_Z3_PRIMARY_SETCRTC_SOURCE_BUILD_2026-06-27.md` and
`docs/reports/NATIVE_INIT_V3335_GPU_Z3_PRIMARY_SETCRTC_LIVE_2026-06-27.md`.**

## 🟣 ACTIVE NOW — DELEGATED: Tier-2 Runtime Kernel REPL (v1-repl → v2a)

**Operator-chartered 2026-06-28. This is the single active epic.** Build a **flash-once runtime kernel
REPL** so future EL1/kernel experiments need NO reflash per step: after one flash, drive runtime kernel
**observe + execute** over the bridge. Exploit-free (NO RKP bypass) — it only reads memory, writes
**non-protected** data, and `call`s **real** kernel function entries; RKP does memory-protection only
(not behavioral monitoring), so this is not RKP-detectable. We already hold EL1 (we flash our own
kernel); this is operator RECON/debug tooling on an owned, bootloader-unlocked, patched device. Full
design + decisions: `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_DESIGN_2026-06-28.md`.

**Already proven (reuse, do not re-derive):**
- Tier-2 `.text` patch boots under RKP; Stage C proved a **new direct `bl printk`** executes under
  RKP_CFP. Plain `printk(fmt,...)` is at vaddr `0xffffff800813d8cc` (NOT `printk_emit` 0x...813c814).
- **`poke`** primitive LIVE-PROVEN (`build_kernel_runtime_poke_agent.py`): hijacks the corrected
  `force_no_nap_store` at file-off `0x8A73C8` / vaddr `0xffffff80089273b4`, room **212 B (53 instr)**,
  magic-guarded (MAGIC `0xA90C0DE5DEADBEEF`), protocol `{u64 magic,u64 addr,u64 val,u64 width}`.
- **`slide`** primitive LIVE-PROVEN (`build_kernel_tier2_repl_v1_slide.py`): a `.text` stub does
  `adr x1,.` + `bl printk` → host derives `slide = runtime_pc − (entry_vaddr + 40)`. This supersedes
  the heavy V2216 perf/codeword method; `/proc/kallsyms` is `%p`-hashed even at `kptr_restrict=0`.
- Reusable host helpers in `build_kernel_tier2_stage_c_direct_bl_printk.py`: `encode_bl`,
  `encode_adr_x0`, `kernel_vaddr`, `locate_printk_variadic_wrapper`, `recompute_boot_id`,
  `parse_boot_layout`, JOPP_MAGIC `0x00BE7BAD`, ROPP eor `0xCA1103D0`/epilogue `0xCA11021E`.

**🚨 BRICK LESSON (binding):** the first poke build bricked because its offset (`0x8A7920`) pointed at
`gpu_busy_percentage_show` (read at boot), and the `eor`+RKP-magic asserts passed because **every ROPP
function** begins that way. **Verify every patch target by its exact function FINGERPRINT (disasm
semantics), never by the generic ROPP shape.** The corrected `force_no_nap_store` asserts: word at
`0x8A73C8` == `0xD10103FF` (`sub sp,#0x40`), next word == `0xCA1103D0` (`eor`), magic at `0x8A73C4`,
next magic at `0x8A749C`. `force_no_nap` is never read/written at boot or by the periodic monitor.

**v1-repl = ✅ DONE / LIVE-PROVEN** (`build_kernel_tier2_repl_v1_repl.py`, image `b846ae9f…`, commit
f44b34c8). One flash-once 212 B stub in `force_no_nap_store`: magic guard + op byte → `op0 slide`,
`op1 peek(addr,len≤8)`, `op2 poke(addr,val,width)`, `op3 call(target,x0..x7)`, plain-`printk` output,
ROPP frame preserving x16+x17, `blr` to JOPP entries. Codex host-built + self-Gate-2'd; operator
re-Gate-2'd (all 48 instrs) + live-validated all four ops + rolled back V2321 `fail=0`: slide leaked,
`peek` of the stub entry returned its own first qword, `call printk(fmt,0xCAFE1234)` printed
`A90Rcafe1234` and captured return `0xc`, `op2` NULL-poke faulted (store path executes). Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V1_REPL_2026-06-28.md`.

**v2a0 = ✅ DONE (kallsyms extractor FIXED, commit ab480fea).** Root cause of the old "garbage map"
(and the original brick-target confusion) was a missing **ULEB128 compressed-name length** decode in
`a90_stock_kallsyms_extract.py` → names drifted off addresses mid-table. Fixed + operator-disasm-verified
(two independent anchors agree: `printk @ 0xffffff800813d8cc`, `force_no_nap_store @ 0xffffff80089273b4`).
Semantic locators are now cross-checks, not overrides.

**v2a1 = ✅ DONE / LIVE-PROVEN (`a90_repl.py` + `tests/test_a90_repl.py`).** Host driver that drives the
**existing** v1-repl image (no new flash) **by symbol name**: `runtime(sym) = link(System.map) + slide`.
Live selftest PASS (then rolled back V2321 `fail=0`): named `peek` of `force_no_nap_store` and `__kmalloc`
== static-image qwords; named `call printk(format, sentinel)` echoed the sentinel. Transport lessons pinned:
USB-ACM bridge is not the console UART (printk only via the ring); busybox `dmesg` is read-and-CLEAR so the
driver writes + reads `A90R` in ONE `run` shell bounded by `tail -n N`; **`call kallsyms_lookup_name` is
unsafe** (faulted/rebooted live, recoverable) → the call proof uses the v1-repl-proven `printk` target.
Report: `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A1_NAMED_DRIVER_2026-06-29.md`.

### ✅ v2a2 = DONE / LIVE-PROVEN — recovered-export `__kmalloc` poke round-trip

**Objective:** prove a real allocator-backed `poke`→`peek` round-trip over the **EXISTING** v1-repl image
(NO new boot image, NO new kernel `.text`). Extend the host driver `a90_repl.py` (commit 5b8aebe6) with a
`poke-roundtrip` subcommand + a faithful unit test, run it live, roll back to v2321, commit. This **reuses
the already-LIVE-PROVEN ops** op1 peek / op2 poke / op3 call — do **not** write any new kernel stub.
The original map-derived allocator addresses in the charter below were later proven to be drifted labels;
the live pass uses the v2a2R' recovered export addresses documented in the current status block.

**Reuse (do not re-derive):**
- Driver `workspace/public/src/scripts/revalidation/a90_repl.py`. Op buffer: `+0x00` u64 magic
  `0xA90C0DE5DEADBEEF`, `+0x08` u8 op, `+0x10` arg0, `+0x18` arg1, `+0x20` arg2, `+0x28..0x50` call x2..x7.
  op1 `peek(addr,len≤8)`, op2 `poke(addr,val,width 4|8)`, op3 `call(target,x0..x7)` → stub prints
  `A90R<x0_return>`. **Reuse `op_sh()`** (write+read in ONE `run` shell, bounded `tail -n N`).
- Live image to flash (already validated): `boot_linux_tier2_repl_v1_repl.img` SHA256
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- System.map: regenerate with `a90_stock_kallsyms_extract.py` against the v2321 image into a PRIVATE dir
  (`workspace/private/runs/kernel/v2a2-*`). Link addrs: `__kmalloc=0xffffff80082724bc`,
  `kfree=0xffffff800827276c`; runtime = link + slide(op0).

**🚨 LIVE TRANSPORT FACTS (pinned from v2a1 live — obey or you WILL burn runs):**
- USB-ACM bridge is **not** the kernel console UART → `printk` only readable via the log ring
  (`dmesg`/`/dev/kmsg`), never inline on serial.
- busybox `dmesg` here is **read-and-CLEAR** (consuming) → write the cmd buffer + read the `A90R` line in
  ONE `run /bin/busybox sh -c` invocation bounded by `tail -n N` (`op_sh()` already does this); do NOT
  split write/read into separate invocations (the ring drains between them).
- Binary writes: `printf '\NNN…' > /sys/class/kgsl/kgsl-3d0/force_no_nap` (octal) via native-init `run`
  (argv `["run","/bin/busybox","sh","-c",SH]`; a90ctl auto cmdv1x-encodes path/space args).
- **DO NOT call `kallsyms_lookup_name`** — it faulted/rebooted the device live (recoverable). Resolve every
  symbol from System.map, never from a runtime lookup call.

**Sequence (run_selftest-style; `panic_on_oops=0` during, restore `1` in `finally`):**
1. `slide = op0`.
2. `ptr = call __kmalloc(size=0x1000, gfp=GFP_KERNEL)` (target=`__kmalloc`+slide, x0=size, x1=gfp). Derive
   `GFP_KERNEL` EXACTLY from kernel headers under `workspace/private/inputs/.../include/linux/gfp.h` for
   this 4.14 tree: `___GFP_IO|___GFP_FS|___GFP_DIRECT_RECLAIM|___GFP_KSWAPD_RECLAIM` =
   `0x40|0x80|0x400000|0x1000000` = **`0x14000c0`**. Do not use the stale `0x6c0` note from older planning.
   The returned x0 is a runtime heap pointer — **keep it OUT of commits** (private evidence only).
   **Sanity-gate:** `ptr` must be non-null and in the kernel lowmem VA range; if not, STOP (do not poke a
   bad ptr).
3. `poke(ptr, sentinelA=0xA90F00D1CAFE0001, width=8)`; `peek(ptr,8)` MUST == sentinelA.
4. `poke(ptr, sentinelB=0x1122334455667788, width=8)`; `peek(ptr,8)` MUST == sentinelB (proves the store
   landed, not a stale read). Optional: 32-bit `width=4` poke+peek to exercise that path.
5. `call kfree(ptr)` (target=`kfree`+slide, x0=ptr). A valid kmalloc'd ptr is a clean slab free; if it
   faults the device reboots into the v1-repl boot partition (recoverable). Do **not** peek-after-free.
6. Restore `panic_on_oops=1`. Roll back to clean v2321 (`native_init_flash --from-native --expect-sha256
   ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`). Final `selftest fail=0`.

**Gate-2 + tests:** extend `tests/test_a90_repl.py` with a faithful-stub poke-roundtrip integration test
(fake transport modelling a kmalloc'd scratch dict: op2 writes it, op1 reads it back, op3 `__kmalloc`
returns a fake ptr, `kfree` no-ops). `py_compile`; run the full `tests/` suite. **No new kernel image is
built** (assert this; confirm the v1-repl image SHA is unchanged) → no operator disasm needed for this unit.

Then v2b (`show`-buf bulk `peek` for arbitrary length) stays BLOCKED until a safe fixed scratch anchor +
cleanup protocol are proven; the printk-loop stays the shipping default. Guardrails below + the v2a2-specific
note: `poke` writes ONLY to the `__kmalloc`'d buffer we own (non-protected) and we `kfree` it.

**STATUS (2026-06-29 v2a2 host/source gate) — host driver was source-ready before live ABI discovery.** Codex extended
`a90_repl.py` with the `poke-roundtrip` subcommand and added a faithful fake-transport integration test
that models `__kmalloc` returning an owned lowmem pointer, two qword `poke`/`peek` checks, the optional
low-32-bit poke path, and `kfree`. The driver keeps raw slide/runtime pointer values out of stdout and
committed artifacts; `--evidence-dir` writes them only to private evidence. It regenerates the v2a2 private
System.map under `workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/`; anchors match `printk`,
`kgsl_pwrctrl_force_no_nap_store`, `__kmalloc`, and `kfree`. Host validation: `py_compile` PASS,
`tests.test_a90_repl` **28/28 PASS**, v1-repl image SHA remains `b846ae9f…`, v2321 rollback SHA remains
`ca978551…`. Full repo `unittest discover` was attempted and remains non-green in this checkout
(`3679` tests, `217` failures, `56` errors, `3` skipped) due to existing private artifact dependencies
outside v2a2; focused v2a2 tests pass. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2_POKE_ROUNDTRIP_SOURCE_2026-06-29.md`.

**STATUS (2026-06-29 v2a2 LIVE attempt) — blocked by allocator ABI mismatch, device recovered.** Codex
flashed the unchanged v1-repl image (`b846ae9f...`) through `native_init_flash.py`; post-flash
`version/status/selftest` were clean. The first `poke-roundtrip` run timed out around the
`panic_on_oops=0` transaction but the device stayed reachable. The retry reached `op3 call __kmalloc`
and faulted before any `poke`: dmesg showed fault address `0x1048`, and static boot-image disassembly
of the recovered `__kmalloc @ 0xffffff80082724bc` shows `ldr x23, [x0,#72]` before the first helper call.
Calling that entry as `__kmalloc(size=0x1000, GFP_KERNEL)` therefore dereferences `0x1000+0x48`, exactly
the observed fault. v2a1 named-peek proved name→address mapping, not allocator call ABI. `panic_on_oops`
was restored to `1`; rollback to clean v2321 via the checked helper passed with readback SHA
`ca978551...`, `version/status` passed, final `selftest verbose` was `pass=11 warn=1 fail=0`, and a direct
check showed `panic_on_oops=1`. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2_LIVE_ALLOCATOR_ABI_BLOCKED_2026-06-29.md`.
`a90_repl.py` now has a host-side guard that rejects scalar allocator candidates whose entry
dereferences `x0` before the first `BL`; the current direct `__kmalloc` path is blocked before live.
**Do not rerun direct `call __kmalloc(size, GFP_KERNEL)` without a newly validated target.**

> ### 🛑 OPERATOR GATE-2 CORRECTION (2026-06-29) — the "allocator ABI" root-cause is a MISDIAGNOSIS; the MAP is mislabeled
>
> Operator re-Gate-2'd the live blocker by disasm + xref analysis of the v2321/v1-repl boot image and
> found the loop chased the wrong problem. **There is no allocator-ABI problem. The kallsyms map (post-v2a0)
> still MISLABELS the mm/slab region**, so `call __kmalloc` called the WRONG function.
> - **Ironclad evidence — bl xref counts:** map `__kmalloc @0xffffff80082724bc`, `kfree @0xffffff800827276c`,
>   and `kmalloc_slab @0xffffff800823eaa4` each have **0 direct `bl` xrefs** in the whole image. `__kmalloc`
>   and especially `kfree` are among the most-called kernel functions (hundreds–thousands of call sites);
>   **0 xrefs is impossible if those addresses were really those functions.**
> - **Disasm corroboration:** the function at the map's `__kmalloc` saves 4 args and does `ldr x23,[x0,#72]`
>   before its first `BL` — impossible for `__kmalloc(size_t size, gfp_t flags)` (source `slab.h:358`; `x0` is
>   a scalar size, never dereferenced). The map's `kmalloc_slab`/`__kmalloc_track_caller` entries likewise do
>   not match their signatures. By contrast `printk @0x813d8cc` and the kgsl/`force_no_nap` region remain
>   correct → this is a **localized residual name↔address decode drift in the mm/slab region**, not a global map break.
> - **Why v2a1 didn't catch it:** v2a1's named-`peek` only checks bytes-at-address; it never tests that the
>   name maps to the right *function*. The first real test of `__kmalloc`'s identity was this `call`, which faulted.
>
> **Consequences / redirect (supersedes v2a2R "ABI locator" and v2a2H "new helper image"):**
> - **Do NOT build a new helper image (v2a2H) and do NOT keep auditing allocator "ABIs."** Both target a
>   non-existent problem. `__kmalloc(size, GFP_KERNEL)` *is* callable via the existing v1-repl `op3` scalar
>   path — once the CORRECT address is used.
> - **New v2a2R' (host-only): get GROUND-TRUTH allocator addresses.** Either (a) decode the **PREL32
>   `__ksymtab` export table** (`struct kernel_symbol { s32 value_offset; s32 name_offset; }`; value =
>   `&entry + value_offset`) to read the real `__kmalloc`/`kfree` addresses, and/or (b) re-audit
>   `a90_stock_kallsyms_extract.py` for the residual mm-region drift. Then **disasm-verify** the chosen
>   `__kmalloc`: `x0` = scalar size (no pre-`BL` `x0` deref), high `bl`-xref count, reaches the slab path; and
>   `kfree`: `x0` = pointer, frees cleanly. Only then re-enable the existing-image `poke-roundtrip`.
> - The loop's `x0`-deref guard is a fine generic safety net — **keep it**, but it must not be read as
>   "allocators are unsafe to call." The guard correctly rejected a *mislabeled* entry.
> - This stays host-only (no device, no collision); operator will cross-check the recovered addresses by
>   independent disasm before any live rerun. Device remains clean on v2321.

**STATUS (2026-06-29 v2a2R' host-only recovery) — ground-truth allocator addresses recovered.**
`a90_repl.py allocator-export-recovery` now bypasses the mislabeled mm/slab System.map entries by finding
exact export strings in the static v1-repl boot image, following aligned qword references to those strings,
and selecting the nearby JOPP text entries with no pre-first-`BL` `x0` dereference and high direct-`BL`
xref counts. Required recovered link addresses:
`__kmalloc=0xffffff800826ae34` (`1765` direct `bl` xrefs) and
`kfree=0xffffff800826b354` (`10596` direct `bl` xrefs). Optional slab helpers also recover:
`kmalloc_order=0xffffff8008238444`, `kmalloc_order_trace=0xffffff8008238484`. The mapped
`__ksymtab___kmalloc`/`__ksymtab_kfree` qwords read as `0x0`, proving those map labels are drifted too.
Focused validation: `tests.test_a90_repl` **31/31 PASS**. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2RP_ALLOCATOR_EXPORT_RECOVERY_2026-06-29.md`.

**STATUS (2026-06-29 v2a2 recovered-export LIVE PASS) — allocator-backed poke round-trip is live-proven.**
Host objdump cross-check confirmed recovered `__kmalloc=0xffffff800826ae34` preserves scalar `x0` until
the first `BL` and recovered `kfree=0xffffff800826b354` preserves `x0` as the pointer argument; direct
`bl` xrefs are `1765` and `10596`. Flashed exact v1-repl image
`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` via `native_init_flash.py`; pushed
image SHA and boot readback SHA matched, and post-flash health was clean after one serial-fragment retry.
Ran `a90_repl.py poke-roundtrip --use-recovered-allocator-exports`: decision
`a90-repl-v2a2-poke-roundtrip-pass`; checks `kmalloc-owned-buffer`, sentinel A/B qword `poke`→`peek`,
low32 `poke`→`peek`, and `kfree-owned-buffer` all passed. `panic_on_oops` was restored to `1`; candidate
selftest was `pass=11 warn=1 fail=0`; rollback to v2321
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb` had matching readback SHA; final
`version/status/selftest` were clean (`fail=0`) and final `panic_on_oops=1`. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2_LIVE_RECOVERED_EXPORTS_2026-06-29.md`.
**v2a is now complete.** v2b (`show`-buf bulk `peek` for arbitrary length) remains blocked/optional until
a fixed scratch anchor + cleanup protocol is proven; otherwise the v1-repl printk loop is the shipping
bulk path.

### ✅ v2a2R (HOST-ONLY) — allocator ABI locator / safe owned-buffer plan

Find a replacement for the invalid direct `__kmalloc` plan before any more live `poke-roundtrip` attempts.
This unit is host-only by default: inspect the v1-repl boot image + regenerated System.map, classify candidate
owned-buffer APIs by static ABI, and require a report/test update before live. Acceptable outcomes:

1. a JOPP entry whose first basic block matches a scalar allocator ABI and returns a sane writable pointer,
   paired with a validated free path; or
2. a revised small helper design that returns/owns a scratch buffer under the normal boot-image flash gates.

No live device command is needed unless the static ABI gate produces a concrete, bounded candidate. If the
only viable path is a new helper image, build and Gate-2 it as a new V-iteration; do not mutate the existing
v1-repl image in place. Keep raw runtime pointers and slides out of committed artifacts.

**STATUS (2026-06-29 v2a2R host-only audit) — existing scalar allocator path saturated.** `a90_repl.py`
now exposes `allocator-audit`, which checks 13 plausible owned-buffer allocator/free pairs in the v1-repl
boot image for JOPP shape, pre-helper-call `x0` dereferences, leaf/global-return thunks, and known
pointer-argument wrappers. Result:
`a90-repl-v2a2r-allocator-abi-audit-no-live-ready-scalar`; every candidate is rejected and
`live_ready_candidates=[]`. Focused validation is now `tests.test_a90_repl` **29/29 PASS**. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2R_ALLOCATOR_ABI_AUDIT_2026-06-29.md`.
**Superseded by the correction above:** this audit rejected mislabeled map entries, not real allocator
functions. Keep the `x0`-deref guard as a safety net, but use v2a2R' export recovery before any live
allocator-backed round-trip.

### ⛔ SUPERSEDED by the OPERATOR GATE-2 CORRECTION above — v2a2H (new owned-scratch helper image) is NOT the next unit

**The real NEXT BOUNDED UNIT was v2a2R' (host-only), followed by the recovered-export live rerun; both are
now complete.** Do not build a new helper image to work around a map-mislabel. The block below is retained
only as the (now-rejected) ABI-workaround design.

### ~~v2a2H (HOST-ONLY SOURCE GATE) — explicit owned-scratch helper~~ (rejected; see correction)

Design and source-gate a replacement for the invalid direct allocator path. The target is still the original
v2a2 semantic proof: a non-protected owned buffer where `op2 poke` lands, `op1 peek` reads back the value,
and cleanup/rollback leaves the device clean. The implementation must avoid guessing allocator ABIs from
exported names.

Preferred shape:
- Build a new bounded helper image only if the source design can prove an explicit owned scratch location or
  call target with a known ABI. Do not mutate the existing v1-repl image in place.
- Keep all writes recoverable under the boot-partition-only flash gates; no forbidden partitions, no RKP
  bypass, no protected `.text`/rodata/page-table/cred target.
- Gate-2 before flash: diff only `{boot-id, intended helper body}`, disassemble helper body, preserve JOPP/
  ROPP expectations, and prove the scratch target is writable non-protected state.
- Live step, when reached: flash exact SHA, health-check, run `poke` -> `peek` -> cleanup, restore
  `panic_on_oops=1`, rollback to v2321, final `selftest fail=0`.

**Guardrails (hard, RECON / exploit-free):** NO RKP bypass, NO write to RKP-protected memory
(`.text`/rodata/page-tables/cred), NO RWX, NO `ret`/`blr`/CFP-site patch, NO grooming/UAF/spray,
preserve `x17`. Magic-guard every hijacked handler. Boot-partition-only via `native_init_flash.py`
with pinned + readback SHA; rollback target v2321
(`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`). Gate-2 **disasm** every candidate
(objdump the patched body; confirm diff is contained to `{boot-id@0x240, target-function body}`, magics
preserved) BEFORE flashing. Keep raw runtime pointers / the per-boot slide OUT of committed reports.
Fails-twice → STOP and report; anti-churn in force. Report each unit to `docs/reports/`.

**Operator/loop split:** the operator (Claude) did the corrected `poke` agent, `slide`, v1-repl Gate-2,
the v2a0 kallsyms fix, and the v2a1 named host driver (all live-validated, since only the operator can
reach the device bridge + commit). Codex builds host-only/RE units; the operator runs all live flash/
validate + commits. v2a1 was operator-direct (small + protocol-tight). v2a is complete; the next frontier
is the v2c productization epic below.

### ▶ ACTIVE NEXT EPIC = v2c — Tier-2 Kernel REPL PRODUCTIZATION (correctness + stability + usability)

> ### 🛑 OPERATOR GATE-2 CORRECTION (2026-06-29) — the C2A "map-audit" is UNSOUND; do NOT rewrite the kallsyms decoder off it
>
> Operator independently checked the C2A audit (commit 62047499). **Its "`map_match=0`, `12479` mismatches"
> is a TOOL ARTIFACT, not evidence the map is broadly wrong.** The audit treats `export-recovery` as ground
> truth, but recovery is a **noisy heuristic** (it scans for any qword ref to a `"<name>\0"` string), so it
> produces FALSE candidates:
> - **`printk`**: the map address `0xffffff800813d8cc` is CORRECT (operator-verified 3 ways: two independent
>   extractor anchors, `stage_c.locate_printk_variadic_wrapper`, and a LIVE `call printk(fmt,sentinel)` in
>   v2a1 that printed the sentinel — a wrong address could not have). But recovery returns **two candidates,
>   `0x813adfc` and `0x81b8eac`, NEITHER equal to the real printk**, and buckets it "ambiguous". So
>   `map≠recovery` here means **recovery is wrong, not the map**.
> - Recovery happened to be right for `__kmalloc`/`kfree` (single clean candidate, operator-verified by xref
>   + signature), so those map entries ARE wrong — but that does NOT generalize. **The map is verified-CORRECT
>   for printk and the kgsl region, and verified-WRONG only for the mm/slab allocator region.**
>
> **Steer:**
> - **Do NOT rewrite/`root-fix` `a90_stock_kallsyms_extract.py` based on the current audit** (there is an
>   uncommitted extractor edit in flight — drop or gate it). A decoder rewrite driven by a buggy "whole map is
>   drifted" signal can break the regions that are currently correct.
> - **C2 must FIX THE AUDIT (make the oracle sound) BEFORE drawing any map conclusion.** Ground truth must
>   come from a *real* `__ksymtab` parse (locate the actual `__ksymtab`/`__ksymtab_strings` section bounds and
>   walk its entries), not heuristic string-ref scanning; and/or only flag a symbol "map-wrong" when the
>   recovered candidate is HIGH-CONFIDENCE (single, JOPP entry, plausible `bl`-xref count, signature-sane) AND
>   the map address is *independently* shown wrong (e.g. its own xref count is implausibly low / signature
>   mismatched). **Validate the fixed audit against known anchors: `printk` MUST come out `map-match`
>   (truth==map==`0x813d8cc`); `__kmalloc`/`kfree` MUST come out `map-mismatch` with the recovered address as
>   truth.** Only after the audit reproduces those three is its drift count trustworthy.
> - **We are not in danger:** C1 fail-closed already protects `call`/`poke` (a wrong map address cannot be
>   dispatched). So C2 is about *restoring general trust + a correct drift map*, with no safety pressure — take
>   the time to make the oracle correct rather than chase a 12k-mismatch artifact.

**Operator-chartered 2026-06-29 after a maturity review.** v2a proved the capability (flash-once
`slide`/`peek`/`poke`/`call`, named/recovered-address resolution, owned-buffer round-trip), but it is an
operator-driven proof, not yet a *trustworthy, stable, usable tool*. v2c hardens it into one. **No new boot
image is needed** for most of this — it drives the existing v1-repl image (`b846ae9f…`); only bounded live
re-validation flashes, with v2321 rollback. Work the sub-units in priority order; each is a bounded
host-only unit unless it explicitly needs a live check. Report each to `docs/reports/`.

**The #1 gap is CORRECTNESS (the kallsyms map silently mislabels regions — this is what bit v2a2).**

- **C1 — fail-closed resolution (highest priority).** Make the `System.map` *untrusted by default* for any
  `call`/`poke` target. Add `resolve_verified(symbol) -> (link_vaddr, verified: bool, method, evidence)`
  and REQUIRE `verified=True` before any `call`/`poke`; refuse otherwise. Verification ladder:
  (1) export-recovery ground truth (already built, exported symbols only); (2) disasm-signature + `bl`-xref
  sanity (e.g. a callable function entry must be JOPP-shaped, have a plausible xref count, and not match a
  known-bad shape); (3) optional agreement with the map. `peek` of read-only data may use the map but must
  surface `verified=False` in output. This structurally prevents the v2a2 mislabel-call class.

  **STATUS (2026-06-29 v2c C1 host pass) — fail-closed resolution is implemented host-side.**
  `a90_repl.py` now has `VerifiedResolution` + `resolve_verified(...)`: call/poke targets must be verified
  before dispatch, `__kmalloc`/`kfree` resolve through the v2a2R' recovered-export ground truth, `printk`
  is accepted only by map-address disasm/xref sanity, `kallsyms_lookup_name` is explicitly blocked as a
  known unsafe live call, and read-only `peek` surfaces `verified=False`. `run_selftest` verifies its call
  target before transport; `run_poke_roundtrip` verifies allocator call/free targets and rejects stale
  map-derived allocator overrides before any REPL op. Validation: `py_compile` pass,
  `tests.test_a90_repl` **36/36 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C1_FAIL_CLOSED_RESOLUTION_2026-06-29.md`.
- **C2 — map-trust audit + decoder root-fix.** Build a host-only `map-audit` that cross-checks the kallsyms
  `System.map` against export-recovery ground truth for *all* exported symbols, emits a drift report (which
  symbols/address-regions disagree), and quantifies map accuracy. Then use that to find and fix the residual
  `a90_stock_kallsyms_extract.py` name↔address drift in the mm/slab (and any other drifted) region — the
  v2a0 ULEB128 fix did not cover it. Goal: a map that is either correct everywhere or annotated with its
  trustworthy regions. (C2 can be staged: audit first, decoder fix as a follow-up.)

  **STATUS (2026-06-29 v2c C2A host pass) — map-audit landed; decoder fix/fencing remains open.**
  `a90_repl.py map-audit` now builds a one-pass export-name/ref index from the raw v1-repl image and compares
  recovered export-record values against `System.map`. On the current v2a1 map it audits `12628` exported
  symbols: `12490` recoverable candidates, `12479` map mismatches, `11` ambiguous, `138` missing recovery,
  and `0` map matches. Focus rows preserve the v2a2 allocator proof (`__kmalloc` recovered
  `0xffffff800826ae34`, `kfree` recovered `0xffffff800826b354`) and show `printk` as ambiguous rather than
  auto-promoted. Validation: `py_compile` pass, `tests.test_a90_repl` **37/37 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2_MAP_AUDIT_2026-06-29.md`.
  **Next C2 step:** fix the kallsyms decoder root cause or explicitly fence trusted map regions; do not treat
  this System.map as globally trustworthy.

  **STATUS (2026-06-29 v2c C2C host pass) — C2A audit oracle corrected/fenced.**
  `a90_repl.py map-audit` now defaults to a high-confidence anchor oracle instead of the broad C2A
  string-ref heuristic. It validates the operator-required anchors: `printk` is `map-match`
  (`truth==map==0xffffff800813d8cc`) via the Stage-C plain-`printk` semantic signature plus C1
  `resolve_verified(...)`; `__kmalloc` is `map-mismatch` (`truth=0xffffff800826ae34`,
  map `0xffffff80082724bc`) with a single JOPP/no-`x0`-deref/high-xref export candidate and independent
  map refutation (`0` direct `bl` xrefs plus pre-call `x0` deref); `kfree` is `map-mismatch`
  (`truth=0xffffff800826b354`, map `0xffffff800827276c`) with the same evidence shape. The old whole-map
  scanner remains only as `run_string_ref_map_audit(...)` and must not drive a decoder rewrite. Validation:
  `py_compile` pass, `tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract` **56/56 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2C_HIGH_CONFIDENCE_MAP_AUDIT_2026-06-29.md`.
  Remaining C2 work: a real `__ksymtab`/`__ksymtab_strings` section parse, or equivalent grounded oracle,
  before claiming any broad drift count or changing `a90_stock_kallsyms_extract.py`.

  **STATUS (2026-06-29 v2c C2D host pass) — noisy C2A ksymtab source fenced.**
  The local Samsung kernel source for this image defines `struct kernel_symbol` as the 16-byte absolute
  pair `{ unsigned long value; const char *name; }`, not the PREL32 `{ s32 value_offset; s32 name_offset; }`
  ABI. `a90_repl.py ksymtab-audit` now checks that source ABI directly and separates it from the large
  24-byte `0x403, pointer, aux` table that C2A had accidentally treated as broad truth. For `printk`,
  `__kmalloc`, and `kfree`, no parseable 16-byte source-ABI ksymtab row exists in the raw v1-repl image;
  all string-ref candidates are inside the single noisy 24-byte `0x403` table (`162763` records). This
  explicitly fences the broad drift count and blocks any decoder rewrite from that table. Validation:
  `py_compile` pass, CLI `ksymtab-audit` pass, `tests.test_a90_repl` +
  `tests.test_a90_stock_kallsyms_extract` **62/62 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2D_KSYMTAB_ABI_AUDIT_2026-06-29.md`.
  C2 status: known allocator drift is fixed by C1 verified resolution and C2C anchors; broad map drift is
  intentionally **not claimed** unless a future independent oracle is added.
- **S1 — transport stability.** Harden the live op path against the observed serial-fragment noise
  (`ATAT` / missing `A90P1 END`): per-op bounded re-read/realign retry, robust ring read (busybox `dmesg`
  is read-and-clear; keep the single-shell `op_sh` + `tail -n N`), and clear classification of
  transient-noise vs real failure. Ops should self-heal a noisy read instead of aborting the run.

  **STATUS (2026-06-29 v2c S1A host pass) — safe-op retry + transient-noise classification landed.**
  `a90_repl.py` now raises `ReplTransientNoiseError` for no-`A90R` capture, retries replay-safe ops
  (`slide`/`peek`) with bounded `--safe-op-retries`, uses configured `--dmesg-tail`, and exposes
  `--retry-delay-sec`. Generic `call` is deliberately not replayed by default to avoid duplicate
  `__kmalloc`/`kfree` side effects; `run_selftest` marks its `printk` proof call explicitly replay-safe.
  Validation: `py_compile` pass, `tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract`
  **56/56 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_S1A_SAFE_OP_RETRY_2026-06-29.md`.
  Remaining S1 gate: live serial-fragment validation and any extra non-replay re-read/realign handling if
  unsafe ops still see fragment loss.

  **STATUS (2026-06-29 v2c S1 live gate) — sequential REPL live path passed; parallel host commands still noisy.**
  Flashed the unchanged v1-repl image via `native_init_flash.py` with pinned SHA/readback SHA, then ran the
  v2c REPL selftest plus U1 `read`/`call`/owned-`poke` commands with `--safe-op-retries 3`; all passed and
  the device stayed healthy. A deliberately accidental parallel final `a90ctl version`/`selftest` check hit
  host-side serial-lock / `ATAT` fragment noise, then sequential retry passed immediately. Treat this as a
  caller-concurrency constraint: live bridge validation commands remain single-client/sequential unless a
  later transport layer adds explicit concurrency support. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_U1_S1_LIVE_VALIDATION_2026-06-29.md`.
- **U1 — usability surface.** Add first-class CLI: `call SYMBOL [args…]` (verified targets only),
  `read SYMBOL|ADDR --len N` = **arbitrary-length bulk peek by host-side looping op1 in 8-byte chunks**
  (this unblocks the old "v2b" need with NO new image — looping the existing `peek` op suffices for reads),
  and `poke` to a verified-owned buffer. Keep raw runtime pointers/slide out of stdout (private evidence
  only), as today.

  **STATUS (2026-06-29 v2c U1 host pass) — first-class CLI surface landed.**
  `a90_repl.py` now exposes `read`, `call`, and `poke` subcommands on the existing v1-repl image. `read`
  accepts a symbol/link-vaddr/runtime-vaddr and performs arbitrary-length host-side looped op1 reads in
  1..8 byte chunks, reporting SHA256/static-image-match while keeping raw bytes and runtime addresses in
  private evidence only. `call` requires C1 `resolve_verified(..., purpose="call")`, supports private
  runtime-pointer tokens like `@repl_format`/`@symbol`, and rejects unverified symbols before transport; args
  and returns are redacted from stdout. `poke` is owned-buffer-only: verified `__kmalloc` → poke fresh buffer
  → peek verify → verified `kfree`, with no arbitrary-address poke path.
  Validation: `py_compile` pass, CLI `--help` smoke checks pass, `tests.test_a90_repl` +
  `tests.test_a90_stock_kallsyms_extract` **61/61 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_U1_CLI_SURFACE_2026-06-29.md`.

  **STATUS (2026-06-29 v2c U1 live pass + rollback clean) — CLI surface is device-proven.**
  Live run over the existing v1-repl image passed: `read kgsl_pwrctrl_force_no_nap_store --len 20`
  reported `chunk_count=3`, `static_image_match=true`, and SHA256
  `5642494b8364c16a197612eba47d416916d4059ae03f5a46a8aeeb285f5184c9`; `call printk @repl_format
  0xa90ca11 --replay-safe` used verified `printk`, private evidence confirmed sentinel echo + stub return;
  `poke --width 8 0xaabbccddeeff0011` allocated a verified `__kmalloc` buffer, matched poke→peek, and
  freed via verified `kfree`. Rolled back to v2321 (`ca978551...`) via the checked flash helper; final
  `version` was `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)` and final `selftest verbose`
  was `pass=11 warn=1 fail=0`. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_U1_S1_LIVE_VALIDATION_2026-06-29.md`.
- **U2 (optional/stretch).** Small ergonomics: a session that fetches the slide once and reuses it; a
  `--json` machine surface; a short operator runbook for the tool in `docs/operations/`.

**Definition of done for v2c:** named `call`/`poke` cannot target an unverified address (fail-closed);
a map-audit report exists and the known mm/slab drift is fixed or explicitly fenced; arbitrary-length
`read` works; the live op path survives serial-fragment noise without aborting; one bounded live
re-validation passes and rolls back to v2321 `fail=0`; raw pointers/slide never leave private evidence.

**STATUS (2026-06-29) — v2c core DoD DONE.** C1 fail-closed resolution, C2C/C2D map-audit fencing,
U1 CLI `read`/`call`/owned-`poke`, S1 sequential live validation, and rollback-to-v2321 `fail=0` are all
landed and reported. U2 remains optional/stretch only; any future broad map drift claim still requires a
new independent oracle and must not come from the noisy 24-byte `0x403` table.

### ▶ NEXT UNIT = v2c-C2E — real `__ksymtab` ground-truth oracle + authoritative drift map (+ kallsyms decoder root-fix decision)

**Operator-chartered 2026-06-29.** This closes the one real remaining correctness gap: the kallsyms
`System.map` is mislabeled in unknown regions (mm/slab proven), and today only C1 fail-closed + per-symbol
export-recovery protect us. C2E builds a *sound, at-scale* ground-truth oracle and produces an authoritative
map-drift report, then decides whether a decoder root-fix is warranted. **Host-only** until a bounded live
re-validation is explicitly needed; drives the existing v1-repl image; no new boot image.

**Hard lessons to obey (do NOT repeat):**
- The C2A string-ref scanner is UNSOUND (noisy; printk → false candidates `0x813adfc`/`0x81b8eac`, missing
  the real `0x813d8cc`). **Do NOT use name-string-ref heuristics as ground truth.** They stay non-authoritative.
- A correct oracle MUST reproduce the operator anchors or it is wrong: `printk=0xffffff800813d8cc`,
  `force_no_nap_store=0xffffff80089273b4`, `__kmalloc=0xffffff800826ae34` (`cmp x0,#0x2000`, 1765 `bl` xrefs),
  `kfree=0xffffff800826b354` (10596 xrefs). Gate the oracle on these before trusting any drift count.

**Steps:**
1. **Structural `__ksymtab` parse (the sound oracle).** Locate the real export tables by STRUCTURE, not
   names: find the contiguous run of fixed-stride entries where every "name" field points into one
   contiguous `__ksymtab_strings`-like ASCII region and every "value" field resolves to a `.text` JOPP
   function entry (`u32(entry-4)==0x00be7bad`). Determine the exact entry layout empirically (old-style
   `{unsigned long value; const char *name}` vs PREL32 `{s32 value_off; s32 name_off}` vs the observed
   24-byte/`0x403`-stride variant) by which layout makes ALL anchors resolve correctly. Also try to bound it
   via `__start___ksymtab`/`__stop___ksymtab` if those map symbols land in a trustworthy region. Output: an
   authoritative `{addr → exported-name}` table that reproduces every anchor.
2. **Authoritative drift report.** Cross-check that table against `System.map` for all exported symbols;
   emit real match/mismatch counts + the mismatched address-regions. (This is the *trustworthy* version of
   the C2A audit; it must show `printk=match`, `__kmalloc`/`kfree=mismatch`.) Make `run_map_audit` (or a new
   `ksymtab-audit`) use this oracle for exported symbols.
3. **Localize the kallsyms decoder divergence.** Using the ksymtab ground truth, find the exact symbol /
   table position where `a90_stock_kallsyms_extract.py` first pairs a name with the wrong address in the
   mm/slab region (the v2a0 ULEB128 fix covered names-length but something else drifts here). Diagnose the
   root cause (e.g. an offsets-table padding/alignment or ABSOLUTE_PERCPU edge) WITHOUT guessing.
4. **Decoder root-fix DECISION (gated).** Only fix `a90_stock_kallsyms_extract.py` if step 3 yields a
   precise, low-risk cause AND the regenerated map reproduces ALL anchors with **zero regression** on the
   currently-correct regions (printk/kgsl). Operator will independently disasm-verify the regenerated map
   before any reliance. If the cause is not cleanly isolable, DO NOT rewrite the decoder — instead publish a
   trust-region map (which `System.map` regions are ksymtab-confirmed) and keep C1 fail-closed as the
   safety net. Non-exported (static) symbols remain map-only and stay `verified=false` for `call`/`poke`.

**Definition of done for C2E:** a structural `__ksymtab` oracle that reproduces all four anchors; an
authoritative drift report (real counts, `printk=match`/`__kmalloc`+`kfree=mismatch`); the decoder
divergence localized with a root cause; and either a regression-free decoder fix (operator-disasm-verified)
or an explicit, documented decision to keep map-as-is + trust-region fencing. C1 fail-closed stays enforced
throughout. Guardrails unchanged below; keep raw pointers/slide out of commits; fails-twice → STOP + report.
After C2E, U2 ergonomics + a tool runbook are the only optional remainders, then the REPL epic can close.

**STATUS (2026-06-29 v2c C2E host pass) — relocated `__ksymtab` oracle + trust-region decision landed.**
`a90_repl.py ksymtab-ground-truth` reconstructs zeroed 16-byte source `__ksymtab` rows from the 24-byte
`0x403` relocation table by structure (`target+0=value`, `target+8=name`) and selects high-density export
runs. It emits `12518` authoritative exported rows over target range
`0xffffff800a562d60..0xffffff800a594270`. Against current v2a1 `System.map`, the real drift report is
`0` matches / `12518` mismatches / `0` missing. Against the previous C2B padding-fix candidate map, the same
oracle gives `12514` matches / `4` mismatches, validating the 95-zero-u32 padding root-cause at scale while
leaving residual semantic/local-symbol conflicts. Anchors: `__kmalloc=0xffffff800826ae34` and
`kfree=0xffffff800826b354` match relocated ksymtab; `kgsl_pwrctrl_force_no_nap_store=0xffffff80089273b4`
is non-exported and stays a semantic map anchor; `printk=0xffffff800813d8cc` is the live-call semantic
anchor while the export relocation row points at `0xffffff800813adfc`, so the conflict is explicit rather
than hidden. Decoder decision: **do not rewrite/promote `a90_stock_kallsyms_extract.py` in this unit**; keep
map-as-is plus relocated-ksymtab trust-region fencing until the padding fix and semantic exceptions receive
operator disasm verification. Validation: `py_compile` pass, CLI `ksymtab-ground-truth` pass,
`tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract` **63/63 PASS**. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2E_KSYMTAB_GROUND_TRUTH_ORACLE_2026-06-29.md`.

> ### ✅ OPERATOR GATE-2 (2026-06-29) — C2E oracle is RIGHT; C2B padding fix is VINDICATED; promote it (gated). My earlier C2A-revert conclusion was partly wrong.
>
> Operator independently verified the C2E result and a regenerated C2B map. **The relocated-`__ksymtab`
> oracle is correct, and the current `System.map` really is broadly drifted for exported symbols — my
> earlier "map is mostly right, only mm/slab wrong" was based on a FALSE printk confirmation.**
> - **printk:** `0xffffff800813d8cc` (current map + signature override) and `0xffffff800813adfc` (oracle
>   export row) have **byte-identical variadic prologues** (both are printk-twins), but xref counts settle it:
>   `0x813d8cc` has **14** `bl` xrefs, `0x813adfc` has **44694**. **The real `printk` is `0x813adfc`** (the
>   most-called function in the kernel). The v2a1 live `call printk` "worked" only because it hit a
>   functionally-equivalent twin — that was a false positive, not proof the map address was right.
> - **C2B is a precise, real root-cause and is regression-free.** I regenerated the map with C2B applied
>   (`padding_before_relative_base = 380 = 95×4`, skipping the zero-u32 pad before `kallsyms_relative_base`):
>   `__kmalloc → 0xffffff800826ae34` ✓, `kfree → 0xffffff800826b354` ✓ (both were WRONG in the current map),
>   while `kgsl_pwrctrl_force_no_nap_store → 0xffffff80089273b4` ✓ and `num_pwrlevels_show → 0xffffff80089262dc`
>   ✓ are PRESERVED (no kgsl regression — C2B's early-return guard handles that). This matches the oracle
>   `12514/12518`. **My earlier instruction to revert C2B was the mistake; the loop was right to keep it and
>   build C2E to settle it.**
>
> **Re-authorized direction (supersedes the "do not promote / map-as-is" decision above):**
> 1. **Promote the C2B padding fix** into `a90_stock_kallsyms_extract.py` (re-apply commit 4ba3c52c's
>    `padding_before_relative_base` logic + the kgsl early-return guard). Operator has disasm-verified the
>    four anchors on the regenerated map; gate stands only on the loop reproducing them in-tree.
> 2. **Fix the printk-twin bug (separate from C2B).** `locate_printk_variadic_wrapper` /
>    `apply_printk_signature_decode` currently pick the 14-xref twin `0x813d8cc`; there are ≥2 identical-
>    prologue variadic functions, so the locator must **disambiguate by `bl`-xref count** (the real `printk`
>    is the highest-xref one, `0x813adfc`). After this, the regenerated map's `printk` must be `0x813adfc`
>    and the C2E drift vs the oracle should approach `~12518/12518`. (Note: the live-proven v1-repl IMAGE
>    still calls the twin `0x813d8cc` — that is functionally fine and need NOT be rebuilt; only the
>    host-side map/locator needs the real address.)
> 3. **Re-run the C2E drift report on the promoted map** and confirm: all four anchors correct, printk now
>    `0x813adfc`, near-total oracle agreement, and a fenced residual list (any remaining mismatches are
>    non-exported/local or genuine semantic exceptions, not decode drift). C1 fail-closed stays enforced.
> 4. Operator will independently re-disasm-verify the promoted in-tree map (anchors + a sample of newly-
>    corrected exports) before it is trusted for anything beyond C1-gated use. Guardrails unchanged; this is
>    host-only (no device); keep raw pointers/slide out of commits.
> 5. **FOLLOW-UP (host-only, recommended) — cross-validate against `vmlinux-to-elf`.** Web research
>    (2026-06-29) confirms every bug we hit is a *documented, known* class, and a mature reference tool
>    already handles them: `vmlinux-to-elf` (github.com/marin-m/vmlinux-to-elf, also bkerler fork) recovers a
>    System.map from a raw arm64 `Image` and explicitly handles (a) the variable kallsyms table
>    alignment/padding (our 380-byte `relative_base` pad) and (b) the ksymtab relocation gotcha
>    (pre-4.19 arm64 uses 16-byte `{value,name}` + **24-byte `R_AARCH64_RELATIVE` (`0x403`) RELA** records;
>    the unrelocated section reads as zeros — exactly why our C2E oracle reconstructs from the relocations).
>    Run `vmlinux-to-elf` on the v2321 image as an INDEPENDENT THIRD oracle and require three-way agreement
>    (promoted extractor map ≡ C2E ksymtab-relocation oracle ≡ `vmlinux-to-elf`) on the four anchors + a
>    sample of corrected exports before declaring the map ground-truth. If `vmlinux-to-elf` disagrees, treat
>    that as a STOP-and-investigate signal, not a silent override. (It is a host-only Python tool — vendor it
>    privately if used; do not add a network/runtime dependency to the build.) Refs: kallsyms BASE_RELATIVE
>    `addr = kallsyms_relative_base + (u32)offset` (LWN 673381); ksymtab PREL32/RELA relative refs
>    (LWN 758337). This is a *confidence* step; C1 fail-closed already gates safety regardless.

**STATUS (2026-06-29 v2c Gate-2 host pass) — C2B padding fix promoted; printk twin fixed by BL-xref.**
`a90_stock_kallsyms_extract.py` now skips the `380`-byte zero padding before `kallsyms_relative_base` and
keeps the C2B KGSL early-return guard, so regenerated map anchors are
`printk=0xffffff800813adfc`, `__kmalloc=0xffffff800826ae34`, `kfree=0xffffff800826b354`,
`kgsl_pwrctrl_force_no_nap_store=0xffffff80089273b4`, and
`kgsl_pwrctrl_num_pwrlevels_show=0xffffff80089262dc`. `locate_printk_variadic_wrapper` now selects the
variadic-body candidate with the maximum direct `bl` xref count (`44694`), eliminating the lower-xref
`0xffffff800813d8cc` twin false positive. C1 `resolve_verified(printk)` now resolves through export/xref
ground truth. C2E recheck against the regenerated private promoted map is `12515` matches / `3` mismatches /
`0` missing over `12518` relocated export rows; residuals are `ehci_reset`,
`iio_read_channel_ext_info`, and `iio_write_channel_ext_info`, fenced for operator disasm review. Host-only:
no device action, no boot image change. Validation: `py_compile` pass, focused unittest set **71/71 PASS**,
CLI extractor pass, CLI `ksymtab-ground-truth` pass. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_GATE2_C2B_KALLSYMS_PROMOTION_2026-06-29.md`.

**STATUS (2026-06-29 v2c third-oracle host pass) — `vmlinux-to-elf` independently confirms the promoted
map.** Private `vmlinux-to-elf` clone at commit `19683fb95b29cd31362d49e6f48ab8368f96cbdf` was installed
under `workspace/private/inputs/external_tools/kernel/vmlinux-to-elf` only. `kallsyms-finder` on
`boot_linux_v2321_usb_clean_identity_rodata.img` emitted `147295` symbols and found the same structural
layout: token table `0x02103100`, token index `0x02103500`, markers `0x02101f00`, names `0x01f10700`,
`kallsyms_num_syms` `0x01f10600`, relocation table `0x2699618..0x2a532b8` (`162780` records), and
`kallsyms_offsets` `0x01e80700`. Its output map SHA256 is
`9e6a1d6f322344e3d6fced7e6d29a254e1516cc5163bad8595388a9d0d02ec3a`, byte-identical to the promoted
extractor map. C2E three-way compare gives identical promoted and `vmlinux-to-elf` counts:
`12515` matches / `3` mismatches / `0` missing, with the same fenced residuals
`ehci_reset`, `iio_read_channel_ext_info`, and `iio_write_channel_ext_info`. Four core anchors plus
`kallsyms_lookup_name` agree (`printk=0xffffff800813adfc`, `__kmalloc=0xffffff800826ae34`,
`kfree=0xffffff800826b354`, `force_no_nap_store=0xffffff80089273b4`,
`num_pwrlevels_show=0xffffff80089262dc`, `kallsyms_lookup_name=0xffffff800817cfa4`). Host-only: no device
action, no boot image change. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_VMLINUX_TO_ELF_THIRD_ORACLE_2026-06-29.md`.

> ### ✅ OPERATOR GATE-2 SIGN-OFF (2026-06-29) — C2E/v2c DONE; operator disasm-review CLEARED; **loop HALTS at this boundary**
>
> I independently regenerated the promoted extractor map from the v2321 image and it is **byte-identical**
> to both the promoted map and the `vmlinux-to-elf` output (all SHA `9e6a1d6f322344e3d6fced7e6d29a254e1516cc5163bad8595388a9d0d02ec3a`).
> I disasm-confirmed all four anchors by independent BL-xref count: `printk=0xffffff800813adfc` (44694 xrefs —
> NOT the 14-xref twin `0x813d8cc`), `__kmalloc=0xffffff800826ae34` (1765), `kfree=0xffffff800826b354` (10596),
> `kgsl_pwrctrl_force_no_nap_store=0xffffff80089273b4` (preserved, no kgsl regression), `num_pwrlevels_show=0xffffff80089262dc`.
> The `locate_printk_variadic_wrapper` disambiguation is **structural** (max direct-BL xref + tie guard + min-1000
> threshold), not a hardcoded address; it independently returns `0x813adfc`. C1 fail-closed is **strengthened**
> (printk now requires export/xref ground truth; the old hardcoded drifted-map expectation table is removed).
> The 3 residuals (`ehci_reset`, `iio_read_channel_ext_info`, `iio_write_channel_ext_info`) are **identical across
> all three oracles** → a semantic export-alias artifact on the oracle side, not decoder drift; correctly fenced.
> **C2E DoD met and exceeded (third independent oracle byte-identical).** The Runtime Kernel REPL side-quest is at
> its epic boundary: the loop should **HALT here and not invent further units.** Operator will re-charter the next
> direction (close the REPL epic / U2 ergonomics + tool runbook / a new epic). Do not flash, do not start a new
> kallsyms/decoder unit, do not touch the device.

**Guardrails: unchanged from below** (RECON / exploit-free; no RKP bypass; no protected-memory write; no
RWX; preserve `x17`; boot-partition-only flashes with pinned+readback SHA; rollback v2321; fails-twice →
STOP + report; keep raw runtime pointers/slide out of commits; scoped `git add`). Operator cross-checks any
recovered/verified address by independent disasm before a live rerun and steers via GOAL.md; the loop owns
host build + (sandbox-disabled) live + commits. v2b "show-buf" bulk peek is **superseded** by U1's
host-side looped `read` (no new image required); only build a new image if a future unit needs new on-device
behavior.

## 🟣 DONE — DELEGATED OPERATOR SIDE-QUEST — Tier-2 Stage C: confirm a patched-in direct `bl` executes under RKP_CFP

**DONE (2026-06-28) — direct `bl printk` executed under RKP_CFP and the device was rolled back to
clean v2321.** Stage A/B had already proven Tier-2 kernel `.text` patching boots and takes runtime
effect. Stage C now proves the last gate: a **new direct `bl` call** injected into reachable kernel
`.text` can execute under RKP_CFP. The loop first tried the wrong variadic target
(`printk_emit(..., fmt, ...)` at `0xffffff800813c814`), which rebooted without marker; it recovered,
rolled back to clean v2321, then corrected the locator to the plain `printk(fmt, ...)` wrapper at
`0xffffff800813d8cc`. The passing candidate SHA was
`21c567f0d3ebaa9d6caaa7c6310463fe7aa1710e5ca6a077305c36e489f16b8a`; `panic_on_oops=0` was set,
reading `/sys/class/kgsl/kgsl-3d0/num_pwrlevels` returned cleanly, and dmesg showed
`A90TIER2C`. `panic_on_oops=1` was restored, then v2321 rollback readback SHA matched
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`; final `version` and
`selftest` were clean (`pass=11 warn=1 fail=0`). Reports:
`docs/reports/KERNEL_SECURITY_TIER2_STAGE_C_DIRECT_BL_PRINTK_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/KERNEL_SECURITY_TIER2_STAGE_C_DIRECT_BL_PRINTK_LIVE_2026-06-28.md`. RECON guardrails
held: no grooming/UAF/EL1, no `ret`/`blr`/CFP-site patches, `x17` preserved, boot-partition-only
via `native_init_flash.py`.

## ✅ CLOSED — SoftAP server-endgame (S0→S4), DONE at V3344 (history below; loop re-chartered to the Runtime Kernel REPL side-quest above)

**STATUS (2026-06-27 S0 charter/recon) — V3336 pivots the loop from GPU to SoftAP and freezes the
target shape before any AP-mode mutation.** The goal is not the existing phone/router lab where A90 is
a Wi-Fi client. The endgame is A90 as the self-contained lab appliance: A90 brings up a WPA2 SoftAP,
serves a bounded local transfer endpoint, accepts a client connection, proves download/upload SHA
integrity, cleans up, and leaves `selftest fail=0`. Existing `wifi status/scan/connect/dhcp/ping`,
profile, autoconnect, `wifiinv`, and `wififeas` are useful prerequisites but are client-mode surfaces;
`docs/operations/A90_PHONE_WIFI_TRANSFER_SERVER.md` remains a client-mode data-path harness, not the
SoftAP target. Current public allowlist policy has `allow_server_exposure=false`, so the next unit must
make AP/server exposure explicit, bounded, private, and cleanup-backed before any daemon start. Report:
`docs/reports/NATIVE_INIT_V3336_SOFTAP_SERVER_ENDGAME_CHARTER_2026-06-27.md`.

**STATUS (2026-06-27 S1 read-only live inventory) — V3337 ran the no-flash, no-mutation SoftAP
inventory gate on resident `0.11.103`.** Bridge was healthy; `version/status/selftest` were clean
(`selftest pass=12 warn=1 fail=0`). `wifi status` reported `wlan0_present=0`, no carrier/IP/default
route, standalone supplicant executable present but stopped, ctrl socket missing, autoconnect disabled,
and `secret_values_logged=0`. `wifiinv` reported `net_total=9`, `wlan_like=0`, `rfkill_wifi=0`,
`module_matches=0`, `paths=9/26`, `file_matches=16`; current visible matches are system Wi-Fi rc/config
surfaces, not a native-visible hostapd AP stack. `wififeas` returned `decision=no-go` with gates
`wlan=no rfkill=no module=no candidates=yes`: do not enable Wi-Fi/AP mode from native-init with current
evidence. A read-only BusyBox applet inventory did show transfer/server helpers (`httpd`, `nc`,
`udhcpd`, `wget`, `sha256sum`) are present, so the server half is not the immediate blocker. **S1 is
DONE; next bounded source unit is S2 status/plan/dry-run plumbing that reports this no-go cleanly and
does not start hostapd/AP mode.** Report:
`docs/reports/NATIVE_INIT_V3337_SOFTAP_S1_READONLY_INVENTORY_LIVE_2026-06-27.md`.

**STATUS (2026-06-27 S2 status/plan source) — V3338 added the first `wifi softap` command surface
without AP bring-up.** `wifi softap`, `wifi softap status`, `wifi softap plan`, `wifi softap prepare
[profile]`, and `wifi softap cleanup` now evaluate `a90_wififeas` and print redaction-friendly
readiness fields, gate counters, plan steps, and explicit `*_attempted=0` fields for config write,
hostapd start, DHCP-server start, listener exposure, interface mode change, and address assignment.
`start_supported=0` and `start_allowed=0` are hard-coded in this S2 source unit while S1 remains
no-go. `prepare` is dry-run/no-op under the current blocker and reports
`softap-prepare-blocked-wlan-gate`; no SSID/PSK config is written. Updated the Wi-Fi lifecycle command
contract and added a focused source test. Host validation: `py_compile`, V3338 source test `5/5`, AArch64
`a90_wifi.c` object compile with `-Wall -Wextra -Werror`, and `git diff --check`. No boot image was
built, no flash was run, and no live Wi-Fi action was attempted. Report:
`docs/reports/NATIVE_INIT_V3338_SOFTAP_S2_STATUS_PLAN_SOURCE_2026-06-27.md`.

**STATUS (2026-06-27 S2 flash/live validation) — V3339 built, flashed, and live-validated the
SoftAP status/plan surface on-device.** Built
`boot_linux_v3339_softap_s2_status_plan.img`
(`sha256=5f23c579ddbcac75cf9859685f638cad3371e2ebf228af8e441c6863fa25858b`) from V3335,
flashed only through `native_init_flash.py`, and booted `A90 Linux init 0.11.104
(v3339-softap-s2-status-plan)` with boot readback SHA match and post-flash selftest
`pass=12 warn=1 fail=0`. After stopping the auto HUD/menu gate, live commands
`wifi softap status`, `wifi softap plan`, and `wifi softap prepare` all returned rc `0`.
They reported `wififeas.decision=no-go`, `gates.wlan=0`, `gates.rfkill=0`,
`gates.module=0`, `gates.candidates=1`, `start_supported=0`, `start_allowed=0`,
and all config/AP/server mutation fields as `0`; `prepare` reported
`prepare_dry_run=1` and `decision=softap-prepare-blocked-wlan-gate`. Follow-up
selftest stayed `pass=12 warn=1 fail=0`. **S2 is DONE; S3 AP bring-up remains blocked
until a future read-only lower-surface unit proves WLAN/AP prerequisites.** Reports:
`docs/reports/NATIVE_INIT_V3339_SOFTAP_S2_STATUS_PLAN_SOURCE_BUILD_2026-06-27.md` and
`docs/reports/NATIVE_INIT_V3339_SOFTAP_S2_STATUS_PLAN_LIVE_2026-06-27.md`.

**STATUS (2026-06-28 S3 lower WLAN/AP gate split) — V3340 proved the blocker is lineage-specific
and narrowed the remaining gate.** Reflashed the existing V3339 SoftAP S2 image and confirmed it still
has no `wlan0`: `wifi softap status` stayed `softap-status-blocked-wlan-gate`, `wifi scan` failed at
link-up with `errno=19`, and a lower probe showed `wlan0_present=0`. Then flashed the Wi-Fi-proven
V2237 fallback: after its normal long helper window, the helper exited cleanly with
`supervisor_result=wlan0-ready` and `wlan0_present=1`; standalone `wpa_supplicant` and BusyBox `udhcpd`
were present, and no station/AP/server worker was running. However, no `iw` binary was visible, so
the required `AP iftype settable` add/delete proof is still unverified. The device was rolled back to
V2321 with post-rollback selftest `pass=11 warn=1 fail=0`. **S3 remains blocked, but the next unit is now
specific: port the V2237 WLAN bring-up route into the current SoftAP baseline and add a tiny cfg80211/
nl80211 AP-iftype probe or stage a minimal private `iw` equivalent, before any `mode=2` AP start.**
Report: `docs/reports/NATIVE_INIT_V3340_SOFTAP_S3_LOWER_WLAN_SPLIT_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S3 iftype-probe source/build + live miss) — V3341 added the bounded
`wifi softap iftype-probe [timeout_ms]` AP-iftype add/delete proof, but live validation stopped before
AP-iftype because `wlan0` still did not surface.** Built
`boot_linux_v3341_softap_s3_iftype_probe.img`
(`sha256=a0fe07b1f347a2212d375067c442b163b7e6cd68cb7a605ab5dce4c87082c7af`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.105 (v3341-softap-s3-iftype-probe)`, and kept
health clean (`selftest pass=12 warn=1 fail=0`). The probe preserved the no-start contract
(`config_write_attempted=0`, `wpa_supplicant_mode2_start_attempted=0`, `dhcp_server_start_attempted=0`,
`listener_start_attempted=0`, `address_assign_attempted=0`, `server_exposure_attempted=0`) but timed
out at `wlan0_wait_rc=-110`, `wlan0_present=0`, so `ap_iftype_add_attempted=0`. Helper evidence showed
the post-FW_READY `boot_wlan` trigger succeeded and the kernel requested
`wlan/qca_cld/WCNSS_qcom_cfg.ini`, but the QCACLD firmware_class feeder repeatedly returned
`source_errno=2` and `fed=0`; the remaining blocker is now the read-only Android vendor firmware source
visibility/feed path, not the AP-iftype command itself. **Next bounded unit = V3342: restore a safe
read-only source route for `/vendor/firmware/wlan/qca_cld/*`, then rerun the same iftype probe before
any `wpa_supplicant mode=2` AP start.** Reports:
`docs/reports/NATIVE_INIT_V3341_SOFTAP_S3_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3341_SOFTAP_S3_IFTYPE_PROBE_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S3 firmware-source + lower AP gate pass) — V3342 restored the safe
read-only QCACLD firmware source route and proved the lower WLAN/AP gate.** Built
`boot_linux_v3342_softap_s3_fwsource_iftype_probe.img`
(`sha256=836f76249d578ef42e25a2d0c7b43cc3ef1d8db9efe5dabc6ee5ce13b10e5502`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.106 (v3342-softap-s3-fwsource-iftype-probe)`,
and kept health clean (`selftest pass=12 warn=1 fail=0`). Helper evidence showed
`source_policy=qcacld-fwsource-mounted-vendor-first`, `WCNSS_qcom_cfg.ini` `source_rc=0`, `fed=1`,
and `wlan0_present=1`. The bounded `wifi softap iftype-probe 220000` then passed:
`wlan0_wait_rc=0`, `wlan0_present=1`, `sta_supplicant.stoppable=1`, `ap_iftype_add_rc=0`,
`ap_iftype_iface_created=1`, `ap_iftype_cleanup_ok=1`, and `decision=softap-iftype-probe-pass`.
The no-start contract held (`config_write_attempted=0`, `wpa_supplicant_mode2_start_attempted=0`,
`dhcp_server_start_attempted=0`, `listener_start_attempted=0`, `address_assign_attempted=0`,
`server_exposure_attempted=0`). **Next bounded unit = V3343: start a private, cleanup-backed
`wpa_supplicant mode=2` SoftAP on 2.4GHz ch 1/6/11 with BusyBox `udhcpd`, no WAN/NAT/default-route
export, then run `softap cleanup` and keep `selftest fail=0`.** Reports:
`docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S3 mode=2 AP bring-up + cleanup pass) — V3343 started and cleaned up the first
bounded SoftAP service.** Built `boot_linux_v3343_softap_s3_mode2_bringup.img`
(`sha256=601e27287a1b695c326a99e27522e36bb5afde629da5b30b024f7f59ec5068e7`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.107 (v3343-softap-s3-mode2-bringup)`, and kept
health clean (`selftest pass=12 warn=1 fail=0`). The final `wifi softap start 6` passed with
`wlan0_wait_rc=0`, `wlan0_present=1`, `sta_supplicant.stoppable=1`, `ap_iftype_add_rc=0`,
`ap_iftype_iface_created=1`, `softap_ctrl_reply_category=pong`, `softap.ctrl_status.field.mode=AP`,
`softap.ctrl_status.field.wpa_state=COMPLETED`, `wpa_supplicant_mode2_start_attempted=1`,
`dhcp_server_start_attempted=1`, `dhcp_server_alive=1`, and `decision=softap-start-pass`.
Safety fields stayed closed (`hostapd_start_attempted=0`, `listener_start_attempted=0`,
`server_exposure_attempted=0`, `wan_nat_attempted=0`, `nat_attempted=0`,
`default_route_export_attempted=0`, `dhcp_router_option_exported=0`, `ssid_psk_logged=0`). The final
`wifi softap cleanup` passed (`cleanup.rc=0`, `final_supplicant_count=0`, `final_udhcpd_count=0`,
`final_iface_present=0`, `decision=softap-cleanup-pass`) and post-cleanup selftest stayed
`pass=12 warn=1 fail=0`. **Next bounded unit = S4: start the local transfer server on the private AP,
have a client join, prove HTTP download/raw upload SHA integrity, stop server/AP, and keep public output
redacted.** Reports:
`docs/reports/NATIVE_INIT_V3343_SOFTAP_S3_MODE2_BRINGUP_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3343_SOFTAP_S3_MODE2_BRINGUP_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S4 private transfer server proof) — V3344 closed the SoftAP server-endgame
with a client transfer integrity proof.** Built `boot_linux_v3344_softap_s4_transfer_server.img`
(`sha256=d24fe3fded67d83a1bd87b13f3459bdaec6d588cb947a5231cc08d6c397515a8`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.108 (v3344-softap-s4-transfer-server)`, and kept
health clean (`selftest pass=12 warn=1 fail=0`). The final `wifi softap transfer-start 6` passed
with `wlan0_present=1`, `sta_supplicant.stoppable=1`, `ap_iftype_add_rc=0`,
`softap.ctrl_status.field.mode=AP`, `softap.ctrl_status.field.wpa_state=COMPLETED`,
`dhcp_server_alive=1`, `httpd_alive=1`, `upload_receiver_alive=1`,
`download_payload_bytes=1048576`, `server_bind_private_ap_only=1`, and
`decision=softap-transfer-start-pass`. A host client joined the private AP using private runtime
credentials; public artifacts do not record SSID/PSK/client identifiers/concrete network addresses.
HTTP download matched SHA256 `0fb3f6622678efe11f84f3bf032031802a8745d9c8a1f834aece10fe6d1bbd62`.
Raw upload matched SHA256 `3cd6eccfa373a28f7a411ef5cbdc3c407ada3eaf2263ef5879531989d9dc4348`
on both host and device, with `upload_result=pass`, `upload_result.bytes=1048576`, and
`upload_result.truncated=0`. `wifi softap cleanup` passed with `cleanup.final_httpd_count=0`,
`cleanup.final_supplicant_count=0`, `cleanup.final_udhcpd_count=0`, `cleanup.final_iface_present=0`,
and post-cleanup selftest stayed `pass=12 warn=1 fail=0`. **S0→S4 is DONE. Next bounded unit =
post-endgame hardening/reporting cleanup only: decide whether to promote a reusable host-side S4
validation helper and remove stale S2/S3 wording from narrow tests/docs.** Reports:
`docs/reports/NATIVE_INIT_V3344_SOFTAP_S4_TRANSFER_SERVER_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3344_SOFTAP_S4_TRANSFER_SERVER_LIVE_2026-06-28.md`.

- **S0 (host-only charter/recon) = DONE.** Inventory current command/docs/source surface, distinguish
  client-mode Wi-Fi from SoftAP/server mode, and write the bounded ladder + safety recipe.
- **S1 (read-only live AP/server inventory) = DONE / NO-GO BELOW WLAN.** Current resident has no
  wlan-like interface, Wi-Fi rfkill, or module evidence; transfer applets exist.
- **S2 (source contract + config materialization) = DONE / LIVE VALIDATED BELOW AP START.** Added an explicit `wifi softap`
  command surface with
  `status`, `plan`, and dry-run config materialization under `/cache/a90-softap/`; generated SSID/PSK
  remain private-only, public output reports hashes/booleans only. While S1 remains no-go, S2 must stop
  at status/plan/prepare and must not start hostapd/AP mode.
- **S3 (bounded AP bring-up) = DONE / LIVE VALIDATED.** V3342 proved `wlan0` present, STA supplicant
  stoppable, and AP iftype add/delete with cleanup. V3343 then configured a private local AP subnet, started
  `wpa_supplicant mode=2` on a 2.4GHz non-DFS channel, started bounded BusyBox `udhcpd`, exposed no
  WAN/NAT/default route/server listener by default, and validated `softap cleanup` worker/interface removal.
- **OPERATOR RECON (2026-06-27, host-verified — answers the S3 "lower WLAN/AP gate" + corrects the daemon
  choice).** SoftAP is NOT non-viable; all three layers already exist on this device (verified host-only
  from the stock `System.map` + staged userland, no device action):
  1. **Driver/SAP = built into the stock kernel** (qcacld), 84 SAP symbols incl. `hdd_hostapd_open`,
     `hdd_softap_register_sta`/`stop_bss`/`sta_deauth`/`set_channel_change`, `wlan_hdd_cfg80211_change_beacon`,
     `__cfg80211_stop_ap`, `sap_fsm`, and even `hdd_softap_inspect_dhcp_packet` (the AP/tether path is real).
     Concurrency policy is present too (`policy_mgr_allow_sap_go_concurrency`, `policy_mgr_add_sap_mandatory_chan`,
     `hdd_set_sap_ht2040_mode`), but the first bring-up should be single-AP after stopping the STA supplicant.
  2. **AP daemon = DO NOT stage hostapd.** The already-proven Ubuntu `wpa_supplicant 2.11` binary in the
     staged `ubuntu-arm64-wpa` runtime is built with `CONFIG_AP` (117 AP strings incl.
     `hostapd_setup_interface_complete_sync`). Run SoftAP via `wpa_supplicant` **`mode=2`**, reusing the exact
     client-mode binary + libs already working — this skips the whole hostapd cross-compile/stage detour.
  3. **DHCP = busybox `udhcpd`** (`CONFIG_UDHCPD=y`, already built in); no dnsmasq needed.
  4. **Pin the first AP to 2.4GHz ch 1/6/11** to avoid the 5GHz DFS CAC path (`sap_fsm_cac_start`) — DFS adds
     radar-CAC delay/complexity that will stall first proof. No WAN/NAT (`allow_server_exposure=false` stays
     frozen). So the S3 "lower gate" read-only unit just needs to confirm wlan0 present + AP iftype settable +
     supplicant stoppable; the driver capability question is already answered YES here.
- **S4 (server-endgame proof) = DONE / LIVE VALIDATED.** V3344 started the local transfer server on
  the AP, had a host client join, proved HTTP download and raw upload SHA integrity, stopped the
  server/AP, and confirmed follow-up `selftest fail=0` while public artifacts redacted SSID/PSK,
  client identifiers, and concrete network addresses.

`native_gpu_compute_c0_reference_v3299.py` encodes and validates the staged A640 compute dispatch envelope against
`/tmp/a90-mesa-gpu-src/`: CS program regs, `CP_LOAD_STATE6` shader/constant/UAV state, `RM6_COMPUTE`, NDRANGE,
`CP_EXEC_CS`, and WFI/readback ordering all match the Mesa computerator/fd6 references; `kern_invocationid.asm` is fixed
to a 32-lane `buf[i] == i` proof. V3300 then materialized that kernel into verified A640 CS shader words with a bounded
host-only full-NIR freedreno tool build under `/tmp/a90-mesa-c1-fullnir-softpipe-v3300` and `ir3-disasm -g FD640`.
The verified C1 shader is 32 dwords / 128 bytes, `instrlen=1`, `constlen=4`, `local_size=32,1,1`,
`sha256=7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a`, and disassembles to
`mov.u32u32 r0.y, r0.x`; `(rpt5)nop`; `stib.b.untyped.1d.u32.1.imm r0.x, r0.y, 0`; `end`. No boot artifact was built
and no flash was run for V3300. V3301 embeds those verified CS words in native-init, adds
`gpu c1-compute-invocationid-probe`, binds one 32-word R32_UINT UAV descriptor, emits `SP_CS_*`, `LOAD_STATE6`
shader/constants/UAV, `RM6_COMPUTE`, and `CP_EXEC_CS`, then gates success on WFI/readback where all `buf[i] == i`.
V3301 source/build validation produced
`workspace/private/inputs/boot_images/boot_linux_v3301_gpu_compute_c1_invocationid_probe.img`
(`sha256=c4128f367a17f2481866142d79942d958ea19fa34528937dece6edf3d04e7dfa`, size 66052096 bytes);
flash/readback verified the exact artifact, booted `0.11.75`, and the live
`gpu c1-compute-invocationid-probe --timeout-ms 5000 --materialize-devnode` run passed:
`readback0=0`, `readback1=1`, `readback31=31`, `expected_match_count=32`, `mismatch_count=0`, `pass=1`,
`total_elapsed_ms=28`. Post-probe selftest stayed `fail=0`, and the bridge capture fault filter found no GPU
fault/hang/page-fault match. V3302 embeds a verified 32-dword FD640 workgroup-id CS shader
(`sha256=9259cd6e225aba4d1e86fb88527494404617b2aaf753c948379ade2edb18a6d1`, asm
`sha256=1f7f223c66a97975e416dce96b0a960933b7fa21b7bf4c6d380b3eb63e31b0d6`) and dispatches
16,384 one-lane workgroups into a 128x128 R32_UINT UAV. V3302 source/build validation produced
`workspace/private/inputs/boot_images/boot_linux_v3302_gpu_compute_c2_pattern_probe.img`
(`sha256=3f437360d9c428548fb1d89dfa90d56091313375c0b04578c45d95021d43af5a`, size 66117632 bytes);
flash/readback verified the exact artifact, booted `0.11.76`, and the live
`gpu c2-compute-pattern-probe --timeout-ms 5000 --materialize-devnode` run passed:
`readback0=0`, `readback1=1`, `readback127=127`, `readback128=128`, `readback4096=4096`,
`readback8192=8192`, `readback16383=16383`, `expected_match_count=16384`, `mismatch_count=0`,
`pass=1`, `total_elapsed_ms=15`. Post-probe selftest stayed `fail=0`, and the bridge capture fault
filter found no GPU fault/hang/page-fault match. V3303 then added `gpu c3-compute-kms-probe`, which
runs the C2 probe, writes a bounded 64KiB UAV snapshot, verifies the snapshot, expands it into the KMS
dumb framebuffer, presents, and holds. V3303 source/build validation produced
`workspace/private/inputs/boot_images/boot_linux_v3303_gpu_compute_c3_kms_probe.img`
(`sha256=0a041e834cedae3b54bea5c1b4fb70b4be133156e8c9317d8f6c30b304c01e20`, size 66117632 bytes);
flash/readback verified the exact artifact and booted `0.11.77`. The live
`gpu c3-compute-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode` run passed:
`snapshot_write_bytes=65536`, `snapshot_expected_match_count=16384`, `snapshot_mismatch_count=0`,
`blit_rect=92,752,896,896`, `blit_scale=7`, `present_rc=0`, `result=compute-pattern-presented`,
`hold_elapsed_ms=30000`, `vis.result=compute-pattern-presented-held`, `rc=0`, `duration_ms=30161`.
Post-probe selftest stayed `fail=0`, and the bridge capture fault filter found no GPU
fault/hang/page-fault match. A later 60 s eye-confirm replay attempt was paused before a new proof could be collected
because the host lost the A90 USB gadget (`serial-missing`, no ACM/ADB/NCM after 90 s); no new flash or rollback was
attempted. USB visibility later recovered; resident `0.11.77` health stayed `selftest fail=0`, and the existing V3303
C3 command was replayed with a 60 s hold: `snapshot_expected_match_count=16384`,
`snapshot_mismatch_count=0`, `present_rc=0`, `result=compute-pattern-presented`, `hold_elapsed_ms=60000`,
`vis.result=compute-pattern-presented-held`, `rc=0`, `duration_ms=60041`; post-replay selftest stayed `fail=0`, and
the GPU fault filter had no match. A final replay again returned `0.11.77`, pre/post `selftest fail=0`,
`present_rc=0`, `vis.result=compute-pattern-presented-held`, 60 s hold, and no GPU fault-filter match. The operator
then visually confirmed the expected held pattern on the panel: "무지개 그라데이션과 네모난 격자무늬 프렉탈 같은검 말하는건가? 보인다".
C3 is therefore closed, and the visible compute-demo C0→C3 ladder is DONE + EYE-CONFIRMED. V3304 then pre-staged a
fresh sparse Mesa freedreno reference at `/tmp/a90-mesa-gpu-src` (commit
`6adb0d5e01dca952fcb04b7773ad92b0ab2e132d`) and added `native_gpu_2d_d0_texture_reference_v3304.py`. The D0 recon
passed against `fd6_texture.cc`, `fd6_texture.h`, `fd6_emit.cc`, `fd6_emit.h`, `fd6_program.cc`, `a6xx.xml`,
`adreno_pm4.xml`, and `ir3-cat5.xml`: sampler descriptors are 4 dwords, TEXMEMOBJ descriptors are 16 dwords, FS texture
state is `FD6_GROUP_FS_TEX`, FS sampler load is `CP_LOAD_STATE6_FRAG` + `ST6_SHADER` + `SB6_FS_TEX`, FS TEXMEMOBJ load
is `CP_LOAD_STATE6_FRAG` + `ST6_CONSTANTS` + `SB6_FS_TEX`, `SP_PS_CONFIG` carries `NTEX/NSAMP`, and the non-bindless
cat5 `sam` contract exposes `s#0/t#0`. V3305 then added
`native_gpu_2d_d1_textured_shader_bytes_v3305.py`, using a local libdrm-backed Mesa tool build under
`/tmp/a90-mesa-d1-texture-build-libdrm` to materialize and `ir3-disasm` verify the minimal FD640 textured FS:
`bary.f r0.x, 0, r0.x`; `bary.f r0.y, 1, r0.x`; `sam (f32)(xyzw)r0.z, r0.x, s#0, t#0`; `end`; padded nops.
The shader is 32 dwords / 128 bytes, `instrlen=1`, `constlen=0`, `max_reg=1`, `max_half_reg=-1`,
`num_samp=1`, `num_tex=1`, `sha256=4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3`, and its
sample output register `r0.z` maps to scalar regid 2, matching the existing H3 color-output contract
(`GPU_H3_PS_OUTPUT_REGID=2`, fullregfootprint covers the payload, RGBA8 MRT contract present). V3310 then closed D1 with
`gpu d1-texture-checkerboard-probe`: a 128x128 static checkerboard sampled through the textured FS, linearized, and
verified with a full 128x128 changed readback plus 64/64 bbox-local checker samples. V3311 then closed D2 with
`gpu d2-realframe-texture-probe --preset badapple --frame-index 515`: the device read the SD-cache Bad Apple mono1
A90VSTR1 stream, expanded frame 515 into a 480x360 RGBA8 texture, rendered it into the 128x128 target, and matched all
64 bbox-local source-frame samples (`source_dark_count=86381`, `source_light_count=86419`, output dark/light positive,
`output_other_count=0`). V3312 then implemented D3 video-present plumbing but live validation found two host-visible
contract bugs: the command rejected the report's `--timeout-ms 120000` because the probe still used the 10 s G0 ceiling,
and the forked child returned through the shell/A90P1 completion path before the parent could print summary telemetry.
V3313 fixed both issues (`GPU_D3_VIDEO_MAX_TIMEOUT_MS=120000`, child writes the summary pipe and `_exit()`s) and passed
the D3 live telemetry gate: 60 Bad Apple frames uploaded as textures, rendered to a 960x720 target, A2D-linearized,
copied into KMS, and presented with `gpu.d3.video.result=video-texture-present-pass`, `presented=60`,
`fps_milli=29969`, `changed_total=41472000`, `copy.avg_us=16653`, `present.avg_us=13924`, post-probe
`selftest fail=0`, and no GPU fault-filter match. A follow-up no-flash eye-confirm replay held the same V3313
GPU-blit path for 60 s and passed again: `gpu.d3.video.result=video-texture-present-pass`, `presented=60`,
`fps_milli=30177`, `changed_total=41472000`, `copy.avg_us=16585`, `present.avg_us=13794`, post-replay
`selftest fail=0`, and no focused dmesg fault-filter match. V3314 then strengthened the close gate by adding
`--start-frame` and final-frame semantic sampling, so the 60 s hold starts from the high-contrast Bad Apple segment
instead of the black intro. The V3314 live run rendered and held 60 frames from frame 515, presented successfully,
produced only black/white output pixels (`semantic_output_other_count=0`), and stayed healthy, but the exact semantic
sample gate returned `63/64` because one source-edge sample expected white while the scaled texture output was black.
V3315 then accepted a bounded 3x3 source-neighborhood match around scaled texture edges while still requiring 64/64
semantic samples and zero non-binary output pixels. The V3315 live run passed with `video-texture-present-pass`,
`presented=60`, `fps_milli=29655`, `changed_total=41472000`, `semantic_sample_count=64`, `match_count=64`,
`exact_match_count=63`, `edge_tolerant_match_count=1`, `mismatch_count=0`, `output_other_count=0`, post-probe
`selftest fail=0`, and no focused dmesg fault-filter match. A follow-up no-flash eye-confirm replay held the same
V3315 GPU-blit path for 60 s and passed again: `video-texture-present-pass`, `presented=60`, `fps_milli=29908`,
`semantic_sample_count=64`, `match_count=64`, `exact_match_count=63`, `edge_tolerant_match_count=1`,
`mismatch_count=0`, `output_other_count=0`, post-replay `selftest fail=0`, and no focused dmesg fault-filter match.
A later attempt to extend the hold to 120 s correctly hit the current guard (`bad-hold max_ms=60000`), then replayed
the supported max 60 s hold again with the same clean result (`video-texture-present-pass`, `presented=60`,
`fps_milli=30005`, `match_count=64`, `edge_tolerant_match_count=1`, `mismatch_count=0`, `output_other_count=0`,
post-replay `selftest fail=0`, no fault-filter match). The operator then visually confirmed the held frame on the
physical panel: "배드애플 보였다 프레임은 정상적으로 나오는거 같았다". D3 and rung ② are therefore DONE +
EYE-CONFIRMED. The next GPU-chain item is ③ modularization/extraction: pull the common KGSL submit/fence/buffer layer
only now that triangle, compute, and accelerated 2D are all real consumers.

**(historical, first-triangle ladder — DONE record)** Threshold from fixed-function plumbing to *real GPU
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
V3236/V3237 then kept that r1 shader-output split and raised VS/PS `FULLREGFOOTPRINT` to `2`, producing
`SP_VS_CNTL_0=0x00100100` and `SP_PS_CNTL_0=0x81000100`. The image flashed as `0.11.45
(v3236-gpu-h3-shader-footprint-probe)` and passed post-flash health (`selftest pass=12 warn=1 fail=0`). The first H3
attempt timed out, but focused dmesg showed the actual blocker was fresh-boot firmware visibility:
`request_firmware(a630_sqe.fw) failed` while `firmware_class.path` pointed at `/vendor/firmware_mnt/image`; `gpu
g0-status` showed the SQE/GMU firmware present in `/cache/a90-runtime/pkg/gpu-g0-fw`. After `gpu g0-fwclass-prepare`,
G0 open returned in `26ms`, G3 noop retired in `9ms`, and the same H3 draw retired (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=12`) with no GPU fault/hang signature. Readback still
stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still
not reached. This removes the V3234 timeout as a shader-footprint objection under the correct G0 firmware prep
precondition, and exposes a validation hazard: H3/H4 probes must either run G0 fwclass prep during materialization or
require it as a preflight before KGSL open. Next bounded unit should close that preflight hole, then continue remaining
Mesa first-draw packet deltas around RB/CCU/FS-output or shader-output linkage before claiming H4.
V3238/V3239 then closed that preflight hole by moving `gpu g0-fwclass-prepare` into `gpu_g0_materialize_devnode()`.
The image flashed as `0.11.46 (v3238-gpu-g0-fwclass-materialize-prep-probe)` and passed health. Fresh-boot `gpu
g0-status` intentionally showed the old hazard (`firmware_class.path=/vendor/firmware_mnt/image`, `/dev/kgsl-3d0`
missing, SQE/GMU present only in `/cache/a90-runtime/pkg/gpu-g0-fw`). Without running manual prepare, the H3
`--materialize-devnode` path then emitted `gpu.g0.materialize.fwclass_prepare_attempted=1`,
`gpu.g0.fwclass_prepare.result=ok`, `gpu.g0.materialize.fwclass_prepare_rc=0`, created `/dev/kgsl-3d0`, and the draw
retired (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=31`) with no GPU
SQE timeout/fault/hang signature. Readback still stayed unchanged (`readback_changed_count=0`,
`readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still not reached. This removes firmware-path false
timeouts from future H3/H4 work; next bounded unit should return to the remaining first-triangle packet/linkage gap,
likely RB/CCU/FS-output or shader-output contract, before claiming H4.
V3240/V3241 then tested the Mesa A6xx `sample_locations_disable_stateobj` gap by adding
`GRAS_SC_MSAA_SAMPLE_POS_CNTL=0`, `RB_MSAA_SAMPLE_POS_CNTL=0`, and `TPL1_MSAA_SAMPLE_POS_CNTL=0` to H3. The image
flashed as `0.11.47 (v3240-gpu-h3-sample-location-probe)` with SHA256
`9fc11231bc8267174a8ecc20bb7ba7aac77604ea5fdff8eba7fd406eb4b7501b` and passed post-flash health (`selftest
pass=12 warn=1 fail=0`). Fresh-boot `gpu g0-status` again showed the expected pre-materialization hazard, and the H3
`--materialize-devnode` path automatically ran fwclass prep (`gpu.g0.materialize.fwclass_prepare_attempted=1`,
`gpu.g0.fwclass_prepare.result=ok`, `gpu.g0.materialize.fwclass_prepare_rc=0`). The draw retired cleanly with the new
state counts (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=229`,
`state_reg_writes=91`, `total_elapsed_ms=31`) and no focused dmesg timeout/fault/hang/snapshot signature, but readback
still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes
the tested sample-location disable-state group as the primary blocker; next bounded unit should continue the remaining
Mesa first-draw packet/linkage diff around RB/CCU/FS-output or the shader-output contract before claiming H4.
V3242/V3243 then tested the operator-supplied CP render-mode hypothesis by adding Mesa A6xx
`CP_SET_MARKER(RM6_DIRECT_RENDER)` (`opcode=0x65`, payload `0x00000001`) immediately after the initial WFI and before
H3 3D state, while also keeping sysmem `RB_CCU_CNTL=0x10000000` for Adreno640v2 (`num_ccu=2`, color offset
`0x20000`). The image flashed as `0.11.48 (v3242-gpu-h3-direct-render-marker-probe)` with SHA256
`eb472fa77edfe20cfeeb5dd280279ba1203e2d4e3fd34d236d81e780bcb5ef13` and passed post-flash health (`selftest
pass=12 warn=1 fail=0`). Live H3 telemetry confirmed `gpu.h3.draw.cp_set_marker=0x1`, `pm4_dwords=233`, and
`state_reg_writes=92`; the draw still submitted and retired (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
`total_elapsed_ms=31`) with no KGSL/GPU fault/hang/snapshot/timeout signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes missing
`CP_SET_MARKER(RM6_DIRECT_RENDER)` as the primary no-pixel root cause. Next bounded unit should prioritize the remaining
shader/output contract: prove the hand-assembled ir3 VS writes the clip-space position to the VPC-consumed position
output slot and that the FS output register/MRT linkage matches the current `r1` split, before doing another broad
register sweep. LRZ is already programmed disabled in the state stream and RB CCU sysmem control is present, so keep
those lower priority unless new evidence reopens them.
V3244/V3245 then tested the smallest output-register fallback by keeping the V3242 direct-render marker, RB CCU sysmem,
sample-location, static-context, and fullregfootprint state intact while switching the hand-assembled ir3 contract to
`r0`: VS passes through `r0.xy` and writes `r0.zw=0/1`, FS writes color to `r0.x`, and VS/PS output regids are both
`0` (`SP_VS_OUTPUT_REG0=0x00000f00`). The image flashed as `0.11.49 (v3244-gpu-h3-r0-output-probe)` with SHA256
`9764d950f93ada582b5b853c17dcf480635df0aeffe5ee90d6cab7845533c66d` and passed post-flash health (`selftest
pass=12 warn=1 fail=0`). Live telemetry confirmed the r0 contract (`vs_output_regid=0x0`, `ps_output_regid=0x0`,
`sp_vs_output_reg0=0xf00`) with unchanged envelope counts (`pm4_dwords=233`, `state_reg_writes=92`); the draw again
submitted and retired (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `total_elapsed_ms=29`) with no KGSL/GPU
fault/hang/snapshot/timeout signature, but readback stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`). This removes a simple `r1` output-register mismatch as the primary no-pixel root cause.
Next bounded unit should stop toggling output regid alone and prove the shader execution contract more directly:
disassemble/audit the exact hand-assembled ir3 words including scheduling bits, or replace them with a minimal
known-good compiler/disassembler-derived ir3 payload while preserving the same KGSL-direct envelope.
V3246 then performed that host-side shader-byte audit without changing or flashing a boot artifact. A minimal Mesa
freedreno `ir3-disasm` was built under `/tmp/a90-mesa-h3-build-ir3` and
`native_gpu_h3_shader_byte_audit_v3246.py --require-ir3-disasm` decoded the exact H3 words from
`80_shell_dispatch.inc.c`: VS is `mov.f32f32 r0.x,r0.x`; `mov.f32f32 r0.y,r0.y`;
`mov.f32f32 r0.z,(0.0)`; `mov.f32f32 r0.w,(1.0)`; `end`; `nop`, and FS is
`mov.f32f32 r0.x,(1.0)`; `end`; `nop`; `nop`. All decoded words have no `(ss)`/`(sy)` flags, matching the current
plain hand encoding. The audit also closes two targeted register-side shader contract suspicions: FS writes a full f32
`r0.x` and `SP_PS_OUTPUT_REG0` has `HALF_PRECISION=0`, so the current full-output path is internally consistent; position
is designated by `VPC_VS_CNTL.positionloc=0` plus `SP_VS_VPC_DEST_REG0.OUTLOC0=0`, while `VPC_VS_SIV_CNTL=0xffff` is only
the layer/view sentinel, not the position selector. This makes the exact hand-assembled bytes unlikely to be the
no-pixel root cause. Next bounded unit should compare the remaining first-draw packet/linkage delta outside the already
verified shader bytes, especially render-target/RB linkage or any compiler-emitted minimal-shader state that is still
absent from the KGSL-direct envelope.
V3247/V3248 then tested a concrete remaining Mesa A6xx RB linkage delta by changing the already-emitted
`RB_RENDER_CNTL` value from `0x00000000` to `0x00000010`, matching `fd6_gmem.cc::update_render_cntl()` with
`CCUSINGLECACHELINESIZE=2`, while keeping the V3244 r0 shader contract, V3246 audited ir3 bytes, direct-render marker,
RB CCU sysmem state, sample-location defaults, static-context defaults, and firmware-class materialize preflight intact.
The image built as `0.11.50 (v3247-gpu-h3-rb-render-cntl-probe)` with SHA256
`56ea2b9aa2b46e2c5257db52c4c05a392871bed67fbd6c6a61807a880d3a5f4e`, flashed through `native_init_flash.py`, passed
post-flash health (`selftest pass=12 warn=1 fail=0`), and live telemetry confirmed `gpu.h3.draw.rb_render_cntl=0x10`
with unchanged envelope counts (`pm4_dwords=233`, `state_reg_writes=92`). The draw again submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=29`) and the focused dmesg
filter found no KGSL/GPU fault, hang, snapshot, or timeout signature, but the readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the missing
`RB_RENDER_CNTL.CCUSINGLECACHELINESIZE=2` hypothesis as the primary no-pixel root cause. Next bounded unit should
continue outside shader bytes and this RB render-control field, using a remaining Mesa first-draw packet diff to isolate
a narrower render-target/cache/visibility or draw-mode delta before claiming H4.
V3249/V3250 then tested the Mesa A6xx restore-path cache/visibility hypothesis by adding `fd6_cache_inv()` before the
H3 shader/state/draw packets: `CP_EVENT_WRITE(PC_CCU_INVALIDATE_COLOR=0x19)`,
`CP_EVENT_WRITE(PC_CCU_INVALIDATE_DEPTH=0x18)`, `CP_EVENT_WRITE(CACHE_INVALIDATE=0x31)`, then `CP_WAIT_FOR_IDLE`. The
image built as `0.11.51 (v3249-gpu-h3-cache-invalidate-probe)` with SHA256
`167251fa73fa537c8a3c75716a7b7e3061605b62a0fd24494a11805d089c50a6`, flashed through `native_init_flash.py`, and passed
post-flash health (`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed the candidate sequence
(`pre_draw_cache_invalidate_events=0x19,0x18,0x31`) and the expected command growth (`pm4_dwords=240`,
`state_reg_writes=92`) while preserving `rb_render_cntl=0x10`. The draw again submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=29`), and the focused dmesg
filter found no KGSL/GPU fault, hang, snapshot, or GPU timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes missing pre-draw
CCU/UCHE invalidation as the primary no-pixel root cause. Next bounded unit should continue with a narrower
first-draw packet diff outside shader bytes, `RB_RENDER_CNTL`, and pre-draw cache invalidation; good remaining targets
are draw-state bootstrap such as `CP_SET_MODE`/`SP_UPDATE_CNTL`/restore state ordering, or another concrete
compiler-emitted program/output state delta if it can be isolated before flashing.
V3251/V3252 then tested the operator-identified shader-binary/load-contract hypothesis. The source unit replaced the H3
VS with the local Mesa reference minimal VS bytes (`mov.u32u32 r0.z, 0x3f800000`; `mov.u32u32 r0.w, 0x3f800000`;
`end`; zero padding), kept the V3246 `ir3-disasm`-audited FS, aligned both shader BO payloads to 128 bytes, and changed
`SP_VS_INSTR_SIZE`, `SP_PS_INSTR_SIZE`, and CP_LOAD_STATE6 shader `NUM_UNIT` to Mesa-style `instrlen=1`. The image
built as `0.11.52 (v3251-gpu-h3-compiler-vs-instrlen-probe)` with SHA256
`ac608fe5914a834b5f895c79ee28b4c4d5212b8fbdbcec0e73408fde92226426`, flashed through `native_init_flash.py`, passed
post-flash health (`selftest pass=12 warn=1 fail=0`), and live telemetry confirmed the new shader-load contract
(`vs_shader_dwords=32`, `fs_shader_dwords=32`, `vs_shader_instrlen=1`, `fs_shader_instrlen=1`, `ir3_instr_align=16`,
`ir3_mov_u32u32_r0z_hi=0x204cc002`, `ir3_mov_u32u32_r0w_hi=0x204cc003`). Two H3 runs submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and the focused dmesg filter found no
KGSL/GPU fault, hang, snapshot, or timeout signature, but the readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes unverified shader bytes
and shader `instrlen`/load unit count as the primary no-pixel root cause. Next bounded unit should stay shader-byte
frozen unless a real disassembler-backed mismatch appears, and instead isolate a concrete Mesa first-draw packet delta
outside shader bytes: draw-state bootstrap ordering, `CP_SET_MODE`/`SP_UPDATE_CNTL`-style restore state, or the sysmem
MRT/CCU visibility path.
V3253/V3254 then tested the next concrete Mesa first-draw packet delta by adding draw-local `SP_UPDATE_CNTL=0x0000009f`
at register `0xbb08` before H3 shader state, matching the local freedreno A6xx draw/program state object pattern
(`VS_STATE|HS_STATE|DS_STATE|GS_STATE|FS_STATE|GFX_UAV`, bindless masks zero). The image built as
`0.11.53 (v3253-gpu-h3-sp-update-cntl-probe)` with SHA256
`1395721839c41ac07ff41379fabaa298d40479b237384add1bcfb6c1837d5769`, flashed through `native_init_flash.py`, passed
post-flash health after a serial bridge restart cleared one stale framing failure (`selftest pass=12 warn=1 fail=0`),
and live telemetry confirmed `sp_update_cntl=0x9f`, `pm4_dwords=242`, and unchanged `state_reg_writes=92`. Two H3 runs
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`), and the
focused dmesg filter found no KGSL/GPU fault, hang, snapshot, or timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the missing draw-local
`SP_UPDATE_CNTL=0x9f` packet as the primary no-pixel root cause. Remaining bounded work should stay outside shader bytes
and now focus on restore-state ordering/`CP_SET_MODE` versus the sysmem MRT/CCU visibility path.
V3255/V3256 then tested the Mesa sysmem render-pass bin-control delta. Source review first ruled out the proposed A640
`RB_CCU_CNTL` magic-value change: local Mesa A640 trace and `config_sysmem` calculation both confirm current
`RB_CCU_CNTL=0x10000000`. V3255 instead added the missing sysmem `set_bin_size` pair,
`GRAS_SC_BIN_CNTL=0x02c00000` and `RB_CNTL=0x02c00000`, built as
`0.11.54 (v3255-gpu-h3-sysmem-bin-control-probe)` with SHA256
`0ccb33c25dcbbf9a8274d2d569c135a48a9ef208bb27e512d0cd73687a651501`, flashed through `native_init_flash.py`, and
passed post-flash health after a host-side serial bridge restart cleared a transaction-lock/framing issue caused by
parallel manual health commands (`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed
`gras_sc_bin_cntl=0x2c00000`, `rb_cntl=0x2c00000`, `pm4_dwords=246`, and `state_reg_writes=94`. Two H3 runs submitted
and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=13`), with no focused
KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes missing sysmem
`GRAS_SC_BIN_CNTL/RB_CNTL` as the primary no-pixel root cause. Next bounded unit should avoid broad register sweeping
and diff against fd6 sysmem prep/draw ordering; one concrete remaining mismatch already visible is Mesa
`VPC_SO_OVERRIDE(false)` while current H3 still reports `vpc_so_override=0x1`.
V3257/V3258 then tested that mismatch directly by changing `VPC_SO_OVERRIDE` at register `0x9306` from `0x1` to
Mesa sysmem prep's `0x0` (`VPC_SO_OVERRIDE(false)`). The image built as
`0.11.55 (v3257-gpu-h3-vpc-so-override-probe)` with SHA256
`c308eee87756e5417b6b356a83c4c9c3721b056b4b9f37797b2a3269596db7e1`, flashed through `native_init_flash.py`, and
passed post-flash health after one host-side bridge connection reset was cleared by a short wait and sequential retry
(`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed `vpc_so_override=0x0`, `pm4_dwords=246`, and
`state_reg_writes=94`. Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, warm `total_elapsed_ms=12`), with no focused KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout
signature, but readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`). This removes `VPC_SO_OVERRIDE=0x1` as the primary no-pixel root cause. Next bounded
packet delta should continue from `fd6_emit_sysmem_prep()` rather than broad register sweeping: Mesa emits
`CP_SKIP_IB2_ENABLE_GLOBAL=0`, `CP_SKIP_IB2_ENABLE_LOCAL=1`, and `CP_SET_VISIBILITY_OVERRIDE=1` before the large
draw-state CRB, and current H3 does not emit those packets.
V3259/V3260 then tested that exact Mesa sysmem-prep packet trio. V3259 added
`CP_SKIP_IB2_ENABLE_GLOBAL=0`, `CP_SKIP_IB2_ENABLE_LOCAL=1`, and `CP_SET_VISIBILITY_OVERRIDE=1` immediately after the
direct-render marker and before H3 3D state, built as `0.11.56 (v3259-gpu-h3-visibility-packets-probe)` with SHA256
`48854bdd6d11d658254c364456f55e794c247484cb0b8f199065a9354f95f02a`, flashed through `native_init_flash.py`, and
passed post-flash health after one host-side serial bridge framing issue was cleared by restarting the managed bridge
and retrying health checks sequentially (`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed
`cp_skip_ib2_enable_global=0x1d` value `0x0`, `cp_skip_ib2_enable_local=0x23` value `0x1`,
`cp_set_visibility_override=0x64` value `0x1`, `pm4_dwords=252`, and `state_reg_writes=94`. Two H3 runs submitted
and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=11`), with no focused
KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the missing
visibility/IB2 sysmem-prep packet trio as the primary no-pixel root cause. Next bounded unit should stop isolated
packet guessing and capture/diff a real Mesa fd6 sysmem single-triangle command stream against H3; if that capture is
not immediately available, the remaining concrete sysmem-prep gap to test is exact window-offset/order state around
`RB_WINDOW_OFFSET`, `RB_RESOLVE_WINDOW_OFFSET`, `SP_WINDOW_OFFSET`, and `TPL1_WINDOW_OFFSET`.

V3261/V3262 then tested that remaining concrete window-offset/order gap, but the first live artifact did not produce
a valid GPU result: adding Mesa's zero `RB_WINDOW_OFFSET`, `RB_RESOLVE_WINDOW_OFFSET`, `SP_WINDOW_OFFSET`, and
`TPL1_WINDOW_OFFSET` packets raised the expected H3 stream to `260` dwords while the shared command-buffer guard was
still `GPU_G4_CMD_MAX_DWORDS=256`. The flashed image booted and passed health, but the live H3 run failed before
submit (`cmd_write_rc=-1`, `pm4_dwords=0`, `submit_rc=-1`), so V3262 only proved a host-side PM4 assembly guard bug,
not a new no-pixel datapoint. V3263 corrected that guard to `320` dwords and rebuilt from the V3259 ramdisk baseline
as `0.11.58 (v3263-gpu-h3-window-offset-cmdroom-probe)` with SHA256
`f38f2fdb7cb71cabc6603e606bcd28965715e128f8211bf767f47f851da7f3d8`, flashed through `native_init_flash.py`, and
passed post-flash health after one host-side serial bridge framing retry (`selftest pass=12 warn=1 fail=0`). V3264 live
telemetry confirmed the corrected stream assembled and submitted (`cmd_write_rc=0`, `pm4_dwords=260`,
`state_reg_writes=98`, `submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`), with no focused KGSL/GPU/GMU/A640 fault,
hang, snapshot, or timeout signature, but two H3 runs still left readback unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the zero window-offset
sysmem-prep packet group and command-buffer room as the primary no-pixel root cause. The next bounded unit should be a
real Mesa fd6 sysmem single-triangle command-stream capture/diff against H3, with special attention to any remaining
per-MRT render-component/write-enable register names that are not equivalent to the already-programmed
`RB_PS_OUTPUT_MASK`, `SP_PS_OUTPUT_MASK`, and `RB_MRT0_CONTROL.COMPONENT_ENABLE` path.

V3265/V3266 then tested the next concrete draw-state bootstrap packet because a real Mesa `.rd` capture was not
immediately available on the host (`meson`/Mesa driver build absent; existing local Mesa build contains freedreno tools
only, not the Gallium driver). V3265 added Mesa restore-path `CP_SET_MODE(0)` (`opcode=0x63`, value `0`) after the
pre-draw CCU/cache invalidation and before the H3 shader/state/draw packets, built from the V3263 baseline as
`0.11.59 (v3265-gpu-h3-cp-set-mode-probe)` with SHA256
`cb8c579aa4cc694de363d7e2334c202f255431bba9e4f1a385fe0f2b3094ba84`, flashed through `native_init_flash.py`, and
passed post-flash health after a managed bridge restart cleared serial fragment noise (`selftest pass=12 warn=1
fail=0`). V3266 live telemetry confirmed `cp_set_mode=0x63`, `cp_set_mode_value=0x0`, `pm4_dwords=262`,
`state_reg_writes=98`, `submit_rc=0`, `wait_rc=0`, and `retired_timestamp=1`; two H3 runs still left readback unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), with no focused
KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature and post-probe health still clean. This removes missing
restore-path `CP_SET_MODE(0)` as the primary no-pixel root cause. Next bounded unit should either build a host-only
freedreno Gallium+drm-shim reference environment to generate an `.rd` for cffdump diff, or, if that remains unavailable,
continue source-grounded diff around remaining A6xx program/RB state that is present in Mesa but absent from H3.

V3267 source-audited the new `RB_CCU_CNTL` magic hypothesis against local Mesa fd6 code before changing H3. Mesa's A640
entry uses `a6xx_base + a6xx_gen2` with `num_ccu=2`; `a6xx_base` gives sysmem depth/color cache sizes of 64KiB per CCU;
`fd6_calc_gmem_cache_offsets()` computes sysmem `depth_ccu_offset=0` and `color_ccu_offset=2 * 64KiB = 0x20000`; and the
A6xx XML encodes `RB_CCU_CNTL.COLOR_OFFSET` as `(offset >> 12) << 23`, yielding exactly `0x10000000`. That matches current
H3 (`GPU_H3_RB_CCU_CNTL=0x10000000`, color offset `0x20000`, depth offset `0`), so no boot delta was built for this
candidate. The same audit confirmed V3255/V3256 already emit the Mesa sysmem `set_bin_size()` equivalents
(`GRAS_SC_BIN_CNTL` and `RB_CNTL`), and that the suggested `RB_RENDER_COMPONENTS`/`SP_FS_RENDER_COMPONENTS` names are not
A6xx register names; the current A6xx write-enable path is `RB_PS_OUTPUT_MASK`, `SP_PS_OUTPUT_MASK`, and
`RB_MRT0_CONTROL.COMPONENT_ENABLE` for MRT0. This removes the CCU-magic replacement, bin-control absence, and A4/A5-style
component-register hypotheses as actionable H3 fixes. Next bounded unit should be the real Mesa fd6 sysmem
single-triangle `.rd`/cffdump diff; if host Mesa Gallium+drm-shim setup remains unavailable, continue source-grounded diff
around remaining A6xx program/RB/static non-context state.

V3268/V3269 used the now-working local freedreno `cffdump` path plus Mesa A6xx rasterizer source to test a concrete
draw-state delta: Mesa emits `VPC_RAST_CNTL=POLYMODE6_TRIANGLES` (`0x3`) and `PC_DGEN_RAST_CNTL=POLYMODE6_TRIANGLES`
(`0x3`), while H3 previously only emitted `VPC_RAST_STREAM_CNTL`. V3268 added both raster polygon-mode registers,
built as `0.11.60 (v3268-gpu-h3-raster-mode-probe)` with SHA256
`8fc356e60545ad36e412367d40b4da6f6f9a9766c6251369684f187c49323240`, flashed through `native_init_flash.py`, and
passed post-flash health after one managed bridge restart cleared serial fragment noise (`selftest pass=12 warn=1
fail=0`). V3269 live telemetry confirmed `vpc_rast_cntl=0x3`, `pc_dgen_rast_cntl=0x3`, `pm4_dwords=266`, and
`state_reg_writes=100`; two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
warm `total_elapsed_ms=12`), with no focused KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature and
post-probe health still clean. Readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`), so H4 is still not reached. This removes missing A6xx polygon raster-mode state as the
primary no-pixel root cause. Next bounded unit should keep using a real Mesa command-stream/source diff and avoid
re-testing the ruled-out CCU/bin/component/CP_SET_MODE/window-offset/visibility/raster-mode hypotheses.

V3270/V3271 source-audited the round-4 HLSQ/output hypothesis before changing H3. The old `HLSQ_CONTROL_*` /
`HLSQ_*_CNTL` register block is not present in the local A6xx XML/fd6 program path being mirrored here; A6xx shader
payload binding stays through the existing `CP_LOAD_STATE6` preload packets, so the live unit did not blindly write
legacy HLSQ offsets. The source delta instead added the fd6/A640-confirmed program/output defaults that were missing
from H3: `SP_VS_CONST_CONFIG=0x100`, `SP_PS_CONST_CONFIG=0x100`, and `SP_PS_OUTPUT_CNTL=0xfcfcfc00` for invalid
depth/sampmask/stencil regids in a color-only FS. V3270 built `0.11.61
(v3270-gpu-h3-sp-const-fs-output-probe)` with SHA256
`dec8c8f956f75e0d035ec21919e5b2fd2d0fb16a81f191eb1b033d59a0138325`, flashed through
`native_init_flash.py`, and passed post-flash health after one managed bridge restart cleared serial fragment noise
(`selftest pass=12 warn=1 fail=0`). V3271 live telemetry confirmed `sp_vs_const_config=0x100`,
`sp_ps_const_config=0x100`, `sp_ps_output_cntl=0xfcfcfc00`, `pm4_dwords=270`, and `state_reg_writes=100`; two H3 runs
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`), with no
focused KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature and post-probe health still clean. Readback
remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still
not reached. This removes missing SP const enable and missing invalid FS depth/sampmask/stencil output regids as the
primary no-pixel root cause. Next bounded unit should fall back to the real fd6 sysmem single-triangle `.rd`/cffdump
register-packet diff against H3 instead of continuing isolated downstream register sweeps.

V3272/V3273 then tested the actionable part of the follow-up "HLSQ front-end" claim. The legacy `HLSQ_CONTROL_*` /
`HLSQ_*_CNTL` names still are not an A6xx fd6 draw-state path in the local XML/source, but the real A6xx SP front-end
program-id/system-value group was missing: `SP_PS_INITIAL_TEX_LOAD_CNTL`, `SP_PS_WAVE_CNTL`, `SP_LB_PARAM_LIMIT`, and
`SP_REG_PROG_ID_0..2` (H3 already emitted `SP_REG_PROG_ID_3`). V3272 added the current constant-FS-compatible fd6
mapping: no varyings, `SP_PS_INITIAL_TEX_LOAD_CNTL=0x8`, `SP_PS_WAVE_CNTL=0x0`, `SP_LB_PARAM_LIMIT=0x7`, and invalid
`0xfc` regids for unused front-face/sample/IJ/coord system values (`SP_REG_PROG_ID_0..2=0xfcfcfcfc`,
`SP_REG_PROG_ID_3=0x0000fcfc`). It built `0.11.62 (v3272-gpu-h3-sp-frontend-prog-id-probe)` with SHA256
`6ff91c08ee0a866c251675780a23b94834aed44ccd26a3ead4f3e4e9022b0b96`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`). V3273 live telemetry confirmed
`sp_ps_initial_tex_load_cntl=0x8`, `sp_ps_wave_cntl=0x0`, `sp_lb_param_limit=0x7`,
`sp_reg_prog_id_0=0xfcfcfcfc`, `sp_reg_prog_id_1=0xfcfcfcfc`, `sp_reg_prog_id_2=0xfcfcfcfc`, `pm4_dwords=282`,
and `state_reg_writes=106`; two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still not reached. This
removes missing SP front-end/system-value invalid-reg state as the primary no-pixel root cause. Next bounded unit
should continue the real fd6 `.rd`/cffdump diff and focus on direct-sysmem-compatible remaining deltas, especially the
clip/guardband/SU group (`GRAS_CL_CNTL=0xc0`, `GRAS_CL_GUARDBAND_CLIP_ADJ=0x0007fdff`, `GRAS_SU_CNTL=0x814`) before
any broader GMEM/UBWC flag-buffer architecture change.

V3274/V3275 then tested that direct-sysmem-compatible clip/guardband/SU group and re-audited the repeated round-4 HLSQ
claim before live flash. The local A6xx XML/fd6 draw path still does not expose the legacy `HLSQ_CONTROL_*` /
`HLSQ_*_CNTL` block as a safe A6xx register-packet target; V3274 therefore did not guess HLSQ offsets, and instead made
the fd6-confirmed output routing explicit (`RB_PS_OUTPUT_CNTL=0`, `RB_PS_MRT_CNTL=1`, `SP_PS_OUTPUT_CNTL=0xfcfcfc00`,
`SP_PS_MRT_CNTL=1`) while adding `GRAS_CL_CNTL=0xc0`, `GRAS_CL_GUARDBAND_CLIP_ADJ=0x0007fdff`,
`GRAS_SU_CNTL=0x814`, `GRAS_SU_POINT_MINMAX=0xffc00001`, `GRAS_SU_POINT_SIZE=0x10`, and zero
`GRAS_SU_POLY_OFFSET_*` companions. V3274 built `0.11.63 (v3274-gpu-h3-clip-guardband-su-probe)` with SHA256
`b9f85b95fda81edd77f2bc121c940275c4122f5842ba929400c7f49b43bdb313`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`; one serial prompt-fragment selftest attempt was retried after
`version` re-synchronized the bridge). V3275 live telemetry confirmed `pm4_dwords=292`, `state_reg_writes=111`, the
new HLSQ audit/output routing telemetry, and the CL/SU values above; two H3 runs submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and post-probe selftest stayed clean.
Readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) with no
focused KGSL/GPU/GMU/A640 page-fault, hang, snapshot, or timeout signature, so H4 is still not reached. This removes the
clip/guardband/SU rasterizer-state gap and the rechecked legacy-HLSQ/output-routing gap as primary no-pixel causes. Next
bounded unit should stop isolated register sweeps and mine or capture a real fd6 sysmem single-triangle `.rd`/cffdump
diff against H3, admitting only direct-sysmem-compatible missing packet groups.

V3276/V3277 then used that diff direction for a larger, coherent cffdump-inspired varying/IJ linkage unit rather than a
single-register toggle. V3276 changed H3 so the VS writes clip-space position to regid `8` (`r2`), preserves a four-
component varying stream from regid `0`, and the FS uses verified cffdump `bary.f` instructions with MRT0 color output
from FS regid `2`. It also updated `SP_VS_OUTPUT_CNTL=2`, `SP_VS_OUTPUT_REG0=0x0f000f08`,
`SP_VS_VPC_DEST_REG0=0x400`, `VPC_VS_CNTL=0x00ff0408`, `VPC_PS_CNTL=0xff01ff04`, varying-aware
`SP_PS_INITIAL_TEX_LOAD_CNTL=0x7fc0`, `SP_PS_WAVE_CNTL=3`, `SP_REG_PROG_ID_1=0xfcfcfc00`,
`PC_MODE_CNTL=0x1f`, `PC_VS_CNTL=8`, and invalid VFD sideband regids. V3276 built `0.11.64
(v3276-gpu-h3-varying-ij-probe)` with SHA256
`1cfada71599befc2cd47c5ffb53f1eab4673d5200bbe92c77f8137ed0e86471e`, flashed through
`native_init_flash.py`, and passed post-flash health (`selftest pass=12 warn=1 fail=0`; one normal-input
post-flash selftest attempt lost the serial END marker and passed when rerun with slow input). V3277 live telemetry
confirmed `pm4_dwords=306`, `state_reg_writes=118`, `vfd_reg_writes=14`, `sp_vs_cntl0=0x80100180`,
`sp_ps_cntl0=0x81500100`, `vpc_vs_cntl=0xff0408`, `vpc_ps_cntl=0xff01ff04`, and the cffdump bary shader markers.
Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm
`total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) with no focused KGSL/GPU/GMU/A640
fault, hang, snapshot, timeout, CP opcode, or hardware-error signature, so H4 is still not reached. This removes the
cffdump varying/IJ/VPC/VFD linkage group as the primary no-pixel cause. Next bounded unit should stop adding isolated
HLSQ/output/raster guesses and compare a real fd6 sysmem single-triangle `.rd`/cffdump packet stream against H3, then
admit only direct-sysmem-compatible missing packet groups.

V3278/V3279 then tested the strongest direct-sysmem cffdump color-target mismatch found in the local `.rd` diff:
the reference A640 sysmem triangle uses `SP_PS_MRT[0].REG=0x00000030` / RGBA8 UNORM for MRT0, while H3 still used
`FMT6_32_FLOAT` (`0x4a`). V3278 changed H3 MRT0 to `FMT6_8_8_8_8_UNORM` (`0x30`) while keeping the V3276 varying/IJ
pipeline intact, added telemetry for `color_format_source`, `sp_ps_mrt_reg0`, `rb_mrt0_buf_info`, and
`offscreen=rgba8-linear-128x128`, and explicitly kept the local A6xx/H3 HLSQ audit: the local XML/generated headers
and cffdump path do not expose a legacy `HLSQ_CONTROL_*` program block to write safely. V3278 built `0.11.65
(v3278-gpu-h3-rgba8-mrt-probe)` with SHA256
`c51ac3a3e10114d605fd5ffb4d0a27b6c6a5a2e4259ab9282389f2f5aa5f8e71`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`). V3279 live telemetry confirmed
`sp_ps_mrt_reg0=0x30`, `rb_mrt0_buf_info=0x30`, `color_format=0x30`, `pm4_dwords=306`, `state_reg_writes=118`, and
`vfd_reg_writes=14`. Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) with no focused KGSL/GPU/GMU/A640
fault, hang, snapshot, timeout, CP opcode, page-fault, or hardware-error signature; dmesg only showed expected first-use
`a640_zap` load/reset plus an unrelated modem firmware timeout. This removes the cffdump float-vs-RGBA8 MRT mismatch
as the primary no-pixel cause. Next bounded unit should use the real fd6 sysmem single-triangle `.rd`/cffdump packet
diff against current H3 rather than isolated HLSQ/output/raster guesses, and admit only direct-sysmem-compatible missing
packet groups.

V3280/V3281 continued that `.rd`/cffdump direction with the remaining coherent color-target group from local A640
cffdump draw[2], rather than writing speculative legacy `HLSQ_CONTROL_*` registers. V3280 kept the V3278 direct-render,
sysmem, varying/IJ, and RGBA8 baseline but changed the MRT0 target to the cffdump flag-MRT group:
`RB_RENDER_CNTL=0x10010`, `RB_MRT0_BUF_INFO=0x330`, `RB_COLOR_FLAG_BUFFER[0].PITCH=0x4001`, plus a bounded 4 KiB
color-flag BO and telemetry for flag-buffer readback. The source unit built `0.11.66
(v3280-gpu-h3-flag-mrt-probe)` with SHA256
`e295699879f3bb30bff85cfebaeb46b9c4ffd3909d0289bd882e3b2a9decfc19`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`; one verbose selftest attempt lost the serial END marker
after partial output, then a short selftest rerun passed). V3281 live telemetry confirmed `rb_render_cntl=0x10010`,
`rb_mrt0_buf_info=0x330`, `color_flag_buffer_pitch=0x4001`, `pm4_dwords=311`, `state_reg_writes=121`, and
`vfd_reg_writes=14`. Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), and the new flag buffer also
stayed unchanged (`color_flag_changed_count=0`, `color_flag0=0x0`) with no focused KGSL/GPU/GMU/A640 fault, hang,
snapshot, timeout, opcode, SMMU/IOMMU, or page-fault signature. This removes the flag-MRT color-target mismatch as
the primary no-pixel cause. Next bounded unit should continue the real fd6 sysmem single-triangle `.rd`/cffdump diff
against current H3 and admit only direct-sysmem-compatible packet groups; do not return to isolated HLSQ/output/raster
guesses unless the diff proves that packet group is actually missing.

V3282/V3283 then tested the first A640 device-DB init-magic candidate from the operator-staged
`/tmp/a90-mesa-gpu-src/a640_magic_regs.txt`, adding only `RB_DBG_ECO_CNTL=0x04100000` at register `0x8e04` before
H3 shader and draw state while preserving the V3280 flag-MRT target group. The source unit built `0.11.67
(v3282-gpu-h3-rb-dbg-eco-probe)` with SHA256
`f2afd2eda2b8632fff582e79c3defe5b9520ecb63d36e0498f3fced945fa9879`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`; one immediate verbose selftest attempt lost framing after
prompt noise, then slow-mode `version`/`selftest` passed). V3283 live telemetry confirmed
`a640_magic_mode=rb-dbg-eco-only`, `rb_dbg_eco_cntl_reg=0x8e04`, `rb_dbg_eco_cntl=0x4100000`,
`a640_init_magic_reg_writes=1`, `pm4_dwords=313`, `state_reg_writes=121`, and `vfd_reg_writes=14`. Two H3 runs
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and
post-probe selftest stayed clean. Readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`), and the color-flag buffer also stayed unchanged (`color_flag_changed_count=0`,
`color_flag0=0x0`) with no focused KGSL/GPU/Adreno/A6xx/A640 fault, hang, snapshot, timeout, opcode, SMMU/IOMMU, or
page-fault signature in the recent dmesg tail. This removes `RB_DBG_ECO_CNTL` alone as the primary no-pixel cause. Next
bounded unit should follow the operator probe order by adding the rest of the non-zero A640 device-DB magic block
(`SP_CHICKEN_BITS`, `TPL1_DBG_ECO_CNTL`, `VPC_DBG_ECO_CNTL`, `RB_RBP_CNTL`, `PC_MODE_CNTL`, `PC_POWER_CNTL`,
`VFD_POWER_CNTL`, and `UCHE_UNKNOWN_0E12`) while keeping `RB_CCU_CNTL` separate.

V3284/V3285 followed that probe order and added the full non-zero A640/a6xx_gen2 device-DB magic block before H3 shader
and draw state: `RB_DBG_ECO_CNTL=0x04100000`, `SP_CHICKEN_BITS=0x420`, `TPL1_DBG_ECO_CNTL=0x8000`,
`VPC_DBG_ECO_CNTL=0x02000000`, `RB_RBP_CNTL=1`, `PC_MODE_CNTL=0x1f`, `PC_POWER_CNTL=1`, `VFD_POWER_CNTL=1`, and
`UCHE_UNKNOWN_0E12=1`. Because the block raises the expected H3 PM4 size to `329` dwords, V3284 also raised the shared
GPU command-buffer guard from `320` to `384` dwords. The source unit built `0.11.68
(v3284-gpu-h3-a640-magic-block-probe)` with SHA256
`7eacd6670856beaeea681d1df6deb3169bcee68fe730c8dcb050b6fdc28b6572`, flashed through `native_init_flash.py`, and
passed flash-helper version/status plus post-flash health (`selftest pass=12 warn=1 fail=0`; one immediate standalone
selftest attempt lost serial framing after truncated input, then slow-mode `version`/`selftest` passed). V3285 live
telemetry confirmed `a640_magic_mode=nonzero-block`, `a640_init_magic_reg_writes=9`, `pm4_dwords=329`,
`state_reg_writes=121`, and `vfd_reg_writes=14`. Two H3 runs submitted and retired cleanly (`submit_rc=0`,
`wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained
unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), and the color-flag buffer
also stayed unchanged (`color_flag_changed_count=0`, `color_flag0=0x0`). Focused dmesg showed no GPU fault, hang,
snapshot, opcode, SMMU/IOMMU, or page-fault signature; only an unrelated modem firmware timeout and expected first-use
`a640_zap` load/reset lines matched the filter. This removes the A640 magic-reg block as the primary no-pixel cause.
Next bounded unit should stop isolated magic/register guesses and use the definitive packet-level path: capture or
assemble a real Mesa/freedreno A640 sysmem single-triangle `.rd`/cffdump stream and diff it against current H3,
admitting only remaining direct-sysmem-compatible packet groups.

V3286 converted that packet-level direction into a host-only cffdump/current-H3 diff using the local A640 freedreno
trace at `/tmp/a90-h3-cffdump/triangle_list.rd` (SHA256
`2fe5c6781058bb698e373bef3d2a9cffe4f04503d9fe3c9f81f2938cdb053011`) and decoded
`triangle_summary.txt`. No boot image was built or flashed. The diff confirms the already-tested/closed H3 core state
now matches the reference draw for `RB_RENDER_CNTL`, `RB_MRT[0].CONTROL`, `RB_MRT[0].BUF_INFO`,
`SP_PS_OUTPUT_CNTL`, `SP_PS_MRT[0].REG`, `VPC_VS_CNTL`, `VPC_PS_CNTL`, SP/RB output masks, raster state, and most
program routing. It also separates unsafe/contextual differences from candidates: the trace draw is a GMEM pass with a
later resolve, so `RB_CCU_CNTL`, `GRAS_SC_BIN_CNTL`, `RB_CNTL`, target-size pitches/scissors/viewports, and addresses
are not direct H3 copy targets. The top remaining deltas are now: (1) the coherent VFD/VS input contract
(`VFD_CNTL_0=0x303`, 36-byte stride, three fetch/decode streams, vertex-id in `r2.y`) versus current H3's single
2-float fetch (`VFD_CNTL_0=0x101`, 8-byte stride); (2) the smaller direct-sysmem-compatible blend/output group
(`SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, `RB_MRT[0].BLEND_CONTROL=0x08040804`) versus current zeros; and
(3) `SP_VS_CONST_CONFIG=0x101`, which is coupled to the reference VS constants and should not be copied alone. Next
bounded unit should prefer a coherent reference-contract VFD/VS replay, or, if a smaller live probe is desired first,
test only the blend/output-state group together under the existing H3 timeout/readback guards.

V3287 then implemented the top V3286 packet-diff candidate as a source/build unit while preserving the already-tested
V3284/V3285 A640 non-zero init-magic block. H3 now uses the cffdump-shaped VFD/VS input contract:
`VFD_CNTL_0=0x303`, `VFD_CNTL_1=0xfcfcfc09`, three fetch/decode streams, 36-byte vertex stride, and vertex payload
`r0.xyzw` varying color + `r1.xyzw` clip-space position + `r2.x` integer sideband. The VS was changed from the older
constant-built position path to a constant-free `r1.xyzw -> r2.xyzw` pass-through while preserving `r0` for the existing
cffdump barycentric FS. The source unit built `0.11.69 (v3287-gpu-h3-vfd-vs-contract-probe)` with SHA256
`560538eb253daa013971a2492575f80797082b3359d51e159c3a76e990aa9255`; no device flash or live readback was run in this
build unit. Focused source tests and shader/cffdump audits passed. Next live unit, if selected, should flash V3287
through `native_init_flash.py` under the usual rollback gates and check whether `readback_changed_count` or the
color-flag buffer changes before moving to the smaller blend/output-state group.

V3288 flashed that V3287 candidate through `native_init_flash.py` after reconfirming the rollback images and TWRP
recovery. Flash-helper verification matched local, remote, and boot readback-prefix SHA
`560538eb253daa013971a2492575f80797082b3359d51e159c3a76e990aa9255`; resident came back as `0.11.69
(v3287-gpu-h3-vfd-vs-contract-probe)`, and post-flash/post-probe selftest stayed `pass=12 warn=1 fail=0`. Two H3
draw-envelope runs confirmed the VFD/VS contract was live (`VFD_CNTL_0=0x303`, `VFD_CNTL_1=0xfcfcfc09`, fetch instrs
`0xc8200000/0xc8200200/0x44c00400`, dest cntls `0xf/0x4f/0x81`, stride `36`, `pm4_dwords=335`, `vfd_reg_writes=20`),
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=11`), but
readback and the color-flag buffer remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`, `color_flag_changed_count=0`, `color_flag0=0x0`). Focused dmesg showed no GPU fault,
hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature; only the unrelated modem firmware wait timeout and expected
`a640_zap` first-use lines matched. This removes the VFD/VS input-contract mismatch as the primary no-pixel cause. Next
bounded live unit should test the smaller direct-sysmem-compatible blend/output group from V3286:
`SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`.

V3289 implemented that direct-sysmem-compatible blend/output group as a source/build unit on top of the V3288
live-tested VFD/VS contract. H3 now emits `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and
`RB_MRT[0].BLEND_CONTROL=0x08040804`, while PM4 size and register counts stay unchanged (`pm4_dwords=335`,
`state_reg_writes=121`, `vfd_reg_writes=20`). The source unit built `0.11.70
(v3289-gpu-h3-blend-output-probe)` with SHA256
`10e43f8fc8c751774d830b797b783f3a058f10efaeeccab5d0dd57f806e6f34d`; no device flash or live readback was run in this
build unit. Focused source tests, shader-byte audit, cffdump current-H3 model tests, and the boot build passed. Next
live unit should flash V3289 through `native_init_flash.py` under the usual rollback gates and check whether this
blend/output group changes `readback_changed_count` or the color-flag buffer.

V3290 flashed the V3289 artifact through `native_init_flash.py` after reconfirming the rollback images and TWRP
recovery. Flash-helper verification matched local, remote, and boot readback-prefix SHA
`10e43f8fc8c751774d830b797b783f3a058f10efaeeccab5d0dd57f806e6f34d`; resident came back as `0.11.70
(v3289-gpu-h3-blend-output-probe)`, and post-flash/post-probe health stayed clean (`selftest pass=12 warn=1 fail=0`;
one immediate selftest attempt lost serial framing after truncated input, then slow-mode selftest passed). Two H3
draw-envelope runs submitted and retired cleanly and, for the first time, changed sysmem readback and the color-flag
buffer: run 1 reported `readback_changed_count=672`, `readback_first_changed_index=9216`,
`readback_first_changed_value=0xfb9802e6`, `color_flag_changed_count=32`, `color_flag_first_changed_index=256`,
`color_flag_first_changed_value=0x1010101`, `total_elapsed_ms=30`; warm run 2 repeated the same changed counts and
first-changed values with `total_elapsed_ms=12`. `readback0` and `readback_center` remained the clear value
`0x20202020`, so this is H4 first-pixel/readback proof rather than H5 visible/centered presentation. Focused dmesg
showed no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature; only the unrelated WLAN firmware wait
timeout matched the filter. This confirms the missing load-bearing group was the blend/output state, not the already
ruled-out A640 magic block or VFD/VS input contract alone. Next bounded unit is H5: present or blit the proven offscreen
triangle result to `/dev/dri/card0`, or first inspect/reposition the changed region if a centered display proof is
required.

V3291 implemented the first H5 source/build unit on top of that H4 proof. The new `gpu h5-triangle-kms-probe` /
`gpu triangle-kms-probe` command reuses the V3290-proven H3 draw/readback path, asks the KGSL child to return a bounded
`128x128` color-buffer snapshot before cleanup, keeps KMS ownership in the parent init process, scales the raw H3
readback into the existing `/dev/dri/card0` dumb framebuffer, and presents it with the existing `SETCRTC` path. This is
intentionally a raw tile-order visualization because the H3 target is still `RGBA8 tile6_3`; zero-copy scanout,
scaled-plane presentation, proprietary blob, full Mesa compiler port, and power writes are not attempted. The source
unit built `0.11.71 (v3291-gpu-h5-triangle-kms-probe)` with SHA256
`eea6c10b184ea19ce7c391899dae26c4bbf8b8ed4ac828409355b1d789a67f95`; no device flash or live KMS presentation was run
in this build unit. Focused V3291 source tests, existing H3 source regression tests, `py_compile`, `git diff --check`,
and the boot build passed. One legacy V3204 G5 source test was inspected separately and is stale against the current
shared G4 event helper count, so it was not used as a V3291 pass criterion. Next live unit should flash V3291 through
`native_init_flash.py` under the usual rollback gates and run
`gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode`, followed by post-probe selftest and focused GPU
dmesg filtering. H5 should only be claimed if the command reports `gpu.h5.kms.result=h3-readback-kms-presented` and the
panel visibly presents the H3 readback proof surface.

V3292 flashed that V3291 artifact through `native_init_flash.py` after reconfirming the rollback images and TWRP
recovery. Flash-helper verification matched local, remote, and boot readback-prefix SHA
`eea6c10b184ea19ce7c391899dae26c4bbf8b8ed4ac828409355b1d789a67f95`; resident came back as `0.11.71
(v3291-gpu-h5-triangle-kms-probe)`, and health stayed clean (`selftest pass=12 warn=1 fail=0`; one immediate standalone
selftest attempt lost serial framing due `AT` fragment noise, then `version` and slow-mode selftest passed). The live
H5 command completed in `53ms` with `gpu.h5.kms.result=h3-readback-kms-presented`: the H3 child returned the full
`66368`-byte payload, H3 again reported `readback_changed_count=672`, `readback_first_changed_index=9216`,
`readback_first_changed_value=0xfb9802e6`, and `color_flag_changed_count=32`, then the parent KMS path reported
`begin_frame_rc=0`, `fb_width=1080`, `fb_height=2400`, `fb_stride=4352`, `blit_rc=0`,
`blit_rect=28,176,1024,1024`, `blit_scale=8`, `present_rc=0`, and
`gpu-h5-triangle-kms: presented framebuffer 1080x2400 on crtc=133`. Post-probe selftest stayed clean, and focused dmesg
showed no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature; only expected `a640_zap` load/reset
lines matched. This device-proves the H5 KMS presentation path by serial telemetry. The only remaining H5 quality
checkpoint is human visual confirmation of the panel, because this run has no camera/display capture and the current
surface is a raw `RGBA8 tile6_3` readback visualization. If the operator requires a literal centered triangle rather
than the raw proof surface, the next bounded unit should add tile/format conversion or render into a KMS-friendly linear
presentation buffer before moving to after-triangle backlog.

V3293/V3294 implemented and live-tested that literal-presentation direction by adding a bounded A6xx A2D copy from the
V3290-proven `RGBA8 tile6_3` + flag render target into a separate linear RGBA8 snapshot before KMS presentation. The
source unit built `0.11.72 (v3293-gpu-h5-linear-triangle-kms-probe)` with SHA256
`59b7973d99a7d5a44384d3390ad261231f9fab1b16ee21fce48b9f0537e89e70`, raised the shared GPU command-buffer guard to
`512` dwords for the added A2D PM4 stage, and changed H5 telemetry to
`scope=first-triangle-h5-a2d-linearized-h3-readback-to-kms-probe` with raw tile-order visualization disabled. V3294
flashed that exact artifact through `native_init_flash.py` after reconfirming rollback images/TWRP; resident came back
as `0.11.72`, post-flash and post-probe selftest stayed `pass=12 warn=1 fail=0` (one busy/framing hiccup was recovered
by restarting the managed bridge), and the live command completed in `58ms` with
`gpu.h5.kms.result=h3-linear-readback-kms-presented`. H3 still reported the V3290 proof counts
(`readback_changed_count=672`, `readback_first_changed_index=9216`, `color_flag_changed_count=32`), the linear stage
reported `h3_linear_blit_attempted=1`, `h3_linear_readback0=0x0`, and
`h3_linear_readback_center=0xff00b900`, and KMS presented a `1024x1024` scaled region on the `1080x2400` framebuffer
with `present_rc=0`. Focused dmesg showed no GPU fault/hang/snapshot/opcode/SMMU/IOMMU/page-fault signature; only
expected `a640_zap` load/reset lines matched. Caveat: `h3_linear_readback_changed_count=16384` is inflated because the
linear destination was initialized to the old `0x20202020` sentinel while A2D resolves untouched/clear areas to
`0x00000000`; this proves A2D linearization + KMS presentation, but the next bounded unit should zero-clear the linear
buffer and add `linear_nonzero_count`, first-nonzero value, exterior-corner zero samples, and interior sample telemetry
before claiming a strict literal triangle proof and moving to the after-triangle backlog.

V3295/V3296 then removed that caveat and **closed the H0-H5 first-triangle ladder**. V3295 changed the linear
destination to zero-clear and strengthened the H5 gate to require true non-zero pixels, a non-zero center sample, and
zero exterior corner samples before KMS presentation. The source build produced `0.11.73
(v3295-gpu-h5-strict-triangle-kms-probe)` with SHA256
`f20b4ff3ab76fd0c8d854ede72f13079cf0f90fa248dad059768647fa8a7e4ae`. V3296 flashed that artifact through
`native_init_flash.py` after reconfirming rollback images/TWRP; resident came back as `0.11.73`, post-flash and
post-probe selftest stayed `pass=12 warn=1 fail=0`, and the clean rerun of
`gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode` completed in `55ms` with
`gpu.h5.kms.result=h3-linear-readback-kms-presented`. Strict proof telemetry passed:
`h3_linear_readback_nonzero_count=2016`, `h3_linear_readback_first_nonzero_index=8256`,
`h3_linear_readback_first_nonzero_value=0xff00b900`, `h3_linear_readback_center=0xff00b900`,
`h3_linear_readback0=0x0`, `h3_linear_readback_corner_tr=0x0`, `h3_linear_readback_corner_bl=0x0`,
`h3_linear_readback_corner_br=0x0`, `h3_linear_center_nonzero=1`, `h3_linear_exterior_corners_zero=1`, and
`strict_linear_triangle_sample_proof=1`; KMS reported `present_rc=0` for a `1024x1024` scaled region on the
`1080x2400` framebuffer. Focused dmesg showed no GPU fault/hang/snapshot/opcode/SMMU/IOMMU/page-fault signature
(only expected `a640_zap` load/reset and an unrelated modem firmware wait timeout). This is the first real GPU
triangle proof: vertex buffer + VS + rasterizer + FS + sysmem color/flag write + A2D linearization + KMS presentation,
all within the freedreno/KGSL-direct recoverable envelope. Next work should move to the after-triangle backlog, starting
with a small visible compute/fragment-shader demo or extraction of the now-proven GPU path.

V3297/V3298 then closed the operator sensory H5 gate. V3297 kept the strict proof path but changed presentation from a
raw proof surface to a recognizable KMS screen: it finds the A2D-linearized nonzero triangle bbox, scales that mask into
a centered high-contrast solid triangle, stops autohud before present, and holds the framebuffer on screen. The source
build produced `0.11.74 (v3297-gpu-h5-visual-triangle-hold-probe)` with SHA256
`a0728c476f7fa6793d28fc930d7dcdf8c3eac99dc3db44e7044274c5431f4e80`. V3298 flashed that artifact through
`native_init_flash.py` after reconfirming rollback images/TWRP; resident came back as `0.11.74`, post-flash and
post-probe selftest stayed `pass=12 warn=1 fail=0`, and after `hide` cleared the auto menu the live command
`gpu h5-triangle-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode` completed in `30159ms` with
`gpu.h5.kms.result=h3-visual-triangle-kms-presented` and `gpu.h5.vis.result=triangle-presented-held`. Strict proof
telemetry still passed (`h3_linear_readback_nonzero_count=2016`, `h3_linear_readback_center=0xff00b900`,
`h3_linear_exterior_corners_zero=1`, `strict_linear_triangle_sample_proof=1`), the visible bbox was
`64,64,126,126`, and KMS presented a centered `945x945` visual triangle region at `67,727` on the `1080x2400`
framebuffer. The operator confirmed the triangle was visible on the panel during the hold. Focused dmesg again showed
no GPU fault/hang/snapshot/opcode/SMMU/IOMMU/page-fault signature. The first-triangle epic is now closed both by
telemetry and by human visual confirmation; the next rung is the after-triangle backlog.

**GPU roadmap — ORDERED CHAIN after the triangle (operator "full-steam" 2026-06-26; do NOT pre-build, pull each rung
only when reached, but the loop must flow rung→rung and NOT halt between them — re-charter the active-epic to the next
rung as each closes).** Honest ceiling acknowledged and accepted: native-init has NO OpenCL/Vulkan/CUDA (blob/Bionic
wall), so every kernel/shader is hand-assembled ir3 and this never becomes a general GPGPU server — the value is
*device-proven GPU capability + accelerating our own pipeline*, not third-party workloads.

- **① VISIBLE compute demo (DONE = C0→C3, V3303 eye-confirmed; e.g. Mandelbrot/particle → KMS).** Reuses the shader path minus the
  rasterizer; gives GPU compute a *screen consumer*. **Matrix/GPGPU math is absorbed here, NOT a standalone goal** —
  no module/library to load (OpenCL/BLAS = blob/Bionic wall; Mesa rusticl/turnip = full-stack port, unbounded), so any
  kernel is hand-assembled ir3; an abstract matmul with no consumer is the forbidden "capability with no consumer".
- **② GPU-ACCELERATED 2D = texturing + frame blit/scale (DONE + EYE-CONFIRMED, V3315).** Bring up the A6xx texture
  pipe (TPL1 sampler): render a textured fullscreen quad sampling an image, then use the GPU to scale/composite/blit
  frames — the demo player (Bad Apple/DOOM) blits via CPU `memcpy` today, so this makes the GPU a *real consumer of
  existing work* (frees the CPU, enables higher res/fps) and exercises the sampler path. This is the third real call
  site for the rule-of-three extraction and the natural motivator for zero-copy.
- **③ Modularization = EXTRACTION, not an epic.** Do not design a `a90_gpu` API upfront. With triangle + compute +
  accel-blit as three real consumers pulling on the same G0-G3 core (rule of three), *extract* the common KGSL
  submit/fence/buffer layer into an internal helper as a bounded refactor; formalize an API only after the call sites
  reveal its shape.
- **④ zero-copy KMS/dmabuf scanout** (G5 CPU-copy → direct GPU-buffer scanout; crux = A6xx tiling/UBWC ↔ display
  modifier) — efficiency win; do after ② makes CPU-copy the bottleneck. Closing ④ closes the GPU epic.

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
- **GPU EPIC CLOSED = ④ zero-copy KMS/dmabuf scanout (Z0→Z3) is DONE + EYE-CONFIRMED; NEXT = SoftAP server-endgame.**
  Four GPU rungs are CLOSED + EYE-CONFIRMED: first-triangle H0→H5 (GREEN RIGHT-TRIANGLE; `V3295/V3296`, `0.11.73`),
  COMPUTE demo C0→C3 (rainbow/grid pattern; `V3303`, `0.11.77`), GPU-accel 2D D0→D3 (held Bad Apple GPU-blit frame;
  `V3315`, `0.11.87`), and on-panel SYSTEM MONITOR M0→M3 (held GPU-drawn graphs; `V3321`, `selftest fail=0`), which
  DELIVERED the ③ rule-of-three extraction (shared KGSL submit/fence/buffer/texture/present helper). Per the operator
  decision (2026-06-27: "④ 먼저 닫고 SoftAP"), V3335 made the GPU-rendered buffer the full-panel scanout buffer directly
  (G5 CPU-copy → direct GPU-buffer scan-out) through the primary SETCRTC path. KMS present + GPU only, NO power writes
  (bright-line-trivially safe). **NEXT = pivot to the SoftAP server-endgame** (highest-ROI feature toward the
  headless-server-distro). Bluetooth / sensors / haptics remain
  reference-only until separately chartered (attended daytime quick-wins).
  **Z-ladder status (2026-06-27):** Z2 is closed: V3326 rendered the monitor graph directly into a DRM msm scanout GEM
  exported as PRIME/imported into KGSL, with `kms_copy_attempted=0`, `kms_present_attempted=0`, `changed_count=691200`,
  semantic exact match `64/64`, and post-probe `selftest fail=0`. Z3 overlay-plane scanout was intentionally abandoned
  after the overlay wall. V3327 fixed
  the imported render-target shape but hit non-master-fd `EACCES`; V3328 reused the KMS master fd and moved the failure
  to `EINVAL`; V3329 added atomic plane commit; V3330 switched the target to a KMS dumb scanout buffer; V3331 filtered
  for an idle overlay plane (`plane_id=90`, `selected_type=0`); V3332 added `zpos/alpha/rotation`; V3333 proved the
  selected overlay has no `IN_FORMATS` blob and is treated LINEAR-capable while lacking `pixel blend mode`; V3334 proved
  `DRM_MODE_ATOMIC_ALLOW_MODESET` does not change the result (`atomic_flags=0x400`, still `atomic_commit_rc=-22`).
  V3335 then rendered into a full-screen KMS dumb buffer imported into KGSL and presented that same framebuffer through
  primary SETCRTC with `kms_copy_attempted=0`, `present_rc=0`, `restore_rc=0`, semantic exact `64/64`, post-probe
  `selftest fail=0`, and operator eye-confirmation that the held graph was visible and remained on-panel.
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
