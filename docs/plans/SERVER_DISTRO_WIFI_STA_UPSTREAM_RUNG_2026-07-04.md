# Server-Distro Wi-Fi STA Upstream Rung

- Date: 2026-07-04
- Status: WSTA14 blocked at Debian WLAN driver state before association
- Scope: next hardware rung after the Stage0 server-distro hardware contract.
- Device action in this doc: none.

## 0. Goal

Make the D4/D-public Debian appliance reach upstream internet through the phone radio as a
Wi-Fi station, without depending on the host USB/NCM network for public tunnel traffic.

The target flow is:

```text
native init wakes qcacld enough for wlan0
  -> switch_root to Debian
  -> Debian starts STA supplicant + DHCP from private config
  -> Debian route/tunnel uses wlan0
  -> USB NCM remains the recovery/admin path
```

This is the server-appliance rung. It is not a demo workload and it is not SoftAP
concurrency.

## 1. Ground Truth Already Proven

- V2237 proved the older Wi-Fi lineage can associate, DHCP, and externally ping on both
  bands with private credentials.
- V3342 proved the current post-GPU/server lineage can materialize `wlan0` again by using
  the mounted-vendor QCACLD firmware source route:
  `source_policy=qcacld-fwsource-mounted-vendor-first`, `wlan0_present=1`, and
  `decision=softap-iftype-probe-pass`.
- V3344 proved SoftAP/server mode, but that is a private AP transfer endpoint. It does not
  prove upstream internet for the Debian appliance.
- The Stage0 hardware contract assigns native init only the `wlan0` materialization
  responsibility. Debian owns IP config, route policy, and the public tunnel after
  handoff.

## 2. Ownership Boundary

| Surface | Native init owns | Debian owns |
| --- | --- | --- |
| `wlan0` creation | Yes: qcacld/vendor firmware/service glue. | No. Debian consumes the interface after it exists. |
| STA supplicant | No by default. Native may run bounded tests only. | Yes: long-lived station supplicant after handoff. |
| DHCP / DNS / default route | No by default. Native may run bounded tests only. | Yes: Debian applies upstream route policy. |
| USB NCM | Preserve kernel gadget and local admin route. | May use for admin, must not break recovery. |
| Public tunnel | Never. | `cloudflared` or later tunnel client, outbound-only. |

Native child processes must not silently linger across `switch_root` to own Wi-Fi. If a
temporary native Wi-Fi worker is used for a probe, it must be stopped before handoff.

## 3. Debian Rootfs Requirements

The current server-distro rootfs builder includes `iproute2` and `iputils-ping`, but not a
Debian STA client stack. The STA rung should add, source-side first:

- `wpasupplicant` for the long-lived Debian station process;
- one DHCP client path, preferably `isc-dhcp-client` for a conventional Debian userspace;
- one outbound TCP probe path, currently `netcat-openbsd`, so DHCP/default-route success
  cannot masquerade as real upstream reachability;
- a firstboot opt-in script path under `/etc/a90-dpublic/` that starts STA only when the
  operator has staged private config;
- marker fields in `/run/a90-d3-marker` for route ownership and redacted status.

Credentials must stay in private runtime/config state. Public repo artifacts may record only
booleans, redacted profile labels, return codes, and `secret_values_logged=0`.

## 4. Rung Plan

### WSTA0: design lock

This document. No device action.

### WSTA1: Debian STA client source unit

Add rootfs/client support without starting Wi-Fi by default:

- include `wpasupplicant` and one DHCP client in the rootfs builder;
- add `/usr/local/bin/a90-dpublic-wifi-sta` or an equivalent firstboot helper;
- firstboot runs it only when `/etc/a90-dpublic/wifi-sta-enable` exists and a private
  config file is present;
- output is redacted and marker-only;
- tests prove default D-public boot still does not start STA or cloudflared.

No boot image flash is required for this source unit.

### WSTA2: native materialization live gate

Build/flash the exact current native candidate through `native_init_flash.py` only if a new
boot artifact is needed. Validate below association:

- `server-distro hardware-contract` prints `next.required=wifi-sta-upstream`;
- `wifi status` or a bounded no-start probe reaches `wlan0_present=1`;
- no native STA supplicant, DHCP, ping, AP, NAT, or listener remains running;
- `selftest fail=0`.

If `wlan0` does not appear after the bounded window, stop the rung and do not continue into
Debian STA or public tunnel checks.

### WSTA3: Debian STA association + route live gate

With private operator-provided config staged into the userdata appliance:

