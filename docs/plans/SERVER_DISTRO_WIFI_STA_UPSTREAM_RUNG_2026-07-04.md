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

### WSTA17: Debian post-handoff materialization boundary

Source result: implemented.  Snapshot-only mode now records redacted rfkill/phy/proc-wireless
state and runs bounded materialization branches below credentials: `link-cycle`,
`managed-reassert`, and `rfkill-unblock`.  A scan pass requires direct `iw` scan rc `0` and
BSS count `>0`.

Live result: blocked.  Native STA-only scan passed on attempt 11 with `scan_result_count=11`,
and `switch_root` reached Debian PID1.  Debian immediate state had `wlan0_present=1`, WLAN
rfkill unblocked, one phy, and a `/proc/net/wireless` row, but direct `iw` scan returned rc
`234`.  The link-cycle branch brought the interface down but could not bring it back up:
`ip link set wlan0 up` returned rc `2`, manually confirmed as `RTNETLINK answers: Invalid
argument`.  Direct scan then returned rc `156` / `Network is down (-100)`.  Reasserting
managed type succeeded but did not restore link-up; rfkill CLI was absent and sysfs rfkill
was already unblocked.  Final decision: `wifi-sta-handoff-materialization-scan-failed`;
device returned to native V3384 with `selftest fail=0`.

Interpretation: this is below credentials and below supplicant.  The preserved netdev/phy is
visible, but direct Debian ownership cannot produce a usable scan state, and toggling the link
down loses the ability to bring it up again.  The next boundary is the handoff control plane:
which WLAN companion processes/state survive `switch_root`, and what kernel error appears at
the first scan/up failure.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA17_HANDOFF_MATERIALIZATION_BLOCKED_2026-07-04.md`.

### WSTA18: handoff control-plane boundary

Source result: none.  WSTA18 was a report-only live diagnostic using the WSTA16
link-down-free snapshot image copied into a private WSTA18 run.

Live result: blocked at the WLAN control-plane boundary.  Native STA-only scan passed on
attempt 11 with `scan_result_count=10`.  Native focused dmesg showed `cnss_diag` and
`cnss-daemon` cld80211 netlink activity plus WLAN firmware/driver ready before handoff.
After `switch_root`, Debian still had `wlan0`, phy/rfkill, and `ip link set wlan0 up`
returned rc `0`, but direct `iw scan` returned rc `234` / `Invalid argument (-22)`.  The
Debian process snapshot lacked the native vendor WLAN userspace (`cnss-daemon`, `cnss_diag`,
and related Android/vendor companions); dmesg showed `firmware down indication`,
`PD service down ... Root PD shutdown`, and repeated `WMI stop in progress`.  Device
returned to native V3384 with `selftest fail=0`.

Interpretation: direct Debian netdev ownership is the wrong immediate target.  The kernel
objects survive enough to show `wlan0`, but the WCNSS/WMI control plane is down after full
PID1 handoff.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md`.

### WSTA19: native-owned chroot Wi-Fi boundary

Source result: added `run_wsta19_native_owned_chroot_wifi.py` plus focused tests.  The
runner keeps native PID1 alive, uses the WSTA2 materialization preflight when `wlan0` is not
admin-up, mounts the SD-backed Debian image as a chroot, starts temporary key-only `dropbear`,
proves SSH into Debian over USB/NCM, and runs native `wifi scan` while the chroot is active.

Live result: pass after a fresh native reboot.  A first same-boot attempt blocked before the
chroot at the known stale `flags=0x1002` / `SIOCSIFFLAGS EINVAL` state, and a same-boot
WSTA2 iftype-probe also failed.  The final pass used the reliable sequence:

```text
fresh native V3384 boot
  -> WSTA2 materialization preflight
  -> native scan
  -> SD image SHA restage if needed
  -> Debian chroot dropbear SSH
  -> native scan while chroot is active
  -> cleanup and final selftest
```

Key live markers:

```text
materialization: wlan0_wait_elapsed_ms=69042 link_up_rc=0 decision=softap-iftype-probe-pass
native_pre_chroot_scan: decision=wifi-scan-pass scan_result_count=9
ssh: A90D2_SSH_MARKER debian_version=12.14 stage_marker=present
native_during_chroot_scan: decision=wifi-scan-pass scan_result_count=11
cleanup_postcheck: mount_absent=1 loop_node_absent=1 dropbear_absent=1
final: V3384 selftest fail=0
```

