# S22+ RF-sensing side-track candidates (UWB CIR / Wi-Fi CFR)

Date: 2026-11-21
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` (with A90 and S20+ as possible
auxiliary nodes)
Baseline: `S906NKSS7FYG8`
Status: idea memo only. It selects no goal and authorizes no device action.
Starting UWB or Wi-Fi radio activity is a device action under
[AGENTS.md](../../AGENTS.md) and would need its own goal, target lane and
approval. The modem goal's no-RF-transmission boundary is unchanged.

Related: [security side-track candidates](S22PLUS_FYG8_SECURITY_SIDE_TRACK_CANDIDATES_2026-09-16.md)
(Candidate E: Wi-Fi/network-facing components) and the
[post-2025-08 CVE backlog](S22PLUS_FYG8_POST_2025_08_SECURITY_BACKLOG_2026-09-16.md).
Open question 1 below reads the same WLAN host driver binary, so either track's
extraction serves both.

## Idea

Phone radios produce channel measurements that normal APIs discard. Those
measurements describe the multipath around the device. Read as data, they act
as a coarse radar-like sensor: presence, motion, respiration-scale phase
change. They do not form images.

- **UWB CIR** (channel impulse response, time domain). About 500 MHz of
  bandwidth gives about 30 cm range bins (c / 2B). It answers "where".
- **Wi-Fi CSI / CFR** (per-subcarrier amplitude and phase, frequency domain).
  20–160 MHz gives about 1–7.5 m range resolution, so it relies on change over
  many packets (phase, Doppler) and MIMO. It answers "how it moves". Prior art
  includes Intel 5300 CSI Tool, Atheros CSI Tool, Nexmon CSI, ESP32, CMU
  "DensePose from WiFi", and the IEEE 802.11bf WLAN sensing work.
- CIR and CFR are a Fourier pair. The practical difference is bandwidth and
  how accessible each one is.

### Accuracy model (qualitative; no numbers claimed)

- **Fusing UWB and Wi-Fi on one device** helps with activity and pose, and with
  wide-area presence. It helps little with ranging, where UWB alone is already
  strong. Errors stay partly correlated because both radios see the same
  multipath from the same position.
- **Multiple devices at different positions** usually give the largest gain.
  One range is a ring, two give an intersection, three or more give a point.
  They also reduce occlusion, and their multipath views are less correlated.
  Placement (GDOP) matters more than device count, and returns diminish after
  about 3–4 well-placed nodes. Costs:
  - Inter-device sync: UWB ranging solves clock offset. Wi-Fi CSI phase is not
    coherent across devices because of CFO/SFO, so use amplitude or
    intra-device antenna phase differences.
  - Each node's position must be calibrated.
  - Nodes must schedule airtime.
- **Practical topology:** the S22+ is the CFR receiver. The other phones only
  transmit ordinary Wi-Fi frames, which gives bistatic illumination from
  several directions. CFR support is needed only on the receiver.

### Single-device constraints

- UWB channel 5 (about 6.24–6.74 GHz) lies inside the Wi-Fi 6E 6 GHz band, so
  the phone likely time-multiplexes the two radios through coexistence control
  (mechanism unverified). That limits truly simultaneous capture.
- The UWB chip clock and the Wi-Fi chip clock are separate. Aligning CIR and
  CFR timestamps is its own task.

## Evidence already in hand (static, H0)

| Fact | Source | Status |
|---|---|---|
| UWB driver `uwb.ko` (84,816 B, sha256 `9ecc58a0…7c8c`) in FYG8 vendor modules | `docs/module-map/s22plus-fyg8/inventory.tsv` | verified |
| UWB framework packages `com.android.uwb.resources` and `com.samsung.android.uwb.resources.mccmncregulation` (per-MCC/MNC regulation table implied) | `docs/reports/S22PLUS_SYSTEM_APP_EXTRA_DEBLOAT_2026-07-06.md` | verified (name only) |
| UWB controller is NXP SR100. `CONFIG_UWB_SR100=y`, built into `uwb.ko` with `CONFIG_SAMSUNG_UWB=m`. A Qorvo QM35 driver also exists in Kconfig but is not enabled | FYG8 kernel source `drivers/uwb/{Kconfig,Makefile}` | verified in source; shipped binary not cross-checked |
| `sr100.c` is a thin SPI misc-device pipe for UCI frames (4,200 B buffers, 16 MHz SPI; ioctls `SET_PWR`, `SET_DBG`, `SET_FWD`, `ESE_RESET`, …). CIR generation and export are firmware/HAL concerns, not kernel ones | FYG8 kernel source `drivers/uwb/sr100.{c,h}` | verified in source |
| Qualcomm `qcacld-3.0` has CFR capture. `configs/default_defconfig` sets `CONFIG_WLAN_CFR_ENABLE := y` and `CONFIG_WLAN_ENH_CFR_ENABLE := y` in the `CONFIG_CNSS_QCA6490` and `CONFIG_CNSS_KIWI` branches | FYG8 vendor source `vendor/qcom/opensource/wlan/qcacld-3.0` | verified in source |
| No CFR entries in that tree's `qca6390_defconfig` / `adrastea_defconfig` or in the QCA6390 branch of `default_defconfig` | same | verified for this source version only |

## Open questions (all H0-startable)

1. Does the shipped FYG8 WLAN module (`qca_cld3*`) actually contain CFR code,
   such as symbols, strings or the vendor nl80211 CFR command path? This
   decides whether CFR is alive in the product build rather than only in
   source defaults.
   - Checked 2026-11-22: no WLAN host driver in either FYG8 module inventory
     (`docs/module-map/s22plus-fyg8{,-super}/inventory.tsv`). Only
     `rmnet_wlan.ko` and `wlan_firmware_service.ko` appear.
   - It likely ships in the vendor partition. A hash-bound FYG8 `vendor.img`
     exists on the external lab disk (see the security side-track memo's
     2026-11-22 update), so no re-extraction is needed.
2. Is the S22+ Wi-Fi chip QCA6490 or Kiwi? The waipio DT references both.
3. What does the userspace path to enable peer CFR capture look like, and where
   is data delivered (relayfs/debugfs, netlink)? Recalled, not verified.
4. Does the stock UWB HAL or the SR100 firmware expose CIR, for example through
   a debug-log config, vendor UCI notifications or test mode? Search the stock
   vendor partition for the HAL binary and firmware blob, then list
   CIR/debug/test strings and UCI vendor GIDs.
5. What do Samsung `uwb_logger` and the `SET_DBG` ioctl record?
6. Auxiliary nodes:
   - Confirm the S20+ Wi-Fi chip (believed QCA6390) and the A90 WCN3990
     mapping, each against its own stock driver version.
   - S20+ and A90 have no UWB (S20+ belief: Samsung UWB started with the
     Note20 Ultra). Multi-node UWB would need a partner device such as a
     SmartTag+.

## Boundaries

- Sense only the operator's own space, between the operator's own devices.
  Wi-Fi sensing can detect people through walls, which is a privacy hazard.
- Stock radios in stock modes on approved channels only. No firmware
  modification, no regulation-table changes, no signature or access-control
  bypass.
- This memo stays secondary to the active S22+ mainline and modem goals.