- boot into Debian PID1;
- Debian can bring the materialized `wlan0` administratively UP;
- firstboot starts Debian `wpa_supplicant` for `wlan0`;
- `wlan0` reaches carrier/association before DHCP is treated as meaningful;
- DHCP obtains an address and DNS without logging concrete private network identifiers in
  public artifacts;
- default route for outbound internet becomes Wi-Fi while USB NCM remains reachable for
  local admin/recovery;
- marker/status proves `wifi_sta_default_route_iface=wlan0`, `ncm_recovery_preserved=1`,
  gateway ARP resolution, DNS resolution, and outbound TCP/443 reachability.

This gate is blocked, not failed, when credentials are absent.

### WSTA4/WSTA9: D-public over Wi-Fi

Only after WSTA3/WSTA7 passes:

- start the D-public smoke service locally;
- start `cloudflared` only from Debian and only when explicitly enabled;
- confirm the tunnel's outbound route is `wlan0`;
- confirm smoke response through the tunnel;
- cleanup/disable leaves no stale tunnel runtime and no secret/public URL in git.

Live result: blocked above Wi-Fi.  WSTA8 proved the no-clock Debian appliance can reach
local D-public readiness and true STA L3 pass (`wifi_sta_decision=wifi-sta-pass`, default
route on `wlan0`, gateway/DNS/TCP443 probes OK), but `cloudflared` did not obtain a
generated public quick URL.  The failure point is the device quick-tunnel API path:
`cloudflared` exits on API POST timeout, strict URL detection sees no generated public URL,
and device OpenSSL reports DNS lookup failure for `api.trycloudflare.com` while a host
control POST to the same API succeeds.  A clock-seeded attempt regressed Wi-Fi scan/association,
so do not seed or jump wall clock before Wi-Fi in this rung.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA8_DPUBLIC_TUNNEL_BLOCKED_2026-07-04.md`.

WSTA9 added a manual device-side API probe and did not start cloudflared. The probe
recorded default route on `wlan0` and two nameservers, but both the control hostname and
quick API hostname failed DNS, TCP/443 failed through `nc.openbsd`, wget POST returned
rc=4, OpenSSL POST returned rc=1, and `api_probe_decision=api-dns-failed`. A follow-up
L3 diagnostic showed the gateway neighbor had degraded and numeric external TCP failed,
so the failure is upstream STA/L3 persistence, not yet a Cloudflare-specific API bug. A
manual STA refresh then produced a latest marker segment ending in `wpa_state=DISCONNECTED`,
carrier down, and `wifi_sta_decision=wifi-sta-assoc-failed`. Device ended back on native
V3384 with `selftest fail=0`.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA9_API_PROBE_BLOCKED_2026-07-04.md`.

### WSTA10: STA/L3 persistence before tunnel retry

Do not retry cloudflared until a same-boot dwell window proves gateway, DNS, and TCP/443
remain stable after the initial `wifi-sta-pass`. Next work should add timestamped marker
phases so stale pass markers cannot mask a later disconnect, collect redacted association
state/events after firstboot, and only then decide whether a keepalive/reassociate policy
belongs in the Debian STA helper.

Live result: blocked at dwell.  WSTA10 added per-run phase markers and a six-sample
post-pass dwell gate.  The appliance reached initial L3 pass, dwell samples 1-5 stayed
good, and sample 6 failed with `wpa_state=COMPLETED`, carrier up, default route still on
`wlan0`, gateway ARP still resolved, but DNS/TCP no longer passing.  The final decision was
`wifi-sta-dwell-failed`.  Firstboot also gated the tunnel path, so cloudflared did not start
after the dwell failure.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA10_DWELL_BLOCKED_2026-07-04.md`.

### WSTA11: associated but L3 degraded

Live result: blocked at the gateway reachability boundary.  WSTA11 kept the WSTA10
sequence/dwell markers and added redacted `wpa_cli PING` plus `SIGNAL_POLL` samples during
dwell.  Samples 1-5 stayed good.  Sample 6 still had `wpa_state=COMPLETED`, `wpa_cli`
control `PING` success, carrier up, default route on `wlan0`, and gateway ARP resolved, but
gateway ping failed first; DNS then failed and TCP/443 was not attempted.  The first-failure
markers were `wifi_sta_dwell_first_fail_sample=6` and
`wifi_sta_dwell_first_fail_reason=gateway-ping`.  This narrows the blocker to associated
but gateway-degraded behavior, not raw signal loss or supplicant disconnect.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA11_SIGNAL_DWELL_BLOCKED_2026-07-04.md`.

