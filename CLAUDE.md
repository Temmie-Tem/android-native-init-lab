# CLAUDE.md

This is the active agent guide for this repository. Keep it short and current.
For full history, read `docs/reports/`, `docs/overview/PROJECT_STATUS.md`, and
`docs/archive/legacy/guides/CLAUDE_LEGACY_WIFI_RESEARCH_LOG_2026-06-07.md`.

## Current Project State

- Device: Samsung Galaxy A90 5G `SM-A908N`, build `A908NKSU5EWA3`.
- Kernel: Samsung stock Android Linux `4.14.190`.
- Runtime goal: custom static `/init` as PID 1 on the stock Android kernel.
- **Resident validated image / rollback checkpoint (V2321): `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`** — image `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`, SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`. Carries the full V2313–V2315 USB control surface, V2316 serial redaction/userspace configfs identity, V2318 manufacturer rodata patch (`SAMSUNG` → `A90-LNX`), and the V2321 fixed-length clean product rodata patch (`SAMSUNG_Android\0` → `A90 Linux ARM64\0`) with no product-slot overrun; adjacent USB configfs `KERN_ERR` log-prefix bytes `0x01 0x33` are retained. Live validation: pinned boot-only flash/readback PASS, `version/status/selftest fail=0`, `usb status control.ok=1`, host descriptor now `iManufacturer=A90-LNX`, `iProduct=A90 Linux ARM64`, `iSerial=A90NATIVE001`, and `usb mass-storage expose`/`remove` smoke passed with NCM+ACM control returning. Known manufacturer collateral retained: the merged kernel rodata suffix `Gamepad for SAMSUNG` becomes `Gamepad for A90-LNX`; accepted for this fixed-string line. **`A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`** (image `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`, SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`) remains the deeper fully-Wi-Fi-proven fallback, with `boot_linux_v48.img` as final fallback.
- **Current validated test artifact (V2323): `A90 Linux init 0.9.287 (v2323-usb-multi-lun-identity)`** — image `workspace/private/inputs/boot_images/boot_linux_v2323_usb_multi_lun_identity.img`, SHA256 `c0d5d73ecf66fa26dd8efb1535e6ed61f3e37123ffd175663a5f8709aaf7eccb`. Closes named multi-LUN mass-storage U-B: parent USB descriptor remains V2321; `mass_storage.0/lun.0/inquiry_string` is `A90-LNX A90-INTERNAL    0001` with FAT label `A90INTERNAL`, and `mass_storage.0/lun.1/inquiry_string` is `A90-LNX A90-SD          0001` with FAT label `A90SD`. Both LUNs are `/cache` file-backed read-only FAT16 images, 8 MiB each. Host validation passed: `lsblk -S` sees two USB SCSI disks with models `A90-INTERNAL` and `A90-SD`, and the block view sees labels `A90INTERNAL` and `A90SD`, filesystem `vfat`, read-only `1`. `usb mass-storage remove` returns to NCM+ACM-only control with `selftest fail=0`. V2321 remains the rollback target until an explicit promotion decision. Previous U-A artifact: V2322 `0.9.286`, SHA256 `81355888b6b19407c76463ee8d5ca045fd0f17294c3329ceda0afc1ab2a36f53`.
- **Active epic — internal audio (ADSP/Q6) feasibility (V2324–V2332, 2026-06-14):** research whether the internal speaker/headphone path can be driven under native init (speaker *playback only*; modem/call audio and `q6voice` are out of scope). See `GOAL.md` active-epic block. AUD-0 (V2324, host-only) inventory: audio drivers are **built into the stock kernel image** (no vendor `.ko` to insert), and the ADSP firmware (`ADSP.MDT` + sparse `.b0x` segments), 33 `.acdb` calibration files, `mixer_paths_{pahu,tavil}.xml`, and the heavy Binder/HIDL `audio.primary.msmnile.so` HAL (itself libtinyalsa-based) all exist in the stock vendor image → **not non-viable**; mainline q6 path rejected (needs a kernel we do not run). On-device read-only `audio adsp-status` (V2326) plus the heavily-gated one-shot `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` (token + firmware preflight; writes `1` to `/sys/kernel/boot_adsp/boot` once) were exercised live only under explicit per-run operator approval. V2331 disabled the legacy Wi-Fi-only `firmware_class.path=/mnt/vendor/firmware` override for the audio artifact, leaving the boot cmdline path `/vendor/firmware_mnt/image`; V2332 then accepted exactly one AUD-2 ADSP boot write and brought up ADSP/Q6 far enough to expose `rpmsg.count=20` with `adsp_like=7`, `sound_class card_like=1 control_like=1`, and `/proc/asound/cards` entry `sm8150-tavil-snd-card`. **AUD-2 is closed as pass: DSP comes up + ALSA card appears.** Playback is not proven: `/dev/snd` node count remained `0`, and no mixer/HAL/tinyalsa/PCM/adsprpc path was attempted. AUD-3 remains separately operator-gated and should first design safe ALSA device-node materialization or prove tinyalsa can open the available native-init card path. Latest audio test build: `0.9.292 (v2334-audio-snd-nodes-preflight)`, image `boot_linux_v2334_audio_snd_nodes_preflight.img`, SHA256 `53b1130cd912ca4019a3d76835eb721804bae0460b920eb7fdfad5509a2dfcac`. V2334 is source/build-only: it adds read-only `audio snd-status` plus token-gated `audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY` for `/dev/snd` node materialization, with no ALSA open/ioctl/mixer/tinyalsa/playback. V2335 adds the source-only gated live runner for that materialization check; dry-run passed. The first exact-gated live attempt is recorded at V2336: V2334 flashed and booted, but the run stopped before any audio command because `candidate-selftest` hit a serial protocol desync; auto-rollback to V2321 succeeded with final `selftest fail=0`. The runner is now hardened with slow input plus bounded observation retries, and V2337 adds host-only regression tests for the approval gate, dry-run command plan, preflight checks, and observation retry helper. V2338 retried the exact-gated live run: V2334 booted, `audio adsp-boot-once` was accepted once, ADSP/Q6 again exposed `rpmsg.count=20 adsp_like=7`, `sound_class.count=128 card_like=1 control_like=1`, and `sm8150-tavil-snd-card`, but the runner stopped before `audio snd-materialize-once` because its card-wait parser missed inline `control_like=1`; rollback to V2321 succeeded with `selftest fail=0`. V2339 fixed that host parser and added regression tests so inline `sound_class` fields satisfy the pre-materialization card gate while `/dev/snd/* state=missing` no longer counts as materialized. Materialization still has no result and requires a fresh exact AUD-3-preflight operator gate before retry. Previous AUD-2 liveness build: `0.9.291 (v2331-audio-adsp-fwclass-native-path)`, SHA256 `8d3e95f7a638fff508d893ee321c0569a04debbad2d16ed7c34188c0a9d9de74`. **Device is currently resident on the V2321 rollback checkpoint.**
- Audio runner latest host-only hardening: V2340 routes the V2335 AUD-3 preflight runner's live serial native-init commands through shared `a90_transport.run_serial_command_recovered()`. Read-only observation commands may use recovery/retry for busy/protocol-noise/serial-missing cases, while token-gated `audio adsp-boot-once` and `audio snd-materialize-once` remain one-shot/non-retried. This was host-only; materialization still has no result and requires the exact AUD-3-preflight gate before a live retry.
- Audio readiness latest live check: V2341 performed only read-only/no-flash readiness on the resident V2321 checkpoint. Bridge was reachable, V2321 `--verify-only` passed, `selftest verbose` returned `fail=0`, and the V2335/V2340 runner dry-run preflight still passed with V2334/V2321/V2237 hashes available. No ADSP or `/dev/snd` command ran. The exact AUD-3-preflight phrase is still required before materialization.
- Audio AUD-3 latest live attempt: V2343 used the exact AUD-3-preflight approval to flash V2334, booted `0.9.292`, and passed candidate `selftest fail=0`, but stopped before ADSP activation because `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT` returned `rc=-16 status=busy` (`auto menu active`). No ADSP boot write, `/dev/snd` materialization, ALSA open/ioctl, mixer, tinyalsa, or playback occurred. Auto-rollback to V2321 succeeded and final `selftest fail=0`. Next unit is a host-only runner fix: pre-hide/menu-settle before token-gated one-shot commands while preserving no-retry after dispatch.
- Audio runner latest host-only fix: V2344 adds explicit safe `cmdv1 hide` plus bounded `--menu-settle-sec` before both token-gated one-shot audio commands (`adsp-boot-once` and `snd-materialize-once`) while preserving no-retry semantics after dispatch. Validation passed: `py_compile`, focused V2335 runner tests (9), dry-run plan with two settle entries, full unittest suite (1005), and `git diff --check`. A fresh exact AUD-3-preflight gate is still required for the next live retry.
- Audio tool staging latest host-only checkpoint: V2345 adds `build_audio_tinyalsa_tools_v2345.py`, fetching pinned AOSP `platform/external/tinyalsa` commit `e14bf1479ebaaabf60bc4472ce8d304f72f03c32` into `workspace/private` and building static stripped AArch64 `tinymix`, `tinypcminfo`, and `tinyplay` under `workspace/private/builds/audio/v2345-audio-tinyalsa-tools/bin/`. This is host-only and does not run tinyalsa or touch `/dev/snd`; it prepares the later read-only tinyalsa inventory gate after materialization. Validation passed: `py_compile`, focused builder tests (4), full unittest suite (1009), and `git diff --check`.
- Audio tinyalsa inventory gate latest host-only checkpoint: V2346 adds `native_audio_tinyalsa_inventory_gate_v2346.py`, a dry-run-only planner that verifies the V2345 private `tinymix`/`tinypcminfo` hashes and emits a future read-only mixer/PCM inventory command plan. It explicitly excludes `tinyplay`, mixer set operands, PCM playback/write, audio HAL, and adsprpc paths. This does not replace the pending exact-gated V2334 `/dev/snd` materialization run; future tinyalsa inventory has its own exact phrase and must wait until materialization passes.
- Bridge readiness latest host-only fix: V2347 updates `a90_bridge.py`, `serial_tcp_bridge.py`, and `a90_transport.py` to prefer the current V2321 A90-LNX by-id ACM identity (`usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00`) while retaining the legacy Samsung fallback. Read-only validation on resident V2321 selected the A90-LNX symlink, `selftest verbose` returned `fail=0`, and the AUD-3 runner dry-run preflight remained OK. No flash, ADSP, `/dev/snd`, ALSA, mixer, tinyalsa, or playback action ran; exact AUD-3 approval is still required.
- Audio AUD-3 materialization latest live result: V2348 used the exact AUD-3-preflight phrase, flashed V2334 `0.9.292`, ran one token-gated ADSP boot and one token-gated `/dev/snd` materialization, and then rolled back to V2321. Before materialization `audio.dev_snd.count=0`; after materialization `/dev/snd` had `count=61 control_like=1 pcm_like=59`, with `created=61 failed=0`, `open_attempted=0`, `ioctl_attempted=0`, `playback_attempted=0`, and `audio.status.audio_playback_attempted=0`. Candidate selftest and final rollback selftest both returned `fail=0`; final device version is again V2321 `0.9.285`. Playback is still unproven; next safe step is a separately gated read-only tinyalsa inventory, not `tinyplay`.
- Audio route-delta planning latest state: V2362 host-only design selected Android route-delta capture as the next speaker-route measurement. The proposed measurement boots normal Android, uses Android framework `AudioTrack` playback through AudioFlinger/vendor HAL, captures `tinymix -D 0 --all-values` before/during/after, rolls back to V2321, and diffs `SEC_TDM_RX_0` / `WSA_CDC_DMA_RX_0` / `RX INT7` / `COMP7` / `Spkr` controls offline. V2364 closed the checked-helper gap by adding `native_init_flash.py --post-flash-target android-adb`, Android boot-complete polling, optional Magisk root check, and `--expect-android-magic` while leaving native-init serial verification as the default path. V2365 added a host-only route-delta dry-run planner that verifies the pinned Android boot candidates and V2345 `tinymix`, emits the checked-helper Android flash/stage/snapshot/playback/rollback command plan, and records that the archived Android boot image needs a private `0600` sealed copy before helper use. The remaining live blocker is the missing Android framework `AudioTrack` stimulus DEX. V2363 replayed the already-passed AUD-3C read-only tinyalsa inventory on request: V2334 again materialized `/dev/snd` (`61` nodes), `tinymix`/`tinypcminfo` read-only commands returned `rc=0`, and rollback to V2321 ended with `selftest fail=0`. Do not attempt internal speaker playback, native `tinymix set`, PCM playback open/write, `tinyplay`, or Android route-delta live capture until the stimulus artifact exists, the runner is live-capable, and a fresh exact route-delta gate is provided.
- Audio playback design latest host-only checkpoint: V2342 analyzed the private vendor route XML after V2332 identified `sm8150-tavil-snd-card`. Future playback should use `mixer_paths_tavil.xml`, not `pahu`; start with wired-headphones/dummy-load routes before internal speaker; and first stage a provenance-pinned tinyalsa tool bundle because no standalone `tinymix`/`tinyplay`/`tinypcminfo` binary is currently staged. This does not bypass the current materialization gate.
- Previous validated checkpoint: `A90 Linux init 0.9.284 (v2320-usb-product-overrun2-rodata)` — image `workspace/private/inputs/boot_images/boot_linux_v2320_usb_product_overrun2_rodata.img`, SHA256 `4d80b3fbfc4317625b6ca23baa332b37d10061ecc7ac48926d2dc6df20a99402`. V2320 proved the two-byte product overrun boundary but intentionally damaged the adjacent USB configfs error-log prefix (`0x01 0x33` → `0x32 0x00`), so it is retained as experiment evidence, not the clean rollback checkpoint.
- Previous validated checkpoint: `A90 Linux init 0.9.283 (v2319-usb-product-overrun1-rodata)` — image `workspace/private/inputs/boot_images/boot_linux_v2319_usb_product_overrun1_rodata.img`, SHA256 `24f5a99e1c3f0d362f4b49cbc72ded9b12e10aa44d69133c9088091866c9b723`. V2319 proved the one-byte product overrun boundary: `iManufacturer=A90-LNX`, `iProduct=A90 Linux ARM64X`, `iSerial=A90NATIVE001`.
- Previous validated checkpoint: `A90 Linux init 0.9.282 (v2318-usb-full-identity-rodata)` — image `workspace/private/inputs/boot_images/boot_linux_v2318_usb_full_identity_rodata.img`, SHA256 `d3b22893763482f554abdb2bdab03d8e7a15d9186a15dd7b56482646c23a05b3`. V2318 proved the fixed-length full identity patch: `iManufacturer=A90-LNX`, `iProduct=A90 Linux ARM`, `iSerial=A90NATIVE001`.
- Previous validated checkpoint: `A90 Linux init 0.9.281 (v2317-usb-product-rodata)` — image `workspace/private/inputs/boot_images/boot_linux_v2317_usb_product_rodata.img`, SHA256 `a15558050fc038221420f99577bc18b03851e3ff5280afb61d535ae3ec4d3070`. V2317 proved the lowest-risk product-only kernel rodata patch and left `iManufacturer=SAMSUNG` for the next fixed-string test.
- Previous promoted checkpoint: `A90 Linux init 0.9.280 (v2316-usb-linux-identity)` — image `workspace/private/inputs/boot_images/boot_linux_v2316_usb_linux_identity.img`, SHA256 `cf54ff0ae3cca4af31263140e588920296abecdb0ffb690a807b3d8b393f452a`. V2316 redacted the real USB serial to `A90NATIVE001` and proved host-visible `iManufacturer`/`iProduct` are kernel-forced while configfs strings remain userspace-controlled.
- Previous validated test artifact: `A90 Linux init 0.9.279 (v2315-usb-ms-persona)` — closed U3 and layer ① of the USB gadget runtime-control epic. `usb mass-storage expose` creates a bounded read-only 8 MiB `/cache` backing image, links `mass_storage.0` as aux `configs/b.1/f3`, preserves `ncm.usb0` (`f2`) and `acm.usb0` (`f1`) with `control.ok=1`, and enumerates on the host as a read-only USB disk; `usb mass-storage remove` unlinks the aux function, clears the LUN file, removes the host disk, and returns to control-only `control.ok=1`; final `selftest fail=0`.
- Previous WLAN-event artifact: `A90 Linux init 0.9.276 (v2312-e1-connect-event-closure)` — kept V2311's modularized nl80211/rtnetlink event monitors and added `wifi connect-event`, confirming `NL80211_CMD_CONNECT` correlation with carrier up without DHCP/routes/ping.
- Previous promoted artifact: `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`, image `workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img` — adds read-only Wi-Fi detail surface on top of v2237.
- Known-good fallback: `workspace/private/inputs/boot_images/boot_linux_v48.img`.
- Baseline lineage (since the workspace reorg): `v726-wifi-lifecycle` → `v2169-transport-contract` → `v2174-wifi-urandom-connect` → `v2178-wifi-profile-autoconnect` → `v2182-hud-menu-cleanup` → `v2189-security-p0-stage-fix` → `v2232-service-object-fwclass-bridge` → `v2236-strict-wifi-connect` → `v2237-supplicant-terminate-poll` → `v2254-wifi-detail-surface` → `v2316-usb-linux-identity` → `v2317-usb-product-rodata` → `v2318-usb-full-identity-rodata` → `v2319-usb-product-overrun1-rodata` → `v2320-usb-product-overrun2-rodata` → `v2321-usb-clean-identity-rodata` → `v2322-usb-named-lun-identity` → `v2323-usb-multi-lun-identity` → `v2326-audio-adsp-status` → `v2327-audio-adsp-boot-once` → `v2329-audio-adsp-fw-preflight` → `v2331-audio-adsp-fwclass-native-path` (audio test builds; rollback still V2321).
- Current Wi-Fi status: native `wlan0` connects end-to-end (associate → DHCP → external ping) on both bands, and Wi-Fi is now an on-device native-init command surface (`wifi status` / `wifi scan` / `wifi connect` / `wifi connect-event` / `wifi events` / `wifi netevents` / `wifi dhcp` / `wifi ping` / `wifi cleanup`; see `docs/operations/NATIVE_INIT_WIFI_LIFECYCLE_COMMANDS.md`). V2236 requires `wpa_state=COMPLETED` to reject stale carrier, V2237 replaces the blind post-`TERMINATE` sleep with bounded supplicant exit polling plus SIGKILL escalation, V2254 adds read-only route/default-DNS detail fields to `wifi status` and `screenapp wifi-status`, and V2312 closes the WLAN kernel-interface event epic by correlating nl80211 `CONNECT` with carrier up. Long idle/hold data-path stability remains separate follow-up evidence, not a blocker for the current baseline.
- Next promoted/test baseline should use the next global run/build identity, bump native init beyond the current latest test artifact `0.9.291`, and use a `vNNNN-purpose` build tag.
- **Phase status (2026-06-14):** the WLAN kernel-interface event epic is closed at V2312. USB gadget runtime control layer ① is closed at V2315: U1 (`usb status`) at V2313, U2 (`usb mass-storage add/remove`) at V2314, and U3 read-only mass-storage persona end-to-end at V2315. V2316 redacted the real device serial and proved host-visible mfg/product are Samsung-forced in the downstream kernel; V2317 validated the lowest-risk kernel-side product-only rodata patch, V2318 validated the next fixed-length manufacturer rodata patch, V2319 validated the one-byte product overrun boundary, V2320 validated the two-byte product overrun boundary, and V2321 promoted the no-overrun clean descriptor `iManufacturer=A90-LNX`, `iProduct=A90 Linux ARM64`, `iSerial=A90NATIVE001` as the rollback checkpoint. Named mass-storage identity U-A is closed at V2322: single file-backed read-only `lun.0` appears on the host as SCSI model `A90-INTERNAL` with FAT label `A90INTERNAL`; U-B is closed at V2323: `lun.0` and `lun.1` appear as SCSI models `A90-INTERNAL` and `A90-SD` with FAT labels `A90INTERNAL` and `A90SD`. The boot-time userspace gadget identity is still written by the prebuilt `a90_usbnet` helper (bundled in the ramdisk from `workspace/private/inputs/external_tools/userland/bin/a90_usbnet-aarch64-static`), so changing `a90_usb_gadget.c`/`a90_usbnet.c` source still requires recompiling that prebuilt for userspace/configfs changes to take effect. The current chartered work is the internal-audio (ADSP/Q6) feasibility epic (see the active-epic bullet above and `GOAL.md`); AUD-3 playback remains a separate operator-gated step. Do not start adb-over-ffs layer ② or HID/BadUSB layer ③ without a new explicit goal. Kernel-observation reached exact KASLR slide (V2216 codeword-exact); ROPP full-stack symbolization needs the RKP-protected per-boot key = out of read-only scope. Kernel-security recon is also closed below.
- **Kernel-security recon phase CLOSED (2026-06-13).** Three n-day candidates triaged host-only, zero memory corruption triggered: FastRPC CVE-2024-43047 = vulnerable-in-source but **unreachable** (DSP rpmsg channel down under native init); Binder CVE-2023-20938/-21255 = **not vulnerable** (`is_failure`-keyed cleanup, balanced callers; over-decrement primitive absent); KGSL CVE-2023-33107 = primitive present + source-reachable but **runtime-open-blocked under native init + exploit-dev-gated**. Charter answer: EL1 via non-destructive n-day from this environment = **no**. Lesson confirmed ×3: *fix-marker absence ≠ exploitability*. v2321 is the rollback target; v2237 remains the deeper Wi-Fi-proven fallback. See `docs/reports/NATIVE_INIT_KERNEL_SECURITY_RECON_PHASE_CLOSE_CHECKPOINT_2026-06-13.md` (and V2284–V2308). No further kernel-security unit is chartered; reopen only per that report's criteria.

