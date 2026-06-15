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

### Active epic — Internal audio (ADSP/Q6) feasibility research

**Prior epics CLOSED:** WLAN events at V2312; USB gadget control **layer ①** at V2315; USB
**device identity** at V2316–V2321 (real serial redacted to `A90NATIVE001`; host-visible
descriptor `A90-LNX` / `A90 Linux ARM64` via fixed-length kernel **rodata** patches); **USB
named multi-LUN mass-storage identity** at V2322 (`0.9.286`, U-A single named LUN) and V2323
(`0.9.287`, U-B `lun.0`+`lun.1` → host SCSI models `A90-INTERNAL`/`A90-SD`, FAT labels
`A90INTERNAL`/`A90SD`). Rollback target `v2321` (`0.9.285`); `v2237`/`v48` remain deeper
fallbacks. USB U-C (real SD / internal read-only exposure) stays **DEFERRED**. ②adb-over-ffs and
③HID/BadUSB remain separate follow-on USB epics — **do not start them here.**

**Active epic: determine whether the internal speaker/headphone audio path can be driven under
native init, and — only if a safe path exists — produce sound.** This is a *research / feasibility*
epic: like the kernel-security recon phase, **"NON-VIABLE under native init" is an acceptable,
valuable outcome** if that is where the evidence lands. Do not force a result.

**Grounded starting facts (from the 2026-06-14 session research; re-verify, do not trust blindly):**
- **HW:** codec `wcd934x`/`wcd9360` on **SLIMbus** + **4× `wsa881x`** smart amps on **SoundWire**;
  *all* audio routes through the **ADSP (Q6 DSP)** — you cannot poke the speaker directly.
- **Two Linux audio architectures:** (a) **downstream techpack** (proprietary `msm-pcm-q6`/APRv2 +
  ACDB + Qualcomm audio HAL — what *this* device actually uses); (b) **mainline** `q6afe`/`q6asm`/
  `q6routing` + mainline `wcd934x`/`wsa881x` (postmarketOS). **(b) needs a mainline kernel we do
  NOT run → swapping the kernel is out of scope + brick-risky → (b) is REJECTED up front.**
- **Our stock 4.14 kernel (verified):** the ADSP **PIL/remoteproc node is present** in DTS
  (`qcom,firmware-name = "adsp"`, `sm8150.dtsi:1718`), but `sound/`, `techpack/audio`, the APR bus,
  and all q6 ASoC drivers are **stripped from the open-source drop**. We boot the **stock kernel
  image unchanged**, so its built-in/vendor audio drivers + ADSP firmware + ACDB are **ABI-matched**
  → the only realistic path is **(a): reuse stock vendor blobs**, not a rebuild.
- **The two real walls:** ① does native init ever **bring the ADSP up** (stock Android init does the
  PIL load; we do not)? ② **Qualcomm audio HAL + ACDB calibration**. Lighter hope to test:
  **tinyalsa + tinymix(`mixer_paths*.xml`) direct** on the ASoC card, *bypassing* the full HAL.
