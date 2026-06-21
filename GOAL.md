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
> - **0.11.0 (MINOR) is RESERVED for video-epic close at DOOM completion** — i.e. the full demo ladder
>   (Bad Apple + Nyan + DOOM) device-proven. Do not roll MINOR before DOOM lands; DOOM continues on the 0.10.x line until then.
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
> - **NEXT UNIT: V3027 runtime-private WAD staging preflight** — host-only inspect the private WAD root and pin exact
>   size/hash/staging policy for a later bounded WAD-backed DOOM smoke. Keep WAD/IWAD bytes out of public, ramdisk,
>   and boot image.
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

## Stop conditions

- **ACTIVE EPIC (operator-chartered 2026-06-19) = Video PLAYBACK pipeline on the EXISTING KMS display**
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
  Do NOT start a third epic (Bluetooth/sensors/etc.) — reference-only until separately chartered.
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
- **KGSL `/dev/kgsl-3d0` open-block** is a human-gated investigation, NOT a loop unit (live
  open hangs). Leave it.
- **No doc / metadata / inventory cleanup as a track** (anti-churn trap).
- **Never reopen** external SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO paths for internal `wlan0`.