### WSTA12: gateway reachability diagnostic

Source result: implemented.  The Debian STA helper now records gateway ping attempt count,
success count, first-success timing, total ping timing, neighbor state before/after bounded
`ip neigh get`, DHCP lease-router booleans, and default-route gateway match booleans.  It
also records bounded association retry diagnostics so a later association regression cannot
hide as a gateway problem.

Live result: blocked before gateway dwell.  Native WSTA2 materialization passed with
`wlan0_present=1`, `link_up_rc=0`, and `decision=softap-iftype-probe-pass` after the
default materialization window.  D4 guarded format/populate passed, and `switch_root` reached
Debian on retry after display-owner cleanup.  Debian then failed at association before any
gateway dwell sample.  A hot-patched helper with three bounded association attempts showed
`wpa_state=DISCONNECTED`, carrier down, and `SCAN_RESULTS` count `0` for all three attempts.
The final decision remained `wifi-sta-assoc-failed`.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA12_GATEWAY_DIAG_ASSOC_BLOCKED_2026-07-04.md`.

### WSTA13: Debian scan visibility boundary

Source result: implemented.  The Debian STA helper now records regulatory/country command
booleans and scan-visibility windows: scan trigger rc, scan-result counts, supplicant state,
operstate, and carrier for the initial scan and each bounded retry scan.

Live result: blocked below association.  Native WSTA2 materialization passed after the
default wait window (`wlan0_wait_elapsed_ms=100261`, `wlan0_present=1`, `link_up_rc=0`,
`decision=softap-iftype-probe-pass`).  D4 guarded format/populate passed, and Debian
handoff succeeded on retry after display-owner cleanup.  In Debian, every scan trigger
returned rc=0, but initial and retry scan windows all ended with `final_results_count=0`;
each scan sample also reported `operstate=down` and carrier `0`.  Manual `ip link set
wlan0 up` plus three more scans did not change the result.  Final decision:
`wifi-sta-assoc-failed`.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA13_SCAN_VISIBILITY_BLOCKED_2026-07-04.md`.

### WSTA14: Debian link-state / scan-engine boundary

Source result: implemented.  The Debian STA helper now records redacted `link_snapshot()`
state around link-up, supplicant start, country handling, scanning, reassociation, and retry
relink attempts.  The WSTA private rootfs preparer installs `iw` and records
`linkstate_diag_present` plus `iw_diag_present`.

Live result: blocked at Debian WLAN driver state.  Native WSTA2 materialization passed
(`wlan0_wait_elapsed_ms=93659`, `wlan0_present=1`, `link_up_rc=0`,
`decision=softap-iftype-probe-pass`).  In Debian, `iw` is present and sees a managed phy
(`iw_present=1`, `iw_dev_info_rc=0`, `iw_phy_present=1`, `iw_type_managed=1`), but direct
`iw` scan returns rc `234` and BSS count `0`.  `wlan0` remains administratively UP but not
RUNNING/LOWER_UP (`flags_hex=0x1003`, `flags_up=1`, `flags_running=0`,
`flags_lower_up=0`) after supplicant start, reassociation, and two bounded relink attempts.
All `wpa_cli` scan windows also end at `final_results_count=0`; final decision is
`wifi-sta-assoc-failed`.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA14_LINKSTATE_SCAN_BLOCKED_2026-07-04.md`.

### WSTA15: handoff / WLAN driver-state boundary

Source result: implemented.  The no-flash
`workspace/public/src/scripts/server-distro/run_wsta15_handoff_scan_boundary.py` runner compares
a STA-only native `wifi scan` window with a second scan window after the bounded WSTA2
AP-iftype add/delete probe.  It requires resident V3384 and stays below association, DHCP,
ping, API, and public tunnel work.

Live result: pass for the native scan boundary.  From a fresh native V3384 reboot, initial
`wifi status` had no `wlan0`.  The STA-only scan window failed three times with
`wifi-scan-link-up-failed` / `link_up_errno=19`, then attempt 4 passed with
`scan_result_count=11`.  The AP-iftype probe passed and the post-iftype scan passed
immediately with `scan_result_count=12`.  Final decision:
`wsta15-native-scan-engine-survives-iftype`; no forbidden native Wi-Fi/tunnel workers were
present and post-run selftest stayed `fail=0`.

Interpretation: WSTA15 rules out the narrow "WSTA2 AP-iftype add/delete poisons native scan"
hypothesis.  A STA-only native scan gate can materialize `wlan0` and visible BSS before
handoff.  WSTA14's Debian scan failure is therefore handoff-specific or Debian-side driver
state, not native scan invisibility.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA15_HANDOFF_SCAN_BOUNDARY_2026-07-04.md`.

