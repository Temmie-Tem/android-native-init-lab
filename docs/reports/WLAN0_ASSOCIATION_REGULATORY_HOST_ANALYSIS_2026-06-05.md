# wlan0 Association Failure — Regulatory/Country Host Analysis (2026-06-05)

Host-only OSRC source analysis. No device command, no loop interaction.
Source tree: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0`.

## Trigger

V2152 was the first native connect that actually executed (staging bug from
V2150 fixed: all b64 chunks rc 0, `helper_rc=0`, `helper_stage_ok=True`).
Result: `connect-dhcp-ping-association-failed`,
`association_carrier=False errno=110` (ETIMEDOUT), DHCP/ping never reached,
pre/post flags `0x1002` (no carrier). Target SSID is a 5GHz network
(`...5G`). Scan works (V2148/V2151: 13 BSS); association times out.

## Live follow-up: direct country ioctl + 2.4GHz test

The source-only hypothesis was tested live in V2152 follow-up runs:

- `5g-kr-country`: direct Android driver ioctl path
  `SIOCDEVPRIVATE+1` / `COUNTRY KR` returned `rc=0`, but
  `GETCOUNTRYREV` still read back `US`. Association still timed out
  (`association_carrier=False errno=110`); DHCP/ping did not run.
- `2g-kr-country`: same direct ioctl result (`rc=0`, readback `US`) and the
  same association timeout. This rules out a pure "5GHz NO-IR only" explanation
  for the current native connect failure.
- In both runs, `wpa_supplicant` stayed alive until cleanup, but no control
  socket appeared (`wpa_ctrl.ready=0`, `errno=111`) and the filtered dmesg had
  no visible auth/assoc attempt before carrier timeout.

Updated read: regulatory country is still wrong for native (`US`, not the
requested `KR`), but the identical 2.4GHz failure shows the active association
path itself also needs instrumentation or repair. Do not keep treating 5GHz
NO-IR as the sole remaining blocker.

## Root cause (source-proven): driver is in WORLD regdomain, country never set

### 1. Default country code is empty
`components/mlme/dispatcher/inc/cfg_mlme_reg.h` — `CFG_COUNTRY_CODE` default = `""`:
```
#define CFG_COUNTRY_CODE CFG_STRING("country_code", 0, CFG_COUNTRY_CODE_LEN, "", "country code")
```
With no country, qcacld falls back to the **world regdomain**
(`hdd_world_regrules_*` tables in `core/hdd/src/wlan_hdd_regulatory.c`).
World regdomain on 5GHz = DFS / **NO-IR (passive-only)** on most channels.
→ scan (passive RX) succeeds, **active association TX is blocked** → errno 110.
Symptom matches exactly.

### 2. It will NOT self-heal from beacons
`CFG_ENABLE_11D_IN_WORLD_MODE` default = **0** (disabled):
```
#define CFG_ENABLE_11D_IN_WORLD_MODE CFG_INI_BOOL("enable_11d_in_world_mode", 0, ...)
```
So 802.11d country-IE learning is OFF in world mode → the device will not
adopt KR from neighboring beacons. It stays stuck in world. Explicit country
is required.

### 3. THE TRAP: plain userspace reg hints are silently dropped
`hdd_reg_notifier()` (the `LINUX_VERSION >= 4.4.0` branch — this is a 4.14
kernel) only honors a user reg hint if it is **CELL_BASE**:
```c
case NL80211_REGDOM_SET_BY_USER:
    if (request->user_reg_hint_type != NL80211_USER_REG_HINT_CELL_BASE)
        return;                 /* plain HINT_USER → dropped, no country set */
    ucfg_reg_set_country(hdd_ctx->pdev, country);