## Read First

- `docs/operations/WORKING_RULES.md` — top-level version/path/commit rules.
- `docs/operations/VERSIONING_POLICY.md` — run ID, init version, build tag, helper version, SHA axes.
- `docs/operations/WORKSPACE_STRUCTURE_AND_BOOTSTRAP.md` — canonical workspace layout and restore steps.
- `docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md` — flash and bridge procedure.
- `docs/operations/CLAUDE_NATIVE_INIT_RUNBOOK.md` — detailed operational runbook.
- `docs/reports/METHODS_TRIED_LEDGER_2026-06-04.md` — do-not-repeat ledger for Wi-Fi work.
- `docs/reports/WLAN_PD_PRODUCER_TRIGGER_DEEP_ANALYSIS_2026-06-04.md` — modem/WLAN-PD analysis boundary.

## Canonical Paths

Use workspace paths. Do not recreate old root payload trees.

| Purpose | Path |
| --- | --- |
| Active native-init source | `workspace/public/src/native-init/` |
| Active revalidation scripts | `workspace/public/src/scripts/revalidation/` |
| Shared Python harness | `workspace/public/src/harness/a90harness/` |
| Public boot tooling source | `workspace/public/src/third_party/mkbootimg/` |
| Historical source provenance | `workspace/public/archive/` |
| Boot image inputs/current rollback images | `workspace/private/inputs/boot_images/` |
| Firmware/vendor extracts | `workspace/private/inputs/firmware/` |
| Toolchains/external tools/kernel source | `workspace/private/inputs/` |
| Generated builds | `workspace/private/builds/` |
| Secrets | `workspace/private/secrets/` |
| Raw logs/device dumps/private archives | `workspace/private/raw-logs/`, `workspace/private/device-dumps/`, `workspace/private/archives/` |
| Structured Wi-Fi run evidence | `workspace/private/runs/wifi/` |
| Other structured run evidence | `tmp/wifi/runs/`, `tmp/logs/` |