### WSTA16: immediate Debian post-handoff scan boundary

Source result: implemented.  The Debian STA helper now has an
`/etc/a90-dpublic/wifi-sta-immediate-snapshot-only` mode that records link and direct `iw`
state before starting `wpa_supplicant`, DHCP, ping, API probes, or cloudflared.  The WSTA
private rootfs preparer has `--immediate-snapshot-only`, which stages the enable flag plus
snapshot-only flag without requiring or copying Wi-Fi credentials.

Live result: blocked at the immediate Debian scan boundary.  A first short native STA-only
gate was too early after boot and failed six times with `wifi-scan-link-up-failed` /
`link_up_errno=19`; the extended same-boot gate passed on attempt 5 with
`scan_result_count=11`.  `switch_root` then reached Debian PID1 with `dropbear_started=1`.
In Debian snapshot-only mode, `wlan0` was present and `ip link set wlan0 up` returned rc
`0`, but direct `iw` scan returned rc `234` and BSS count `0` both before and after link-up.
Two delayed manual Debian scans returned the same `Invalid argument (-22)` error and BSS
count `0`.  Final decision: `wifi-sta-immediate-snapshot-scan-failed`; the tunnel gate
stayed closed; device returned to native V3384 with `selftest fail=0`.

Interpretation: native can materialize `wlan0` and visible BSS before handoff, but the
Debian image loses or lacks scan-usable WLAN state immediately after handoff.  The blocker
is below credentials, supplicant association, DHCP, gateway, API, and tunnel work.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA16_IMMEDIATE_HANDOFF_SCAN_BLOCKED_2026-07-04.md`.

### WSTA7: Debian association/control fix

Live result: pass.  The Debian STA helper now waits for the `wpa_supplicant` control
socket and sends the native-good control sequence (`DRIVER COUNTRY KR`, scan,
enable/select network, reassociate) before waiting for carrier and DHCP.  A fresh
WSTA7 userdata appliance reached carrier, DHCP, default route on `wlan0`, gateway ARP,
DNS, and TCP/443 with `wifi_sta_decision=wifi-sta-pass`.

Operational constraint discovered live: after a stale `flags=0x1002` state, `wifi cleanup`
alone did not recover Debian handoff readiness.  A fresh native reboot followed by the
WSTA2 iftype-probe gate did.  Therefore WSTA8 must start from:

```text
fresh native boot -> WSTA2 materialization gate -> require wlan0_admin_up=true -> switch_root
```

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA7_WPA_CLI_ASSOC_PASS_2026-07-04.md`.

## 5. Stop Conditions

Stop before mutation or public exposure if any condition appears:

- rollback images or recovery/TWRP preconditions are missing before a flash;
- `wlan0` does not materialize in the bounded native gate;
- Debian cannot bring the materialized `wlan0` link UP after handoff;
- Debian starts `wpa_supplicant` but `wlan0` never reaches carrier;
- Debian STA tooling is missing from the rootfs;
- private credentials are absent for an association gate;
- USB NCM admin/recovery is lost;
- any path requires modem/cellular, PMIC/regulator/GDSC/GPIO/backlight writes, inbound public
  ports, NAT export, or SoftAP+STA concurrency.

## 6. Explicit Non-Goals

- Do not reopen modem/cellular upstream.
- Do not require SoftAP+STA concurrency for the server appliance.
- Do not make Wi-Fi a hard blocker for local USB/NCM recovery or userdata handoff.
- Do not start public exposure from native init.
- Do not commit SSID, PSK, BSSID, MAC, DHCP lease, concrete private IP, or public tunnel URL.

## 7. Next Implementation Unit

Run WSTA17 as a Debian post-handoff WLAN reset/materialization gate below credentials:

1. keep the fresh native boot -> extended STA-only native scan gate -> SD-backed Debian `switch_root`
   sequence from WSTA16;
2. require native visible BSS before handoff;
3. collect redacted post-handoff rfkill, phy, netdev, nl80211, and link-state snapshots before
   supplicant starts;
4. test bounded Debian-side materialization branches, such as link down/up, managed-type reassertion
   if available, and safe phy/netdev rescan triggers;
5. run direct `iw` scan after each bounded branch and stop as soon as one branch gets visible BSS;
6. do not run credentials, association, DHCP, API, or cloudflared until direct Debian scan works.