- **Out of scope inside this epic:** modem/**call** audio and the `q6voice` daemon (separate, harder,
  and touches the CP/modem boundary) — **speaker/headphone *playback only*.**

Staged units, one V-iteration each. **AUD-0 and AUD-1 are host-only.** **AUD-2 and beyond touch the
ADSP / device audio and (for route-delta) a stock-Android boot. Per the overnight operator
pre-authorization above, the loop MAY self-authorize these device steps and must NOT stop to ask for
human approval — proceed.** All such steps stay inside the boot-partition-only + recoverable envelope:
ADSP subsystem-restart and `tinymix`/PCM/`tinyplay` writes are reboot-recoverable, and a bad boot
auto-rolls-back to `v2321`. Forbidden-partition rules remain absolute. Keep audio writes to
observed/known-good routes and bounded amplitude (no blind smart-amp gain/boost poking).

- **AUD-0 — host-only inventory & decision basis.** From the stock AP/`vendor` image (extract
  host-side; treat as proprietary, keep under `workspace/private/`, never commit), enumerate: audio
  `.ko` modules, the **`adsp` firmware** image, **ACDB** `.acdb` files, `mixer_paths*.xml`,
  `audio_platform_info*.xml`, and the audio-HAL libs. Decide: are the audio drivers **built into the
  boot kernel image** we already flash, or separate vendor `.ko`? Map the exact bring-up chain.
  **Deliverable:** a feasibility report answering *"is a tinyalsa-direct (no full HAL) path plausible,
  or is the full Qualcomm HAL+binder stack mandatory?"* If mandatory → recommend **CLOSE as
  NON-VIABLE** (document, like the kernel-security recon close) and stop the epic.
- **AUD-1 — host-only ADSP/remoteproc path analysis.** Confirm the remoteproc/PIL node, the firmware
  search path, the minimal driver load order, and *how* (in principle) a PID-1 native init would
  trigger the ADSP load via sysfs `remoteproc` state. No device action. **Deliverable:** the precise,
  reviewable device-step plan that AUD-2 would run.
- **AUD-2 — DEVICE (overnight pre-authorized) — ADSP liveness probe.** [DONE — passed V2332/V2348,
  reconfirmed V2359.] Under native init, read `remoteproc` state, attempt the (recoverable) ADSP
  subsystem load, observe whether an ALSA card / `/dev/snd` materializes. Proceed within the
  recoverable envelope; no human-approval stop required.
- **AUD-3 — DEVICE (overnight pre-authorized) — speaker route + first tinyalsa playback.** Resolve the
  speaker route (route-delta capture from stock Android is the current method), then load it via
  `tinymix` and push a bounded-amplitude test PCM with `tinyplay`. First actual sound test. Proceed
  within the recoverable envelope; no human-approval stop required.

**Latest audio route-delta planning state (V2371):** V2362 selected Android route-delta
capture as the next speaker-route measurement and designed it host-only. The measurement should boot
normal Android, use Android framework `AudioTrack` playback through AudioFlinger/vendor HAL, capture
`tinymix -D 0 --all-values` before/during/after, then roll back to V2321 and diff `SEC_TDM_RX_0` /
`WSA_CDC_DMA_RX_0` / `RX INT7` / `COMP7` / `Spkr` controls offline. This is the clean path to learn
Android's actual speaker route without guessing native smart-amp writes. V2364 closed the checked
flash-helper gap by adding `native_init_flash.py --post-flash-target android-adb`, Android
boot-complete polling, optional Magisk root check, and `--expect-android-magic` while preserving the
default native-init serial verification path. V2365 added a host-only dry-run planner for the future
route-delta runner: it verifies the pinned Android boot candidates and V2345 `tinymix`, emits the
checked-helper Android flash/stage/snapshot/playback/rollback command plan, and confirms the archived
Android boot image must be sealed to a private `0600` copy before helper use. V2366 added
`A90AudioRouteStimulus.java` plus a private-output builder. V2368 staged a private Temurin JDK +
Android SDK toolchain and built the DEX at `workspace/private/builds/audio/v2366-android-route-stimulus/A90AudioRouteStimulus.dex` (SHA256 `95c27a152acee5c57d634e03436f72166999f5fd809d772f8f6414a3f9dc2b57`, mode `0600`);
V2365 dry-run with that DEX now reports `live_ready=True`. V2369 converted the planner into an
exact-gated live runner: it creates a run-local `0600` Android boot copy, boots Android through the
checked helper, stages only `tinymix` + the AudioTrack DEX, captures baseline/active/post snapshots,
starts the stimulus in the background so active `tinymix` reads occur during playback, then reboots
Android to recovery and flashes V2321 without incorrectly claiming a native-bridge origin. The
operator text `exact route-delta approval.` is **not** the exact gate and no live run was executed in
V2369. V2370 then closed a live-runner safety gap by adding explicit `--adb` and `--serial`
propagation through Android flash, staging, snapshot, recovery-reboot, and V2321 rollback commands
so a multi-device host cannot silently target the wrong ADB device. V2371 used the exact AUD-3D2
gate for the first live Android route-delta attempt: Android boot/staging/snapshots/cleanup/rollback
all completed and final V2321 selftest was `fail=0`, but the raw `app_process` AudioTrack stimulus
was killed with rc `137`, no AudioFlinger active track survived into the active snapshot, and parsed
`tinymix --all-values` showed `0` changed controls across baseline/active/post. V2372 adds
host-only logcat observability to the route-delta runner: future exact-gated live runs clear and
capture Android `main`/`system`/`crash`/`events` logs around the stimulus window so the rc `137`
kill can be classified before changing stimulus strategy. V2373 adds a host-only APK-style
AudioTrack stimulus source and private-output builder; the signed private APK builds and verifies.
V2374 integrates that private APK into the route-delta runner as `--stimulus-mode apk`, planning
`adb install -r`, Activity launch via `am start`, package/result probes, and uninstall cleanup while
preserving explicit ADB targeting and V2372 logcat capture. V2375 executed that preauthorized
APK-mode Android route-delta handoff and rolled back to V2321 with `selftest fail=0`; APK install
succeeded, but `am start` was redirected to PermissionController `REVIEW_PERMISSIONS`, no
`A90_AUDIO_STIMULUS_*` marker ran, AudioFlinger saw no package activity, and baseline/active/post
`tinymix --all-values` were byte-identical. Host `aapt dump badging` identified the concrete cause:
the APK manifest lacked explicit `uses-sdk`, so Android treated it as `targetSdkVersion < 4` and
added implied dangerous permissions. V2376 fixed the manifest with `minSdkVersion=23` and
`targetSdkVersion=31`, rebuilt the private APK (SHA256
`fef87886bd1fb5f3dd07b857bbe3c4c00f9046f797ba9c84d48b89dc1d2d13f3`, mode `0600`), verified
`apksigner`, confirmed `aapt dump badging` reports `sdkVersion:'23'` and `targetSdkVersion:'31'`
with no implied dangerous permissions, and the route-delta runner dry-run is again
`live_ready=True`. V2377 reran the same preauthorized Android route-delta handoff with that rebuilt
APK: the Activity launched directly (no `REVIEW_PERMISSIONS`), `A90_AUDIO_STIMULUS_BEGIN/END/FINISH`
markers appeared with `rc=0`, AudioFlinger observed a `USAGE_MEDIA` `AudioTrack` delivering 96000
frames at 48 kHz, the active device was speaker, and `tinymix --all-values` produced a concrete route
delta. The route-relevant active controls include `SLIMBUS_0_RX Audio Mixer MultiMedia1=On Off`,
`SLIM RX0 MUX=AIF1_PB`, `RX INT7_1 MIX1 INP0=RX0`, `COMP7 Switch=On`, `AIF4_VI Mixer SPKR_VI_1/2=On`,
`SpkrLeft COMP/BOOST/VISENSE=On`, and `SpkrLeft SWR DAC_Port Switch=On`; most route switches reset
after playback, while `Audio Stream 0 App Type Cfg=69941 15 48000 2 ...` persisted as stream config.
V2377 rolled back to V2321 with final `selftest fail=0`. Magisk-module stimulus delivery is not
part of the native-init runtime path, but keep it as the Android-side measurement fallback used in
earlier Wi-Fi-style handoffs: temporary helper packaging, boot-time Android stimulus hooks, or
vendor-log probes if a future Android delivery wall appears. Next frontier: host-only native playback recipe design from the
observed Android route, including exact control order, reset sequence, low-amplitude PCM plan, and
abort conditions before any native `tinymix set`/`tinyplay`. V2378 added that host-only route recipe
planner (`native_audio_speaker_route_recipe_v2378.py`): it verifies V2377 evidence, exact route
controls, and V2345 `tinymix`/`tinyplay` hashes, then emits a future-only plan with 13 observed
route-apply controls, reverse reset, card0/device0 `tinyplay`, `amplitude=0.02`, `duration_ms=1000`,
and exact future gate `AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply,
low-amplitude tinyplay, reverse reset, rollback to V2321`. V2379 implemented the exact-gated native speaker pilot runner as source/build/test only:
`native_audio_speaker_pilot_live_handoff_v2379.py` reuses the V2334 ADSP + `/dev/snd`
materialization path, stages pinned V2345 `tinymix`/`tinyplay`, generates a run-local
48 kHz stereo S16_LE 0.02-amplitude 1 s WAV, applies only the 13 V2377-observed route controls,
runs one bounded `tinyplay`, reverse-resets 12 controls, verifies reset against pre-apply `tinymix`,
and rolls back to V2321. Dry-run reports `v2379-native-speaker-pilot-runner-dry-run`, `ok=True`.
V2380 ran the exact-gated AUD-4 live pilot and the recoverable envelope held: V2334 flashed, ADSP/card and 61 `/dev/snd` nodes materialized, candidate selftest stayed `fail=0`, and rollback to V2321 ended with `rollback_selftest_fail0=True`. However V2380 is functionally invalid as a speaker proof: the runner selected tcpctl, which split space-containing `tinymix` control names, so all 13 route apply commands and all 12 reset commands reported `Invalid mixer control` on the device while the host step still returned rc 0. `tinyplay` then ran without the intended route and printed `Error playing sample` despite host-step ok. V2381 fixes the runner host-only: route apply/reset default to serial `cmdv1x`, tcpctl/remote `[exit N]` and `ERR exit=N` are hard failures, `Invalid mixer control` and `Error playing sample` are explicit failure markers, dry-run remains `ok=True`, and Magisk is recorded as Android-measurement fallback only (`aud4_uses_magisk=false`). V2382 retried the exact-gated AUD-4 live path and proved the transport fix: `cmdv1x` preserved the space-containing control name, no `Invalid mixer control` split-name failure occurred, and the runner hard-failed safely before playback. The new blocker was value encoding: `tinymix` rejected `SLIMBUS_0_RX Audio Mixer MultiMedia1` string values with `Error: only enum types can be set with strings` / `[exit 22]`, then rollback to V2321 ended with `rollback_selftest_fail0=True`. V2383 fixes that host-only by encoding `BOOL` route values numerically (`On`→`1`, `Off`→`0`) while preserving enum strings such as `AIF1_PB`/`RX0`; the speaker pilot dry-run now emits `SLIMBUS_0_RX Audio Mixer MultiMedia1 1 0`, remains `ok=True`, and still uses serial route transport. V2384 retried the exact-gated AUD-4 live path with numeric bool route values: all 13 route apply commands and all 12 reverse-reset commands returned `rc=0`, including the previous `SLIMBUS_0_RX Audio Mixer MultiMedia1 1 0` blocker. The run reached bounded `tinyplay`, but playback still printed `Error playing sample` with `[exit 0]`; V2381's classifier treated that as hard failure, reset the route, and rollback to V2321 ended with `rollback_selftest_fail0=True`. V2385 classifies this host-only from the pinned tinyalsa source: `tinyplay` returns process rc 0 even when `pcm_write()` fails, and the printed marker only proves `SNDRV_PCM_IOCTL_WRITEI_FRAMES` failed after successful open/params, not the exact errno. V2385 also preserves partial `speaker_pilot` evidence in future blocked live `result.json` files. V2386 adds a host-built diagnostic PCM write probe (`a90_pcm_write_probe_v2386`) linked against the pinned V2345 tinyalsa source; it reports `A90_PCM_PROBE_WRITE_ERROR` with `rc`, `errno`, `strerror`, and `pcm_get_error()` on `pcm_write()` failure, stages the private static AArch64 binary under `workspace/private/builds/audio/v2386-audio-pcm-write-probe/`, and updates the AUD-4 runner so future live playback uses this probe by default instead of stock `tinyplay`. V2387 attempted the exact-gated live retry with the V2386 probe default, but it did not reach route apply or playback: V2334 flashed and candidate health passed, then `candidate-adsp-boot-once` lost the `A90P1 END` marker after printing `audio.adsp_boot_once.retry=forbidden`; source shows that marker is printed only after the ADSP boot write is accepted, so the run is classified as `adsp-accepted-protocol-marker-lost`, not a PCM/probe result. The runner rolled back to V2321 and final `selftest fail=0`. V2388 fixes that host-only by running the ADSP one-shot step with `allow_error=True`, classifying output that contains `audio.adsp_boot_once.retry=forbidden` and no refusal/write-failure markers as accepted even if the protocol END marker is lost, and preserving the classification under `result.adsp_boot_once` before continuing to post-ADSP card/materialization polling. Focused tests cover the exact V2387 corrupted output tail and refusal markers. V2389 reran the exact-gated live path with V2388+V2386 and reached the intended diagnostic point: ADSP boot accepted with protocol OK, `/dev/snd` materialized, all 13 route apply commands returned OK, the V2386 probe opened card0/device0 and reported `A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384`, then failed before first data write at `pcm_prepare()` with `A90_PCM_PROBE_WRITE_ERROR chunk=0 rc=-1 errno=22 strerror="Invalid argument" pcm_error="cannot prepare channel: Invalid argument"`; all 12 reset commands and reset verification passed, rollback to V2321 ended with `selftest fail=0`. V2390 adds host-only read-only observability for that frontier: after any playback-attempt failure, the runner captures `/bin/toybox dmesg` as `dmesg-after-playback-failure-before-reset` before route reset and records it under `speaker_pilot.playback_failure_dmesg`. V2391 reran AUD-4 and reproduced the same V2389/V2386 `pcm_prepare()` failure (`errno=22`, `pcm_error="cannot prepare channel: Invalid argument"`) after ADSP OK, 13/13 route apply OK, and PCM open OK; route reset and rollback to V2321 again passed with `selftest fail=0`. The new dmesg step executed, but unbounded `/bin/toybox dmesg` over tcpctl truncated at early boot logs (`[output truncated]`, no `A90_PCM`/`pcm`/`q6asm`/`snd_pcm` lines), so it is not diagnostic. V2392 fixes that host-only by changing the failure capture to a bounded read-only tail, forced through serial `cmdv1x`: `/bin/busybox sh -c 'dmesg | tail -n 240'`, with dry-run metadata exposing `transport=serial-cmdv1x` and `bounded_tail_lines=240`. V2393 reran AUD-4 and the bounded tail captured the kernel-side cause of the repeated prepare `EINVAL`: AFE starts port `0x4000`, but `afe_get_cal_topology_id` reports cal types `8` and `9` not initialized for port `16384`, `send_afe_cal_type cal_block not found`, `q6asm_send_cal: cal_block is NULL`, app-type lookup falls back to default, then `adm_open` reaches the DSP and returns `ADSP_EFAILED`, producing `msm_pcm_playback_prepare: stream reg failed ret:-22` and `ASoC: platform prepare error: -22`; route reset and rollback to V2321 again passed with `selftest fail=0`. V2394 host-only analyzed the downstream Qualcomm audio calibration/App Type/ACDB loader boundary: V2393's prepare failure is now attributed to missing ACDB/App Type/topology programming (`send_afe_cal_type cal_block not found`, `q6asm_send_cal: cal_block is NULL`, `adm_open` `ADSP_EFAILED`), not route controls or PCM tuning. Vendor `libacdbloader.so` exports the expected ACDB init/send/topology APIs and opens `/dev/msm_audio_cal` with `/vendor/etc/acdbdata`/`audconf/OPEN`, while `audio.primary.msmnile.so` owns `platform_send_audio_calibration`, `platform_get_default_app_type*`, and app-type mixer programming. Magisk remains allowed only as the Android-side measurement/staging fallback, as in Wi-Fi: use it to observe the real vendor HAL/ACDB sequence under normal Android, not as a final native-init runtime dependency. V2395 host-only designed the ACDB/App Type bootstrap discriminator. Symbol-map evidence shows the Samsung HAL owns `adev_open_output_stream`/`start_output_stream`/`select_devices`/`enable_snd_device`, `platform_send_audio_calibration`, `platform_get_default_app_type_v2`, `set_stream_app_type_mixer_ctrl`, and `audio_extn_utils_send_app_type_cfg`; `libacdbloader.so` exports `acdb_loader_init_v4`, `acdb_loader_send_audio_cal_v4/v5`, common topology, gain-dependent calibration, and ACDB reload APIs, but no matching public headers/prototypes exist in the repo. Because these are 32-bit Android/Bionic shared libraries and the native-init helper model is static, direct `dlopen` from the native helper is not valid. V2396 implements the host-only Android/Magisk ACDB measurement planner (`native_audio_acdb_android_measurement_planner_v2396.py`): it reuses the checked Android handoff/V2321 rollback model, generates a private transient Magisk-style observer module under `workspace/private/builds/audio/v2396-acdb-magisk-measurement-module/`, stages it only as an Android-side `su -c` measurement helper, explicitly omits persistent `magisk --install-module`, and plans baseline/active/post ACDB/App Type snapshots plus full logcat around bounded Android `AudioTrack` speaker playback. Dry-run with module materialization reports `ok=True`, `future_live_ready=True`, `future_live_blockers=[]`, and `command_safety_ok=True`; module zip SHA256 is `4e14e9fe4b8995c5e5beb828d701350e933444282ebf68dc3285b96f07d81e2f`. V2397 extends that same script with an exact-gated `--run-live` path: it forces private module materialization, seals the Android boot image, flashes Android through the checked helper, stages the transient observer and APK, captures baseline/active/post ACDB/App Type state plus full logcat, pulls private artifacts, cleans up, reboots to recovery, and rolls back to V2321. Host-only validation proves bad approval returns `v2397-android-acdb-measurement-live-refused` before live action, and the materialized dry-run remains `future_live_ready=True`. V2398 is host-only and locks the Magisk strategy: Magisk remains an Android-side measurement capsule only, with V2397's transient `su -c` helper as the default; escalation to a temporary boot module or vendor wrapper requires a new exact gate and only if transient capture misses early ACDB/App Type edges. Next live frontier remains the exact-gated AUD-5A measurement using approval phrase `AUD-5A-android-acdb-magisk-measurement go: rollbackable Android AudioTrack speaker ACDB/AppType capture, transient Magisk-root observer only, no native speaker write, rollback to V2321`; after that capture, classify whether a private native ACDB bootstrap is bounded or whether speaker audio is HAL-dependent in native-init scope. V2399 adds the host-only post-live analyzer `analyze_audio_acdb_android_measurement_v2399.py`: it consumes private V2397 run artifacts recursively, classifies `bounded-native-acdb-candidate` / `hal-dependent-or-opaque` / `negative-no-calibration` / `capture-incomplete`, and exits non-zero if no V2397 run exists yet. V2400 wires that analyzer into the exact-gated V2397 live runner: after future capture success plus rollback proof, `result.json` gets `post_live_analysis`; parser errors are recorded without changing rollback evidence. V2401 attempted the exact-gated AUD-5A Android/Magisk ACDB live capture: Android boot-complete and Magisk `su` root were verified, but the first staging command failed with `error: closed`; runner rollback then failed because Android ADB was transiently unavailable and the fallback incorrectly tried the native serial path while Android was still resident. The device was manually recovered through the checked helper to V2321 with final `selftest fail=0`. Next required work is Android ADB post-handoff settle plus rollback retry hardening before rerunning AUD-5A. V2402 is host-only runner hardening for that failure: the AUD-5A runner now adds an Android post-handoff settle gate (`adb wait-for-device`, boot-complete re-check, Magisk-root re-check), retries Android `adb reboot recovery` when checked rollback times out while ADB still reports `device`, and probes native serial before using `--from-native`. Validation passed with py_compile, focused V2396 tests (13), full unittest suite (1087), dry-run `future_live_ready=True`, and `git diff --check`. Next meaningful unit is a fresh AUD-5A live rerun. V2403 reran the exact-gated AUD-5A live path after V2402: Android boot and the first two post-handoff settle steps passed, but the new Magisk-root settle command was malformed for `adb shell su -c` and failed with `/system/bin/sh: syntax error: unexpected 'gid=2000'` before any staging/probe. The hardened rollback path worked: Android ADB recovery reboot plus checked V2321 flash completed and final `selftest fail=0`. Next work is a host-only root-check fix: run simple `su -c id` and validate `uid=0` from captured stdout; do not blind-rerun AUD-5A again before that fix lands. V2404 completes that host-only fix: the runner now probes `adb shell su -c id`, validates captured stdout for `uid=0` in Python, and exposes the Magisk module policy as a dry-run `magisk_strategy` (`M0` transient helper default; `M1` temporary boot module only if M0 misses early ACDB/App Type edges; no native-init runtime dependency). Validation passed with py_compile, focused V2396 tests (15), full unittest suite (1089), materialized dry-run `future_live_ready=True`, and `git diff --check`. Next meaningful unit is the V2405 fresh bounded AUD-5A live rerun. V2405 reran the exact-gated AUD-5A live path after V2404: Android boot, post-handoff ADB settle, and `adb shell su -c id` all passed live (`uid=0` with Magisk context), proving the root-check fix. The run then failed at `stage-0` before any probe/playback because the M0 artifact directory still targeted `/cache/a90-audio-acdb-v2396`; Android returned `chmod: /cache/a90-audio-acdb-v2396: Permission denied`. Rollback via Android recovery plus checked V2321 flash succeeded and final `selftest fail=0`. Next work is a host-only artifact-path fix: move the M0 output under the writable staged `/data/local/tmp/a90-audio-acdb-v2396/` tree and update probe/service/collect/cleanup paths; do not escalate to M1 because this was not an early-capture timing miss. V2406 completes that host-only fix: M0 artifacts now live under `/data/local/tmp/a90-audio-acdb-v2396/artifacts`, generated probe/service scripts no longer reference `/cache`, probes pass `A90_V2396_OUT`, collection/cleanup/optional strace follow the new path, and tests assert no `/cache/a90-audio-acdb-v2396` remains in commands or generated module files. Validation passed with py_compile, focused V2396 tests (15), full unittest suite (1089), materialized dry-run `future_live_ready=True`, and `git diff --check`. V2407 then reran the exact-gated AUD-5A M0 live path successfully: Android boot, Magisk-root settle, staging under `/data/local/tmp`, baseline/active/post probes, AudioTrack playback, artifact pull, cleanup, and checked V2321 rollback all passed; final native `selftest fail=0`. Logcat captured the speaker calibration/App Type edge (`send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15, sample_rate 48000`, `ACDB -> send_audio_cal acdb_id=15 path=0 app id=0x11135`, `AUDIO_SET_AUDPROC_CAL cal_type[11]`, `AUDIO_SET_AFE_CAL cal_type[16]`), and tinymix showed `Audio Stream 0 App Type Cfg=69941 15 48000 2 ...`. V2407 also fixed the post-live analyzer integration so it writes final rollback state before analysis; rerun analyzer decision is `bounded-native-acdb-candidate`. M0 succeeded, so M1 temporary boot module is not justified. V2408 completed the host-only native ACDB/App Type bootstrap design: split the next native work into N1 App-Type-first (`Audio Stream 0 App Type Cfg 69941 15 48000 2` before the existing route/probe), N2 `/dev/msm_audio_cal` ioctl plumbing preflight, and N3 ACDB payload replay only after payload bytes are pinned. Magisk remains an Android-good measurement capsule, not a native runtime dependency; future Magisk use is limited to extracting missing ACDB ioctl/payload facts if N1/N2 prove they are needed. Next meaningful unit is V2409 host-only planner/runner support for the N1 App-Type gate, not another Android/Magisk capture. V2409 completed that host-only runner support: `native_audio_speaker_pilot_live_handoff_v2379.py` now has `--set-observed-app-type`, inserts the V2407 `Audio Stream 0 App Type Cfg 69941 15 48000 2` command before the route/probe, keeps AUD-4 default behavior unchanged, and requires the separate AUD-5B exact phrase for live App-Type-first runs. Magisk remains measurement-only; M1 boot-module escalation is still deferred because M0 already captured the needed edge. Next meaningful unit is the bounded live N1 App-Type-first discriminator. V2410 ran that bounded AUD-5B live discriminator: the App Type command returned rc 0, all 13 route controls applied, the V2386 PCM probe still failed at `pcm_prepare()` with `errno=22`, dmesg still showed missing AFE/ASM cal blocks plus ADM `ADSP_EFAILED`, all 12 reset commands and reset verification passed, and rollback to V2321 ended with `selftest fail=0`. N1 is closed as insufficient; next meaningful unit is N2 host-only `/dev/msm_audio_cal` preflight/ioctl ABI design, not another App Type retry. V2411 completed that host-only N2 design: source confirms `msm_audio_cal` is a dynamic misc device with public calibration ioctls 200-205, but N2 must stay existence/open-only because every real calibration ioctl can dispatch registered callbacks and mutate calibration state; Magisk remains M0 transient measurement by default, with M1 temporary boot module reserved only if M0 misses early `/dev/msm_audio_cal` payloads. V2412 implemented the host-only AUD-5C dry-run planner `native_audio_msm_audio_cal_preflight_gate_v2412.py`: it emits the V2334 materialization plus `/proc/misc`/`/dev/msm_audio_cal` inventory, runtime devnode materialization, and one open/close-only probe plan, rejects calibration ioctl/playback/Magisk tokens in focused tests, and keeps live execution as a separate next V-iteration. V2413 completed the exact-gated AUD-5C live open-only preflight: after fixing the dry-run/live shell path to `/bin/busybox sh`, V2334 flashed and passed health, ADSP boot-one-shot was accepted, `/dev/snd` materialized with 61 nodes, `/proc/misc` registered `msm_audio_cal` minor `54`, a runtime `/dev/msm_audio_cal` node was created and opened O_RDONLY once, the created node was removed, and rollback to V2321 ended with `selftest fail=0`. N2 reachability/openability is now closed. V2414 then defined the host-only N3 boundary: current Android-good evidence proves ACDB/App Type edges but not raw `msm_audio_cal` ioctl payload bytes/order, so native replay is blocked until a new Android-good payload-capture unit pins command sequence, decoded headers, private payload hashes, mem_handle policy, and cleanup/rollback behavior. Magisk remains measurement-only: M0 transient root observer first, M1 temporary boot module only if M0 misses an early payload edge. V2415 implemented the host-only N3-CAP0 payload-capture planner: it adds a source-controlled AArch64 Android-side ptrace observer that attaches to the stock audio process, filters ioctl syscalls whose fd resolves to /dev/msm_audio_cal, copies up to 512 bytes of the user request buffer into private JSONL only, and emits a future checked Android/M0 capture plan. The helper does not open /dev/msm_audio_cal or issue calibration ioctls; its Magisk policy follows the Wi-Fi-style measurement pattern with M0 transient root helper first and an M1 temporary boot module only if M0 reports missed-early-payload. Live execution is deferred to V2416 with the exact AUD-5D gate, and native replay remains blocked until decoded headers/payload hashes/cleanup policy are pinned.  V2416 executed the exact-gated M0 live handoff twice and rolled back to V2321 with final `selftest fail=0`: the first attempt exposed a private-artifact permission issue, and the second fixed collection but captured `0` `msm_audio_cal` ioctl entries even though logcat showed the real speaker ACDB edge in `android.hardware.audio.service` worker TID `4198` with `/dev/msm_audio_cal` open. This localizes the miss to process-main-thread-only ptrace, not to Magisk timing. Next meaningful unit is V2417 host-only thread-complete M0 capture support (`/proc/<pid>/task/*` helper per TID); do not escalate to an M1 temporary Magisk boot module unless thread-complete M0 still classifies a true missed-early-payload condition.  V2417 completed the host-only thread-complete M0 fix: the generated Android capture controller now enumerates `/proc/<pid>/task/*`, snapshots task lists/comm names, and starts one ptrace helper per TID; the helper now separates trace target `--pid <tid>` from fd-table owner `--fd-pid <tgid>` so worker-thread ioctls can be captured without relying on `/proc/<tid>/fd`. M1 temporary Magisk boot-module escalation remains deferred until a thread-complete M0 live rerun still misses a logcat-proven ACDB edge. V2363 and V2367 repeated the already-passed
AUD-3C read-only tinyalsa inventory at operator request: V2334 again materialized `/dev/snd`
(`61` nodes), `tinymix`/`tinypcminfo` read-only queries returned `rc=0`, and rollback to
V2321 ended with `selftest fail=0`; V2367 private evidence is
`workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-025616/`. These were
reproducibility replays and did not change the next frontier.

**Validation:** AUD-0/AUD-1 are host-only — `py_compile`/unittest for any harness code, no flash,
no device. Every AUD-2/AUD-3 device step (now overnight pre-authorized — no human-approval stop, but
the flash-safety machinery below is **unconditional and stays ON**): boot-only flash via the checked
helper, pinned + readback SHA, post-boot health check (`version`/`status`/`selftest fail=0`), USB
control channel returns, **auto-rollback to `v2321` on any failure** (`v2237`/`v48` deeper fallbacks),
no cascading bad flashes, known-good rollback image must be present before flashing. Bump init beyond
the current validated artifact; `vNNNN-purpose` tag. **If the evidence lands on "full HAL mandatory,"
close the epic with that evidence rather than grinding.**

### Next epic (QUEUED — start only after the audio epic reaches closure) — Video (Venus decode / display) feasibility *recon*

**Do NOT start this while the audio epic is open.** Begin only once audio is closed — either
internal-speaker playback is proven (a `tinyplay` made sound) **or** it is closed as "full HAL
mandatory / non-viable." One frontier at a time; finish audio first. Like audio, this is a
*research / feasibility* epic and a **"NON-VIABLE under native init" close is an acceptable outcome**.
Start **host-only** (recon/observation), exactly parallel to AUD-0/AUD-1, before any device step.

**Grounded starting facts (2026-06-14/15 session research; re-verify, do not trust blindly):**
- **Venus (HW video decode)** = the natural successor: `CONFIG_MSM_VIDC_V4L2=y` is in the stock kernel,
  and Venus is a **PIL/remoteproc subsystem with its own `venus` firmware** — so the **ADSP PIL
  bring-up pattern just proven in the audio epic transfers directly.** Decode → frames → out over the
  already-working NCM/Wi-Fi = a headless media node (no panel needed).
- **Display** = a separate flavor (NOT PIL): `DRM_MSM=y`, `DRM_MSM_DSI_STAGING=y`, panel
  `ss_dsi_panel_S6E3FC2_AMS670TA01_FHD`, and **continuous splash is configured** (`cont_splash` /
  `qcom,cont-splash` in DTS) → the bootloader lights the panel and hands a live framebuffer to the
  kernel. The cheap probe is whether native init inherits a writable `/dev/dri/card0` or `/dev/fb0`
  **before cont-splash teardown** — i.e. draw to a screen region WITHOUT a from-scratch DSI panel init.
- **GPU (Adreno/KGSL) = OUT of scope here** (open-hang wall; GMU + GX-GDSC power = regulator
  brick-caution). Not needed for decode (Venus) or scanout (DPU).

**Staged units (host-only first):**
- **VID-0 — host-only inventory & decision basis.** From the stock vendor image + kernel source + DTS,
  enumerate the Venus `venus*` firmware + the VIDC V4L2 driver / expected `/dev/video*` nodes, and the
  display DRM/DSI/cont-splash config + panel node. Decide the lower-risk sub-target: **Venus headless
  decode (reuses the proven PIL pattern)** vs **display cont-splash framebuffer probe**. Deliverable:
  feasibility report.
- **VID-1 — host-only path analysis.** Venus: the remoteproc/PIL `venus` load path + minimal V4L2
  decode plumbing (parallel to AUD-1). Display: cont-splash teardown timing + `/dev/dri/card0` vs
  `/dev/fb0` exposure + a region-blit plan that does **not** re-init the panel. Deliverable: the
  reviewable device-step plan.
- **VID-2+ — DEVICE (overnight pre-authorized, recoverable envelope) — observation first.** Does
  native init see `/dev/video*` (Venus) / an inherited framebuffer (display)? Venus PIL load is
  reboot-recoverable like ADSP. **Display: use ONLY the inherited cont-splash surface — do NOT drive
  backlight/PMIC/PWM/regulator or run a from-scratch DSI panel init (brick-caution); if the splash
  surface is already torn down / blanked, STOP that sub-target and report rather than re-lighting the
  panel.**

**Closure:** a grounded "what's reachable" answer (Venus headless decode? display region-draw via
cont-splash?) or a defensible non-viable close. The fun end-targets — Bad Apple, then DOOM (touch
evdev or USB-keyboard input) — are downstream demos, **not** this recon epic.

### Downstream demo targets (REFERENCE / direction only — NOT an active directive)

The payoff demos the audio + video tracks aim at. This is **direction, not a committed step list**
(refine the exact approach from recon results), and it is **gated**: do NOT start any item until its
prerequisites are actually proven. Until then this block is **orientation only** — e.g. it tells the
video recon to **optimize for a drawable display framebuffer (the demos need it), not Venus** (the
demos need no hardware video decode). Do not let it pull the loop off the one active frontier.

Dependency-ordered (prereq in parens):
1. **Boot chime = sound check** (prereq: AUD-4 sound) — PID-1 init plays a bundled bounded-amplitude
   chime at boot, **best-effort / non-fatal — never block boot on audio**. Minimal "audio integrated
   into the system" proof.
2. **Display framebuffer** (prereq: none — this *is* the video recon's display sub-target) — a
   drawable inherited **cont-splash** surface (`/dev/dri/card0` or `/dev/fb0`) + region blit; **no
   from-scratch DSI panel init, no backlight/PMIC/regulator writes (brick-caution); if the splash
   surface is already torn down, STOP and report rather than re-lighting the panel**.
3. **Bad Apple demo** (prereq: audio + display framebuffer) — pre-decoded raw frames + raw PCM + a
   sync loop (no codec, no Venus). The AV-integration demo.
4. **Touch bring-up** (prereq: none; parallel-able) — read the touch panel via evdev
   `/dev/input/event*` (driver likely auto-probes; may need a firmware_class feed). The input track.
5. **DOOM = capstone** (prereq: display + input [touch *or* USB-keyboard fallback]; audio SFX
   optional) — `doomgeneric`: `DG_DrawFrame` → framebuffer region, `DG_GetKey` → touch evdev.
   Combines display + input + audio.

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

## Current audio frontier update (V2440)

V2428 completed the fixed Android/Magisk M0 rerun and justified M1: the helper resumed the
same worker TID that logcat showed running the speaker/ACDB path with `/dev/msm_audio_cal`
open, yet still captured `0` calibration ioctls. V2429 then completed the host-only M1
planner. It builds a private temporary Magisk `service.sh` module that packages the same
V2423 thread-set clone-following observer earlier in Android boot/service lifetime, using
`service.sh` late_start mode rather than blocking `post-fs-data`.

V2430 implemented and ran the exact-gated Android M1 live runner. Android boot/root handoff,
`/data/local/tmp` staging, APK install, cleanup-finally, checked V2321 rollback, and final
native `selftest fail=0` all passed. The module never activated: direct `su -c` placement
under `/data/adb/modules/a90_audio_acdb_m1_v2429` failed with `Permission denied` at
`stage-6`, before the Android reboot that would start Magisk `service.sh`. No M1
`msm_audio_cal` ioctl artifact was captured.

V2431 completed the host-only Magisk staging redesign. Official Magisk docs confirm
`/data/adb/modules` and `/data/adb/modules_update` are Magisk-managed secure paths,
`service.sh` is the correct non-blocking late_start module hook, `su -mm` /
`--mount-master` exists for the global mount namespace, and `magisk --install-module ZIP`
is the official installer interface. Because V2430 failed before cleanup of a real module
could be proven, install-module remains deferred.

V2432 completed the checked Android read-only Magisk access probe and rolled back to V2321
with final native `selftest fail=0`. A pre-commit self-audit found the first private V2432
run had malformed `adb shell su -c` quoting, so its `su` probes ran as `shell`; the runner
was fixed before commit. The corrected live run proved `su -c` and `su -mm -c` execute as
`uid=0(root)` / `u:r:magisk:s0`, and both can read `/data/adb`, `/data/adb/modules`, and
`/data/adb/service.d` with no root permission-denied lines. `/data/adb/modules_update` was
absent, not permission-denied. This re-opens the Magisk module path as a viable
Android-good measurement/packaging mechanism: V2430's direct-staging failure is now
suspect as command construction/quoting, not proof that the module namespace is blocked.

V2433 completed the host-only cleanup-probe design. The next live write must not activate
M1 yet; it should only create and remove one inert unique directory under
`/data/adb/modules/.a90_v2433_cleanup_probe_<run_stamp>`, with no `module.prop`, no
`service.sh`, no boot-script files, no reboot before cleanup proof, and checked rollback to
V2321 after cleanup. This is the targeted safety bridge between read-only Magisk access and
any real temporary module activation.

V2434 implemented the source/test-only exact-gated cleanup-probe runner for that design.
Its dry-run emits the checked Android handoff, `su -c` and `su -mm -c` identity/path
probes, one future create/remove operation for
`/data/adb/modules/.a90_v2433_cleanup_probe_<safe_tag>`, exact marker cleanup with
`rm -f "$MARKER"` plus `rmdir "$PROBE_DIR"`, residue checks, and checked rollback to
V2321. Focused tests cover wrong-approval refusal, unsafe tag rejection, exact safe-prefix
path generation, success/residue summarization, and command-safety blockers for
activation files, broad module removal, playback, and calibration tokens. V2434 did not
boot Android and did not write `/data/adb`.

V2435 then ran that exact-gated cleanup probe live under normal Android and rolled back to
V2321 with final native `selftest fail=0`. The runner flashed the pinned Android boot image,
verified Magisk root settle, ran both `su -c` and `su -mm -c` read-only probes, created the
single inert path `/data/adb/modules/.a90_v2433_cleanup_probe_v2435_20260615-133444`, wrote
and read one `.probe` marker, removed the marker with `rm -f "$MARKER"`, removed the
directory with `rmdir "$PROBE_DIR"`, and reported `cleanup-probe-ok` with
`no_residue_seen=true`, `permission_denied_lines=[]`, and `residue_lines=[]`. This closes
the cleanup bridge: corrected direct Magisk-root staging can touch the module namespace and
cleanly unwind an exact inert path before rollback.

M1 remains Android-good **measurement/packaging** only. It does not open `/dev/msm_audio_cal`,
issue calibration ioctls, replay native audio, write native speaker/mixer/PCM state, or
become a native-init dependency. Native replay remains blocked until raw ioctl command order,
decoded headers, private payload hashes, mem-handle policy, and cleanup behavior are pinned.

V2436 completed that source/test-only M1 retry runner as a new wrapper rather than mutating
the historical V2430 artifact. It keeps the V2429 private temporary Magisk module template
and Android-good measurement purpose, but changes staging/cleanup to the V2432/V2435-proven
remote-shell form: `adb shell "su -c '<script>'"` for root scripts and
`adb shell "su -mm -c '<script>'"` for mount-master read-only module namespace probes. The
dry-run preflights exact module/module_update absence, avoids deleting module paths before
the pre-residue check, stages only exact files into `/data/adb/modules/a90_audio_acdb_m1_v2429`,
requires `A90_M1_RESIDUE_CHECK_OK`, `A90_M1_INSTALL_OK`, and `A90_M1_CLEANUP_OK`, rejects
broad `/data/adb/modules` removal and `magisk --install-module`, and remains host-only in
V2436. Materialized dry-run is `future_live_ready=true` with no blockers.

V2437 then ran that exact-gated live M1 retry and rolled back cleanly to V2321 with final
native `selftest fail=0`. Android boot, Magisk root settle, both Magisk namespace read-only
probes, the exact pre-residue check, and root-side staging setup all passed. The run stopped
before module install/activation because `stage-4` tried to `adb push` module files into
`/data/local/tmp/a90-audio-acdb-m1-v2429/module-stage/` after root had created that staging
tree as `0700`. The Android `shell` user therefore hit `Permission denied`. No
`service.sh` module was installed, no Android reboot for module activation occurred, and no
ACDB payload artifact was captured. This is a runner payload-transfer bug, not evidence that
the Magisk module namespace is blocked: V2435 already proved exact create/remove under
`/data/adb/modules` works when performed by correctly quoted Magisk root shell commands.

Magisk remains Android-good **measurement/packaging** only, matching the earlier Wi-Fi-style
handoffs: it is acceptable to use a temporary module to move the stock-Android observer
earlier in boot/service lifetime, but it must not become a native-init runtime dependency or
issue native calibration ioctls, native speaker/mixer/PCM writes, Wi-Fi actions, DHCP,
routes, or ping.

Next meaningful unit is **V2438 host-only staging-transfer fix**. Keep the V2436 wrapper and
M1 semantics, but split file transfer by privilege: push module payload files into a
shell-writable incoming directory under `/data/local/tmp/a90-audio-acdb-m1-v2429/`, validate
exact filenames/hashes, then use `su -c` to copy/install only those exact files into
`/data/adb/modules/a90_audio_acdb_m1_v2429` with final restrictive permissions and exact
cleanup. Keep `magisk --install-module` deferred and do not rerun live activation until the
host-only fix, tests, dry-run, and command-safety checks pass.

V2438 completed that host-only staging-transfer fix as a new runner instead of mutating the
V2436 artifact. It creates a shell-owned incoming directory at
`/data/local/tmp/a90-audio-acdb-m1-v2429/incoming` (`uid:gid 2000:2000`) while keeping the
parent run directory traversable but not listable (`0711`), then has root validate exactly
four files and their SHA-256 values before copying into
`/data/adb/modules/a90_audio_acdb_m1_v2429`. The final module path is still root-owned and
permission-tightened, cleanup remains exact, and `magisk --install-module` remains deferred.
Materialized dry-run is `future_live_ready=true` with `command_safety_ok=true`; focused
tests prove all pushes target `/incoming/` rather than the broken V2437 `module-stage` path
and that hash/file-count validation is present.

Next meaningful unit is **V2439 exact-gated live rerun** with the V2438 runner. It should
use the same M1 boundary as V2437: Android-good measurement only, temporary Magisk
`service.sh` module, no native speaker/mixer/PCM writes, no native `/dev/msm_audio_cal`
ioctl, no native ACDB replay, and exact cleanup before checked V2321 rollback. If V2439
captures payload events, analyze command order, decoded headers, private payload hashes,
mem-handle policy, and cleanup behavior before native replay design. If V2439 activates the
module but still captures zero events, classify that Android-good measurement wall before
changing hook strategy.

V2439 then ran that exact-gated live rerun and rolled back to V2321 with final native
`selftest fail=0`. It closed the V2437 staging-transfer wall: all four payload files pushed
into the V2438 shell-owned `/incoming/` directory, root validated exact SHA-256 values,
installed the exact module files under `/data/adb/modules/a90_audio_acdb_m1_v2429`, and
reported `A90_M1_INSTALL_OK`. The planned Android reboot for Magisk `service.sh`
activation then occurred. After reboot, `adb wait-for-device` and boot-complete recheck
passed, but the immediate `su -c id` root check failed with `adb: no devices/emulators
found`; cleanup-finally reacquired ADB, uninstalled the APK, removed the module/run
directory with `A90_M1_CLEANUP_OK`, and checked V2321 rollback passed. No logcat,
playback, or artifact collection ran, so V2439 says nothing about whether the M1 observer
captures payload events. The new wall is a post-module-reboot ADB/Magisk-root settle
robustness gap, not staging or module namespace.

Next meaningful unit is **V2440 host-only post-module-reboot settle hardening**. Keep the
V2438 staging/install path unchanged, but replace the single post-reboot `su -c id` check
with a bounded ADB reacquire + Magisk-root retry loop that records failed attempts as
metadata and proceeds only after `uid=0`. Do not alter observer payload, module semantics,
playback stimulus, native audio boundaries, cleanup, or rollback behavior.

V2440 completed that host-only hardening as a new runner. It preserves V2438 incoming
transfer, exact SHA validation, final module install path, observer payload, playback
stimulus, cleanup, rollback, and native-audio boundaries. Only the post-module-reboot
settle path changed: after `adb wait-for-device` and boot-complete recheck, the runner now
performs up to eight bounded `adb wait-for-device` + `su -c id` root-check attempts with
three seconds between attempts, records each root-check step as
`root_ready=true|false` plus `settle_decision`, and proceeds only after stdout contains
`uid=0`. Materialized dry-run is `future_live_ready=true` with command safety clean; focused
tests prove a transient first root-check failure is tolerated and a later `uid=0` result
continues.

Next meaningful unit is **V2441 exact-gated live rerun** with the V2440 runner. It should
keep the same M1 boundary as V2439: Android-good measurement only, temporary Magisk
`service.sh` module, no native speaker/mixer/PCM writes, no native `/dev/msm_audio_cal`
ioctl, no native ACDB replay, and exact cleanup before checked V2321 rollback.

V2441 ran that exact-gated live rerun and rolled back to V2321 with final native
`selftest fail=0`, but it exposed a V2440 runner wiring miss before any logcat/playback or
artifact collection. The module staging/install path still works (`A90_M1_INSTALL_OK`),
and cleanup removed both `/data/adb/modules/a90_audio_acdb_m1_v2429` and
`/data/local/tmp/a90-audio-acdb-m1-v2429`. After the Android reboot for Magisk
`service.sh` activation, `adb wait-for-device` and boot-complete recheck passed, but the
root check failed with `adb: no devices/emulators found`. Source inspection shows why:
V2440 calls `run_post_module_reboot_settle()` immediately after the initial Android flash,
before module staging, while the actual post-module activation reboot still uses the older
single-shot `v2396.run_android_post_handoff_settle()` path. Classification:
`post-module-reboot-settle-retry-wired-to-wrong-boundary`. The next meaningful unit is
**V2442 host-only wiring fix**: move/use the bounded post-module root retry after
`android-reboot-for-magisk-service`, add a focused ordering regression test, and do not
rerun live until dry-run/tests prove the retry loop is attached to the module-activation
reboot.


V2442 completed that host-only wiring fix. The new runner preserves the V2438/V2440
staging/install, SHA validation, observer payload, playback stimulus, cleanup, rollback,
and native-audio boundaries, but changes live settle ordering: the initial Android flash
uses the established Android post-handoff settle, while the bounded post-module root retry
now runs after `android-reboot-for-magisk-service` and before logcat/playback. A focused
ordering regression asserts that the module activation reboot is followed by
`run_post_module_reboot_settle()` before `logcat-clear-before-stimulus`, preventing the
V2441 `android-post-handoff-settle-2` single-shot edge from returning. Materialized dry-run
is `future_live_ready=true` with command safety clean; focused V2442 tests pass (`8`), full
unittest discovery passes (`1206`), and `git diff --check` passes. Next meaningful unit is
**V2443 exact-gated live rerun** using the V2442 runner, with the same M1 Android-good
measurement boundary and no native ACDB replay.


V2443 ran that exact-gated live rerun and rolled back to V2321 with final native
`selftest fail=0`. The V2442 wiring fix worked: after `android-reboot-for-magisk-service`,
the run executed `android-post-module-reboot-root-check-1` with `root_ready=true` before
logcat/playback. The Android stimulus ran and logcat again showed the speaker ACDB edge
(`send_app_type_cfg_for_device PLAYBACK app_type 69941`, `ACDB -> send_audio_cal acdb_id
15`, `AUDIO_SET_AUDPROC_CAL cal_type[11]`, `AUDIO_SET_AFE_CAL cal_type[16]`). However,
payload capture still produced zero JSONL entries. The module service found target pids
`795` and `918` and launched helper processes, but both helper logs contain only usage
text. Source inspection shows why: the helper accepts `--duration-sec` only up to `120`,
while the generated `service.sh` passed the default remaining duration `180`. Classification:
`helper-started-but-rejected-duration-arg`. Next meaningful unit is **V2444 host-only
service duration clamp**: keep the V2442 live wiring and boundaries unchanged, clamp each
helper invocation's `--duration-sec` to the helper-supported maximum, add tests, and only
then rerun live.


V2444 completed that host-only clamp. The shared M1 module template now emits
`HELPER_MAX_DURATION_SEC="120"`, computes per-target `helper_duration`, clamps it to the
helper-supported maximum, logs `helper_duration` in `A90_M1_HELPER_START`, and invokes the
helper with `--duration-sec "$helper_duration"` rather than raw `$remaining`. V2444 also
adds a fresh runner identity preserving the V2442 live wiring. Focused tests prove the
service template no longer passes `$remaining` directly; materialized dry-run is
`future_live_ready=true` with command safety clean and generated service containing the
clamp; focused tests pass (`12`), full unittest discovery passes (`1214`), and
`git diff --check` passes. Next meaningful unit is **V2445 exact-gated live rerun** using
the V2444 runner. First success criterion is helper JSONL startup/trace telemetry, not yet
native replay.

V2445 ran that exact-gated live rerun with the V2444 runner. Android handoff, staging,
APK install, incoming SHA validation, and final module install all passed (`A90_M1_INSTALL_OK`),
including the duration-clamped `service.sh` SHA `f94ed1949b7d738dc0f9a2ca12456bbec8913fef516899e102cbd97f45a409f7`.
The run did not reach logcat/playback/artifact pull because the post-module
`adb wait-for-device` step timed out after `120s`; cleanup immediately entered its finally
path, waited another `86.292s`, reacquired ADB, uninstalled the APK, removed both
`/data/adb/modules/a90_audio_acdb_m1_v2429` and `/data/local/tmp/a90-audio-acdb-m1-v2429`,
then checked V2321 rollback passed. Independent post-run health is V2321 with
`selftest fail=0`. The measured Android ADB return time was about `206.359s` after the
module-activation reboot, so the new wall is a post-module wait-budget/classification gap,
not staging, cleanup, rollback, or helper argument handling. Next meaningful unit is
**V2446 host-only post-module wait-budget hardening**: extend or split the post-module ADB
wait above the observed return time, add focused tests, and keep the M1 Android-good
measurement boundary unchanged. Do not blind-rerun live before that host-only fix.

V2446 completed that host-only hardening. It adds a fresh V2446 runner identity, separates
post-module `adb wait-for-device` from the generic `120s` ADB command timeout, and defaults
the dedicated post-module ADB wait budget to `300s`, above the observed V2445 `206.359s`
return. The dry-run records `adb_wait_timeout_sec=300.0` and
`v2446_observed_v2445_adb_return_sec=206.359`; materialized dry-run is
`future_live_ready=true` with command safety clean. Focused tests pass (`8`), full unittest
discovery passes (`1222`), and `git diff --check` passes.

V2447 ran the exact-gated live rerun with the V2446 runner. The new post-module wait budget
worked: Android ADB returned after the Magisk module activation reboot in `191.618s` under
the `300s` timeout, Magisk root was ready, playback and artifact collection ran, cleanup
completed, and checked rollback returned the device to V2321 with independent
`selftest fail=0`. The temporary Magisk module path is therefore valid as a Wi-Fi-style
Android-good measurement capsule: boot-time helper packaging, service hooks, vendor-log
probes, exact cleanup, and rollback are usable. It is **not** a native-init runtime
dependency. The capture result remains negative: `10` threadset helpers started,
`138` tracees were added, `90` clone events were followed, and audio HAL worker TID
`12004` (the logcat-proven ACDB worker) was attached, but the helper captured `0`
`/dev/msm_audio_cal` ioctl entries/exits while logcat showed `send_app_type_cfg_for_device`
and `ACDB -> send_audio_cal acdb_id=15`. Next meaningful unit is **V2448 host-only
artifact/capture-method analysis**: do not blind-rerun M1; classify the ptrace syscall
state machine, clone/syscall sequencing, fd-resolution timing, and timestamp gaps, then add
future helper timestamps or switch capture method only if that analysis justifies it. Native
ACDB replay remains blocked until command sequence, decoded headers, payload hashes, and
cleanup policy are pinned.

V2448 completed that host-only analysis. Source review confirms the V2423 helper records
only fd-matched `/dev/msm_audio_cal` `ioctl_entry`/`ioctl_exit` events; it does not record
total syscall stops, total ioctl attempts before fd filtering, fd readlink misses, unmatched
fd targets, entry/exit parity state, or timestamps. V2447 artifacts also show the relevant
p8795/p8796 helper JSONL files were pulled before helper completion: both lack terminal
`stop` events, and p8795 ends immediately after `tracee-add`/`clone-child-resumed` for
TID `12004`. Therefore the V2447 zero-ioctl classification is a partial/opaque observer
result, not a clean negative. Next meaningful unit is **V2449 host-only diagnostic M1
observer/runner revision**: add service/helper timestamps, public-safe syscall/ioctl/fd
counters and first-N unmatched ioctl samples, classify missing terminal `stop` as
`partial-helper-still-running`, and make the runner wait for helper completion before
collecting artifacts. Do not rerun M1 unchanged and do not attempt native ACDB replay.

V2449 completed that host-only diagnostic observer revision. It adds
`a90_acdb_ioctl_capture_diag_v2449.c` and
`native_audio_acdb_m1_diag_observer_planner_v2449.py`: the helper now emits monotonic/wall
timestamps, syscall-stop/syscall-entry counters, pre-filter `ioctl` counts,
`/dev/msm_audio_cal` fd-match/fd-miss/readlink-error counters, bounded metadata-only
`ioctl_unmatched` samples, and terminal `stop` counters. The temporary M1 service module
now passes `--max-unmatched-samples`, logs `A90_M1_DIAG_*` service/helper markers, waits for
helper completion, and the future collection contract requires terminal JSONL `stop`
records or the `partial-helper-still-running` classification. Materialized dry-run reports
`future_live_ready=true`, command safety clean, private helper SHA256
`9520e9f297ba4cb52ce2730d8166876409162a70f64998b7c2ac16ca21f165f8`, and private module zip
SHA256 `ef98419a2a63f610115238eebf934391e8d1799a3c3b9329d9426c4618428bd0`.
V2450 implemented and ran the exact-gated AUD-5K live handoff. The first run exposed a
service/helper argument mismatch (`--duration-sec 180` rejected by the helper's max `120`);
V2450 fixed the service helper cap to `120` and reran. The second run proved the diagnostic
helper can trace Android audio processes (`syscall_stop_count=257929`,
`ioctl_any_entry_count=2619`) and rollback to V2321 cleanly, but captured no
`/dev/msm_audio_cal` payload (`ioctl_fd_match_count=0`, only binder/hwbinder fd misses) and
classified as `partial-helper-still-running` because five JSONL files lacked terminal `stop`.
The decisive timing fact is that the temporary Magisk service starts at Android boot and can
age out before host-triggered AudioTrack playback after a long post-module ADB settle
(observed about `207s`). V2451 completed the host-only hybrid M1 late-observer
implementation: the boot service remains an optional early observer, while a host-coordinated
late supervisor starts the staged `a90_acdb_ioctl_capture_diag_v2449` helper after
post-module ADB/root settle and before playback, waits for terminal `stop`, and classifies late
artifacts separately so old boot-service partials do not dominate the result. Materialized
dry-run reports `future_live_ready=true` and command safety clean. Magisk remains the right
Wi-Fi-style Android-good measurement capsule, but not a native runtime dependency. Next
V2452 executed that exact AUD-5L live path but failed before module staging: Android boot/root
settle passed, `stage-0`/`stage-1` readonly Magisk probes passed, then `stage-2` failed with
`adb: no devices/emulators found` before the pre-residue shell script ran. Cleanup and checked
V2321 rollback passed (`selftest fail=0`). This is an Android ADB stage-gap, not ACDB evidence
and not a negative payload result. V2453 completed the host-only stage-wait hardening: the V2451
runner now inserts `adb wait-for-device` before every staged `adb shell`, `adb push`, and
`adb install` command; materialized dry-run reports `stage_wait_count=10`, `future_live_ready=true`,
and command safety clean. Next meaningful unit is a **fresh V2454 exact-gated AUD-5L live rerun**
using the same exact phrase:
`AUD-5L-acdb-m1-hybrid-late-observer go: rollbackable Android AudioTrack speaker msm_audio_cal
diagnostic ioctl capture with temporary Magisk service module plus host-coordinated late
observer, helper-completion wait, no native calibration ioctl, no native speaker write,
rollback to V2321`. V2454 reran that path and proved the stage-wait hardening: all staged
shell/push/install waits passed, all module/APK staging passed, and `stage-9` installed the
temporary module with `A90_M1_INSTALL_OK`. The run then failed before late observer startup at
the post-module hard boot-complete recheck: after `adb wait-for-device` returned at about
`207.6s`, `sys.boot_completed` and `dev.bootcomplete` stayed empty for the next 30s. Cleanup
and checked V2321 rollback passed (`selftest fail=0`). This is still not ACDB evidence and not
a negative payload result. V2455 completed the host-only post-module settle hardening: the V2451
runner now keeps the long ADB wait, records post-module boot-complete as a soft 180s telemetry
gate with `A90_POST_MODULE_BOOT_COMPLETE_*` markers, and still requires Magisk `uid=0` root as
the hard gate before late observer/playback. Materialized dry-run reports
`future_live_ready=true`, `command_safety_ok=true`, `stage_wait_count=10`,
`boot_complete_soft_gate=true`, and `root_check_hard_gate=true`. Magisk remains the Wi-Fi-style
Android-good measurement capsule only, not a native-init runtime dependency. Next meaningful unit
is a **fresh V2456 exact-gated AUD-5L live rerun**. Do not attempt native ACDB replay before
payload order, decoded headers, hashes, mem-handle policy, and cleanup policy are pinned.
V2456 preflight is now complete without flash/playback: bridge is reachable, V2321
`version/status/selftest verbose` passed with `fail=0`, checked V2321 `--verify-only` passed,
V2321/V2237/V48 rollback inputs are present, and the materialized V2451/V2455 dry-run reports
`future_live_ready=true`, `command_safety_ok=true`, `stage_wait_count=10`,
`boot_complete_soft_gate=true`, and `root_check_hard_gate=true`. After the 2026-06-15
principle-based preauthorization update, V2456 then executed the AUD-5L live rerun inside the
recoverable envelope: Android flash via checked helper passed, Android ADB and boot-complete
recheck passed, but the initial `adb shell su -c id` root recheck returned rc `0` with empty
stdout/stderr, so the runner failed closed before module staging, late observer startup, playback,
or artifact collection. Cleanup confirmed no M1 module/run-dir residue, checked rollback to V2321
passed, and final `selftest verbose` returned `fail=0`. This is not ACDB payload evidence and not
a negative payload result. Next meaningful unit is host-only runner hardening for this
`root-output-empty` gap: classify the empty-output case distinctly, add bounded root reprobe/retry
metadata, keep `uid=0` as the hard gate before late observer/playback, and do not rerun AUD-5L
unchanged. V2457 completed that host-only hardening: the shared Android/Magisk settle path now
classifies root probes as `root-ready` / `root-output-empty` / `root-command-failed` /
`root-no-uid0`, validates combined stdout/stderr for `uid=0`, records rc and output lengths, and
retries the initial post-handoff root check up to 4 attempts with 2s delay before failing closed.
V2451 dry-run metadata now exposes the root hard-gate contract, and the post-module root retry loop
uses the same classification metadata. Focused tests passed (`28` tests), `py_compile` passed, and
materialized V2451 dry-run is live-ready with `future_live_ready=true`, `future_live_blockers=[]`,
and `command_safety_ok=true`. Next meaningful unit is a fresh AUD-5L live rerun using the
V2457-hardened runner; if root output is empty again, the run should now preserve per-attempt
`root-output-empty` evidence instead of stopping after a single opaque root check. V2458 executed
that live rerun and rolled back cleanly to V2321 with final `selftest fail=0`. The root hardening
worked: both initial and post-module Magisk checks were `root-ready` on attempt 1. The run reached
the intended Android-good measurement window: temporary M1 module staging/install passed, post-module
ADB/root settle passed, the late observer started before playback, Android framework `AudioTrack`
played successfully (`A90_AUDIO_STIMULUS_FINISH rc=0`), logcat showed the speaker ACDB edge
(`send_app_type_cfg_for_device PLAYBACK app_type 69941, acdb_dev_id 15`, `ACDB -> send_audio_cal
acdb_id=15`, `AUDIO_SET_AUDPROC_CAL cal_type[11]`, `AUDIO_SET_AFE_CAL cal_type[16]`), artifacts were
pulled, cleanup removed the module/run dir, and rollback passed. Payload result: no
`/dev/msm_audio_cal` ioctl payload was captured. Overall classification was
`hybrid-late-ioctl-any-but-fd-miss`; late observer classification was
`late-ioctl-any-but-fd-miss` with `ioctl_any_entry_count=492`, `ioctl_fd_match_count=0`, complete
terminal stops, and no payload hashes. The late FD snapshot showed the traced audio HAL process
`12816` had `/dev/msm_audio_cal` open as fd `13`, and clone-follow attached the ACDB worker TID
`15644`, but that traced process reported `ioctl_any_entry_count=0`; captured ioctl activity was
only binder/hwbinder in the AudioFlinger-side process. Do not rerun M1 unchanged. Next meaningful
unit is host-only mechanism analysis of stock `libacdbloader.so`/HAL plus the kernel
`msm_audio_cal` ABI to explain how the logged `AUDIO_SET_*` calibration reaches the kernel without a
userspace `/dev/msm_audio_cal` ioctl in the traced playback window; inspect `allocate_cal_block:
mmap`, mmap/shared-memory/binder/vendor-service possibilities, and whether native needs ACDB loader
semantics rather than raw ioctl replay.

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
