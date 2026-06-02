# REDIRECT — wlan0 lives on the INTERNAL modem WLAN PD, not esoc0; first gate = firmware-serve verification (2026-06-02)

**Out-of-band host review + cross-validation. Read this before designing the next
live cycle. It supersedes the esoc0/MDM2AP contracts** (`ESOC_NATURAL_PATH_*`,
`ESOC_ANDROID_NATIVE_POWER_DIFF_*`, `ESOC_PON_SOURCE_*`, `ESOC_DTB_PARITY_*`) **as
the active track.** Those remain valid as the proof that the *external* SDX50M
modem is a hardware wall — but that wall is on the wrong subsystem for wlan0.

## The reframe (triple-confirmed)

There are TWO separate modems on this board, and ~800 cycles (V844→V1657) debugged
the wrong one for the wlan0 goal:

- **Internal modem (subsys0 / mss)** = host of `msm/modem/wlan_pd`. WLAN firmware
  `wlanmdsp.mbn` is sideloaded onto this modem's DSP as a protection domain. **This
  is where wlan0 comes from.**
- **External SDX50M (subsys9 / esoc0 / mdm3)** = a separate PCIe 5G modem. All the
  `mdm_subsys_powerup` / MDM2AP / GPIO135-142 / RC1 / PON work is here. **wlan0
  does not route through it.**

Evidence (three independent lines, all agree):

1. **Project's own timing** falsifies esoc0-as-WLFW-prerequisite:
   - V620: Android `wlan_pd → esoc0 = 2153 ms` (wlan_pd UP ~2 s *before* esoc0).
   - V1331: `wlfw_start = 8.396 s`, `__subsystem_get(esoc0) = 8.449 s` — WLFW
     starts ~53 ms *before* esoc0.
   - V1332 recorded this as PASS, then the track kept chasing esoc0 anyway.
   - Trace `pil_modem = 8, pil_esoc_or_sdx = 0`: WLAN firmware loads on the
     internal modem PIL, zero esoc/sdx PIL in the WLAN window.
   - V844's pivot was correlation-not-causation ("mss ONLINE + mdm3 OFFLINING +
     no WLFW ⇒ mdm3 gates WLFW"), contradicting V620.

2. **Mainline Linux architecture** (ath10k/WCN3990, postmarketOS, ICNSS source)
   independently confirms the model:
   - `wlanmdsp.mbn` is "sideloaded to the modem DSP via TQFTPserv"; must sit in
     the same directory as the modem firmware.
   - Load infra = **pd-mapper + tqftpserv + rmtfs** — exactly native's companion
     stack (`qrtr-ns → pd-mapper → rmt_storage → tftp_server`).
   - ICNSS talks to WLFW over QMI and listens to WLAN-PD restart notifications;
     readiness = QMI server arrive → `wlfw_msa_mem_info_send_sync` →
     `wlfw_msa_ready_send_sync` → `fw_ready_ind`.
   - The `wlanmdsp.mbn` + ICNSS + SNOC/PLD signature is **WCN3990-class integrated
     WLAN**, not PCIe QCA6390. The "QCA6390" label in CLAUDE.md is misleading.

3. **Native evidence fits the corrected model exactly**:
   - V829: domain list returns `msm/modem/wlan_pd` ⇒ pd-mapper *does* publish the
     domain. The load-infra registration layer is OK.
   - V830/V831: `wlan_pd` state stays UNINIT (`0x7fffffff`) ⇒ the domain is known
     but the modem never *started* the WLAN PD image.
   - V751/V752: native QCACLD/HDD reaches `qcwlanstate` but never gets
     ICNSS-QMI / FW-ready ⇒ no WLFW service 69 ⇒ ICNSS waits forever.
   - **V1586 got furthest on the right track**: firmware-overlay + PM route
     reached "modem: Brought out of reset" + `wlfw_progress=True`.

## Corrected goal path (the whole problem reduces to one gate)

```
1. mss (internal modem) ONLINE                       ← native ✓ (V1586)
2. tqftpserv serves wlanmdsp.mbn to the modem        ← ??? UNVERIFIED
3. modem starts WLAN PD → WLFW service 69 publishes  ← ★ THE blocker (wlan_pd UNINIT)
4. ICNSS: QMI server arrive → MSA mem sync →
   MSA ready → fw_ready → BDF(bdwlan/regdb) → wlan0  ← mainline, follows automatically
```

Native already knows WLFW service 69 never publishes (wlan_pd UNINIT). That
localizes the stall to **at/before step 3 = the firmware-serve cluster (A/B/D)**.
MSA (step 4 / "C") is downstream of WLFW and is NOT the current blocker — do not
investigate it until service 69 appears (that would repeat the
debug-below-the-wall failure mode).

## THE GATE — read-only firmware-serve verification (one run)

### Trigger — internal-modem natural path ONLY (reuse V1586 route)
Bring up mss the way V1586 already does: firmware-mount overlay (read-only) +
`subsys_modem` holder + the companion stack
`qrtr-ns → pd-mapper → rmt_storage → tftp_server → cnss_diag → cnss-daemon`.