Root `scripts/`, `stage3/`, `mkbootimg/`, `firmware/`, `kernel_build/`,
`toolchains/`, `external_tools/`, `backups/`, and `out/` are not active paths.
If an old script or document references them, migrate the active command before
using it for new baseline work.

## Version Rules

Keep these axes separate:

- Run ID: `VNNNN`, for project execution and reports.
- Native init version: `MAJOR.MINOR.PATCH`, visible on device and bumped only when the flashed artifact changes.
- Build tag: `vNNNN-purpose`, embedded in the boot/init baseline.
- Helper version: `helper-vNNN`, for helper binaries only.
- SHA256: final artifact identity.

Never use helper numbers as run IDs or boot image tags. If a new boot image SHA
becomes the rollback/test baseline, promote it under a new run/build identity.

## Common Commands

Start the serial bridge:

```bash
python3 workspace/public/src/scripts/revalidation/serial_tcp_bridge.py --port 54321
```

Query native init through the bridge:

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py version
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py 'selftest verbose'
```

Rebuild known boot-image baselines into private outputs:

```bash
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2169_transport_contract.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2174_wifi_urandom_connect.py
python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v2176_wifi_dhcp.py
```

Flash only through the checked flash helper:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img --from-native
```

Boot image pack/unpack tools live under:

```bash
workspace/public/src/third_party/mkbootimg/
```

## Safety Invariants

- Keep TWRP and at least one known-good boot image available before live work.
- Never write `/efs`, `/sec_efs`, modem partitions, RPMB, keymaster, vbmeta, or bootloader partitions.
- Do not write proprietary firmware/vendor extracts to tracked public paths.
- Do not commit boot images, firmware, ramdisks, compiled binaries, raw logs, credentials, DHCP leases, or unredacted MAC/BSSID/IP traces.
- Use `workspace/private/` for private, large, proprietary, or generated payloads.
- Promote only redacted, small, reproducible, or metadata-only state to `docs/`, `docs/artifacts/`, or `workspace/public/`.
- For Wi-Fi tests, keep credentials in env files under `workspace/private/secrets/`; do not log PSKs.
- Do not run Wi-Fi scan/connect/DHCP/ping unless the current task explicitly asks for that bounded validation.
- Do not revisit external SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO paths for internal `wlan0` bring-up unless new evidence explicitly reopens them.

## Development Discipline

- Inspect `git status --short` before and after changes.
- Keep patches focused; do not repair unrelated historical docs unless the task is structural cleanup.
- Prefer `rg` for search and `git mv` for tracked moves.
- Use `apply_patch` for targeted edits.
- Validate touched Python with `python3 -m py_compile` where applicable.
- Run `git diff --check` before handoff or commit.
- Do not commit unless the user asks for a commit.