Interpretation: the chroot ownership model preserves the vendor WLAN control plane that full
`switch_root` lost in WSTA18.  Debian can run as a service consumer while native init keeps
Wi-Fi ownership.  This validates the practical direction for a Wi-Fi-enabled appliance:
native-owned scan/connect/status service boundary first; direct Debian raw WLAN ownership only
after a separate control-plane preservation/relaunch design.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md`.

### WSTA20/WSTA21: Native-Owned Service Boundary and Debian Client

WSTA20 live result: pass.  Native init now exposes `wifi service [status|start|stop|once] <dir>`
as a bounded file request/response boundary.  Debian/chroot consumers write `seq` plus
`op=status|scan`; native init writes redacted responses with `owner=native-init`.  The live gate
flashed V3385 through the checked helper, ran WSTA2 materialization, mounted the Debian chroot,
wrote status/scan requests from Debian, and verified native-owned responses.  No association,
DHCP, ping, public tunnel, userdata, or `switch_root` action ran.

WSTA21 source result: pass.  `/usr/local/bin/a90-native-wifi-service-client` is now the Debian-side
consumer for that file protocol.  It publishes atomic status/scan requests, waits for matching
responses, checks the native service version/owner, allowlists printed response keys, and denies
connect/association/DHCP/ping/public-tunnel operations before writing any request.  Both the WSTA3
private-rootfs preparer and base Debian rootfs builder stage it.

Reports:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA20_NATIVE_SERVICE_BOUNDARY_PASS_2026-07-04.md`,
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA21_NATIVE_SERVICE_CLIENT_SOURCE_2026-07-04.md`.

### WSTA22: Debian Client Live Gate

Live result: pass.  The WSTA21 helper now works from inside the Debian chroot against the
native-owned WSTA20 service.  The passing run used resident V3385 without a boot flash, verified
native scan readiness first, mounted the SD-backed Debian chroot, temporarily staged
`/usr/local/bin/a90-native-wifi-service-client`, started native `wifi service`, and executed helper
`status` and `scan` from Debian.  Status and scan both returned
`native-wifi-service-client-pass`; scan returned `wifi-scan-pass` with redacted results and BSS
visibility.  Helper staging, service, chroot, loop, and dropbear cleanup passed; final V3385
`selftest fail=0`.

Operational finding: stale same-boot WLAN state can leave `wlan0` admin-up but make native scan and
iftype add fail with `EINVAL`.  WSTA22 now gates on native scan readiness and can perform one bounded
native reboot recovery before chroot/service work.

Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA22_NATIVE_SERVICE_CLIENT_LIVE_PASS_2026-07-04.md`.

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

### WSTA23: Native Uplink Service Boundary

WSTA23 source/build result: pass.  The selected path is a separate native-owned uplink service,
not a mechanical extension of the WSTA20 status/scan service.

Native init now exposes `wifi uplink-service [status|start|stop|once] <dir>` with version
`a90-native-wifi-uplink-service-v1`.  The service uses the same bounded file request/response
shape but has a distinct command, version string, and safety vocabulary.  It supports:

- `op=status`: observe current WLAN/default-route/autoconnect readiness without starting connect
  or DHCP.
- `op=autoconnect`: run the existing native autoconnect/profile path only when the request includes
  `confirm=A90_NATIVE_UPLINK_AUTOCONNECT_V1`.

The no-confirm path returns `wifi-uplink-service-confirm-required` before any connect attempt.
Public tunnel and external ping execution are denied.  Credential-bearing operations are reported as
`credentials=private-config-gated`, and responses preserve `secret_values_logged=0`.

V3386 built as `A90 Linux init 0.11.142 (v3386-wifi-uplink-service-boundary)`, boot SHA
`9c097e55a2cf1f371ebba581378eeeb058c192147cdf6964d1c6721c7350a55a`, helper SHA
`fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`.  No device flash,
association, DHCP, ping, public exposure, userdata, or switch-root action ran in this source unit.
Report: `docs/reports/NATIVE_INIT_V3386_WIFI_UPLINK_SERVICE_BOUNDARY_SOURCE_BUILD_2026-07-04.md`.

V3386 live precheck and flash passed, but the first status response exposed a profile label value.
No secret file contents, association, DHCP, ping, or public exposure ran, and the temporary service
was stopped.  WSTA23 therefore adds V3387 as a redaction fix before completing the live gate:
profile label values are replaced with `autoconnect_profile_present`, `config_profile_present`, and
`requested_profile_present` booleans.  V3387 built as `A90 Linux init 0.11.143
(v3387-wifi-uplink-service-redacted)`, boot SHA
`ebebf4384f408c5cd20630b12cfd94d56d4d484664612b692de986fdecf6da5d`, helper SHA
`fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`.  Report:
`docs/reports/NATIVE_INIT_V3387_WIFI_UPLINK_SERVICE_REDACTED_SOURCE_BUILD_2026-07-04.md`.

## 7. Next Implementation Unit

WSTA23 live non-credential gate, revised to use V3387:

1. Flash V3387 through `native_init_flash.py` after normal rollback/recovery prechecks.
2. Health-check `version`, `status`, and `selftest`.
3. Start `wifi uplink-service` in a chroot-visible temp directory.
4. Prove `op=status` returns `owner=native-init`, `version=a90-native-wifi-uplink-service-v1`,
   redacted status fields, profile-present booleans rather than profile label values, and no
   connect/DHCP/public exposure.
5. Prove `op=autoconnect` without `confirm=A90_NATIVE_UPLINK_AUTOCONNECT_V1` returns
   `wifi-uplink-service-confirm-required` and does not create a connect/DHCP side effect.
6. Stop service, cleanup, and finish with `selftest fail=0`.

Full autoconnect/DHCP remains a separate credential-gated live unit.  Do not run association, DHCP,
ping, or public tunnel work in the no-confirm live gate.

WSTA23 live result: pass on V3387.  Flash/readback matched
`ebebf4384f408c5cd20630b12cfd94d56d4d484664612b692de986fdecf6da5d`, post-boot health passed, the
status response emitted only profile-present booleans, no-confirm autoconnect returned
`wifi-uplink-service-confirm-required`, cleanup passed, and final `selftest fail=0`.  Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA23_UPLINK_SERVICE_LIVE_PASS_2026-07-04.md`.

## 8. Next Implementation Unit

WSTA24 Debian-side uplink-service client/helper:

1. Add a Debian helper distinct from `a90-native-wifi-service-client`.
2. Support `status` and a no-confirm `autoconnect` denial probe only.
3. Reject confirmed autoconnect, connect, DHCP, ping, and public tunnel operations before request write
   unless a future credential-gated unit explicitly authorizes them.
4. Stage the helper through the SD-backed Debian rootfs preparation path.
5. Live-gate helper behavior against resident V3387 without running association/DHCP.

WSTA24 source result: pass.  `/usr/local/bin/a90-native-wifi-uplink-client` now supports only
`status` and `autoconnect-no-confirm`, deny-lists confirmed autoconnect/connect/DHCP/ping/public
tunnel before request write, filters response output to redacted allowlisted keys, and is staged by
both the WSTA3 private rootfs preparer and base Debian rootfs builder.  Host validation passed with
shell syntax, `py_compile`, and 25 unit tests.  Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA24_UPLINK_CLIENT_SOURCE_2026-07-04.md`.

## 9. Next Implementation Unit

WSTA24 live gate on resident V3387:

1. Confirm resident V3387 health and `selftest fail=0`.
2. Mount the SD-backed Debian chroot and start temporary key-only dropbear as in WSTA22.
3. Start native `wifi uplink-service` in a chroot-visible service directory.
4. Run `/usr/local/bin/a90-native-wifi-uplink-client status` from Debian and verify pass/redaction.
5. Run `/usr/local/bin/a90-native-wifi-uplink-client autoconnect-no-confirm` from Debian and verify
   `wifi-uplink-service-confirm-required`.
6. Stop native service, remove temporary helper staging if used, cleanup chroot/dropbear/loop state,
   and finish with `selftest fail=0`.

Do not run confirmed autoconnect, association, DHCP, ping, or public tunnel work in WSTA24.

WSTA24 live result: pass on resident V3387.  The live runner
`workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py` verified
resident `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`, baseline
`selftest fail=0`, and the hardware contract.  The SD-backed Debian rootfs image was refreshed to
expected SHA `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`, then mounted as
a chroot with temporary key-only dropbear.  The runner staged
`/usr/local/bin/a90-native-wifi-uplink-client`, started native `wifi uplink-service`, and proved:

- helper `status`: `native-wifi-uplink-client-pass` plus
  `wifi-uplink-service-status-pass`, `owner=native-init`, `credentials=0`, `connect=0`,
  `dhcp_routing=observed-only`, `public_tunnel=0`, and `secret_values_logged=0`;
- helper `autoconnect-no-confirm`: `native-wifi-uplink-client-pass`, native `rc=-13`,
  `wifi-uplink-service-confirm-required`, `connect=confirm-gated`, `dhcp_routing=config-gated`,
  `external_ping_execution=0`, and `public_tunnel=0`.