```
Consequences — **do NOT waste cycles on these, they will be ignored:**
- ❌ `iw reg set KR` (sends `NL80211_USER_REG_HINT_USER`) → dropped.
- ❌ `wpa_supplicant country=KR` (also a plain USER hint via cfg80211) → dropped.

(Our V2152 supplicant conf has no `country=` and `update_config=0` anyway —
but even adding it would not have worked because of this gate.)

## Working levers (source-proven), in order of preference

The kernel-internal programming path is
`hdd_reg_set_country() → ucfg_reg_set_country()` (regulatory.c:732/745). It is
reachable from userspace via paths that **bypass** the `hdd_reg_notifier`
CELL_BASE gate:

- **(A) PRIMARY — wpa_supplicant `DRIVER COUNTRY KR` command.** `drv_cmd_country`
  (`wlan_hdd_ioctl.c:3408`) is bound to both the `"COUNTRY"` and `"SETCOUNTRYREV"`
  driver private commands (`wlan_hdd_ioctl.c:8170-8171`) and calls
  `hdd_reg_set_country() → ucfg_reg_set_country()` directly, bypassing the
  notifier CELL_BASE gate entirely. Works in offload and non-offload modes.
  **We already start wpa_supplicant in the connect test**, so this is the
  cheapest lever: issue `wpa_cli -i wlan0 -p <ctrl> driver COUNTRY KR` (or the
  control-socket `DRIVER COUNTRY KR`) right after supplicant comes up, before
  association. Equivalent: wext private `SETCOUNTRYREV` ioctl from our helper.
- **(B) INI `country_code=KR`** in `WCNSS_qcom_cfg.ini` — **we are the INI
  supplier** via the firmware_class feeder (V2137), so this is fully in our
  control. Programmed at startup. CAVEAT: at init,
  `ucfg_reg_program_default_cc()` is only called
  `if (!ucfg_reg_is_regdb_offloaded(psoc))` (main.c:13061). If regdb is
  offloaded (likely on WCN3990 with regdb.bin), the init default-cc path is
  skipped and country must go through `ucfg_reg_set_country` (the WMI
  init-country command). So (B) alone may be insufficient under offload —
  pair with (A) or verify offload state first. Still a useful belt-and-braces.
- **(C) CELL_BASE nl80211 hint — UNRELIABLE here, deprioritized.** The
  notifier branch that would honor it sets `wiphy->features |=
  NL80211_FEATURE_CELL_BASE_REG_HINTS` only under
  `#if defined CFG80211_USER_HINT_CELL_BASE_SELF_MANAGED || ...`
  (regulatory.c:1489), and kernel docs note CELL_BASE also depends on
  `CONFIG_CFG80211_CERTIFICATION_ONUS`. Both are uncertain on this build, so do
  not rely on (C). Use (A).

## Android side (where Samsung normally gets country)

- `macloader` reads only `/mnt/vendor/efs/wifi/.mac.info` (MAC, not country) —
  confirmed in strings; country is NOT macloader's job.
- On stock, country arrives via the **telephony/framework CELL_BASE reg hint**
  or a framework property → neither runs in native context, which is exactly
  why native stays in world regdomain.
- Further Android-reversing value is low here: the source already names the
  mechanism. Only worth a strings pass on the Wi-Fi HAL / cnss-daemon if (A)/(B)
  both fail and we need the exact property/cmd Samsung uses.

## Updated recommendation

The original host-only recommendation was necessary but not sufficient:
native did not program the requested country through the direct driver ioctl,
and the 2.4GHz test failed the same way as 5GHz.

Next live unit:
1. Add redacted `wpa_supplicant`/driver association telemetry for the connect
   window, because current dmesg shows link-up but no auth/assoc edge.
2. Classify why `COUNTRY KR` returns success while `GETCOUNTRYREV` remains
   `US` (regdb offload / async WMI programming / Samsung policy override).
3. If the control socket is required for Samsung's connect path, create the
   same init-provided socket/ctrl surface Android uses instead of relying on a
   best-effort private `ctrl_interface` directory.

Avoid `iw reg set` and supplicant `country=` — proven no-ops here.

If (A) does not move the regdomain, classify regdb offload state
(`ucfg_reg_is_regdb_offloaded`) from dmesg/icnss evidence and route country via
the WMI init-country path / lever (C), not more userspace reg hints.