**Forbidden as trigger or anywhere in the window** (all of these are the *external*
modem / contaminating paths): `/dev/subsys_esoc0` open, `mdm_helper`/`ks` eSoC
contract, forced RC1 enumerate (`rc_sel`/`case`/`debug/enumerate`), fake-ONLINE
system-info spoof, eSoC notify/`BOOT_DONE`, PMIC/GPIO/GDSC writes, global PCI
rescan, platform bind/unbind.

### Measure — one window, read-only. Resolve A/B/D together.
1. **(B) tqftpserv serving activity.** Capture the `tftp_server`/tqftpserv child's
   stdout/stderr (reuse the helper `--result-output-path` / child-output capture
   from V1568/V1588). Mainline says: "check tqftpserv messages in syslog." Record
   every filename it is asked for and whether it answered — especially any request
   for `wlanmdsp.mbn` / `modem*` during the modem-PD-load window.
2. **(A) firmware path parity.** Snapshot the directory tqftpserv serves from (and
   the firmware mount path the modem reads). Record presence + size of
   `wlanmdsp.mbn`, `modem.mdt`, `modem.b0x`/`modem.mbn`. Cross-check against the
   sda29 vendor firmware set (read-only) — is wlanmdsp.mbn actually *visible at the
   served path*, not just present on sda29? (Prior evidence: "wlanmdsp hits: 0",
   "modem.mdt = False".)
3. **(downstream discriminator, expected absent) WLFW service 69 + wlan_pd state.**
   Reuse the helper QRTR nameservice readback (v125+) for service `69` and the
   `wlan_pd` listener (V830/V831). Expected: still UNINIT / 69 absent — this
   confirms the stall is at PD load, not downstream.
4. **(context) dmesg**: `Brought out of reset`, pil modem markers, any
   tqftpserv/rmtfs/qmi error lines.

This run **observes only** — it does NOT move/remount/rewrite firmware. If a file
is missing at the served path, that is a *finding to hand back*, not to fix in-run.

### Labels (fixed — one run sets one)
- `firmware-not-requested`: no modem TFTP/QRTR request for `wlanmdsp.mbn`/modem
  firmware in the window ⇒ the modem PIL never reached the PD-load stage (upstream:
  modem.mdt / full-image / modem not actually fully booted) ⇒ hand back; next gate
  is modem-image/PIL, not firmware path.
- `firmware-requested-but-absent-at-served-path`: tqftpserv is asked for the file
  but it is missing/zero at the served path (the "wlanmdsp hits: 0" case) ⇒
  **concrete fixable target = firmware path/mount parity** ⇒ hand back to design a
  bounded read-only-identified mount-fix gate.
- `firmware-served-pd-still-uninit`: tqftpserv served `wlanmdsp.mbn` (request seen +
  file present + answered) yet wlan_pd stays UNINIT / no WLFW 69 ⇒ blocker is
  modem-side PD start (signing / MSA prerequisite / PD-mapper domain start) ⇒ hand
  back; THEN MSA (C) becomes the next legitimate gate.
- `tqftpserv-not-running`: the daemon didn't start/stay up ⇒ route regression, fix
  the companion route, not the modem.

Transport loss or failed rollback = FAIL, not a result.

## Discipline (do NOT repeat V1370–V1559 / V1616–V1630)
ONE run sets the label. Do not spin window/timing variants. No autonomous fix from
any label — `firmware-requested-but-absent-at-served-path` hands back to the user
for an explicit bounded mount-fix gate. Do not enter MSA (C) until WLFW 69 appears.
Do not return to esoc0/MDM2AP/RC1 — that track is closed for the wlan0 goal.

## Hard stops (unchanged)
Read-only. No firmware/partition writes, no remount-writes (observe what is mounted/
served only), sda29 read-only, no esoc0/subsys_esoc0 trigger, no forced RC1/case
writes, no fake-ONLINE, no eSoC notify/`BOOT_DONE`, no PMIC/GPIO/GDSC writes, no
global PCI rescan, no platform bind/unbind, no Wi-Fi HAL/scan/connect, no
credentials, no DHCP/routes, no external ping. Only the approved test-boot↔v724
rollback; verify selftest `fail=0` after.

## Refs
V1586 (furthest-progress firmware-overlay route: "modem brought out of reset" +
wlfw_progress), V829 (pd-mapper publishes wlan_pd), V830/V831 (wlan_pd UNINIT),
V751/V752 (HDD init, no ICNSS-QMI/FW-ready), V620/V1331/V1332 (wlfw before esoc0),
V784/V785 (memshare/CMA = MSA context, deferred to step 4). External:
ath10k/WCN3990 + postmarketOS SDM845 (wlanmdsp sideload via tqftpserv; pd-mapper +
tqftpserv + rmtfs), ICNSS `icnss_qmi.c` (WLFW QMI / MSA / WLAN-PD notif).