Service stop, helper cleanup, chroot/dropbear/loop cleanup, and final V3387 `selftest fail=0`
passed.  No boot flash, switch-root, userdata touch, association, confirm-token supply, DHCP, ping,
or public tunnel action ran.  Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA24_UPLINK_CLIENT_LIVE_PASS_2026-07-04.md`.

## 10. Next Implementation Unit

WSTA25 should be a separate credential-gated confirmed autoconnect/DHCP design or preflight unit:

1. Keep the default path no-confirm and denied.
2. Require an explicit confirm token and private credential-policy check before any association.
3. Keep DHCP/routing and public exposure as separate gates; do not couple public tunnel startup to
   confirmed Wi-Fi association.
4. Preserve redacted output: no SSID, PSK, BSSID, MAC, DHCP lease, concrete private IP, or public URL
   in committed reports.
5. Include cleanup and native health checks before/after any live credentialed run.

Until that unit is explicitly selected, confirmed association, DHCP, ping, and public tunnel execution
remain parked.

WSTA25 source/preflight result: pass.  The Debian-side
`/usr/local/bin/a90-native-wifi-uplink-client` now includes `autoconnect-confirmed`, but the path is
fail-closed by default and requires both environment gates before request write:

- `A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED=1`
- exact `A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN`

Without both gates, the helper exits before creating `request`.  With both gates, it writes
`op=autoconnect` plus the native confirm field and accepts a redacted
`wifi-uplink-service-autoconnect-pass` response without echoing the token.  Direct `autoconnect`,
`connect`, `dhcp`, `ping`, public tunnel, and ambiguous `confirmed-autoconnect` operations remain
denied before request write.  No live confirmed autoconnect, association, DHCP, ping, routing, public
tunnel, boot flash, switch-root, userdata touch, or credential-value logging ran.  Validation passed:
shell syntax, `py_compile`, and focused helper/rootfs/WSTA tests (`32 tests`, `OK`).  Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA25_CONFIRMED_GATE_SOURCE_2026-07-04.md`.

## 11. Next Implementation Unit

WSTA25 live confirmed-autoconnect gate, only if explicitly selected:

1. Require resident V3387 or later and native health `selftest fail=0`.
2. Mount the SD-backed Debian chroot and start temporary key-only dropbear.
3. Start native `wifi uplink-service` in a chroot-visible service directory.
4. Run the Debian helper `autoconnect-confirmed` with both WSTA25 environment gates.
5. Collect only redacted response metadata: owner, decision, rc, carrier/default-route booleans,
   autoconnect result fields, and secret hygiene markers.
6. Stop service, cleanup helper/chroot/dropbear/loop state, and finish with `selftest fail=0`.
7. Keep DHCP/routing and public exposure as separate gates unless the live unit explicitly expands to
   cover them.

WSTA25 live runner source/preflight result: pass.  The new
`workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py` runner is
fail-closed by default and stops before bridge/device/chroot work unless all live gates are supplied:

- `--allow-confirmed-live`
- `--ack-credentialed-wifi`
- matching `--confirm-token`

If those gates are supplied, the runner still performs a redacted status request first and requires
native readiness (`config_profile_present=1`, `profile_valid=1`, `autoconnect_ready=1`,
`autoconnect_enabled=1`) before invoking `autoconnect-confirmed`.  The confirmed helper command is
sent through SSH stdin with `input_redacted=1`, so the result command vector does not store the token.
Fail-closed dry run produced `wsta25-blocked-explicit-live-allow-required` with no device work.
Validation passed with `py_compile`, focused WSTA/helper/rootfs tests (`38 tests`, `OK`), and
`git diff --check`.  Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA25_LIVE_RUNNER_SOURCE_2026-07-04.md`.

## 12. Next Implementation Unit

Credentialed WSTA25 live execution is now mechanically ready but still explicitly gated.  If selected:

1. Run the WSTA25 live runner with all live gates.
2. Let the runner block if native status says autoconnect is not ready.
3. If ready, collect only redacted confirmed-autoconnect metadata and final native health.
4. Keep public exposure and any public tunnel startup out of this unit unless explicitly re-scoped.

WSTA25 host preflight result: pass.  The new
`workspace/public/src/scripts/server-distro/prepare_wsta25_live_gate_preflight.py` preflight validates
the private Wi-Fi env and live-runner gate surface without contacting the device.  Current local
metadata shows the Wi-Fi env exists, owner-private mode is true, SSID/PSK are present, SSID byte
length is `8`, PSK length is `11`, PSK format is `passphrase`, and `secret_values_logged=0`.
The WSTA25 live runner surface has explicit live gates, confirm-token arg, status readiness gate,
redacted SSH stdin executor, no direct `wifi connect`/`dhcp`/`ping`, and no public tunnel path.  The
default runner dry run still blocks before device access with
`wsta25-blocked-explicit-live-allow-required`.  The preflight emits only a redacted command template:
`--confirm-token <redacted:A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN>`.  Report:
`docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA25_LIVE_GATE_PREFLIGHT_2026-07-04.md`.

## 13. Next Implementation Unit

The explicit WSTA25 credentialed live run is now the next gated step:

1. Invoke `run_wsta25_confirmed_autoconnect_live.py` with all live gates.
2. Require resident V3387 or later and final native `selftest fail=0`.
3. Let runner status readiness decide whether confirmed request is sent.
4. If confirmed request is sent, record only redacted response metadata and cleanup evidence.
5. Keep public exposure/tunnel startup out of the unit.
